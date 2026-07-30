import os
import sqlite3
import random
import string
import math
import re
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ============================== CONFIG ==============================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("متغیر محیطی BOT_TOKEN تنظیم نشده!")

ADMIN_ID = 1624053514
DB_PATH = "bot.db"
REQUIRED_CHANNELS = ["@TitanVipofficial1", "@AkhbarJangDollar"]
CARD_NUMBER = "5859-8311-1695-8942"
CARD_OWNER = "مجید عزیزی"
MIN_AGE = 18
MAX_AGE = 50

BOT_USERNAME = "EasyGap_bot"
BOT_LINK = f"https://t.me/{BOT_USERNAME}"

DEFAULT_START_COINS = 10
PROFILE_COMPLETE_BONUS = 10
PHOTO_BONUS = 5
REFERRAL_BONUS = 15

RANDOM_PRICE_MIN = 1
RANDOM_PRICE_MAX = 499

# «شیپ» / اعلام رابطه: کانالی که با رضایت هر دو طرف، خبر رل‌شدن‌ها توش پست می‌شه.
# اگه ست نشه، فقط جایزه‌ی سکه اعمال می‌شه و پستی توی کانال گذاشته نمی‌شه.
SHIP_CHANNEL_ID = os.environ.get("SHIP_CHANNEL_ID", "@EasyGapShip")
RELATIONSHIP_COIN_REWARD = 20

# بعد از «رل زدن» (رابطه‌ی تایید شده)، کاربر باید این تعداد روز صبر کنه تا
# دکمه‌ی «کات کردن» توی پروفایلش فعال بشه. جلوی کات‌های آنی و رل‌بازی الکی
# برای گرفتن سکه رو می‌گیره.
BREAKUP_COOLDOWN_DAYS = 7

SHIP_CHEAT_WARNING_TEXT = (
    "⚠️ <b>قبل از ثبت «رل» این نکته رو جدی بگیر</b>\n"
    "━━━━━━━━━━━━━━━━━\n"
    "استفاده از رل زدن الکی، هماهنگی با یه نفر برای رل زدن فرمایشی و گرفتن سکه‌ی جایزه، یا هر شکلی از "
    "تقلب در این بخش، تخلف محسوب می‌شه و حساب هر دو طرف مسدود خواهد شد.\n"
    "لطفاً با نیت واقعی وارد این مرحله بشید. <b>تقلب نکنید!</b> 🙏"
)

# Local placeholder image shown whenever a user has no profile photo yet.
NO_PHOTO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "no_photo.jpg")

COIN_PACKAGES = [
    (320, 140000),
    (540, 216000),
    (1500, 350000),
    (2000, 700000),
]

VIP_PRICE = 900
VIP_DURATION_DAYS = 90
VIP_BENEFITS_TEXT = (
    "🌟 <b>مزایای اشتراک VIP ایزی گپ</b>\n"
    "━━━━━━━━━━━━━━━━━\n"
    "💬 درخواست چت و جستجوی جنسیتی کاملاً رایگان و نامحدود\n"
    "✉️ پیام دایرکت رایگان و نامحدود\n"
    "🔍 دسترسی به لیست کامل «افراد نزدیک» بدون محدودیت\n"
    "🏅 نشان اختصاصی 🌟VIP کنار نام شما در همه جا\n"
    "⚡️ اولویت نمایش در لیست جستجوها و افراد نزدیک\n"
    "🎯 مشاهده لایک‌کننده‌ها و مخاطبین به‌صورت کامل\n"
    "🛡 پشتیبانی ویژه و اولویت‌دار برای تیکت‌ها\n"
    "━━━━━━━━━━━━━━━━━\n"
    f"💎 قیمت: {VIP_PRICE:,} تومان / ۳ ماهه"
)

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"

def to_en_digits(text: str) -> str:
    if not text:
        return text
    table = {}
    for i, ch in enumerate(PERSIAN_DIGITS):
        table[ch] = str(i)
    for i, ch in enumerate(ARABIC_DIGITS):
        table[ch] = str(i)
    return "".join(table.get(ch, ch) for ch in text)

# Only Persian letters, spaces, half-space (ZWNJ) and Persian digits are accepted for the name.
PERSIAN_NAME_RE = re.compile(r"^[\u0600-\u06FF\u200c\s]+$")

def is_valid_persian_name(text: str) -> bool:
    text = text.strip()
    if not text or len(text) > 30:
        return False
    return bool(PERSIAN_NAME_RE.match(text))

