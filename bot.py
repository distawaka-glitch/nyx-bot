import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, OWNER_ID
from checker import (
    check_many, generate_candidates, filter_by_params,
    generate_random, generate_random_digits
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_state = {}


def is_owner(obj) -> bool:
    u = getattr(obj, "from_user", None)
    return u is not None and u.id == OWNER_ID


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

    words = []
    if len(parts) > 1:
        words = parts[1].split()

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
        if digits is True:
            cands = generate_random_digits(gen_len, count=30)
        else:
            cands = generate_random(gen_len, count=30)

    cands = list(dict.fromkeys(cands))
    filtered = filter_by_params(cands, length=length, digits=digits)
    if not filtered:
        return await status.edit_text("нет кандидатов. измени фильтры или добавь слова.")

    await status.edit_text(f"проверяю {len(filtered)} юзернеймов...")
    free = []

    async def progress(done, total, r):
        if done % 10 == 0 or done == total:
            try:
                await status.edit_text(f"{done}/{total}... свободно: {len(free)}")
            except:
                pass

    results = await check_many(filtered, progress_cb=progress)
    for r in results:
        if r["taken"] is False:
            free.append(r["username"])

    if free:
        text = f"найдено свободных: {len(free)}\n\n" + "\n".join("@" + u for u in free[:80])
        if len(free) > 80:
            text += f"\n... и ещё {len(free) - 80}"
    else:
        text = "свободных не найдено. попробуй другие параметры."

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
    results = await check_many(usernames)
    lines = []
    for r in results:
        if r["taken"] is True:
            lines.append(f"@{r['username']} занят")
        elif r["taken"] is False:
            lines.append(f"@{r['username']} свободен")
        else:
            lines.append(f"@{r['username']} ошибка: {r.get('error', '?')}")
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