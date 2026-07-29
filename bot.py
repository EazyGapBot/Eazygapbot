import os   # این خط رو اول اضافه کن
import sqlite3
import random
import string
import math
import logging
from datetime import datetime

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
# توکن رو از محیط می‌خونیم (اینجا دیگه توکن نوشته نشده)
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

COIN_PACKAGES = [
    (320, 140000),
    (540, 216000),
    (1500, 350000),
    (2000, 700000),
]

PROVINCES = {
    "تهران": ["تهران", "شهریار", "اسلامشهر", "ورامین", "پاکدشت"],
    "اصفهان": ["اصفهان", "کاشان", "نجف‌آباد", "خمینی‌شهر"],
    "فارس": ["شیراز", "مرودشت", "جهرم", "کازرون"],
    "خراسان رضوی": ["مشهد", "نیشابور", "سبزوار", "تربت حیدریه"],
    "آذربایجان شرقی": ["تبریز", "مراغه", "میانه"],
    "آذربایجان غربی": ["ارومیه", "خوی", "مهاباد"],
    "بوشهر": ["بوشهر", "بندرکنگان", "دشتستان"],
    "خوزستان": ["اهواز", "آبادان", "دزفول"],
    "کرمان": ["کرمان", "سیرجان", "رفسنجان"],
    "گیلان": ["رشت", "انزلی", "لاهیجان"],
    "مازندران": ["ساری", "بابل", "آمل", "قائم‌شهر"],
    "البرز": ["کرج", "نظرآباد", "فردیس"],
    "قم": ["قم"],
    "یزد": ["یزد", "میبد", "اردکان"],
    "کرمانشاه": ["کرمانشاه", "اسلام‌آباد غرب"],
    "هرمزگان": ["بندرعباس", "میناب", "قشم"],
    "سیستان و بلوچستان": ["زاهدان", "زابل", "چابهار"],
    "کردستان": ["سنندج", "سقز", "مریوان"],
    "همدان": ["همدان", "ملایر", "نهاوند"],
    "لرستان": ["خرم‌آباد", "بروجرد", "دورود"],
    "مرکزی": ["اراک", "ساوه", "خمین"],
    "قزوین": ["قزوین", "تاکستان"],
    "زنجان": ["زنجان", "ابهر"],
    "گلستان": ["گرگان", "گنبدکاووس", "علی‌آباد"],
    "اردبیل": ["اردبیل", "مشگین‌شهر", "پارس‌آباد"],
    "سمنان": ["سمنان", "شاهرود", "دامغان"],
    "چهارمحال و بختیاری": ["شهرکرد", "بروجن"],
    "کهگیلویه و بویراحمد": ["یاسوج", "گچساران"],
    "ایلام": ["ایلام", "دهلران"],
    "خراسان جنوبی": ["بیرجند", "قائنات"],
    "خراسان شمالی": ["بجنورد", "شیروان"],
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
    c.execute(
        """
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
            invite_count INTEGER DEFAULT 0
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS messages_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_session TEXT,
            sender_id INTEGER,
            receiver_id INTEGER,
            sender_msg_id INTEGER,
            receiver_msg_id INTEGER,
            created_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            coins INTEGER,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS likes (
            liker_id INTEGER,
            liked_id INTEGER,
            PRIMARY KEY (liker_id, liked_id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            owner_id INTEGER,
            contact_id INTEGER,
            PRIMARY KEY (owner_id, contact_id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            target_id INTEGER,
            reason TEXT,
            created_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS notify_requests (
            watcher_id INTEGER,
            target_id INTEGER,
            created_at TEXT,
            PRIMARY KEY (watcher_id, target_id)
        )
        """
    )
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
    row = conn.execute(
        "SELECT * FROM users WHERE username_code=?", (code,)
    ).fetchone()
    conn.close()
    return row


def create_user_if_missing(user_id, invited_by=None):
    if get_user(user_id):
        return
    conn = db()
    code = gen_code()
    while conn.execute(
        "SELECT 1 FROM users WHERE username_code=?", (code,)
    ).fetchone():
        code = gen_code()
    conn.execute(
        """INSERT INTO users (user_id, username_code, coins, invited_by, joined_at, last_seen, reg_step)
           VALUES (?, ?, 0, ?, ?, ?, 'gender')""",
        (user_id, code, invited_by, datetime.now().isoformat(), datetime.now().isoformat()),
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
    watchers = conn.execute(
        "SELECT watcher_id FROM notify_requests WHERE target_id=?", (user_id,)
    ).fetchall()
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


def add_coins(user_id, amount):
    conn = db()
    conn.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


def is_registered(row):
    return row and row["reg_step"] is None and row["gender"] and row["age"] and row["province"] and row["city"]


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ============================== KEYBOARDS ==============================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("به یه ناشناس وصلم کن!🌠")],
        [KeyboardButton("افراد نزدیک📌"), KeyboardButton("جستوجوی کاربران🔍")],
        [KeyboardButton("سکه🪙"), KeyboardButton("پروفایل👤")],
        [KeyboardButton("راهنما📒")],
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
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("پسر", callback_data="gender:پسر"),
                InlineKeyboardButton("دختر", callback_data="gender:دختر"),
            ]
        ]
    )


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
    rows.append([InlineKeyboardButton("بررسی عضویت و فعال‌سازی🔮", callback_data="check_membership")])
    return InlineKeyboardMarkup(rows)


def coin_shop_keyboard():
    rows = [[InlineKeyboardButton("معرفی به دوستان", callback_data="show_invite")]]
    for coins, price in COIN_PACKAGES:
        rows.append(
            [InlineKeyboardButton(f"خرید {coins} سکه: {price:,} تومان", callback_data=f"buy:{coins}:{price}")]
        )
    return InlineKeyboardMarkup(rows)


