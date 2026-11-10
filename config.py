import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
CHECK_DELAY = float(os.getenv("CHECK_DELAY", "0.8"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "5"))

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
    "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}

PERSONALITY_SUFFIXES = [
    "ov", "ova", "ev", "eva", "in", "ina", "sky", "skaya",
    "enko", "uk", "yuk", "ich", "ovich", "ovna", "ichna",
    "man", "boy", "girl", "x", "xx", "pro", "top", "off",
    "on", "ik", "ka", "ok", "ek",
]
