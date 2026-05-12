import logging
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from config import settings
from database.db_queries import (
    get_user, update_user_balance, update_total_spent,
    create_order, log_transaction
)
from keyboards.reply_kb import get_main_menu

logger = logging.getLogger(__name__)
router = Router()

USD_TO_SOM = 12700


# ══════════════════════════════════════════════════════════════════════════════
# 📌 STATES
# ══════════════════════════════════════════════════════════════════════════════

class OrderStates(StatesGroup):
    searching_service = State()
    waiting_quantity  = State()
    waiting_link      = State()
    confirming_order  = State()


# ══════════════════════════════════════════════════════════════════════════════
# 📦 ASOSIY KATEGORIYALAR
# ══════════════════════════════════════════════════════════════════════════════

CATEGORIES = [
    {"id": "telegram",   "name": "🔵 Telegram",          "emoji": "🔵"},
    {"id": "instagram",  "name": "🟣 Instagram",          "emoji": "🟣"},
    {"id": "youtube",    "name": "🔴 YouTube",            "emoji": "🔴"},
    {"id": "tiktok",     "name": "⚫ TikTok",             "emoji": "⚫"},
    {"id": "tg_premium", "name": "💠 TG Premium & Stars", "emoji": "💠"},
    {"id": "free",       "name": "🎁 Tekin Xizmatlar",   "emoji": "🎁"},
]

# ══════════════════════════════════════════════════════════════════════════════
# 🗂 SUB-KATEGORIYALAR
# format: SUB_CATEGORIES[cat_id] = [{"id": "...", "name": "...", "icon": "..."}, ...]
# ══════════════════════════════════════════════════════════════════════════════