FOOTER = "🔒 SECURE   ⚡ FAST   ♾️ UNLIMITED   🕶 PRIVATE"


def back_keyboard(target="back:main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data=target)]])


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

    if is_new and invited_by:
        add_coins(invited_by, 20)
        update_user(invited_by, invite_count=(get_user(invited_by)["invite_count"] or 0) + 1)
        try:
            await context.bot.send_message(
                invited_by, "🎉 یک نفر با لینک دعوت شما وارد ربات شد و 20 سکه رایگان دریافت کردید!"
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
            f"✨ خوش برگشتی!\n\nخب حالا چه کاری برات انجام بدم؟\n\n{FOOTER}", reply_markup=MAIN_MENU
        )
        return

    # begin / continue registration
    step = row["reg_step"] or "gender"
    if step == "gender":
        await update.message.reply_text("❓ لطفا جنسیت خود را انتخاب کنید 👇", reply_markup=gender_keyboard())
    elif step == "age":
        await ask_age(update.message, context)
    elif step == "province":
        await update.message.reply_text(
            "سن شما ثبت شد\n\n• استانت رو از لیست پایین 👇انتخاب کن", reply_markup=province_keyboard()
        )
    elif step == "city":
        await update.message.reply_text(
            "استان شما ثبت شد ، خب حالا فقط کافیه شهر خودت رو انتخاب کنی تا وارد ربات شیم\n\n"
            "• شهرستانت رو از لیست پایین 👇انتخاب کن",
            reply_markup=city_keyboard(row["province"]),
        )


async def ask_age(message_target, context):
    await message_target.reply_text(
        "• سنت رو از لیست پایین 👇انتخاب کن یا خودت تایپ کن:", reply_markup=age_keyboard()
    )


async def send_membership_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (
        f"({user_id}) عزیز برای استفاده از ربات ابتدا باید در کانال(های) زیر عضو بشی 👇\n\n"
        + "\n".join(f"👉{ch}" for ch in REQUIRED_CHANNELS)
        + "\n\nبعد از عضویت، دکمه «بررسی عضویت و فعال‌سازی🔮» را بزن\n\nاز منوی پایین👇🏻 انتخاب کن:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=membership_keyboard())
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=membership_keyboard())


async def registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    row = get_user(user_id)
    data = query.data

    if data.startswith("gender:"):
        gender = data.split(":", 1)[1]
        update_user(user_id, gender=gender, reg_step="age")
        await query.message.edit_text("سن شما ثبت شد")
        await ask_age(query.message, context)
        await query.answer()
        return

    if data.startswith("age:"):
        age = int(data.split(":", 1)[1])
        update_user(user_id, age=age, reg_step="province")
        await query.message.edit_text(
            "سن شما ثبت شد\n\n• استانت رو از لیست پایین 👇انتخاب کن", reply_markup=province_keyboard()
        )
        await query.answer()
        return

    # ================ خط اصلاح‌شده اینجاست ================
    if data.startswith("province:") and row["reg_step"] == "province":
        province = data.split(":", 1)[1]
        update_user(user_id, province=province, reg_step="city")
        await query.message.edit_text(
            "استان شما ثبت شد ، خب حالا فقط کافیه شهر خودت رو انتخاب کنی تا وارد ربات شیم\n\n"
            "• شهرستانت رو از لیست پایین 👇انتخاب کن",
            reply_markup=city_keyboard(province),
        )
        await query.answer()
        return
    # ====================================================

    if data.startswith("city:") and row["reg_step"] == "city":
        city = data.split(":", 1)[1]
        update_user(user_id, city=city, reg_step=None)
        await query.message.edit_text(
            "✅اطلاعات شما ثبت شد.\n\n"
            "به خانواده بزرگ《ایزی گپ🤖》 خوش اومدی بهت توصیه میکنم اول از همه با لمس کردن "
            "《🤔 راهنما》 با ربات آشنا شی!"
        )
        ok = await is_member_of_all(context, user_id)
        if not ok:
            gate_text = (
                f"({user_id}) عزیز برای استفاده از ربات ابتدا باید در کانال(های) زیر عضو بشی 👇\n\n"
                + "\n".join(f"👉{ch}" for ch in REQUIRED_CHANNELS)
                + "\n\nبعد از عضویت، دکمه «بررسی عضویت و فعال‌سازی🔮» را بزن\n\nاز منوی پایین👇🏻 انتخاب کن:"
            )
            await context.bot.send_message(user_id, gate_text, reply_markup=membership_keyboard())
        else:
            await context.bot.send_message(user_id, "خب حالا چه کاری برات انجام بدم؟", reply_markup=MAIN_MENU)
        await query.answer()
        return

    # age typed instead of button will be handled by text handler; ignore stale province/city clicks mismatched with step
    await query.answer()


async def registration_text_guard(update: Update, context: ContextTypes.DEFAULT_TYPE, row):
    """Handles free-text input during forced registration (age typed manually)."""
    text = update.message.text.strip()
    step = row["reg_step"]
    if step == "age":
        if text.isdigit() and MIN_AGE <= int(text) <= MAX_AGE:
            update_user(update.effective_user.id, age=int(text), reg_step="province")
            await update.message.reply_text(
                "سن شما ثبت شد\n\n• استانت رو از لیست پایین 👇انتخاب کن", reply_markup=province_keyboard()
            )
        else:
            await update.message.reply_text(
                f"⚠️ لطفا فقط عدد بین {MIN_AGE} تا {MAX_AGE} وارد کن یا از دکمه‌های بالا انتخاب کن."
            )
        return
    # any other step: registration must be completed via buttons
    await update.message.reply_text("لطفا از دکمه‌های بالا برای تکمیل ثبت‌نام استفاده کن 👆")


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
    """Returns True if user can proceed (registered + member). Otherwise handles the reply itself."""
    user_id = update.effective_user.id
    row = get_user(user_id)
    if row is None:
        await start(update, context)
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
        f"• نام: {row['name'] or '—'}",
        f"• جنسیت: {row['gender']}",
        f"• استان: {row['province']}",
        f"• شهر: {row['city']}",
        f"• سن: {row['age']}",
    ]
    if viewer_is_self:
        lines.append(f"\n• تعداد لایک ها: {row['likes']}")
        lines.append(f"\n{online} (🗣)")
        lines.append(f"\n🆔 آیدی : /user_{row['username_code']}")
        lines.append("\nتنظیم حالت سایلنت : /silent")
        lines.append("\nحذف اکانت ربات : /deleted_account")
    return "\n".join(lines)


