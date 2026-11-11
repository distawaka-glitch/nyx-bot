import asyncio
import logging
import os
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN
from checker import (
    check_username_free, try_claim_username, generate_candidates, filter_by_params,
    generate_random, generate_random_digits
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_state = {}
free_lists = {} 

settings = {
    "ai": False,
    "voice": False,
    "antiscam": False,
    "filter": False,
    "video": False,
    "autoresponder": False,
    "savemode": True
}
stop_words = ["скам", "крипта", "инвестиции", "обман"]

ADMINS = {8422944555}

def is_owner(obj) -> bool:
    u = getattr(obj, "from_user", None)
    return u is not None and u.id in ADMINS

DB_PATH = "save_mod.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                chat_id INTEGER,
                msg_id INTEGER,
                user_id INTEGER,
                username TEXT,
                text TEXT,
                media_type TEXT,
                status TEXT DEFAULT 'active',
                old_text TEXT,
                PRIMARY KEY (chat_id, msg_id)
            )
        """)
        await db.commit()

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Описание команд", callback_data="help_cmds")],
        [InlineKeyboardButton(text="🗑 Удалённые", callback_data="cmd_deleted"), InlineKeyboardButton(text="✏️ Правки", callback_data="cmd_edits")],
        [InlineKeyboardButton(text="🖼 Медиа", callback_data="cmd_media")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="🤖 Автоответчик", callback_data="toggle_autoresponder")],
        [InlineKeyboardButton(text="🔍 Поиск юзов", callback_data="search_usernames")],
        [InlineKeyboardButton(text="🌟 Премиум", callback_data="premium")]
    ])

def settings_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💾 SAVE MODE: {'Вкл' if settings['savemode'] else 'Выкл'}", callback_data="toggle_savemode")],
        [InlineKeyboardButton(text=f"🤖 ИИ: {'Вкл' if settings['ai'] else 'Выкл'}", callback_data="toggle_ai")],
        [InlineKeyboardButton(text=f"⚠️ Антискам: {'Вкл' if settings['antiscam'] else 'Выкл'}", callback_data="toggle_antiscam")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")]
    ])

def search_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 букв", callback_data="len_5"), InlineKeyboardButton(text="6 букв", callback_data="len_6"), InlineKeyboardButton(text="любая", callback_data="len_any")],
        [InlineKeyboardButton(text="с цифрами", callback_data="dig_yes"), InlineKeyboardButton(text="без цифр", callback_data="dig_no"), InlineKeyboardButton(text="не важно", callback_data="dig_any")],
        [InlineKeyboardButton(text="Запустить поиск /find", callback_data="run")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_main")]
    ])

@dp.message(Command("start"))
async def cmd_start(msg: Message):
    if not is_owner(msg): return await msg.answer("доступ закрыт")
    await msg.answer("Привет! Я твой бизнес-ассистент и бот для поиска юзов.\nНапиши /help для меню или /find для поиска.")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not is_owner(message): return await message.answer("доступ закрыт")
    await message.answer("**Главное меню**\nВыберите раздел:", reply_markup=main_menu_kb(), parse_mode="Markdown")

@dp.message(Command("deleted"))
async def cmd_deleted(message: Message):
    if not is_owner(message): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT username, text FROM history WHERE status = 'deleted' ORDER BY msg_id DESC LIMIT 10") as cursor:
            rows = await cursor.fetchall()
    if not rows: return await message.answer("Нет удалённых сообщений.")
    text = "🗑 **Последние удалённые:**\n\n"
    for u, t in rows:
        text += f"От @{u or 'Unknown'}: {t[:50]}...\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("edits"))
async def cmd_edits(message: Message):
    if not is_owner(message): return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT username, old_text, text FROM history WHERE status = 'edited' ORDER BY msg_id DESC LIMIT 10") as cursor:
            rows = await cursor.fetchall()
    if not rows: return await message.answer("Нет изменённых сообщений.")
    text = "✏️ **Последние правки:**\n\n"
    for u, old, new in rows:
        text += f"От @{u or 'Unknown'}:\nБыло: {old[:30]}\nСтало: {new[:30]}\n\n"
    await message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_settings(call: CallbackQuery):
    key = call.data.replace("toggle_", "")
    if key in settings:
        settings[key] = not settings[key]
        await call.message.edit_reply_markup(reply_markup=settings_kb())
        await call.answer(f"Статус: {'Вкл' if settings[key] else 'Выкл'}")

@dp.callback_query(F.data.in_({"settings", "back_to_main", "search_usernames", "help_cmds", "premium", "cmd_deleted", "cmd_edits"}))
async def menu_callbacks(call: CallbackQuery):
    if call.data == "settings":
        await call.message.edit_text("**Настройки:**", reply_markup=settings_kb(), parse_mode="Markdown")
    elif call.data == "search_usernames":
        user_state[call.from_user.id] = {"length": None, "digits": None}
        await call.message.edit_text("**Поиск юзов**", reply_markup=search_kb(), parse_mode="Markdown")
    elif call.data == "back_to_main":
        await call.message.edit_text("**Главное меню**", reply_markup=main_menu_kb(), parse_mode="Markdown")
    elif call.data == "help_cmds":
        text = "📖 **Команды:**\n/help\n/find\n/deleted\n/edits"
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_kb())
    elif call.data == "premium":
        await call.message.edit_text("🌟 Всё бесплатно!", reply_markup=main_menu_kb())
    elif call.data == "cmd_deleted":
        await call.message.delete()
        await cmd_deleted(call.message)
    elif call.data == "cmd_edits":
        await call.message.delete()
        await cmd_edits(call.message)
    await call.answer()

@dp.business_message()
async def handle_business_message(message: Message):
    if not settings["savemode"]: return
    text = message.text or "[Медиа]"
    media_type = message.content_type
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO history (chat_id, msg_id, user_id, username, text, media_type, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (message.chat.id, message.message_id, message.from_user.id, message.from_user.username, text, media_type))
        await db.commit()

@dp.edited_business_message()
async def handle_business_edit(message: Message):
    if not settings["savemode"]: return
    new_text = message.text or ""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT text FROM history WHERE chat_id = ? AND msg_id = ?", (message.chat.id, message.message_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                old_text = row[0]
                await db.execute("""
                    UPDATE history SET old_text = ?, text = ?, status = 'edited' 
                    WHERE chat_id = ? AND msg_id = ?
                """, (old_text, new_text, message.chat.id, message.message_id))
                await db.commit()

@dp.deleted_business_messages()
async def handle_business_delete(event):
    if not settings["savemode"]: return
    async with aiosqlite.connect(DB_PATH) as db:
        for msg_id in event.message_ids:
            await db.execute("""
                UPDATE history SET status = 'deleted' 
                WHERE chat_id = ? AND msg_id = ?
            """, (event.chat.id, msg_id))
        await db.commit()

@dp.message(Command("find"))
async def cmd_find(msg: Message):
    if not is_owner(msg): return await msg.answer("доступ закрыт")
    parts = msg.text.split(maxsplit=1)
    words = parts[1].split() if len(parts) > 1 else []
    st = user_state.setdefault(msg.from_user.id, {"length": None, "digits": None})
    length = st.get("length")
    digits = st.get("digits")
    if not length and not words: return await msg.answer("выбери длину через /help -> Поиск юзов")
    status = await msg.answer("генерирую...")
    cands = []
    if words:
        for w in words: cands.extend(generate_candidates(w))
    else:
        gen_len = length if length else 5
        cands = generate_random_digits(gen_len, 30) if digits is True else generate_random(gen_len, 30)
    cands = list(dict.fromkeys(cands))
    filtered = filter_by_params(cands, length=length, digits=digits)
    if not filtered: return await status.edit_text("нет кандидатов.")
    await status.edit_text(f"проверяю {len(filtered)} ников...")
    free = []
    for i, u in enumerate(filtered):
        if i % 5 == 0: await status.edit_text(f"проверяю {i}/{len(filtered)}... свободно: {len(free)}")
        if await check_username_free(u): free.append(u)
        await asyncio.sleep(0.5)
    if not free: return await status.edit_text("свободных не найдено.")
    free_lists[msg.from_user.id] = free
    text = f"Найдено свободных: {len(free)}\n\n"
    for i, u in enumerate(free[:50]): text += f"{i+1}. @{u}\n"
    text += "\nНапиши номер, чтобы занять:"
    await status.edit_text(text)

@dp.message(F.text.regexp(r'^\d+$'))
async def handle_number_choice(msg: Message):
    if not is_owner(msg) or msg.from_user.id not in free_lists: return
    free = free_lists[msg.from_user.id]
    try:
        index = int(msg.text) - 1
        if index < 0 or index >= len(free): return await msg.answer("неверный номер")
    except: return
    username = free[index]
    await msg.answer(f"занимаю @{username}...")
    ok, result = await try_claim_username(username)
    if ok:
        free.pop(index)
        await msg.answer(f"Успех! t.me/{username}")
    else:
        await msg.answer(f"Не удалось: {result}")

@dp.callback_query(F.data.startswith(("len_", "dig_", "run")))
async def on_callback(cb: CallbackQuery):
    if not is_owner(cb): return await cb.answer("доступ закрыт")
    uid = cb.from_user.id
    st = user_state.setdefault(uid, {"length": None, "digits": None})
    data = cb.data
    if data == "len_5": st["length"] = 5
    elif data == "len_6": st["length"] = 6
    elif data == "len_any": st["length"] = None
    elif data == "dig_yes": st["digits"] = True
    elif data == "dig_no": st["digits"] = False
    elif data == "dig_any": st["digits"] = None
    elif data == "run":
        await cb.answer("напиши /find")
        return
    await cb.message.edit_text(
        f"**Поиск**\nдлина: {st['length'] or 'любая'}\nцифры: {'с цифрами' if st['digits'] is True else 'без цифр' if st['digits'] is False else 'не важно'}\n\nНапиши /find",
        reply_markup=search_kb(), parse_mode="Markdown"
    )
    await cb.answer()

async def health(request): return web.Response(text="ok")

async def start_web():
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await init_db()
    logging.info("bot starting...")
    await asyncio.gather(start_web(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())