PROVINCES = {
    "تهران": ["تهران", "ری", "شمیرانات", "اسلامشهر", "شهریار", "ملارد", "قدس", "رباط‌کریم",
              "بهارستان", "پاکدشت", "ورامین", "پیشوا", "پردیس", "دماوند", "فیروزکوه", "طالقان"],
    "اصفهان": ["اصفهان", "کاشان", "نجف‌آباد", "خمینی‌شهر", "شاهین‌شهر و میمه", "فلاورجان", "لنجان",
               "مبارکه", "نائین", "اردستان", "نطنز", "گلپایگان", "خوانسار", "فریدن", "فریدون‌شهر",
               "چادگان", "سمیرم", "دهاقان", "شهرضا", "آران و بیدگل", "برخوار", "تیران و کرون"],
    "فارس": ["شیراز", "مرودشت", "جهرم", "کازرون", "فسا", "داراب", "لار", "آباده", "اقلید",
             "استهبان", "فیروزآباد", "لامرد", "ممسنی", "نی‌ریز", "زرین‌دشت", "سپیدان", "خرم‌بید",
             "مهر", "پاسارگاد", "قیر و کارزین", "ارسنجان", "بوانات", "رستم", "خنج", "گراش",
             "فراشبند", "کوار", "زرقان", "سروستان"],
    "خراسان رضوی": ["مشهد", "نیشابور", "سبزوار", "تربت حیدریه", "قوچان", "کاشمر", "تربت جام", "چناران",
                    "درگز", "فریمان", "گناباد", "رشتخوار", "سرخس", "تایباد", "خواف", "بردسکن", "بجستان",
                    "جوین", "جغتای", "خلیل‌آباد", "فیض‌آباد", "زبرخان", "مه‌ولات", "کلات"],
    "آذربایجان شرقی": ["تبریز", "مراغه", "میانه", "مرند", "اهر", "بناب", "سراب", "شبستر", "هشترود",
                       "کلیبر", "جلفا", "ورزقان", "هریس", "بستان‌آباد", "چاراویماق", "عجب‌شیر", "ملکان",
                       "خداآفرین", "اسکو", "آذرشهر", "ترکمانچای"],
    "آذربایجان غربی": ["ارومیه", "خوی", "بوکان", "مهاباد", "میاندوآب", "سلماس", "نقده", "پیرانشهر",
                       "سردشت", "تکاب", "شاهین‌دژ", "چالدران", "ماکو", "پلدشت", "شوط", "چایپاره", "اشنویه"],
    "بوشهر": ["بوشهر", "دشتستان", "تنگستان", "دشتی", "دیر", "کنگان", "عسلویه", "دیلم", "جم", "گناوه"],
    "خوزستان": ["اهواز", "آبادان", "خرمشهر", "دزفول", "بندر ماهشهر", "شوشتر", "شوش", "اندیمشک",
                "ایذه", "مسجدسلیمان", "رامهرمز", "باغ‌ملک", "هویزه", "هندیجان", "امیدیه", "بهبهان",
                "دشت آزادگان", "حمیدیه", "کارون", "لالی", "گتوند", "رامشیر", "آغاجاری"],
    "کرمان": ["کرمان", "رفسنجان", "سیرجان", "بم", "جیرفت", "زرند", "بردسیر", "بافت", "کهنوج",
              "شهربابک", "راور", "انار", "عنبرآباد", "رودبار جنوب", "منوجان", "قلعه‌گنج", "فهرج",
              "ریگان", "ارزوئیه", "نرماشیر", "رابر"],
    "گیلان": ["رشت", "بندرانزلی", "لاهیجان", "لنگرود", "رودسر", "آستارا", "تالش", "صومعه‌سرا",
              "فومن", "شفت", "رودبار", "آستانه اشرفیه", "رضوانشهر", "ماسال", "املش", "سیاهکل"],
    "مازندران": ["ساری", "بابل", "آمل", "قائم‌شهر", "بهشهر", "نور", "نوشهر", "چالوس", "تنکابن",
                 "رامسر", "بابلسر", "جویبار", "فریدونکنار", "نکا", "میاندورود", "سوادکوه", "گلوگاه",
                 "عباس‌آباد"],
    "البرز": ["کرج", "فردیس", "نظرآباد", "ساوجبلاغ", "اشتهارد", "طالقان"],
    "قم": ["قم"],
    "یزد": ["یزد", "میبد", "اردکان", "بافق", "ابرکوه", "تفت", "مهریز", "بهاباد", "خاتم", "اشکذر"],
    "کرمانشاه": ["کرمانشاه", "اسلام‌آباد غرب", "پاوه", "سنقر", "کنگاور", "هرسین", "صحنه",
                 "سرپل ذهاب", "قصرشیرین", "جوانرود", "گیلانغرب", "ثلاث باباجانی", "دالاهو"],
    "هرمزگان": ["بندرعباس", "میناب", "بندرلنگه", "قشم", "رودان", "حاجی‌آباد", "بستک", "پارسیان",
                "بشاگرد", "ابوموسی", "خمیر", "جاسک", "سیریک"],
    "سیستان و بلوچستان": ["زاهدان", "زابل", "ایرانشهر", "چابهار", "سراوان", "خاش", "نیک‌شهر", "کنارک",
                         "سرباز", "دلگان", "میرجاوه", "هیرمند", "زهک", "فنوج", "قصرقند", "مهرستان",
                         "سیب و سوران", "رودبار جنوب"],
    "کردستان": ["سنندج", "سقز", "مریوان", "بانه", "قروه", "بیجار", "کامیاران", "دیواندره", "دهگلان", "سروآباد"],
    "همدان": ["همدان", "ملایر", "نهاوند", "تویسرکان", "اسدآباد", "کبودراهنگ", "رزن", "بهار", "فامنین"],
    "لرستان": ["خرم‌آباد", "بروجرد", "دورود", "الیگودرز", "کوهدشت", "ازنا", "پل‌دختر",
               "رومشکان", "دلفان", "چگنی", "سلسله"],
    "مرکزی": ["اراک", "ساوه", "خمین", "محلات", "دلیجان", "شازند", "تفرش", "آشتیان", "زرندیه", "کمیجان"],
    "قزوین": ["قزوین", "تاکستان", "البرز", "آبیک", "بوئین‌زهرا", "آوج"],
    "زنجان": ["زنجان", "ابهر", "خدابنده", "خرمدره", "ماهنشان", "طارم", "ایجرود"],
    "گلستان": ["گرگان", "گنبدکاووس", "علی‌آباد کتول", "آق‌قلا", "کردکوی", "بندر ترکمن",
               "رامیان", "مینودشت", "کلاله", "آزادشهر", "گالیکش", "مراوه‌تپه", "بندر گز"],
    "اردبیل": ["اردبیل", "مشگین‌شهر", "پارس‌آباد", "گرمی", "خلخال", "بیله‌سوار", "نمین", "نیر", "کوثر", "سرعین"],
    "سمنان": ["سمنان", "شاهرود", "دامغان", "گرمسار", "مهدی‌شهر", "میامی", "سرخه"],
    "چهارمحال و بختیاری": ["شهرکرد", "بروجن", "فارسان", "لردگان", "کوهرنگ", "کیار", "اردل", "بن", "سامان"],
    "کهگیلویه و بویراحمد": ["یاسوج", "گچساران", "دنا", "باشت", "بهمئی", "چرام", "لنده"],
    "ایلام": ["ایلام", "دهلران", "آبدانان", "دره‌شهر", "ایوان", "شیروان و چرداول", "مهران", "بدره", "ملکشاهی", "چوار"],
    "خراسان جنوبی": ["بیرجند", "قائنات", "فردوس", "نهبندان", "سربیشه", "بشرویه", "درمیان", "زیرکوه", "خوسف", "طبس"],
    "خراسان شمالی": ["بجنورد", "شیروان", "اسفراین", "جاجرم", "مانه و سملقان", "فاروج", "رازوجرگلان", "گرمه"],
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================== DATABASE ==============================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username_code TEXT UNIQUE,
            name TEXT,
            gender TEXT,
            age INTEGER,
            province TEXT,
            city TEXT,
            coins INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            photo_file_id TEXT,
            lat REAL,
            lon REAL,
            silent INTEGER DEFAULT 0,
            invited_by INTEGER,
            state TEXT DEFAULT 'new',
            reg_step TEXT,
            in_chat_with INTEGER,
            pending_search TEXT,
            last_seen TEXT,
            joined_at TEXT,
            invite_count INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            is_blocked INTEGER DEFAULT 0,
            block_reason TEXT,
            vip_until TEXT,
            profile_bonus_claimed INTEGER DEFAULT 0,
            same_age_only INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_session TEXT,
            sender_id INTEGER,
            receiver_id INTEGER,
            sender_msg_id INTEGER,
            receiver_msg_id INTEGER,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            coins INTEGER,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            liker_id INTEGER,
            liked_id INTEGER,
            PRIMARY KEY (liker_id, liked_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            owner_id INTEGER,
            contact_id INTEGER,
            PRIMARY KEY (owner_id, contact_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            target_id INTEGER,
            reason TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS notify_requests (
            watcher_id INTEGER,
            target_id INTEGER,
            created_at TEXT,
            PRIMARY KEY (watcher_id, target_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS blocklist (
            owner_id INTEGER,
            blocked_id INTEGER,
            PRIMARY KEY (owner_id, blocked_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            status TEXT DEFAULT 'open',
            admin_response TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS coin_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            delta INTEGER,
            source TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_a INTEGER,
            user_b INTEGER,
            status TEXT DEFAULT 'pending',
            a_phone TEXT,
            b_phone TEXT,
            a_channel_consent TEXT,
            b_channel_consent TEXT,
            posted INTEGER DEFAULT 0,
            created_at TEXT,
            confirmed_at TEXT
        )
    """)
    # Identity table: ties banned accounts to their phone number so a new
    # Telegram account (new user_id) sharing the same verified phone number
    # cannot be used to evade a block.
    c.execute("""
        CREATE TABLE IF NOT EXISTS banned_phones (
            phone TEXT PRIMARY KEY,
            reason TEXT,
            banned_at TEXT
        )
    """)
    # Migrations
    existing_cols = [r["name"] for r in c.execute("PRAGMA table_info(payments)").fetchall()]
    if "type" not in existing_cols:
        c.execute("ALTER TABLE payments ADD COLUMN type TEXT DEFAULT 'coins'")
    if "base_amount" not in existing_cols:
        c.execute("ALTER TABLE payments ADD COLUMN base_amount INTEGER")
    rel_cols = [r["name"] for r in c.execute("PRAGMA table_info(relationships)").fetchall()]
    if "a_phone" not in rel_cols:
        c.execute("ALTER TABLE relationships ADD COLUMN a_phone TEXT")
    if "b_phone" not in rel_cols:
        c.execute("ALTER TABLE relationships ADD COLUMN b_phone TEXT")
    if "ended_at" not in rel_cols:
        c.execute("ALTER TABLE relationships ADD COLUMN ended_at TEXT")
    if "ended_by" not in rel_cols:
        c.execute("ALTER TABLE relationships ADD COLUMN ended_by INTEGER")
    user_cols = [r["name"] for r in c.execute("PRAGMA table_info(users)").fetchall()]
    user_migrations = {
        "is_admin": "INTEGER DEFAULT 0",
        "is_blocked": "INTEGER DEFAULT 0",
        "block_reason": "TEXT",
        "vip_until": "TEXT",
        "profile_bonus_claimed": "INTEGER DEFAULT 0",
        "same_age_only": "INTEGER DEFAULT 0",
        "phone_number": "TEXT",
        "photo_bonus_claimed": "INTEGER DEFAULT 0",
        "fraud_flagged": "INTEGER DEFAULT 0",
    }
    for col, coltype in user_migrations.items():
        if col not in user_cols:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {coltype}")
    conn.commit()
    conn.close()

def gen_code(n=6):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(n))

def get_user(user_id):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row

def get_user_by_code(code):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE username_code=?", (code,)).fetchone()
    conn.close()
    return row

def create_user_if_missing(user_id, invited_by=None):
    if get_user(user_id):
        return
    conn = db()
    code = gen_code()
    while conn.execute("SELECT 1 FROM users WHERE username_code=?", (code,)).fetchone():
        code = gen_code()
    conn.execute(
        """INSERT INTO users (user_id, username_code, coins, invited_by, joined_at, last_seen, reg_step)
           VALUES (?, ?, ?, ?, ?, ?, 'name')""",
        (user_id, code, DEFAULT_START_COINS, invited_by, datetime.now().isoformat(), datetime.now().isoformat()),
    )
    if DEFAULT_START_COINS:
        conn.execute(
            "INSERT INTO coin_ledger (user_id, delta, source, created_at) VALUES (?, ?, ?, ?)",
            (user_id, DEFAULT_START_COINS, "signup_bonus", datetime.now().isoformat()),
        )
    conn.commit()
    conn.close()

def update_user(user_id, **kwargs):
    if not kwargs:
        return
    conn = db()
    keys = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    conn.execute(f"UPDATE users SET {keys} WHERE user_id=?", values)
    conn.commit()
    conn.close()

def touch_last_seen(user_id):
    update_user(user_id, last_seen=datetime.now().isoformat())

async def notify_watchers(user_id, context):
    conn = db()
    watchers = conn.execute("SELECT watcher_id FROM notify_requests WHERE target_id=?", (user_id,)).fetchall()
    if not watchers:
        conn.close()
        return
    conn.execute("DELETE FROM notify_requests WHERE target_id=?", (user_id,))
    conn.commit()
    conn.close()
    target = get_user(user_id)
    for w in watchers:
        try:
            await context.bot.send_message(
                w["watcher_id"],
                f"🔔 کاربر /user_{target['username_code']} هم اکنون آنلاین شد!",
            )
        except Exception:
            pass

def add_coins(user_id, amount, source="other"):
    conn = db()
    conn.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))
    conn.execute(
        "INSERT INTO coin_ledger (user_id, delta, source, created_at) VALUES (?, ?, ?, ?)",
        (user_id, amount, source, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

FRAUD_CHECK_THRESHOLD = 500
LEGIT_COIN_SOURCES = ("purchase", "referral")

async def add_coins_checked(user_id, amount, source, context):
    """Same as add_coins, but for positive amounts it also runs the >500
    unexplained-balance check and alerts the admin (never auto-bans — the
    admin gets a one-tap block button and decides)."""
    add_coins(user_id, amount, source=source)
    if amount > 0:
        await check_coin_fraud(user_id, context)

async def check_coin_fraud(user_id, context):
    row = get_user(user_id)
    if not row or row["fraud_flagged"] or row["coins"] < FRAUD_CHECK_THRESHOLD:
        return
    conn = db()
    q_marks = ",".join("?" * len(LEGIT_COIN_SOURCES))
    legit = conn.execute(
        f"SELECT COALESCE(SUM(delta),0) FROM coin_ledger WHERE user_id=? AND delta>0 AND source IN ({q_marks})",
        (user_id, *LEGIT_COIN_SOURCES),
    ).fetchone()[0]
    breakdown = conn.execute(
        "SELECT source, SUM(delta) as s FROM coin_ledger WHERE user_id=? AND delta>0 GROUP BY source ORDER BY s DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    if legit >= row["coins"]:
        # کل موجودی با خرید/رفرال توجیه می‌شه، چیز مشکوکی نیست.
        return
    update_user(user_id, fraud_flagged=1)
    lines = "\n".join(f"• {b['source']}: {b['s']:+}" for b in breakdown)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 مسدود کردن این کاربر", callback_data=f"admin:blockdo:{user_id}", style="danger")]
    ])
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"🚨 هشدار: موجودی سکه غیرقابل‌توجیه\n"
            f"👤 کاربر: /user_{row['username_code']} (آیدی: {user_id})\n"
            f"💰 موجودی فعلی: {row['coins']}\n"
            f"💳 جمع سکه‌ی حاصل از خرید+رفرال: {legit}\n\n"
            f"📊 ریز منابع سکه:\n{lines}\n\n"
            "این کاربر به بیش از ۵۰۰ سکه رسیده بدون اینکه همه‌ش از خرید یا رفرال باشه. "
            "بررسی کن و اگه تشخیص تقلب دادی، با دکمه‌ی زیر مسدودش کن.",
            reply_markup=kb,
        )
    except Exception:
        logger.exception("Failed to notify admin about possible coin fraud for user_id=%s", user_id)

def is_registered(row):
    # Identity is anchored to the permanent Telegram user_id (primary key),
    # not to a phone number — no phone verification step is required.
    return bool(
        row
        and row["reg_step"] is None
        and row["name"]
        and row["gender"]
        and row["age"]
        and row["province"]
        and row["city"]
    )

def is_admin_user(user_id):
    if user_id == ADMIN_ID:
        return True
    row = get_user(user_id)
    return bool(row and row["is_admin"])

def is_vip(row):
    if not row or not row["vip_until"]:
        return False
    try:
        return datetime.fromisoformat(row["vip_until"]) > datetime.now()
    except Exception:
        return False

def grant_vip(user_id, days=VIP_DURATION_DAYS):
    row = get_user(user_id)
    base = datetime.now()
    if row and row["vip_until"]:
        try:
            existing = datetime.fromisoformat(row["vip_until"])
            if existing > base:
                base = existing
        except Exception:
            pass
    new_until = base + timedelta(days=days)
    update_user(user_id, vip_until=new_until.isoformat())
    return new_until

def vip_badge(row):
    return " 🌟" if is_vip(row) else ""

def resolve_target_user(text: str):
    text = to_en_digits(text.strip())
    if text.startswith("@"):
        return None
    if text.startswith("/user_"):
        return get_user_by_code(text.split("/user_", 1)[1])
    if text.startswith("user_"):
        return get_user_by_code(text.split("user_", 1)[1])
    if text.lstrip("-").isdigit():
        return get_user(int(text))
    return None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_active_relationship(user_id):
    """آخرین «رل» تاییدشده و کات‌نشده‌ی این کاربر رو برمی‌گردونه، یا None اگه
    رابطه‌ی فعالی نداشته باشه."""
    conn = db()
    rel = conn.execute(
        "SELECT * FROM relationships WHERE status='confirmed' AND (user_a=? OR user_b=?) "
        "ORDER BY confirmed_at DESC LIMIT 1",
        (user_id, user_id),
    ).fetchone()
    conn.close()
    return rel

def relationship_partner_id(rel, user_id):
    return rel["user_b"] if rel["user_a"] == user_id else rel["user_a"]

def breakup_ready_at(rel):
    confirmed = datetime.fromisoformat(rel["confirmed_at"])
    return confirmed + timedelta(days=BREAKUP_COOLDOWN_DAYS)

# ============================== IDENTITY / PHONE VERIFICATION ==============================

def ban_phone_for_user(user_id, reason=None):
    """Record a user's verified phone number as permanently banned so a new
    Telegram account cannot re-register with the same number."""
    row = get_user(user_id)
    if not row or not row["phone_number"]:
        return
    conn = db()
    conn.execute(
        "INSERT OR REPLACE INTO banned_phones (phone, reason, banned_at) VALUES (?,?,?)",
        (row["phone_number"], reason, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

def phone_is_banned(phone):
    conn = db()
    row = conn.execute("SELECT * FROM banned_phones WHERE phone=?", (phone,)).fetchone()
    conn.close()
    return row

def phone_used_by_blocked_account(phone, exclude_user_id):
    conn = db()
    row = conn.execute(
        "SELECT * FROM users WHERE phone_number=? AND user_id!=? AND is_blocked=1",
        (phone, exclude_user_id),
    ).fetchone()
    conn.close()
    return row

# ============================== PROFILE COMPLETION NUDGE ==============================

def profile_completion_missing(row):
    missing = []
    if not row["name"]:
        missing.append("نام")
    if not row["photo_file_id"]:
        missing.append("عکس")
    return missing

def profile_completion_nudge_text(row):
    missing = profile_completion_missing(row)
    if not missing:
        return None
    steps = len(missing)
    missing_text = " و ".join(missing)
    return (
        f"🔔 فقط {steps} قدم تا تکمیل پروفایل !\n\n"
        f"اطلاعات تکمیل نشده ی شما : {missing_text}\n\n"
        f"پروفایل خود را تکمیل کنید👇 و {PHOTO_BONUS} سکه دریافت کنید ."
    )

def profile_completion_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✨📝 تکمیل پروفایل 📝✨", callback_data="profile_complete_start", style="success")]
    ])

async def maybe_send_profile_nudge(update: Update, context: ContextTypes.DEFAULT_TYPE, row):
    text = profile_completion_nudge_text(row)
    if not text:
        return
    await context.bot.send_message(row["user_id"], text, reply_markup=profile_completion_keyboard())

NAME_RULES_TEXT = (
    "⚠️ توجه کنید : با توجه به این که پروفایل کاربران به صورت عمومی قابل مشاهده است ، "
    "در صورت رعایت نکردن قوانین زیر حساب کاربری شما بصورت دائمی مسدود خواهد شد.\n\n"
    "1️⃣ هرگونه محتوای غیر اخلاقی یا توهین آمیز در پروفایل ( عکس یا متن )\n"
    "2️⃣ پخش شماره موبایل یا اطلاعات شخصی دیگران\n"
    "3️⃣ تبلیغات کانال ، ربات و یا سایت\n\n"
    "❓ لطفا نام خود را به صورت متن ارسال کنید .\n👇👇👇"
)

async def send_name_prompt(user_id, context, edit_message=None):
    update_user(user_id, state="await_name")
    if edit_message is not None:
        await edit_message.edit_text(NAME_RULES_TEXT, reply_markup=back_keyboard("back:main"))
    else:
        await context.bot.send_message(user_id, NAME_RULES_TEXT, reply_markup=back_keyboard("back:main"))

async def send_photo_prompt(user_id, context, edit_message=None):
    text = "📷 لطفا عکس پروفایل جدید خودت رو ارسال کن (فقط عکس قابل قبوله):"
    update_user(user_id, state="await_photo")
    if edit_message is not None:
        await edit_message.edit_text(text, reply_markup=back_keyboard("back:main"))
    else:
        await context.bot.send_message(user_id, text, reply_markup=back_keyboard("back:main"))

# ============================== KEYBOARDS ==============================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("به یه ناشناس وصلم کن!🌠")],
        [KeyboardButton("افراد نزدیک📌"), KeyboardButton("جستوجوی کاربران🔍")],
        [KeyboardButton("سکه🪙"), KeyboardButton("🌟 اشتراک VIP")],
        [KeyboardButton("پروفایل👤"), KeyboardButton("راهنما📒")],
        [KeyboardButton("معرفی به دوستان ( سکه ی رایگان🪙✅ )")],
        [KeyboardButton("لینک ناشناس من")],
    ],
    resize_keyboard=True,
)

AGE_BUTTONS = [str(a) for a in range(MIN_AGE, MAX_AGE + 1)]

def age_keyboard():
    rows = []
    row = []
    for i, a in enumerate(AGE_BUTTONS, 1):
        row.append(InlineKeyboardButton(a, callback_data=f"age:{a}"))
        if i % 5 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def gender_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🙋‍♂️ پسر", callback_data="gender:پسر"),
         InlineKeyboardButton("🙋‍♀️ دختر", callback_data="gender:دختر")]
    ])

def province_keyboard(prefix="province"):
    rows = []
    row = []
    for i, p in enumerate(PROVINCES.keys(), 1):
        row.append(InlineKeyboardButton(p, callback_data=f"{prefix}:{p}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def city_keyboard(province, prefix="city"):
    rows = []
    row = []
    for i, c in enumerate(PROVINCES.get(province, []), 1):
        row.append(InlineKeyboardButton(c, callback_data=f"{prefix}:{c}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def membership_keyboard():
    rows = [[InlineKeyboardButton(f"👉 {ch}", url=f"https://t.me/{ch.lstrip('@')}")] for ch in REQUIRED_CHANNELS]
    rows.append([InlineKeyboardButton("بررسی عضویت و فعال‌سازی🔮", callback_data="check_membership", style="success")])
    return InlineKeyboardMarkup(rows)

def coin_shop_keyboard():
    rows = [[InlineKeyboardButton("🎁 معرفی به دوستان", callback_data="show_invite", style="primary")]]
    for coins, price in COIN_PACKAGES:
        rows.append([InlineKeyboardButton(f"خرید {coins} سکه: {price:,} تومان", callback_data=f"buy:{coins}:{price}", style="primary")])
    return InlineKeyboardMarkup(rows)

FOOTER = "🔒 امن  •  ⚡️ سریع  •  ♾️ نامحدود  •  🕶 خصوصی"

def back_keyboard(target="back:main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=target)]])

def phone_request_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 تایید هویت با شماره موبایل", request_contact=True)]],
        resize_keyboard=True,
    )

# ============================== MEMBERSHIP CHECK ==============================

async def is_member_of_all(context, user_id):
    for ch in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception:
            return False
    return True

# ============================== START / REGISTRATION ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    invited_by = None
    if context.args and context.args[0].startswith("inv_"):
        code = context.args[0][4:]
        inviter = get_user_by_code(code)
        if inviter and inviter["user_id"] != user_id:
            invited_by = inviter["user_id"]

    is_new = get_user(user_id) is None
    create_user_if_missing(user_id, invited_by=invited_by)
    row = get_user(user_id)

    if row["is_blocked"]:
        await send_block_message(update, context, row)
        return

    if is_new and invited_by:
        await add_coins_checked(invited_by, REFERRAL_BONUS, "referral", context)
        update_user(invited_by, invite_count=(get_user(invited_by)["invite_count"] or 0) + 1)
        try:
            await context.bot.send_message(invited_by,
                f"🎉 یک نفر با لینک⚡️ دعوت شما وارد《 ایزی گپ 》شد و {REFERRAL_BONUS} سکه رایگان به حسابت اضافه شد!"
            )
        except Exception:
            pass

    if is_new:
        try:
            await context.bot.send_message(user_id,
                f"🎁 {DEFAULT_START_COINS} سکه هدیه‌ی خوش‌آمدگویی به حساب شما اضافه شد!"
            )
        except Exception:
            pass

    if is_registered(row):
        touch_last_seen(user_id)
        ok = await is_member_of_all(context, user_id)
        if not ok:
            await send_membership_gate(update, context)
            return
        await update.message.reply_text(
            f"✨ خوش برگشتی{vip_badge(row)}!\n\n"
            "💫 خب، امروز چیکار می‌تونم برات انجام بدم؟\n"
            "از منوی پایین👇 یکی رو انتخاب کن\n\n"
            f"┄┄┄┄┄┄┄┄┄┄\n{FOOTER}",
            reply_markup=MAIN_MENU,
        )
        return

    step = row["reg_step"] or "name"
    if step == "name":
        await update.message.reply_text(
            "❓ لطفا نام خود را به فارسی وارد کنید ( فقط حروف فارسی قابل قبول است ) :"
        )
    elif step == "gender":
        await update.message.reply_text("نام شما ثبت شد\n\n❓ لطفا جنسیت خود را انتخاب کنید 👇", reply_markup=gender_keyboard())
    elif step == "age":
        await ask_age(update.message, context)
    elif step == "province":
        await update.message.reply_text("سن شما ثبت شد\n\n• استانت رو از لیست پایین 👇انتخاب کن", reply_markup=province_keyboard())
    elif step == "city":
        await update.message.reply_text(
            "استان شما ثبت شد ، خب حالا فقط کافیه شهر خودت رو انتخاب کنی\n\n"
            "• شهرستانت رو از لیست پایین 👇انتخاب کن",
            reply_markup=city_keyboard(row["province"]),
        )

async def ask_age(message_target, context):
    await message_target.reply_text(
        "• سنت رو از لیست پایین 👇انتخاب کن یا خودت تایپ کن:", reply_markup=age_keyboard()
    )

async def ask_phone(message_target, context):
    await message_target.reply_text(
        "شهر شما ثبت شد ✅\n\n"
        "🔐 برای تایید هویت و جلوگیری از سو استفاده، در آخرین قدم لازمه شماره موبایلت رو "
        "با دکمه پایین👇 برامون ارسال کنی. این شماره پیش کسی نمایش داده نمیشه.\n\n"
        "⚠️ هر شماره موبایل فقط مجاز به داشتن یک حساب کاربری در ایزی گپ است.",
        reply_markup=phone_request_keyboard(),
    )

async def send_membership_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (f"({user_id}) عزیز برای استفاده از ربات ابتدا باید در کانال(های) زیر عضو بشی 👇\n\n"
            + "\n".join(f"👉{ch}" for ch in REQUIRED_CHANNELS)
            + "\n\nبعد از عضویت، دکمه «بررسی عضویت و فعال‌سازی🔮» را بزن\n\nاز منوی پایین👇🏻 انتخاب کن:")
    if update.message:
        await update.message.reply_text(text, reply_markup=membership_keyboard())
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=membership_keyboard())

async def registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    row = get_user(user_id)
    data = query.data

    if data.startswith("gender:") and row["reg_step"] == "gender":
        gender = data.split(":", 1)[1]
        update_user(user_id, gender=gender, reg_step="age")
        await query.message.edit_text("جنسیت شما ثبت شد")
        await ask_age(query.message, context)
        await query.answer()
        return

    if data.startswith("age:"):
        age = int(data.split(":", 1)[1])
        update_user(user_id, age=age, reg_step="province")
        await query.message.edit_text("سن شما ثبت شد\n\n• استانت رو از لیست پایین 👇انتخاب کن", reply_markup=province_keyboard())
        await query.answer()
        return

    if data.startswith("province:") and row["reg_step"] == "province":
        province = data.split(":", 1)[1]
        update_user(user_id, province=province, reg_step="city")
        await query.message.edit_text(
            "استان شما ثبت شد ، خب حالا فقط کافیه شهر خودت رو انتخاب کنی\n\n"
            "• شهرستانت رو از لیست پایین 👇انتخاب کن",
            reply_markup=city_keyboard(province),
        )
        await query.answer()
        return

    if data.startswith("city:") and row["reg_step"] == "city":
        city = data.split(":", 1)[1]
        update_user(user_id, city=city, reg_step=None)
        await query.message.edit_text("✅ شهر شما ثبت شد.")
        await finish_registration(update, context, user_id)
        await query.answer()
        return
    await query.answer()

async def finish_registration(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    row = get_user(user_id)
    if not row["profile_bonus_claimed"]:
        await add_coins_checked(user_id, PROFILE_COMPLETE_BONUS, "profile_bonus", context)
        update_user(user_id, profile_bonus_claimed=1)
        bonus_line = f"\n\n🎁 {PROFILE_COMPLETE_BONUS} سکه هدیه‌ی تکمیل پروفایل به حسابت اضافه شد!"
    else:
        bonus_line = ""
    await context.bot.send_message(
        user_id,
        "✅ اطلاعات شما ثبت شد و هویتت تایید شد." + bonus_line + "\n\n"
        "به خانواده بزرگ《 ایزی گپ 🤖》خوش اومدی! بهت توصیه می‌کنم اول از همه با لمس کردن "
        "《🤔 راهنما》 با ربات آشنا شی!",
        reply_markup=MAIN_MENU,
    )
    ok = await is_member_of_all(context, user_id)
    if not ok:
        gate_text = (f"({user_id}) عزیز برای استفاده از ربات ابتدا باید در کانال(های) زیر عضو بشی 👇\n\n"
                     + "\n".join(f"👉{ch}" for ch in REQUIRED_CHANNELS)
                     + "\n\nبعد از عضویت، دکمه «بررسی عضویت و فعال‌سازی🔮» را بزن\n\nاز منوی پایین👇🏻 انتخاب کن:")
        await context.bot.send_message(user_id, gate_text, reply_markup=membership_keyboard())
    else:
        row = get_user(user_id)
        await maybe_send_profile_nudge(update, context, row)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = get_user(user_id)
    contact = update.message.contact
    if row is None:
        await start(update, context)
        return
    ship_mode = row["state"] == "ship_wait_phone" and row["pending_search"] and row["pending_search"].startswith("ship:")
    if not contact or contact.user_id != user_id:
        await update.message.reply_text(
            "⚠️ لطفا فقط شماره موبایل خودت رو با دکمه‌ی پایین ارسال کن، نه شماره‌ی شخص دیگه رو.",
            reply_markup=ship_phone_keyboard() if ship_mode else phone_request_keyboard(),
        )
        return
    if ship_mode:
        await handle_ship_phone(update, context, row, contact)
        return
    if row["reg_step"] != "phone":
        return

    phone = to_en_digits(contact.phone_number.lstrip("+"))

    banned = phone_is_banned(phone)
    also_blocked = phone_used_by_blocked_account(phone, user_id)
    if banned or also_blocked:
        reason = (banned["reason"] if banned else None) or "این شماره موبایل قبلاً در ایزی گپ مسدود شده است."
        update_user(user_id, phone_number=phone, reg_step=None, is_blocked=1, block_reason=reason)
        await update.message.reply_text(
            "⛔️ اکانت شما به دلیل استفاده از شماره موبایلی که قبلاً مسدود شده، مسدود شد.",
            reply_markup=None,
        )
        await send_block_message(update, context, get_user(user_id))
        return

    update_user(user_id, phone_number=phone, reg_step=None)
    await finish_registration(update, context, user_id)

async def registration_text_guard(update: Update, context: ContextTypes.DEFAULT_TYPE, row):
    text = update.message.text.strip()
    step = row["reg_step"]
    if step == "name":
        if is_valid_persian_name(text):
            update_user(update.effective_user.id, name=text, reg_step="gender")
            await update.message.reply_text("نام شما ثبت شد\n\n❓ لطفا جنسیت خود را انتخاب کنید 👇", reply_markup=gender_keyboard())
        else:
            await update.message.reply_text("⚠️ لطفا نام خود را فقط با حروف فارسی ارسال کن (بدون عدد، ایموجی یا حروف انگلیسی).")
        return
    if step == "age":
        if text.isdigit() and MIN_AGE <= int(text) <= MAX_AGE:
            update_user(update.effective_user.id, age=int(text), reg_step="province")
            await update.message.reply_text("سن شما ثبت شد\n\n• استانت رو از لیست پایین 👇انتخاب کن", reply_markup=province_keyboard())
        else:
            await update.message.reply_text(f"⚠️ لطفا فقط عدد بین {MIN_AGE} تا {MAX_AGE} وارد کن یا از دکمه‌های بالا انتخاب کن.")
        return
    if step == "phone":
        await update.message.reply_text(
            "🔐 لطفا فقط با لمس دکمه پایین شماره موبایلت رو ارسال کن:",
            reply_markup=phone_request_keyboard(),
        )
        return
    await update.message.reply_text("لطفا از دکمه‌های بالا برای تکمیل ثبت‌نام استفاده کن 👆")

async def send_block_message(update: Update, context: ContextTypes.DEFAULT_TYPE, row):
    text = ("‼️ متاسفانه اکانت شما به دلیل گزارش کاربران\n"
            "و عدم رعایت قوانین توسط پشتیبانی ربات مسدود شده است\n\n"
            f"🆔 /user_{row['username_code']}\n")
    if row["block_reason"]:
        text += f"\n📝 دلیل مسدودی: {row['block_reason']}\n"
    text += ("\nدر صورتی که قوانین ربات را رعایت کرده‌اید و به‌ناحق مسدود شده‌اید، "
             "می‌توانید از دکمه‌ی زیر برای پشتیبانی تیکت ارسال کنید و درخواست بررسی مجدد بدهید 👇")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📝 ارسال تیکت اعتراض", callback_data="ticket:new", style="primary")]])
    if update.message:
        await update.message.reply_text(text, reply_markup=kb)
    elif update.callback_query:
        await context.bot.send_message(update.effective_user.id, text, reply_markup=kb)

async def ticket_new_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    conn = db()
    open_ticket = conn.execute("SELECT 1 FROM tickets WHERE user_id=? AND status='open'", (user_id,)).fetchone()
    conn.close()
    if open_ticket:
        await query.answer("⏳ شما همین الان یک تیکت باز دارید، منتظر بررسی ادمین بمانید.", show_alert=True)
        return
    update_user(user_id, state="await_ticket_text")
    await context.bot.send_message(user_id,
        "📝 لطفاً توضیح خودت درباره‌ی این مسدودی رو در یک پیام متنی بنویس و بفرست تا برای ادمین ارسال بشه:"
    )
    await query.answer()

async def handle_ticket_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    user_id = update.effective_user.id
    row = get_user(user_id)
    update_user(user_id, state=None)
    conn = db()
    cur = conn.execute(
        "INSERT INTO tickets (user_id, text, status, created_at) VALUES (?,?,?,?)",
        (user_id, text, "open", datetime.now().isoformat()),
    )
    ticket_id = cur.lastrowid
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ تیکت شما با موفقیت ثبت شد و به‌زودی توسط پشتیبانی بررسی می‌شود.")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ پاسخ و رفع مسدودی", callback_data=f"tkok:{ticket_id}", style="success"),
         InlineKeyboardButton("❌ رد تیکت", callback_data=f"tkno:{ticket_id}", style="danger")]
    ])
    admin_targets = get_admin_ids()
    for admin_id in admin_targets:
        try:
            await context.bot.send_message(admin_id,
                f"📩 تیکت جدید #{ticket_id}\n👤 کاربر: {user_id} (/user_{row['username_code']})\n\n📝 متن:\n{text}",
                reply_markup=kb,
            )
        except Exception:
            pass

def get_admin_ids():
    conn = db()
    rows = conn.execute("SELECT user_id FROM users WHERE is_admin=1").fetchall()
    conn.close()
    ids = {r["user_id"] for r in rows}
    ids.add(ADMIN_ID)
    return list(ids)

async def ticket_decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin_user(update.effective_user.id):
        await query.answer("فقط ادمین!", show_alert=True)
        return
    action, ticket_id = query.data.split(":")
    ticket_id = int(ticket_id)
    conn = db()
    ticket = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if not ticket:
        conn.close()
        await query.answer("تیکت یافت نشد.", show_alert=True)
        return
    if action == "tkok":
        conn.execute("UPDATE tickets SET status='resolved' WHERE id=?", (ticket_id,))
        conn.commit()
        update_user(ticket["user_id"], is_blocked=0, block_reason=None)
        await context.bot.send_message(ticket["user_id"],
            "✅ تیکت شما بررسی شد و اکانت شما از حالت مسدودی خارج شد. خوش برگشتی به《 ایزی گپ 》!",
            reply_markup=MAIN_MENU,
        )
        await query.message.edit_text(query.message.text + "\n\n✅ تیکت پذیرفته و کاربر آنبلاک شد.")
    else:
        conn.execute("UPDATE tickets SET status='rejected' WHERE id=?", (ticket_id,))
        conn.commit()
        await context.bot.send_message(ticket["user_id"],
            "❌ درخواست تجدیدنظر شما بررسی شد و رد شد. مسدودی همچنان فعال است."
        )
        await query.message.edit_text(query.message.text + "\n\n❌ تیکت رد شد.")
    conn.close()
    await query.answer()

async def check_membership_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    ok = await is_member_of_all(context, user_id)
    if ok:
        await query.message.delete()
        await context.bot.send_message(user_id, "خب حالا چه کاری برات انجام بدم؟", reply_markup=MAIN_MENU)
    else:
        await query.answer("هنوز در همه کانال‌ها عضو نشدی!", show_alert=True)

# ============================== GATE WRAPPER ==============================

async def require_ready(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    row = get_user(user_id)
    if row is None:
        await start(update, context)
        return False
    if row["is_blocked"]:
        await send_block_message(update, context, row)
        return False
    if not is_registered(row):
        if update.message and update.message.text and not update.message.text.startswith("/"):
            await registration_text_guard(update, context, row)
        else:
            await start(update, context)
        return False
    ok = await is_member_of_all(context, user_id)
    if not ok:
        await send_membership_gate(update, context)
        return False
    touch_last_seen(user_id)
    await notify_watchers(user_id, context)
    return True

# ============================== PROFILE ==============================

def profile_text(row, viewer_is_self=True):
    online = "هم اکنون 👀 آنلایـــن"
    lines = [
        f"• نام: {row['name'] or '—'}{vip_badge(row)}",
        f"• جنسیت: {row['gender']}",
        f"• استان: {row['province']}",
        f"• شهر: {row['city']}",
        f"• سن: {row['age']}",
    ]
    if viewer_is_self:
        lines.append(f"\n💰 سکه: {row['coins']}")
        lines.append(f"• تعداد لایک ها: {row['likes']}")
        if is_vip(row):
            until = datetime.fromisoformat(row["vip_until"]).strftime("%Y-%m-%d")
            lines.append(f"🌟 اشتراک VIP فعال تا {until}")
        lines.append(f"\n{online} (🗣)")
        lines.append(f"\n🆔 آیدی : /user_{row['username_code']}")
        lines.append("\nتنظیم حالت سایلنت : /silent")
    return "\n".join(lines)

def profile_keyboard(row=None):
    rows = [
        [InlineKeyboardButton("📍 مشاهده موقعیت GPS من", callback_data="my_gps")],
        [InlineKeyboardButton("❤️ مشاهده لایک‌کننده‌ها", callback_data="my_likers")],
        [InlineKeyboardButton("📇 لیست مخاطبین", callback_data="my_contacts")],
        [InlineKeyboardButton("✏️ ویرایش پروفایل", callback_data="edit_profile")],
        [InlineKeyboardButton("⚙️ تنظیمات پیشرفته", callback_data="adv_settings")],
    ]
    if row is not None:
        rel = get_active_relationship(row["user_id"])
        if rel:
            rows.append([InlineKeyboardButton("💔 کات کردن", callback_data=f"cutrel:{rel['id']}", style="danger")])
    return InlineKeyboardMarkup(rows)

def advanced_settings_keyboard(row):
    same_age_label = "🔴 غیرفعال کردن جستجوی هم‌سن" if row["same_age_only"] else "🎂 فعال کردن جستجوی هم‌سن"
    silent_label = "🔔 غیرفعال کردن حالت سایلنت" if row["silent"] else "🔕 فعال کردن حالت سایلنت"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(same_age_label, callback_data="adv:sameage")],
        [InlineKeyboardButton(silent_label, callback_data="adv:silent")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back:profile")],
    ])

def contact_profile_keyboard(target_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن به مخاطبین", callback_data=f"addcontact:{target_id}", style="success"),
         InlineKeyboardButton("➖ حذف از مخاطبین", callback_data=f"removecontact:{target_id}", style="danger")],
        [InlineKeyboardButton("🔔 اطلاع بده وقتی آنلاین شد (1 سکه)", callback_data=f"notifyon:{target_id}")],
        [InlineKeyboardButton("🚫 گزارش کاربر", callback_data=f"report:{target_id}", style="danger")],
    ])

def full_profile_keyboard(target_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 پیام دایرکت", callback_data=f"dm:{target_id}"),
         InlineKeyboardButton("💬 درخواست چت", callback_data=f"reqchat:{target_id}")],
        [InlineKeyboardButton("🔒 بلاک کردن کاربر", callback_data=f"pblock:{target_id}", style="danger"),
         InlineKeyboardButton("🚫 گزارش کاربر", callback_data=f"report:{target_id}", style="danger")],
        [InlineKeyboardButton("➕ افزودن به مخاطبین", callback_data=f"addcontact:{target_id}", style="success"),
         InlineKeyboardButton("➖ حذف از مخاطبین", callback_data=f"removecontact:{target_id}", style="danger")],
    ])

async def send_profile_photo(bot, chat_id, row, caption, reply_markup=None):
    """Send the user's profile photo, or the local 'no photo' placeholder if
    they haven't uploaded one yet. Falls back to a text-only message if the
    photo can't be sent for any reason, so a missing/broken image file never
    silently breaks the profile button (or any other caller)."""
    try:
        if row["photo_file_id"]:
            await bot.send_photo(chat_id, row["photo_file_id"], caption=caption, reply_markup=reply_markup)
            return
        if os.path.exists(NO_PHOTO_PATH):
            with open(NO_PHOTO_PATH, "rb") as f:
                await bot.send_photo(chat_id, f, caption=caption, reply_markup=reply_markup)
            return
        logger.warning("NO_PHOTO_PATH missing at %s; sending text-only profile.", NO_PHOTO_PATH)
    except Exception:
        logger.exception("send_profile_photo failed for chat_id=%s; falling back to text.", chat_id)
    await bot.send_message(chat_id, caption, reply_markup=reply_markup)

async def show_full_profile(update, context, viewer_id, target):
    viewer = get_user(viewer_id)
    text_lines = [
        f"• نام: {target['name'] or '—'}{vip_badge(target)}",
        f"• جنسیت: {target['gender']}",
        f"• استان: {target['province']}",
        f"• شهر: {target['city']}",
        f"• سن: {target['age']}",
        f"\n❤️ تعداد لایک‌ها: {target['likes']}",
        f"\n🆔 آیدی : /user_{target['username_code']}",
    ]
    if viewer and viewer["lat"] is not None and target["lat"] is not None:
        d = haversine(viewer["lat"], viewer["lon"], target["lat"], target["lon"])
        text_lines.append(f"\n🏁 فاصله از شما: {d:.0f} کیلومتر")
    text = "\n".join(text_lines)
    kb = full_profile_keyboard(target["user_id"])
    await send_profile_photo(context.bot, viewer_id, target, text, kb)

def edit_profile_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚻 تغییر جنسیت", callback_data="editf:gender")],
        [InlineKeyboardButton("📝 تغییر نام", callback_data="editf:name")],
        [InlineKeyboardButton("🎂 تغییر سن", callback_data="editf:age")],
        [InlineKeyboardButton("🏙 تغییر شهر", callback_data="editf:city")],
        [InlineKeyboardButton("🖼 تغییر عکس پروفایل", callback_data="editf:photo")],
        [InlineKeyboardButton("📍 تغییر موقعیت GPS", callback_data="editf:gps")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back:profile")],
    ])

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    row = get_user(update.effective_user.id)
    text = profile_text(row)
    await send_profile_photo(context.bot, update.effective_user.id, row, text, profile_keyboard(row))

async def profile_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    row = get_user(user_id)
    data = query.data

    if data == "edit_profile":
        await query.message.edit_reply_markup(reply_markup=edit_profile_keyboard())
        await query.answer()
        return

    if data == "adv_settings":
        try:
            await query.message.edit_caption(
                caption="⚙️ تنظیمات پیشرفته — یکی از گزینه‌های زیر رو تغییر بده 👇",
                reply_markup=advanced_settings_keyboard(row),
            )
        except Exception:
            await query.message.edit_text(
                "⚙️ تنظیمات پیشرفته — یکی از گزینه‌های زیر رو تغییر بده 👇",
                reply_markup=advanced_settings_keyboard(row),
            )
        await query.answer()
        return

    if data == "adv:sameage":
        new_val = 0 if row["same_age_only"] else 1
        update_user(user_id, same_age_only=new_val)
        row = get_user(user_id)
        await query.message.edit_reply_markup(reply_markup=advanced_settings_keyboard(row))
        await query.answer("🎂 جستجوی هم‌سن فعال شد." if new_val else "📴 جستجوی هم‌سن غیرفعال شد.")
        return

    if data == "adv:silent":
        new_val = 0 if row["silent"] else 1
        update_user(user_id, silent=new_val)
        row = get_user(user_id)
        await query.message.edit_reply_markup(reply_markup=advanced_settings_keyboard(row))
        await query.answer("🔕 حالت سایلنت فعال شد." if new_val else "🔔 حالت سایلنت غیرفعال شد.")
        return
    if data == "back:profile":
        await query.message.edit_reply_markup(reply_markup=profile_keyboard(row))
        await query.answer()
        return
    if data == "my_gps":
        if row["lat"] is None:
            await query.answer("موقعیتی ثبت نکردی!", show_alert=True)
        else:
            await context.bot.send_location(user_id, row["lat"], row["lon"])
            await query.answer()
        return
    if data == "my_likers":
        conn = db()
        n = conn.execute("SELECT COUNT(*) c FROM likes WHERE liked_id=?", (user_id,)).fetchone()["c"]
        conn.close()
        await query.answer(f"تعداد لایک‌کننده‌ها: {n}", show_alert=True)
        return
    if data == "my_contacts":
        conn = db()
        rows = conn.execute("SELECT contact_id FROM contacts WHERE owner_id=?", (user_id,)).fetchall()
        conn.close()
        if not rows:
            await query.answer("لیست مخاطبینت خالیه!", show_alert=True)
        else:
            names = []
            kb_rows = []
            for r in rows[:20]:
                u = get_user(r["contact_id"])
                if u:
                    names.append(f"{u['name'] or '—'} (/user_{u['username_code']})")
                    kb_rows.append([InlineKeyboardButton(
                        f"➖ حذف {u['name'] or '—'}", callback_data=f"removecontact:{u['user_id']}", style="danger"
                    )])
            await query.message.reply_text(
                "👥 مخاطبین شما:\n\n" + "\n".join(names),
                reply_markup=InlineKeyboardMarkup(kb_rows) if kb_rows else None,
            )
        await query.answer()
        return
    if data.startswith("editf:"):
        field = data.split(":", 1)[1]
        if field == "gender":
            await query.message.edit_text("جنسیت جدید رو انتخاب کن 👇", reply_markup=gender_keyboard())
            update_user(user_id, pending_search="editgender")
        elif field == "name":
            await send_name_prompt(user_id, context, edit_message=query.message)
        elif field == "age":
            await query.message.edit_text("سن جدید رو انتخاب کن یا تایپ کن 👇", reply_markup=age_keyboard())
            update_user(user_id, state="await_age_edit")
        elif field == "city":
            await query.message.edit_text("شهر جدید رو انتخاب کن 👇", reply_markup=city_keyboard(row["province"], prefix="cityedit"))
        elif field == "photo":
            await send_photo_prompt(user_id, context, edit_message=query.message)
        elif field == "gps":
            await send_gps_request(update, context, edit=True)
        await query.answer()
        return
    if data.startswith("cityedit:"):
        city = data.split(":", 1)[1]
        update_user(user_id, city=city)
        await query.message.edit_text("✅ شهر شما با موفقیت تغییر کرد.", reply_markup=back_keyboard("back:profile"))
        await query.answer()
        return
    if data == "profile_complete_start":
        missing = profile_completion_missing(row)
        if "نام" in missing:
            await send_name_prompt(user_id, context, edit_message=query.message)
        elif "عکس" in missing:
            await send_photo_prompt(user_id, context, edit_message=query.message)
        else:
            await query.answer("✅ پروفایل شما از قبل کامل است!", show_alert=True)
        await query.answer()
        return
    if data == "back:main":
        await query.message.delete()
        await context.bot.send_message(user_id, "خب حالا چه کاری برات انجام بدم؟", reply_markup=MAIN_MENU)
        await query.answer()
        return

async def editgender_cb_wrap(update, context):
    query = update.callback_query
    row = get_user(update.effective_user.id)
    if row and row["pending_search"] == "editgender" and query.data.startswith("gender:"):
        gender = query.data.split(":", 1)[1]
        update_user(update.effective_user.id, gender=gender, pending_search=None)
        await query.message.edit_text("✅ جنسیت شما تغییر کرد.", reply_markup=back_keyboard("back:profile"))
        await query.answer()
        return True
    return False

# ============================== GPS ==============================

async def send_gps_request(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    text = ("⚠️ هنگام ارسال موقعیت مکانی مطمعن شوید GPS موبایل شما روشن است.\n\n"
            "✅ کسی قادر به دیدن موقعیت مکانی شما در ربات نخواهد بود و فقط برای تخمین فاصله و "
            "یافتن افراد نزدیک کاربرد خواهد داشت\n\n"
            "❓موقعیت GPS خود را ارسال کنید👇")
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📍 ارسال موقعیت GPS من", request_location=True)], ["بازگشت"]],
        resize_keyboard=True,
    )
    user_id = update.effective_user.id
    if edit and update.callback_query:
        await update.callback_query.message.delete()
    await context.bot.send_message(user_id, text, reply_markup=kb)

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    user_id = update.effective_user.id
    loc = update.message.location
    update_user(user_id, lat=loc.latitude, lon=loc.longitude)
    await update.message.reply_text(
        "✏️ تغییر موقعیت GPS با موفقیت انجام شد ☑️\n\nخب ، حالا چه کاری برات انجام بدم؟\n\nاز منوی پایین👇 انتخاب کن",
        reply_markup=MAIN_MENU,
    )

# ============================== COINS / PAYMENT ==============================

async def show_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    row = get_user(update.effective_user.id)
    text = (f"💰 سکه فعلی شما: {row['coins']}{vip_badge(row)}\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "❓ روش‌های بدست آوردن سکه چیست؟\n\n"
            "1️⃣ معرفی دوستان (رایگان) 🎁:\n\n"
            f"بنر لینک⚡️ مخصوص خودت (/link) رو برای دوستات بفرست و به ازای هرنفر {REFERRAL_BONUS} سکه رایگان بگیر\n\n"
            "2️⃣ خرید سکه بصورت آنلاین 💳:\n\n"
            "برای خرید سکه یکی از تعرفه‌های زیر رو انتخاب کن 👇")
    await update.message.reply_text(text, reply_markup=coin_shop_keyboard())
    await maybe_send_profile_nudge(update, context, row)

async def coin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data

    if data == "show_invite":
        await send_invite_message(update, context, edit=True)
        await query.answer()
        return

    if data.startswith("buy:"):
        _, coins, price = data.split(":")
        coins, base_price = int(coins), int(price)
        final_price = base_price + random.randint(RANDOM_PRICE_MIN, RANDOM_PRICE_MAX)
        rial = final_price * 10
        text = ("💎 لطفاً دقیقاً مبلغ زیر را به شماره کارت واریز کنید:\n\n"
                f"💰 مبلغ قابل پرداخت:\n`{final_price:,} تومان`\n`{rial:,} ریال`\n\n"
                f"💳 شماره کارت:\n`{CARD_NUMBER}`\n👤 {CARD_OWNER}\n\n"
                "⚠️ توجه بسیار مهم: لطفاً دقیقاً همین رقم (تا آخرین تومان) رو واریز کن، عدد رو رند نکن.\n\n"
                "بعد از واریز، عکس رسید پرداخت رو همینجا ارسال کن 📸")
        conn = db()
        conn.execute(
            "INSERT INTO payments (user_id, coins, amount, base_amount, type, status, created_at) VALUES (?,?,?,?,?,?,?)",
            (user_id, coins, final_price, base_price, "coins", "awaiting_receipt", datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        update_user(user_id, state="await_receipt")
        await query.message.edit_text(text, parse_mode="Markdown")
        await query.answer()
        return

async def show_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    row = get_user(update.effective_user.id)
    text = VIP_BENEFITS_TEXT
    if is_vip(row):
        until = datetime.fromisoformat(row["vip_until"]).strftime("%Y-%m-%d")
        text += f"\n\n✅ اشتراک VIP شما فعال است تا تاریخ {until}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تمدید اشتراک VIP", callback_data="vip:buy", style="primary")]])
    else:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🌟 خرید اشتراک VIP", callback_data="vip:buy", style="primary")]])
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
    await maybe_send_profile_nudge(update, context, row)

async def vip_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if query.data == "vip:buy":
        final_price = VIP_PRICE + random.randint(RANDOM_PRICE_MIN, RANDOM_PRICE_MAX)
        rial = final_price * 10
        text = ("🌟 لطفاً دقیقاً مبلغ زیر را برای فعال‌سازی اشتراک VIP به شماره کارت واریز کنید:\n\n"
                f"💰 مبلغ قابل پرداخت:\n`{final_price:,} تومان`\n`{rial:,} ریال`\n\n"
                f"💳 شماره کارت:\n`{CARD_NUMBER}`\n👤 {CARD_OWNER}\n\n"
                "⚠️ توجه: دقیقاً همین رقم رو واریز کن و عدد رو رند نکن.\n\n"
                "بعد از واریز، عکس رسید پرداخت رو همینجا ارسال کن 📸")
        conn = db()
        conn.execute(
            "INSERT INTO payments (user_id, coins, amount, base_amount, type, status, created_at) VALUES (?,?,?,?,?,?,?)",
            (user_id, 0, final_price, VIP_PRICE, "vip", "awaiting_receipt", datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        update_user(user_id, state="await_receipt")
        await query.message.edit_text(text, parse_mode="Markdown")
        await query.answer()
        return

async def send_invite_message(update, context, edit=False):
    row = get_user(update.effective_user.id)
    link = f"{BOT_LINK}?start=inv_{row['username_code']}"
    text = (f"همین الان رو لینک بزن 👇\n{link}\n\n"
            "⚡️ لینک دعوت شما با موفقیت ساخته شد 👆\n\n"
            "🎁 شما می‌تونی بنر حاوی لینک⚡️ خودت رو به گـــروه‌ها و دوستات ارسال کنی\n\n"
            f"- با معرفی هر نفر {REFERRAL_BONUS} سکه بگیر! برای اطلاعات بیشتر راهنمای سکه (/help_credit) رو بخون.\n\n"
            f"👈 شما تاکنون {row['invite_count'] or 0} نفر رو به《 ایزی گپ 》دعوت کرده‌ای .")
    if edit and update.callback_query:
        await update.callback_query.message.edit_text(text)
    else:
        await update.message.reply_text(text)

async def receipt_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    conn = db()
    pay = conn.execute(
        "SELECT * FROM payments WHERE user_id=? AND status='awaiting_receipt' ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if not pay:
        conn.close()
        return
    conn.execute("UPDATE payments SET status='under_review' WHERE id=?", (pay["id"],))
    conn.commit()
    conn.close()
    update_user(user_id, state=None)

    await update.message.reply_text("✅ رسید شما دریافت شد و در حال بررسی توسط ادمین است.")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ پذیرفتن و ارسال سکه", callback_data=f"pay_ok:{pay['id']}", style="success"),
         InlineKeyboardButton("❌ رد کردن", callback_data=f"pay_no:{pay['id']}", style="danger")]
    ])
    ptype = pay["type"] or "coins"
    if ptype == "vip":
        detail = f"🌟 اشتراک VIP ({VIP_DURATION_DAYS} روزه)"
    else:
        detail = f"سکه: {pay['coins']}"
    for admin_id in get_admin_ids():
        try:
            await context.bot.send_photo(
                admin_id,
                photo.file_id,
                caption=(f"رسید جدید از کاربر {user_id}\n"
                         f"مبلغ واریزی: {pay['amount']:,} تومان\n{detail}\n"
                         f"می‌خوای تایید کنی؟"),
                reply_markup=kb,
            )
        except Exception:
            pass

async def admin_payment_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin_user(update.effective_user.id):
        await query.answer("فقط ادمین!", show_alert=True)
        return
    action, pay_id = query.data.split(":")
    pay_id = int(pay_id)
    conn = db()
    pay = conn.execute("SELECT * FROM payments WHERE id=?", (pay_id,)).fetchone()
    if not pay:
        conn.close()
        await query.answer("یافت نشد.")
        return
    ptype = pay["type"] or "coins"
    if action == "pay_ok":
        conn.execute("UPDATE payments SET status='approved' WHERE id=?", (pay_id,))
        conn.commit()
        if ptype == "vip":
            until = grant_vip(pay["user_id"])
            await context.bot.send_message(pay["user_id"],
                f"✅ پرداخت شما تایید شد!\n🌟 اشتراک VIP شما تا تاریخ {until.strftime('%Y-%m-%d')} فعال شد.\n\nاز امکانات ویژه‌ت لذت ببر 🎉"
            )
        else:
            await add_coins_checked(pay["user_id"], pay["coins"], "purchase", context)
            await context.bot.send_message(pay["user_id"], f"✅ پرداخت شما تایید شد و {pay['coins']} سکه به حسابت اضافه شد.")
        try:
            await query.message.edit_caption(caption=query.message.caption + "\n\n✅ تایید شد.")
        except Exception:
            pass
    else:
        conn.execute("UPDATE payments SET status='rejected' WHERE id=?", (pay_id,))
        conn.commit()
        await context.bot.send_message(pay["user_id"], "❌ متاسفانه رسید شما تایید نشد.")
        try:
            await query.message.edit_caption(caption=query.message.caption + "\n\n❌ رد شد.")
        except Exception:
            pass
    conn.close()
    await query.answer()

# ============================== NAME / AGE / PHOTO TEXT & PHOTO CAPTURE ==============================

async def free_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = get_user(user_id)
    if row is None:
        await start(update, context)
        return
    if row["state"] == "await_ticket_text" and update.message.text:
        await handle_ticket_text(update, context, update.message.text.strip())
        return
    if row["state"] and row["state"].startswith("admin_wait_") and update.message.text and is_admin_user(user_id):
        await handle_admin_text(update, context, row, update.message.text.strip())
        return
    if row["is_blocked"]:
        await send_block_message(update, context, row)
        return
    if not is_registered(row):
        await registration_text_guard(update, context, row)
        return

    state = row["state"]
    text = update.message.text.strip() if update.message.text else ""

    if state == "await_name":
        if is_valid_persian_name(text):
            update_user(user_id, name=text, state=None)
            await update.message.reply_text("✅ نام شما با موفقیت تغییر کرد.", reply_markup=MAIN_MENU)
        else:
            await update.message.reply_text("⚠️ لطفا نام خود را فقط با حروف فارسی ارسال کن (بدون عدد، ایموجی یا حروف انگلیسی).")
        return
    if state == "await_age_edit":
        if text.isdigit() and MIN_AGE <= int(text) <= MAX_AGE:
            update_user(user_id, age=int(text), state=None)
            await update.message.reply_text("✅ سن شما با موفقیت تغییر کرد.", reply_markup=MAIN_MENU)
        else:
            await update.message.reply_text(f"⚠️ فقط عدد بین {MIN_AGE} تا {MAX_AGE} وارد کن.")
        return
    if state == "in_chat":
        await relay_message(update, context)
        return
    if state == "ship_wait_phone" and row["pending_search"] and row["pending_search"].startswith("ship:"):
        if text == "❌ انصراف از رل":
            await cancel_ship_phone_step(update, context, row)
        else:
            await update.message.reply_text(
                "برای ادامه، شماره‌ت رو با دکمه‌ی «📞 ارسال شماره‌ام» بفرست، یا برای انصراف روی «❌ انصراف از رل» بزن.",
                reply_markup=ship_phone_keyboard(),
            )
        return
    if state == "await_dm_text" and row["pending_search"] and row["pending_search"].startswith("dmtarget:"):
        _, target_id, cost = row["pending_search"].split(":")
        target_id, cost = int(target_id), int(cost)
        target = get_user(target_id)
        update_user(user_id, state=None, pending_search=None)
        if not target:
            await update.message.reply_text("کاربر یافت نشد.", reply_markup=MAIN_MENU)
            return
        if row["coins"] < cost:
            await update.message.reply_text(f"⚠️ سکه کافی نداری! ({cost} سکه مورد نیاز)", reply_markup=MAIN_MENU)
            return
        if cost:
            add_coins(user_id, -cost, source="spend_dm")
        try:
            await context.bot.send_message(target_id,
                f"📩 پیام دایرکت جدید از /user_{row['username_code']}:\n\n{text}"
            )
            await update.message.reply_text("✅ پیام دایرکت شما ارسال شد.", reply_markup=MAIN_MENU)
        except Exception:
            await update.message.reply_text("❌ ارسال پیام ناموفق بود.", reply_markup=MAIN_MENU)
        return
    await main_menu_router(update, context)

# ============================== PHOTO HANDLER ==============================

async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    user_id = update.effective_user.id
    row = get_user(user_id)
    if row["state"] == "await_photo":
        file_id = update.message.photo[-1].file_id
        update_user(user_id, photo_file_id=file_id, state=None)
        bonus_line = ""
        if not row["photo_bonus_claimed"]:
            await add_coins_checked(user_id, PHOTO_BONUS, "photo_bonus", context)
            update_user(user_id, photo_bonus_claimed=1)
            bonus_line = f"\n\n🎁 {PHOTO_BONUS} سکه هدیه‌ی تکمیل پروفایل به حسابت اضافه شد!"
        await update.message.reply_text("✅ عکس پروفایل شما تغییر کرد." + bonus_line, reply_markup=MAIN_MENU)
        return
    if row["state"] == "await_receipt":
        await receipt_photo_handler(update, context)
        return
    if row["state"] == "in_chat":
        await relay_photo(update, context)
        return
    await update.message.reply_text("این عکس در این مرحله قابل قبول نیست.")

# ============================== ANONYMOUS CHAT ==============================

waiting_queue = {"any": [], "male": [], "female": []}

def chat_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 پروفایل مخاطب", callback_data="chat:profile")],
        [InlineKeyboardButton("💞 پیشنهاد رل", callback_data="chat:ship", style="success")],
        [InlineKeyboardButton("⛔️ پایان چت", callback_data="chat:end", style="danger")],
    ])

def ship_phone_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📞 ارسال شماره‌ام برای تایید رل", request_contact=True)],
         [KeyboardButton("❌ انصراف از رل")]],
        resize_keyboard=True,
    )

async def anon_connect_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    text = "🔴 حتما قبل از استفاده از ربات قوانین ربات « /help_terms » را مطالعه کنید."
    await update.message.reply_text(text)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("جستوجوی شانسی🎲", callback_data="search:any", style="primary")],
        [InlineKeyboardButton("👧 جستوجوی دختر", callback_data="search:دختر")],
        [InlineKeyboardButton("🧑 جستوجوی پسر", callback_data="search:پسر")],
        [InlineKeyboardButton("📡 جستجوی اطراف", callback_data="search:nearby")],
        [InlineKeyboardButton("🗺 جستوجو بر پایه‌ی استان", callback_data="search:province")],
    ])
    await update.message.reply_text(f"🤩 به کی وصلت کنم؟ انتخاب کن 👇🎲\n\n{FOOTER}", reply_markup=kb)
    row = get_user(update.effective_user.id)
    await maybe_send_profile_nudge(update, context, row)

SEARCH_LABELS = {
    "any": "🎲 جستجوی شانسی",
    "دختر": "👧 جستجوی دختر",
    "پسر": "🧑 جستجوی پسر",
}

def searching_text(label: str, same_age_on: bool) -> str:
    toggle_state = "✅ فعال" if same_age_on else "📴 غیر فعال"
    return (f"🔎 در حال جستجوی مخاطب ناشناس شما...\n{label}\n\n"
            "⏳ حداکثر تا ۲ دقیقه صبر کن؛ به محض پیدا شدن یه نفر بهت خبر می‌دم 🔔\n\n"
            f"⚙️ جستجوی هم‌سن: {toggle_state}")

def searching_keyboard(gender_filter: str, same_age_on: bool) -> InlineKeyboardMarkup:
    toggle_label = "🔴 غیرفعال کردن جستجوی هم‌سن" if same_age_on else "🎂 فعال کردن جستجوی هم‌سن"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data=f"sameage:toggle:{gender_filter}")],
        [InlineKeyboardButton("❌ لغو جستجو", callback_data="cancelsearch", style="danger")],
    ])

async def show_searching_ui(query, user_id, gender_filter):
    row = get_user(user_id)
    same_age_on = bool(row["same_age_only"]) if row else False
    label = SEARCH_LABELS.get(gender_filter, SEARCH_LABELS["any"])
    await query.message.edit_text(
        searching_text(label, same_age_on),
        reply_markup=searching_keyboard(gender_filter, same_age_on),
    )

async def try_match(user_id, gender_filter, context):
    me = get_user(user_id)
    conn = db()
    q = "SELECT user_id FROM users WHERE pending_search IS NOT NULL AND pending_search LIKE 'waiting:%' AND user_id != ?"
    candidates = conn.execute(q, (user_id,)).fetchall()
    conn.close()
    for cand in candidates:
        cand_row = get_user(cand["user_id"])
        if not cand_row:
            continue
        want = cand_row["pending_search"].split(":", 1)[1]
        if want in ("any",) or want == me["gender"]:
            if gender_filter in ("any",) or gender_filter == cand_row["gender"]:
                if me["same_age_only"] and cand_row["age"] != me["age"]:
                    continue
                if cand_row["same_age_only"] and cand_row["age"] != me["age"]:
                    continue
                return cand_row
    return None

async def connect_two_users(user_a, user_b, context):
    session = gen_code(8)
    update_user(user_a, in_chat_with=user_b, pending_search=None, state="in_chat")
    update_user(user_b, in_chat_with=user_a, pending_search=None, state="in_chat")
    context.bot_data.setdefault("chat_sessions", {})[user_a] = session
    context.bot_data.setdefault("chat_sessions", {})[user_b] = session

    text = ("🤩😉 پیدا کردم و وصل‌تون کردم!\nبه مخاطبت 👋 کن 🗣\n\n"
            "⚠️ هشدار جدی:\nلطفاً اطلاعات شخصی مثل شناسنامه، گواهینامه یا اطلاعات خصوصی خودتون رو "
            "برای هم ارسال نکنید. مسئولیت انتشار اطلاعات شخصی بر عهده خود کاربران است.")
    for uid in (user_a, user_b):
        await context.bot.send_message(uid, text, reply_markup=chat_menu_keyboard())

async def search_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    row = get_user(user_id)
    data = query.data

    if data.startswith("search:"):
        mode = data.split(":", 1)[1]
        if mode == "nearby":
            if row["lat"] is None:
                await query.message.edit_text("⚠️ خطا: برای استفاده از این قسمت ابتدا باید موقعیت مکانی(GPS) خود را ثبت کنید!")
                await context.bot.send_message(user_id, "📍 با کلیک روی دکمه‌ی پایین موقعیت خودت رو ثبت کن:")
                await send_gps_request(update, context)
            else:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("👧 دختر (۴ سکه)", callback_data="nearbygender:دختر")],
                    [InlineKeyboardButton("🧑 پسر (۴ سکه)", callback_data="nearbygender:پسر")],
                    [InlineKeyboardButton("🎲 فرقی نمی‌کنه (رایگان)", callback_data="nearbygender:any")],
                ])
                await query.message.edit_text("📡 چه کسی از اطرافت برات پیدا کنم؟ انتخاب کن👇", reply_markup=kb)
            await query.answer()
            return
        if mode == "province":
            await query.message.edit_text("🗺 به کدوم استان وصلت کنم...؟ انتخاب کن👇", reply_markup=province_keyboard(prefix="matchprov"))
            await query.answer()
            return
        if mode in ("دختر", "پسر"):
            cost = 0 if is_vip(row) else 1
            if row["coins"] < cost:
                await show_insufficient_coins(query, cost)
                await query.answer()
                return
            add_coins(user_id, -cost, source="spend_search")
            matched = await do_random_connect(user_id, mode, update, context)
            if not matched:
                await show_searching_ui(query, user_id, mode)
            await query.answer()
            return
        # any
        matched = await do_random_connect(user_id, "any", update, context)
        if not matched:
            await show_searching_ui(query, user_id, "any")
        await query.answer()
        return

    if data.startswith("sameage:toggle:"):
        if not (row["pending_search"] and row["pending_search"].startswith("waiting:")):
            await query.answer("⚠️ جستجوی فعالی وجود نداره.", show_alert=True)
            return
        gender_filter = data.split(":", 2)[2]
        new_val = 0 if row["same_age_only"] else 1
        update_user(user_id, same_age_only=new_val)
        await show_searching_ui(query, user_id, gender_filter)
        await query.answer("🎂 جستجوی هم‌سن فعال شد." if new_val else "📴 جستجوی هم‌سن غیرفعال شد.")
        return

    if data == "cancelsearch":
        if row["pending_search"] and row["pending_search"].startswith("waiting:"):
            update_user(user_id, pending_search=None)
            await query.message.edit_text("❌ جستجو لغو شد.\n\nهر وقت خواستی، دوباره امتحان کن 🌠")
            await context.bot.send_message(user_id, "💫 خب حالا چه کاری برات انجام بدم؟", reply_markup=MAIN_MENU)
        else:
            await query.message.edit_text("⚠️ جستجوی فعالی برای لغو پیدا نشد.")
        await query.answer()
        return

    if data.startswith("matchprov:"):
        province = data.split(":", 1)[1]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🧑 جستجوی پسر (۴ سکه)", callback_data=f"provconn:{province}:پسر")],
            [InlineKeyboardButton("👧 جستجوی دختر (۴ سکه)", callback_data=f"provconn:{province}:دختر")],
            [InlineKeyboardButton("🎲 فرقی نمی‌کنه (رایگان)", callback_data=f"provconn:{province}:any")],
        ])
        await query.message.edit_text(f"چه کسی رو ازاستان {province} برات پیدا کنم؟ انتخاب کن👇", reply_markup=kb)
        await query.answer()
        return

    if data.startswith("provconn:"):
        _, province, gender = data.split(":")
        cost = 0 if (gender == "any" or is_vip(row)) else 4
        if row["coins"] < cost:
            await show_insufficient_coins(query, cost)
            await query.answer()
            return
        if cost:
            add_coins(user_id, -cost, source="spend_search")
        await do_province_connect(user_id, province, gender, update, context)
        await query.answer()
        return

    if data.startswith("nearbygender:"):
        gender = data.split(":", 1)[1]
        cost = 0 if (gender == "any" or is_vip(row)) else 4
        if row["coins"] < cost:
            await show_insufficient_coins(query, cost)
            await query.answer()
            return
        if cost:
            add_coins(user_id, -cost, source="spend_search")
        matched = await do_random_connect(user_id, gender, update, context)
        if not matched:
            await show_searching_ui(query, user_id, gender)
        await query.answer()
        return

async def show_insufficient_coins(query, cost):
    text = (f"⚠️ خطا : شما سکه کافی ندارید! ({cost} سکه مورد نیاز)\n\n"
            "برای معرفی ربات و دریافت سکه ، دکمه زیر👇 رو لمس کن تا لینک معرفی مخصوص خودتو دریافت کنی")
    rows = [[InlineKeyboardButton("🎁 معرفی به دوستان", callback_data="show_invite", style="primary")]]
    for c, p in COIN_PACKAGES:
        rows.append([InlineKeyboardButton(f"خرید {c} سکه: {p:,} تومان", callback_data=f"buy:{c}:{p}", style="primary")])
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(rows))

async def do_random_connect(user_id, gender_filter, update, context):
    partner = await try_match(user_id, gender_filter, context)
    if partner:
        await connect_two_users(user_id, partner["user_id"], context)
        return True
    update_user(user_id, pending_search=f"waiting:{gender_filter}")
    return False

async def do_province_connect(user_id, province, gender, update, context):
    conn = db()
    q = "SELECT * FROM users WHERE province=? AND user_id != ? AND in_chat_with IS NULL"
    params = [province, user_id]
    if gender != "any":
        q += " AND gender=?"
        params.append(gender)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    if not rows:
        await context.bot.send_message(user_id, "😔 متاسفانه در حال حاضر کاربر مناسبی در این استان پیدا نشد.")
        return
    partner = random.choice(rows)
    await connect_two_users(user_id, partner["user_id"], context)

async def send_province_list(user_id, province, gender, update, context):
    conn = db()
    q = "SELECT * FROM users WHERE province=? AND user_id != ?"
    params = [province, user_id]
    if gender != "any":
        q += " AND gender=?"
        params.append(gender)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    if not rows:
        await context.bot.send_message(user_id, "کاربری یافت نشد.")
        return
    lines = [f"{r['age']} {r['name'] or '—'} /user_{r['username_code']} {r['province']}({r['city']})" for r in rows[:20]]
    await context.bot.send_message(user_id, "📋 لیست هم‌استانی‌ها:\n\n" + "\n".join(lines))

# ============================== RELAY MESSAGES IN CHAT ==============================

async def relay_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = get_user(user_id)
    partner_id = row["in_chat_with"]
    if not partner_id:
        update_user(user_id, state=None)
        await main_menu_router(update, context)
        return
    sent = await context.bot.send_message(partner_id, update.message.text)
    conn = db()
    conn.execute(
        "INSERT INTO messages_log (chat_session, sender_id, receiver_id, sender_msg_id, receiver_msg_id, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (
            context.bot_data.get("chat_sessions", {}).get(user_id, ""),
            user_id,
            partner_id,
            update.message.message_id,
            sent.message_id,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

async def relay_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = get_user(user_id)
    partner_id = row["in_chat_with"]
    if not partner_id:
        return
    await context.bot.send_photo(partner_id, update.message.photo[-1].file_id)

async def chat_menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    row = get_user(user_id)
    data = query.data

    if data == "chat:profile":
        partner_id = row["in_chat_with"]
        if not partner_id:
            await query.answer("در حال حاضر در چتی نیستی.", show_alert=True)
            return
        partner = get_user(partner_id)
        text = profile_text(partner, viewer_is_self=False)
        text += f"\n\n🆔 آیدی : /user_{partner['username_code']}"
        if row["lat"] is not None and partner["lat"] is not None:
            d = haversine(row["lat"], row["lon"], partner["lat"], partner["lon"])
            text += f"\n\n🏁 فاصله از شما: {d:.1f} کیلومتر"
        pkb = contact_profile_keyboard(partner_id)
        await send_profile_photo(context.bot, user_id, partner, text, pkb)
        await query.answer()
        return

    if data == "chat:ship":
        partner_id = row["in_chat_with"]
        if not partner_id:
            await query.answer("در حال حاضر در چتی نیستی.", show_alert=True)
            return
        partner = get_user(partner_id)
        if not partner or partner["in_chat_with"] != user_id:
            await query.answer("در حال حاضر در چتی نیستی.", show_alert=True)
            return
        conn = db()
        existing = conn.execute(
            "SELECT id FROM relationships WHERE status='pending' AND "
            "((user_a=? AND user_b=?) OR (user_a=? AND user_b=?))",
            (user_id, partner_id, partner_id, user_id),
        ).fetchone()
        if existing:
            conn.close()
            await query.answer("یه پیشنهاد رل قبلاً برای همین چت در انتظار جواب هست.", show_alert=True)
            return
        cur = conn.execute(
            "INSERT INTO relationships (user_a, user_b, status, created_at) VALUES (?, ?, 'pending', ?)",
            (user_id, partner_id, datetime.now().isoformat()),
        )
        rel_id = cur.lastrowid
        conn.commit()
        conn.close()
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ قبول می‌کنم", callback_data=f"shipok:{rel_id}", style="success"),
             InlineKeyboardButton("❌ رد می‌کنم", callback_data=f"shipno:{rel_id}", style="danger")]
        ])
        try:
            await context.bot.send_message(user_id, SHIP_CHEAT_WARNING_TEXT, parse_mode="HTML")
            await context.bot.send_message(
                partner_id,
                f"💌 کاربر /user_{row['username_code']} می‌خواد رسماً باهات «رل» بشه!\nقبول می‌کنی؟\n\n"
                + SHIP_CHEAT_WARNING_TEXT,
                reply_markup=kb,
                parse_mode="HTML",
            )
            await query.answer("💌 پیشنهادت ارسال شد، منتظر جوابش باش.", show_alert=True)
        except Exception:
            conn = db()
            conn.execute("UPDATE relationships SET status='failed' WHERE id=?", (rel_id,))
            conn.commit()
            conn.close()
            await query.answer("⚠️ نشد پیام رو براش بفرستم.", show_alert=True)
        return


        await query.message.edit_text(
            "🤖 پیام سیستم 👇\n\nمطمئنی می‌خوای این گپ رو ببندی؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ ادامه‌ی چت", callback_data="chat:continue", style="success"),
                 InlineKeyboardButton("⛔️ اتمام چت", callback_data="chat:finish", style="danger")]
            ]),
        )
        await query.answer()
        return

    if data == "chat:continue":
        await query.message.edit_text("✅ میتونی چت رو ادامه بدی.")
        await query.answer()
        return

    if data == "chat:finish":
        partner_id = row["in_chat_with"]
        session_code = context.bot_data.get("chat_sessions", {}).get(user_id, gen_code(8))
        context.bot_data.setdefault("session_ended_at", {})[session_code] = datetime.now().isoformat()
        update_user(user_id, in_chat_with=None, state=None)
        report_and_delete_notice = (
            "برای گزارش عدم رعایت قوانین (/help_terms) می‌توانید با لمس 《 🚫 گزارش کاربر 》 در پروفایل، "
            "کاربر را گزارش کنید.\n"
            "🗑تا 30 دقیقه بعد اتمام چت می‌تونی با دستور زیر پیام‌های ارسال شده رو به طرف مقابل پاک کنی!\n"
            f"/delet_messages_{session_code}"
        )
        if partner_id:
            update_user(partner_id, in_chat_with=None, state=None)
            partner_text = (f"چت شما با کاربر: /user_{row['username_code']} توسط کاربر مقابل قطع شد\n\n"
                            f"{report_and_delete_notice}")
            await context.bot.send_message(partner_id, partner_text, reply_markup=MAIN_MENU)
            ender_text = (f"چت شما با کاربر: /user_{get_user(partner_id)['username_code']} توسط شما قطع شد\n\n"
                          f"{report_and_delete_notice}")
        else:
            ender_text = "✅ چت پایان یافت."
        await query.message.edit_text(ender_text)
        await context.bot.send_message(user_id, "خب حالا چه کاری برات انجام بدم؟", reply_markup=MAIN_MENU)
        await query.answer()
        return

# ============================== CONTACT PROFILE ACTIONS ==============================

async def contact_profile_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    action, target_id = query.data.split(":")
    target_id = int(target_id)

    if action == "addcontact":
        conn = db()
        conn.execute("INSERT OR IGNORE INTO contacts (owner_id, contact_id) VALUES (?,?)", (user_id, target_id))
        conn.commit()
        conn.close()
        await query.answer("✅ به مخاطبین اضافه شد.", show_alert=True)
        return

    if action == "removecontact":
        conn = db()
        existed = conn.execute(
            "SELECT 1 FROM contacts WHERE owner_id=? AND contact_id=?", (user_id, target_id)
        ).fetchone()
        conn.execute("DELETE FROM contacts WHERE owner_id=? AND contact_id=?", (user_id, target_id))
        conn.commit()
        conn.close()
        if existed:
            await query.answer("➖ از مخاطبین حذف شد.", show_alert=True)
        else:
            await query.answer("این کاربر توی لیست مخاطبینت نبود.", show_alert=True)
        return

    if action == "notifyon":
        row = get_user(user_id)
        cost = 1
        if row["coins"] < cost:
            await query.answer(f"⚠️ سکه کافی نداری! ({cost} سکه مورد نیاز)", show_alert=True)
            return
        add_coins(user_id, -cost, source="spend_notify")
        conn = db()
        conn.execute("INSERT OR REPLACE INTO notify_requests (watcher_id, target_id, created_at) VALUES (?,?,?)",
            (user_id, target_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        await query.answer("🔔 به محض آنلاین شدن این کاربر بهت خبر می‌دم.", show_alert=True)
        return

    if action == "report":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔞 محتوای غیراخلاقی", callback_data=f"reportreason:{target_id}:غیراخلاقی", style="danger")],
            [InlineKeyboardButton("😡 آزار و اذیت", callback_data=f"reportreason:{target_id}:آزار", style="danger")],
            [InlineKeyboardButton("🕵️ انتشار اطلاعات شخصی", callback_data=f"reportreason:{target_id}:حریم‌خصوصی", style="danger")],
            [InlineKeyboardButton("📢 تبلیغات", callback_data=f"reportreason:{target_id}:تبلیغات", style="danger")],
        ])
        await context.bot.send_message(user_id, "🚫 دلیل گزارش این کاربر رو انتخاب کن:", reply_markup=kb)
        await query.answer()
        return

async def report_reason_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    _, target_id, reason = query.data.split(":")
    target_id = int(target_id)
    conn = db()
    conn.execute("INSERT INTO reports (reporter_id, target_id, reason, created_at) VALUES (?,?,?,?)",
        (user_id, target_id, reason, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    await query.message.edit_text("✅ گزارش شما ثبت شد و توسط تیم پشتیبانی بررسی خواهد شد.")
    target = get_user(target_id)
    await context.bot.send_message(ADMIN_ID,
        f"🚫 گزارش جدید\nگزارش‌دهنده: {user_id}\nکاربر گزارش‌شده: {target_id} "
        f"(/user_{target['username_code'] if target else '?'})\nدلیل: {reason}"
    )
    await query.answer()

# ============================== SHIPPING / RELATIONSHIP ANNOUNCEMENTS ==============================
# Mutual-consent relationship confirmation: BOTH sides must accept the
# proposal, and BOTH sides must separately agree before anything is posted
# to the public channel. The channel post never includes photos — only the
# anonymous /user_XXXX codes — and either side can decline the public post
# while still keeping the coin reward.

async def cancel_ship_phone_step(update: Update, context: ContextTypes.DEFAULT_TYPE, row):
    user_id = update.effective_user.id
    rel_id = int(row["pending_search"].split(":", 1)[1])
    conn = db()
    rel = conn.execute("SELECT * FROM relationships WHERE id=?", (rel_id,)).fetchone()
    if rel and rel["status"] == "pending_phone":
        conn.execute("UPDATE relationships SET status='cancelled' WHERE id=?", (rel_id,))
        conn.commit()
    conn.close()
    update_user(user_id, state=None, pending_search=None)
    await update.message.reply_text("عملیات رل لغو شد.", reply_markup=MAIN_MENU)
    if rel:
        partner_id = rel["user_b"] if user_id == rel["user_a"] else rel["user_a"]
        partner = get_user(partner_id)
        if partner and partner["state"] == "ship_wait_phone":
            update_user(partner_id, state=None, pending_search=None)
            try:
                await context.bot.send_message(partner_id, "😔 کاربر مقابل از فرآیند رل انصراف داد.", reply_markup=MAIN_MENU)
            except Exception:
                pass

async def handle_ship_phone(update: Update, context: ContextTypes.DEFAULT_TYPE, row, contact):
    user_id = update.effective_user.id
    rel_id = int(row["pending_search"].split(":", 1)[1])
    conn = db()
    rel = conn.execute("SELECT * FROM relationships WHERE id=?", (rel_id,)).fetchone()
    if not rel or rel["status"] != "pending_phone" or user_id not in (rel["user_a"], rel["user_b"]):
        conn.close()
        update_user(user_id, state=None, pending_search=None)
        await update.message.reply_text("این درخواست دیگه معتبر نیست.", reply_markup=MAIN_MENU)
        return
    phone = to_en_digits(contact.phone_number.lstrip("+"))
    col = "a_phone" if user_id == rel["user_a"] else "b_phone"
    conn.execute(f"UPDATE relationships SET {col}=? WHERE id=?", (phone, rel_id))
    conn.commit()
    rel = conn.execute("SELECT * FROM relationships WHERE id=?", (rel_id,)).fetchone()
    conn.close()

    update_user(user_id, state=None, pending_search=None)
    if rel["a_phone"] and rel["b_phone"]:
        await finalize_relationship(rel_id, context)
    else:
        await update.message.reply_text("✅ شماره‌ت ثبت شد، منتظر طرف مقابل باش.", reply_markup=MAIN_MENU)

async def finalize_relationship(rel_id, context: ContextTypes.DEFAULT_TYPE):
    conn = db()
    already = conn.execute(
        "SELECT r2.id FROM relationships r1, relationships r2 WHERE r1.id=? AND r2.status='confirmed' AND r2.id!=r1.id AND "
        "((r2.user_a=r1.user_a AND r2.user_b=r1.user_b) OR (r2.user_a=r1.user_b AND r2.user_b=r1.user_a))",
        (rel_id,),
    ).fetchone()
    conn.execute("UPDATE relationships SET status='confirmed', confirmed_at=? WHERE id=?",
                 (datetime.now().isoformat(), rel_id))
    conn.commit()
    rel = conn.execute("SELECT * FROM relationships WHERE id=?", (rel_id,)).fetchone()
    conn.close()

    a = get_user(rel["user_a"])
    b = get_user(rel["user_b"])

    # رد و بدل کردن شماره‌ها به عنوان کارت مخاطب تلگرامی
    try:
        await context.bot.send_contact(rel["user_a"], phone_number=rel["b_phone"], first_name=b["name"] or "دوست‌جدید")
    except Exception:
        logger.exception("Failed to relay phone contact to user_a for rel_id=%s", rel_id)
    try:
        await context.bot.send_contact(rel["user_b"], phone_number=rel["a_phone"], first_name=a["name"] or "دوست‌جدید")
    except Exception:
        logger.exception("Failed to relay phone contact to user_b for rel_id=%s", rel_id)

    reward_given = False
    if not already:
        await add_coins_checked(rel["user_a"], RELATIONSHIP_COIN_REWARD, "relationship_reward", context)
        await add_coins_checked(rel["user_b"], RELATIONSHIP_COIN_REWARD, "relationship_reward", context)
        reward_given = True

    reward_line = (f"🪙 هرکدومتون {RELATIONSHIP_COIN_REWARD} سکه جایزه گرفتید!" if reward_given
                    else "🪙 چون قبلاً یه‌بار جایزه‌ی این جفت رو گرفته بودید، این‌بار سکه‌ی اضافه تعلق نگرفت.")
    celebrate = f"🎉💞 تبریک! شماره‌هاتون رد و بدل شد و رسماً «رل» شدید!\n{reward_line}"

    consent_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله، اعلام کن", callback_data=f"shipchan:{rel_id}:yes", style="success"),
         InlineKeyboardButton("❌ نه، نمی‌خوام", callback_data=f"shipchan:{rel_id}:no", style="danger")]
    ])
    consent_text = ("می‌خوای این خبر خوش، فقط به‌صورت ناشناس (با کد کاربری، بدون عکس) توی کانال ما جشن گرفته "
                    "بشه؟ هر دو نفر باید موافقت کنن تا پست بشه.")
    for uid in (rel["user_a"], rel["user_b"]):
        try:
            await context.bot.send_message(uid, celebrate, reply_markup=MAIN_MENU)
            await context.bot.send_message(uid, consent_text, reply_markup=consent_kb)
        except Exception:
            pass

async def ship_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data

    if data.startswith("shipok:") or data.startswith("shipno:"):
        rel_id = int(data.split(":", 1)[1])
        conn = db()
        rel = conn.execute("SELECT * FROM relationships WHERE id=?", (rel_id,)).fetchone()
        if not rel or rel["status"] != "pending":
            conn.close()
            await query.answer("این درخواست دیگه معتبر نیست.", show_alert=True)
            return
        if rel["user_b"] != user_id:
            conn.close()
            await query.answer("این درخواست برای تو نیست.", show_alert=True)
            return

        if data.startswith("shipno:"):
            conn.execute("UPDATE relationships SET status='rejected' WHERE id=?", (rel_id,))
            conn.commit()
            conn.close()
            await query.message.edit_text("❌ پیشنهاد رل رد شد.")
            try:
                await context.bot.send_message(rel["user_a"], "😔 کاربر مقابل پیشنهاد رلت رو رد کرد.")
            except Exception:
                pass
            await query.answer()
            return

        # shipok: don't reward yet — first both sides must exchange real phone
        # numbers. This is the anti-collusion check: two accounts faking a
        # relationship to farm coins would have to also hand each other a
        # real, Telegram-verified phone number, which raises the cost of
        # cheating a lot more than a couple of button taps.
        conn.execute("UPDATE relationships SET status='pending_phone' WHERE id=?", (rel_id,))
        conn.commit()
        conn.close()

        warning_text = (
            "💞 پیشنهاد رل قبول شد!\n\n"
            "⚠️ توجه: جایزه‌ی سکه فقط بعد از اینکه هر دو نفر شماره‌ی تلفنشون رو با هم رد و بدل کنن فعال می‌شه.\n"
            "🚫 اگه تشخیص داده بشه از این روش برای رل‌زنی الکی یا سوءاستفاده از سیستم سکه استفاده شده، "
            "حساب‌های هر دو طرف مسدود می‌شه!\n\n"
            "برای ادامه، با دکمه‌ی پایین شماره‌ت رو ارسال کن 👇"
        )
        await query.message.edit_text("💞 پیشنهاد رل قبول شد! برای ادامه به پیام بعدی نگاه کن.")
        for uid in (rel["user_a"], rel["user_b"]):
            update_user(uid, state="ship_wait_phone", pending_search=f"ship:{rel_id}")
            try:
                await context.bot.send_message(uid, warning_text, reply_markup=ship_phone_keyboard())
            except Exception:
                pass
        await query.answer()
        return

    if data.startswith("shipchan:"):
        _, rel_id, choice = data.split(":")
        rel_id = int(rel_id)
        conn = db()
        rel = conn.execute("SELECT * FROM relationships WHERE id=?", (rel_id,)).fetchone()
        if not rel or rel["status"] != "confirmed":
            conn.close()
            await query.answer("این درخواست دیگه معتبر نیست.", show_alert=True)
            return
        if user_id not in (rel["user_a"], rel["user_b"]):
            conn.close()
            await query.answer("این مورد به تو مربوط نیست.", show_alert=True)
            return
        col = "a_channel_consent" if user_id == rel["user_a"] else "b_channel_consent"
        conn.execute(f"UPDATE relationships SET {col}=? WHERE id=?", (choice, rel_id))
        conn.commit()
        rel = conn.execute("SELECT * FROM relationships WHERE id=?", (rel_id,)).fetchone()
        conn.close()
        await query.message.edit_text("✅ نظرت ثبت شد، ممنون!" if choice == "yes" else "باشه، این حریم خصوصیته و محترم می‌شماریمش.")

        if rel["a_channel_consent"] == "yes" and rel["b_channel_consent"] == "yes" and not rel["posted"]:
            a = get_user(rel["user_a"])
            b = get_user(rel["user_b"])
            if SHIP_CHANNEL_ID:
                post_text = (
                    "💞 یه «شیپ» جدید توی ایزی‌گپ رخ داد! 🎉\n\n"
                    f"🆔 /user_{a['username_code']}  💘  /user_{b['username_code']}\n\n"
                    "به این دو نفر تبریک می‌گیم! شما هم می‌تونید شانستون رو امتحان کنید 😉"
                )
                try:
                    await context.bot.send_message(SHIP_CHANNEL_ID, post_text)
                    conn = db()
                    conn.execute("UPDATE relationships SET posted=1 WHERE id=?", (rel_id,))
                    conn.commit()
                    conn.close()
                except Exception:
                    logger.exception("Failed to post ship announcement to channel %s.", SHIP_CHANNEL_ID)
        await query.answer()
        return

# ============================== BREAKUP (کات کردن) ==============================
# دکمه‌ی «کات کردن» توی پروفایل کاربر: فقط وقتی رابطه‌ی تاییدشده‌ای وجود داشته
# باشه نشون داده می‌شه، و فقط بعد از گذشت BREAKUP_COOLDOWN_DAYS از تاریخ تایید
# رابطه فعال می‌شه. این محدودیت جلوی رل‌زدن و کات‌کردن آنی برای چرخوندن سکه رو
# می‌گیره و به کاربر اجازه می‌ده بعد از کات، آزادانه با یک نفر دیگه رل بزنه.

async def breakup_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data

    if data.startswith("cutrel:"):
        rel_id = int(data.split(":", 1)[1])
        conn = db()
        rel = conn.execute("SELECT * FROM relationships WHERE id=?", (rel_id,)).fetchone()
        conn.close()
        if not rel or rel["status"] != "confirmed" or user_id not in (rel["user_a"], rel["user_b"]):
            await query.answer("این رابطه دیگه معتبر نیست.", show_alert=True)
            return

        ready_at = breakup_ready_at(rel)
        if datetime.now() < ready_at:
            remaining = ready_at - datetime.now()
            days_left = max(1, math.ceil(remaining.total_seconds() / 86400))
            await query.answer(
                f"⏳ هنوز {days_left} روز مونده تا بتونی کات کنی؛ باید {BREAKUP_COOLDOWN_DAYS} روز از رل زدنتون بگذره.",
                show_alert=True,
            )
            return

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💔 بله، کات می‌کنم", callback_data=f"cutrelconfirm:{rel_id}", style="danger"),
             InlineKeyboardButton("انصراف", callback_data=f"cutrelcancel:{rel_id}", style="success")]
        ])
        await query.message.reply_text(
            "🤖 پیام سیستم 👇\n\nمطمئنی می‌خوای این رابطه رو کات کنی؟ این کار قابل بازگشت نیست.",
            reply_markup=kb,
        )
        await query.answer()
        return

    if data.startswith("cutrelcancel:"):
        await query.message.edit_text("✅ باشه، رابطه‌ت دست‌نخورده موند.")
        await query.answer()
        return

    if data.startswith("cutrelconfirm:"):
        rel_id = int(data.split(":", 1)[1])
        conn = db()
        rel = conn.execute("SELECT * FROM relationships WHERE id=?", (rel_id,)).fetchone()
        if not rel or rel["status"] != "confirmed" or user_id not in (rel["user_a"], rel["user_b"]):
            conn.close()
            await query.answer("این رابطه دیگه معتبر نیست.", show_alert=True)
            return
        if datetime.now() < breakup_ready_at(rel):
            conn.close()
            await query.answer("⏳ هنوز زمانش نرسیده.", show_alert=True)
            return

        conn.execute(
            "UPDATE relationships SET status='ended', ended_at=?, ended_by=? WHERE id=?",
            (datetime.now().isoformat(), user_id, rel_id),
        )
        conn.commit()
        conn.close()

        partner_id = relationship_partner_id(rel, user_id)
        ender = get_user(user_id)
        await query.message.edit_text("💔 رابطه‌تون کات شد. هر وقت خواستی می‌تونی با یکی دیگه رل بزنی.")
        try:
            await context.bot.send_message(
                partner_id,
                f"💔 کاربر /user_{ender['username_code']} رابطه‌تون رو توی بات کات کرد.",
                reply_markup=MAIN_MENU,
            )
        except Exception:
            pass
        await query.answer()
        return

# ============================== NEARBY ==============================

async def nearby_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    row = get_user(update.effective_user.id)
    if row["lat"] is None:
        await update.message.reply_text("⚠️خطا: برای استفاده از این قسمت ابتدا باید موقعیت مکانی(GPS) خود را ثبت کنید!")
        await send_gps_request(update, context)
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 5KM", callback_data="radius:5"),
         InlineKeyboardButton("📍 10KM", callback_data="radius:10"),
         InlineKeyboardButton("📍 30KM", callback_data="radius:30")],
        [InlineKeyboardButton("📍 60KM", callback_data="radius:60"),
         InlineKeyboardButton("📍 100KM", callback_data="radius:100")],
    ])
    await update.message.reply_text(
        "📡میخوای تا چه فاصله ای از اطرافت جستجو کنم ؟\nمثلا تا 5 کیلومتر...؟! انتخاب کن👇", reply_markup=kb
    )
    await maybe_send_profile_nudge(update, context, row)

async def nearby_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data.startswith("radius:"):
        radius = data.split(":", 1)[1]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🧑 فقط پسرها", callback_data=f"nearbyf:{radius}:پسر")],
            [InlineKeyboardButton("👧 فقط دخترها", callback_data=f"nearbyf:{radius}:دختر")],
            [InlineKeyboardButton("🌈 همه رو نشون بده", callback_data=f"nearbyf:{radius}:any")],
        ])
        await query.message.edit_text(f"📡چه کسایی رو تا ({radius} KM📍) از اطرافت نشونت بدم؟ انتخاب کن👇", reply_markup=kb)
        await query.answer()
        return

    if data.startswith("nearbyf:") or data.startswith("nearbymore:"):
        parts = data.split(":")
        if parts[0] == "nearbyf":
            _, radius, gender = parts
            offset = 0
        else:
            _, radius, gender, offset = parts
            offset = int(offset)
        radius = float(radius)
        page_size = 10
        user_id = query.from_user.id
        me = get_user(user_id)
        conn = db()
        q = "SELECT * FROM users WHERE lat IS NOT NULL AND user_id != ?"
        params = [user_id]
        if gender != "any":
            q += " AND gender=?"
            params.append(gender)
        rows = conn.execute(q, params).fetchall()
        conn.close()

        results = []
        for r in rows:
            d = haversine(me["lat"], me["lon"], r["lat"], r["lon"])
            if d <= radius:
                results.append((d, r))
        results.sort(key=lambda x: x[0])

        if not results:
            await query.message.edit_text("😔 کاربری در این محدوده پیدا نشد.")
            await query.answer()
            return

        page = results[offset : offset + page_size]
        if not page:
            await query.answer("لیست به پایان رسید.", show_alert=True)
            return

        lines = ["📍 لیست افراد نزدیک شما که در ۳ روز اخیر آنلاین بوده اند\n"]
        for d, r in page:
            lines.append(
                f"‏{r['age']} 😐 {r['name'] or '—'}{vip_badge(r)} /user_{r['username_code']}  "
                f"{r['province']}({r['city']}) (🏁 {d:.0f} km) (❤️{r['likes']})"
            )
        lines.append(f"\nجستجو شده در {datetime.now().strftime('%Y/%m/%d %H:%M')}")

        next_offset = offset + page_size
        buttons = []
        if next_offset < len(results):
            buttons.append([InlineKeyboardButton("➡️ مشاهده‌ی ادامه‌ی لیست", callback_data=f"nearbymore:{radius}:{gender}:{next_offset}")])
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back:main")])

        await query.message.edit_text("\n\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()
        return

# ============================== USER SEARCH ==============================

async def user_search_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 به مخاطب مورد نظرم وصلم کن", callback_data="usearch:byid", style="primary")],
        [InlineKeyboardButton("🎂 هم‌سن‌ها", callback_data="usearch:sameage")],
        [InlineKeyboardButton("🗺 هم‌استانی‌ها", callback_data="usearch:sameprov")],
        [InlineKeyboardButton("🆕 کاربران جدید", callback_data="usearch:newest")],
        [InlineKeyboardButton("🔥 کاربران محبوب (بر اساس لایک)", callback_data="usearch:popular")],
    ])
    await update.message.reply_text("چه کسایی رو نشونت بدم؟ انتخاب کن👇", reply_markup=kb)
    row = get_user(update.effective_user.id)
    await maybe_send_profile_nudge(update, context, row)

async def usearch_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    row = get_user(user_id)
    data = query.data.split(":", 1)[1]

    if data == "byid":
        await query.message.edit_text("🆔 آیدی عددی، یوزرنیم تلگرام یا کد ربات (/user_XXXX) شخص مورد نظر رو ارسال کن:")
        update_user(user_id, state="await_search_byid")
        await query.answer()
        return

    conn = db()
    if data == "sameage":
        rows = conn.execute("SELECT * FROM users WHERE age=? AND user_id != ?", (row["age"], user_id)).fetchall()
    elif data == "sameprov":
        rows = conn.execute("SELECT * FROM users WHERE province=? AND user_id != ?", (row["province"], user_id)).fetchall()
    elif data == "newest":
        rows = conn.execute("SELECT * FROM users WHERE user_id != ? ORDER BY joined_at DESC LIMIT 15", (user_id,)).fetchall()
    elif data == "popular":
        rows = conn.execute("SELECT * FROM users WHERE user_id != ? ORDER BY likes DESC LIMIT 15", (user_id,)).fetchall()
    else:
        rows = []
    conn.close()

    if not rows:
        await query.message.edit_text("کاربری یافت نشد.")
        await query.answer()
        return

    lines = [f"{r['age']} 😐 {r['name'] or '—'}{vip_badge(r)} /user_{r['username_code']} {r['province']}({r['city']})" for r in rows[:15]]
    await query.message.edit_text("📋 نتایج:\n\n" + "\n".join(lines))
    await query.answer()

# ============================== CONNECT BY /user_CODE ==============================

async def user_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    cmd = update.message.text.strip()
    code = cmd.split("/user_", 1)[1]
    target = get_user_by_code(code)
    if not target:
        await update.message.reply_text("کاربر یافت نشد.")
        return
    if target["user_id"] == update.effective_user.id:
        text = profile_text(target)
        pkb = profile_keyboard(target)
        await send_profile_photo(context.bot, update.effective_user.id, target, text, pkb)
        return
    conn = db()
    blocked_me = conn.execute("SELECT 1 FROM blocklist WHERE owner_id=? AND blocked_id=?",
        (target["user_id"], update.effective_user.id)).fetchone()
    conn.close()
    if blocked_me:
        await update.message.reply_text("⚠️ امکان مشاهده‌ی این کاربر وجود ندارد.")
        return
    await show_full_profile(update, context, update.effective_user.id, target)

async def full_profile_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    action, target_id = query.data.split(":")
    target_id = int(target_id)
    row = get_user(user_id)
    target = get_user(target_id)
    if not target:
        await query.answer("کاربر یافت نشد.", show_alert=True)
        return

    if action == "reqchat":
        cost = 0 if is_vip(row) else 2
        if row["coins"] < cost:
            await query.answer(f"⚠️ سکه کافی نداری! ({cost} سکه مورد نیاز)", show_alert=True)
            return
        if cost:
            add_coins(user_id, -cost, source="spend_chat_request")
        await context.bot.send_message(target_id,
            f"📩 کاربری درخواست چت با شما رو فرستاده! (/user_{row['username_code']})",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ پذیرفتن", callback_data=f"pchat_ok:{user_id}", style="success"),
                 InlineKeyboardButton("❌ رد کردن", callback_data=f"pchat_no:{user_id}", style="danger")]
            ]),
        )
        await query.answer("✅ درخواست چت شما ارسال شد، منتظر پاسخ کاربر باش.", show_alert=True)
        return

    if action == "dm":
        cost = 0 if is_vip(row) else 1
        update_user(user_id, state="await_dm_text", pending_search=f"dmtarget:{target_id}:{cost}")
        await context.bot.send_message(user_id, f"📩 پیام دایرکتت رو برای /user_{target['username_code']} بنویس و بفرست:")
        await query.answer()
        return

    if action == "pblock":
        conn = db()
        conn.execute("INSERT OR IGNORE INTO blocklist (owner_id, blocked_id) VALUES (?,?)", (user_id, target_id))
        conn.commit()
        conn.close()
        await query.answer("🔒 این کاربر بلاک شد و دیگه نمی‌تونه باهات ارتباط بگیره.", show_alert=True)
        return

async def pchat_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, requester_id = query.data.split(":")
    requester_id = int(requester_id)
    if action == "pchat_ok":
        await connect_two_users(requester_id, update.effective_user.id, context)
        await query.message.edit_text("✅ درخواست پذیرفته شد و چت وصل شد.")
    else:
        await context.bot.send_message(requester_id, "❌ متاسفانه درخواست چت شما رد شد.")
        await query.message.edit_text("درخواست رد شد.")
    await query.answer()

# ============================== HELP ==============================

HELP_MAIN = (
    "🔹راهنمای استفاده از ربات:\n"
    "من اینجام که کمکت کنم! برای دریافت راهنمایی در مورد هر موضوع، کافیه دستور آبی رنگی که مقابل "
    "اون سوال هست رو لمس کنی:\n\n"
    "🔸 - چگونه بصورت ناشناس چت کنم؟ /help_chat\n"
    "🔸 - سکه یا امتیاز چیست؟ /help_credit\n"
    "🔸 - چگونه افراد نزدیکمو پیدا کنم؟ /help_gps\n"
    "🔸 - پروفایل چیست؟ /help_profile\n"
    "🔸 - چگونه درخواست چت بفرستم؟ /help_pchat\n"
    "🔸 - پیام دایرکت چیست؟ /help_direct\n"
    "🔸 - چگونه با میان بر ها کار کنم؟ /help_shortcuts\n"
    "🔸 - 🚫 قوانین استفاده از ربات /help_terms\n"
    "🔸 - اطلاع رسانی آنلاین شدن مخاطب /help_onw\n"
    "🔸 - اطلاع رسانی اتمام چت مخاطب /help_chw\n"
    "🔸 - مخاطبین چیست ؟ /help_contacts\n"
    "🔸 - آموزش حذف پیام در چت /help_deleteMessage\n"
    "🔸 - چگونه بصورت پیشرفته بین کاربران جستجو کنم ؟ /help_search"
)

HELP_TOPICS = {
    "help_chat": "برای چت ناشناس، از منوی پایین «به یه ناشناس وصلم کن!🌠» رو بزن و یکی از روش‌های جستجو رو انتخاب کن.",
    "help_credit": (
        "🔹 سکه یا امتیاز چیست؟\n\nشما با داشتن سکه میتوانید :\n\n"
        "- پیام دایرکت بفرستید (1 سکه)\n- درخواست چت بفرستید (2 سکه)\n"
        "- از جستجوی پسر یا جستجوی دختر استفاده کنید (1 سکه)\n"
        "- از جستجوی اطراف یا جستجو بر پایه‌ی استان با جنسیت مشخص استفاده کنید (4 سکه)\n"
        "- از «به محض آنلاین شدن اطلاع بده» استفاده کنید (1 سکه)\n\n"
        "🌟 کاربران VIP از همه‌ی این امکانات رایگان و نامحدود استفاده می‌کنن!\n\n"
        "📢 توجه: سکه فقط در صورتی کسر می‌شود که درخواست موفق باشد.\n\n"
        "❓ روش‌های بدست آوردن سکه چیست؟\n\n"
        f"1️⃣ هدیه‌ی ورود: همین که وارد ربات بشی {DEFAULT_START_COINS} سکه رایگان می‌گیری 🎁\n\n"
        f"2️⃣ تکمیل ثبت‌نام: با تکمیل ثبت‌نامت {PROFILE_COMPLETE_BONUS} سکه رایگان می‌گیری 👤\n\n"
        f"3️⃣ آپلود عکس پروفایل: با آپلود عکس پروفایلت {PHOTO_BONUS} سکه رایگان می‌گیری 🖼\n\n"
        f"4️⃣ معرفی دوستان: بنر لینک⚡️ مخصوص خودت (/link) رو برای دوستات بفرست و به ازای هرنفر که "
        f"وارد ربات بشه {REFERRAL_BONUS} سکه رایگان بگیر 😎"
    ),
    "help_gps": "با زدن دکمه «افراد نزدیک📌» و ثبت موقعیت GPS می‌تونی کاربران اطرافت رو پیدا کنی.",
    "help_profile": "پروفایل شامل نام، جنسیت، استان، شهر، سن و تعداد لایک‌های شماست. از دکمه «پروفایل👤» قابل مشاهده و ویرایشه.",
    "help_pchat": "با دستور /user_کد یا از بخش جستجوی کاربران می‌تونی برای کسی درخواست چت بفرستی.",
    "help_direct": "پیام دایرکت یعنی ارسال پیام مستقیم به یک کاربر خاص بدون نیاز به اتصال چت ناشناس.",
    "help_shortcuts": "میان‌برها همون دستورات سریع مثل /link و /user_کد هستن که مستقیم به بخش مربوطه می‌برنت.",
    "help_terms": (
        "🚫 قوانین استفاده از ربات:\n\n"
        "1️⃣ ارسال هرگونه محتوای غیر اخلاقی یا توهین‌آمیز ممنوع است.\n"
        "2️⃣ انتشار اطلاعات شخصی خود یا دیگران (شماره تماس، آدرس، مدارک) ممنوع است.\n"
        "3️⃣ تبلیغ کانال، ربات یا سایت دیگر ممنوع است.\n"
        "4️⃣ آزار، تهدید یا اذیت سایر کاربران ممنوع است.\n"
        "5️⃣ این ربات مخصوص کاربران بالای ۱۸ سال است.\n\n"
        "عدم رعایت قوانین منجر به مسدودی دائمی حساب کاربری می‌شود."
    ),
    "help_onw": "با فعال کردن این گزینه (نیازمند سکه) وقتی مخاطب موردنظرت آنلاین بشه بهت اطلاع داده می‌شه.",
    "help_chw": "وقتی طرف مقابل چت رو تموم کنه، بهت یک پیام سیستمی اطلاع میده.",
    "help_contacts": "مخاطبین لیستی از کاربرانیه که تو اونا رو ذخیره کردی تا راحت‌تر باهاشون در ارتباط باشی.",
    "help_search": "از بخش «جستوجوی کاربران🔍» می‌تونی بر اساس سن، استان، تازه‌واردها یا محبوبیت جستجو کنی.",
    "help_deleteMessage": "تا 30 دقیقه بعد از پایان چت، با دستور /delet_messages_کد می‌تونی پیام‌هات رو از طرف مقابل پاک کنی.",
}

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    await update.message.reply_text(HELP_MAIN)

async def help_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    cmd = update.message.text.strip().lstrip("/").split("@")[0]
    reply = HELP_TOPICS.get(cmd, "توضیحاتی برای این بخش ثبت نشده.")
    await update.message.reply_text(reply)

# ============================== MISC COMMANDS ==============================

async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    await send_invite_message(update, context)

async def anon_link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    row = get_user(update.effective_user.id)
    await update.message.reply_text(f"🔗 لینک ناشناس شما:\n{BOT_LINK}?start=inv_{row['username_code']}")

async def silent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    row = get_user(update.effective_user.id)
    new_state = 0 if row["silent"] else 1
    update_user(update.effective_user.id, silent=new_state)
    await update.message.reply_text("🔕 حالت سایلنت فعال شد." if new_state else "🔔 حالت سایلنت غیرفعال شد.")

async def on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    update_user(update.effective_user.id, same_age_only=1)
    await update.message.reply_text("🎂 جستجوی هم‌سن فعال شد؛ از این به بعد فقط با کاربرای هم‌سن خودت وصل می‌شی.")

async def off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    update_user(update.effective_user.id, same_age_only=0)
    await update.message.reply_text("📴 جستجوی هم‌سن غیرفعال شد.")

# ============================== ADMIN PANEL ==============================

def admin_panel_keyboard(owner):
    rows = [
        [InlineKeyboardButton("🪙 مدیریت سکه کاربر", callback_data="admin:coin", style="primary")],
        [InlineKeyboardButton("🔒 مسدود / رفع مسدود کاربر", callback_data="admin:block", style="danger")],
        [InlineKeyboardButton("🎁 اهدای اشتراک VIP 🌟", callback_data="admin:giftvip", style="primary")],
        [InlineKeyboardButton("📋 تیکت‌های باز", callback_data="admin:tickets")],
    ]
    if owner:
        rows.append([InlineKeyboardButton("➕ افزودن ادمین جدید", callback_data="admin:addadmin", style="success")])
    return InlineKeyboardMarkup(rows)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin_user(user_id):
        await update.message.reply_text("⛔️ این بخش فقط برای ادمین‌هاست.")
        return
    await update.message.reply_text(
        "🛠 <b>پنل مدیریت ایزی گپ</b>\n━━━━━━━━━━━━━━━━━\nیکی از گزینه‌های زیر رو انتخاب کن 👇",
        reply_markup=admin_panel_keyboard(user_id == ADMIN_ID),
        parse_mode="HTML",
    )

async def admin_panel_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if not is_admin_user(user_id):
        await query.answer("⛔️ فقط ادمین!", show_alert=True)
        return
    data = query.data

    if data == "admin:coin":
        update_user(user_id, state="admin_wait_target", pending_search="mode:coin")
        await query.message.edit_text("🪙 آیدی عددی یا کد کاربر (/user_XXXX) شخص مورد نظر رو ارسال کن:")
        await query.answer()
        return
    if data == "admin:block":
        update_user(user_id, state="admin_wait_target", pending_search="mode:block")
        await query.message.edit_text("🔒 آیدی عددی یا کد کاربر (/user_XXXX) شخص مورد نظر رو ارسال کن:")
        await query.answer()
        return
    if data == "admin:giftvip":
        update_user(user_id, state="admin_wait_target", pending_search="mode:giftvip")
        await query.message.edit_text("🎁 آیدی عددی یا کد کاربر (/user_XXXX) شخصی که می‌خوای بهش VIP هدیه بدی رو ارسال کن:")
        await query.answer()
        return
    if data == "admin:addadmin":
        if user_id != ADMIN_ID:
            await query.answer("⛔️ فقط مالک ربات می‌تونه ادمین اضافه کنه.", show_alert=True)
            return
        update_user(user_id, state="admin_wait_target", pending_search="mode:addadmin")
        await query.message.edit_text("➕ آیدی عددی یا کد کاربر (/user_XXXX) شخصی که می‌خوای ادمین کنی رو ارسال کن:")
        await query.answer()
        return
    if data == "admin:tickets":
        conn = db()
        rows = conn.execute("SELECT * FROM tickets WHERE status='open' ORDER BY id DESC LIMIT 15").fetchall()
        conn.close()
        if not rows:
            await query.message.edit_text("✅ هیچ تیکت باز وجود ندارد.")
            await query.answer()
            return
        await query.message.edit_text(f"📋 {len(rows)} تیکت باز پیدا شد، به‌ترتیب ارسال می‌شن 👇")
        for t in rows:
            target = get_user(t["user_id"])
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ پاسخ و رفع مسدودی", callback_data=f"tkok:{t['id']}", style="success"),
                 InlineKeyboardButton("❌ رد تیکت", callback_data=f"tkno:{t['id']}", style="danger")]
            ])
            await context.bot.send_message(user_id,
                f"📩 تیکت #{t['id']}\n👤 کاربر: {t['user_id']} (/user_{target['username_code'] if target else '?'})\n\n📝 متن:\n{t['text']}",
                reply_markup=kb,
            )
        await query.answer()
        return

    if data.startswith("admin:coinamt:"):
        _, _, target_id, delta = data.split(":")
        target_id, delta = int(target_id), int(delta)
        await add_coins_checked(target_id, delta, "admin_grant", context)
        newrow = get_user(target_id)
        await query.message.edit_text(f"✅ انجام شد. سکه کاربر /user_{newrow['username_code']} اکنون: {newrow['coins']}")
        try:
            await context.bot.send_message(target_id,
                f"🔔 موجودی سکه شما توسط پشتیبانی {'افزایش' if delta > 0 else 'کاهش'} یافت "
                f"({'+' if delta > 0 else ''}{delta} سکه). موجودی فعلی: {newrow['coins']}"
            )
        except Exception:
            pass
        await query.answer()
        return

    if data.startswith("admin:coincustom:"):
        target_id = int(data.split(":")[2])
        update_user(user_id, state="admin_wait_coin_amount", pending_search=f"coin:{target_id}")
        await query.message.edit_text("🔢 مقدار سکه رو وارد کن (برای کم کردن، عدد منفی بفرست، مثلاً -20):")
        await query.answer()
        return

    if data.startswith("admin:blockdo:"):
        target_id = int(data.split(":")[2])
        update_user(user_id, state="admin_wait_block_reason", pending_search=f"block:{target_id}")
        await query.message.edit_text("📝 دلیل مسدودسازی این کاربر رو بنویس:")
        await query.answer()
        return

    if data.startswith("admin:unblockdo:"):
        target_id = int(data.split(":")[2])
        update_user(target_id, is_blocked=0, block_reason=None)
        target = get_user(target_id)
        await query.message.edit_text(f"✅ کاربر /user_{target['username_code']} از مسدودی خارج شد.")
        try:
            await context.bot.send_message(target_id, "✅ اکانت شما از حالت مسدودی خارج شد. خوش برگشتی!", reply_markup=MAIN_MENU)
        except Exception:
            pass
        await query.answer()
        return

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE, row, text):
    user_id = update.effective_user.id
    state = row["state"]
    pending = row["pending_search"] or ""

    if state == "admin_wait_target":
        if text.strip() in ("بازگشت", "لغو", "/cancel"):
            update_user(user_id, state=None, pending_search=None)
            await update.message.reply_text("عملیات لغو شد.", reply_markup=MAIN_MENU)
            return
        mode = pending.split(":", 1)[1] if ":" in pending else ""
        target = resolve_target_user(text)
        if not target:
            await update.message.reply_text("⚠️ کاربری پیدا نشد. دوباره آیدی عددی یا کد /user_XXXX رو بفرست (یا برای لغو بنویس «بازگشت»):")
            return
        update_user(user_id, state=None, pending_search=None)

        if mode == "coin":
            info = (f"👤 کاربر: {target['name'] or '—'}{vip_badge(target)}\n"
                    f"🆔 /user_{target['username_code']}\n"
                    f"💰 سکه فعلی: {target['coins']}\n\n"
                    "چقدر سکه اضافه یا کم کنم؟")
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕10", callback_data=f"admin:coinamt:{target['user_id']}:10", style="success"),
                 InlineKeyboardButton("➕50", callback_data=f"admin:coinamt:{target['user_id']}:50", style="success"),
                 InlineKeyboardButton("➕100", callback_data=f"admin:coinamt:{target['user_id']}:100", style="success")],
                [InlineKeyboardButton("➖10", callback_data=f"admin:coinamt:{target['user_id']}:-10", style="danger"),
                 InlineKeyboardButton("➖50", callback_data=f"admin:coinamt:{target['user_id']}:-50", style="danger"),
                 InlineKeyboardButton("➖100", callback_data=f"admin:coinamt:{target['user_id']}:-100", style="danger")],
                [InlineKeyboardButton("🔢 مقدار دلخواه", callback_data=f"admin:coincustom:{target['user_id']}")],
            ])
            await update.message.reply_text(info, reply_markup=kb)
            return

        if mode == "block":
            if target["is_blocked"]:
                info = f"👤 کاربر /user_{target['username_code']} در حال حاضر مسدود است.\n📝 دلیل: {target['block_reason'] or '—'}"
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ رفع مسدودی", callback_data=f"admin:unblockdo:{target['user_id']}", style="success")]])
            else:
                info = f"👤 کاربر /user_{target['username_code']} در حال حاضر آزاد است."
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔒 مسدود کردن", callback_data=f"admin:blockdo:{target['user_id']}", style="danger")]])
            await update.message.reply_text(info, reply_markup=kb)
            return

        if mode == "addadmin":
            update_user(target["user_id"], is_admin=1)
            await update.message.reply_text(f"✅ کاربر /user_{target['username_code']} اکنون ادمین ربات است.")
            try:
                await context.bot.send_message(target["user_id"], "🎉 شما توسط مالک ربات به عنوان ادمین ایزی گپ منصوب شدید!")
            except Exception:
                pass
            return

        if mode == "giftvip":
            until = grant_vip(target["user_id"], VIP_DURATION_DAYS)
            await update.message.reply_text(
                f"🎁 اشتراک VIP به کاربر /user_{target['username_code']} هدیه داده شد.\n"
                f"🌟 فعال تا تاریخ: {until.strftime('%Y-%m-%d')}"
            )
            try:
                await context.bot.send_message(
                    target["user_id"],
                    f"🎁🌟 تبریک! پشتیبانی ایزی گپ یه اشتراک VIP به شما هدیه داد!\n"
                    f"فعال تا تاریخ {until.strftime('%Y-%m-%d')} — از امکانات ویژه‌ت لذت ببر 🎉",
                )
            except Exception:
                pass
            return
        return

    if state == "admin_wait_coin_amount":
        target_id = int(pending.split(":", 1)[1])
        text_en = to_en_digits(text)
        try:
            delta = int(text_en)
        except ValueError:
            await update.message.reply_text("⚠️ فقط عدد وارد کن (مثبت یا منفی):")
            return
        update_user(user_id, state=None, pending_search=None)
        await add_coins_checked(target_id, delta, "admin_grant", context)
        newrow = get_user(target_id)
        await update.message.reply_text(f"✅ انجام شد. سکه کاربر اکنون: {newrow['coins']}")
        try:
            await context.bot.send_message(target_id,
                f"🔔 موجودی سکه شما توسط پشتیبانی تغییر کرد ({'+' if delta>0 else ''}{delta}). موجودی فعلی: {newrow['coins']}"
            )
        except Exception:
            pass
        return

    if state == "admin_wait_block_reason":
        target_id = int(pending.split(":", 1)[1])
        update_user(user_id, state=None, pending_search=None)
        update_user(target_id, is_blocked=1, block_reason=text)
        # Also permanently tie this user's verified phone number to the ban so
        # a brand new Telegram account with the same number gets auto-blocked.
        ban_phone_for_user(target_id, reason=text)
        target = get_user(target_id)
        await update.message.reply_text(f"✅ کاربر /user_{target['username_code']} مسدود شد.")
        try:
            await context.bot.send_message(target_id,
                "‼️ متاسفانه اکانت شما به دلیل گزارش کاربران و عدم رعایت قوانین توسط پشتیبانی ربات مسدود شده است\n\n"
                f"🆔 /user_{target['username_code']}\n📝 دلیل: {text}\n\n"
                "در صورتی که به‌ناحق مسدود شدید، از دکمه‌ی زیر تیکت اعتراض بفرستید 👇",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📝 ارسال تیکت اعتراض", callback_data="ticket:new", style="primary")]]),
            )
        except Exception:
            pass
        return

# ============================== MAIN MENU ROUTER ==============================

async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    text = update.message.text

    if text == "به یه ناشناس وصلم کن!🌠":
        await anon_connect_entry(update, context)
    elif text == "افراد نزدیک📌":
        await nearby_entry(update, context)
    elif text == "جستوجوی کاربران🔍":
        await user_search_entry(update, context)
    elif text == "سکه🪙":
        await show_coins(update, context)
    elif text == "🌟 اشتراک VIP":
        await show_vip(update, context)
    elif text == "پروفایل👤":
        await show_profile(update, context)
    elif text == "راهنما📒":
        await help_command(update, context)
    elif text == "معرفی به دوستان ( سکه ی رایگان🪙✅ )":
        await send_invite_message(update, context)
    elif text == "لینک ناشناس من":
        await anon_link_command(update, context)
    elif text == "بازگشت":
        await update.message.reply_text("خب حالا چه کاری برات انجام بدم؟", reply_markup=MAIN_MENU)
    else:
        row = get_user(update.effective_user.id)
        if row and row["state"] == "await_search_byid":
            await handle_search_byid(update, context, text)
        else:
            await update.message.reply_text("متوجه نشدم، لطفا از دکمه‌های پایین استفاده کن 👇", reply_markup=MAIN_MENU)

async def handle_search_byid(update, context, text):
    user_id = update.effective_user.id
    update_user(user_id, state=None)
    if text.strip() in ("بازگشت", "لغو", "/cancel"):
        await update.message.reply_text("خب حالا چه کاری برات انجام بدم؟", reply_markup=MAIN_MENU)
        return
    target = None
    if text.startswith("/user_"):
        target = get_user_by_code(text.split("/user_", 1)[1])
    elif text.lstrip("-").isdigit():
        target = get_user(int(text))
    if not target:
        await update.message.reply_text("کاربر یافت نشد.", reply_markup=MAIN_MENU)
        return
    await update.message.reply_text(
        f"کاربر پیدا شد: {target['name'] or '—'} /user_{target['username_code']}\n"
        f"برای ارسال درخواست چت، دستور /user_{target['username_code']} رو بزن."
    )

# ============================== DISPATCH CALLBACK ROUTER ==============================

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data == "ticket:new":
        await ticket_new_callback(update, context)
        return
    if data.startswith(("tkok:", "tkno:")):
        await ticket_decision_callback(update, context)
        return

    row = get_user(update.effective_user.id)
    if row and row["is_blocked"]:
        await update.callback_query.answer("⛔️ اکانت شما مسدود است.", show_alert=True)
        return

    if data.startswith("admin:"):
        await admin_panel_callbacks(update, context)
        return
    if data.startswith("vip:"):
        await vip_callbacks(update, context)
        return
    if data.startswith(("reqchat:", "dm:", "pblock:")):
        await full_profile_callbacks(update, context)
        return
    if data == "check_membership":
        await check_membership_cb(update, context)
        return
    if data.startswith("gender:"):
        row = get_user(update.effective_user.id)
        if row and row["pending_search"] == "editgender":
            if await editgender_cb_wrap(update, context):
                return
        await registration_callback(update, context)
        return
    if data.startswith(("age:", "province:", "city:")):
        await registration_callback(update, context)
        return
    if data.startswith(("editf:", "cityedit:", "edit_profile", "back:profile", "my_gps", "my_likers", "my_contacts", "profile_complete_start", "adv_settings", "adv:")):
        await profile_callbacks(update, context)
        return
    if data == "back:main":
        await profile_callbacks(update, context)
        return
    if data.startswith(("search:", "matchprov:", "provconn:", "nearbygender:", "sameage:toggle:")) or data == "cancelsearch":
        await search_callbacks(update, context)
        return
    if data.startswith(("radius:", "nearbyf:", "nearbymore:")):
        await nearby_callbacks(update, context)
        return
    if data.startswith("usearch:"):
        await usearch_callbacks(update, context)
        return
    if data.startswith("chat:"):
        await chat_menu_callbacks(update, context)
        return
    if data.startswith(("shipok:", "shipno:", "shipchan:")):
        await ship_callbacks(update, context)
        return
    if data.startswith(("show_invite", "buy:")):
        await coin_callbacks(update, context)
        return
    if data.startswith(("pay_ok:", "pay_no:")):
        await admin_payment_decision(update, context)
        return
    if data.startswith(("pchat_ok:", "pchat_no:")):
        await pchat_decision(update, context)
        return
    if data.startswith(("addcontact:", "removecontact:", "notifyon:", "report:")):
        await contact_profile_actions(update, context)
        return
    if data.startswith("reportreason:"):
        await report_reason_callback(update, context)
        return
    if data.startswith(("cutrel:", "cutrelconfirm:", "cutrelcancel:")):
        await breakup_callbacks(update, context)
        return

    await update.callback_query.answer()

# ============================== TEXT / COMMAND CATCH-ALL ==============================

async def generic_command_catch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    row = get_user(user_id)

    if row:
        if row["state"] == "await_ticket_text":
            await handle_ticket_text(update, context, text)
            return
        if row["state"] and row["state"].startswith("admin_wait_") and is_admin_user(user_id):
            await handle_admin_text(update, context, row, text)
            return
        if row["state"] == "await_search_byid":
            await handle_search_byid(update, context, text)
            return
        if row["state"] == "await_dm_text" and row["pending_search"] and row["pending_search"].startswith("dmtarget:"):
            await free_text_router(update, context)
            return

    if text.startswith("/user_"):
        await user_code_command(update, context)
        return
    if text.startswith("/delet_messages_"):
        await delete_messages_command(update, context, text.split("/delet_messages_", 1)[1])
        return
    if not await require_ready(update, context):
        return
    await update.message.reply_text("دستور نامعتبر است.")

async def delete_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE, session_code: str):
    user_id = update.effective_user.id
    ended_at = context.bot_data.get("session_ended_at", {}).get(session_code)
    if not ended_at:
        await update.message.reply_text("⚠️ این لینک حذف پیام معتبر نیست یا منقضی شده.")
        return
    elapsed_min = (datetime.now() - datetime.fromisoformat(ended_at)).total_seconds() / 60
    if elapsed_min > 30:
        await update.message.reply_text("⚠️ مهلت 30 دقیقه‌ای برای حذف پیام‌ها به پایان رسیده.")
        return

    conn = db()
    rows = conn.execute("SELECT * FROM messages_log WHERE chat_session=? AND sender_id=?", (session_code, user_id)).fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("پیامی برای حذف پیدا نشد.")
        return

    deleted = 0
    for r in rows:
        try:
            await context.bot.delete_message(chat_id=r["receiver_id"], message_id=r["receiver_msg_id"])
            deleted += 1
        except Exception:
            pass

    await update.message.reply_text(f"🗑 {deleted} پیام از چت طرف مقابل حذف شد.")

# ============================== WEB SERVER FOR RENDER ==============================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_web_server():
    server = HTTPServer(("0.0.0.0", 8000), HealthHandler)
    server.serve_forever()

# ============================== APP SETUP ==============================

def build_help_handlers(app):
    for topic in HELP_TOPICS:
        app.add_handler(CommandHandler(topic, help_topic_command))

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Catches any exception raised inside a handler. Without this, a crash
    (e.g. a missing file, a bad callback, a DB error) is only written to the
    log and the user sees nothing at all — this is what made buttons like
    «پروفایل» look 'completely dead' when something failed underneath them."""
    logger.exception("Unhandled exception while processing update: %s", update)
    try:
        if isinstance(update, Update) and update.effective_user:
            chat_id = update.effective_user.id
            await context.bot.send_message(
                chat_id,
                "⚠️ یه خطای غیرمنتظره پیش اومد، دوباره امتحان کن. اگه ادامه داشت، لطفا با پشتیبانی تماس بگیر.",
                reply_markup=MAIN_MENU,
            )
    except Exception:
        logger.exception("Failed to notify user about the error.")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("vip", show_vip))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("silent", silent_command))
    app.add_handler(CommandHandler("on", on_command))
    app.add_handler(CommandHandler("off", off_command))
    build_help_handlers(app)

    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_router))
    app.add_handler(
        MessageHandler(filters.Regex(r"^/user_") | filters.Regex(r"^/delet_messages_"), generic_command_catch)
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text_router))

    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_error_handler(global_error_handler)

    # راه‌اندازی وب‌سرور برای پینگ (Render)
    threading.Thread(target=start_web_server, daemon=True).start()
    logger.info("Web server started on port 8000 for health checks.")

    logger.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