def profile_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("مشاهده موقعیت GPS من", callback_data="my_gps")],
            [InlineKeyboardButton("مشاهده لایک کننده ها", callback_data="my_likers")],
            [InlineKeyboardButton("لیست مخاطبین", callback_data="my_contacts")],
            [InlineKeyboardButton("ویرایش پروفایل", callback_data="edit_profile")],
        ]
    )


def contact_profile_keyboard(target_id):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ افزودن به مخاطبین", callback_data=f"addcontact:{target_id}")],
            [InlineKeyboardButton("🔔 اطلاع بده وقتی آنلاین شد (1 سکه)", callback_data=f"notifyon:{target_id}")],
            [InlineKeyboardButton("🚫 گزارش کاربر", callback_data=f"report:{target_id}")],
        ]
    )


def edit_profile_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("تغییر جنسیت", callback_data="editf:gender")],
            [InlineKeyboardButton("تغییر نام", callback_data="editf:name")],
            [InlineKeyboardButton("تغییر سن", callback_data="editf:age")],
            [InlineKeyboardButton("تغییر شهر", callback_data="editf:city")],
            [InlineKeyboardButton("تغییر عکس پروفایل", callback_data="editf:photo")],
            [InlineKeyboardButton("تغییر موقعیت GPS", callback_data="editf:gps")],
            [InlineKeyboardButton("بازگشت", callback_data="back:profile")],
        ]
    )


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    row = get_user(update.effective_user.id)
    text = profile_text(row)
    if row["photo_file_id"]:
        await update.message.reply_photo(row["photo_file_id"], caption=text, reply_markup=profile_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=profile_keyboard())


async def profile_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    row = get_user(user_id)
    data = query.data

    if data == "edit_profile":
        await query.message.edit_reply_markup(reply_markup=edit_profile_keyboard())
        await query.answer()
        return

    if data == "back:profile":
        await query.message.edit_reply_markup(reply_markup=profile_keyboard())
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
        rows = conn.execute(
            "SELECT contact_id FROM contacts WHERE owner_id=?", (user_id,)
        ).fetchall()
        conn.close()
        if not rows:
            await query.answer("لیست مخاطبینت خالیه!", show_alert=True)
        else:
            names = []
            for r in rows[:20]:
                u = get_user(r["contact_id"])
                if u:
                    names.append(f"{u['name'] or '—'} (/user_{u['username_code']})")
            await query.message.reply_text("👥 مخاطبین شما:\n\n" + "\n".join(names))
        await query.answer()
        return

    if data.startswith("editf:"):
        field = data.split(":", 1)[1]
        if field == "gender":
            await query.message.edit_text("جنسیت جدید رو انتخاب کن 👇", reply_markup=gender_keyboard())
            update_user(user_id, pending_search="editgender")
        elif field == "name":
            await query.message.edit_text(
                "⚠️ توجه کنید : با توجه به این که پروفایل کاربران به صورت عمومی قابل مشاهده است ، "
                "در صورت رعایت نکردن قوانین زیر حساب کاربری شما بصورت دائمی مسدود خواهد شد.\n\n"
                "1️⃣ هرگونه محتوای غیر اخلاقی یا توهین آمیز در پروفایل ( عکس یا متن )\n"
                "2️⃣ پخش شماره موبایل یا اطلاعات شخصی دیگران\n"
                "3️⃣ تبلیغات کانال ، ربات و یا سایت\n\n"
                "❓ لطفا نام خود را به صورت متن ارسال کنید .\n👇👇👇",
                reply_markup=back_keyboard("back:profile"),
            )
            update_user(user_id, state="await_name")
        elif field == "age":
            await query.message.edit_text("سن جدید رو انتخاب کن یا تایپ کن 👇", reply_markup=age_keyboard())
            update_user(user_id, state="await_age_edit")
        elif field == "city":
            await query.message.edit_text(
                "شهر جدید رو انتخاب کن 👇", reply_markup=city_keyboard(row["province"], prefix="cityedit")
            )
        elif field == "photo":
            await query.message.edit_text(
                "📷 لطفا عکس پروفایل جدید خودت رو ارسال کن (فقط عکس قابل قبوله):",
                reply_markup=back_keyboard("back:profile"),
            )
            update_user(user_id, state="await_photo")
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

    if data == "back:main":
        await query.message.delete()
        await context.bot.send_message(user_id, "خب حالا چه کاری برات انجام بدم؟", reply_markup=MAIN_MENU)
        await query.answer()
        return


