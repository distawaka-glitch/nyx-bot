import asyncio
import random
import string
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.tl.types import InputPeerChannel
from config import API_ID, API_HASH, TG_SESSION, TRANSLIT, PERSONALITY_SUFFIXES

client = TelegramClient(StringSession(TG_SESSION), API_ID, API_HASH)

async def check_username_free(username: str) -> bool:
    """Проверяет, можно ли занять ник для канала."""
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False
        
        try:
            # ResolveUsername ищет ник в Telegram
            await client(functions.contacts.ResolveUsernameRequest(username=username))
            return False # Нашел - значит занят
        except errors.rpcerrorlist.UsernameNotOccupiedError:
            return True # Не найден - свободен
        except errors.rpcerrorlist.UsernameInvalidError:
            return False # Некорректная ссылка (карантин/запрет)
        except Exception:
            return False # Другие ошибки - пропускаем
    except:
        return False

async def try_claim_username(username: str):
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return False, "сессия не авторизована"

        result = await client(functions.channels.CreateChannelRequest(
            title=f"claim_{username}", about="temp", megagroup=False
        ))
        channel = result.chats[0]
        peer = InputPeerChannel(channel.id, channel.access_hash)

        await client(functions.channels.UpdateUsernameRequest(
            channel=peer, username=username
        ))
        return True, f"✅ @{username} -> t.me/{username}"

    except errors.rpcerrorlist.UsernameOccupiedError:
        return False, f"@{username} занят"
    except errors.rpcerrorlist.UsernamePurchaseAvailableError:
        return False, f"@{username} продаётся на Fragment"
    except errors.rpcerrorlist.UsernameInvalidError:
        return False, f"@{username} некорректная ссылка (карантин)"
    except errors.rpcerrorlist.FloodWaitError as e:
        return False, f"флуд-вейт {e.seconds} сек"
    except Exception as e:
        return False, f"ошибка: {str(e)}"

# ... (функции generate_candidates, generate_random, generate_random_digits, filter_by_params остаются такими же, как в прошлом скрипте)