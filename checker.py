import asyncio
import aiohttp
from config import CHECK_DELAY, CONCURRENCY, TRANSLIT, PERSONALITY_SUFFIXES

TG_API = "https://t.me/{}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}


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


async def check_username(session, username):
    try:
        async with session.get(TG_API.format(username), headers=HEADERS, allow_redirects=True, timeout=10) as resp:
            text = await resp.text()
            taken = 'tgme_page' in text and 'tgme_page_extra' in text
            if "tgme_page_title" not in text:
                taken = False
            return {"username": username, "taken": taken, "status": resp.status}
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