async def editgender_cb_wrap(update, context):
    # reuse gender: callback but write directly instead of registration flow if editing
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
    text = (
        "⚠️ هنگام ارسال موقعیت مکانی مطمعن شوید GPS موبایل شما روشن است.\n\n"
        "✅ کسی قادر به دیدن موقعیت مکانی شما در ربات نخواهد بود و فقط برای تخمین فاصله و "
        "یافتن افراد نزدیک کاربرد خواهد داشت\n\n"
        "❓موقعیت GPS خود را ارسال کنید👇"
    )
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
    row = get_user(user_id)
    if row["pending_search"] == "nearby_wait_radius" or True:
        pass
    await update.message.reply_text(
        "✏️ تغییر موقعیت GPS با موفقیت انجام شد ☑️\n\nخب ، حالا چه کاری برات انجام بدم؟\n\nاز منوی پایین👇 انتخاب کن",
        reply_markup=MAIN_MENU,
    )


# ============================== COINS / PAYMENT ==============================


async def show_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    row = get_user(update.effective_user.id)
    text = (
        f"💰سکه فعلی شما : {row['coins']}\n"
        "ــــــــــــــــــــــــــــــــــــــــ\n\n"
        "❓روش های بدست آوردن سکه چیست؟\n\n"
        "1️⃣ معرفی دوستان (رایگان) :\n\n"
        "برای افزایش سکه به صورت رایگان بنر لینک⚡️ مخصوص خودت (/link) رو برای دوستات "
        "بفرست و 20 سکه دریافت کن\n\n"
        "2️⃣ خرید سکه بصورت آنلاین :\n\n"
        "برای خرید سکه یکی از تعرفه های زیر را انتخب نمایید👇"
    )
    await update.message.reply_text(text, reply_markup=coin_shop_keyboard())


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
        coins, price = int(coins), int(price)
        rial = price * 10
        amount_str = f"{price:,}".replace(",", ",")
        text = (
            "💎 لطفاً دقیقاً مبلغ زیر را به شماره کارت واریز کنید:\n\n"
            f"💰 مبلغ قابل پرداخت:\n`{price:,} تومان`\n`{rial:,} ریال`\n\n"
            f"💳 شماره کارت:\n`{CARD_NUMBER}`\n👤 {CARD_OWNER}\n\n"
            "⚠️ توجه بسیار مهم: لطفاً به هیچ وجه عدد را رند نکنید و دقیقاً همین مبلغ را واریز کنید.\n\n"
            "بعد از واریز، عکس رسید پرداخت رو همینجا ارسال کن 📸"
        )
        conn = db()
        conn.execute(
            "INSERT INTO payments (user_id, coins, amount, status, created_at) VALUES (?,?,?,?,?)",
            (user_id, coins, price, "awaiting_receipt", datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        update_user(user_id, state="await_receipt")
        await query.message.edit_text(text, parse_mode="Markdown")
        await query.answer()
        return


async def send_invite_message(update, context, edit=False):
    row = get_user(update.effective_user.id)
    link = f"http://t.me/MeloGap?start=inv_{row['username_code']}"
    text = (
        f"همین الان رو لینک بزن 👇\n{link}\n\n"
        "لینک⚡️ دعوت شما با موفقیت ساخته شد 👆\n\n"
        "شما میتوانید بنر حاوی لینک⚡️ خود را به گـــروه ها و دوستان خود ارسال کنید\n\n"
        "- با معرفی هر نفر 30 سکه بگیرید! برای اطلاعات بیشتر راهنمای سکه(/help_credit)را بخوانید.\n\n"
        f"👈 شما تاکنون {row['invite_count'] or 0} نفر را به این ربات دعوت کرده اید ."
    )
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

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ پذیرفتن و ارسال سکه", callback_data=f"pay_ok:{pay['id']}"),
                InlineKeyboardButton("❌ رد کردن", callback_data=f"pay_no:{pay['id']}"),
            ]
        ]
    )
    await context.bot.send_photo(
        ADMIN_ID,
        photo.file_id,
        caption=(
            f"رسید جدید از کاربر {user_id}\n"
            f"مبلغ: {pay['amount']:,} تومان\nسکه: {pay['coins']}\n"
            f"می‌خوای سکه رو براش بفرستی؟"
        ),
        reply_markup=kb,
    )


async def admin_payment_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
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
    if action == "pay_ok":
        conn.execute("UPDATE payments SET status='approved' WHERE id=?", (pay_id,))
        conn.commit()
        add_coins(pay["user_id"], pay["coins"])
        await context.bot.send_message(
            pay["user_id"], f"✅ پرداخت شما تایید شد و {pay['coins']} سکه به حسابت اضافه شد."
        )
        await query.message.edit_caption(caption=query.message.caption + "\n\n✅ تایید شد.")
    else:
        conn.execute("UPDATE payments SET status='rejected' WHERE id=?", (pay_id,))
        conn.commit()
        await context.bot.send_message(pay["user_id"], "❌ متاسفانه رسید شما تایید نشد.")
        await query.message.edit_caption(caption=query.message.caption + "\n\n❌ رد شد.")
    conn.close()
    await query.answer()


# ============================== NAME / AGE / PHOTO TEXT & PHOTO CAPTURE ==============================


async def free_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    row = get_user(user_id)
    if row is None:
        await start(update, context)
        return
    if not is_registered(row):
        await registration_text_guard(update, context, row)
        return

    state = row["state"]
    text = update.message.text.strip() if update.message.text else ""

    if state == "await_name":
        update_user(user_id, name=text, state=None)
        await update.message.reply_text("✅ نام شما با موفقیت تغییر کرد.", reply_markup=MAIN_MENU)
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

    # not in a special state -> route to main menu buttons
    await main_menu_router(update, context)


# ============================== PHOTO HANDLER (profile pic or receipt) ==============================


