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
# 🔑 REAL SMM PANEL ID MAPPING
# ══════════════════════════════════════════════════════════════════════════════

SMM_ID_MAP: dict[str, int] = {
    # ── TELEGRAM A'ZOLAR ──────────────────────────────────────────────────────
    "tg_01": 14455,   # Mix, arzon
    "tg_02": 14453,   # Real R60
    "tg_03": 14455,   # Arzon tezkor
    "tg_04": 21021,   # 60 Days Non Drop
    "tg_05": 21021,
    "tg_06": 21022,   # 90 Days Non Drop
    "tg_07": 14455,   # Global
    "tg_08": 24847,   # High Quality
    # ── TELEGRAM KO'RISHLAR ───────────────────────────────────────────────────
    "tg_v01": 15974,  # Any Post, eng arzon
    "tg_v02": 16926,  # Last 1 Post
    "tg_v03": 1369,   # Last 50 Post
    "tg_v04": 13290,  # Instant
    "tg_v05": 13132,  # 10M
    "tg_v06": 15974,
    "tg_v07": 28478,  # Premium Views
    # ── TELEGRAM REAKTSIYALAR ─────────────────────────────────────────────────
    "tg_r01": 23343,  # Aralash
    "tg_r02": 23335,  # 👍
    "tg_r03": 23339,  # 🔥
    "tg_r04": 23345,  # 🎉
    "tg_r05": 23346,  # 🤩
    "tg_r06": 23338,  # ❤️
    "tg_r07": 23337,  # 🤝
    "tg_r08": 23361,  # 👎 Negative
    # ── TELEGRAM IZOHLAR & BOSHQA ─────────────────────────────────────────────
    "tg_c01": 23343,
    "tg_c02": 23343,
    "tg_c03": 23343,
    "tg_c04": 23343,
    "tg_c05": 23343,
    "tg_c06": 23343,
    # ── INSTAGRAM OBUNACHILAR ─────────────────────────────────────────────────
    "ig_01": 22042,   # Real People
    "ig_02": 16345,   # Accs with Stories
    "ig_03": 17598,   # Mix HQ
    "ig_04": 16344,
    "ig_05": 16343,
    "ig_06": 16344,
    "ig_07": 16344,
    # ── INSTAGRAM LAYKLAR ─────────────────────────────────────────────────────
    "ig_l01": 30776,  # Eng arzon
    "ig_l02": 13157,  # Real Look
    "ig_l03": 13753,  # No Drop
    "ig_l04": 16360,
    "ig_l05": 13157,
    "ig_l06": 16360,
    # ── INSTAGRAM KO'RISHLAR ──────────────────────────────────────────────────
    "ig_v01": 19865,  # Eng arzon
    "ig_v02": 17649,  # Story Views
    "ig_v03": 15094,  # Emergency
    "ig_v04": 16413,  # Views+Reels
    "ig_v05": 16280,
    # ── INSTAGRAM BOSHQA ──────────────────────────────────────────────────────
    "ig_o01": 10564,
    "ig_o02": 10570,
    "ig_o03": 13260,
    "ig_o04": 19865,
    "ig_o05": 19865,
    "ig_o06": 19865,
    # ── YOUTUBE KO'RISHLAR ────────────────────────────────────────────────────
    "yt_v01": 9221,   # Lifetime Warranty
    "yt_v02": 13541,  # Speed 200K/D
    "yt_v03": 20374,  # Dual Method
    "yt_v04": 20427,  # USA Retention
    "yt_v05": 13897,  # Arzon
    "yt_v06": 1904,   # Russia
    "yt_v07": 17258,  # Views+Likes
    # ── YOUTUBE OBUNACHILAR ───────────────────────────────────────────────────
    "yt_s01": 14265,
    "yt_s02": 14265,
    "yt_s03": 14265,
    "yt_s04": 14265,
    # ── YOUTUBE LAYKLAR ───────────────────────────────────────────────────────
    "yt_l01": 20363,
    "yt_l02": 22066,  # 0-15 Min
    "yt_l03": 13494,  # 0-1 Hour
    "yt_l04": 24131,
    # ── YOUTUBE BOSHQA ────────────────────────────────────────────────────────
    "yt_o01": 20363,
    "yt_o02": 20363,
    "yt_o03": 20363,
    # ── TIKTOK OBUNACHILAR ────────────────────────────────────────────────────
    "tt_01":  25166,
    "tt_02":  24942,  # 0-15Min
    "tt_03":  1811,   # R30
    "tt_f04": 25167,
    # ── TIKTOK LAYKLAR ────────────────────────────────────────────────────────
    "tt_l01": 18654,  # Eng arzon
    "tt_l02": 19672,
    "tt_l03": 25003,
    "tt_l04": 25004,
    # ── TIKTOK KO'RISHLAR ─────────────────────────────────────────────────────
    "tt_v01": 6359,   # Eng arzon
    "tt_v02": 3231,   # 0-30Min
    "tt_v03": 5171,   # 0-15Min
    "tt_v04": 17778,  # Instant
    "tt_v05": 6895,
    # ── TIKTOK BOSHQA ─────────────────────────────────────────────────────────
    "tt_o01": 6359,
    "tt_o02": 6359,
    "tt_o03": 6359,
    "tt_o04": 6359,
    # ── TG PREMIUM ────────────────────────────────────────────────────────────
    "tgp_01": 28506,
    "tgp_02": 28506,
    "tgp_03": 28506,
    "tgp_04": 28506,
    "tgp_05": 28506,
    "tgp_06": 28478,  # Premium Views
    "tgp_07": 28479,  # Last 5 Posts
    "tgp_08": 28480,  # Last 20 Posts
    "tgp_09": 28561,
    "tgp_10": 28562,  # Story Views
    "tgp_11": 28565,  # Shares
    "tgp_12": 28563,
    # ── TEKIN ─────────────────────────────────────────────────────────────────
    "free_01": 15974,
    "free_02": 30776,
    "free_03": 13897,
    "free_04": 6359,
    "free_05": 0,
    "free_06": 14455,
    "free_07": 0,
}