SUB_CATEGORIES = {
    "telegram": [
        {"id": "tg_sub_members",   "name": "👥 A'zolar",         "icon": "👥"},
        {"id": "tg_sub_views",     "name": "👀 Ko'rishlar",       "icon": "👀"},
        {"id": "tg_sub_reactions", "name": "❤️ Reaktsiyalar",     "icon": "❤️"},
        {"id": "tg_sub_comments",  "name": "💬 Izohlar & Boshqa", "icon": "💬"},
    ],
    "instagram": [
        {"id": "ig_sub_followers", "name": "👥 Obunachilar",   "icon": "👥"},
        {"id": "ig_sub_likes",     "name": "❤️ Layklar",        "icon": "❤️"},
        {"id": "ig_sub_views",     "name": "👁 Ko'rishlar",     "icon": "👁"},
        {"id": "ig_sub_other",     "name": "💬 Izoh & Boshqa",  "icon": "💬"},
    ],
    "youtube": [
        {"id": "yt_sub_views",       "name": "👀 Ko'rishlar",    "icon": "👀"},
        {"id": "yt_sub_subscribers", "name": "🔔 Obunachilar",   "icon": "🔔"},
        {"id": "yt_sub_likes",       "name": "👍 Layklar",       "icon": "👍"},
        {"id": "yt_sub_other",       "name": "💬 Izoh & Boshqa", "icon": "💬"},
    ],
    "tiktok": [
        {"id": "tt_sub_followers", "name": "👥 Obunachilar",   "icon": "👥"},
        {"id": "tt_sub_likes",     "name": "❤️ Layklar",        "icon": "❤️"},
        {"id": "tt_sub_views",     "name": "👀 Ko'rishlar",     "icon": "👀"},
        {"id": "tt_sub_other",     "name": "💬 Izoh & Boshqa", "icon": "💬"},
    ],
    "tg_premium": [
        {"id": "tgp_sub_premium", "name": "💠 Premium Obuna", "icon": "💠"},
        {"id": "tgp_sub_stars",   "name": "⭐ Stars & Sovg'a", "icon": "⭐"},
    ],
    "free": [
        {"id": "free_sub_all", "name": "🎁 Barcha Tekin Xizmatlar", "icon": "🎁"},
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# 🗂 XIZMATLAR (sub-kategoriya bo'yicha)
# ══════════════════════════════════════════════════════════════════════════════

ALL_SERVICES = {

    # ── TELEGRAM → A'ZOLAR ───────────────────────────────────────────────────
    "tg_sub_members": [
        {
            "service": "tg_01",
            "name": "👥 A'zolar [ Real va Faol ]",
            "rate": "0.80", "min": 100, "max": 50000, "time": "0–2 soat",
            "info": [
                "📑 Tur: ⚡️ Real va faol a'zolar",
                "♻️ Tushsa — 30 kun kafolat",
                "⛔️ Chiqishlar: minimal",
                "👤 Kanal/guruh ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "tg_02",
            "name": "👥 A'zolar [ Premium Sifat ]",
            "rate": "1.20", "min": 50, "max": 20000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 💎 Premium sifat, uzoq qoladi",
                "♻️ Tushsa — to'ldiriladi (kafolat bor)",
                "⛔️ Chiqishlar: juda kam",
                "👤 Kanal/guruh ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "tg_03",
            "name": "👥 A'zolar [ Arzon va Tezkor ]",
            "rate": "0.40", "min": 200, "max": 100000, "time": "0–1 soat",
            "info": [
                "📑 Tur: 💨 Tezkor, katta hajmli",
                "♻️ Tiklashlar yo'q",
                "⛔️ Chiqishlar bor (tabiiy)",
                "👤 Kanal/guruh ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "tg_04",
            "name": "👥 A'zolar [ Bot Emas, Real ]",
            "rate": "1.80", "min": 100, "max": 30000, "time": "2–8 soat",
            "info": [
                "📑 Tur: 🧑 Haqiqiy profillar (rasm, post bor)",
                "♻️ Tushsa — 30 kun kafolat",
                "⛔️ Chiqishlar: kam",
                "👤 Kanal/guruh ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "tg_05",
            "name": "🇺🇿 A'zolar [ O'zbek, Real ]",
            "rate": "3.00", "min": 50, "max": 5000, "time": "2–12 soat",
            "info": [
                "📑 Tur: 🇺🇿 Faqat O'zbekistonlik foydalanuvchilar",
                "♻️ Tushsa — kafolat bor",
                "⛔️ Chiqishlar: minimal",
                "👤 Kanal ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "tg_06",
            "name": "🇺🇿 A'zolar [ O'zbek Guruh ]",
            "rate": "3.50", "min": 50, "max": 5000, "time": "2–24 soat",
            "info": [
                "📑 Tur: 🇺🇿 Guruhga O'zbek a'zolar",
                "♻️ Tushsa — kafolat bor",
                "⛔️ Chiqishlar: minimal",
                "👤 Guruh public bo'lishi kerak",
            ]
        },
        {
            "service": "tg_07",
            "name": "👥 A'zolar [ Xorijiy, Global ]",
            "rate": "0.30", "min": 100, "max": 200000, "time": "0–2 soat",
            "info": [
                "📑 Tur: 🌍 Dunyo bo'ylab aralash a'zolar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Chiqishlar bor (tabiiy)",
                "👤 Kanal ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "tg_08",
            "name": "👥 A'zolar [ Kanal — Sekin ]",
            "rate": "0.60", "min": 100, "max": 50000, "time": "6–24 soat",
            "info": [
                "📑 Tur: 🐢 Sekin va tabiiy o'sish",
                "♻️ Tushsa — 15 kun kafolat",
                "⛔️ Chiqishlar: juda kam",
                "👤 Kanal ochiq bo'lishi kerak",
            ]
        },
    ],

    # ── TELEGRAM → KO'RISHLAR ─────────────────────────────────────────────────
    "tg_sub_views": [
        {
            "service": "tg_v01",
            "name": "👀 Ko'rishlar [ Tezkor — 30 daqiqa ]",
            "rate": "0.08", "min": 500, "max": 1000000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: ⚡️ Eng tezkor ko'rishlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_v02",
            "name": "👀 Ko'rishlar [ Oxirgi 5 Post ]",
            "rate": "0.12", "min": 500, "max": 500000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: 📋 Oxirgi 5 postga bir vaqtda",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal",
                "🔗 Kanal linkini yuboring",
            ]
        },
        {
            "service": "tg_v03",
            "name": "👀 Ko'rishlar [ Oxirgi 10 Post ]",
            "rate": "0.15", "min": 500, "max": 500000, "time": "0–1 soat",
            "info": [
                "📑 Tur: 📋 Oxirgi 10 postga bir vaqtda",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal",
                "🔗 Kanal linkini yuboring",
            ]
        },
        {
            "service": "tg_v04",
            "name": "👀 Ko'rishlar [ Oxirgi 50 Post ]",
            "rate": "0.25", "min": 500, "max": 200000, "time": "0–2 soat",
            "info": [
                "📑 Tur: 📋 Oxirgi 50 postga bir vaqtda",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal",
                "🔗 Kanal linkini yuboring",
            ]
        },
        {
            "service": "tg_v05",
            "name": "👀 Ko'rishlar [ Barcha Postlarga ]",
            "rate": "0.40", "min": 500, "max": 100000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🗂 Kanalingizdagi BARCHA postlarga",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal",
                "🔗 Kanal linkini yuboring",
            ]
        },
        {
            "service": "tg_v06",
            "name": "🇺🇿 Ko'rishlar [ O'zbek ]",
            "rate": "0.35", "min": 500, "max": 100000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🇺🇿 O'zbek auditoriyasidan",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_v07",
            "name": "👀 Ko'rishlar [ Premium Akkauntlar ]",
            "rate": "0.55", "min": 100, "max": 100000, "time": "1–3 soat",
            "info": [
                "📑 Tur: 💎 Faqat Premium TG akkauntlardan",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
    ],

    # ── TELEGRAM → REAKTSIYALAR ───────────────────────────────────────────────
    "tg_sub_reactions": [
        {
            "service": "tg_r01",
            "name": "❤️🔥 Reaktsiyalar [ Aralash ]",
            "rate": "0.25", "min": 10, "max": 10000, "time": "0–1 soat",
            "info": [
                "📑 Tur: 🎭 Aralash (❤️ 👍 🔥 🎉 😍 💯)",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_r02",
            "name": "👍 Reaktsiya [ Like ]",
            "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: 👍 Faqat layk reaktsiyasi",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_r03",
            "name": "🔥 Reaktsiya [ Olov ]",
            "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: 🔥 Faqat olov reaktsiyasi",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_r04",
            "name": "🎉 Reaktsiya [ Bayram ]",
            "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: 🎉 Faqat bayram reaktsiyasi",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_r05",
            "name": "💯 Reaktsiya [ Yuz foiz ]",
            "rate": "0.22", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: 💯 Faqat 100 reaktsiyasi",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_r06",
            "name": "😍 Reaktsiya [ Havas ]",
            "rate": "0.22", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: 😍 Faqat havas reaktsiyasi",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_r07",
            "name": "❤️ Reaktsiya [ Qizil Yurak ]",
            "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: ❤️ Faqat qizil yurak reaktsiyasi",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_r08",
            "name": "👎 Reaktsiya [ Dislike ]",
            "rate": "0.22", "min": 10, "max": 5000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: 👎 Faqat dislike reaktsiyasi",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
    ],

    # ── TELEGRAM → IZOHLAR & BOSHQA ──────────────────────────────────────────
    "tg_sub_comments": [
        {
            "service": "tg_c01",
            "name": "💬 Izohlar [ Haqiqiy ]",
            "rate": "2.50", "min": 5, "max": 500, "time": "1–12 soat",
            "info": [
                "📑 Tur: 💬 Mazmunli haqiqiy izohlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Izoh yozish ochiq bo'lishi kerak",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_c02",
            "name": "📤 Ulashishlar [ Share ]",
            "rate": "0.30", "min": 100, "max": 50000, "time": "1–3 soat",
            "info": [
                "📑 Tur: 🔁 Post ulashishlar soni",
                "♻️ Tiklashlar yo'q",
                "⛔️ Faqat ochiq kanal postlari",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_c03",
            "name": "📊 So'rovnoma Ovozlari",
            "rate": "0.50", "min": 50, "max": 5000, "time": "0–2 soat",
            "info": [
                "📑 Tur: 🗳 So'rovnomaga ovoz qo'shish",
                "♻️ Tiklashlar yo'q",
                "⛔️ So'rovnoma ochiq bo'lishi kerak",
                "🔗 So'rovnoma havolasini yuboring",
            ]
        },
        {
            "service": "tg_c04",
            "name": "🔗 Havola Bosishlar [ Clicks ]",
            "rate": "0.45", "min": 100, "max": 50000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🖱 Postdagi havola bosishlar soni",
                "♻️ Tiklashlar yo'q",
                "⛔️ Havola ishlayotgan bo'lishi kerak",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "tg_c05",
            "name": "📣 Kanal Mention [ Eslatish ]",
            "rate": "5.00", "min": 10, "max": 1000, "time": "2–24 soat",
            "info": [
                "📑 Tur: 📣 Boshqa kanallarda eslatish",
                "♻️ Tiklashlar yo'q",
                "⛔️ Kanal public bo'lishi kerak",
                "🔗 Kanal @username yuboring",
            ]
        },
        {
            "service": "tg_c06",
            "name": "👁 Post Saqlashlar [ Forwards ]",
            "rate": "0.60", "min": 100, "max": 20000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 💾 Post forward va saqlash soni",
                "♻️ Tiklashlar yo'q",
                "⛔️ Post ochiq bo'lishi kerak",
                "🔗 Post havolasini yuboring",
            ]
        },
    ],

    # ── INSTAGRAM → OBUNACHILAR ───────────────────────────────────────────────
    "ig_sub_followers": [
        {
            "service": "ig_01",
            "name": "👥 Obunachilar [ Haqiqiy va Faol ]",
            "rate": "1.50", "min": 100, "max": 100000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🧑 Haqiqiy profillar (rasm, post bor)",
                "♻️ Tushsa — 30 kun kafolat",
                "⛔️ Chiqishlar: minimal",
                "👤 Profil ochiq (public) bo'lishi kerak",
            ]
        },
        {
            "service": "ig_02",
            "name": "👥 Obunachilar [ Premium Sifat ]",
            "rate": "2.50", "min": 50, "max": 30000, "time": "6–24 soat",
            "info": [
                "📑 Tur: 💎 Premium, uzoq muddatga qoladi",
                "♻️ Tushsa — to'ldiriladi (kafolat bor)",
                "⛔️ Chiqishlar: juda kam",
                "👤 Profil ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "ig_03",
            "name": "👥 Obunachilar [ Arzon, Tezkor ]",
            "rate": "0.80", "min": 100, "max": 50000, "time": "0–3 soat",
            "info": [
                "📑 Tur: 💨 Tezkor, arzon variant",
                "♻️ Tiklashlar yo'q",
                "⛔️ Chiqishlar bor (tabiiy)",
                "👤 Profil ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "ig_04",
            "name": "👥 Obunachilar [ Ayollar ]",
            "rate": "2.00", "min": 100, "max": 20000, "time": "2–12 soat",
            "info": [
                "📑 Tur: 👩 Asosan ayol foydalanuvchilar",
                "♻️ Tushsa — kafolat bor",
                "⛔️ Chiqishlar: minimal",
                "👤 Profil ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "ig_05",
            "name": "👥 Obunachilar [ Erkaklar ]",
            "rate": "2.00", "min": 100, "max": 20000, "time": "2–12 soat",
            "info": [
                "📑 Tur: 👨 Asosan erkak foydalanuvchilar",
                "♻️ Tushsa — kafolat bor",
                "⛔️ Chiqishlar: minimal",
                "👤 Profil ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "ig_06",
            "name": "👥 Obunachilar [ Arab ]",
            "rate": "1.80", "min": 100, "max": 50000, "time": "2–12 soat",
            "info": [
                "📑 Tur: 🇸🇦 Arab foydalanuvchilar",
                "♻️ Tushsa — kafolat bor",
                "⛔️ Chiqishlar: minimal",
                "👤 Profil ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "ig_07",
            "name": "👥 Obunachilar [ Turk ]",
            "rate": "1.60", "min": 100, "max": 50000, "time": "2–12 soat",
            "info": [
                "📑 Tur: 🇹🇷 Turk foydalanuvchilar",
                "♻️ Tushsa — kafolat bor",
                "⛔️ Chiqishlar: minimal",
                "👤 Profil ochiq bo'lishi kerak",
            ]
        },
    ],

    # ── INSTAGRAM → LAYKLAR ──────────────────────────────────────────────────
    "ig_sub_likes": [
        {
            "service": "ig_l01",
            "name": "❤️ Layklar [ Tezkor ]",
            "rate": "0.12", "min": 50, "max": 50000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: ⚡️ Eng tezkor layklar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Chiqishlar bor",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "ig_l02",
            "name": "❤️ Layklar [ Haqiqiy Profildan ]",
            "rate": "0.30", "min": 50, "max": 20000, "time": "1–3 soat",
            "info": [
                "📑 Tur: 🧑 Haqiqiy faol profillardan",
                "♻️ Tiklashlar yo'q",
                "⛔️ Chiqishlar: minimal",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "ig_l03",
            "name": "❤️ Layklar [ Oxirgi 5 Post ]",
            "rate": "0.50", "min": 100, "max": 10000, "time": "0–2 soat",
            "info": [
                "📑 Tur: 📋 Oxirgi 5 postga bir vaqtda",
                "♻️ Tiklashlar yo'q",
                "⛔️ Profil ochiq bo'lishi kerak",
                "👤 Profil @username yuboring",
            ]
        },
        {
            "service": "ig_l04",
            "name": "❤️ Layklar [ Oxirgi 10 Post ]",
            "rate": "0.90", "min": 100, "max": 10000, "time": "0–3 soat",
            "info": [
                "📑 Tur: 📋 Oxirgi 10 postga bir vaqtda",
                "♻️ Tiklashlar yo'q",
                "⛔️ Profil ochiq bo'lishi kerak",
                "👤 Profil @username yuboring",
            ]
        },
        {
            "service": "ig_l05",
            "name": "❤️ AutoLike [ 30 kun ]",
            "rate": "1.50", "min": 100, "max": 5000, "time": "Doimiy",
            "info": [
                "📑 Tur: 🤖 Har yangi postga avtomatik layk",
                "♻️ 30 kunlik avtomatik xizmat",
                "⛔️ Profil ochiq bo'lishi kerak",
                "👤 Profil @username yuboring",
            ]
        },
        {
            "service": "ig_l06",
            "name": "❤️ Layklar [ Arab ]",
            "rate": "0.40", "min": 50, "max": 20000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🇸🇦 Arab profillardan layklar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Post ochiq bo'lishi kerak",
                "🔗 Post havolasini yuboring",
            ]
        },
    ],

    # ── INSTAGRAM → KO'RISHLAR ────────────────────────────────────────────────
    "ig_sub_views": [
        {
            "service": "ig_v01",
            "name": "👁 Ko'rishlar [ Video va Reels ]",
            "rate": "0.07", "min": 500, "max": 1000000, "time": "0–1 soat",
            "info": [
                "📑 Tur: 🎬 Video va Reels ko'rishlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Post ochiq bo'lishi kerak",
                "🔗 Video/Reels havolasini yuboring",
            ]
        },
        {
            "service": "ig_v02",
            "name": "📊 Story Ko'rishlar",
            "rate": "0.10", "min": 100, "max": 100000, "time": "0–2 soat",
            "info": [
                "📑 Tur: 📖 Story ko'rishlar soni",
                "♻️ Tiklashlar yo'q",
                "⛔️ Story aktiv bo'lishi kerak (24 soat)",
                "👤 Profil @username yuboring",
            ]
        },
        {
            "service": "ig_v03",
            "name": "🔴 Live Ko'ruvchilar",
            "rate": "1.50", "min": 10, "max": 1000, "time": "0–10 daqiqa",
            "info": [
                "📑 Tur: 🔴 Live efir ko'ruvchilari",
                "♻️ Live tugagach ketadi (tabiiy)",
                "⛔️ Live ayni paytda ishlayotgan bo'lsin",
                "🔗 Profil havolasini yuboring",
            ]
        },
        {
            "service": "ig_v04",
            "name": "🟡 IGTV Ko'rishlar",
            "rate": "0.15", "min": 500, "max": 200000, "time": "0–3 soat",
            "info": [
                "📑 Tur: 📺 IGTV video ko'rishlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ IGTV video ochiq bo'lishi kerak",
                "🔗 IGTV havolasini yuboring",
            ]
        },
        {
            "service": "ig_v05",
            "name": "👁 Reels Ko'rishlar [ Yuqori Sifat ]",
            "rate": "0.20", "min": 500, "max": 500000, "time": "0–2 soat",
            "info": [
                "📑 Tur: 🏆 HQ Reels ko'rishlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Reels ochiq bo'lishi kerak",
                "🔗 Reels havolasini yuboring",
            ]
        },
    ],

    # ── INSTAGRAM → IZOH & BOSHQA ─────────────────────────────────────────────
    "ig_sub_other": [
        {
            "service": "ig_o01",
            "name": "💬 Izohlar [ Haqiqiy ]",
            "rate": "3.00", "min": 5, "max": 1000, "time": "1–24 soat",
            "info": [
                "📑 Tur: 💬 Mazmunli haqiqiy izohlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Izoh yozish ochiq bo'lishi kerak",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "ig_o02",
            "name": "📤 Saqlashlar [ Post Saves ]",
            "rate": "0.50", "min": 100, "max": 10000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🔖 Post saqlashlar (algoritm uchun)",
                "♻️ Tiklashlar yo'q",
                "⛔️ Post ochiq bo'lishi kerak",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "ig_o03",
            "name": "🔁 Reels Ulashishlar",
            "rate": "0.40", "min": 100, "max": 20000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🔁 Reels ulashishlar soni",
                "♻️ Tiklashlar yo'q",
                "⛔️ Reels ochiq bo'lishi kerak",
                "🔗 Reels havolasini yuboring",
            ]
        },
        {
            "service": "ig_o04",
            "name": "✅ Profil Tashrif [ Visit ]",
            "rate": "0.20", "min": 500, "max": 100000, "time": "0–3 soat",
            "info": [
                "📑 Tur: 👣 Profilga tashrif buyuruvchilar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Profil ochiq bo'lishi kerak",
                "👤 Profil @username yuboring",
            ]
        },
        {
            "service": "ig_o05",
            "name": "💌 DM Ko'rishlar",
            "rate": "0.35", "min": 100, "max": 10000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 📩 Story javoblari va DM ko'rishlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Profil ochiq bo'lishi kerak",
                "👤 Profil @username yuboring",
            ]
        },
        {
            "service": "ig_o06",
            "name": "🔔 Mention [ @tag ]",
            "rate": "1.20", "min": 50, "max": 5000, "time": "2–12 soat",
            "info": [
                "📑 Tur: 📣 Postlarda profil mention",
                "♻️ Tiklashlar yo'q",
                "⛔️ Profil ochiq bo'lishi kerak",
                "👤 Profil @username yuboring",
            ]
        },
    ],

    # ── YOUTUBE → KO'RISHLAR ─────────────────────────────────────────────────
    "yt_sub_views": [
        {
            "service": "yt_v01",
            "name": "👀 Ko'rishlar [ Yuqori Sifat HQ ]",
            "rate": "0.70", "min": 1000, "max": 1000000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🏆 HQ — YouTube siyosatiga mos",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq (public) bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "yt_v02",
            "name": "👀 Ko'rishlar [ Tezkor ]",
            "rate": "0.40", "min": 1000, "max": 500000, "time": "0–3 soat",
            "info": [
                "📑 Tur: ⚡️ Tezkor, arzon ko'rishlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "yt_v03",
            "name": "👀 Ko'rishlar [ 60% Retention ]",
            "rate": "1.20", "min": 500, "max": 100000, "time": "6–24 soat",
            "info": [
                "📑 Tur: ⏱ 60% davomiylik bilan tomosha",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "yt_v04",
            "name": "👀 Ko'rishlar [ 100% Retention ]",
            "rate": "2.50", "min": 100, "max": 50000, "time": "12–48 soat",
            "info": [
                "📑 Tur: ✅ To'liq tomosha — eng kuchli signal",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "yt_v05",
            "name": "📱 Shorts Ko'rishlar",
            "rate": "0.10", "min": 1000, "max": 2000000, "time": "0–3 soat",
            "info": [
                "📑 Tur: 📱 YouTube Shorts ko'rishlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Shorts video ochiq bo'lishi kerak",
                "🔗 Shorts havolasini yuboring",
            ]
        },
        {
            "service": "yt_v06",
            "name": "⏱ Watch Time [ 4000 Soat ]",
            "rate": "8.00", "min": 100, "max": 4000, "time": "2–7 kun",
            "info": [
                "📑 Tur: ⏱ Monetizatsiya uchun Watch Time",
                "♻️ Kafolat: yetkazilmasa qaytariladi",
                "⛔️ Video ochiq bo'lishi kerak (unlisted emas)",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "yt_v07",
            "name": "👀 Ko'rishlar [ 30% Retention ]",
            "rate": "0.85", "min": 500, "max": 200000, "time": "3–12 soat",
            "info": [
                "📑 Tur: ⏱ 30% davomiylik bilan tomosha",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
    ],

    # ── YOUTUBE → OBUNACHILAR ─────────────────────────────────────────────────
    "yt_sub_subscribers": [
        {
            "service": "yt_s01",
            "name": "🔔 Obunachilar [ Haqiqiy ]",
            "rate": "3.50", "min": 100, "max": 10000, "time": "6–48 soat",
            "info": [
                "📑 Tur: 🧑 Haqiqiy obunachilar",
                "♻️ Tushsa — 30 kun kafolat",
                "⛔️ Chiqishlar bor (tabiiy)",
                "👤 Kanal ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "yt_s02",
            "name": "🔔 Obunachilar [ Premium ]",
            "rate": "5.00", "min": 50, "max": 5000, "time": "12–72 soat",
            "info": [
                "📑 Tur: 💎 Premium, uzoq qoladigan",
                "♻️ Tushsa — kafolat bor",
                "⛔️ Chiqishlar: minimal",
                "👤 Kanal ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "yt_s03",
            "name": "🔔 Obunachilar [ Tezkor ]",
            "rate": "2.00", "min": 100, "max": 50000, "time": "1–6 soat",
            "info": [
                "📑 Tur: ⚡️ Tezkor yetkazilish",
                "♻️ Tiklashlar yo'q",
                "⛔️ Chiqishlar bor (tabiiy)",
                "👤 Kanal ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "yt_s04",
            "name": "🔔 Qo'ng'iroq [ Notification Bell ]",
            "rate": "1.00", "min": 100, "max": 5000, "time": "2–12 soat",
            "info": [
                "📑 Tur: 🔔 Qo'ng'iroq bosishlar soni",
                "♻️ Tiklashlar yo'q",
                "⛔️ Kanal ochiq bo'lishi kerak",
                "👤 Kanal havolasini yuboring",
            ]
        },
    ],

    # ── YOUTUBE → LAYKLAR ─────────────────────────────────────────────────────
    "yt_sub_likes": [
        {
            "service": "yt_l01",
            "name": "👍 Layklar [ Haqiqiy ]",
            "rate": "0.60", "min": 100, "max": 20000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 👍 Haqiqiy profillardan layklar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "yt_l02",
            "name": "👍 Layklar [ Tezkor ]",
            "rate": "0.30", "min": 100, "max": 50000, "time": "0–1 soat",
            "info": [
                "📑 Tur: ⚡️ Tezkor layklar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "yt_l03",
            "name": "❤️ Shorts Layklar",
            "rate": "0.35", "min": 100, "max": 50000, "time": "0–3 soat",
            "info": [
                "📑 Tur: ❤️ Shorts uchun maxsus layklar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Shorts video ochiq bo'lishi kerak",
                "🔗 Shorts havolasini yuboring",
            ]
        },
        {
            "service": "yt_l04",
            "name": "👎 Disliklar [ Raqobat uchun ]",
            "rate": "0.80", "min": 100, "max": 10000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 👎 Raqib kanalga dislike",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
    ],

    # ── YOUTUBE → IZOH & BOSHQA ───────────────────────────────────────────────
    "yt_sub_other": [
        {
            "service": "yt_o01",
            "name": "💬 Izohlar [ Haqiqiy ]",
            "rate": "4.00", "min": 5, "max": 500, "time": "1–24 soat",
            "info": [
                "📑 Tur: 💬 Mazmunli haqiqiy izohlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Izoh yozish yoqilgan bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "yt_o02",
            "name": "🔁 Ulashishlar",
            "rate": "0.50", "min": 100, "max": 10000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🔁 Video ulashishlar soni",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "yt_o03",
            "name": "📌 Playlist Qo'shish",
            "rate": "0.80", "min": 100, "max": 10000, "time": "2–12 soat",
            "info": [
                "📑 Tur: 📌 Playlistlarga qo'shilishlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
    ],

    # ── TIKTOK → OBUNACHILAR ──────────────────────────────────────────────────
    "tt_sub_followers": [
        {
            "service": "tt_01",
            "name": "👥 Obunachilar [ Haqiqiy ]",
            "rate": "0.90", "min": 100, "max": 50000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🧑 Haqiqiy TikTok obunachilar",
                "♻️ Tushsa — 30 kun kafolat",
                "⛔️ Chiqishlar: minimal",
                "👤 Profil ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "tt_02",
            "name": "👥 Obunachilar [ Tezkor ]",
            "rate": "0.50", "min": 100, "max": 100000, "time": "0–2 soat",
            "info": [
                "📑 Tur: ⚡️ Tezkor, katta hajm",
                "♻️ Tiklashlar yo'q",
                "⛔️ Chiqishlar bor (tabiiy)",
                "👤 Profil ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "tt_03",
            "name": "👥 Obunachilar [ Premium ]",
            "rate": "1.80", "min": 50, "max": 30000, "time": "2–12 soat",
            "info": [
                "📑 Tur: 💎 Premium, uzoq qoladigan",
                "♻️ Tushsa — kafolat bor",
                "⛔️ Chiqishlar: juda kam",
                "👤 Profil ochiq bo'lishi kerak",
            ]
        },
        {
            "service": "tt_f04",
            "name": "👥 Obunachilar [ AQSh ]",
            "rate": "2.50", "min": 100, "max": 20000, "time": "6–24 soat",
            "info": [
                "📑 Tur: 🇺🇸 AQSh foydalanuvchilari",
                "♻️ Tushsa — kafolat bor",
                "⛔️ Chiqishlar: minimal",
                "👤 Profil ochiq bo'lishi kerak",
            ]
        },
    ],

    # ── TIKTOK → LAYKLAR ─────────────────────────────────────────────────────
    "tt_sub_likes": [
        {
            "service": "tt_l01",
            "name": "❤️ Layklar [ Tezkor ]",
            "rate": "0.15", "min": 100, "max": 100000, "time": "0–1 soat",
            "info": [
                "📑 Tur: ⚡️ Eng tezkor layklar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Chiqishlar bor",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "tt_l02",
            "name": "❤️ Layklar [ Haqiqiy ]",
            "rate": "0.35", "min": 100, "max": 50000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🧑 Haqiqiy profillardan layklar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Chiqishlar: minimal",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "tt_l03",
            "name": "❤️ AutoLike [ 30 kun ]",
            "rate": "1.20", "min": 100, "max": 5000, "time": "Doimiy",
            "info": [
                "📑 Tur: 🤖 Avtomatik layk — 30 kunlik",
                "♻️ 30 kun davomida ishlaydi",
                "⛔️ Profil ochiq bo'lishi kerak",
                "👤 Profil @username yuboring",
            ]
        },
        {
            "service": "tt_l04",
            "name": "❤️ Layklar [ Arab ]",
            "rate": "0.45", "min": 100, "max": 30000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🇸🇦 Arab profillardan layklar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
    ],

    # ── TIKTOK → KO'RISHLAR ──────────────────────────────────────────────────
    "tt_sub_views": [
        {
            "service": "tt_v01",
            "name": "👀 Ko'rishlar [ Tezkor ]",
            "rate": "0.04", "min": 1000, "max": 5000000, "time": "0–30 daqiqa",
            "info": [
                "📑 Tur: ⚡️ Eng tezkor ko'rishlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "tt_v02",
            "name": "👀 Ko'rishlar [ Yuqori Sifat ]",
            "rate": "0.12", "min": 1000, "max": 1000000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🏆 Sifatli ko'rishlar (algoritm uchun)",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "tt_v03",
            "name": "▶️ Profil Ko'rishlar",
            "rate": "0.20", "min": 500, "max": 100000, "time": "0–3 soat",
            "info": [
                "📑 Tur: 👣 TikTok profil ko'rishlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Profil ochiq bo'lishi kerak",
                "👤 Profil @username yuboring",
            ]
        },
        {
            "service": "tt_v04",
            "name": "🔴 Live Ko'ruvchilar",
            "rate": "1.20", "min": 10, "max": 500, "time": "0–10 daqiqa",
            "info": [
                "📑 Tur: 🔴 Live efir ko'ruvchilari",
                "♻️ Live tugagach ketadi (tabiiy)",
                "⛔️ Live ayni paytda ishlayotgan bo'lsin",
                "🔗 Profil havolasini yuboring",
            ]
        },
        {
            "service": "tt_v05",
            "name": "👀 Ko'rishlar [ 50% Retention ]",
            "rate": "0.25", "min": 1000, "max": 500000, "time": "2–8 soat",
            "info": [
                "📑 Tur: ⏱ 50% davomiylik bilan tomosha",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
    ],

    # ── TIKTOK → IZOH & BOSHQA ───────────────────────────────────────────────
    "tt_sub_other": [
        {
            "service": "tt_o01",
            "name": "💬 Izohlar [ Haqiqiy ]",
            "rate": "2.50", "min": 5, "max": 500, "time": "1–12 soat",
            "info": [
                "📑 Tur: 💬 Mazmunli haqiqiy izohlar",
                "♻️ Tiklashlar yo'q",
                "⛔️ Izoh yozish ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "tt_o02",
            "name": "🔁 Ulashishlar",
            "rate": "0.35", "min": 100, "max": 20000, "time": "1–3 soat",
            "info": [
                "📑 Tur: 🔁 Video ulashishlar soni",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "tt_o03",
            "name": "📊 Saqlashlar [ Saves ]",
            "rate": "0.40", "min": 100, "max": 10000, "time": "1–6 soat",
            "info": [
                "📑 Tur: 🔖 Video saqlashlar (viral uchun muhim)",
                "♻️ Tiklashlar yo'q",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "tt_o04",
            "name": "🎁 TikTok Coins",
            "rate": "1.00", "min": 100, "max": 10000, "time": "0–6 soat",
            "info": [
                "📑 Tur: 🪙 TikTok Coins — gift berish uchun",
                "♻️ Kafolat: yetkazilmasa qaytariladi",
                "⛔️ Akkaunt aktiv bo'lishi kerak",
                "👤 Profil @username yuboring",
            ]
        },
    ],

    # ── TG PREMIUM → PREMIUM OBUNA ────────────────────────────────────────────
    "tgp_sub_premium": [
        {
            "service": "tgp_01",
            "name": "💠 Telegram Premium [ 1 Oy ]",
            "rate": "4.00", "min": 1, "max": 100, "time": "0–6 soat",
            "info": [
                "📑 Tur: 💠 Premium obuna — 1 oylik",
                "♻️ Kafolat: aktivatsiya kafolatlanadi",
                "⛔️ Akkaunt Telegram da ro'yxatdan o'tgan bo'lsin",
                "👤 @username yuboring",
            ]
        },
        {
            "service": "tgp_02",
            "name": "💠 Telegram Premium [ 3 Oy ]",
            "rate": "10.00", "min": 1, "max": 100, "time": "0–6 soat",
            "info": [
                "📑 Tur: 💠 Premium obuna — 3 oylik",
                "♻️ Kafolat: aktivatsiya kafolatlanadi",
                "⛔️ Akkaunt Telegram da aktiv bo'lsin",
                "👤 @username yuboring",
            ]
        },
        {
            "service": "tgp_03",
            "name": "💠 Telegram Premium [ 6 Oy ]",
            "rate": "18.00", "min": 1, "max": 50, "time": "0–12 soat",
            "info": [
                "📑 Tur: 💠 Premium obuna — 6 oylik",
                "♻️ Kafolat: aktivatsiya kafolatlanadi",
                "⛔️ Akkaunt Telegram da aktiv bo'lsin",
                "👤 @username yuboring",
            ]
        },
        {
            "service": "tgp_04",
            "name": "💠 Telegram Premium [ 12 Oy ]",
            "rate": "32.00", "min": 1, "max": 20, "time": "0–24 soat",
            "info": [
                "📑 Tur: 💠 Premium obuna — 1 yillik",
                "♻️ Kafolat: aktivatsiya kafolatlanadi",
                "⛔️ Akkaunt Telegram da aktiv bo'lsin",
                "👤 @username yuboring",
            ]
        },
        {
            "service": "tgp_05",
            "name": "🎁 Premium Sovg'a [ Do'stingizga ]",
            "rate": "4.50", "min": 1, "max": 100, "time": "0–6 soat",
            "info": [
                "📑 Tur: 🎁 Do'stingizga Premium sovg'a",
                "♻️ Kafolat: yetkazilmasa qaytariladi",
                "⛔️ Qabul qiluvchi Telegram da aktiv bo'lsin",
                "👤 @username yuboring",
            ]
        },
        {
            "service": "tgp_11",
            "name": "🏅 Fragment Username [ Sotib olish ]",
            "rate": "20.00", "min": 1, "max": 10, "time": "1–24 soat",
            "info": [
                "📑 Tur: 🏅 Fragment orqali premium username",
                "♻️ Kafolat: muvaffaqiyatli bo'lmasa qaytariladi",
                "⛔️ Username bo'sh va sotuvda bo'lishi kerak",
                "👤 @username yuboring",
            ]
        },
    ],

    # ── TG PREMIUM → STARS ────────────────────────────────────────────────────
    "tgp_sub_stars": [
        {
            "service": "tgp_06",
            "name": "⭐ Telegram Stars [ 50 ta ]",
            "rate": "1.00", "min": 1, "max": 500, "time": "0–6 soat",
            "info": [
                "📑 Tur: ⭐ 50 ta Telegram Stars",
                "♻️ Kafolat: yetkazilmasa qaytariladi",
                "⛔️ Stars qabul qiluvchi bot/kanal kerak",
                "🔗 Bot yoki kanal linkini yuboring",
            ]
        },
        {
            "service": "tgp_07",
            "name": "⭐ Telegram Stars [ 100 ta ]",
            "rate": "1.80", "min": 1, "max": 500, "time": "0–6 soat",
            "info": [
                "📑 Tur: ⭐ 100 ta Telegram Stars",
                "♻️ Kafolat: yetkazilmasa qaytariladi",
                "⛔️ Stars qabul qiluvchi bot/kanal kerak",
                "🔗 Bot yoki kanal linkini yuboring",
            ]
        },
        {
            "service": "tgp_08",
            "name": "⭐ Telegram Stars [ 500 ta ]",
            "rate": "8.00", "min": 1, "max": 200, "time": "0–6 soat",
            "info": [
                "📑 Tur: ⭐ 500 ta Telegram Stars (katta to'plam)",
                "♻️ Kafolat: yetkazilmasa qaytariladi",
                "⛔️ Stars qabul qiluvchi bot/kanal kerak",
                "🔗 Bot yoki kanal linkini yuboring",
            ]
        },
        {
            "service": "tgp_09",
            "name": "⭐ Telegram Stars [ 1000 ta ]",
            "rate": "14.00", "min": 1, "max": 100, "time": "0–12 soat",
            "info": [
                "📑 Tur: ⭐ 1000 ta Telegram Stars (eng katta)",
                "♻️ Kafolat: yetkazilmasa qaytariladi",
                "⛔️ Stars qabul qiluvchi bot/kanal kerak",
                "🔗 Bot yoki kanal linkini yuboring",
            ]
        },
        {
            "service": "tgp_10",
            "name": "🌟 Stars Sovg'a [ Xabar orqali ]",
            "rate": "1.50", "min": 50, "max": 10000, "time": "0–6 soat",
            "info": [
                "📑 Tur: 🌟 Xabarga Stars yuborish",
                "♻️ Kafolat: yetkazilmasa qaytariladi",
                "⛔️ Xabar ochiq bo'lishi kerak",
                "🔗 Post/xabar havolasini yuboring",
            ]
        },
        {
            "service": "tgp_12",
            "name": "⭐ Telegram Stars [ 2500 ta ]",
            "rate": "32.00", "min": 1, "max": 50, "time": "0–24 soat",
            "info": [
                "📑 Tur: ⭐ 2500 ta Telegram Stars (mega to'plam)",
                "♻️ Kafolat: yetkazilmasa qaytariladi",
                "⛔️ Stars qabul qiluvchi bot/kanal kerak",
                "🔗 Bot yoki kanal linkini yuboring",
            ]
        },
    ],

    # ── TEKIN XIZMATLAR ───────────────────────────────────────────────────────
    "free_sub_all": [
        {
            "service": "free_01",
            "name": "🆓 Telegram 50 Ko'rish [ Tekin ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "0–1 soat",
            "info": [
                "📑 Tur: 🎁 Birinchi buyurtma — BEPUL",
                "♻️ Har foydalanuvchi 1 martadan",
                "⛔️ Kanal ochiq bo'lishi kerak",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "free_02",
            "name": "🆓 Instagram 10 Layk [ Tekin ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "0–1 soat",
            "info": [
                "📑 Tur: 🎁 Sinab ko'rish — BEPUL",
                "♻️ Har foydalanuvchi 1 martadan",
                "⛔️ Post ochiq bo'lishi kerak",
                "🔗 Post havolasini yuboring",
            ]
        },
        {
            "service": "free_03",
            "name": "🆓 YouTube 100 Ko'rish [ Tekin ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "0–2 soat",
            "info": [
                "📑 Tur: 🎁 Sinab ko'rish — BEPUL",
                "♻️ Har foydalanuvchi 1 martadan",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "free_04",
            "name": "🆓 TikTok 200 Ko'rish [ Tekin ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "0–1 soat",
            "info": [
                "📑 Tur: 🎁 Sinab ko'rish — BEPUL",
                "♻️ Har foydalanuvchi 1 martadan",
                "⛔️ Video ochiq bo'lishi kerak",
                "🔗 Video havolasini yuboring",
            ]
        },
        {
            "service": "free_05",
            "name": "🎁 Do'st Taklif [ Bonus 5 000 so'm ]",
            "rate": "0.00", "min": 1, "max": 999, "time": "Darhol",
            "info": [
                "📑 Tur: 🤝 Do'st taklif qilish bonusi",
                "♻️ Ikkalangiz ham 5 000 so'm olasiz",
                "⛔️ Do'stingiz yangi foydalanuvchi bo'lishi kerak",
                "👤 Referal havolangizni ulashing",
            ]
        },
        {
            "service": "free_06",
            "name": "🆓 Telegram 5 A'zo [ Tekin ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "0–2 soat",
            "info": [
                "📑 Tur: 🎁 Yangi foydalanuvchilar uchun",
                "♻️ Har foydalanuvchi 1 martadan",
                "⛔️ Kanal ochiq bo'lishi kerak",
                "🔗 Kanal havolasini yuboring",
            ]
        },
        {
            "service": "free_07",
            "name": "🎁 Kunlik Bonus [ 500 so'm ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "Darhol",
            "info": [
                "📑 Tur: 🎰 Har kunlik bepul bonus",
                "♻️ Har 24 soatda 1 marta",
                "⛔️ /bonus buyrug'ini yuboring",
                "👤 Hech narsa yuborish shart emas",
            ]
        },
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# 🔧 YORDAMCHI FUNKSIYALAR
# ══════════════════════════════════════════════════════════════════════════════

def find_service(svc_id: str) -> dict | None:
    for services in ALL_SERVICES.values():
        for s in services:
            if s["service"] == svc_id:
                return s
    return None


def find_sub_by_svc(svc_id: str) -> str | None:
    for sub_id, services in ALL_SERVICES.items():
        for s in services:
            if s["service"] == svc_id:
                return sub_id
    return None


def find_cat_by_sub(sub_id: str) -> str:
    for cat_id, subs in SUB_CATEGORIES.items():
        for s in subs:
            if s["id"] == sub_id:
                return cat_id
    return "telegram"


def search_services(query: str) -> list:
    q = query.lower().strip()
    results, seen = [], set()
    for services in ALL_SERVICES.values():
        for svc in services:
            if q in svc["name"].lower() or q in svc["service"].lower():
                if svc["service"] not in seen:
                    results.append(svc)
                    seen.add(svc["service"])
    return results


def price_label(rate_val: float) -> str:
    if rate_val == 0:
        return "🆓 BEPUL"
    return f"{rate_val * USD_TO_SOM / 1000:,.2f} so'm/1000"


def calc_total(rate_val: float, qty: int) -> float:
    if rate_val == 0:
        return 0.0
    return (rate_val * USD_TO_SOM / 1000) * qty


def _to_dict(row) -> dict | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        return None


def get_sub_service_count(cat_id: str) -> int:
    total = 0
    for sub in SUB_CATEGORIES.get(cat_id, []):
        total += len(ALL_SERVICES.get(sub["id"], []))
    return total


# ══════════════════════════════════════════════════════════════════════════════
# ⌨️ KLAVIATURALAR
# ══════════════════════════════════════════════════════════════════════════════

def kb_categories():
    builder = InlineKeyboardBuilder()
    for i in range(0, len(CATEGORIES) - 1, 2):
        c1, c2 = CATEGORIES[i], CATEGORIES[i + 1]
        count1  = get_sub_service_count(c1["id"])
        count2  = get_sub_service_count(c2["id"])
        builder.row(
            InlineKeyboardButton(
                text=f"{c1['name']} ({count1})",
                callback_data=f"cat|{c1['id']}"
            ),
            InlineKeyboardButton(
                text=f"{c2['name']} ({count2})",
                callback_data=f"cat|{c2['id']}"
            ),
        )
    if len(CATEGORIES) % 2 != 0:
        last  = CATEGORIES[-1]
        count = get_sub_service_count(last["id"])
        builder.row(InlineKeyboardButton(
            text=f"{last['name']} ({count})",
            callback_data=f"cat|{last['id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔍 Xizmat Qidirish",          callback_data="open_search"))
    builder.row(InlineKeyboardButton(text="📋 Barcha Xizmatlar Ro'yxati", callback_data="all_services_list"))
    return builder.as_markup()


def kb_subcategories(cat_id: str):
    subs    = SUB_CATEGORIES.get(cat_id, [])
    cat     = next((c for c in CATEGORIES if c["id"] == cat_id), None)
    builder = InlineKeyboardBuilder()
    for sub in subs:
        count = len(ALL_SERVICES.get(sub["id"], []))
        builder.row(InlineKeyboardButton(
            text=f"{sub['name']} ({count} ta)",
            callback_data=f"sub|{sub['id']}",
        ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_cats"))
    return builder.as_markup()


def kb_services(sub_id: str, page: int = 0):
    services    = ALL_SERVICES.get(sub_id, [])
    per_page    = 8
    start       = page * per_page
    end         = start + per_page
    total_pages = max(1, (len(services) + per_page - 1) // per_page)
    cat_id      = find_cat_by_sub(sub_id)

    builder = InlineKeyboardBuilder()
    for svc in services[start:end]:
        builder.row(InlineKeyboardButton(
            text=f"{svc['name']} — {price_label(float(svc['rate']))}",
            callback_data=f"svc|{svc['service']}",
        ))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀️ Oldingi", callback_data=f"subpage|{sub_id}|{page - 1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"📄 {page + 1}/{total_pages}", callback_data="noop"
    ))
    if end < len(services):
        nav.append(InlineKeyboardButton(
            text="Keyingi ▶️", callback_data=f"subpage|{sub_id}|{page + 1}"
        ))
    builder.row(*nav)
    builder.row(InlineKeyboardButton(
        text="🔙 Orqaga", callback_data=f"cat|{cat_id}"
    ))
    return builder.as_markup()


def kb_search_results(results: list):
    builder = InlineKeyboardBuilder()
    for svc in results[:10]:
        builder.row(InlineKeyboardButton(
            text=f"{svc['name']} — {price_label(float(svc['rate']))}",
            callback_data=f"svc|{svc['service']}",
        ))
    builder.row(InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="back_to_cats"))
    return builder.as_markup()


def kb_cancel_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order"))
    return builder.as_markup()


def kb_confirm():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash",   callback_data="confirm_order"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order"),
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# 🎨 XIZMAT KARTOCHKASI
# ══════════════════════════════════════════════════════════════════════════════

def build_service_card(svc: dict) -> str:
    rate_val = float(svc["rate"])
    is_free  = rate_val == 0
    rate_som = rate_val * USD_TO_SOM / 1000 if not is_free else 0

    price_line = (
        "💵 Narx (x1000): <b>BEPUL 🆓</b>"
        if is_free
        else f"💵 Narx (x1000): <b>{rate_som * 1000:,.2f} so'm</b>"
    )

    t = svc["time"]
    if any(x in t for x in ["daqiqa", "Darhol", "0–30", "0–1 soat"]):
        start_line = "📑 : ⚡️ Boshlanishi: Tez"
    elif "kun" in t:
        start_line = f"📑 : 📅 Bajarilish: {t}"
    elif "Doimiy" in t:
        start_line = "📑 : 🔄 Doimiy (avtomatik)"
    else:
        start_line = f"📑 : 🕐 Boshlanishi: {t} ichida"

    info_lines = "\n".join(svc.get("info", []))

    return (
        f"<b>{svc['name']}</b>\n"
        f"{price_line}\n"
        f"{start_line}\n"
        f"{info_lines}\n"
        f"☝️ Ta'rif bilan tanishib chiqib ✅ <b>Davom etish</b> tugmasini bosing!"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 🎯 HANDLERLAR
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "🛒 Xizmatlar")
async def services_menu(message: Message):
    total = sum(get_sub_service_count(c["id"]) for c in CATEGORIES)
    await message.answer(
        "🛍 <b>SMM Xizmatlar</b>\n\n"
        "✅ Tezkor • Sifatli • Arzon\n"
        f"📦 Jami: <b>{total} ta xizmat</b>\n"
        "🎁 Tekin xizmatlar ham mavjud!\n\n"
        "📌 Kerakli platformani tanlang 👇",
        parse_mode="HTML",
        reply_markup=kb_categories(),
    )


@router.callback_query(F.data == "back_to_cats")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    total = sum(get_sub_service_count(c["id"]) for c in CATEGORIES)
    await callback.message.edit_text(
        "🛍 <b>SMM Xizmatlar</b>\n\n"
        "✅ Tezkor • Sifatli • Arzon\n"
        f"📦 Jami: <b>{total} ta xizmat</b>\n"
        "🎁 Tekin xizmatlar ham mavjud!\n\n"
        "📌 Kerakli platformani tanlang 👇",
        parse_mode="HTML",
        reply_markup=kb_categories(),
    )
    await callback.answer()


# Kategoriya → Sub-kategoriyalar
@router.callback_query(F.data.startswith("cat|"))
async def show_category(callback: CallbackQuery):
    cat_id = callback.data.split("|")[1]
    cat    = next((c for c in CATEGORIES if c["id"] == cat_id), None)
    if not cat:
        await callback.answer("Kategoriya topilmadi!", show_alert=True)
        return

    subs   = SUB_CATEGORIES.get(cat_id, [])
    total  = get_sub_service_count(cat_id)
    hint   = "\n💡 Hech qanday to'lovsiz!" if cat_id == "free" else ""

    sub_lines = "\n".join(
        f"  {s['name']} — {len(ALL_SERVICES.get(s['id'], []))} ta"
        for s in subs
    )

    await callback.message.edit_text(
        f"{cat['name']} <b>xizmatlari</b>{hint}\n\n"
        f"📦 Jami: <b>{total} ta xizmat</b>\n\n"
        f"{sub_lines}\n\n"
        f"👇 Bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=kb_subcategories(cat_id),
    )
    await callback.answer()


# Sub-kategoriya → Xizmatlar ro'yxati
@router.callback_query(F.data.startswith("sub|"))
async def show_subcategory(callback: CallbackQuery):
    sub_id = callback.data.split("|")[1]
    sub    = None
    for subs in SUB_CATEGORIES.values():
        sub = next((s for s in subs if s["id"] == sub_id), None)
        if sub:
            break

    services = ALL_SERVICES.get(sub_id, [])
    label    = sub["name"] if sub else sub_id

    await callback.message.edit_text(
        f"{label} <b>xizmatlari</b>\n\n"
        f"📦 Jami: <b>{len(services)} ta xizmat</b>\n"
        f"👇 Kerakli xizmatni tanlang:",
        parse_mode="HTML",
        reply_markup=kb_services(sub_id, 0),
    )
    await callback.answer()


# Sahifalash
@router.callback_query(F.data.startswith("subpage|"))
async def paginate_services(callback: CallbackQuery):
    parts    = callback.data.split("|")
    sub_id   = parts[1]
    page     = int(parts[2])
    sub      = None
    for subs in SUB_CATEGORIES.values():
        sub = next((s for s in subs if s["id"] == sub_id), None)
        if sub:
            break
    services = ALL_SERVICES.get(sub_id, [])
    label    = sub["name"] if sub else sub_id
    await callback.message.edit_text(
        f"{label} <b>xizmatlari</b>\n\n"
        f"📦 Jami: <b>{len(services)} ta xizmat</b>\n"
        f"👇 Kerakli xizmatni tanlang:",
        parse_mode="HTML",
        reply_markup=kb_services(sub_id, page),
    )
    await callback.answer()


@router.callback_query(F.data == "all_services_list")
async def all_services_list(callback: CallbackQuery):
    text  = "📋 <b>Barcha xizmatlar ro'yxati:</b>\n\n"
    total = 0
    for cat in CATEGORIES:
        count = get_sub_service_count(cat["id"])
        subs  = SUB_CATEGORIES.get(cat["id"], [])
        text += f"{cat['name']} — <b>{count} ta</b>\n"
        for sub in subs:
            sc = len(ALL_SERVICES.get(sub["id"], []))
            text += f"  {sub['name']}: {sc} ta\n"
        total += count
        text  += "\n"
    text += f"📦 Jami: <b>{total} ta xizmat</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb_categories())
    await callback.answer()


# ── QIDIRUV ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "open_search")
async def open_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.searching_service)
    await callback.message.edit_text(
        "🔍 <b>Xizmat Qidirish</b>\n\n"
        "Xizmat nomini yozing:\n"
        "<i>Masalan: a'zolar, layk, ko'rish, premium, stars...</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_cats")
        ).as_markup(),
    )
    await callback.answer()


@router.message(OrderStates.searching_service)
async def process_search(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if query == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_main_menu())
        return
    if len(query) < 2:
        await message.answer("❌ Kamida 2 ta harf kiriting!")
        return

    results = search_services(query)
    await state.clear()

    if not results:
        await message.answer(
            f"🔍 <b>«{query}»</b> bo'yicha hech narsa topilmadi.\n💡 Boshqa so'z bilan qidiring.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="back_to_cats")
            ).as_markup(),
        )
        return

    await message.answer(
        f"🔍 <b>«{query}»</b> — <b>{len(results)} ta</b> xizmat topildi:\n\n👇 Tanlang:",
        parse_mode="HTML",
        reply_markup=kb_search_results(results),
    )


# ── XIZMAT KARTOCHKASI ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("svc|"))
async def show_service_detail(callback: CallbackQuery, state: FSMContext):
    svc_id = callback.data.split("|")[1]
    svc    = find_service(svc_id)
    if not svc:
        await callback.answer("Xizmat topilmadi!", show_alert=True)
        return

    sub_id   = find_sub_by_svc(svc_id)
    rate_val = float(svc["rate"])

    await state.update_data(
        service_id=svc_id,
        service_name=svc["name"],
        rate=rate_val,
        min_qty=svc["min"],
        max_qty=svc["max"],
        sub_id=sub_id,
        time=svc["time"],
    )

    btn_text = "🎁 Bepul olish" if rate_val == 0 else "✅ Davom etish"
    builder  = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"order_start|{svc_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"sub|{sub_id}"))

    await callback.message.edit_text(
        build_service_card(svc),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


# ── BUYURTMA OQIMI ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("order_start|"))
async def order_start(callback: CallbackQuery, state: FSMContext):
    svc_id   = callback.data.split("|")[1]
    svc      = find_service(svc_id)
    if not svc:
        await callback.answer("Xizmat topilmadi!", show_alert=True)
        return

    rate_val = float(svc["rate"])
    is_free  = rate_val == 0

    await state.update_data(
        service_id=svc_id,
        service_name=svc["name"],
        rate=rate_val,
        min_qty=svc["min"],
        max_qty=svc["max"],
        time=svc["time"],
    )

    if is_free:
        await state.update_data(quantity=svc["min"])
        await state.set_state(OrderStates.waiting_link)
        await callback.message.edit_text(
            f"✅ <b>{svc['name']}</b> tanlandi!\n\n"
            f"🔗 Havola (link) yuboring:\n"
            f"<i>Namuna: https://t.me/username</i>",
            parse_mode="HTML",
            reply_markup=kb_cancel_inline(),
        )
    else:
        await state.set_state(OrderStates.waiting_quantity)
        await callback.message.edit_text(
            f"<b>{svc['name']}</b>\n\n"
            f"🔽 Minimal: <b>{svc['min']:,} ta</b>\n"
            f"🔼 Maksimal: <b>{svc['max']:,} ta</b>\n\n"
            f"✏️ Kerakli miqdorni kiriting:",
            parse_mode="HTML",
            reply_markup=kb_cancel_inline(),
        )
    await callback.answer()


@router.message(OrderStates.waiting_quantity)
async def process_quantity(message: Message, state: FSMContext):
    if (message.text or "").strip() == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_main_menu())
        return
    try:
        qty = int((message.text or "").replace(" ", "").replace(",", ""))
    except ValueError:
        await message.answer("❌ Faqat butun son kiriting!")
        return

    data = await state.get_data()
    if qty < data.get("min_qty", 1):
        await message.answer(f"❌ Minimal: <b>{data['min_qty']:,} ta</b>", parse_mode="HTML")
        return
    if qty > data.get("max_qty", 999999):
        await message.answer(f"❌ Maksimal: <b>{data['max_qty']:,} ta</b>", parse_mode="HTML")
        return

    await state.update_data(quantity=qty)
    await state.set_state(OrderStates.waiting_link)
    await message.answer(
        f"✅ <b>{qty:,} ta</b> qabul qilindi!\n\n"
        f"🔗 Post havolasini yuboring:\n"
        f"<i>❕ Namuna: https://instagram.com/p/xyz/</i>",
        parse_mode="HTML",
        reply_markup=kb_cancel_inline(),
    )


@router.message(OrderStates.waiting_link)
async def process_link(message: Message, state: FSMContext):
    if (message.text or "").strip() == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_main_menu())
        return

    link = (message.text or "").strip()
    valid = any(link.startswith(p) for p in ("http://", "https://", "@", "t.me/"))
    if not valid:
        await message.answer(
            "❌ <b>Noto'g'ri havola!</b>\n\n"
            "• <code>https://t.me/username</code>\n"
            "• <code>@username</code>\n"
            "• <code>t.me/username</code>",
            parse_mode="HTML",
        )
        return

    data     = await state.get_data()
    qty      = data.get("quantity") or data.get("min_qty", 1)
    rate_val = float(data.get("rate", 0))
    total    = calc_total(rate_val, qty)

    await state.update_data(link=link, total=total)

    user    = _to_dict(await get_user(message.from_user.id))
    balance = float((user.get("balance") if user else 0) or 0)

    price_line   = "💰 Narx: <b>BEPUL 🆓</b>" if rate_val == 0 else f"💰 Narx: <b>{total:,.2f} so'm</b>"
    balance_line = f"💳 Balans: <b>{balance:,.2f} so'm</b>"

    await state.set_state(OrderStates.confirming_order)
    await message.answer(
        f"📋 <b>Buyurtma ma'lumotlari</b>\n\n"
        f"🛍 Xizmat: <b>{data.get('service_name', '')}</b>\n"
        f"🔗 Havola: <code>{link}</code>\n"
        f"📊 Miqdor: <b>{qty:,} ta</b>\n"
        f"{price_line}\n"
        f"{balance_line}\n\n"
        f"Tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=kb_confirm(),
    )


@router.callback_query(F.data == "cancel_order")
async def cancel_order_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ Buyurtma bekor qilindi.", reply_markup=None)
    except Exception:
        await callback.message.answer("❌ Buyurtma bekor qilindi.", reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    data    = await state.get_data()
    user_id = callback.from_user.id
    user    = _to_dict(await get_user(user_id))

    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return

    total   = float(data.get("total", 0.0))
    is_free = total == 0.0
    balance = float(user.get("balance") or 0)

    if not is_free and balance < total:
        shortage = total - balance
        await callback.message.edit_text(
            f"❌ <b>Balans yetarli emas!</b>\n\n"
            f"💳 Sizning balans: <b>{balance:,.2f} so'm</b>\n"
            f"💰 Kerakli summa: <b>{total:,.2f} so'm</b>\n"
            f"➖ Yetishmaydi: <b>{shortage:,.2f} so'm</b>\n\n"
            f"💳 <b>Hisob To'ldirish</b> bo'limiga o'ting!",
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    if not is_free:
        await update_user_balance(user_id, total, add=False)
        await update_total_spent(user_id, total)

    quantity = data.get("quantity") or data.get("min_qty", 1)
    order_id = await create_order(
        user_id=user_id,
        service_id=data["service_id"],
        service_name=data["service_name"],
        link=data["link"],
        quantity=quantity,
        charge=total,
    )
    await log_transaction(user_id, total, "order", f"Buyurtma #{order_id}: {data['service_name']}")

    smm_order_id = await _place_smm_order(data["service_id"], data["link"], quantity)
    await state.clear()

    ext_id = smm_order_id or order_id
    await callback.message.edit_text(
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"🆔 Buyurtma ID: <b>{ext_id}</b>\n"
        f"Yuqoridagi ID orqali buyurtmangiz holatini tekshirishingiz mumkin!",
        parse_mode="HTML",
    )
    await callback.answer("✅ Buyurtma qabul qilindi!")


# ══════════════════════════════════════════════════════════════════════════════
# 🌐 SMM API
# ══════════════════════════════════════════════════════════════════════════════

async def _place_smm_order(service_id: str, link: str, quantity: int) -> int | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                settings.SMM_API_URL,
                data={
                    "key":      settings.SMM_API_KEY,
                    "action":   "add",
                    "service":  service_id,
                    "link":     link,
                    "quantity": quantity,
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                result = await resp.json()
                if "error" in result:
                    logger.error(f"SMM API xato: {result['error']}")
                    return None
                return result.get("order")
    except Exception as e:import logging
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from config import settings
from database.db_queries import (
    get_user, update_user_balance, update_total_spent,
    create_order, log_transaction
)
from keyboards.reply_kb import get_main_menu

logger = logging.getLogger(__name__)
router = Router()

USD_TO_SOM = 12700


# ══════════════════════════════════════════════════════════════════════════════
# 📌 STATES
# ══════════════════════════════════════════════════════════════════════════════

class OrderStates(StatesGroup):
    searching_service = State()
    waiting_quantity  = State()
    waiting_link      = State()
    confirming_order  = State()


# ══════════════════════════════════════════════════════════════════════════════
# 📦 KATEGORIYALAR
# ══════════════════════════════════════════════════════════════════════════════

CATEGORIES = [
    {"id": "telegram",   "name": "🔵 Telegram"},
    {"id": "instagram",  "name": "🟣 Instagram"},
    {"id": "youtube",    "name": "🔴 YouTube"},
    {"id": "tiktok",     "name": "⚫ TikTok"},
    {"id": "tg_premium", "name": "💠 TG Premium & Stars"},
    {"id": "free",       "name": "🎁 Tekin Xizmatlar"},
]

SUB_CATEGORIES = {
    "telegram": [
        {"id": "tg_sub_members",   "name": "👥 A'zolar"},
        {"id": "tg_sub_views",     "name": "👀 Ko'rishlar"},
        {"id": "tg_sub_reactions", "name": "❤️ Reaktsiyalar"},
        {"id": "tg_sub_comments",  "name": "💬 Izohlar & Boshqa"},
    ],
    "instagram": [
        {"id": "ig_sub_followers", "name": "👥 Obunachilar"},
        {"id": "ig_sub_likes",     "name": "❤️ Layklar"},
        {"id": "ig_sub_views",     "name": "👁 Ko'rishlar"},
        {"id": "ig_sub_other",     "name": "💬 Izoh & Boshqa"},
    ],
    "youtube": [
        {"id": "yt_sub_views",       "name": "👀 Ko'rishlar"},
        {"id": "yt_sub_subscribers", "name": "🔔 Obunachilar"},
        {"id": "yt_sub_likes",       "name": "👍 Layklar"},
        {"id": "yt_sub_other",       "name": "💬 Izoh & Boshqa"},
    ],
    "tiktok": [
        {"id": "tt_sub_followers", "name": "👥 Obunachilar"},
        {"id": "tt_sub_likes",     "name": "❤️ Layklar"},
        {"id": "tt_sub_views",     "name": "👀 Ko'rishlar"},
        {"id": "tt_sub_other",     "name": "💬 Izoh & Boshqa"},
    ],
    "tg_premium": [
        {"id": "tgp_sub_premium", "name": "💠 Premium Obuna"},
        {"id": "tgp_sub_stars",   "name": "⭐ Stars & Sovg'a"},
    ],
    "free": [
        {"id": "free_sub_all", "name": "🎁 Barcha Tekin Xizmatlar"},
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# 🗂 XIZMATLAR
# info maydoni — string (har bir qator \n bilan ajratilgan)
# ══════════════════════════════════════════════════════════════════════════════

ALL_SERVICES = {

    # ── TELEGRAM → A'ZOLAR ───────────────────────────────────────────────────
    "tg_sub_members": [
        {
            "service": "tg_01",
            "name": "👥 A'zolar [ Real va Faol ] ⚡️",
            "rate": "0.80", "min": 100, "max": 50000, "time": "0–2 soat",
            "info": "♻️ Kafolat: 30 kun\n⛔️ Chiqishlar: minimal\n👤 Kanal/guruh ochiq bo'lishi kerak",
        },
        {
            "service": "tg_02",
            "name": "👥 A'zolar [ Premium Sifat ] 💎",
            "rate": "1.20", "min": 50, "max": 20000, "time": "1–6 soat",
            "info": "♻️ Kafolat: bor, tushsa to'ldiriladi\n⛔️ Chiqishlar: juda kam\n👤 Kanal/guruh ochiq bo'lishi kerak",
        },
        {
            "service": "tg_03",
            "name": "👥 A'zolar [ Arzon va Tezkor ] 💨",
            "rate": "0.40", "min": 200, "max": 100000, "time": "0–1 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor (tabiiy)\n👤 Kanal/guruh ochiq bo'lishi kerak",
        },
        {
            "service": "tg_04",
            "name": "👥 A'zolar [ Bot Emas, Real ] 🧑",
            "rate": "1.80", "min": 100, "max": 30000, "time": "2–8 soat",
            "info": "♻️ Kafolat: 30 kun\n⛔️ Chiqishlar: kam\n👤 Kanal/guruh ochiq bo'lishi kerak",
        },
        {
            "service": "tg_05",
            "name": "🇺🇿 A'zolar [ O'zbek, Real ]",
            "rate": "3.00", "min": 50, "max": 5000, "time": "2–12 soat",
            "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Kanal ochiq bo'lishi kerak",
        },
        {
            "service": "tg_06",
            "name": "🇺🇿 A'zolar [ O'zbek Guruh ]",
            "rate": "3.50", "min": 50, "max": 5000, "time": "2–24 soat",
            "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Guruh public bo'lishi kerak",
        },
        {
            "service": "tg_07",
            "name": "👥 A'zolar [ Xorijiy, Global ] 🌍",
            "rate": "0.30", "min": 100, "max": 200000, "time": "0–2 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor (tabiiy)\n👤 Kanal ochiq bo'lishi kerak",
        },
        {
            "service": "tg_08",
            "name": "👥 A'zolar [ Kanal — Sekin ] 🐢",
            "rate": "0.60", "min": 100, "max": 50000, "time": "6–24 soat",
            "info": "♻️ Kafolat: 15 kun\n⛔️ Chiqishlar: juda kam\n👤 Kanal ochiq bo'lishi kerak",
        },
    ],

    # ── TELEGRAM → KO'RISHLAR ─────────────────────────────────────────────────
    "tg_sub_views": [
        {
            "service": "tg_v01",
            "name": "👀 Ko'rishlar [ Tezkor ] ⚡️",
            "rate": "0.08", "min": 500, "max": 1000000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_v02",
            "name": "👀 Ko'rishlar [ Oxirgi 5 Post ] 📋",
            "rate": "0.12", "min": 500, "max": 500000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal\n🔗 Kanal linkini yuboring",
        },
        {
            "service": "tg_v03",
            "name": "👀 Ko'rishlar [ Oxirgi 10 Post ] 📋",
            "rate": "0.15", "min": 500, "max": 500000, "time": "0–1 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal\n🔗 Kanal linkini yuboring",
        },
        {
            "service": "tg_v04",
            "name": "👀 Ko'rishlar [ Oxirgi 50 Post ] 📋",
            "rate": "0.25", "min": 500, "max": 200000, "time": "0–2 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal\n🔗 Kanal linkini yuboring",
        },
        {
            "service": "tg_v05",
            "name": "👀 Ko'rishlar [ Barcha Postlarga ] 🗂",
            "rate": "0.40", "min": 500, "max": 100000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal\n🔗 Kanal linkini yuboring",
        },
        {
            "service": "tg_v06",
            "name": "🇺🇿 Ko'rishlar [ O'zbek ]",
            "rate": "0.35", "min": 500, "max": 100000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_v07",
            "name": "👀 Ko'rishlar [ Premium Akkauntlar ] 💎",
            "rate": "0.55", "min": 100, "max": 100000, "time": "1–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
    ],

    # ── TELEGRAM → REAKTSIYALAR ───────────────────────────────────────────────
    "tg_sub_reactions": [
        {
            "service": "tg_r01",
            "name": "❤️🔥 Reaktsiyalar [ Aralash ]",
            "rate": "0.25", "min": 10, "max": 10000, "time": "0–1 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_r02",
            "name": "👍 Reaktsiya [ Like ]",
            "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_r03",
            "name": "🔥 Reaktsiya [ Olov ]",
            "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_r04",
            "name": "🎉 Reaktsiya [ Bayram ]",
            "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_r05",
            "name": "💯 Reaktsiya [ Yuz foiz ]",
            "rate": "0.22", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_r06",
            "name": "😍 Reaktsiya [ Havas ]",
            "rate": "0.22", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_r07",
            "name": "❤️ Reaktsiya [ Qizil Yurak ]",
            "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_r08",
            "name": "👎 Reaktsiya [ Dislike ]",
            "rate": "0.22", "min": 10, "max": 5000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
    ],

    # ── TELEGRAM → IZOHLAR & BOSHQA ──────────────────────────────────────────
    "tg_sub_comments": [
        {
            "service": "tg_c01",
            "name": "💬 Izohlar [ Haqiqiy ]",
            "rate": "2.50", "min": 5, "max": 500, "time": "1–12 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Izoh yozish ochiq bo'lishi kerak\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_c02",
            "name": "📤 Ulashishlar [ Share ]",
            "rate": "0.30", "min": 100, "max": 50000, "time": "1–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_c03",
            "name": "📊 So'rovnoma Ovozlari",
            "rate": "0.50", "min": 50, "max": 5000, "time": "0–2 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ So'rovnoma ochiq bo'lishi kerak\n🔗 So'rovnoma havolasini yuboring",
        },
        {
            "service": "tg_c04",
            "name": "🔗 Havola Bosishlar [ Clicks ]",
            "rate": "0.45", "min": 100, "max": 50000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Havola ishlayotgan bo'lishi kerak\n🔗 Post havolasini yuboring",
        },
        {
            "service": "tg_c05",
            "name": "📣 Kanal Mention [ Eslatish ]",
            "rate": "5.00", "min": 10, "max": 1000, "time": "2–24 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Kanal public bo'lishi kerak\n🔗 Kanal @username yuboring",
        },
        {
            "service": "tg_c06",
            "name": "👁 Post Saqlashlar [ Forwards ]",
            "rate": "0.60", "min": 100, "max": 20000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Post ochiq bo'lishi kerak\n🔗 Post havolasini yuboring",
        },
    ],

    # ── INSTAGRAM → OBUNACHILAR ───────────────────────────────────────────────
    "ig_sub_followers": [
        {
            "service": "ig_01",
            "name": "👥 Obunachilar [ Haqiqiy va Faol ] 🧑",
            "rate": "1.50", "min": 100, "max": 100000, "time": "1–6 soat",
            "info": "♻️ Kafolat: 30 kun\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq (public) bo'lishi kerak",
        },
        {
            "service": "ig_02",
            "name": "👥 Obunachilar [ Premium Sifat ] 💎",
            "rate": "2.50", "min": 50, "max": 30000, "time": "6–24 soat",
            "info": "♻️ Kafolat: bor, tushsa to'ldiriladi\n⛔️ Chiqishlar: juda kam\n👤 Profil ochiq bo'lishi kerak",
        },
        {
            "service": "ig_03",
            "name": "👥 Obunachilar [ Arzon, Tezkor ] ⚡️",
            "rate": "0.80", "min": 100, "max": 50000, "time": "0–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor (tabiiy)\n👤 Profil ochiq bo'lishi kerak",
        },
        {
            "service": "ig_04",
            "name": "👥 Obunachilar [ Ayollar ] 👩",
            "rate": "2.00", "min": 100, "max": 20000, "time": "2–12 soat",
            "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak",
        },
        {
            "service": "ig_05",
            "name": "👥 Obunachilar [ Erkaklar ] 👨",
            "rate": "2.00", "min": 100, "max": 20000, "time": "2–12 soat",
            "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak",
        },
        {
            "service": "ig_06",
            "name": "👥 Obunachilar [ Arab ] 🇸🇦",
            "rate": "1.80", "min": 100, "max": 50000, "time": "2–12 soat",
            "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak",
        },
        {
            "service": "ig_07",
            "name": "👥 Obunachilar [ Turk ] 🇹🇷",
            "rate": "1.60", "min": 100, "max": 50000, "time": "2–12 soat",
            "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak",
        },
    ],

    # ── INSTAGRAM → LAYKLAR ──────────────────────────────────────────────────
    "ig_sub_likes": [
        {
            "service": "ig_l01",
            "name": "❤️ Layklar [ Tezkor ] ⚡️",
            "rate": "0.12", "min": 50, "max": 50000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor\n🔗 Post havolasini yuboring",
        },
        {
            "service": "ig_l02",
            "name": "❤️ Layklar [ Haqiqiy Profildan ] 🧑",
            "rate": "0.30", "min": 50, "max": 20000, "time": "1–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar: minimal\n🔗 Post havolasini yuboring",
        },
        {
            "service": "ig_l03",
            "name": "❤️ Layklar [ Oxirgi 5 Post ] 📋",
            "rate": "0.50", "min": 100, "max": 10000, "time": "0–2 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring",
        },
        {
            "service": "ig_l04",
            "name": "❤️ Layklar [ Oxirgi 10 Post ] 📋",
            "rate": "0.90", "min": 100, "max": 10000, "time": "0–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring",
        },
        {
            "service": "ig_l05",
            "name": "❤️ AutoLike [ 30 kun ] 🤖",
            "rate": "1.50", "min": 100, "max": 5000, "time": "Doimiy",
            "info": "♻️ 30 kunlik avtomatik xizmat\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring",
        },
        {
            "service": "ig_l06",
            "name": "❤️ Layklar [ Arab ] 🇸🇦",
            "rate": "0.40", "min": 50, "max": 20000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Post ochiq bo'lishi kerak\n🔗 Post havolasini yuboring",
        },
    ],

    # ── INSTAGRAM → KO'RISHLAR ────────────────────────────────────────────────
    "ig_sub_views": [
        {
            "service": "ig_v01",
            "name": "👁 Ko'rishlar [ Video va Reels ] 🎬",
            "rate": "0.07", "min": 500, "max": 1000000, "time": "0–1 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Post ochiq bo'lishi kerak\n🔗 Video/Reels havolasini yuboring",
        },
        {
            "service": "ig_v02",
            "name": "📊 Story Ko'rishlar",
            "rate": "0.10", "min": 100, "max": 100000, "time": "0–2 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Story aktiv bo'lishi kerak (24 soat)\n👤 Profil @username yuboring",
        },
        {
            "service": "ig_v03",
            "name": "🔴 Live Ko'ruvchilar",
            "rate": "1.50", "min": 10, "max": 1000, "time": "0–10 daqiqa",
            "info": "♻️ Live tugagach ketadi (tabiiy)\n⛔️ Live ayni paytda ishlayotgan bo'lsin\n🔗 Profil havolasini yuboring",
        },
        {
            "service": "ig_v04",
            "name": "🟡 IGTV Ko'rishlar",
            "rate": "0.15", "min": 500, "max": 200000, "time": "0–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ IGTV video ochiq bo'lishi kerak\n🔗 IGTV havolasini yuboring",
        },
        {
            "service": "ig_v05",
            "name": "👁 Reels Ko'rishlar [ Yuqori Sifat ] 🏆",
            "rate": "0.20", "min": 500, "max": 500000, "time": "0–2 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Reels ochiq bo'lishi kerak\n🔗 Reels havolasini yuboring",
        },
    ],

    # ── INSTAGRAM → IZOH & BOSHQA ─────────────────────────────────────────────
    "ig_sub_other": [
        {
            "service": "ig_o01",
            "name": "💬 Izohlar [ Haqiqiy ]",
            "rate": "3.00", "min": 5, "max": 1000, "time": "1–24 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Izoh yozish ochiq bo'lishi kerak\n🔗 Post havolasini yuboring",
        },
        {
            "service": "ig_o02",
            "name": "📤 Saqlashlar [ Post Saves ] 🔖",
            "rate": "0.50", "min": 100, "max": 10000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Post ochiq bo'lishi kerak\n🔗 Post havolasini yuboring",
        },
        {
            "service": "ig_o03",
            "name": "🔁 Reels Ulashishlar",
            "rate": "0.40", "min": 100, "max": 20000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Reels ochiq bo'lishi kerak\n🔗 Reels havolasini yuboring",
        },
        {
            "service": "ig_o04",
            "name": "✅ Profil Tashrif [ Visit ] 👣",
            "rate": "0.20", "min": 500, "max": 100000, "time": "0–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring",
        },
        {
            "service": "ig_o05",
            "name": "💌 DM Ko'rishlar",
            "rate": "0.35", "min": 100, "max": 10000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring",
        },
        {
            "service": "ig_o06",
            "name": "🔔 Mention [ @tag ] 📣",
            "rate": "1.20", "min": 50, "max": 5000, "time": "2–12 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring",
        },
    ],

    # ── YOUTUBE → KO'RISHLAR ─────────────────────────────────────────────────
    "yt_sub_views": [
        {
            "service": "yt_v01",
            "name": "👀 Ko'rishlar [ Yuqori Sifat HQ ] 🏆",
            "rate": "0.70", "min": 1000, "max": 1000000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq (public) bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "yt_v02",
            "name": "👀 Ko'rishlar [ Tezkor ] ⚡️",
            "rate": "0.40", "min": 1000, "max": 500000, "time": "0–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "yt_v03",
            "name": "👀 Ko'rishlar [ 60% Retention ] ⏱",
            "rate": "1.20", "min": 500, "max": 100000, "time": "6–24 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "yt_v04",
            "name": "👀 Ko'rishlar [ 100% Retention ] ✅",
            "rate": "2.50", "min": 100, "max": 50000, "time": "12–48 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "yt_v05",
            "name": "📱 Shorts Ko'rishlar",
            "rate": "0.10", "min": 1000, "max": 2000000, "time": "0–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Shorts video ochiq bo'lishi kerak\n🔗 Shorts havolasini yuboring",
        },
        {
            "service": "yt_v06",
            "name": "⏱ Watch Time [ 4000 Soat ]",
            "rate": "8.00", "min": 100, "max": 4000, "time": "2–7 kun",
            "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Video ochiq bo'lishi kerak (unlisted emas)\n🔗 Video havolasini yuboring",
        },
        {
            "service": "yt_v07",
            "name": "👀 Ko'rishlar [ 30% Retention ] ⏱",
            "rate": "0.85", "min": 500, "max": 200000, "time": "3–12 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
    ],

    # ── YOUTUBE → OBUNACHILAR ─────────────────────────────────────────────────
    "yt_sub_subscribers": [
        {
            "service": "yt_s01",
            "name": "🔔 Obunachilar [ Haqiqiy ] 🧑",
            "rate": "3.50", "min": 100, "max": 10000, "time": "6–48 soat",
            "info": "♻️ Kafolat: 30 kun\n⛔️ Chiqishlar bor (tabiiy)\n👤 Kanal ochiq bo'lishi kerak",
        },
        {
            "service": "yt_s02",
            "name": "🔔 Obunachilar [ Premium ] 💎",
            "rate": "5.00", "min": 50, "max": 5000, "time": "12–72 soat",
            "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Kanal ochiq bo'lishi kerak",
        },
        {
            "service": "yt_s03",
            "name": "🔔 Obunachilar [ Tezkor ] ⚡️",
            "rate": "2.00", "min": 100, "max": 50000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor (tabiiy)\n👤 Kanal ochiq bo'lishi kerak",
        },
        {
            "service": "yt_s04",
            "name": "🔔 Qo'ng'iroq [ Notification Bell ]",
            "rate": "1.00", "min": 100, "max": 5000, "time": "2–12 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Kanal ochiq bo'lishi kerak\n👤 Kanal havolasini yuboring",
        },
    ],

    # ── YOUTUBE → LAYKLAR ─────────────────────────────────────────────────────
    "yt_sub_likes": [
        {
            "service": "yt_l01",
            "name": "👍 Layklar [ Haqiqiy ]",
            "rate": "0.60", "min": 100, "max": 20000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "yt_l02",
            "name": "👍 Layklar [ Tezkor ] ⚡️",
            "rate": "0.30", "min": 100, "max": 50000, "time": "0–1 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "yt_l03",
            "name": "❤️ Shorts Layklar",
            "rate": "0.35", "min": 100, "max": 50000, "time": "0–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Shorts video ochiq bo'lishi kerak\n🔗 Shorts havolasini yuboring",
        },
        {
            "service": "yt_l04",
            "name": "👎 Disliklar [ Raqobat uchun ]",
            "rate": "0.80", "min": 100, "max": 10000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
    ],

    # ── YOUTUBE → IZOH & BOSHQA ───────────────────────────────────────────────
    "yt_sub_other": [
        {
            "service": "yt_o01",
            "name": "💬 Izohlar [ Haqiqiy ]",
            "rate": "4.00", "min": 5, "max": 500, "time": "1–24 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Izoh yozish yoqilgan bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "yt_o02",
            "name": "🔁 Ulashishlar",
            "rate": "0.50", "min": 100, "max": 10000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "yt_o03",
            "name": "📌 Playlist Qo'shish",
            "rate": "0.80", "min": 100, "max": 10000, "time": "2–12 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
    ],

    # ── TIKTOK → OBUNACHILAR ──────────────────────────────────────────────────
    "tt_sub_followers": [
        {
            "service": "tt_01",
            "name": "👥 Obunachilar [ Haqiqiy ] 🧑",
            "rate": "0.90", "min": 100, "max": 50000, "time": "1–6 soat",
            "info": "♻️ Kafolat: 30 kun\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak",
        },
        {
            "service": "tt_02",
            "name": "👥 Obunachilar [ Tezkor ] ⚡️",
            "rate": "0.50", "min": 100, "max": 100000, "time": "0–2 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor (tabiiy)\n👤 Profil ochiq bo'lishi kerak",
        },
        {
            "service": "tt_03",
            "name": "👥 Obunachilar [ Premium ] 💎",
            "rate": "1.80", "min": 50, "max": 30000, "time": "2–12 soat",
            "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: juda kam\n👤 Profil ochiq bo'lishi kerak",
        },
        {
            "service": "tt_f04",
            "name": "👥 Obunachilar [ AQSh ] 🇺🇸",
            "rate": "2.50", "min": 100, "max": 20000, "time": "6–24 soat",
            "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak",
        },
    ],

    # ── TIKTOK → LAYKLAR ─────────────────────────────────────────────────────
    "tt_sub_likes": [
        {
            "service": "tt_l01",
            "name": "❤️ Layklar [ Tezkor ] ⚡️",
            "rate": "0.15", "min": 100, "max": 100000, "time": "0–1 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor\n🔗 Video havolasini yuboring",
        },
        {
            "service": "tt_l02",
            "name": "❤️ Layklar [ Haqiqiy ] 🧑",
            "rate": "0.35", "min": 100, "max": 50000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar: minimal\n🔗 Video havolasini yuboring",
        },
        {
            "service": "tt_l03",
            "name": "❤️ AutoLike [ 30 kun ] 🤖",
            "rate": "1.20", "min": 100, "max": 5000, "time": "Doimiy",
            "info": "♻️ 30 kun davomida ishlaydi\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring",
        },
        {
            "service": "tt_l04",
            "name": "❤️ Layklar [ Arab ] 🇸🇦",
            "rate": "0.45", "min": 100, "max": 30000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
    ],

    # ── TIKTOK → KO'RISHLAR ──────────────────────────────────────────────────
    "tt_sub_views": [
        {
            "service": "tt_v01",
            "name": "👀 Ko'rishlar [ Tezkor ] ⚡️",
            "rate": "0.04", "min": 1000, "max": 5000000, "time": "0–30 daqiqa",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "tt_v02",
            "name": "👀 Ko'rishlar [ Yuqori Sifat ] 🏆",
            "rate": "0.12", "min": 1000, "max": 1000000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "tt_v03",
            "name": "▶️ Profil Ko'rishlar 👣",
            "rate": "0.20", "min": 500, "max": 100000, "time": "0–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring",
        },
        {
            "service": "tt_v04",
            "name": "🔴 Live Ko'ruvchilar",
            "rate": "1.20", "min": 10, "max": 500, "time": "0–10 daqiqa",
            "info": "♻️ Live tugagach ketadi (tabiiy)\n⛔️ Live ayni paytda ishlayotgan bo'lsin\n🔗 Profil havolasini yuboring",
        },
        {
            "service": "tt_v05",
            "name": "👀 Ko'rishlar [ 50% Retention ] ⏱",
            "rate": "0.25", "min": 1000, "max": 500000, "time": "2–8 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
    ],

    # ── TIKTOK → IZOH & BOSHQA ───────────────────────────────────────────────
    "tt_sub_other": [
        {
            "service": "tt_o01",
            "name": "💬 Izohlar [ Haqiqiy ]",
            "rate": "2.50", "min": 5, "max": 500, "time": "1–12 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Izoh yozish ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "tt_o02",
            "name": "🔁 Ulashishlar",
            "rate": "0.35", "min": 100, "max": 20000, "time": "1–3 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "tt_o03",
            "name": "📊 Saqlashlar [ Saves ] 🔖",
            "rate": "0.40", "min": 100, "max": 10000, "time": "1–6 soat",
            "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "tt_o04",
            "name": "🎁 TikTok Coins 🪙",
            "rate": "1.00", "min": 100, "max": 10000, "time": "0–6 soat",
            "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Akkaunt aktiv bo'lishi kerak\n👤 Profil @username yuboring",
        },
    ],

    # ── TG PREMIUM → PREMIUM OBUNA ────────────────────────────────────────────
    "tgp_sub_premium": [
        {
            "service": "tgp_01",
            "name": "💠 Telegram Premium [ 1 Oy ]",
            "rate": "4.00", "min": 1, "max": 100, "time": "0–6 soat",
            "info": "♻️ Kafolat: aktivatsiya kafolatlanadi\n⛔️ Akkaunt Telegram da ro'yxatdan o'tgan bo'lsin\n👤 @username yuboring",
        },
        {
            "service": "tgp_02",
            "name": "💠 Telegram Premium [ 3 Oy ]",
            "rate": "10.00", "min": 1, "max": 100, "time": "0–6 soat",
            "info": "♻️ Kafolat: aktivatsiya kafolatlanadi\n⛔️ Akkaunt Telegram da aktiv bo'lsin\n👤 @username yuboring",
        },
        {
            "service": "tgp_03",
            "name": "💠 Telegram Premium [ 6 Oy ]",
            "rate": "18.00", "min": 1, "max": 50, "time": "0–12 soat",
            "info": "♻️ Kafolat: aktivatsiya kafolatlanadi\n⛔️ Akkaunt Telegram da aktiv bo'lsin\n👤 @username yuboring",
        },
        {
            "service": "tgp_04",
            "name": "💠 Telegram Premium [ 12 Oy ]",
            "rate": "32.00", "min": 1, "max": 20, "time": "0–24 soat",
            "info": "♻️ Kafolat: aktivatsiya kafolatlanadi\n⛔️ Akkaunt Telegram da aktiv bo'lsin\n👤 @username yuboring",
        },
        {
            "service": "tgp_05",
            "name": "🎁 Premium Sovg'a [ Do'stingizga ]",
            "rate": "4.50", "min": 1, "max": 100, "time": "0–6 soat",
            "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Qabul qiluvchi Telegram da aktiv bo'lsin\n👤 @username yuboring",
        },
        {
            "service": "tgp_11",
            "name": "🏅 Fragment Username [ Sotib olish ]",
            "rate": "20.00", "min": 1, "max": 10, "time": "1–24 soat",
            "info": "♻️ Kafolat: muvaffaqiyatli bo'lmasa qaytariladi\n⛔️ Username bo'sh va sotuvda bo'lishi kerak\n👤 @username yuboring",
        },
    ],

    # ── TG PREMIUM → STARS ────────────────────────────────────────────────────
    "tgp_sub_stars": [
        {
            "service": "tgp_06",
            "name": "⭐ Telegram Stars [ 50 ta ]",
            "rate": "1.00", "min": 1, "max": 500, "time": "0–6 soat",
            "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Stars qabul qiluvchi bot/kanal kerak\n🔗 Bot yoki kanal linkini yuboring",
        },
        {
            "service": "tgp_07",
            "name": "⭐ Telegram Stars [ 100 ta ]",
            "rate": "1.80", "min": 1, "max": 500, "time": "0–6 soat",
            "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Stars qabul qiluvchi bot/kanal kerak\n🔗 Bot yoki kanal linkini yuboring",
        },
        {
            "service": "tgp_08",
            "name": "⭐ Telegram Stars [ 500 ta ]",
            "rate": "8.00", "min": 1, "max": 200, "time": "0–6 soat",
            "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Stars qabul qiluvchi bot/kanal kerak\n🔗 Bot yoki kanal linkini yuboring",
        },
        {
            "service": "tgp_09",
            "name": "⭐ Telegram Stars [ 1000 ta ]",
            "rate": "14.00", "min": 1, "max": 100, "time": "0–12 soat",
            "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Stars qabul qiluvchi bot/kanal kerak\n🔗 Bot yoki kanal linkini yuboring",
        },
        {
            "service": "tgp_10",
            "name": "🌟 Stars Sovg'a [ Xabar orqali ]",
            "rate": "1.50", "min": 50, "max": 10000, "time": "0–6 soat",
            "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Xabar ochiq bo'lishi kerak\n🔗 Post/xabar havolasini yuboring",
        },
        {
            "service": "tgp_12",
            "name": "⭐ Telegram Stars [ 2500 ta ]",
            "rate": "32.00", "min": 1, "max": 50, "time": "0–24 soat",
            "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Stars qabul qiluvchi bot/kanal kerak\n🔗 Bot yoki kanal linkini yuboring",
        },
    ],

    # ── TEKIN XIZMATLAR ───────────────────────────────────────────────────────
    "free_sub_all": [
        {
            "service": "free_01",
            "name": "🆓 Telegram 50 Ko'rish [ Tekin ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "0–1 soat",
            "info": "♻️ Har foydalanuvchi 1 martadan\n⛔️ Kanal ochiq bo'lishi kerak\n🔗 Post havolasini yuboring",
        },
        {
            "service": "free_02",
            "name": "🆓 Instagram 10 Layk [ Tekin ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "0–1 soat",
            "info": "♻️ Har foydalanuvchi 1 martadan\n⛔️ Post ochiq bo'lishi kerak\n🔗 Post havolasini yuboring",
        },
        {
            "service": "free_03",
            "name": "🆓 YouTube 100 Ko'rish [ Tekin ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "0–2 soat",
            "info": "♻️ Har foydalanuvchi 1 martadan\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "free_04",
            "name": "🆓 TikTok 200 Ko'rish [ Tekin ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "0–1 soat",
            "info": "♻️ Har foydalanuvchi 1 martadan\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring",
        },
        {
            "service": "free_05",
            "name": "🎁 Do'st Taklif [ Bonus 5 000 so'm ]",
            "rate": "0.00", "min": 1, "max": 999, "time": "Darhol",
            "info": "♻️ Ikkalangiz ham 5 000 so'm olasiz\n⛔️ Do'stingiz yangi foydalanuvchi bo'lishi kerak\n👤 Referal havolangizni ulashing",
        },
        {
            "service": "free_06",
            "name": "🆓 Telegram 5 A'zo [ Tekin ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "0–2 soat",
            "info": "♻️ Har foydalanuvchi 1 martadan\n⛔️ Kanal ochiq bo'lishi kerak\n🔗 Kanal havolasini yuboring",
        },
        {
            "service": "free_07",
            "name": "🎁 Kunlik Bonus [ 500 so'm ]",
            "rate": "0.00", "min": 1, "max": 1, "time": "Darhol",
            "info": "♻️ Har 24 soatda 1 marta\n⛔️ /bonus buyrug'ini yuboring\n👤 Hech narsa yuborish shart emas",
        },
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# 🔧 YORDAMCHI FUNKSIYALAR
# ══════════════════════════════════════════════════════════════════════════════

def find_service(svc_id: str) -> dict | None:
    for services in ALL_SERVICES.values():
        for s in services:
            if s["service"] == svc_id:
                return s
    return None


def find_sub_by_svc(svc_id: str) -> str | None:
    for sub_id, services in ALL_SERVICES.items():
        for s in services:
            if s["service"] == svc_id:
                return sub_id
    return None


def find_cat_by_sub(sub_id: str) -> str:
    for cat_id, subs in SUB_CATEGORIES.items():
        for s in subs:
            if s["id"] == sub_id:
                return cat_id
    return "telegram"


def search_services(query: str) -> list:
    q = query.lower().strip()
    results, seen = [], set()
    for services in ALL_SERVICES.values():
        for svc in services:
            if q in svc["name"].lower() or q in svc["service"].lower():
                if svc["service"] not in seen:
                    results.append(svc)
                    seen.add(svc["service"])
    return results


def price_label(rate_val: float) -> str:
    if rate_val == 0:
        return "🆓 BEPUL"
    return f"{rate_val * USD_TO_SOM / 1000:,.0f} so'm/1000"


def calc_total(rate_val: float, qty: int) -> float:
    if rate_val == 0:
        return 0.0
    return (rate_val * USD_TO_SOM / 1000) * qty


def _to_dict(row) -> dict | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        return None


def get_sub_service_count(cat_id: str) -> int:
    return sum(len(ALL_SERVICES.get(s["id"], [])) for s in SUB_CATEGORIES.get(cat_id, []))


# ══════════════════════════════════════════════════════════════════════════════
# ⌨️ KLAVIATURALAR
# ══════════════════════════════════════════════════════════════════════════════

def kb_categories():
    builder = InlineKeyboardBuilder()
    for i in range(0, len(CATEGORIES) - 1, 2):
        c1, c2 = CATEGORIES[i], CATEGORIES[i + 1]
        builder.row(
            InlineKeyboardButton(text=c1["name"], callback_data=f"cat|{c1['id']}"),
            InlineKeyboardButton(text=c2["name"], callback_data=f"cat|{c2['id']}"),
        )
    if len(CATEGORIES) % 2 != 0:
        last = CATEGORIES[-1]
        builder.row(InlineKeyboardButton(text=last["name"], callback_data=f"cat|{last['id']}"))
    builder.row(InlineKeyboardButton(text="🔍 Xizmat Qidirish",           callback_data="open_search"))
    builder.row(InlineKeyboardButton(text="📋 Barcha Xizmatlar Ro'yxati", callback_data="all_services_list"))
    return builder.as_markup()


def kb_subcategories(cat_id: str):
    builder = InlineKeyboardBuilder()
    for sub in SUB_CATEGORIES.get(cat_id, []):
        builder.row(InlineKeyboardButton(
            text=sub["name"],
            callback_data=f"sub|{sub['id']}",
        ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_cats"))
    return builder.as_markup()


def kb_services(sub_id: str, page: int = 0):
    services    = ALL_SERVICES.get(sub_id, [])
    per_page    = 8
    start       = page * per_page
    end         = start + per_page
    total_pages = max(1, (len(services) + per_page - 1) // per_page)
    cat_id      = find_cat_by_sub(sub_id)

    builder = InlineKeyboardBuilder()
    for svc in services[start:end]:
        builder.row(InlineKeyboardButton(
            text=f"{svc['name']} — {price_label(float(svc['rate']))}",
            callback_data=f"svc|{svc['service']}",
        ))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀️ Oldingi", callback_data=f"subpage|{sub_id}|{page - 1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"📄 {page + 1}/{total_pages}", callback_data="noop"
    ))
    if end < len(services):
        nav.append(InlineKeyboardButton(
            text="Keyingi ▶️", callback_data=f"subpage|{sub_id}|{page + 1}"
        ))
    builder.row(*nav)
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"cat|{cat_id}"))
    return builder.as_markup()


def kb_search_results(results: list):
    builder = InlineKeyboardBuilder()
    for svc in results[:10]:
        builder.row(InlineKeyboardButton(
            text=f"{svc['name']} — {price_label(float(svc['rate']))}",
            callback_data=f"svc|{svc['service']}",
        ))
    builder.row(InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="back_to_cats"))
    return builder.as_markup()


def kb_cancel_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order"))
    return builder.as_markup()


def kb_confirm():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash",   callback_data="confirm_order"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order"),
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# 🎨 XIZMAT KARTOCHKASI — yangi format
# ══════════════════════════════════════════════════════════════════════════════

def build_service_card(svc: dict) -> str:
    rate_val = float(svc["rate"])
    is_free  = rate_val == 0

    # Narx qatori
    if is_free:
        price_line = "💵 Narx (x1000): <b>BEPUL 🆓</b>"
    else:
        total_per_1000 = rate_val * USD_TO_SOM
        price_line = f"💵 Narx (x1000): <b>{total_per_1000:,.0f} so'm</b>"

    # Vaqt qatori
    t = svc["time"]
    if any(x in t for x in ["daqiqa", "Darhol", "0–30"]):
        time_line = "📑 : ⚡️ Boshlanish vaqti: Tez"
    elif "Doimiy" in t:
        time_line = "📑 : 🔄 Boshlanish vaqti: Doimiy (avtomatik)"
    elif "kun" in t:
        time_line = f"📑 : 📅 Boshlanish vaqti: {t}"
    else:
        time_line = f"📑 : 🕐 Boshlanish vaqti: {t}"

    # Info — string yoki list bo'lishi mumkin
    info = svc.get("info", "")
    if isinstance(info, list):
        info = "\n".join(info)

    return (
        f"<b>{svc['name']}</b>\n\n"
        f"🔑 ID: {svc['service']}\n"
        f"{price_line}\n"
        f"{time_line}\n\n"
        f"{info}\n\n"
        f"☝️ Ta'rif bilan tanishib chiqib ✅ <b>Davom etish</b> tugmasini bosing!"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 🎯 HANDLERLAR
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "🛒 Xizmatlar")
async def services_menu(message: Message):
    total = sum(get_sub_service_count(c["id"]) for c in CATEGORIES)
    await message.answer(
        "🛍 <b>SMM Xizmatlar</b>\n\n"
        "✅ Tezkor • Sifatli • Arzon\n"
        f"📦 Jami: <b>{total} ta xizmat</b>\n"
        "🎁 Tekin xizmatlar ham mavjud!\n\n"
        "📌 Kerakli platformani tanlang 👇",
        parse_mode="HTML",
        reply_markup=kb_categories(),
    )


@router.callback_query(F.data == "back_to_cats")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    total = sum(get_sub_service_count(c["id"]) for c in CATEGORIES)
    await callback.message.edit_text(
        "🛍 <b>SMM Xizmatlar</b>\n\n"
        "✅ Tezkor • Sifatli • Arzon\n"
        f"📦 Jami: <b>{total} ta xizmat</b>\n"
        "🎁 Tekin xizmatlar ham mavjud!\n\n"
        "📌 Kerakli platformani tanlang 👇",
        parse_mode="HTML",
        reply_markup=kb_categories(),
    )
    await callback.answer()


# ── Kategoriya → Sub-kategoriyalar ───────────────────────────────────────────
@router.callback_query(F.data.startswith("cat|"))
async def show_category(callback: CallbackQuery):
    cat_id = callback.data.split("|")[1]
    cat    = next((c for c in CATEGORIES if c["id"] == cat_id), None)
    if not cat:
        await callback.answer("Kategoriya topilmadi!", show_alert=True)
        return

    await callback.message.edit_text(
        f"🛍️ <b>{cat['name']}</b>\n\n"
        f"Quyidagi ichki bo'limlardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=kb_subcategories(cat_id),
    )
    await callback.answer()


# ── Sub-kategoriya → Xizmatlar ───────────────────────────────────────────────
@router.callback_query(F.data.startswith("sub|"))
async def show_subcategory(callback: CallbackQuery):
    sub_id = callback.data.split("|")[1]
    sub    = None
    for subs in SUB_CATEGORIES.values():
        sub = next((s for s in subs if s["id"] == sub_id), None)
        if sub:
            break

    services = ALL_SERVICES.get(sub_id, [])
    label    = sub["name"] if sub else sub_id

    await callback.message.edit_text(
        f"<b>{label}</b>\n\n"
        f"📦 Jami: <b>{len(services)} ta xizmat</b>\n"
        f"👇 Kerakli xizmatni tanlang:",
        parse_mode="HTML",
        reply_markup=kb_services(sub_id, 0),
    )
    await callback.answer()


# ── Sahifalash ────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("subpage|"))
async def paginate_services(callback: CallbackQuery):
    parts  = callback.data.split("|")
    sub_id = parts[1]
    page   = int(parts[2])
    sub    = None
    for subs in SUB_CATEGORIES.values():
        sub = next((s for s in subs if s["id"] == sub_id), None)
        if sub:
            break
    services = ALL_SERVICES.get(sub_id, [])
    label    = sub["name"] if sub else sub_id
    await callback.message.edit_text(
        f"<b>{label}</b>\n\n"
        f"📦 Jami: <b>{len(services)} ta xizmat</b>\n"
        f"👇 Kerakli xizmatni tanlang:",
        parse_mode="HTML",
        reply_markup=kb_services(sub_id, page),
    )
    await callback.answer()


@router.callback_query(F.data == "all_services_list")
async def all_services_list(callback: CallbackQuery):
    text  = "📋 <b>Barcha xizmatlar ro'yxati:</b>\n\n"
    total = 0
    for cat in CATEGORIES:
        count = get_sub_service_count(cat["id"])
        subs  = SUB_CATEGORIES.get(cat["id"], [])
        text += f"{cat['name']} — <b>{count} ta</b>\n"
        for sub in subs:
            sc    = len(ALL_SERVICES.get(sub["id"], []))
            text += f"  {sub['name']}: {sc} ta\n"
        total += count
        text  += "\n"
    text += f"📦 Jami: <b>{total} ta xizmat</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb_categories())
    await callback.answer()


# ── QIDIRUV ───────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "open_search")
async def open_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.searching_service)
    await callback.message.edit_text(
        "🔍 <b>Xizmat Qidirish</b>\n\n"
        "Xizmat nomini yozing:\n"
        "<i>Masalan: a'zolar, layk, ko'rish, premium, stars...</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_cats")
        ).as_markup(),
    )
    await callback.answer()


@router.message(OrderStates.searching_service)
async def process_search(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if query == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_main_menu())
        return
    if len(query) < 2:
        await message.answer("❌ Kamida 2 ta harf kiriting!")
        return

    results = search_services(query)
    await state.clear()

    if not results:
        await message.answer(
            f"🔍 <b>«{query}»</b> bo'yicha hech narsa topilmadi.\n💡 Boshqa so'z bilan qidiring.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="back_to_cats")
            ).as_markup(),
        )
        return

    await message.answer(
        f"🔍 <b>«{query}»</b> — <b>{len(results)} ta</b> xizmat topildi:\n\n👇 Tanlang:",
        parse_mode="HTML",
        reply_markup=kb_search_results(results),
    )


# ── XIZMAT KARTOCHKASI ────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("svc|"))
async def show_service_detail(callback: CallbackQuery, state: FSMContext):
    svc_id = callback.data.split("|")[1]
    svc    = find_service(svc_id)
    if not svc:
        await callback.answer("Xizmat topilmadi!", show_alert=True)
        return

    sub_id   = find_sub_by_svc(svc_id)
    rate_val = float(svc["rate"])

    await state.update_data(
        service_id=svc_id,
        service_name=svc["name"],
        rate=rate_val,
        min_qty=svc["min"],
        max_qty=svc["max"],
        sub_id=sub_id,
        time=svc["time"],
    )

    btn_text = "🎁 Bepul olish" if rate_val == 0 else "✅ Davom etish"
    builder  = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"order_start|{svc_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"sub|{sub_id}"))

    await callback.message.edit_text(
        build_service_card(svc),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


# ── BUYURTMA OQIMI ────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("order_start|"))
async def order_start(callback: CallbackQuery, state: FSMContext):
    svc_id   = callback.data.split("|")[1]
    svc      = find_service(svc_id)
    if not svc:
        await callback.answer("Xizmat topilmadi!", show_alert=True)
        return

    rate_val = float(svc["rate"])
    is_free  = rate_val == 0

    await state.update_data(
        service_id=svc_id,
        service_name=svc["name"],
        rate=rate_val,
        min_qty=svc["min"],
        max_qty=svc["max"],
        time=svc["time"],
    )

    if is_free:
        await state.update_data(quantity=svc["min"])
        await state.set_state(OrderStates.waiting_link)
        await callback.message.edit_text(
            f"✅ <b>{svc['name']}</b> tanlandi!\n\n"
            f"🔗 Havola (link) yuboring:\n"
            f"<i>Namuna: https://t.me/username</i>",
            parse_mode="HTML",
            reply_markup=kb_cancel_inline(),
        )
    else:
        await state.set_state(OrderStates.waiting_quantity)
        await callback.message.edit_text(
            f"<b>{svc['name']}</b>\n\n"
            f"🔽 Minimal: <b>{svc['min']:,} ta</b>\n"
            f"🔼 Maksimal: <b>{svc['max']:,} ta</b>\n\n"
            f"✏️ Kerakli miqdorni kiriting:",
            parse_mode="HTML",
            reply_markup=kb_cancel_inline(),
        )
    await callback.answer()


@router.message(OrderStates.waiting_quantity)
async def process_quantity(message: Message, state: FSMContext):
    if (message.text or "").strip() == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_main_menu())
        return
    try:
        qty = int((message.text or "").replace(" ", "").replace(",", ""))
    except ValueError:
        await message.answer("❌ Faqat butun son kiriting!")
        return

    data = await state.get_data()
    if qty < data.get("min_qty", 1):
        await message.answer(f"❌ Minimal: <b>{data['min_qty']:,} ta</b>", parse_mode="HTML")
        return
    if qty > data.get("max_qty", 999999):
        await message.answer(f"❌ Maksimal: <b>{data['max_qty']:,} ta</b>", parse_mode="HTML")
        return

    await state.update_data(quantity=qty)
    await state.set_state(OrderStates.waiting_link)
    await message.answer(
        f"✅ <b>{qty:,} ta</b> qabul qilindi!\n\n"
        f"🔗 Post havolasini yuboring:\n"
        f"<i>❕ Namuna: https://instagram.com/p/xyz/</i>",
        parse_mode="HTML",
        reply_markup=kb_cancel_inline(),
    )


@router.message(OrderStates.waiting_link)
async def process_link(message: Message, state: FSMContext):
    if (message.text or "").strip() == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_main_menu())
        return

    link = (message.text or "").strip()
    valid = any(link.startswith(p) for p in ("http://", "https://", "@", "t.me/"))
    if not valid:
        await message.answer(
            "❌ <b>Noto'g'ri havola!</b>\n\n"
            "• <code>https://t.me/username</code>\n"
            "• <code>@username</code>\n"
            "• <code>t.me/username</code>",
            parse_mode="HTML",
        )
        return

    data     = await state.get_data()
    qty      = data.get("quantity") or data.get("min_qty", 1)
    rate_val = float(data.get("rate", 0))
    total    = calc_total(rate_val, qty)

    await state.update_data(link=link, total=total)

    user    = _to_dict(await get_user(message.from_user.id))
    balance = float((user.get("balance") if user else 0) or 0)

    price_line   = "💰 Narx: <b>BEPUL 🆓</b>" if rate_val == 0 else f"💰 Narx: <b>{total:,.0f} so'm</b>"
    balance_line = f"💳 Balans: <b>{balance:,.0f} so'm</b>"

    await state.set_state(OrderStates.confirming_order)
    await message.answer(
        f"📋 <b>Buyurtma ma'lumotlari</b>\n\n"
        f"🛍 Xizmat: <b>{data.get('service_name', '')}</b>\n"
        f"🔗 Havola: <code>{link}</code>\n"
        f"📊 Miqdor: <b>{qty:,} ta</b>\n"
        f"{price_line}\n"
        f"{balance_line}\n\n"
        f"Tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=kb_confirm(),
    )


@router.callback_query(F.data == "cancel_order")
async def cancel_order_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ Buyurtma bekor qilindi.", reply_markup=None)
    except Exception:
        await callback.message.answer("❌ Buyurtma bekor qilindi.", reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    data    = await state.get_data()
    user_id = callback.from_user.id
    user    = _to_dict(await get_user(user_id))

    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return

    total   = float(data.get("total", 0.0))
    is_free = total == 0.0
    balance = float(user.get("balance") or 0)

    if not is_free and balance < total:
        shortage = total - balance
        await callback.message.edit_text(
            f"❌ <b>Balans yetarli emas!</b>\n\n"
            f"💳 Sizning balans: <b>{balance:,.0f} so'm</b>\n"
            f"💰 Kerakli summa: <b>{total:,.0f} so'm</b>\n"
            f"➖ Yetishmaydi: <b>{shortage:,.0f} so'm</b>\n\n"
            f"💳 <b>Hisob To'ldirish</b> bo'limiga o'ting!",
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    if not is_free:
        await update_user_balance(user_id, total, add=False)
        await update_total_spent(user_id, total)

    quantity = data.get("quantity") or data.get("min_qty", 1)
    order_id = await create_order(
        user_id=user_id,
        service_id=data["service_id"],
        service_name=data["service_name"],
        link=data["link"],
        quantity=quantity,
        charge=total,
    )
    await log_transaction(user_id, total, "order", f"Buyurtma #{order_id}: {data['service_name']}")

    smm_order_id = await _place_smm_order(data["service_id"], data["link"], quantity)
    await state.clear()

    ext_id = smm_order_id or order_id
    await callback.message.edit_text(
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"🆔 Buyurtma ID: <b>{ext_id}</b>\n"
        f"Yuqoridagi ID orqali buyurtmangiz holatini tekshirishingiz mumkin!",
        parse_mode="HTML",
    )
    await callback.answer("✅ Buyurtma qabul qilindi!")


# ══════════════════════════════════════════════════════════════════════════════
# 🌐 SMM API
# ══════════════════════════════════════════════════════════════════════════════

async def _place_smm_order(service_id: str, link: str, quantity: int) -> int | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                settings.SMM_API_URL,
                data={
                    "key":      settings.SMM_API_KEY,
                    "action":   "add",
                    "service":  service_id,
                    "link":     link,
                    "quantity": quantity,
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                result = await resp.json()
                if "error" in result:
                    logger.error(f"SMM API xato: {result['error']}")
                    return None
                return result.get("order")
    except Exception as e:
        logger.error(f"SMM API xato: {e}")
        return None


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()