async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    user_id = update.effective_user.id
    row = get_user(user_id)
    if row["state"] == "await_photo":
        file_id = update.message.photo[-1].file_id
        update_user(user_id, photo_file_id=file_id, state=None)
        await update.message.reply_text("✅ عکس پروفایل شما تغییر کرد.", reply_markup=MAIN_MENU)
        return
    if row["state"] == "await_receipt":
        await receipt_photo_handler(update, context)
        return
    if row["state"] == "in_chat":
        await relay_photo(update, context)
        return
    # unexpected photo -> ignore / break any loop
    await update.message.reply_text("این عکس در این مرحله قابل قبول نیست.")


# ============================== ANONYMOUS CHAT ==============================

waiting_queue = {"any": [], "male": [], "female": []}


def chat_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("پروفایل مخاطب", callback_data="chat:profile")],
            [InlineKeyboardButton("پایان چت", callback_data="chat:end")],
        ]
    )


async def anon_connect_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    text = "🔴 حتما قبل از استفاده از ربات قوانین ربات « /help_terms » را مطالعه کنید."
    await update.message.reply_text(text)
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("جستوجوی شانسی🎲", callback_data="search:any")],
            [InlineKeyboardButton("جستوجوی دختر", callback_data="search:دختر")],
            [InlineKeyboardButton("جستوجوی پسر", callback_data="search:پسر")],
            [InlineKeyboardButton("جستجوی اطراف", callback_data="search:nearby")],
            [InlineKeyboardButton("جستوجو برپایه استان", callback_data="search:province")],
        ]
    )
    await update.message.reply_text(f"🤩 به کی وصلت کنم؟ انتخاب کن 👇🎲\n\n{FOOTER}", reply_markup=kb)


async def try_match(user_id, gender_filter, context):
    """Try to find a waiting partner. gender_filter: 'any' | 'دختر' | 'پسر'."""
    conn = db()
    q = "SELECT user_id FROM users WHERE pending_search IS NOT NULL AND pending_search LIKE 'waiting:%' AND user_id != ?"
    candidates = conn.execute(q, (user_id,)).fetchall()
    conn.close()
    for cand in candidates:
        cand_row = get_user(cand["user_id"])
        if not cand_row:
            continue
        want = cand_row["pending_search"].split(":", 1)[1]
        # check mutual compatibility (both accept each other's gender preference)
        if want in ("any",) or want == get_user(user_id)["gender"]:
            if gender_filter in ("any",) or gender_filter == cand_row["gender"]:
                return cand_row
    return None


async def connect_two_users(user_a, user_b, context):
    session = gen_code(8)
    update_user(user_a, in_chat_with=user_b, pending_search=None, state="in_chat")
    update_user(user_b, in_chat_with=user_a, pending_search=None, state="in_chat")
    context.bot_data.setdefault("chat_sessions", {})[user_a] = session
    context.bot_data.setdefault("chat_sessions", {})[user_b] = session

    text = (
        "🤩😉 پیدا کردم و وصل‌تون کردم!\nبه مخاطبت 👋 کن 🗣\n\n"
        "⚠️ هشدار جدی:\nلطفاً اطلاعات شخصی مثل شناسنامه، گواهینامه یا اطلاعات خصوصی خودتون رو "
        "برای هم ارسال نکنید. مسئولیت انتشار اطلاعات شخصی بر عهده خود کاربران است."
    )
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
                await query.message.edit_text(
                    "⚠️خطا: برای استفاده از این قسمت ابتدا باید موقعیت مکانی(GPS) خود را ثبت کنید!"
                )
                await context.bot.send_message(user_id, "با کلیک روی دکمه ی پایین موقعیت خودت رو ثبت کن:")
                await send_gps_request(update, context)
            else:
                await do_random_connect(user_id, "any", update, context)
            await query.answer()
            return

        if mode == "province":
            await query.message.edit_text(
                f"به کدوم استان وصلت کنم...؟ انتخاب کن👇", reply_markup=province_keyboard(prefix="matchprov")
            )
            await query.answer()
            return

        if mode in ("دختر", "پسر"):
            cost = 2
            if row["coins"] < cost:
                await show_insufficient_coins(query, cost)
                await query.answer()
                return
            add_coins(user_id, -cost)
            await do_random_connect(user_id, mode, update, context)
            await query.answer()
            return

        # any (شانسی)
        await query.message.edit_text(
            "🔎 درحال جستجوی مخاطب ناشناس شما\n🎲 -جستجوی شانسی\n\n"
            "⏳ حداکثر تا ۲ دقیقه صبر کنید.\n\n"
            "⚙️ جستجوی همسن : 📴 غیر فعال\n- فعال کردن : /on"
        )
        await do_random_connect(user_id, "any", update, context)
        await query.answer()
        return

    if data.startswith("matchprov:"):
        province = data.split(":", 1)[1]
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("دختر باشه ( 3 سکه )", callback_data=f"provgender:{province}:دختر")],
                [InlineKeyboardButton("پسر باشه ( 3 سکه )", callback_data=f"provgender:{province}:پسر")],
                [InlineKeyboardButton("فرقی نمیکنه ( رایگان )", callback_data=f"provgender:{province}:any")],
            ]
        )
        await query.message.edit_text(f"چه کسی رو از استان {province} برات پیدا کنم؟ انتخاب کن👇", reply_markup=kb)
        await query.answer()
        return

    if data.startswith("provgender:"):
        _, province, gender = data.split(":")
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(f"وصل شدن به هم استانی {('شانسی' if gender=='any' else gender)}", callback_data=f"provconn:{province}:{gender}")],
                [InlineKeyboardButton("لیست هم استانیای من( 10 سکه )", callback_data=f"provlist:{province}:{gender}")],
            ]
        )
        await query.message.edit_text(
            "میخوای شانسی به یکی از هم‌استانیات وصلت کنم یا لیست تمام کاربران هم‌استانیت رو بدم؟",
            reply_markup=kb,
        )
        await query.answer()
        return

    if data.startswith("provconn:"):
        _, province, gender = data.split(":")
        cost = 0 if gender == "any" else 3
        if row["coins"] < cost:
            await show_insufficient_coins(query, cost)
            await query.answer()
            return
        if cost:
            add_coins(user_id, -cost)
        await do_province_connect(user_id, province, gender, update, context)
        await query.answer()
        return

    if data.startswith("provlist:"):
        _, province, gender = data.split(":")
        cost = 10
        if row["coins"] < cost:
            await show_insufficient_coins(query, cost)
            await query.answer()
            return
        add_coins(user_id, -cost)
        await send_province_list(user_id, province, gender, update, context)
        await query.answer()
        return


