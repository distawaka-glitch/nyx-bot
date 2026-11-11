import asyncio
import random
import string
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.tl.types import InputPeerChannel, InputPeerEmpty, InputChannel
from config import API_ID, API_HASH, TG_SESSION, TRANSLIT, PERSONALITY_SUFFIXES

client = TelegramClient(StringSession(TG_SESSION), API_ID, API_HASH)

async def check_username_free(username: str) -> bool:
    """Возвращает True, если ник свободен, False если занят"""
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False
        
        # Проверяем через CheckUsername, но для этого нужен канал.
        # Поэтому просто пытаемся найти юзернейм через ResolveUsername (если найдет - занят)
        try:
            await client(functions.contacts.ResolveUsernameRequest(username=username))
            return False # Нашел - значит занят
        except errors.rpcerrorlist.UsernameNotOccupiedError:
            return True # Не найден - свободен
        except Exception:
            return False # Ошибка - считаем занятым
    except:
        return False

async def try_claim_username(username: str):
    """Пытается создать канал и назначить ему юзернейм"""
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, "сессия не авторизована"

        # 1. Создаем канал
        result = await client(functions.channels.CreateChannelRequest(
            title=f"claim_{username}", about="temp", megagroup=False
        ))
        channel = result.chats[0]
        peer = InputPeerChannel(channel.id, channel.access_hash)

        # 2. Занимаем ник
        await client(functions.channels.UpdateUsernameRequest(
            channel=peer, username=username
        ))
        return True, f"✅ @{username} -> t.me/{username}"

    except errors.rpcerrorlist.UsernameOccupiedError:
        return False, f"@{username} занят"
    except errors.rpcerrorlist.UsernamePurchaseAvailableError:
        return False, f"@{username} продаётся на Fragment"
    except errors.rpcerrorlist.FloodWaitError as e:
        return False, f"флуд-вейт {e.seconds} сек"
    except Exception as e:
        return False, f"ошибка: {str(e)}"


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