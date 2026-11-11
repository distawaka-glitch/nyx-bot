import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN
from checker import (
    try_claim_username, generate_candidates, filter_by_params,
    generate_random, generate_random_digits
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_state = {}

ADMINS = {8422944555, 8769561220, 6646589541}

def is_owner(obj) -> bool:
    u = getattr(obj, "from_user", None)
    return u is not None and u.id in ADMINS

def menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 букв", callback_data="len_5"), InlineKeyboardButton(text="6 букв", callback_data="len_6"), InlineKeyboardButton(text="любая", callback_data="len_any")],
        [InlineKeyboardButton(text="с цифрами", callback_data="dig_yes"), InlineKeyboardButton(text="без цифр", callback_data="dig_no"), InlineKeyboardButton(text="не важно", callback_data="dig_any")],
        [InlineKeyboardButton(text="команда /find", callback_data="run")],
    ])

@dp.message(Command("start"))
async def cmd_start(msg: Message):
    if not is_owner(msg):
        return await msg.answer("доступ закрыт")
    user_state[msg.from_user.id] = {"length": None, "digits": None}
    await msg.answer("настрой параметры:\nзатем: /find калаш лампа ников\nили просто /find (без слов) для случайных", reply_markup=menu_kb())

@dp.message(Command("find"))
async def cmd_find(msg: Message):
    if not is_owner(msg):
        return await msg.answer("доступ закрыт")
    parts = msg.text.split(maxsplit=1)
    words = parts[1].split() if len(parts) > 1 else []
    st = user_state.setdefault(msg.from_user.id, {"length": None, "digits": None})
    length = st.get("length")
    digits = st.get("digits")
    if not length and not words:
        return await msg.answer("выбери длину (5, 6 или любая) через кнопки выше")

    status = await msg.answer("генерирую кандидатов...")
    cands = []
    if words:
        for w in words:
            cands.extend(generate_candidates(w))
    else:
        gen_len = length if length else 5
        cands = generate_random_digits(gen_len, 30) if digits is True else generate_random(gen_len, 30)

    cands = list(dict.fromkeys(cands))
    filtered = filter_by_params(cands, length=length, digits=digits)
    if not filtered:
        return await status.edit_text("нет кандидатов.")

    await status.edit_text(f"проверяю и занимаю {len(filtered)} ников...")
    success = []
    for i, u in enumerate(filtered):
        if i % 5 == 0:
            await status.edit_text(f"проверяю {i}/{len(filtered)}...\nзанято: {len(success)}")
        ok, result = await try_claim_username(u)
        if ok:
            success.append(result)
            await asyncio.sleep(1.5)

    text = f"Успешно занято: {len(success)}\n\n" + "\n".join(success) if success else "Не удалось занять ни один ник."
    await status.edit_text(text[:4000])

@dp.message(Command("check"))
async def cmd_check(msg: Message):
    if not is_owner(msg):
        return await msg.answer("доступ закрыт")
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return await msg.answer("формат: /check nick1 nick2")
    usernames = [u.strip().lstrip("@").lower() for u in parts[1].split()]
    status = await msg.answer(f"проверяю {len(usernames)}...")
    lines = []
    for u in usernames:
        ok, result = await try_claim_username(u)
        lines.append(result)
    await status.edit_text("\n".join(lines)[:4000])

@dp.callback_query(F.data.startswith(("len_", "dig_", "run")))
async def on_callback(cb: CallbackQuery):
    if not is_owner(cb):
        return await cb.answer("доступ закрыт")
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
        await cb.answer("используй /find слово1 слово2 или просто /find")
        return
    await cb.message.edit_text(
        f"параметры:\nдлина: {st['length'] or 'любая'}\nцифры: {'с цифрами' if st['digits'] is True else 'без цифр' if st['digits'] is False else 'не важно'}\n\nтеперь: /find калаш лампа ников",
        reply_markup=menu_kb(),
    )
    await cb.answer()

async def health(request):
    return web.Response(text="ok")

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
    await asyncio.gather(
        start_web(),
        dp.start_polling(bot),
    )

if __name__ == "__main__":
    asyncio.run(main())