async def show_insufficient_coins(query, cost):
    text = (
        f"⚠️ خطا : شما سکه کافی ندارید! ({cost} سکه مورد نیاز)\n\n"
        "برای معرفی ربات و دریافت سکه ، دکمه زیر👇 رو لمس کن تا لینک معرفی مخصوص خودتو دریافت کنی"
    )
    rows = [[InlineKeyboardButton("معرفی به دوستان", callback_data="show_invite")]]
    for c, p in COIN_PACKAGES:
        rows.append([InlineKeyboardButton(f"خرید {c} سکه: {p:,} تومان", callback_data=f"buy:{c}:{p}")])
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(rows))


async def do_random_connect(user_id, gender_filter, update, context):
    partner = await try_match(user_id, gender_filter, context)
    if partner:
        await connect_two_users(user_id, partner["user_id"], context)
    else:
        update_user(user_id, pending_search=f"waiting:{gender_filter}")
        await context.bot.send_message(
            user_id,
            "⏳ در صف انتظار قرار گرفتی، به محض پیدا شدن یک نفر بهت اطلاع می‌دم.",
        )


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
        if partner["photo_file_id"]:
            await context.bot.send_photo(user_id, partner["photo_file_id"], caption=text, reply_markup=pkb)
        else:
            await context.bot.send_message(user_id, text, reply_markup=pkb)
        await query.answer()
        return

    if data == "chat:end":
        await query.message.edit_text(
            "🤖 پیام سیستم 👇\n\nمطمئنی می‌خوای این گپ رو ببندی؟",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("ادامه ی چت", callback_data="chat:continue"),
                        InlineKeyboardButton("اتمام چت", callback_data="chat:finish"),
                    ]
                ]
            ),
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
        if partner_id:
            update_user(partner_id, in_chat_with=None, state=None)
            end_text = (
                f"چت شما با «آیدی کاربر(/user_{row['username_code']})» توسط کاربر مقابل قطع شد\n\n"
                f"برای گزارش عدم رعایت قوانین (/help_terms) می‌توانید با لمس 《 🚫 گزارش کاربر 》 در پروفایل، "
                "کاربر را گزارش کنید.\n"
                f"🗑تا 30 دقیقه بعد اتمام چت می‌تونی با دستور زیر پیام‌های ارسال شده رو به طرف مقابل پاک کنی!\n"
                f"/delet_messages_{session_code}"
            )
            await context.bot.send_message(partner_id, end_text, reply_markup=MAIN_MENU)
            await context.bot.send_message(
                user_id,
                f"🗑تا 30 دقیقه بعد اتمام چت می‌تونی با دستور زیر پیام‌های ارسال شده رو به طرف مقابل پاک کنی!\n"
                f"/delet_messages_{session_code}",
            )
        await query.message.edit_text("✅ چت پایان یافت.")
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
        conn.execute(
            "INSERT OR IGNORE INTO contacts (owner_id, contact_id) VALUES (?,?)", (user_id, target_id)
        )
        conn.commit()
        conn.close()
        await query.answer("✅ به مخاطبین اضافه شد.", show_alert=True)
        return

    if action == "notifyon":
        row = get_user(user_id)
        cost = 1
        if row["coins"] < cost:
            await query.answer(f"⚠️ سکه کافی نداری! ({cost} سکه مورد نیاز)", show_alert=True)
            return
        add_coins(user_id, -cost)
        conn = db()
        conn.execute(
            "INSERT OR REPLACE INTO notify_requests (watcher_id, target_id, created_at) VALUES (?,?,?)",
            (user_id, target_id, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        await query.answer("🔔 به محض آنلاین شدن این کاربر بهت خبر می‌دم.", show_alert=True)
        return

    if action == "report":
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("محتوای غیراخلاقی", callback_data=f"reportreason:{target_id}:غیراخلاقی")],
                [InlineKeyboardButton("آزار و اذیت", callback_data=f"reportreason:{target_id}:آزار")],
                [InlineKeyboardButton("انتشار اطلاعات شخصی", callback_data=f"reportreason:{target_id}:حریم‌خصوصی")],
                [InlineKeyboardButton("تبلیغات", callback_data=f"reportreason:{target_id}:تبلیغات")],
            ]
        )
        await context.bot.send_message(user_id, "🚫 دلیل گزارش این کاربر رو انتخاب کن:", reply_markup=kb)
        await query.answer()
        return