def get_smm_id(service_id: str) -> int:
    return SMM_ID_MAP.get(service_id, 0)


# ══════════════════════════════════════════════════════════════════════════════
# 📌 STATES
# ══════════════════════════════════════════════════════════════════════════════

class OrderStates(StatesGroup):
    searching_service = State()
    waiting_quantity  = State()
    waiting_link      = State()
    confirming_order  = State()


# ══════════════════════════════════════════════════════════════════════════════
# 🔗 HAVOLA VALIDATSIYASI
# ══════════════════════════════════════════════════════════════════════════════

LINK_RULES = {
    "tg_": {
        "prefixes": ("https://t.me/", "http://t.me/", "t.me/", "@"),
        "hint": "📌 Telegram havolasi yuborish kerak\n\n✅ Formatlar:\n• <code>https://t.me/username</code>\n• <code>@username</code>",
    },
    "ig_": {
        "prefixes": ("https://www.instagram.com/", "https://instagram.com/", "http://instagram.com/", "@"),
        "hint": "📌 Instagram havolasi yuborish kerak\n\n✅ Format:\n• <code>https://www.instagram.com/username</code>",
    },
    "yt_": {
        "prefixes": ("https://www.youtube.com/", "https://youtube.com/", "https://youtu.be/"),
        "hint": "📌 YouTube havolasi yuborish kerak\n\n✅ Formatlar:\n• <code>https://www.youtube.com/watch?v=...</code>\n• <code>https://youtu.be/...</code>",
    },
    "tt_": {
        "prefixes": ("https://www.tiktok.com/", "https://tiktok.com/", "https://vm.tiktok.com/", "@"),
        "hint": "📌 TikTok havolasi yuborish kerak\n\n✅ Format:\n• <code>https://www.tiktok.com/@username</code>",
    },
    "tgp_": {
        "prefixes": ("@", "https://t.me/", "http://t.me/", "t.me/"),
        "hint": "📌 Telegram @username yoki havola yuborish kerak\n\n✅ Format:\n• <code>@username</code>",
    },
    "free_": {
        "prefixes": ("https://", "http://", "@", "t.me/"),
        "hint": "📌 Havola yuborish kerak\n\n✅ Format:\n• <code>https://t.me/username</code>",
    },
}


def get_link_rule(service_id: str) -> dict:
    for prefix, rule in LINK_RULES.items():
        if service_id.startswith(prefix):
            return rule
    return {
        "prefixes": ("https://", "http://", "@", "t.me/"),
        "hint": "📌 To'g'ri havola kiriting",
    }


def validate_link(link: str, service_id: str) -> bool:
    rule = get_link_rule(service_id)
    return any(link.startswith(p) for p in rule["prefixes"])


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
# ══════════════════════════════════════════════════════════════════════════════

