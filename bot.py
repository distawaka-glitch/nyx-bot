import asyncio
import logging
import os
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
business_logs = []

settings = {
    "ai": False,
    "voice": False,
    "antiscam": False,
    "filter": False,
    "video": False,
    "autoresponder": False
}
stop_words = ["скам", "крипта", "инвестиции", "обман"]

ADMINS = {8422944555, 8769561220, 6646589541}

def is_owner(obj) -> bool:
    u = getattr(obj, "from_user", None)
    return u is not None and u.id in ADMINS

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Описание команд", callback_data="help_cmds")],
        [InlineKeyboardButton(text="💬 Диалоги", callback_data="dialogs")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="🤖 Автоответчик", callback_data="toggle_autoresponder")],
        [InlineKeyboardButton(text="🔍 Поиск юзов", callback_data="search_usernames")],
        [InlineKeyboardButton(text="🌟 Премиум функционал", callback_data="premium")]
    ])

def settings_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🤖 ИИ: {'Вкл' if settings['ai'] else 'Выкл'}", callback_data="toggle_ai")],
        [InlineKeyboardButton(text=f"🎙 Голосовые: {'Вкл' if settings['voice'] else 'Выкл'}", callback_data="toggle_voice")],
        [InlineKeyboardButton(text=f"⚠️ Антискам: {'Вкл' if settings['antiscam'] else 'Выкл'}", callback_data="toggle_antiscam")],
        [InlineKeyboardButton(text=f"🔫 Тесак Фильтр: {'Вкл' if settings['filter'] else 'Выкл'}", callback_data="toggle_filter")],
        [InlineKeyboardButton(text=f"🖼 Загрузка видео: {'Вкл' if settings['video'] else 'Выкл'}", callback_data="toggle_video")],
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
    await message.answer("**Ваши настройки**\nВыберите раздел для управления:", reply_markup=main_menu_kb(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_settings(call: CallbackQuery):
    key = call.data.replace("toggle_", "")
    if key in settings:
        settings[key] = not settings[key]
        await call.message.edit_reply_markup(reply_markup=settings_kb())
        await call.answer(f"Статус изменен: {'Вкл' if settings[key] else 'Выкл'}")
    elif key == "autoresponder":
        settings["autoresponder"] = not settings["autoresponder"]
        await call.answer(f"Автоответчик: {'Вкл' if settings['autoresponder'] else 'Выкл'}")

@dp.callback_query(F.data.in_({"settings", "back_to_main", "search_usernames", "dialogs", "help_cmds", "premium"}))
async def menu_callbacks(call: CallbackQuery):
    if call.data == "settings":
        await call.message.edit_text("**Настройки функций:**", reply_markup=settings_kb(), parse_mode="Markdown")
    elif call.data == "search_usernames":
        user_state[call.from_user.id] = {"length": None, "digits": None}
        await call.message.edit_text("**Поиск юзернеймов**\nНастройте параметры:", reply_markup=search_kb(), parse_mode="Markdown")
    elif call.data == "back_to_main":
        await call.message.edit_text("**Ваши настройки**\nВыберите раздел:", reply_markup=main_menu_kb(), parse_mode="Markdown")
    elif call.data == "help_cmds":
        text = "📖 **Описание команд:**\n\n/help — это меню\n/find — поиск юзов\n/check [ник] — проверить ник"
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_kb())
    elif call.data == "premium":
        text = "🌟 **Премиум функционал**\n\nВ этом боте всё бесплатно. Никаких подписок и ограничений."
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_kb())
    elif call.data == "dialogs":
        if not business_logs:
            text = "💬 **Диалоги**\n\nПока нет сообщений."
        else:
            text = "💬 **Последние сообщения:**\n\n" + "\n".join(business_logs[-10:])
        await call.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_kb())
    await call.answer()

@dp.business_message()
async def handle_business_message(message: Message):
    user_id = message.from_user.id
    text = message.text or ""
    
    log_entry = f"@{message.from_user.username or user_id}: {text[:30]}"
    business_logs.append(log_entry)
    if len(business_logs) > 50: business_logs.pop(0)

    if settings["antiscam"] and any(w in text.lower() for w in stop_words):
        await bot.send_message(
            chat_id=message.chat.id,
            text="⚠️ Сообщение заблокировано антискам-фильтром.",
            business_connection_id=message.business_connection_id
        )
        return

    if settings["filter"] and "хуй" in text.lower():
        await bot.send_message(
            chat_id=message.chat.id,
            text="🔫 Тесак-фильтр: не матерись.",
            business_connection_id=message.business_connection_id
        )
        return

    if settings["autoresponder"]:
        await bot.send_message(
            chat_id=message.chat.id,
            text="🤖 Я сейчас занят, отвечу позже.",
            business_connection_id=message.business_connection_id
        )

@dp.message(Command("find"))
async def cmd_find(msg: Message):
    if not is_owner(msg): return await msg.answer("доступ закрыт")
    parts = msg.text.split(maxsplit=1)
    words = parts[1].split() if len(parts) > 1 else []
    st = user_state.setdefault(msg.from_user.id, {"length": None, "digits": None})
    length = st.get("length")
    digits = st.get("digits")
    
    if not length and not words:
        return await msg.answer("выбери длину через /help -> Поиск юзов")

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
    logging.info("bot starting...")
    await asyncio.gather(start_web(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())