async def report_reason_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    _, target_id, reason = query.data.split(":")
    target_id = int(target_id)
    conn = db()
    conn.execute(
        "INSERT INTO reports (reporter_id, target_id, reason, created_at) VALUES (?,?,?,?)",
        (user_id, target_id, reason, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    await query.message.edit_text("✅ گزارش شما ثبت شد و توسط تیم پشتیبانی بررسی خواهد شد.")
    target = get_user(target_id)
    await context.bot.send_message(
        ADMIN_ID,
        f"🚫 گزارش جدید\nگزارش‌دهنده: {user_id}\nکاربر گزارش‌شده: {target_id} "
        f"(/user_{target['username_code'] if target else '?'})\nدلیل: {reason}",
    )
    await query.answer()


# ============================== NEARBY ==============================


async def nearby_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    row = get_user(update.effective_user.id)
    if row["lat"] is None:
        await update.message.reply_text(
            "⚠️خطا: برای استفاده از این قسمت ابتدا باید موقعیت مکانی(GPS) خود را ثبت کنید!"
        )
        await send_gps_request(update, context)
        return
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("5KM", callback_data="radius:5"),
                InlineKeyboardButton("10KM", callback_data="radius:10"),
                InlineKeyboardButton("30KM", callback_data="radius:30"),
            ],
            [
                InlineKeyboardButton("60KM", callback_data="radius:60"),
                InlineKeyboardButton("100KM", callback_data="radius:100"),
            ],
        ]
    )
    await update.message.reply_text(
        "📡میخوای تا چه فاصله ای از اطرافت جستجو کنم ؟\nمثلا تا 5 کیلومتر...؟! انتخاب کن👇", reply_markup=kb
    )


async def nearby_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data.startswith("radius:"):
        radius = data.split(":", 1)[1]
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("فقط پسر ها", callback_data=f"nearbyf:{radius}:پسر")],
                [InlineKeyboardButton("فقط دختر ها", callback_data=f"nearbyf:{radius}:دختر")],
                [InlineKeyboardButton("همه رو نشون بده", callback_data=f"nearbyf:{radius}:any")],
            ]
        )
        await query.message.edit_text(
            f"📡چه کسایی رو تا ({radius} KM📍) از اطرافت نشونت بدم؟ انتخاب کن👇", reply_markup=kb
        )
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

        lines = [f"📍 لیست افراد نزدیک شما که در ۳ روز اخیر آنلاین بوده اند\n"]
        for d, r in page:
            lines.append(
                f"‏{r['age']} 😐 {r['name'] or '—'} /user_{r['username_code']}  "
                f"{r['province']}({r['city']}) (🏁 {d:.0f} km) (❤️{r['likes']})"
            )
        lines.append(f"\nجستجو شده در {datetime.now().strftime('%Y/%m/%d %H:%M')}")

        next_offset = offset + page_size
        buttons = []
        if next_offset < len(results):
            buttons.append(
                [InlineKeyboardButton("مشاهده ادامه ی لیست", callback_data=f"nearbymore:{radius}:{gender}:{next_offset}")]
            )
        buttons.append([InlineKeyboardButton("بازگشت", callback_data="back:main")])

        await query.message.edit_text("\n\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()
        return


# ============================== USER SEARCH ==============================


async def user_search_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("به مخاطب مورد نظرم وصلم کن", callback_data="usearch:byid")],
            [InlineKeyboardButton("هم سن ها", callback_data="usearch:sameage")],
            [InlineKeyboardButton("هم استانی ها", callback_data="usearch:sameprov")],
            [InlineKeyboardButton("کاربران جدید", callback_data="usearch:newest")],
            [InlineKeyboardButton("کاربران محبوب بر اساس لایک", callback_data="usearch:popular")],
        ]
    )
    await update.message.reply_text("چه کسایی رو نشونت بدم؟ انتخاب کن👇", reply_markup=kb)


async def usearch_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    row = get_user(user_id)
    data = query.data.split(":", 1)[1]

    if data == "byid":
        await query.message.edit_text(
            "🆔 آیدی عددی، یوزرنیم تلگرام یا کد ربات (/user_XXXX) شخص مورد نظر رو ارسال کن:"
        )
        update_user(user_id, state="await_search_byid")
        await query.answer()
        return

    conn = db()
    if data == "sameage":
        rows = conn.execute(
            "SELECT * FROM users WHERE age=? AND user_id != ?", (row["age"], user_id)
        ).fetchall()
    elif data == "sameprov":
        rows = conn.execute(
            "SELECT * FROM users WHERE province=? AND user_id != ?", (row["province"], user_id)
        ).fetchall()
    elif data == "newest":
        rows = conn.execute(
            "SELECT * FROM users WHERE user_id != ? ORDER BY joined_at DESC LIMIT 15", (user_id,)
        ).fetchall()
    elif data == "popular":
        rows = conn.execute(
            "SELECT * FROM users WHERE user_id != ? ORDER BY likes DESC LIMIT 15", (user_id,)
        ).fetchall()
    else:
        rows = []
    conn.close()

    if not rows:
        await query.message.edit_text("کاربری یافت نشد.")
        await query.answer()
        return

    lines = [
        f"{r['age']} 😐 {r['name'] or '—'} /user_{r['username_code']} {r['province']}({r['city']})"
        for r in rows[:15]
    ]
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
        pkb = profile_keyboard()
        if target["photo_file_id"]:
            await update.message.reply_photo(target["photo_file_id"], caption=text, reply_markup=pkb)
        else:
            await update.message.reply_text(text, reply_markup=pkb)
        return
    cost = 2
    row = get_user(update.effective_user.id)
    if row["coins"] < cost:
        await update.message.reply_text(f"⚠️ خطا : شما سکه کافی ندارید! ({cost} سکه مورد نیاز)")
        return
    add_coins(update.effective_user.id, -cost)
    await context.bot.send_message(
        target["user_id"],
        f"📩 کاربری درخواست چت با شما رو فرستاده! (/user_{row['username_code']})",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("پذیرفتن", callback_data=f"pchat_ok:{update.effective_user.id}"),
                    InlineKeyboardButton("رد کردن", callback_data=f"pchat_no:{update.effective_user.id}"),
                ]
            ]
        ),
    )
    await update.message.reply_text("درخواست چت شما ارسال شد، منتظر پاسخ کاربر باش.")


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
    "🔸 - چگونه بصورت پیشرفته بین کاربران جستجو کنم ؟ /help_search\n"
    "🔸 - چگونه اکانت ربات را حذف کنم ؟ /deleted_account"
)

