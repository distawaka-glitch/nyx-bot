import asyncio
import aiohttp
import random
import string
from config import CHECK_DELAY, CONCURRENCY, TRANSLIT, PERSONALITY_SUFFIXES

TG_API = "https://t.me/{}"
FRAG_API = "https://fragment.com/username/{}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def transliterate(word: str) -> str:
    out = []
    for ch in word.lower():
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif ch.isascii() and (ch.isalnum() or ch == "_"):
            out.append(ch)
    return "".join(out)


def generate_candidates(base: str, suffixes=None, max_len=32) -> list:
    base_lat = transliterate(base)
    if not base_lat:
        return []
    if suffixes is None:
        suffixes = PERSONALITY_SUFFIXES
    cands = {base_lat}
    for suf in suffixes:
        cand = base_lat + suf
        if len(cand) <= max_len:
            cands.add(cand)
    return sorted(cands)


def generate_random(length: int, count: int = 20) -> list:
    vowels = "aeiouy"
    consonants = "bcdfghjklmnpqrstvwxz"
    out = set()
    while len(out) < count:
        if length % 2 == 0:
            pattern = ["c", "v"] * (length // 2)
        else:
            pattern = ["c", "v"] * (length // 2) + ["c"]
        word = ""
        for p in pattern:
            if p == "v":
                word += random.choice(vowels)
            else:
                word += random.choice(consonants)
        if len(word) == length:
            out.add(word)
    return list(out)


def generate_random_digits(length: int, count: int = 20) -> list:
    letters = string.ascii_lowercase
    out = set()
    while len(out) < count:
        word = "".join(random.choices(letters, k=length - 1))
        word += str(random.randint(0, 9))
        word_list = list(word)
        random.shuffle(word_list)
        out.add("".join(word_list))
    return list(out)


async def check_username(session, username):
    url = TG_API.format(username)
    try:
        async with session.get(url, headers=HEADERS, allow_redirects=True, timeout=10) as resp:
            text = await resp.text()
            if resp.status != 200:
                return {"username": username, "taken": None, "status": resp.status}

            # Если есть tgme_page_title — точно занят (обычный профиль)
            if "tgme_page_title" in text:
                return {"username": username, "taken": True, "status": resp.status}

            # Проверка Fragment (только для NFT, где tgme_page_title может отсутствовать)
            frag_url = FRAG_API.format(username)
            try:
                async with session.get(frag_url, headers=HEADERS, allow_redirects=True, timeout=10) as frag_resp:
                    if frag_resp.status == 200:
                        frag_text = await frag_resp.text()
                        # Ищем маркер реального владельца (занят)
                        if "Owned by" in frag_text:
                            return {"username": username, "taken": True, "status": 200}
            except:
                pass

            # Если ничего не нашли — свободен
            return {"username": username, "taken": False, "status": resp.status}
    except Exception as e:
        return {"username": username, "taken": None, "error": str(e)}


async def check_many(usernames, progress_cb=None):
    sem = asyncio.Semaphore(CONCURRENCY)
    results = []
    done = 0
    total = len(usernames)

    async with aiohttp.ClientSession() as session:
        async def worker(u):
            nonlocal done
            async with sem:
                r = await check_username(session, u)
                await asyncio.sleep(CHECK_DELAY)
                done += 1
                if progress_cb:
                    await progress_cb(done, total, r)
                return r
        tasks = [asyncio.create_task(worker(u)) for u in usernames]
        for coro in asyncio.as_completed(tasks):
            results.append(await coro)
    return results


def filter_by_params(usernames, length=None, digits=None):
    out = []
    for u in usernames:
        if length is not None and len(u) != length:
            continue
        has_digit = any(c.isdigit() for c in u)
        if digits is True and not has_digit:
            continue
        if digits is False and has_digit:
            continue
        out.append(u)
    return out