ALL_SERVICES = {
    "tg_sub_members": [
        {"service": "tg_01", "name": "👥 A'zolar [ Real va Faol ] ⚡️",     "rate": "0.80", "min": 100,  "max": 50000,   "time": "0–2 soat",   "info": "♻️ Kafolat: 30 kun\n⛔️ Chiqishlar: minimal\n👤 Kanal/guruh ochiq bo'lishi kerak"},
        {"service": "tg_02", "name": "👥 A'zolar [ Premium Sifat ] 💎",     "rate": "1.20", "min": 50,   "max": 20000,   "time": "1–6 soat",   "info": "♻️ Kafolat: bor, tushsa to'ldiriladi\n⛔️ Chiqishlar: juda kam\n👤 Kanal/guruh ochiq bo'lishi kerak"},
        {"service": "tg_03", "name": "👥 A'zolar [ Arzon va Tezkor ] 💨",   "rate": "0.40", "min": 200,  "max": 100000,  "time": "0–1 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor (tabiiy)\n👤 Kanal/guruh ochiq bo'lishi kerak"},
        {"service": "tg_04", "name": "👥 A'zolar [ Bot Emas, Real ] 🧑",    "rate": "1.80", "min": 100,  "max": 30000,   "time": "2–8 soat",   "info": "♻️ Kafolat: 30 kun\n⛔️ Chiqishlar: kam\n👤 Kanal/guruh ochiq bo'lishi kerak"},
        {"service": "tg_05", "name": "🇺🇿 A'zolar [ O'zbek, Real ]",         "rate": "3.00", "min": 50,   "max": 5000,    "time": "2–12 soat",  "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Kanal ochiq bo'lishi kerak"},
        {"service": "tg_06", "name": "🇺🇿 A'zolar [ O'zbek Guruh ]",         "rate": "3.50", "min": 50,   "max": 5000,    "time": "2–24 soat",  "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Guruh public bo'lishi kerak"},
        {"service": "tg_07", "name": "👥 A'zolar [ Xorijiy, Global ] 🌍",   "rate": "0.30", "min": 100,  "max": 200000,  "time": "0–2 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor (tabiiy)\n👤 Kanal ochiq bo'lishi kerak"},
        {"service": "tg_08", "name": "👥 A'zolar [ Kanal — Sekin ] 🐢",     "rate": "0.60", "min": 100,  "max": 50000,   "time": "6–24 soat",  "info": "♻️ Kafolat: 15 kun\n⛔️ Chiqishlar: juda kam\n👤 Kanal ochiq bo'lishi kerak"},
    ],
    "tg_sub_views": [
        {"service": "tg_v01", "name": "👀 Ko'rishlar [ Tezkor ] ⚡️",              "rate": "0.08", "min": 500,  "max": 1000000, "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
        {"service": "tg_v02", "name": "👀 Ko'rishlar [ Oxirgi 5 Post ] 📋",       "rate": "0.12", "min": 500,  "max": 500000,  "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal\n🔗 Kanal linkini yuboring"},
        {"service": "tg_v03", "name": "👀 Ko'rishlar [ Oxirgi 10 Post ] 📋",      "rate": "0.15", "min": 500,  "max": 500000,  "time": "0–1 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal\n🔗 Kanal linkini yuboring"},
        {"service": "tg_v04", "name": "👀 Ko'rishlar [ Oxirgi 50 Post ] 📋",      "rate": "0.25", "min": 500,  "max": 200000,  "time": "0–2 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal\n🔗 Kanal linkini yuboring"},
        {"service": "tg_v05", "name": "👀 Ko'rishlar [ Barcha Postlarga ] 🗂",    "rate": "0.40", "min": 500,  "max": 100000,  "time": "1–6 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal\n🔗 Kanal linkini yuboring"},
        {"service": "tg_v06", "name": "🇺🇿 Ko'rishlar [ O'zbek ]",                "rate": "0.35", "min": 500,  "max": 100000,  "time": "1–6 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
        {"service": "tg_v07", "name": "👀 Ko'rishlar [ Premium Akkauntlar ] 💎",  "rate": "0.55", "min": 100,  "max": 100000,  "time": "1–3 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
    ],
    "tg_sub_reactions": [
        {"service": "tg_r01", "name": "❤️🔥 Reaktsiyalar [ Aralash ]",     "rate": "0.25", "min": 10, "max": 10000, "time": "0–1 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
        {"service": "tg_r02", "name": "👍 Reaktsiya [ Like ]",              "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
        {"service": "tg_r03", "name": "🔥 Reaktsiya [ Olov ]",              "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
        {"service": "tg_r04", "name": "🎉 Reaktsiya [ Bayram ]",            "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
        {"service": "tg_r05", "name": "💯 Reaktsiya [ Yuz foiz ]",          "rate": "0.22", "min": 10, "max": 10000, "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
        {"service": "tg_r06", "name": "😍 Reaktsiya [ Havas ]",             "rate": "0.22", "min": 10, "max": 10000, "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
        {"service": "tg_r07", "name": "❤️ Reaktsiya [ Qizil Yurak ]",       "rate": "0.20", "min": 10, "max": 10000, "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
        {"service": "tg_r08", "name": "👎 Reaktsiya [ Dislike ]",            "rate": "0.22", "min": 10, "max": 5000,  "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
    ],
    "tg_sub_comments": [
        {"service": "tg_c01", "name": "💬 Izohlar [ Haqiqiy ]",             "rate": "2.50", "min": 5,   "max": 500,   "time": "1–12 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Izoh yozish ochiq bo'lishi kerak\n🔗 Post havolasini yuboring"},
        {"service": "tg_c02", "name": "📤 Ulashishlar [ Share ]",           "rate": "0.30", "min": 100, "max": 50000, "time": "1–3 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Faqat ochiq kanal postlari\n🔗 Post havolasini yuboring"},
        {"service": "tg_c03", "name": "📊 So'rovnoma Ovozlari",             "rate": "0.50", "min": 50,  "max": 5000,  "time": "0–2 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ So'rovnoma ochiq bo'lishi kerak\n🔗 So'rovnoma havolasini yuboring"},
        {"service": "tg_c04", "name": "🔗 Havola Bosishlar [ Clicks ]",     "rate": "0.45", "min": 100, "max": 50000, "time": "1–6 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Havola ishlayotgan bo'lishi kerak\n🔗 Post havolasini yuboring"},
        {"service": "tg_c05", "name": "📣 Kanal Mention [ Eslatish ]",      "rate": "5.00", "min": 10,  "max": 1000,  "time": "2–24 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Kanal public bo'lishi kerak\n🔗 Kanal @username yuboring"},
        {"service": "tg_c06", "name": "👁 Post Saqlashlar [ Forwards ]",    "rate": "0.60", "min": 100, "max": 20000, "time": "1–6 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Post ochiq bo'lishi kerak\n🔗 Post havolasini yuboring"},
    ],
    "ig_sub_followers": [
        {"service": "ig_01", "name": "👥 Obunachilar [ Haqiqiy va Faol ] 🧑", "rate": "1.50", "min": 100, "max": 100000, "time": "1–6 soat",   "info": "♻️ Kafolat: 30 kun\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak"},
        {"service": "ig_02", "name": "👥 Obunachilar [ Premium Sifat ] 💎",   "rate": "2.50", "min": 50,  "max": 30000,  "time": "6–24 soat",  "info": "♻️ Kafolat: bor, tushsa to'ldiriladi\n⛔️ Chiqishlar: juda kam\n👤 Profil ochiq bo'lishi kerak"},
        {"service": "ig_03", "name": "👥 Obunachilar [ Arzon, Tezkor ] ⚡️",  "rate": "0.80", "min": 100, "max": 50000,  "time": "0–3 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor (tabiiy)\n👤 Profil ochiq bo'lishi kerak"},
        {"service": "ig_04", "name": "👥 Obunachilar [ Ayollar ] 👩",         "rate": "2.00", "min": 100, "max": 20000,  "time": "2–12 soat",  "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak"},
        {"service": "ig_05", "name": "👥 Obunachilar [ Erkaklar ] 👨",        "rate": "2.00", "min": 100, "max": 20000,  "time": "2–12 soat",  "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak"},
        {"service": "ig_06", "name": "👥 Obunachilar [ Arab ] 🇸🇦",           "rate": "1.80", "min": 100, "max": 50000,  "time": "2–12 soat",  "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak"},
        {"service": "ig_07", "name": "👥 Obunachilar [ Turk ] 🇹🇷",           "rate": "1.60", "min": 100, "max": 50000,  "time": "2–12 soat",  "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak"},
    ],
    "ig_sub_likes": [
        {"service": "ig_l01", "name": "❤️ Layklar [ Tezkor ] ⚡️",             "rate": "0.12", "min": 50,  "max": 50000, "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor\n🔗 Post havolasini yuboring"},
        {"service": "ig_l02", "name": "❤️ Layklar [ Haqiqiy Profildan ] 🧑",  "rate": "0.30", "min": 50,  "max": 20000, "time": "1–3 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar: minimal\n🔗 Post havolasini yuboring"},
        {"service": "ig_l03", "name": "❤️ Layklar [ Oxirgi 5 Post ] 📋",      "rate": "0.50", "min": 100, "max": 10000, "time": "0–2 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring"},
        {"service": "ig_l04", "name": "❤️ Layklar [ Oxirgi 10 Post ] 📋",     "rate": "0.90", "min": 100, "max": 10000, "time": "0–3 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring"},
        {"service": "ig_l05", "name": "❤️ AutoLike [ 30 kun ] 🤖",            "rate": "1.50", "min": 100, "max": 5000,  "time": "Doimiy",      "info": "♻️ 30 kunlik avtomatik xizmat\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring"},
        {"service": "ig_l06", "name": "❤️ Layklar [ Arab ] 🇸🇦",              "rate": "0.40", "min": 50,  "max": 20000, "time": "1–6 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Post ochiq bo'lishi kerak\n🔗 Post havolasini yuboring"},
    ],
    "ig_sub_views": [
        {"service": "ig_v01", "name": "👁 Ko'rishlar [ Video va Reels ] 🎬",       "rate": "0.07", "min": 500, "max": 1000000, "time": "0–1 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Post ochiq bo'lishi kerak\n🔗 Video/Reels havolasini yuboring"},
        {"service": "ig_v02", "name": "📊 Story Ko'rishlar",                       "rate": "0.10", "min": 100, "max": 100000,  "time": "0–2 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Story aktiv bo'lishi kerak (24 soat)\n👤 Profil @username yuboring"},
        {"service": "ig_v03", "name": "🔴 Live Ko'ruvchilar",                      "rate": "1.50", "min": 10,  "max": 1000,    "time": "0–10 daqiqa","info": "♻️ Live tugagach ketadi (tabiiy)\n⛔️ Live ayni paytda ishlayotgan bo'lsin\n🔗 Profil havolasini yuboring"},
        {"service": "ig_v04", "name": "🟡 IGTV Ko'rishlar",                        "rate": "0.15", "min": 500, "max": 200000,  "time": "0–3 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ IGTV video ochiq bo'lishi kerak\n🔗 IGTV havolasini yuboring"},
        {"service": "ig_v05", "name": "👁 Reels Ko'rishlar [ Yuqori Sifat ] 🏆",   "rate": "0.20", "min": 500, "max": 500000,  "time": "0–2 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Reels ochiq bo'lishi kerak\n🔗 Reels havolasini yuboring"},
    ],
    "ig_sub_other": [
        {"service": "ig_o01", "name": "💬 Izohlar [ Haqiqiy ]",             "rate": "3.00", "min": 5,   "max": 1000,  "time": "1–24 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Izoh yozish ochiq bo'lishi kerak\n🔗 Post havolasini yuboring"},
        {"service": "ig_o02", "name": "📤 Saqlashlar [ Post Saves ] 🔖",   "rate": "0.50", "min": 100, "max": 10000, "time": "1–6 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Post ochiq bo'lishi kerak\n🔗 Post havolasini yuboring"},
        {"service": "ig_o03", "name": "🔁 Reels Ulashishlar",              "rate": "0.40", "min": 100, "max": 20000, "time": "1–6 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Reels ochiq bo'lishi kerak\n🔗 Reels havolasini yuboring"},
        {"service": "ig_o04", "name": "✅ Profil Tashrif [ Visit ] 👣",    "rate": "0.20", "min": 500, "max": 100000,"time": "0–3 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring"},
        {"service": "ig_o05", "name": "💌 DM Ko'rishlar",                  "rate": "0.35", "min": 100, "max": 10000, "time": "1–6 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring"},
        {"service": "ig_o06", "name": "🔔 Mention [ @tag ] 📣",            "rate": "1.20", "min": 50,  "max": 5000,  "time": "2–12 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring"},
    ],
    "yt_sub_views": [
        {"service": "yt_v01", "name": "👀 Ko'rishlar [ Yuqori Sifat HQ ] 🏆",  "rate": "0.70", "min": 1000, "max": 1000000, "time": "1–6 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq (public) bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "yt_v02", "name": "👀 Ko'rishlar [ Tezkor ] ⚡️",          "rate": "0.40", "min": 1000, "max": 500000,  "time": "0–3 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "yt_v03", "name": "👀 Ko'rishlar [ 60% Retention ] ⏱",    "rate": "1.20", "min": 500,  "max": 100000,  "time": "6–24 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "yt_v04", "name": "👀 Ko'rishlar [ 100% Retention ] ✅",   "rate": "2.50", "min": 100,  "max": 50000,   "time": "12–48 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "yt_v05", "name": "📱 Shorts Ko'rishlar",                  "rate": "0.10", "min": 1000, "max": 2000000, "time": "0–3 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Shorts video ochiq bo'lishi kerak\n🔗 Shorts havolasini yuboring"},
        {"service": "yt_v06", "name": "⏱ Watch Time [ 4000 Soat ]",           "rate": "8.00", "min": 100,  "max": 4000,    "time": "2–7 kun",    "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Video ochiq bo'lishi kerak (unlisted emas)\n🔗 Video havolasini yuboring"},
        {"service": "yt_v07", "name": "👀 Ko'rishlar [ 30% Retention ] ⏱",    "rate": "0.85", "min": 500,  "max": 200000,  "time": "3–12 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
    ],
    "yt_sub_subscribers": [
        {"service": "yt_s01", "name": "🔔 Obunachilar [ Haqiqiy ] 🧑",    "rate": "3.50", "min": 100, "max": 10000, "time": "6–48 soat",  "info": "♻️ Kafolat: 30 kun\n⛔️ Chiqishlar bor (tabiiy)\n👤 Kanal ochiq bo'lishi kerak"},
        {"service": "yt_s02", "name": "🔔 Obunachilar [ Premium ] 💎",    "rate": "5.00", "min": 50,  "max": 5000,  "time": "12–72 soat", "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Kanal ochiq bo'lishi kerak"},
        {"service": "yt_s03", "name": "🔔 Obunachilar [ Tezkor ] ⚡️",   "rate": "2.00", "min": 100, "max": 50000, "time": "1–6 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor (tabiiy)\n👤 Kanal ochiq bo'lishi kerak"},
        {"service": "yt_s04", "name": "🔔 Qo'ng'iroq [ Notification ]",  "rate": "1.00", "min": 100, "max": 5000,  "time": "2–12 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Kanal ochiq bo'lishi kerak\n👤 Kanal havolasini yuboring"},
    ],
    "yt_sub_likes": [
        {"service": "yt_l01", "name": "👍 Layklar [ Haqiqiy ]",          "rate": "0.60", "min": 100, "max": 20000, "time": "1–6 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "yt_l02", "name": "👍 Layklar [ Tezkor ] ⚡️",       "rate": "0.30", "min": 100, "max": 50000, "time": "0–1 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "yt_l03", "name": "❤️ Shorts Layklar",               "rate": "0.35", "min": 100, "max": 50000, "time": "0–3 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Shorts video ochiq bo'lishi kerak\n🔗 Shorts havolasini yuboring"},
        {"service": "yt_l04", "name": "👎 Disliklar [ Raqobat uchun ]",  "rate": "0.80", "min": 100, "max": 10000, "time": "1–6 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
    ],
    "yt_sub_other": [
        {"service": "yt_o01", "name": "💬 Izohlar [ Haqiqiy ]",   "rate": "4.00", "min": 5,   "max": 500,   "time": "1–24 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Izoh yozish yoqilgan bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "yt_o02", "name": "🔁 Ulashishlar",           "rate": "0.50", "min": 100, "max": 10000, "time": "1–6 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "yt_o03", "name": "📌 Playlist Qo'shish",     "rate": "0.80", "min": 100, "max": 10000, "time": "2–12 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
    ],
    "tt_sub_followers": [
        {"service": "tt_01",  "name": "👥 Obunachilar [ Haqiqiy ] 🧑",   "rate": "0.90", "min": 100, "max": 50000,  "time": "1–6 soat",   "info": "♻️ Kafolat: 30 kun\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak"},
        {"service": "tt_02",  "name": "👥 Obunachilar [ Tezkor ] ⚡️",   "rate": "0.50", "min": 100, "max": 100000, "time": "0–2 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor (tabiiy)\n👤 Profil ochiq bo'lishi kerak"},
        {"service": "tt_03",  "name": "👥 Obunachilar [ Premium ] 💎",   "rate": "1.80", "min": 50,  "max": 30000,  "time": "2–12 soat",  "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: juda kam\n👤 Profil ochiq bo'lishi kerak"},
        {"service": "tt_f04", "name": "👥 Obunachilar [ AQSh ] 🇺🇸",     "rate": "2.50", "min": 100, "max": 20000,  "time": "6–24 soat",  "info": "♻️ Kafolat: bor\n⛔️ Chiqishlar: minimal\n👤 Profil ochiq bo'lishi kerak"},
    ],
    "tt_sub_likes": [
        {"service": "tt_l01", "name": "❤️ Layklar [ Tezkor ] ⚡️",    "rate": "0.15", "min": 100, "max": 100000, "time": "0–1 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar bor\n🔗 Video havolasini yuboring"},
        {"service": "tt_l02", "name": "❤️ Layklar [ Haqiqiy ] 🧑",   "rate": "0.35", "min": 100, "max": 50000,  "time": "1–6 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Chiqishlar: minimal\n🔗 Video havolasini yuboring"},
        {"service": "tt_l03", "name": "❤️ AutoLike [ 30 kun ] 🤖",   "rate": "1.20", "min": 100, "max": 5000,   "time": "Doimiy",     "info": "♻️ 30 kun davomida ishlaydi\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring"},
        {"service": "tt_l04", "name": "❤️ Layklar [ Arab ] 🇸🇦",     "rate": "0.45", "min": 100, "max": 30000,  "time": "1–6 soat",   "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
    ],
    "tt_sub_views": [
        {"service": "tt_v01", "name": "👀 Ko'rishlar [ Tezkor ] ⚡️",          "rate": "0.04", "min": 1000, "max": 5000000, "time": "0–30 daqiqa", "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "tt_v02", "name": "👀 Ko'rishlar [ Yuqori Sifat ] 🏆",     "rate": "0.12", "min": 1000, "max": 1000000, "time": "1–6 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "tt_v03", "name": "▶️ Profil Ko'rishlar 👣",                "rate": "0.20", "min": 500,  "max": 100000,  "time": "0–3 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Profil ochiq bo'lishi kerak\n👤 Profil @username yuboring"},
        {"service": "tt_v04", "name": "🔴 Live Ko'ruvchilar",                   "rate": "1.20", "min": 10,   "max": 500,     "time": "0–10 daqiqa", "info": "♻️ Live tugagach ketadi (tabiiy)\n⛔️ Live ayni paytda ishlayotgan bo'lsin\n🔗 Profil havolasini yuboring"},
        {"service": "tt_v05", "name": "👀 Ko'rishlar [ 50% Retention ] ⏱",     "rate": "0.25", "min": 1000, "max": 500000,  "time": "2–8 soat",    "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
    ],
    "tt_sub_other": [
        {"service": "tt_o01", "name": "💬 Izohlar [ Haqiqiy ]",          "rate": "2.50", "min": 5,   "max": 500,   "time": "1–12 soat", "info": "♻️ Tiklashlar yo'q\n⛔️ Izoh yozish ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "tt_o02", "name": "🔁 Ulashishlar",                  "rate": "0.35", "min": 100, "max": 20000, "time": "1–3 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "tt_o03", "name": "📊 Saqlashlar [ Saves ] 🔖",     "rate": "0.40", "min": 100, "max": 10000, "time": "1–6 soat",  "info": "♻️ Tiklashlar yo'q\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
        {"service": "tt_o04", "name": "🎁 TikTok Coins 🪙",              "rate": "1.00", "min": 100, "max": 10000, "time": "0–6 soat",  "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Akkaunt aktiv bo'lishi kerak\n👤 Profil @username yuboring"},
    ],
    "tgp_sub_premium": [
        {"service": "tgp_01", "name": "💠 Telegram Premium [ 1 Oy ]",              "rate": "4.00",  "min": 1, "max": 100, "time": "0–6 soat",   "info": "♻️ Kafolat: aktivatsiya kafolatlanadi\n⛔️ Akkaunt Telegram da ro'yxatdan o'tgan bo'lsin\n👤 @username yuboring"},
        {"service": "tgp_02", "name": "💠 Telegram Premium [ 3 Oy ]",              "rate": "10.00", "min": 1, "max": 100, "time": "0–6 soat",   "info": "♻️ Kafolat: aktivatsiya kafolatlanadi\n⛔️ Akkaunt Telegram da aktiv bo'lsin\n👤 @username yuboring"},
        {"service": "tgp_03", "name": "💠 Telegram Premium [ 6 Oy ]",              "rate": "18.00", "min": 1, "max": 50,  "time": "0–12 soat",  "info": "♻️ Kafolat: aktivatsiya kafolatlanadi\n⛔️ Akkaunt Telegram da aktiv bo'lsin\n👤 @username yuboring"},
        {"service": "tgp_04", "name": "💠 Telegram Premium [ 12 Oy ]",             "rate": "32.00", "min": 1, "max": 20,  "time": "0–24 soat",  "info": "♻️ Kafolat: aktivatsiya kafolatlanadi\n⛔️ Akkaunt Telegram da aktiv bo'lsin\n👤 @username yuboring"},
        {"service": "tgp_05", "name": "🎁 Premium Sovg'a [ Do'stingizga ]",        "rate": "4.50",  "min": 1, "max": 100, "time": "0–6 soat",   "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Qabul qiluvchi Telegram da aktiv bo'lsin\n👤 @username yuboring"},
        {"service": "tgp_11", "name": "🏅 Fragment Username [ Sotib olish ]",      "rate": "20.00", "min": 1, "max": 10,  "time": "1–24 soat",  "info": "♻️ Kafolat: muvaffaqiyatli bo'lmasa qaytariladi\n⛔️ Username bo'sh va sotuvda bo'lishi kerak\n👤 @username yuboring"},
    ],
    "tgp_sub_stars": [
        {"service": "tgp_06", "name": "⭐ Telegram Stars [ 50 ta ]",    "rate": "1.00",  "min": 1, "max": 500,  "time": "0–6 soat",  "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Stars qabul qiluvchi bot/kanal kerak\n🔗 Bot yoki kanal linkini yuboring"},
        {"service": "tgp_07", "name": "⭐ Telegram Stars [ 100 ta ]",   "rate": "1.80",  "min": 1, "max": 500,  "time": "0–6 soat",  "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Stars qabul qiluvchi bot/kanal kerak\n🔗 Bot yoki kanal linkini yuboring"},
        {"service": "tgp_08", "name": "⭐ Telegram Stars [ 500 ta ]",   "rate": "8.00",  "min": 1, "max": 200,  "time": "0–6 soat",  "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Stars qabul qiluvchi bot/kanal kerak\n🔗 Bot yoki kanal linkini yuboring"},
        {"service": "tgp_09", "name": "⭐ Telegram Stars [ 1000 ta ]",  "rate": "14.00", "min": 1, "max": 100,  "time": "0–12 soat", "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Stars qabul qiluvchi bot/kanal kerak\n🔗 Bot yoki kanal linkini yuboring"},
        {"service": "tgp_10", "name": "🌟 Stars Sovg'a [ Xabar orqali ]","rate": "1.50", "min": 50, "max": 10000,"time": "0–6 soat",  "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Xabar ochiq bo'lishi kerak\n🔗 Post/xabar havolasini yuboring"},
        {"service": "tgp_12", "name": "⭐ Telegram Stars [ 2500 ta ]",  "rate": "32.00", "min": 1, "max": 50,   "time": "0–24 soat", "info": "♻️ Kafolat: yetkazilmasa qaytariladi\n⛔️ Stars qabul qiluvchi bot/kanal kerak\n🔗 Bot yoki kanal linkini yuboring"},
    ],
    "free_sub_all": [
    {"service": "free_01", "name": "🆓 Telegram 100 Ko'rish [ Tekin ]",     "rate": "0.00", "min": 1, "max": 1, "time": "0–1 soat", "info": "♻️ Har foydalanuvchi 1 martadan\n⛔️ Kanal ochiq bo'lishi kerak\n🔗 Post havolasini yuboring"},
    {"service": "free_02", "name": "🆓 Instagram 10 Layk [ Tekin ]",        "rate": "0.00", "min": 1, "max": 1, "time": "0–1 soat", "info": "♻️ Har foydalanuvchi 1 martadan\n⛔️ Post ochiq bo'lishi kerak\n🔗 Post havolasini yuboring"},
    {"service": "free_03", "name": "🆓 YouTube 100 Ko'rish [ Tekin ]",      "rate": "0.00", "min": 1, "max": 1, "time": "0–2 soat", "info": "♻️ Har foydalanuvchi 1 martadan\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
    {"service": "free_04", "name": "🆓 TikTok 100 Ko'rish [ Tekin ]",       "rate": "0.00", "min": 1, "max": 1, "time": "0–1 soat", "info": "♻️ Har foydalanuvchi 1 martadan\n⛔️ Video ochiq bo'lishi kerak\n🔗 Video havolasini yuboring"},
    {"service": "free_05", "name": "🆓 Telegram 10 Reaktsiya [ Tekin ] ❤️", "rate": "0.00", "min": 1, "max": 1, "time": "0–1 soat", "info": "♻️ Har foydalanuvchi 1 martadan\n⛔️ Post ochiq bo'lishi kerak\n🔗 Post havolasini yuboring"},
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
    return f"{rate_val * USD_TO_SOM:,.0f} so'm"


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


# ✅ TO'G'RILANDI: bot o'zining xabarini o'chiradi, foydalanuvchinikini emas
async def _safe_delete_bot_message(bot, chat_id: int, message_id: int):
    """Faqat BOT yuborgan xabarni o'chiradi."""
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


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
        builder.row(InlineKeyboardButton(text=sub["name"], callback_data=f"sub|{sub['id']}"))
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
        nav.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"subpage|{sub_id}|{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if end < len(services):
        nav.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"subpage|{sub_id}|{page + 1}"))
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


def kb_admin_approve(order_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_approve|{order_id}"),
        InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"admin_reject|{order_id}"),
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# 🎨 XIZMAT KARTOCHKASI
# ══════════════════════════════════════════════════════════════════════════════

def build_service_card(svc: dict) -> str:
    rate_val = float(svc["rate"])
    is_free  = rate_val == 0

    price_line = "💵 Narx (x1000): <b>BEPUL 🆓</b>" if is_free else \
                 f"💵 Narx (x1000): <b>{rate_val * USD_TO_SOM:,.0f} so'm</b>"

    t = svc["time"]
    if any(x in t for x in ["daqiqa", "Darhol", "0–30"]):
        time_line = "📑 Boshlanish: ⚡️ Tez"
    elif "Doimiy" in t:
        time_line = "📑 Boshlanish: 🔄 Doimiy (avtomatik)"
    elif "kun" in t:
        time_line = f"📑 Boshlanish: 📅 {t}"
    else:
        time_line = f"📑 Boshlanish: 🕐 {t}"

    info = svc.get("info", "")

    return (
        f"<b>{svc['name']}</b>\n\n"
        f"🔑 ID: <code>{svc['service']}</code>\n"
        f"{price_line}\n"
        f"🔽 Minimal: <b>{svc['min']:,} ta</b>\n"
        f"🔼 Maksimal: <b>{svc['max']:,} ta</b>\n"
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


@router.callback_query(F.data.startswith("cat|"))
async def show_category(callback: CallbackQuery):
    cat_id = callback.data.split("|")[1]
    cat    = next((c for c in CATEGORIES if c["id"] == cat_id), None)
    if not cat:
        await callback.answer("Kategoriya topilmadi!", show_alert=True)
        return
    await callback.message.edit_text(
        f"🛍️ <b>{cat['name']}</b>\n\nQuyidagi bo'limlardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=kb_subcategories(cat_id),
    )
    await callback.answer()


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
        f"<b>{label}</b>\n\n📦 Jami: <b>{len(services)} ta xizmat</b>\n👇 Kerakli xizmatni tanlang:",
        parse_mode="HTML",
        reply_markup=kb_services(sub_id, 0),
    )
    await callback.answer()


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
        f"<b>{label}</b>\n\n📦 Jami: <b>{len(services)} ta xizmat</b>\n👇 Kerakli xizmatni tanlang:",
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


# ── QIDIRUV ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "open_search")
async def open_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.searching_service)
    # ✅ Bot o'zining xabar ID sini saqlaymiz
    sent = await callback.message.edit_text(
        "🔍 <b>Xizmat Qidirish</b>\n\nXizmat nomini yozing:\n"
        "Masalan: a'zolar, layk, ko'rish, premium, stars...",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_cats")
        ).as_markup(),
    )
    await state.update_data(bot_message_id=callback.message.message_id)
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

    # ✅ Foydalanuvchi xabarini o'chiramiz (faqat bu yerda user xabari o'chirilishi kerak)
    try:
        await message.delete()
    except Exception:
        pass

    # ✅ Bot xabarini (qidiruv so'rovi xabari) o'chiramiz
    data = await state.get_data()
    bot_msg_id = data.get("bot_message_id")
    if bot_msg_id:
        await _safe_delete_bot_message(message.bot, message.chat.id, bot_msg_id)

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
        link_hint=get_link_rule(svc_id)["hint"],
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
    svc_id = callback.data.split("|")[1]
    svc    = find_service(svc_id)
    if not svc:
        await callback.answer("Xizmat topilmadi!", show_alert=True)
        return

    rate_val   = float(svc["rate"])
    is_free    = rate_val == 0
    link_rule  = get_link_rule(svc_id)

    await state.update_data(
        service_id=svc_id,
        service_name=svc["name"],
        rate=rate_val,
        min_qty=svc["min"],
        max_qty=svc["max"],
        time=svc["time"],
        link_hint=link_rule["hint"],
    )

    if is_free:
        await state.update_data(quantity=svc["min"])
        await state.set_state(OrderStates.waiting_link)
        # ✅ edit_text ishlatamiz — yangi xabar emas, shu xabarni o'zgartiradi
        await callback.message.edit_text(
            f"✅ <b>{svc['name']}</b> tanlandi!\n\n🔗 Havola yuboring:\n\n{link_rule['hint']}",
            parse_mode="HTML",
            reply_markup=kb_cancel_inline(),
        )
        # ✅ Bot xabar ID sini saqlaymiz — keyingi bosqichda o'chirish uchun
        await state.update_data(bot_message_id=callback.message.message_id)
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
        # ✅ Bot xabar ID sini saqlaymiz
        await state.update_data(bot_message_id=callback.message.message_id)
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

    # ✅ FAQAT BOT xabarini o'chiramiz (foydalanuvchi raqam kiritgan xabarini EMAS)
    bot_msg_id = data.get("bot_message_id")
    if bot_msg_id:
        await _safe_delete_bot_message(message.bot, message.chat.id, bot_msg_id)

    await state.update_data(quantity=qty)
    await state.set_state(OrderStates.waiting_link)

    hint = data.get("link_hint", "📌 Havola yuboring")
    # ✅ Yangi xabar yuboramiz va uning ID sini saqlaymiz
    sent = await message.answer(
        f"✅ <b>{qty:,} ta</b> qabul qilindi!\n\n🔗 Havola yuboring:\n\n{hint}",
        parse_mode="HTML",
        reply_markup=kb_cancel_inline(),
    )
    await state.update_data(bot_message_id=sent.message_id)


@router.message(OrderStates.waiting_link)
async def process_link(message: Message, state: FSMContext):
    if (message.text or "").strip() == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_main_menu())
        return

    link   = (message.text or "").strip()
    data   = await state.get_data()
    svc_id = data.get("service_id", "")

    if not validate_link(link, svc_id):
        hint = data.get("link_hint", "📌 To'g'ri havola kiriting")
        await message.answer(
            f"❌ <b>Noto'g'ri havola formati!</b>\n\n{hint}",
            parse_mode="HTML",
        )
        return

    # ✅ FAQAT BOT xabarini o'chiramiz
    bot_msg_id = data.get("bot_message_id")
    if bot_msg_id:
        await _safe_delete_bot_message(message.bot, message.chat.id, bot_msg_id)

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
        pass
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

    # Tekin xizmatlar uchun real miqdor
    FREE_QUANTITIES = {
        "free_01": 100,
        "free_02": 10,
        "free_03": 100,
        "free_04": 100,
        "free_05": 10,
    }

    quantity = data.get("quantity") or data.get("min_qty", 1)
    smm_id   = get_smm_id(data["service_id"])
    real_qty = FREE_QUANTITIES.get(data["service_id"], quantity)

    # Peakerr ga avtomatik yuborish
    smm_order_id = await _place_smm_order(smm_id, data["link"], real_qty)

    order_id = await create_order(
        user_id=user_id,
        service_id=data["service_id"],
        service_name=data["service_name"],
        link=data["link"],
        quantity=real_qty,
        charge=total,
        api_order_id=str(smm_order_id) if smm_order_id else None,
    )

    await callback.message.edit_text(
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"🆔 Buyurtma ID: <b>#{order_id}</b>\n\n"
        f"⏳ Buyurtmangiz tez orada bajariladi.",
        parse_mode="HTML",
    )
    await callback.answer("✅ Buyurtma qabul qilindi!")

    user_info  = f"@{callback.from_user.username}" if callback.from_user.username else f"ID: {user_id}"
    price_text = "BEPUL 🆓" if is_free else f"{total:,.0f} so'm"
    smm_id     = get_smm_id(data["service_id"])

    admin_text = (
        f"🔔 <b>YANGI BUYURTMA #{order_id}</b>\n\n"
        f"👤 Foydalanuvchi: {user_info}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"🛍 Xizmat: <b>{data['service_name']}</b>\n"
        f"🔑 Bot ID: <code>{data['service_id']}</code>\n"
        f"🌐 SMM Panel ID: <code>{smm_id}</code>\n"
        f"🔗 Havola: <code>{data['link']}</code>\n"
        f"📊 Miqdor: <b>{quantity:,} ta</b>\n"
        f"💰 Narx: <b>{price_text}</b>\n\n"
        f"✅ Tasdiqlash yoki ❌ rad etish:"
    )

    try:
        await callback.bot.send_message(
            chat_id=settings.ADMIN_ID,
            text=admin_text,
            parse_mode="HTML",
            reply_markup=kb_admin_approve(order_id),
        )
    except Exception as e:
        logger.error(f"Adminga xabar yuborishda xato: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 🛡 ADMIN TASDIQLASH
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin_approve|"))
async def admin_approve_order(callback: CallbackQuery):
    if callback.from_user.id != settings.ADMIN_ID:
        await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return

    order_id = int(callback.data.split("|")[1])
    order    = await _get_order_from_db(order_id)
    if not order:
        await callback.answer("❌ Buyurtma topilmadi!", show_alert=True)
        return

    smm_panel_id = get_smm_id(order["service_id"])
    smm_order_id = await _place_smm_order(smm_panel_id, order["link"], order["quantity"])
    ext_id       = smm_order_id or order_id

    try:
        await callback.message.edit_text(
            callback.message.text + f"\n\n✅ <b>TASDIQLANDI</b> — SMM ID: <b>{ext_id}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer("✅ Buyurtma SMM API ga yuborildi!")

    try:
        await callback.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"🎉 <b>Buyurtmangiz tasdiqlandi!</b>\n\n"
                f"🆔 Buyurtma ID: <b>#{order_id}</b>\n"
                f"🛍 Xizmat: <b>{order['service_name']}</b>\n"
                f"📊 Miqdor: <b>{order['quantity']:,} ta</b>\n\n"
                f"🚀 Xizmat boshlanmoqda..."
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Foydalanuvchiga xabar yuborishda xato: {e}")


@router.callback_query(F.data.startswith("admin_reject|"))
async def admin_reject_order(callback: CallbackQuery):
    if callback.from_user.id != settings.ADMIN_ID:
        await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return

    order_id = int(callback.data.split("|")[1])
    order    = await _get_order_from_db(order_id)
    if not order:
        await callback.answer("❌ Buyurtma topilmadi!", show_alert=True)
        return

    charge = float(order.get("charge", 0) or 0)
    if charge > 0:
        await update_user_balance(order["user_id"], charge, add=True)
        await log_transaction(order["user_id"], charge, "refund", f"Qaytarish — #{order_id}")

    refund_text = f"\n💸 <b>{charge:,.0f} so'm</b> balansga qaytarildi." if charge > 0 else ""

    try:
        await callback.message.edit_text(
            callback.message.text + f"\n\n❌ <b>RAD ETILDI</b>{refund_text}",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer("❌ Buyurtma rad etildi!")

    try:
        await callback.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"❌ <b>Buyurtmangiz rad etildi!</b>\n\n"
                f"🆔 Buyurtma ID: <b>#{order_id}</b>\n"
                f"{refund_text}\n\n"
                f"❓ Savol bo'lsa admin bilan bog'laning."
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Foydalanuvchiga xabar yuborishda xato: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 🌐 SMM API
# ══════════════════════════════════════════════════════════════════════════════

async def _place_smm_order(smm_panel_id: int, link: str, quantity: int) -> int | None:
    if not smm_panel_id:
        logger.error("SMM panel ID topilmadi!")
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                settings.SMM_API_URL,
                data={
                    "key":      settings.SMM_API_KEY,
                    "action":   "add",
                    "service":  smm_panel_id,
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


async def _get_order_from_db(order_id: int) -> dict | None:
    try:
        from database.db_queries import get_order_by_id
        row = await get_order_by_id(order_id)
        return _to_dict(row)
    except Exception as e:
        logger.error(f"Bazadan buyurtma olishda xato: {e}")
        return None


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()