HELP_TOPICS = {
    "help_chat": "برای چت ناشناس، از منوی پایین «به یه ناشناس وصلم کن!🌠» رو بزن و یکی از روش‌های جستجو رو انتخاب کن.",
    "help_credit": (
        "🔹 سکه یا امتیاز چیست؟\n\nشما با داشتن سکه میتوانید :\n\n"
        "- پیام دایرکت بفرستید (1سکه)\n- درخواست چت بفرستید(2سکه)\n"
        "- از جستجوی پسر یا جستجوی دختر استفاده کنید(2سکه)\n"
        "- از ـ«به محض آنلاین شدن اطلاع بده» استفاده کنید(1سکه)\n\n"
        "📢 توجه : سکه فقط در صورتی کسر می شود که درخواست موفق باشد.\n\n"
        "❓روش بدست آوردن سکه چیست؟\n\n1️⃣ معرفی دوستان (رایگان) :\n\n"
        "برای افزایش سکه به صورت رایگان بنر لینک⚡️ مخصوص خودت (/link) رو برای دوستات بفرست و 30 سکه دریافت کن\n\n"
        "- به ازای هرنفری که با لینک⚡️ شما وارد ربات میشه به محض ورود 20 تا سکه رایگان دریافت میکنی و "
        "بعد از اینکه اطلاعات پروفایــــــلش رو کامل کرد 30 تا سکه دیگه هم دریافت میکنی😎 (10+20=30)"
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
    await update.message.reply_text(f"🔗 لینک ناشناس شما:\nhttp://t.me/MeloGap?start=inv_{row['username_code']}")


async def silent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    row = get_user(update.effective_user.id)
    new_state = 0 if row["silent"] else 1
    update_user(update.effective_user.id, silent=new_state)
    await update.message.reply_text("🔕 حالت سایلنت فعال شد." if new_state else "🔔 حالت سایلنت غیرفعال شد.")


async def deleted_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("بله، حذف کن", callback_data="delacc:yes"),
                InlineKeyboardButton("انصراف", callback_data="delacc:no"),
            ]
        ]
    )
    await update.message.reply_text("⚠️ آیا مطمئنی می‌خوای اکانتت رو حذف کنی؟ این عمل غیرقابل بازگشته!", reply_markup=kb)


async def delacc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if query.data == "delacc:yes":
        conn = db()
        conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        await query.message.edit_text("✅ حساب کاربری شما حذف شد. برای شروع دوباره /start رو بزن.")
    else:
        await query.message.edit_text("انصراف داده شد.")
    await query.answer()


async def on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_ready(update, context):
        return
    await update.message.reply_text("⚙️ جستجوی همسن فعال شد.")


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
    target = None
    if text.startswith("/user_"):
        target = get_user_by_code(text.split("/user_", 1)[1])
    elif text.lstrip("-").isdigit():
        target = get_user(int(text))
    if not target:
        await update.message.reply_text("کاربر یافت نشد.")
        return
    await update.message.reply_text(
        f"کاربر پیدا شد: {target['name'] or '—'} /user_{target['username_code']}\n"
        f"برای ارسال درخواست چت، دستور /user_{target['username_code']} رو بزن."
    )


# ============================== DISPATCH CALLBACK ROUTER ==============================


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

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
    if data.startswith(("editf:", "cityedit:", "edit_profile", "back:profile", "my_gps", "my_likers", "my_contacts")):
        await profile_callbacks(update, context)
        return
    if data == "back:main":
        await profile_callbacks(update, context)
        return
    if data.startswith(("search:", "matchprov:", "provgender:", "provconn:", "provlist:")):
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
    if data.startswith(("show_invite", "buy:")):
        await coin_callbacks(update, context)
        return
    if data.startswith(("pay_ok:", "pay_no:")):
        await admin_payment_decision(update, context)
        return
    if data.startswith(("pchat_ok:", "pchat_no:")):
        await pchat_decision(update, context)
        return
    if data.startswith("delacc:"):
        await delacc_callback(update, context)
        return
    if data.startswith(("addcontact:", "notifyon:", "report:")):
        await contact_profile_actions(update, context)
        return
    if data.startswith("reportreason:"):
        await report_reason_callback(update, context)
        return

    await update.callback_query.answer()


# ============================== TEXT / COMMAND CATCH-ALL FOR /user_ and /delet_messages_ ==============================


async def generic_command_catch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
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
    rows = conn.execute(
        "SELECT * FROM messages_log WHERE chat_session=? AND sender_id=?", (session_code, user_id)
    ).fetchall()
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


# ============================== APP SETUP ==============================


def build_help_handlers(app):
    for topic in HELP_TOPICS:
        app.add_handler(CommandHandler(topic, help_topic_command))


def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("silent", silent_command))
    app.add_handler(CommandHandler("deleted_account", deleted_account_command))
    app.add_handler(CommandHandler("on", on_command))
    build_help_handlers(app)

    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_router))
    app.add_handler(
        MessageHandler(filters.Regex(r"^/user_") | filters.Regex(r"^/delet_messages_"), generic_command_catch)
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text_router))

    app.add_handler(CallbackQueryHandler(callback_router))

    logger.info("Bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()