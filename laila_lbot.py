import os
import re
import time
import random
import asyncio
import logging
import io
from telegram import (
    Update, InlineKeyboardButton as B, InlineKeyboardMarkup as M
)
from telegram.constants import ParseMode, ChatType
from telegram.error import TelegramError
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatMemberHandler,
    filters, ContextTypes, Defaults
)

import db

# ==================== الإعدادات ====================
# التوكن والـ OWNER_ID بيتقروا من Environment Variables بدل ما يتكتبوا في الكود
# ده مهم عشان متسربش التوكن لو رفعت الكود على GitHub
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
INITIAL_DEFAULT_CHANNELS = [-1002738530870]

if not BOT_TOKEN:
    raise SystemExit(
        "❌ لازم تحدد BOT_TOKEN كـ Environment Variable قبل ما تشغل البوت.\n"
        "محلي: حطه في ملف .env\n"
        "على Railway: Variables tab -> ضيف BOT_TOKEN"
    )

CHANNEL_WAIT_TIMEOUT_MS = 5 * 60 * 1000
PROMPT_AUTO_DELETE_MS   = 60 * 1000
REMINDER_COOLDOWN_MS    = 5 * 60 * 1000
MAX_CHANNELS_PER_GROUP  = 5

# Pending types
PENDING_DEFAULT         = 0
PENDING_ADD_TRIGGER     = -1
PENDING_ADD_REPLY       = -2
PENDING_ADD_GAME_WORD   = -3
PENDING_ADD_GAME_ANSWER = -4
PENDING_ADD_BANNED_WORD = -5
PENDING_BROADCAST       = -6
PENDING_SPY_WORD        = -7
PENDING_SPY_SETTING     = -8
PENDING_GLOBAL_BANNED   = -9
PENDING_SCHEDULE_TEXT   = -10
PENDING_SCHEDULE_TIME   = -11
PENDING_MENTION_TIME    = -12
PENDING_MENTION_COUNT   = -13
PENDING_MENTION_TEXT    = -14
PENDING_MESSAGES_COUNT  = -15
PENDING_SAY_TEXT        = -16
PENDING_BANK_SETTING    = -17
PENDING_DEVS_ADD        = -100

GROUP_TYPES             = {ChatType.GROUP, ChatType.SUPERGROUP}

SUB_CACHE_TTL    = 120
ADMIN_CACHE_TTL  = 300
RIGHTS_CACHE_TTL = 180

TRIGGER_OWNER = ("المالك",)
TRIGGER_ADMIN = ("الأدمن", "الادمن", "ادمن", "أدمن")
TRIGGER_TOP   = ("توب", "التوب", "top")
TRIGGER_TOP_MONEY_BANK = ("توب الفلوس", "توب فلوس")
# ===== الجديد =====
TRIGGER_MARRY = ("زوجني", "زواج", "اتجوز", "جوزني")
TRIGGER_PARTNER = ("زوجي", "زوجتي", "مين زوجي", "مين زوجتي", "جوزي")
TRIGGER_DIVORCE = ("طلاق", "طلقني", "اتطلق")
TRIGGER_CHILD = ("طفل", "خلف", "خلفه", "انجب", "أنجب")
TRIGGER_CHILD_INCOME = ("رزق الطفل", "رزق الأطفال", "رزق الاطفال", "رزق اطفالي", "رزق أطفالي")
TRIGGER_BUY = ("اشتري", "اشتريت", "شراء", "اشتري عربية", "اشتري قصر", "اشتري برج", "اشتري جزيرة", "اشتري طيارة")
TRIGGER_SELL = ("بيع", "بيعت", "بيع ممتلكاتي")
TRIGGER_MY_DATA = ("بياناتي", "معلوماتي", "ملفي")
TRIGGER_JOKE = ("نكتة", "نكته", "علاج", "ضحكني", "ضحك")
TRIGGER_TIME = ("الوقت", "توقيت", "الساعة", "الوقت ايه", "الوقت إيه")
TRIGGER_REMIND = ("ذكرني",)
TRIGGER_VIP_LIST = ("قائمة VIP", "قائمة vip", "المميزين", "قائمة المميزين", "vip", "VIP")
TRIGGER_VIP_ADD = ("رفع مميز", "رفع مميزة", "vip add")
TRIGGER_VIP_REMOVE = ("مسح مميز", "مسح مميزة", "إزالة مميز", "ازالة مميز")
TRIGGER_VIP_REMOVE_ALL = ("مسح المميزين", "إزالة الكل", "مسح كل المميزين")
TRIGGER_TOP_THIEVES_2 = ("توب الحرامية", "توب حرامية", "الحرامية")
TRIGGER_MY_STATS = ("إحصائياتي", "احصائياتي", "إحصائيتي", "احصائيتي")
TRIGGER_HIS_STATS = ("إحصائياته", "احصائياته", "إحصائياتك", "احصائياتك", "إحصائياتها", "احصائياتها")
TRIGGER_MY_MONEY = ("فلوسي", "فلوسى", "جنيهاتي", "جنيهاتى")
TRIGGER_HIS_MONEY = ("فلوسه", "فلوسها", "فلوسك", "جنيهاته", "جنيهاتها", "جنيهاتك")
TRIGGER_ID = ("ايدي", "أيدي", "معرفي", "id")
TRIGGER_GAMES = ("الألعاب", "الالعاب", "ألعاب", "العاب", "games")
TRIGGER_WARN = ("تحذير",)
TRIGGER_UNWARN = ("الغاء التحذير", "إلغاء التحذير", "الغاء تحذير", "إلغاء تحذير")
TRIGGER_BAN = ("حظر",)
TRIGGER_UNBAN = ("الغاء الحظر", "إلغاء الحظر", "الغاء حظر", "إلغاء حظر")
TRIGGER_MUTE = ("كتم",)
TRIGGER_UNMUTE = ("الغاء الكتم", "إلغاء الكتم", "الغاء كتم", "إلغاء كتم")
TRIGGER_DELETE = ("مسح", "حذف", "امسح", "احذف")
TRIGGER_MUTED_LIST = ("المكتومين", "مكتومين")
TRIGGER_BANNED_LIST = ("المحظورين", "محظورين")
TRIGGER_GAMES_ON = ("تفعيل الالعاب", "تفعيل الألعاب", "شغل الالعاب", "شغل الألعاب")
TRIGGER_GAMES_OFF = ("تعطيل الالعاب", "تعطيل الألعاب", "وقف الالعاب", "وقف الألعاب")
TRIGGER_SPY = ("جاسوس", "الجاسوس", "بكاسه", "بكاسة", "البكاسه", "البكاسة", "امبوستر", "imposter", "الجاسوسية", "جاسوسية")
TRIGGER_EMOJI = ("الإيموجي", "الايموجي", "ايموجي", "إيموجي", "اموجي", "أموجي", "ايموشن", "الاموجي", "إموجي", "اموشن", "الايموشن")
TRIGGER_KET = ("كت", "الكت")
TRIGGER_MAFIA = ("مافيا", "المافيا", "mafia")
TRIGGER_STORY = ("قصة", "القصة", "قصة مبعثرة", "القصة المبعثرة")
TRIGGER_PATTERN = ("اكمل النمط", "أكمل النمط", "النمط")
TRIGGER_FOCUS = ("ركز", "التركيز", "تركيز")
TRIGGER_ODD = ("إيه المختلف", "ايه المختلف", "المختلف")
TRIGGER_GUESS = ("خمن الكلمة", "خمن كلمة")
TRIGGER_SORT = ("ترتيب الأرقام", "ترتيب ارقام", "رتب الأرقام", "رتب الارقام")
TRIGGER_COMMANDS = ("الأوامر", "الاوامر", "أوامر", "اوامر", "commands")
TRIGGER_POINTS_SYSTEM = ("نظام النقاط", "نظام نقاط", "النقاط")

# Bank triggers
TRIGGER_BANK_CREATE = ("إنشاء حساب بنكي", "انشاء حساب بنكي", "إنشاء حساب", "انشاء حساب")
TRIGGER_BANK_DELETE = ("مسح حساب بنكي", "حذف حساب بنكي", "مسح حسابي البنكي")
TRIGGER_BANK_INFO = ("حسابي البنكي", "حسابى البنكي")
TRIGGER_SALARY = ("راتب", "الراتب")
TRIGGER_TIP = ("بقشيش", "بخشيش", "البقشيش", "البخشيش")
TRIGGER_TRANSFER = ("تحويل",)
TRIGGER_STEAL = ("سرقة", "اسرق", "سرق")
TRIGGER_INVEST = ("استثمار", "استثمر")
TRIGGER_LUCK = ("حظ", "الحظ")
TRIGGER_TOP_MONEY = ("توب الفلوس", "توب فلوس")
TRIGGER_TOP_THIEVES = ("توب الحرامية", "توب حرامية", "الحرامية")
TRIGGER_ADD_MONEY = ("إضافة", "اضافة", "إضافه", "اضافه")
TRIGGER_DEDUCT = ("خصم", "اخصم", "أخصم")
TRIGGER_DEDUCT = ("خصم", "اخصم", "أخصم")

GAME_FASTEST = "fastest"
GAME_SCRAMBLE = "scramble"
GAME_QUESTIONS = "questions"
GAME_ENGLISH = "english"
GAME_EMOJI = "emoji"
GAME_SPY = "spy"
GAME_KET = "ket"
GAME_STORY = "story"
GAME_PATTERN = "pattern"
GAME_FOCUS = "focus"
GAME_ODD = "odd"
GAME_GUESS = "guess"
GAME_SORT = "sort"

EMOJI_POOL = ["😀","😎","🥰","😜","🤩","😇","🥳","🤔","😴","🤯","🥶","🤠",
              "🐶","🐱","🐼","🦁","🐸","🦊","🐨","🐵","🦄","🐝","🦋","🐢",
              "🍎","🍕","🍔","🍩","🍦","🍓","🍉","🍇","🥑","🍿","🍫","🍭",
              "⚽","🏀","🎮","🎸","🎨","🎯","🎲","🚗","🚀","⏰","💎","🎁"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("turbot")

BOT_USERNAME = ""
_cache = {}
active_games = {}
timer_games = {}
spy_games = {}
mafia_games = {}
story_games = {}
commands_pages = {}  # تتبع صفحة الأوامر لكل شات

def is_owner(uid): return uid == OWNER_ID

def has_perm(uid, perm_key):
    """هل المستخدم عنده صلاحية معينة؟ المالك عنده كل حاجة"""
    if uid == OWNER_ID:
        return True
    try:
        if db.is_developer(uid):
            return db.get_dev_permission(uid, perm_key)
    except:
        pass
    return False

def can_access_owner_menu(uid):
    """هل يقدر يفتح إعدادات المالك؟"""
    if uid == OWNER_ID:
        return True
    try:
        return db.is_developer(uid)
    except:
        return False

# ==================== الكاش ====================
def cache_get(key, ttl):
    if key not in _cache: return None
    val, ts = _cache[key]
    if time.time() - ts > ttl:
        _cache.pop(key, None)
        return None
    return val

def cache_set(key, val):
    _cache[key] = (val, time.time())

def invalidate_sub(chid, uid): _cache.pop(f"sub:{chid}:{uid}", None)
def invalidate_admin(cid, uid): _cache.pop(f"adm:{cid}:{uid}", None)
def invalidate_bot_rights(cid):
    for k in list(_cache.keys()):
        if k.startswith(f"rights:{cid}"): _cache.pop(k, None)

# ==================== التطابق الذكي ====================
def normalize_text(text):
    if not text: return ""
    t = text.strip().lower()
    # إزالة التشكيل والتطويل
    t = re.sub(r'[\u064B-\u0652\u0670\u0640]', '', t)
    # الهمزات والألف
    t = t.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ٱ', 'ا')
    # التاء المربوطة
    t = t.replace('ة', 'ه')
    # الياء والألف المقصورة
    t = t.replace('ى', 'ي')
    # الواو والهمزة
    t = t.replace('ؤ', 'و').replace('ئ', 'ي')
    # ال التعريف — نزيل ال التعريف عشان تطابق أقوى
    # نزيل المسافات والرموز من البداية والنهاية
    t = re.sub(r'^[\s\.,!؟?،؛;:\-_\*#@\u200f\u200e\u2600-\u27BF\U0001F000-\U0001FAFF\u2190-\u21FF\u2B00-\u2BFF\uFE0F\u200D]+', '', t)
    t = re.sub(r'[\s\.,!؟?،؛:;\-_\*#@\u200f\u200e\u2600-\u27BF\U0001F000-\U0001FAFF\u2190-\u21FF\u2B00-\u2BFF\uFE0F\u200D]+$', '', t)
    # إزالة "ال" التعريف من البداية
    if t.startswith('ال') and len(t) > 2:
        t = t[2:]
    # إزالة المسافات الزيادة
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def normalize_digits(text):
    if not text: return ""
    return str(text).translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))

def normalize_emoji(text):
    if not text: return ""
    return re.sub(r'\s+', '', text.strip())

def emoji_match(user_text, target):
    u = normalize_emoji(user_text)
    t = normalize_emoji(target)
    if u == t: return True
    if u.replace(" ", "") == t.replace(" ", ""): return True
    return False

def find_reply_for(text):
    if not text: return None
    norm = normalize_text(text)
    if not norm: return None
    rows = db.list_auto_replies()
    matches = [r["response"] for r in rows if normalize_text(r["trigger"]) == norm]
    if not matches: return None
    return random.choice(matches)

# ==================== دوال مساعدة ====================
async def is_subscribed(bot, chid, uid):
    key = f"sub:{chid}:{uid}"
    cached = cache_get(key, SUB_CACHE_TTL)
    if cached is not None: return cached
    try:
        m = await bot.get_chat_member(chid, uid)
        ok = m.status in ("creator","administrator","member","restricted")
        cache_set(key, ok)
        return ok
    except TelegramError as e:
        log.warning(f"⚠️ فشل فحص الاشتراك {uid}@{chid}: {e}")
        return True

async def is_user_admin(bot, cid, uid):
    # المالك دايماً أدمن — من غير طلب
    if is_owner(uid):
        return True
    key = f"adm:{cid}:{uid}"
    cached = cache_get(key, ADMIN_CACHE_TTL)
    if cached is not None: return cached
    try:
        m = await bot.get_chat_member(cid, uid)
        ok = m.status in ("creator","administrator")
    except TelegramError:
        ok = False
    cache_set(key, ok)
    return ok

async def get_bot_rights(bot, cid, fresh=False):
    key = f"rights:{cid}"
    if not fresh:
        cached = cache_get(key, RIGHTS_CACHE_TTL)
        if cached is not None: return cached
    try:
        me = await bot.get_me()
        m = await bot.get_chat_member(cid, me.id)
        is_admin = m.status in ("administrator","creator")
        can_del = bool(getattr(m, "can_delete_messages", False)) if is_admin else False
        res = {"is_admin": is_admin, "can_delete": can_del}
    except TelegramError:
        res = {"is_admin": False, "can_delete": False}
    cache_set(key, res)
    return res

async def safe_delete(bot, cid, mid):
    try: await bot.delete_message(cid, mid)
    except TelegramError: pass

def delete_later(bot, cid, mid, delay_ms):
    async def _do():
        await asyncio.sleep(delay_ms/1000)
        await safe_delete(bot, cid, mid)
    asyncio.create_task(_do())

def extract_channel_identifier(message):
    origin = getattr(message, "forward_origin", None)
    if origin:
        ch = getattr(origin, "chat", None)
        if ch:
            if ch.username: return "@" + ch.username
            return str(ch.id)
    text = (message.text or "").strip()
    if not text: return None
    m = re.search(r"(?:https?://)?t\.me/([A-Za-z0-9_]+)", text)
    if m: return "@" + m.group(1)
    if text.startswith("@") and re.match(r"^@[A-Za-z0-9_]{4,}$", text): return text
    if re.match(r"^-?\d+$", text): return text
    return None

async def resolve_channel(bot, ident):
    try:
        ch = await bot.get_chat(ident)
    except TelegramError as e:
        return {"ok": False, "reason": f"❌ لم أستطع الوصول للقناة.\nتأكد أن البوت مشرف فيها.\n({e.message})"}
    link = ch.invite_link or (f"https://t.me/{ch.username}" if ch.username else None)
    return {"ok": True, "channel": {"id": ch.id, "title": ch.title, "username": ch.username, "link": link}}

def escape_html(v=""):
    return v.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def fmt_money(amount):
    """تنسيق الفلوس"""
    try:
        n = int(amount)
        return f"{n:,} جنيه مصري"
    except:
        return f"{amount} جنيه مصري"

def fmt_num(amount):
    try: return f"{int(amount):,}"
    except: return str(amount)

async def can_manage(update, cid):
    uid = update.effective_user.id
    if is_owner(uid): return True
    return await is_user_admin(update.get_bot(), cid, uid)

async def missing_channels(bot, chans, uid):
    out = []
    for c in chans:
        try:
            if not await is_subscribed(bot, c["channel_id"], uid): out.append(c)
        except: pass
    return out

async def get_group_link(bot, cid):
    try:
        chat = await bot.get_chat(cid)
        if chat.invite_link: return chat.invite_link
        if chat.username: return f"https://t.me/{chat.username}"
        try: return await bot.export_chat_invite_link(cid)
        except TelegramError: return None
    except TelegramError:
        return None

# ==================== ردود المالك / الأدمن ====================
async def build_owner_reply(bot, chat_id):
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except TelegramError as e:
        log.warning(f"فشل جلب أدمنز {chat_id}: {e}")
        return None
    for a in admins:
        if a.status == "creator":
            name = a.user.first_name or "المالك"
            return f'<a href="tg://user?id={a.user.id}">{escape_html(name)}</a>'
    return None

async def build_admins_reply(bot, chat_id):
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except TelegramError as e:
        log.warning(f"فشل جلب أدمنز {chat_id}: {e}")
        return None
    owner = None
    others = []
    for a in admins:
        u = a.user
        if u.is_bot: continue
        if a.status == "creator": owner = u
        else: others.append(u)
    if not owner and not others: return None
    lines = []
    if owner:
        lines.append(f"👑 <a href=\"tg://user?id={owner.id}\">{escape_html(owner.first_name or 'المالك')}</a>")
    for u in others:
        lines.append(f"👮 <a href=\"tg://user?id={u.id}\">{escape_html(u.first_name or 'أدمن')}</a>")
    return "\n".join(lines)

# ==================== الإحصائيات ====================
async def build_my_stats_reply(chat_id, user_id, first_name):
    p = db.get_points(chat_id, user_id)
    # الفلوس من البنك دايماً
    acc = db.get_bank_account(user_id)
    money = acc["balance"] if acc else 0
    rank = get_bank_rank(user_id) or "غير مصنف"
    return (
        f"📊 *إحصائياتك*\n\n"
        f"👤 *{escape_html(first_name)}*\n"
        f"🆔 `{user_id}`\n\n"
        f"💰 *الفلوس:* {fmt_money(money)}\n"
        f"🏆 الانتصارات: *{p['wins']}*\n"
        f"🏅 الترتيب: *#{rank}*"
    )

async def build_my_stats_global_reply(user_id, first_name):
    # الفلوس من البنك دايماً
    acc = db.get_bank_account(user_id)
    money = acc["balance"] if acc else 0
    total = db.get_total_points(user_id)
    rank = get_bank_rank(user_id) or "غير مصنف"
    return (
        f"📊 *إحصائياتك*\n\n"
        f"👤 *{escape_html(first_name)}*\n"
        f"🆔 `{user_id}`\n\n"
        f"💰 *الفلوس:* {fmt_money(money)}\n"
        f"🏆 الانتصارات: *{total['wins']}*\n"
        f"🏅 الترتيب العام: *#{rank}*"
    )

def get_bank_rank(user_id):
    """ترتيب المستخدم حسب رصيد البنك"""
    try:
        top = db.get_top_money(10000)
        for i, item in enumerate(top, 1):
            if item["user_id"] == user_id:
                return i
    except:
        pass
    return None

async def build_my_money_reply(chat_id, user_id, first_name):
    acc = db.get_bank_account(user_id)
    if acc:
        money = acc["balance"]
    else:
        p = db.get_points(chat_id, user_id)
        money = p["points"]
    return (f"💰 *فلوس {escape_html(first_name)}*\n\n💰 *الفلوس:* {fmt_money(money)}")

async def build_his_money_reply(chat_id, target_id, target_name):
    acc = db.get_bank_account(target_id)
    if acc:
        money = acc["balance"]
    else:
        p = db.get_points(chat_id, target_id)
        money = p["points"]
    return (f"💰 *فلوس {escape_html(target_name)}*\n\n💰 *الفلوس:* {fmt_money(money)}")

async def build_top_reply(bot, chat_id, title=None):
    top = db.get_top(chat_id, 10)
    if not top:
        return "📊 لا توجد إحصائيات بعد."
    lines = [f"🏆 *توب 10 في {escape_html(title or 'الجروب')}*\n"]
    medals = ["🥇","🥈","🥉"]
    for i, item in enumerate(top, 1):
        try:
            m = await bot.get_chat_member(chat_id, item["user_id"])
            name = m.user.first_name or "عضو"
        except:
            u = db.get_user(item["user_id"])
            name = u["first_name"] if u and u["first_name"] else f"عضو {item['user_id']}"
        prefix = medals[i-1] if i <= 3 else f"{i}."
        lines.append(f"{prefix} {escape_html(name)} — *{fmt_money(item['points'])}*")
    return "\n".join(lines)

async def build_global_top_reply(bot):
    top = db.get_global_top(10)
    if not top:
        return "📊 لا توجد إحصائيات بعد."
    lines = ["🏆 *توب 10 عام (كل الجروبات)*\n"]
    medals = ["🥇","🥈","🥉"]
    for i, item in enumerate(top, 1):
        u = db.get_user(item["user_id"])
        name = u["first_name"] if u and u["first_name"] else f"عضو {item['user_id']}"
        prefix = medals[i-1] if i <= 3 else f"{i}."
        lines.append(f"{prefix} {escape_html(name)} — *{fmt_money(item['points'])}*")
    return "\n".join(lines)

# ============ نهاية الجزء 1 ============

# ============ بداية الجزء 2 — الألعاب ============

async def start_number_game(bot, chat_id):
    num = random.randint(1, 100)
    active_games[chat_id] = {"type": "number", "answer": num}
    try:
        await bot.send_message(chat_id,
            "🔢 *خمن الرقم*\n\nالبوت اختار رقم من *1* لـ *100*\nاكتب تخمينك 👇\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_fastest_game(bot, chat_id):
    rows = db.list_game_content(GAME_FASTEST)
    if not rows:
        await bot.send_message(chat_id, "⚠️ لا توجد كلمات مسجلة بعد.")
        return
    item = random.choice(rows)
    word = item["content"]
    active_games[chat_id] = {"type": "fastest", "answer": normalize_text(word)}
    try:
        await bot.send_message(chat_id,
            f"⚡ *الأسرع*\n\nأول واحد يكتب الكلمة دي يكسب:\n\n👉 {word}\n\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_scramble_game(bot, chat_id):
    rows = db.list_game_content(GAME_SCRAMBLE)
    if not rows:
        await bot.send_message(chat_id, "⚠️ لا توجد كلمات مسجلة بعد.")
        return
    item = random.choice(rows)
    word = item["content"]
    letters = list(word)
    random.shuffle(letters)
    scrambled = " ".join(letters)
    active_games[chat_id] = {"type": "scramble", "answer": normalize_text(word)}
    try:
        await bot.send_message(chat_id,
            f"🔤 *رتب الحروف*\n\nرتب الحروف واكتب الكلمة:\n\n👉 `{scrambled}`\n\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_questions_game(bot, chat_id):
    rows = db.list_game_content(GAME_QUESTIONS)
    if not rows:
        # أسئلة افتراضية
        default_qs = [
            ("عاصمة مصر إيه؟", "القاهرة"),
            ("عاصمة السعودية إيه؟", "الرياض"),
            ("عاصمة فرنسا إيه؟", "باريس"),
            ("عاصمة إيطاليا إيه؟", "روما"),
            ("عاصمة اليابان إيه؟", "طوكيو"),
            ("أكبر كوكب في المجموعة الشمسية؟", "المشتري"),
            ("أصغر كوكب؟", "عطارد"),
            ("عدد أيام السنة؟", "365"),
            ("عدد ألوان قوس قزح؟", "7"),
            ("عدد أيام الأسبوع؟", "7"),
        ]
        item_content, item_answer = random.choice(default_qs)
        active_games[chat_id] = {"type": "questions", "answer": normalize_text(item_answer)}
        try:
            await bot.send_message(chat_id,
                f"❓ *سؤال*\n\n{item_content}\n\nاكتب الإجابة 👇\n⏱ عندك 60 ثانية",
                parse_mode=ParseMode.MARKDOWN)
        except: pass
        return
    item = random.choice(rows)
    question = item["content"]
    answer = (item["answer"] or "").strip()
    active_games[chat_id] = {"type": "questions", "answer": normalize_text(answer)}
    try:
        await bot.send_message(chat_id,
            f"❓ *سؤال*\n\n{question}\n\nاكتب الإجابة الصحيحة 👇\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_english_game(bot, chat_id):
    rows = db.list_game_content(GAME_ENGLISH)
    if not rows:
        await bot.send_message(chat_id, "⚠️ لا توجد كلمات إنجليزية مسجلة بعد.")
        return
    item = random.choice(rows)
    word = item["content"]
    answer = (item["answer"] or "").strip()
    active_games[chat_id] = {"type": "english", "answer": normalize_text(answer)}
    try:
        await bot.send_message(chat_id,
            f"🇬🇧 *إنجليزي*\n\nالكلمة: `{word}`\n\nاكتب معناها بالعربي 👇\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_calc_game(bot, chat_id):
    a = random.randint(1, 50)
    b = random.randint(1, 50)
    op = random.choice(["+", "-", "×"])
    if op == "+": ans = a + b
    elif op == "-": ans = a - b
    else: ans = a * b
    active_games[chat_id] = {"type": "calc", "answer": str(ans)}
    try:
        await bot.send_message(chat_id,
            f"🔢 *احسب*\n\n`{a} {op} {b} = ؟`\n\nاكتب الناتج 👇\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_emoji_game(bot, chat_id):
    emojis = random.sample(EMOJI_POOL, 2)
    answer = emojis[0] + emojis[1]
    active_games[chat_id] = {"type": "emoji", "answer": answer}
    try:
        await bot.send_message(chat_id,
            f"😀 *الإيموجي*\n\nاكتب الإيموجيين دول بالظبط:\n\n{emojis[0]} {emojis[1]}\n\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_ket_game(bot, chat_id):
    rows = db.list_game_content(GAME_KET)
    if not rows:
        await bot.send_message(chat_id, "⚠️ لا توجد أسئلة مسجلة بعد.")
        return
    item = random.choice(rows)
    question = item["content"]
    try:
        await bot.send_message(chat_id,
            f"💭 *كت*\n\n{question}\n\nجاوب بأي حاجة من دماغك 😄",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_timer_game(bot, chat_id):
    target_sec = random.randint(5, 30)  # رقم صحيح بس
    target_ms = target_sec * 1000
    timer_games[chat_id] = {
        "target_ms": target_ms,
        "start_time": time.time(),
        "clicks": {},
        "finished": False
    }
    kb = M([[B("⏱ اضغط!", callback_data=f"timer:click:{chat_id}")]])
    try:
        await bot.send_message(chat_id,
            f"⏱ *المؤقت*\n\nالهدف: *{target_sec}* ثانية\n\nدوس على الزر 👇\n⏳ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except: pass
    asyncio.create_task(_timer_finish(bot, chat_id))

async def _timer_finish(bot, chat_id):
    await asyncio.sleep(60)
    g = timer_games.get(chat_id)
    if not g or g.get("finished"): return
    g["finished"] = True
    if not g["clicks"]:
        try: await bot.send_message(chat_id, "⏱ خلص الوقت ومحدش داس!")
        except: pass
        timer_games.pop(chat_id, None)
        return
    results = []
    for uid, (name, click_ms) in g["clicks"].items():
        diff = abs(click_ms - g["target_ms"])
        results.append((uid, name, click_ms, diff))
    results.sort(key=lambda x: x[3])
    winner = results[0]
    db.add_points(chat_id, winner[0], 10, count_message=False)
    db.add_win(chat_id, winner[0])
    lines = [f"⏱ *انتهى المؤقت!*\nالهدف: *{g['target_ms']/1000:.2f}* ثانية\n"]
    medals = ["🥇","🥈","🥉"]
    for i, (uid, name, click_ms, diff) in enumerate(results[:10], 1):
        prefix = medals[i-1] if i <= 3 else f"{i}."
        lines.append(f"{prefix} {escape_html(name)} — {click_ms/1000:.2f}ث (فرق {diff/1000:.2f})")
    lines.append(f"\n🎉 *{escape_html(winner[1])}* كسب +10 جنيه!")
    try: await bot.send_message(chat_id, "\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except: pass
    timer_games.pop(chat_id, None)

# ==================== لعبة الجاسوس / بكاسة ====================
async def start_spy_lobby(bot, chat_id):
    if chat_id in spy_games and spy_games[chat_id].get("state") == "lobby":
        return
    spy_games[chat_id] = {
        "state": "lobby", "players": {}, "lobby_message_id": None,
        "spy_id": None, "word": None, "votes": {},
    }
    await spy_update_lobby(bot, chat_id, first=True)

async def spy_update_lobby(bot, chat_id, first=False):
    g = spy_games.get(chat_id)
    if not g or g["state"] != "lobby": return
    text = ("🕵️ *الجاسوس / بكاسة*\n\n"
            "الكل يستلم كلمة سرية في الخاص، ما عدا واحد (الجاسوس)\n"
            "كل واحد يقول جملة عن الكلمة والجاسوس يستنتجها\n"
            "في الآخر نصوت على مين الجاسوس\n\n"
            f"👥 اللاعبين: {len(g['players'])}\n"
            "📌 دوس *✋ مشاركة* عشان تدخل\n"
            "⚠️ لازم تكون فاتح البوت في الخاص الأول")
    kb = M([
        [B("✋ مشاركة", callback_data=f"spy:join:{chat_id}")],
        [B("🚀 ابدأ اللعبة", callback_data=f"spy:start:{chat_id}")],
        [B("❌ إلغاء", callback_data=f"spy:cancel:{chat_id}")],
    ])
    if first:
        try:
            msg = await bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            spy_games[chat_id]["lobby_message_id"] = msg.message_id
        except: pass
    else:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=g["lobby_message_id"],
                text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except: pass

async def spy_join(bot, chat_id, user):
    g = spy_games.get(chat_id)
    if not g or g["state"] != "lobby": return "not_active"
    settings = db.get_spy_settings(chat_id)
    if len(g["players"]) >= settings["max_players"]: return "full"
    if user.id in g["players"]: return "already"
    try:
        test = await bot.send_message(user.id, "✅ تمام! هتقدر تشارك في اللعبة.", parse_mode=ParseMode.MARKDOWN)
        try: await bot.delete_message(user.id, test.message_id)
        except: pass
    except TelegramError:
        return "no_pm"
    g["players"][user.id] = user.first_name
    await spy_update_lobby(bot, chat_id)
    return "ok"

async def spy_begin_game(bot, chat_id):
    g = spy_games.get(chat_id)
    if not g or g["state"] != "lobby": return
    settings = db.get_spy_settings(chat_id)
    if len(g["players"]) < settings["min_players"]: return
    words = db.list_game_content(GAME_SPY)
    if not words:
        try: await bot.send_message(chat_id, "⚠️ مفيش كلمات مسجلة للجاسوس.")
        except: pass
        return
    item = random.choice(words)
    word = item["content"]
    g["word"] = word
    g["spy_id"] = random.choice(list(g["players"].keys()))
    g["votes"] = {}
    sent_to = set()
    for uid, name in g["players"].items():
        try:
            if uid == g["spy_id"]:
                await bot.send_message(uid,
                    "🕵️ *إنت الجاسوس!*\n\nمش هتعرف الكلمة السرية.\nاسمع كلام اللاعبين وحاول تستنتجها.\nمتحاولش تتكشف 😏",
                    parse_mode=ParseMode.MARKDOWN)
            else:
                await bot.send_message(uid,
                    f"🎭 *الكلمة السرية:*\n\n`{word}`\n\nقول جملة عنها من غير ما تقولها",
                    parse_mode=ParseMode.MARKDOWN)
            sent_to.add(uid)
        except TelegramError: pass
    if len(sent_to) < settings["min_players"]:
        try: await bot.send_message(chat_id, f"⚠️ في لاعبين مقفولين الخاص، وباقي {len(sent_to)} لاعبين — اللعبة اتلغت.")
        except: pass
        spy_games.pop(chat_id, None)
        return
    g["state"] = "discussion"
    names = "، ".join(g["players"].values())
    try:
        await bot.send_message(chat_id,
            f"🎮 *اللعبة بدأت!*\n\n👥 اللاعبين: {escape_html(names)}\n\n"
            f"⏱ *مرحلة النقاش:* {settings['discussion_sec']//60} دقايق\n\n"
            "💬 كل واحد يقول جملة عن الكلمة\n🕵️ حاولوا تعرفوا مين الجاسوس",
            parse_mode=ParseMode.MARKDOWN)
    except: pass
    asyncio.create_task(spy_discussion_timer(bot, chat_id))

async def spy_discussion_timer(bot, chat_id):
    settings = db.get_spy_settings(chat_id)
    await asyncio.sleep(settings["discussion_sec"])
    g = spy_games.get(chat_id)
    if not g or g["state"] != "discussion": return
    g["state"] = "voting"
    await spy_show_voting(bot, chat_id)
    asyncio.create_task(spy_voting_timer(bot, chat_id))

async def spy_show_voting(bot, chat_id):
    g = spy_games.get(chat_id)
    if not g: return
    settings = db.get_spy_settings(chat_id)
    rows = []
    for uid, name in g["players"].items():
        rows.append([B(f"🗳 {name}", callback_data=f"spy:vote:{chat_id}:{uid}")])
    kb = M(rows)
    try:
        await bot.send_message(chat_id,
            f"🗳 *مرحلة التصويت*\n\n⏱ عندكم *{settings['voting_sec']}* ثانية\n\nصوّتوا على اللي شاكين فيه 👇",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except: pass

async def spy_vote(bot, chat_id, voter_id, voted_id):
    g = spy_games.get(chat_id)
    if not g or g["state"] != "voting": return
    if voter_id not in g["players"]: return
    if voted_id not in g["players"]: return
    if voter_id == voted_id: return
    g["votes"][voter_id] = voted_id
    if len(g["votes"]) >= len(g["players"]):
        await spy_end_game(bot, chat_id)

async def spy_voting_timer(bot, chat_id):
    settings = db.get_spy_settings(chat_id)
    await asyncio.sleep(settings["voting_sec"])
    g = spy_games.get(chat_id)
    if not g or g["state"] != "voting": return
    await spy_end_game(bot, chat_id)

async def spy_end_game(bot, chat_id):
    g = spy_games.get(chat_id)
    if not g: return
    g["state"] = "ended"
    counts = {}
    for voted_id in g["votes"].values():
        counts[voted_id] = counts.get(voted_id, 0) + 1
    if not counts:
        try:
            await bot.send_message(chat_id,
                f"🗳 محدش صوّت!\n\n🕵️ الجاسوس: *{escape_html(g['players'][g['spy_id']])}*\n🎭 الكلمة: `{g['word']}`",
                parse_mode=ParseMode.MARKDOWN)
        except: pass
        spy_games.pop(chat_id, None)
        return
    most_voted = max(counts, key=counts.get)
    voted_name = g["players"].get(most_voted, "؟")
    spy_name = g["players"][g["spy_id"]]
    word = g["word"]
    if most_voted == g["spy_id"]:
        result = f"🎉 *اللاعبين فازوا!*\n\n🕵️ الجاسوس: *{escape_html(spy_name)}*\n🎭 الكلمة: `{word}`"
        for uid in g["players"]:
            if uid != g["spy_id"]:
                db.add_points(chat_id, uid, 5, count_message=False)
                db.add_win(chat_id, uid)
    else:
        result = f"🕵️ *الجاسوس فاز!*\n\n🎯 الجاسوس: *{escape_html(spy_name)}*\n❌ صوّتوا على: *{escape_html(voted_name)}*\n🎭 الكلمة: `{word}`"
        db.add_points(chat_id, g["spy_id"], 10, count_message=False)
        db.add_win(chat_id, g["spy_id"])
    lines = [result, "", "🗳 *نتيجة التصويت:*"]
    for uid, voted_id in g["votes"].items():
        v_name = g["players"].get(uid, "؟")
        t_name = g["players"].get(voted_id, "؟")
        lines.append(f"• {escape_html(v_name)} → {escape_html(t_name)}")
    try: await bot.send_message(chat_id, "\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except: pass
    spy_games.pop(chat_id, None)

async def spy_cancel(bot, chat_id):
    if chat_id in spy_games:
        spy_games.pop(chat_id, None)
        try: await bot.send_message(chat_id, "❌ تم إلغاء اللعبة.")
        except: pass

# ==================== لعبة القصة المبعثرة ====================
async def start_story_lobby(bot, chat_id):
    if chat_id in story_games and story_games[chat_id].get("state") == "lobby":
        return
    story_games[chat_id] = {
        "state": "lobby", "players": {}, "lobby_message_id": None,
        "words": [], "stories": {}, "votes": {},
    }
    await story_update_lobby(bot, chat_id, first=True)

async def story_update_lobby(bot, chat_id, first=False):
    g = story_games.get(chat_id)
    if not g or g["state"] != "lobby": return
    text = ("📖 *القصة المبعثرة*\n\n"
            "البوت يختار 4 كلمات عشوائية\n"
            "كل لاعب يكتب قصة قصيرة فيها الكلمات دي\n"
            "وفي الآخر نصوّت على أحلى قصة\n\n"
            f"👥 اللاعبين: {len(g['players'])}\n"
            "📌 دوس *✋ مشاركة* عشان تدخل\n"
            "⚠️ لازم تكون فاتح البوت في الخاص الأول")
    kb = M([
        [B("✋ مشاركة", callback_data=f"story:join:{chat_id}")],
        [B("🚀 ابدأ اللعبة", callback_data=f"story:start:{chat_id}")],
        [B("❌ إلغاء", callback_data=f"story:cancel:{chat_id}")],
    ])
    if first:
        try:
            msg = await bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            story_games[chat_id]["lobby_message_id"] = msg.message_id
        except: pass
    else:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=g["lobby_message_id"],
                text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except: pass

async def story_join(bot, chat_id, user):
    g = story_games.get(chat_id)
    if not g or g["state"] != "lobby": return "not_active"
    if len(g["players"]) >= 10: return "full"
    if user.id in g["players"]: return "already"
    try:
        test = await bot.send_message(user.id, "✅ تمام! هتقدر تشارك في اللعبة.", parse_mode=ParseMode.MARKDOWN)
        try: await bot.delete_message(user.id, test.message_id)
        except: pass
    except TelegramError:
        return "no_pm"
    g["players"][user.id] = user.first_name
    await story_update_lobby(bot, chat_id)
    return "ok"

async def story_begin_game(bot, chat_id):
    g = story_games.get(chat_id)
    if not g or g["state"] != "lobby": return
    if len(g["players"]) < 3: return
    rows = db.list_game_content(GAME_STORY)
    if len(rows) < 4:
        try: await bot.send_message(chat_id, "⚠️ محتاج 4 كلمات على الأقل مسجلة للقصة.")
        except: pass
        return
    words = [it["content"] for it in random.sample(rows, 4)]
    g["words"] = words
    g["stories"] = {}
    g["votes"] = {}
    g["state"] = "writing"
    words_text = "\n".join(f"• {w}" for w in words)
    try:
        await bot.send_message(chat_id,
            f"📖 *القصة المبعثرة — بدأت!*\n\n"
            f"🎯 *الكلمات الأربعة:*\n{words_text}\n\n"
            f"✍️ كل لاعب يكتب قصة قصيرة فيها الكلمات الأربعة\n"
            f"⏱ عندكم *3 دقايق*\n\n"
            "⚠️ اكتبوا القصص دلوقتي 👇",
            parse_mode=ParseMode.MARKDOWN)
    except: pass
    asyncio.create_task(story_writing_timer(bot, chat_id))

async def story_writing_timer(bot, chat_id):
    await asyncio.sleep(180)
    g = story_games.get(chat_id)
    if not g or g["state"] != "writing": return
    if not g["stories"]:
        try: await bot.send_message(chat_id, "⏱ انتهى الوقت ومحدش كتب قصة. اللعبة اتلغت.")
        except: pass
        story_games.pop(chat_id, None)
        return
    g["state"] = "voting"
    await story_show_stories(bot, chat_id)

async def story_show_stories(bot, chat_id):
    g = story_games.get(chat_id)
    if not g: return
    lines = ["📖 *القصص المشاركة:*\n"]
    for uid, story in g["stories"].items():
        name = g["players"].get(uid, "؟")
        lines.append(f"✍️ *{escape_html(name)}:*\n{escape_html(story[:200])}\n")
    text = "\n".join(lines)
    if len(text) > 4000: text = text[:4000] + "\n... (طويلة)"
    try: await bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN)
    except: pass
    rows = []
    for uid, name in g["players"].items():
        if uid in g["stories"]:
            rows.append([B(f"⭐ {name}", callback_data=f"story:vote:{chat_id}:{uid}")])
    kb = M(rows)
    try:
        await bot.send_message(chat_id, "🗳 *التصويت على أحلى قصة:*\n\n⏱ 60 ثانية",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except: pass
    asyncio.create_task(story_voting_timer(bot, chat_id))

async def story_vote(bot, chat_id, voter_id, voted_id):
    g = story_games.get(chat_id)
    if not g or g["state"] != "voting": return
    if voter_id not in g["players"]: return
    if voter_id == voted_id: return
    g["votes"][voter_id] = voted_id

async def story_voting_timer(bot, chat_id):
    await asyncio.sleep(60)
    g = story_games.get(chat_id)
    if not g or g["state"] != "voting": return
    await story_end_game(bot, chat_id)

async def story_end_game(bot, chat_id):
    g = story_games.get(chat_id)
    if not g: return
    g["state"] = "ended"
    counts = {}
    for voted_id in g["votes"].values():
        counts[voted_id] = counts.get(voted_id, 0) + 1
    if not counts:
        try: await bot.send_message(chat_id, "🗳 محدش صوّت!")
        except: pass
        story_games.pop(chat_id, None)
        return
    winner_id = max(counts, key=counts.get)
    winner_name = g["players"].get(winner_id, "؟")
    db.add_points(chat_id, winner_id, 10, count_message=False)
    db.add_win(chat_id, winner_id)
    lines = [f"🎉 *الفايز:* {escape_html(winner_name)} — *{counts[winner_id]}* صوت\n"]
    lines.append("🗳 *نتيجة التصويت:*")
    for voter_id, voted_id in g["votes"].items():
        v_name = g["players"].get(voter_id, "؟")
        t_name = g["players"].get(voted_id, "؟")
        lines.append(f"• {escape_html(v_name)} → {escape_html(t_name)}")
    lines.append(f"\n🎁 *{escape_html(winner_name)}* كسب +10 جنيه!")
    try: await bot.send_message(chat_id, "\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except: pass
    story_games.pop(chat_id, None)

async def story_cancel(bot, chat_id):
    if chat_id in story_games:
        story_games.pop(chat_id, None)
        try: await bot.send_message(chat_id, "❌ تم إلغاء اللعبة.")
        except: pass

# ==================== لعبة المافيا ====================
async def start_mafia_lobby(bot, chat_id):
    if chat_id in mafia_games and mafia_games[chat_id].get("state") == "lobby":
        return
    mafia_games[chat_id] = {
        "state": "lobby", "players": {}, "lobby_message_id": None,
        "roles": {}, "night_actions": {}, "votes": {}, "round": 0, "alive": set(),
    }
    await mafia_update_lobby(bot, chat_id, first=True)

async def mafia_update_lobby(bot, chat_id, first=False):
    g = mafia_games.get(chat_id)
    if not g or g["state"] != "lobby": return
    text = ("👥 *المافيا*\n\n"
            "🔪 مافيا + 🔍 محقق + 👤 مواطنين\n"
            "بالليل المافيا تقتل والمحقق يفحص\n"
            "بالنهار نصوت على مين نخرجه\n\n"
            f"👥 اللاعبين: {len(g['players'])}\n"
            "📌 دوس *✋ مشاركة* عشان تدخل\n"
            "⚠️ لازم تكون فاتح البوت في الخاص الأول")
    kb = M([
        [B("✋ مشاركة", callback_data=f"mafia:join:{chat_id}")],
        [B("🚀 ابدأ اللعبة", callback_data=f"mafia:start:{chat_id}")],
        [B("❌ إلغاء", callback_data=f"mafia:cancel:{chat_id}")],
    ])
    if first:
        try:
            msg = await bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            mafia_games[chat_id]["lobby_message_id"] = msg.message_id
        except: pass
    else:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=g["lobby_message_id"],
                text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except: pass

async def mafia_join(bot, chat_id, user):
    g = mafia_games.get(chat_id)
    if not g or g["state"] != "lobby": return "not_active"
    settings = db.get_mafia_settings(chat_id)
    if len(g["players"]) >= settings["max_players"]: return "full"
    if user.id in g["players"]: return "already"
    try:
        test = await bot.send_message(user.id, "✅ تمام! هتقدر تشارك في اللعبة.", parse_mode=ParseMode.MARKDOWN)
        try: await bot.delete_message(user.id, test.message_id)
        except: pass
    except TelegramError:
        return "no_pm"
    g["players"][user.id] = user.first_name
    await mafia_update_lobby(bot, chat_id)
    return "ok"

async def mafia_begin_game(bot, chat_id):
    g = mafia_games.get(chat_id)
    if not g or g["state"] != "lobby": return
    settings = db.get_mafia_settings(chat_id)
    n = len(g["players"])
    if n < settings["min_players"]: return
    mafia_count = max(1, n // 4)
    detective_count = 1 if n >= 5 else 0
    players_ids = list(g["players"].keys())
    random.shuffle(players_ids)
    roles = {}
    for i, uid in enumerate(players_ids):
        if i < mafia_count: roles[uid] = "mafia"
        elif i < mafia_count + detective_count: roles[uid] = "detective"
        else: roles[uid] = "citizen"
    g["roles"] = roles
    g["alive"] = set(players_ids)
    g["round"] = 0
    sent = 0
    for uid, role in roles.items():
        try:
            if role == "mafia":
                msg = "🔪 *إنت من المافيا!*\n\nاتفقوا مع باقي المافيا على ضحية كل ليلة."
            elif role == "detective":
                msg = "🔍 *إنت المحقق!*\n\nكل ليلة تختار لاعب واعرف إذا كان مافيا ولا لأ."
            else:
                msg = "👤 *إنت مواطن!*\n\nناقش وحلل وساعد في كشف المافيا."
            await bot.send_message(uid, msg, parse_mode=ParseMode.MARKDOWN)
            sent += 1
        except TelegramError: pass
    if sent < n:
        try: await bot.send_message(chat_id, "⚠️ في لاعبين مقفلين الخاص — اللعبة اتلغت.")
        except: pass
        mafia_games.pop(chat_id, None)
        return
    g["state"] = "night"
    try:
        await bot.send_message(chat_id,
            f"🎮 *اللعبة بدأت!*\n\n👥 عدد اللاعبين: *{n}*\n🔪 عدد المافيا: *{mafia_count}*\n\n"
            "🌙 *الليل بدأ...*\nكل حد يستخدم قدرته في الخاص",
            parse_mode=ParseMode.MARKDOWN)
    except: pass
    await mafia_start_night(bot, chat_id)

async def mafia_start_night(bot, chat_id):
    g = mafia_games.get(chat_id)
    if not g: return
    g["state"] = "night"
    g["night_actions"] = {}
    g["round"] += 1
    alive_list = list(g["alive"])
    mafia_ids = [uid for uid in alive_list if g["roles"].get(uid) == "mafia"]
    for mid in mafia_ids:
        rows = [[B(f"🔪 {g['players'].get(uid, '؟')}", callback_data=f"mafia:kill:{chat_id}:{uid}")] for uid in alive_list if uid != mid]
        try:
            await bot.send_message(mid, f"🌙 *الليلة {g['round']}*\n\nاختار مين عاوز تقتله:",
                parse_mode=ParseMode.MARKDOWN, reply_markup=M(rows))
        except: pass
    det_ids = [uid for uid in alive_list if g["roles"].get(uid) == "detective"]
    for did in det_ids:
        rows = [[B(f"🔍 {g['players'].get(uid, '؟')}", callback_data=f"mafia:check:{chat_id}:{uid}")] for uid in alive_list if uid != did]
        try:
            await bot.send_message(did, f"🌙 *الليلة {g['round']}*\n\nاختار مين عاوز تحققه:",
                parse_mode=ParseMode.MARKDOWN, reply_markup=M(rows))
        except: pass
    asyncio.create_task(mafia_night_timer(bot, chat_id))

async def mafia_night_timer(bot, chat_id):
    settings = db.get_mafia_settings(chat_id)
    await asyncio.sleep(settings["night_sec"])
    g = mafia_games.get(chat_id)
    if not g or g["state"] != "night": return
    await mafia_end_night(bot, chat_id)

async def mafia_action(bot, chat_id, uid, action, target):
    g = mafia_games.get(chat_id)
    if not g or g["state"] != "night": return
    if action == "kill":
        if g["roles"].get(uid) != "mafia": return
        g["night_actions"]["kill"] = target
    elif action == "check":
        if g["roles"].get(uid) != "detective": return
        g["night_actions"]["check"] = target
        is_mafia = g["roles"].get(target) == "mafia"
        try:
            await bot.send_message(uid,
                f"🔍 *نتيجة التحقيق:*\n{g['players'].get(target, '؟')} " + ("مافيا! 🔪" if is_mafia else "مواطن ✅"),
                parse_mode=ParseMode.MARKDOWN)
        except: pass

async def mafia_end_night(bot, chat_id):
    g = mafia_games.get(chat_id)
    if not g: return
    killed = g["night_actions"].get("kill")
    lines = [f"☀️ *النهار بدأ — الجولة {g['round']}*"]
    if killed and killed in g["alive"]:
        g["alive"].discard(killed)
        killed_name = g["players"].get(killed, "؟")
        lines.append(f"🔪 تم قتل *{escape_html(killed_name)}* بالليل!")
    else:
        lines.append("🌙 الليلة عدت بسلام — محدش مات")
    alive_names = "، ".join(g["players"].get(uid, "؟") for uid in g["alive"])
    lines.append(f"\n👥 *الأحياء:* {escape_html(alive_names)}")
    try: await bot.send_message(chat_id, "\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except: pass
    if await mafia_check_win(bot, chat_id): return
    g["state"] = "vote"
    g["votes"] = {}
    rows = []
    for uid in g["alive"]:
        name = g["players"].get(uid, "؟")
        rows.append([B(f"🗳 {name}", callback_data=f"mafia:vote:{chat_id}:{uid}")])
    try:
        await bot.send_message(chat_id,
            f"🗳 *صوّتوا على مين تشكوا فيه:*\n⏱ عندكم *{db.get_mafia_settings(chat_id)['vote_sec']}* ثانية",
            parse_mode=ParseMode.MARKDOWN, reply_markup=M(rows))
    except: pass
    asyncio.create_task(mafia_vote_timer(bot, chat_id))

async def mafia_vote(bot, chat_id, voter_id, voted_id):
    g = mafia_games.get(chat_id)
    if not g or g["state"] != "vote": return
    if voter_id not in g["alive"]: return
    if voted_id not in g["alive"]: return
    if voter_id == voted_id: return
    g["votes"][voter_id] = voted_id
    if len(g["votes"]) >= len(g["alive"]):
        await mafia_end_vote(bot, chat_id)

async def mafia_vote_timer(bot, chat_id):
    settings = db.get_mafia_settings(chat_id)
    await asyncio.sleep(settings["vote_sec"])
    g = mafia_games.get(chat_id)
    if not g or g["state"] != "vote": return
    await mafia_end_vote(bot, chat_id)

async def mafia_end_vote(bot, chat_id):
    g = mafia_games.get(chat_id)
    if not g: return
    counts = {}
    for voted_id in g["votes"].values():
        counts[voted_id] = counts.get(voted_id, 0) + 1
    if not counts:
        try: await bot.send_message(chat_id, "🗳 محدش صوّت!")
        except: pass
    else:
        most_voted = max(counts, key=counts.get)
        voted_name = g["players"].get(most_voted, "؟")
        role = g["roles"].get(most_voted, "citizen")
        role_str = {"mafia": "مافيا 🔪", "detective": "محقق 🔍", "citizen": "مواطن 👤"}.get(role, "؟")
        g["alive"].discard(most_voted)
        try:
            await bot.send_message(chat_id,
                f"🗳 *النتيجة:*\nتم إخراج *{escape_html(voted_name)}*\nكان دوره: *{role_str}*",
                parse_mode=ParseMode.MARKDOWN)
        except: pass
    if await mafia_check_win(bot, chat_id): return
    await mafia_start_night(bot, chat_id)

async def mafia_check_win(bot, chat_id):
    g = mafia_games.get(chat_id)
    if not g: return False
    alive_mafia = [uid for uid in g["alive"] if g["roles"].get(uid) == "mafia"]
    alive_citizens = [uid for uid in g["alive"] if g["roles"].get(uid) != "mafia"]
    if not alive_mafia:
        try: await bot.send_message(chat_id, "🎉 *المواطنون فازوا!*\nتم القضاء على كل المافيا!", parse_mode=ParseMode.MARKDOWN)
        except: pass
        for uid in alive_citizens:
            db.add_points(chat_id, uid, 10, count_message=False)
            db.add_win(chat_id, uid)
        mafia_games.pop(chat_id, None)
        return True
    if len(alive_mafia) >= len(alive_citizens):
        try: await bot.send_message(chat_id, "🔪 *المافيا فازت!*\nسيطرت على الجروب!", parse_mode=ParseMode.MARKDOWN)
        except: pass
        for uid in alive_mafia:
            db.add_points(chat_id, uid, 10, count_message=False)
            db.add_win(chat_id, uid)
        mafia_games.pop(chat_id, None)
        return True
    return False

async def mafia_cancel(bot, chat_id):
    if chat_id in mafia_games:
        mafia_games.pop(chat_id, None)
        try: await bot.send_message(chat_id, "❌ تم إلغاء اللعبة.")
        except: pass

# ==================== الألعاب الجديدة ====================
async def start_pattern_game(bot, chat_id):
    rows = db.list_game_content(GAME_PATTERN)
    if not rows:
        await bot.send_message(chat_id, "⚠️ لا توجد أنماط مسجلة بعد.")
        return
    item = random.choice(rows)
    active_games[chat_id] = {"type": "pattern", "answer": normalize_text(item["answer"] or "")}
    try:
        await bot.send_message(chat_id,
            f"🧩 *أكمل النمط*\n\n{item['content']}\n\nاكتب الرقم أو النمط الناقص 👇\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_focus_game(bot, chat_id):
    rows = db.list_game_content(GAME_FOCUS)
    if not rows:
        await bot.send_message(chat_id, "⚠️ لا توجد عناصر مسجلة بعد.")
        return
    item = random.choice(rows)
    active_games[chat_id] = {"type": "focus", "answer": normalize_text(item["answer"] or "")}
    try:
        await bot.send_message(chat_id,
            f"👀 *ركز*\n\n{item['content']}\n\nاكتب الإجابة 👇\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_odd_game(bot, chat_id):
    rows = db.list_game_content(GAME_ODD)
    if not rows:
        await bot.send_message(chat_id, "⚠️ لا توجد مجموعات مسجلة بعد.")
        return
    item = random.choice(rows)
    active_games[chat_id] = {"type": "odd", "answer": normalize_text(item["answer"] or "")}
    try:
        await bot.send_message(chat_id,
            f"🔍 *إيه المختلف؟*\n\n{item['content']}\n\nاكتب الكلمة المختلفة 👇\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

async def start_guess_game(bot, chat_id):
    rows = db.list_game_content(GAME_GUESS)
    if not rows:
        await bot.send_message(chat_id, "⚠️ لا توجد كلمات مسجلة بعد.")
        return
    item = random.choice(rows)
    hints_raw = item["answer"] or ""
    hints = [h.strip() for h in hints_raw.split("\n") if h.strip()]
    if not hints:
        await bot.send_message(chat_id, "⚠️ مفيش تلميحات للكلمة دي.")
        return
    active_games[chat_id] = {
        "type": "guess", "answer": normalize_text(item["content"]),
        "hints": hints, "current_hint": 0, "msg_id": None,
    }
    try:
        kb = M([[B("💡 تلميح", callback_data=f"guess:hint:{chat_id}")]])
        msg = await bot.send_message(chat_id,
            f"🎯 *خمن الكلمة*\n\n💡 {hints[0]}\n\nاكتب الكلمة 👇\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        active_games[chat_id]["msg_id"] = msg.message_id
    except: pass

async def start_sort_game(bot, chat_id):
    nums = random.sample(range(1, 100), 5)
    order = random.choice(["تصاعدي", "تنازلي"])
    scrambled = " - ".join(str(n) for n in nums)
    if order == "تصاعدي":
        answer = " - ".join(str(n) for n in sorted(nums))
    else:
        answer = " - ".join(str(n) for n in sorted(nums, reverse=True))
    active_games[chat_id] = {"type": "sort", "answer": normalize_text(answer)}
    try:
        await bot.send_message(chat_id,
            f"🔢 *ترتيب الأرقام*\n\n{scrambled}\n\nالمطلوب: رتب *{order}*\n\nاكتب الترتيب 👇\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN)
    except: pass

# ============ نهاية الجزء 2 ============

# ============ بداية الجزء 3 — Bank Turbo ============

# ==================== رسائل البنك ====================

def bank_main_text(user):
    """وصف Bank Turbo"""
    return ("🏦 *Bank Turbo*\n\n"
            "مرحباً بك في البنك 🏦\n\n"
            "💼 *الأوامر المتاحة:*\n"
            "• إنشاء حساب بنكي\n"
            "• حسابي البنكي\n"
            "• فلوسي\n"
            "• راتب\n"
            "• بقشيش\n"
            "• تحويل [مبلغ] (بالرد)\n"
            "• سرقة (بالرد)\n"
            "• استثمار [مبلغ]\n"
            "• حظ [مبلغ]\n"
            "• توب الفلوس\n"
            "• توب الحرامية\n\n"
            "💡 اكتب الأمر زي ما هو عشان يشتغل")

def account_text(acc):
    return (f"🏦 *Bank Turbo*\n\n"
            f"💳 رقم الحساب: `{acc['account_number']}`\n"
            f"💰 الرصيد: *{fmt_money(acc['balance'])}*")

def money_text(acc):
    return f"💰 *رصيدك:* {fmt_money(acc['balance'])}"

# ==================== أوامر Bank Turbo ====================

async def cmd_bank_create(update, ctx):
    """إنشاء حساب بنكي"""
    uid = update.effective_user.id
    u = update.effective_user
    # الرصيد الحالي من جدول points (كل الجروبات)
    total = db.get_total_points(uid)
    initial = total["points"] or 0
    acc_num = db.create_bank_account(uid, u.first_name, u.username, initial)
    if not acc_num:
        existing = db.get_bank_account(uid)
        if existing:
            return await update.message.reply_text(
                f"⚠️ عندك حساب بنكي بالفعل!\n\n"
                f"💳 رقم الحساب: `{existing['account_number']}`\n"
                f"💰 الرصيد: *{fmt_money(existing['balance'])}*",
                parse_mode=ParseMode.MARKDOWN)
        return await update.message.reply_text("❌ حصل خطأ، جرب تاني.")
    await update.message.reply_text(
        f"🏦 *تم إنشاء حسابك في Bank Turbo بنجاح!*\n\n"
        f"💳 رقم الحساب: `{acc_num}`\n"
        f"💰 الرصيد: *{fmt_money(initial)}*",
        parse_mode=ParseMode.MARKDOWN)

async def cmd_bank_delete(update, ctx):
    """مسح حساب بنكي"""
    uid = update.effective_user.id
    acc = db.get_bank_account(uid)
    if not acc:
        return await update.message.reply_text("⚠️ مفيش عندك حساب بنكي.")
    kb = M([
        [B("✅ أيوة امسح", callback_data=f"bank:del_confirm:{uid}")],
        [B("❌ إلغاء", callback_data=f"bank:del_cancel:{uid}")],
    ])
    await update.message.reply_text(
        f"⚠️ *تحذير!*\n\n"
        f"هتمسح حسابك البنكي بالكامل.\n"
        f"💰 رصيدك: *{fmt_money(acc['balance'])}*\n"
        f"💳 رقم حسابك: `{acc['account_number']}`\n\n"
        f"هل إنت متأكد؟",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def cmd_bank_info(update, ctx):
    """حسابي البنكي"""
    uid = update.effective_user.id
    acc = db.get_bank_account(uid)
    if not acc:
        return await update.message.reply_text(
            "⚠️ مفيش عندك حساب بنكي.\n\n"
            "اكتب *إنشاء حساب بنكي* عشان تعمل واحد 😉",
            parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_text(account_text(acc), parse_mode=ParseMode.MARKDOWN)

async def cmd_bank_money(update, ctx):
    """فلوسي — نفس رصيد البنك"""
    uid = update.effective_user.id
    acc = db.get_bank_account(uid)
    if not acc:
        # مفيش حساب بنكي — نسحب الرصيد من نقاط الجروب
        cid = update.effective_chat.id
        p = db.get_points(cid, uid)
        return await update.message.reply_text(
            f"💰 *فلوسك:* {fmt_money(p['points'])}\n\n"
            f"ℹ️ اعمل حساب بنكي: *إنشاء حساب بنكي*",
            parse_mode=ParseMode.MARKDOWN)
    # نفس رصيد البنك
    await update.message.reply_text(money_text(acc), parse_mode=ParseMode.MARKDOWN)

async def cmd_salary(update, ctx):
    """راتب"""
    uid = update.effective_user.id
    acc = db.get_bank_account(uid)
    if not acc:
        return await update.message.reply_text("⚠️ لازم تعمل حساب بنكي الأول.", parse_mode=ParseMode.MARKDOWN)
    cooldown = db.get_bank_setting("salary_cooldown", 86400)
    amount = db.get_bank_setting("salary_amount", 500)
    now = int(time.time())
    elapsed = now - (acc["last_salary"] or 0)
    if elapsed < cooldown:
        remaining = cooldown - elapsed
        return await update.message.reply_text(
            f"⏰ استلمت راتبك بالفعل!\n\n"
            f"⏳ فاضل: *{fmt_time(remaining)}*",
            parse_mode=ParseMode.MARKDOWN)
    db.update_bank_account(uid, last_salary=now)
    db.add_bank_money(uid, amount, "salary")
    new_acc = db.get_bank_account(uid)
    await update.message.reply_text(
        f"💼 *تم استلام راتبك!*\n\n"
        f"💰 +{fmt_money(amount)}\n"
        f"🏦 رصيدك الآن: *{fmt_money(new_acc['balance'])}*",
        parse_mode=ParseMode.MARKDOWN)

async def cmd_tip(update, ctx):
    """بقشيش"""
    uid = update.effective_user.id
    acc = db.get_bank_account(uid)
    if not acc:
        return await update.message.reply_text("⚠️ لازم تعمل حساب بنكي الأول.", parse_mode=ParseMode.MARKDOWN)
    cooldown = db.get_bank_setting("tip_cooldown", 21600)
    amount = db.get_bank_setting("tip_amount", 50)
    now = int(time.time())
    elapsed = now - (acc["last_tip"] or 0)
    if elapsed < cooldown:
        remaining = cooldown - elapsed
        return await update.message.reply_text(
            f"⏰ استلمت بقشيشك!\n\n"
            f"⏳ فاضل: *{fmt_time(remaining)}*",
            parse_mode=ParseMode.MARKDOWN)
    db.update_bank_account(uid, last_tip=now)
    db.add_bank_money(uid, amount, "tip")
    new_acc = db.get_bank_account(uid)
    await update.message.reply_text(
        f"🎁 *استلمت البقشيش!*\n\n"
        f"💰 +{fmt_money(amount)}\n"
        f"⏰ يمكنك استلامه مرة أخرى بعد {fmt_time(cooldown)}",
        parse_mode=ParseMode.MARKDOWN)

async def cmd_transfer(update, ctx, amount):
    """تحويل - بالرد على رسالة"""
    uid = update.effective_user.id
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ لازم ترد على رسالة الشخص اللي عاوز تحوّلله.", parse_mode=ParseMode.MARKDOWN)
    target_user = update.message.reply_to_message.from_user
    if not target_user or target_user.is_bot:
        return await update.message.reply_text("⚠️ مستخدم غير صالح.")
    if target_user.id == uid:
        return await update.message.reply_text("⚠️ مش هينفع تحوّل لنفسك 😅")
    if amount is None or amount <= 0:
        return await update.message.reply_text("⚠️ اكتب مبلغ صحيح: *تحويل 500*", parse_mode=ParseMode.MARKDOWN)
    my_acc = db.get_bank_account(uid)
    if not my_acc:
        return await update.message.reply_text("⚠️ لازم يكون عندك حساب بنكي.")
    target_acc = db.get_bank_account(target_user.id)
    if not target_acc:
        return await update.message.reply_text(f"⚠️ {escape_html(target_user.first_name)} مش عندة حساب بنكي.")
    ok, reason = db.transfer_money(uid, target_user.id, amount)
    if not ok:
        if reason == "insufficient":
            return await update.message.reply_text(f"⚠️ رصيدك مش كافي! عندك *{fmt_money(my_acc['balance'])}*", parse_mode=ParseMode.MARKDOWN)
        return await update.message.reply_text("❌ التحويل فشل، جرب تاني.")
    target_name = target_user.username and f"@{target_user.username}" or target_user.first_name
    await update.message.reply_text(
        f"💸 *تم التحويل بنجاح!*\n\n"
        f"💰 المبلغ: *{fmt_money(amount)}*\n"
        f"👤 إلى: {escape_html(target_name)}",
        parse_mode=ParseMode.MARKDOWN)

async def cmd_steal(update, ctx):
    """سرقة - بالرد"""
    uid = update.effective_user.id
    my_acc = db.get_bank_account(uid)
    if not my_acc:
        return await update.message.reply_text("⚠️ لازم تعمل حساب بنكي الأول.")
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ لازم ترد على رسالة الشخص اللي عاوز تسرقه.", parse_mode=ParseMode.MARKDOWN)
    target_user = update.message.reply_to_message.from_user
    if not target_user or target_user.is_bot:
        return await update.message.reply_text("⚠️ مستخدم غير صالح.")
    if target_user.id == uid:
        return await update.message.reply_text("⚠️ مش هينفع تسرق نفسك 😂")
    # Cooldown
    cooldown = db.get_bank_setting("steal_cooldown", 600)
    now = int(time.time())
    elapsed = now - (my_acc["last_steal"] or 0)
    if elapsed < cooldown:
        remaining = cooldown - elapsed
        return await update.message.reply_text(f"⏰ استنى *{fmt_time(remaining)}* قبل ما تسرق تاني.", parse_mode=ParseMode.MARKDOWN)
    target_acc = db.get_bank_account(target_user.id)
    if not target_acc:
        return await update.message.reply_text(f"⚠️ {escape_html(target_user.first_name)} مش عندة حساب بنكي.")
    db.update_bank_account(uid, last_steal=now)
    success_pct = db.get_bank_setting("steal_success", 40)
    fine = db.get_bank_setting("steal_fine", 50)
    s_min = db.get_bank_setting("steal_min", 50)
    s_max = db.get_bank_setting("steal_max", 300)
    target_name = target_user.username and f"@{target_user.username}" or target_user.first_name
    if random.randint(1, 100) <= success_pct:
        amount = random.randint(s_min, min(s_max, max(s_min, target_acc["balance"])))
        if amount <= 0:
            return await update.message.reply_text("⚠️ الضحية معندهاش فلوس كفاية.")
        ok, _ = db.transfer_money(target_user.id, uid, amount)
        if not ok:
            return await update.message.reply_text("❌ فشلت السرقة، جرب تاني.")
        db.add_stolen(uid, amount)
        new_acc = db.get_bank_account(uid)
        await update.message.reply_text(
            f"🥷 *عملية سرقة ناجحة!*\n\n"
            f"💰 سرقت *{fmt_money(amount)}* من {escape_html(target_name)}\n"
            f"💵 رصيدك الآن: *{fmt_money(new_acc['balance'])}*",
            parse_mode=ParseMode.MARKDOWN)
    else:
        db.deduct_bank_money(uid, fine, "fine")
        new_acc = db.get_bank_account(uid)
        await update.message.reply_text(
            f"🚨 *اتقفشت!*\n\n"
            f"❌ فشلت عملية السرقة.\n"
            f"💸 تم خصم *{fmt_money(fine)}* كغرامة.\n"
            f"💵 رصيدك الآن: *{fmt_money(new_acc['balance'])}*",
            parse_mode=ParseMode.MARKDOWN)

async def cmd_invest(update, ctx, amount):
    """استثمار"""
    uid = update.effective_user.id
    acc = db.get_bank_account(uid)
    if not acc:
        return await update.message.reply_text("⚠️ لازم تعمل حساب بنكي الأول.")
    if amount is None or amount <= 0:
        return await update.message.reply_text("⚠️ اكتب مبلغ صحيح: *استثمار 1000*", parse_mode=ParseMode.MARKDOWN)
    if acc["balance"] < amount:
        return await update.message.reply_text(f"⚠️ رصيدك مش كافي! عندك *{fmt_money(acc['balance'])}*", parse_mode=ParseMode.MARKDOWN)
    cooldown = db.get_bank_setting("invest_cooldown", 3600)
    now = int(time.time())
    elapsed = now - (acc["last_invest"] or 0)
    if elapsed < cooldown:
        remaining = cooldown - elapsed
        return await update.message.reply_text(f"⏰ استنى *{fmt_time(remaining)}* قبل ما تستثمر تاني.", parse_mode=ParseMode.MARKDOWN)
    ok = db.deduct_bank_money(uid, amount, "invest")
    if not ok:
        return await update.message.reply_text("❌ فشل الاستثمار، جرب تاني.")
    pmin = db.get_bank_setting("invest_min_pct", 1)
    pmax = db.get_bank_setting("invest_max_pct", 15)
    pct = random.randint(pmin, pmax)
    profit = int(amount * pct / 100)
    total = amount + profit
    db.add_bank_money(uid, total, "invest_return")
    db.update_bank_account(uid, last_invest=now)
    await update.message.reply_text(
        f"📈 *استثمارك نجح!*\n\n"
        f"💰 المبلغ: *{fmt_money(amount)}*\n"
        f"📊 الربح: *+{pct}%*\n"
        f"💵 العائد: *{fmt_money(total)}*",
        parse_mode=ParseMode.MARKDOWN)

async def cmd_luck(update, ctx, amount):
    """حظ"""
    uid = update.effective_user.id
    acc = db.get_bank_account(uid)
    if not acc:
        return await update.message.reply_text("⚠️ لازم تعمل حساب بنكي الأول.")
    if amount is None or amount <= 0:
        return await update.message.reply_text("⚠️ اكتب مبلغ صحيح: *حظ 500*", parse_mode=ParseMode.MARKDOWN)
    if acc["balance"] < amount:
        return await update.message.reply_text(f"⚠️ رصيدك مش كافي! عندك *{fmt_money(acc['balance'])}*", parse_mode=ParseMode.MARKDOWN)
    cooldown = db.get_bank_setting("luck_cooldown", 3600)
    now = int(time.time())
    elapsed = now - (acc["last_luck"] or 0)
    if elapsed < cooldown:
        remaining = cooldown - elapsed
        return await update.message.reply_text(f"⏰ استنى *{fmt_time(remaining)}* قبل ما تلعب تاني.", parse_mode=ParseMode.MARKDOWN)
    win_pct = db.get_bank_setting("luck_win_pct", 45)
    db.update_bank_account(uid, last_luck=now)
    if random.randint(1, 100) <= win_pct:
        db.add_bank_money(uid, amount, "luck_win")
        new_acc = db.get_bank_account(uid)
        await update.message.reply_text(
            f"🎰 *الحظ ابتسم لك!*\n\n"
            f"💰 ربحت *{fmt_money(amount)}*\n"
            f"💵 رصيدك الآن: *{fmt_money(new_acc['balance'])}*",
            parse_mode=ParseMode.MARKDOWN)
    else:
        db.deduct_bank_money(uid, amount, "luck_lose")
        new_acc = db.get_bank_account(uid)
        await update.message.reply_text(
            f"🎰 *حظك سيئ!*\n\n"
            f"💸 خسرت *{fmt_money(amount)}*\n"
            f"💵 رصيدك الآن: *{fmt_money(new_acc['balance'])}*",
            parse_mode=ParseMode.MARKDOWN)

async def cmd_top_money(update, ctx):
    """توب الفلوس"""
    cid = update.effective_chat.id
    is_group = update.effective_chat.type in GROUP_TYPES
    kb = M([[B("🥷 توب الحرامية ➡️", callback_data="top:thieves")]])
    if is_group:
        top = db.get_top(cid, 10)
        if not top:
            return await update.message.reply_text("📊 لا يوجد لاعبين بعد.", reply_markup=kb)
        lines = ["🏆 *Bank Turbo - أغنى 10 في الجروب*\n"]
        medals = ["🥇","🥈","🥉"]
        for i, item in enumerate(top, 1):
            try:
                m = await ctx.bot.get_chat_member(cid, item["user_id"])
                name = m.user.first_name or "عضو"
                display = escape_html(name)
            except:
                u = db.get_user(item["user_id"])
                display = escape_html(u["first_name"]) if u and u["first_name"] else f"عضو {item['user_id']}"
            prefix = medals[i-1] if i <= 3 else f"{i}."
            lines.append(f"{prefix} {display} — *{fmt_money(item['points'])}*")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        top = db.get_top_money(10)
        if not top:
            return await update.message.reply_text("📊 لا يوجد حسابات بعد.", reply_markup=kb)
        lines = ["🏆 *Bank Turbo - أغنى 10 أشخاص*\n"]
        medals = ["🥇","🥈","🥉"]
        for i, item in enumerate(top, 1):
            display = escape_html(item['first_name'] or "عضو")
            prefix = medals[i-1] if i <= 3 else f"{i}."
            lines.append(f"{prefix} {display} — *{fmt_money(item['balance'])}*")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def cb_top_thieves(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """الصفحة 2: توب الحرامية"""
    q = update.callback_query
    await q.answer()
    top = db.get_top_thieves(10)
    kb = M([
        [B("◀️", callback_data="top:money"), B("▶️", callback_data="top:vip")],
    ])
    if not top:
        return await safe_edit(q, "🥷 *توب الحرامية*\n\n📭 مفيش حرامية لسه 😅",
                              parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    lines = ["🥷 *توب الحرامية - أكبر 10*\n"]
    medals = ["🥇","🥈","🥉"]
    for i, item in enumerate(top, 1):
        display = escape_html(item['first_name'] or "عضو")
        prefix = medals[i-1] if i <= 3 else f"{i}."
        lines.append(f"{prefix} {display} — سرق *{fmt_money(item['total_stolen'])}*")
    lines.append("\n_2/3_")
    await safe_edit(q, "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def cb_top_money_btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """زر توب الفلوس — من الزر"""
    q = update.callback_query
    await q.answer()
    top = db.get_top_money(10)
    kb = M([
        [B("▶️", callback_data="top:thieves"), B("🔙 رجوع", callback_data="panel:home")],
    ])
    if not top:
        return await safe_edit(q, "🏆 *توب الفلوس*\n\n📭 لا يوجد حسابات بعد.",
                              parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    lines = ["🏆 *توب الفلوس - أغنى 10*\n"]
    medals = ["🥇","🥈","🥉"]
    for i, item in enumerate(top, 1):
        display = escape_html(item['first_name'] or "عضو")
        prefix = medals[i-1] if i <= 3 else f"{i}."
        lines.append(f"{prefix} {display} — *{fmt_money(item['balance'])}*")
    lines.append("\n_1/3_")
    await safe_edit(q, "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def cb_top_vip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """الصفحة 3: قائمة VIP"""
    q = update.callback_query
    await q.answer()
    kb = M([
        [B("◀️", callback_data="top:thieves"), B("🔙 رجوع", callback_data="panel:home")],
    ])
    # نجمع كل VIP في كل الجروبات
    vips = db.list_all_vips()
    if not vips:
        return await safe_edit(q, "👑 *قائمة VIP*\n\n📭 مفيش مميزين لسه.",
                              parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    lines = [f"👑 *قائمة VIP* ({len(vips)})\n"]
    for uid in vips[:50]:
        u = db.get_user(uid)
        if u:
            lines.append(f"• {escape_html(u['first_name'])}")
        else:
            lines.append(f"• عضو {uid}")
    lines.append("\n_3/3_")
    await safe_edit(q, "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def cmd_top_thieves(update, ctx):
    """توب الحرامية"""
    top = db.get_top_thieves(10)
    if not top:
        return await update.message.reply_text("📊 مفيش حرامية لسه 😅")
    lines = ["🥷 *Bank Turbo - أكبر 10 حرامية*\n"]
    medals = ["🥇","🥈","🥉"]
    for i, item in enumerate(top, 1):
        display = escape_html(item['first_name'] or "عضو")
        prefix = medals[i-1] if i <= 3 else f"{i}."
        lines.append(f"{prefix} {display} — سرق *{fmt_money(item['total_stolen'])}*")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

# ============ نهاية الجزء 3 ============

# ============ بداية الجزء 4 — الأزرار ============

# ==================== الأزرار الأساسية ====================
def points_system_text():
    """وصف نظام النقاط"""
    return (
        "📋 *نظام النقاط*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "💬 *الرسالة العادية:*\n"
        "• نقطة واحدة (+1)\n\n"
        "💬 *الرد على رسالة:*\n"
        "• نقطتين (+2)\n\n"
        "✅ *إجابة صحيحة في لعبة:*\n"
        "• عشر نقاط (+10)\n\n"
        "🤝 *مساعدة (يحددها المالك):*\n"
        "• حسب ما يحدده المالك\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 *كل 10 نقط = 10 جنيه مصري*\n\n"
        "📌 *أوامر مفيدة:*\n"
        "• إحصائياتي — نقاطك\n"
        "• توب — أعلى 10\n"
        "• فلوسي — رصيدك"
    )

# cb_points_info — اتشال (بنستخدم points_system_text كأمر في الجروب)

def main_menu_kb(owner: bool):
    rows = [
        [B("➕ أضفني إلى مجموعتك", url=f"https://t.me/{BOT_USERNAME}?startgroup=true&admin=delete_messages+invite_users+restrict_members+pin_messages+manage_chat+delete_stories")],
        [B("⚙️ إدارة مجموعاتي", callback_data="panel:list")],
        [B("📊 إحصائياتي", callback_data="stats:me")],
        [B("🏅 توب 10", callback_data="stats:top")],
        [B("📖 الأوامر", callback_data="commands:show:0")],
    ]
    if owner:
        rows.append([B("👑 إعدادات المالك", callback_data="owner:menu")])
    return M(rows)

def bank_menu_kb():
    return M([
        [B("🏦 إنشاء حساب بنكي", callback_data="bank:create_help")],
        [B("💳 حسابي البنكي", callback_data="bank:info_help")],
        [B("💰 فلوسي", callback_data="bank:money_help")],
        [B("💼 راتب", callback_data="bank:salary_help")],
        [B("🎁 بقشيش", callback_data="bank:tip_help")],
        [B("🔙 رجوع", callback_data="panel:home")],
    ])

def owner_menu_kb():
    return M([
        [B("📢 اشتراكات البوت", callback_data="owner:subs")],
        [B("💬 الردود التلقائية", callback_data="owner:ar")],
        [B("🚫 كلمات محظورة عامة", callback_data="owner:gban")],
        [B("🏆 إدارة الألعاب", callback_data="owner:games")],
        [B("🏦 البنك", callback_data="owner:bank")],
        [B("🌐 كل جروبات البوت", callback_data="owner:allgroups")],
        [B("📣 بث لكل الجروبات", callback_data="owner:broadcast")],
        [B("📊 إحصائيات البوت", callback_data="owner:stats")],
        [B("👑 المطورين", callback_data="owner:devs")],
        [B("💾 قاعدة البيانات", callback_data="owner:db")],
        [B("🔙 رجوع", callback_data="panel:home")],
    ])

def owner_bank_kb():
    return M([
        [B("💼 الراتب", callback_data="obank:salary")],
        [B("🎁 البقشيش", callback_data="obank:tip")],
        [B("🔪 السرقة", callback_data="obank:steal")],
        [B("📈 الاستثمار", callback_data="obank:invest")],
        [B("🎰 الحظ", callback_data="obank:luck")],
        [B("💍 الزواج", callback_data="obank:marriage")],
        [B("👶 الأطفال", callback_data="obank:children")],
        [B("🏠 الممتلكات", callback_data="obank:props")],
        [B("🔙 رجوع", callback_data="owner:menu")],
    ])

def obank_marriage_kb():
    return M([
        [B("💰 تكلفة الزواج", callback_data="obank:set:marriage_cost")],
        [B("💸 استرداد الطلاق", callback_data="obank:set:divorce_refund")],
        [B("🔙 رجوع", callback_data="owner:bank")],
    ])

def obank_children_kb():
    return M([
        [B("💰 تكلفة الطفل", callback_data="obank:set:child_cost")],
        [B("💵 ربح الطفل/ساعة", callback_data="obank:set:child_income")],
        [B("👥 أقصى عدد", callback_data="obank:set:max_children")],
        [B("⏰ الكول داون", callback_data="obank:set:child_cooldown")],
        [B("🔙 رجوع", callback_data="owner:bank")],
    ])

def obank_props_kb():
    return M([
        [B("💰 تكلفة الممتلك", callback_data="obank:set:prop_cost")],
        [B("📉 أقل ربح %", callback_data="obank:set:prop_sell_min")],
        [B("📈 أكبر ربح %", callback_data="obank:set:prop_sell_max")],
        [B("⏰ الكول داون", callback_data="obank:set:prop_cooldown")],
        [B("🔙 رجوع", callback_data="owner:bank")],
    ])

def obank_salary_kb():
    return M([
        [B("💰 المبلغ", callback_data=f"obank:set:salary_amount")],
        [B("⏰ الكول داون", callback_data=f"obank:set:salary_cooldown")],
        [B("🔙 رجوع", callback_data="owner:bank")],
    ])

def obank_tip_kb():
    return M([
        [B("💰 المبلغ", callback_data=f"obank:set:tip_amount")],
        [B("⏰ الكول داون", callback_data=f"obank:set:tip_cooldown")],
        [B("🔙 رجوع", callback_data="owner:bank")],
    ])

def obank_steal_kb():
    return M([
        [B("🎯 نسبة النجاح %", callback_data="obank:set:steal_success")],
        [B("💸 الغرامة", callback_data="obank:set:steal_fine")],
        [B("🔽 أقل مبلغ", callback_data="obank:set:steal_min")],
        [B("🔼 أكبر مبلغ", callback_data="obank:set:steal_max")],
        [B("⏰ الكول داون", callback_data="obank:set:steal_cooldown")],
        [B("🔙 رجوع", callback_data="owner:bank")],
    ])

def obank_invest_kb():
    return M([
        [B("📉 أقل ربح %", callback_data="obank:set:invest_min_pct")],
        [B("📈 أكبر ربح %", callback_data="obank:set:invest_max_pct")],
        [B("⏰ الكول داون", callback_data="obank:set:invest_cooldown")],
        [B("🔙 رجوع", callback_data="owner:bank")],
    ])

def obank_luck_kb():
    return M([
        [B("🎯 نسبة الفوز %", callback_data="obank:set:luck_win_pct")],
        [B("⏰ الكول داون", callback_data="obank:set:luck_cooldown")],
        [B("🔙 رجوع", callback_data="owner:bank")],
    ])

def owner_gban_kb():
    return M([
        [B("➕ إضافة كلمات", callback_data="gban:add")],
        [B("🗑 حذف كلمة", callback_data="gban:del_list")],
        [B("📋 عرض الكلمات", callback_data="gban:show")],
        [B("🔙 رجوع", callback_data="owner:menu")],
    ])

def owner_gban_delete_kb(items):
    rows = []
    for it in items:
        rows.append([B(f"🗑 {it['word'][:30]}", callback_data=f"gban:del:{it['id']}")])
    rows.append([B("🔙 رجوع", callback_data="owner:gban")])
    return M(rows)

def owner_db_kb():
    return M([
        [B("📤 تصدير قاعدة البيانات", callback_data="owner:db:export")],
        [B("📥 استعادة قاعدة البيانات", callback_data="owner:db:import")],
        [B("🔙 رجوع", callback_data="owner:menu")],
    ])

def owner_subs_kb():
    return M([
        [B("➕ إضافة قناة", callback_data="owner:add")],
        [B("🗑 حذف قناة", callback_data="owner:del_list")],
        [B("📋 عرض القنوات", callback_data="owner:show")],
        [B("🔙 رجوع", callback_data="owner:menu")],
    ])

def owner_ar_kb():
    return M([
        [B("➕ إضافة رد", callback_data="ar:add")],
        [B("🗑 حذف رد", callback_data="ar:del_list")],
        [B("📋 عرض الردود", callback_data="ar:show")],
        [B("🔙 رجوع", callback_data="owner:menu")],
    ])

def owner_games_kb():
    return M([
        [B("🎭 النكت", callback_data="owner:jokes")],
        [B("⏰ التذكيرات", callback_data="owner:reminders")],
        [B("⚡ الأسرع", callback_data="og:fastest")],
        [B("🔤 رتب الحروف", callback_data="og:scramble")],
        [B("❓ أسئلة عامة", callback_data="og:questions")],
        [B("🇬🇧 إنجليزي", callback_data="og:english")],
        [B("💭 كت", callback_data="og:ket")],
        [B("🕵️ الجاسوس/بكاسة", callback_data="og:spy")],
        [B("📖 القصة المبعثرة", callback_data="og:story")],
        [B("🧩 أكمل النمط", callback_data="og:pattern")],
        [B("👀 ركز", callback_data="og:focus")],
        [B("🔍 إيه المختلف", callback_data="og:odd")],
        [B("🎯 خمن الكلمة", callback_data="og:guess")],
        [B("🔢 خمن الرقم", callback_data="og:info:number")],
        [B("🔢 احسب", callback_data="og:info:calc")],
        [B("😀 الإيموجي", callback_data="og:info:emoji")],
        [B("⏱ مؤقت", callback_data="og:info:timer")],
        [B("👥 المافيا", callback_data="og:info:mafia")],
        [B("🔙 رجوع", callback_data="owner:menu")],
    ])

def owner_jokes_kb():
    return M([
        [B("➕ إضافة نكتة", callback_data="jokes:add")],
        [B("🗑 حذف نكتة", callback_data="jokes:del_list")],
        [B("📋 عرض النكت", callback_data="jokes:show")],
        [B("⏱ وقت النكتة", callback_data="jokes:cooldown")],
        [B("🔙 رجوع", callback_data="owner:games")],
    ])


def owner_jokes_delete_kb(jokes):
    rows = []
    for j in jokes[:30]:
        text = j["text"][:40]
        rows.append([B(f"🗑 {text}", callback_data=f"jokes:del:{j['id']}")])
    rows.append([B("🔙 رجوع", callback_data="owner:jokes")])
    return M(rows)


def owner_reminders_kb():
    return M([
        [B("⏰ أقصى وقت للتذكير", callback_data="reminders:set:max")],
        [B("🔙 رجوع", callback_data="owner:games")],
    ])

def owner_game_kb(game):
    return M([
        [B("➕ إضافة", callback_data=f"og:add:{game}")],
        [B("🗑 حذف", callback_data=f"og:del_list:{game}")],
        [B("📋 عرض", callback_data=f"og:show:{game}")],
        [B("🔙 رجوع", callback_data="owner:games")],
    ])

def owner_game_delete_kb(game, items):
    rows = []
    for it in items[:30]:
        content = (it["content"] or "")[:25]
        if game in (GAME_QUESTIONS, GAME_ENGLISH, GAME_PATTERN, GAME_FOCUS, GAME_ODD, GAME_GUESS):
            ans = (it["answer"] or "")[:15].replace("\n", " ")
            label = f"🗑 {content}" + (f" ← {ans}" if ans else "")
        else:
            label = f"🗑 {content}"
        rows.append([B(label, callback_data=f"og:del:{it['id']}:{game}")])
    rows.append([B("🔙 رجوع", callback_data=f"og:menu:{game}")])
    return M(rows)

def owner_spy_kb():
    return M([
        [B("➕ إضافة كلمة سرية", callback_data="spy:add_word")],
        [B("🗑 حذف كلمة", callback_data="spy:del_list")],
        [B("📋 عرض الكلمات", callback_data="spy:show")],
        [B("⚙️ إعدادات اللعبة", callback_data="spy:settings")],
        [B("🔙 رجوع", callback_data="owner:games")],
    ])

def owner_spy_settings_kb():
    return M([
        [B("👥 الحد الأدنى للاعبين", callback_data="spy:set:min")],
        [B("👥 الحد الأقصى للاعبين", callback_data="spy:set:max")],
        [B("⏱ مدة النقاش", callback_data="spy:set:disc")],
        [B("🗳 مدة التصويت", callback_data="spy:set:vote")],
        [B("🔙 رجوع", callback_data="og:spy")],
    ])

def owner_spy_delete_kb(items):
    rows = []
    for it in items:
        rows.append([B(f"🗑 {(it['content'] or '')[:30]}", callback_data=f"spy:del:{it['id']}")])
    rows.append([B("🔙 رجوع", callback_data="og:spy")])
    return M(rows)

def cancel_kb(target):
    return M([[B("🔙 إلغاء", callback_data=f"owner:cancel:{target}")]])

def games_menu_kb():
    return M([[B("🔙 رجوع", callback_data="panel:home")]])

def groups_list_kb(groups, user_id):
    rows = []
    for g in groups:
        title = (g['title'] or str(g['chat_id']))[:25]
        rows.append([
            B(f"⚙️ {title}", callback_data=f"panel:g:{g['chat_id']}"),
            B("🗑", callback_data=f"panel:forget:{g['chat_id']}")
        ])
    rows.append([B("🔙 رجوع", callback_data="panel:home")])
    return M(rows)

def all_groups_kb(groups):
    rows = []
    for g in groups:
        title = (g["title"] or str(g["chat_id"]))[:35]
        rows.append([B(f"📌 {title}", callback_data=f"owner:goto:{g['chat_id']}")])
    rows.append([B("🔙 رجوع", callback_data="owner:menu")])
    return M(rows)

def group_data_kb(chat_id):
    return M([
        [B("📂 فتح الجروب", callback_data=f"owner:open:{chat_id}")],
        [B("📊 بيانات الجروب", callback_data=f"owner:data:{chat_id}")],
        [B("🔙 رجوع", callback_data="owner:allgroups")],
    ])

def group_data_sub_kb(chat_id):
    return M([
        [B("👥 أعضاء الجروب", callback_data=f"data:members:{chat_id}")],
        [B("📨 رسائل الجروب", callback_data=f"data:messages:{chat_id}")],
        [B("🔙 رجوع", callback_data=f"owner:goto:{chat_id}")],
    ])

def group_panel_kb(group, ch_count, antilink=False):
    rows = []
    if group["activated"]:
        rows.append([B("⛔ تعطيل البوت", callback_data=f"panel:off:{group['chat_id']}")])
    else:
        rows.append([B("✅ تفعيل البوت", callback_data=f"panel:on:{group['chat_id']}")])
    rows.append([B("➕ إضافة قناة", callback_data=f"panel:add:{group['chat_id']}")])
    if ch_count > 0:
        rows.append([B(f"📋 القنوات ({ch_count})", callback_data=f"panel:chs:{group['chat_id']}")])
    rows.append([B("🛡 الحماية", callback_data=f"panel:protect:{group['chat_id']}")])
    rows.append([B("🔄 تحديث", callback_data=f"panel:g:{group['chat_id']}"), B("🔙 رجوع", callback_data="panel:list")])
    return M(rows)

def protect_kb(chat_id, antilink=False, welcome=True):
    al_label = "🔗 منع الروابط: ✅" if antilink else "🔗 منع الروابط: ❌"
    wl_label = "👋 الترحيب: ✅" if welcome else "👋 الترحيب: ❌"
    return M([
        [B(al_label, callback_data=f"protect:al:{chat_id}")],
        [B(wl_label, callback_data=f"protect:wl:{chat_id}")],
        [B("🚫 كلمات ممنوعة", callback_data=f"protect:bw:{chat_id}")],
        [B("⏰ رسائل مجدولة", callback_data=f"protect:sched:{chat_id}")],
        [B("🔔 منشن دوري", callback_data=f"protect:mention:{chat_id}")],
        [B("🔙 رجوع", callback_data=f"panel:g:{chat_id}")],
    ])

def schedule_kb(chat_id):
    return M([
        [B("➕ إضافة رسالة مجدولة", callback_data=f"sched:add:{chat_id}")],
        [B("🗑 حذف رسالة", callback_data=f"sched:del_list:{chat_id}")],
        [B("📋 عرض الرسائل", callback_data=f"sched:show:{chat_id}")],
        [B("🔙 رجوع", callback_data=f"panel:protect:{chat_id}")],
    ])

def schedule_delete_kb(chat_id, items):
    rows = []
    for it in items:
        label = f"🗑 {it['text'][:30]} (كل {it['interval_min']}د)"
        rows.append([B(label, callback_data=f"sched:del:{chat_id}:{it['id']}")])
    rows.append([B("🔙 رجوع", callback_data=f"protect:sched:{chat_id}")])
    return M(rows)

def mention_kb(chat_id, enabled):
    e_label = "✅ مفعل" if enabled else "❌ معطل"
    return M([
        [B(f"الحالة: {e_label}", callback_data=f"mention:toggle:{chat_id}")],
        [B("⏰ الوقت (بالدقايق)", callback_data=f"mention:time:{chat_id}")],
        [B("👥 عدد المنشن", callback_data=f"mention:count:{chat_id}")],
        [B("✍️ نص الرسالة", callback_data=f"mention:text:{chat_id}")],
        [B("🔙 رجوع", callback_data=f"panel:protect:{chat_id}")],
    ])

def banned_words_kb(chat_id, words):
    rows = []
    for w in words:
        rows.append([B(f"🗑 {w['word'][:25]}", callback_data=f"protect:bwd:{w['id']}")])
    rows.append([B("➕ إضافة كلمة", callback_data=f"protect:bwa:{chat_id}")])
    rows.append([B("🔙 رجوع", callback_data=f"panel:protect:{chat_id}")])
    return M(rows)

def channels_kb(cid, chans):
    rows = [[B(f"🗑 {c['title'] or c['username'] or c['channel_id']}", callback_data=f"panel:del:{cid}:{c['channel_id']}")] for c in chans]
    rows.append([B("🔙 رجوع", callback_data=f"panel:g:{cid}")])
    return M(rows)

def default_channels_kb(chans):
    rows = [[B(f"🗑 {c['title'] or c['username'] or c['channel_id']}", callback_data=f"owner:del:{c['channel_id']}")] for c in chans]
    rows.append([B("🔙 رجوع", callback_data="owner:subs")])
    return M(rows)

def ar_delete_kb(replies):
    rows = []
    for r in replies:
        trigger = r["trigger"][:20]
        response = r["response"][:25]
        rows.append([B(f"🗑 {trigger} ← {response}", callback_data=f"ar:del:{r['id']}")])
    rows.append([B("🔙 رجوع", callback_data="owner:ar")])
    return M(rows)

def members_list_kb(chat_id, members, page=0):
    rows = []
    per_page = 10
    start = page * per_page
    chunk = members[start:start+per_page]
    for m in chunk:
        rows.append([B(f"👤 {m['first_name'][:25]}", callback_data=f"data:member:{chat_id}:{m['user_id']}")])
    nav = []
    if page > 0:
        nav.append(B("◀️ السابق", callback_data=f"data:members:{chat_id}:{page-1}"))
    if start + per_page < len(members):
        nav.append(B("▶️ التالي", callback_data=f"data:members:{chat_id}:{page+1}"))
    if nav: rows.append(nav)
    rows.append([B("🔙 رجوع", callback_data=f"owner:data:{chat_id}")])
    return M(rows)

def subscribe_kb(chans, uid):
    rows = []
    for c in chans:
        if c.get("link"):
            rows.append([B(f"📢 {c['title'] or 'اشترك'}", url=c["link"])])
    rows.append([B("✅ تحقق من اشتراكي", callback_data=f"sub:ck:{uid}")])
    return M(rows)

# ==================== قائمة الأوامر (3 صفحات) ====================
def commands_kb(page):
    if page == 0:
        nav = [B("▶️", callback_data="commands:show:1")]
    elif page == 1:
        nav = [B("◀️", callback_data="commands:show:0"), B("▶️", callback_data="commands:show:2")]
    else:
        nav = [B("◀️", callback_data="commands:show:1")]
    return M([nav])

# ==================== نصوص البنك ====================
def bank_create_help_text():
    return ("🏦 *إنشاء حساب بنكي*\n\n"
            "اكتب في الجروب أو الخاص:\n"
            "`إنشاء حساب بنكي`\n\n"
            "هيتحول رصيدك الحالي لحسابك الجديد ✅")

def bank_info_help_text():
    return ("💳 *حسابي البنكي*\n\n"
            "اكتب:\n`حسابي البنكي`\n\n"
            "هيعرضلك رقم حسابك ورصيدك.")

def bank_money_help_text():
    return ("💰 *فلوسي*\n\n"
            "اكتب:\n`فلوسي`\n\n"
            "هيعرضلك رصيدك الحالي.")

def bank_salary_help_text():
    return ("💼 *راتب*\n\n"
            "اكتب:\n`راتب`\n\n"
            "هتستلم الراتب كل 24 ساعة 💰")

def bank_tip_help_text():
    return ("🎁 *بقشيش*\n\n"
            "اكتب:\n`بقشيش` أو `بخشيش`\n\n"
            "هتستلم كل 6 ساعات 💰")

# ============ نهاية الجزء 4 ============

# ============ بداية الجزء 5 — النصوص + الأوامر ============

# ==================== دوال مساعدة للنصوص ====================
def fmt_time(seconds):
    """تنسيق الوقت"""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} ثانية"
    mins = seconds // 60
    if mins < 60:
        return f"{mins} دقيقة"
    hours = mins // 60
    mins = mins % 60
    if hours < 24:
        return f"{hours} ساعة" + (f" و{mins} دقيقة" if mins else "")
    days = hours // 24
    hours = hours % 24
    return f"{days} يوم" + (f" و{hours} ساعة" if hours else "")

def game_name(g):
    return {
        GAME_FASTEST: "⚡ الأسرع",
        GAME_SCRAMBLE: "🔤 رتب الحروف",
        GAME_QUESTIONS: "❓ أسئلة عامة",
        GAME_ENGLISH: "🇬🇧 إنجليزي",
        GAME_KET: "💭 كت",
        GAME_SPY: "🕵️ الجاسوس/بكاسة",
        GAME_STORY: "📖 القصة المبعثرة",
        GAME_PATTERN: "🧩 أكمل النمط",
        GAME_FOCUS: "👀 ركز",
        GAME_ODD: "🔍 إيه المختلف",
        GAME_GUESS: "🎯 خمن الكلمة",
    }.get(g, g)

def help_text():
    return (
        "🤖 *بوت Laila*\n\n"
        "📌 *للتفعيل:*\n"
        "ارفعني مشرفًا في الجروب\n\n"
        "🎮 *الألعاب:*\n"
        "اكتب امر \"الالعاب\"\n"
        "ثم اختر اي لعبة.\n\n"
        "💰 *النقاط:*\n"
        "رسالة عادية = 1 جنيه مصري \n"
        "رسالة رد = 2 جنيه مصري \n"
        "إجابة صحيحة = 10 جنيه مصري \n\n"
        "🏦 *البنك:*\n"
        "📌 اكتب \n"
        "\"إنشاء حساب بنكي\"\n\n"
        "🛡 *الحماية:*\n"
        "إدارة مجموعاتي → الحماية\n\n"
        "📖 كل الأوامر: /commands"
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """أمر /help — للكل في الخاص"""
    if update.effective_chat.type != ChatType.PRIVATE:
        return
    try:
        await update.message.reply_text(help_text(), parse_mode=ParseMode.MARKDOWN)
    except: pass

async def cmd_commands(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """أمر /commands — للكل في الخاص"""
    if update.effective_chat.type != ChatType.PRIVATE:
        return
    try:
        await update.message.reply_text(
            commands_page_text(0),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=commands_kb(0))
    except: pass

def main_text(user):
    return (f"أهلاً بك {user.first_name} 👋\n\n"
            "🤖 *بوت Laila*\n\n"
            "✨ *بيعمل إيه؟*\n"
            "🛡 اشتراك إجباري\n"
            "⚙️ إدارة جروبات وحماية\n"
            "🎮 ألعاب ونقاط\n\n"
            "📌 لتفعيل البوت، يُرجى رفعه مشرفًا في الجروب.\n\n"
            "اختار من الأزرار تحت 👇")

def owner_text():
    chans = db.list_default_channels()
    replies = db.list_auto_replies()
    gban = db.list_global_banned_words()
    users_count = db.count_users()
    # عدد الجروبات النشطة (من الكاش لو موجود)
    try:
        active_count = db.count_active_groups()
    except:
        active_count = len(db.list_groups())
    return ("👑 *إعدادات المالك*\n\n"
            f"📢 الاشتراكات: {len(chans)} قناة\n"
            f"💬 الردود التلقائية: {len(replies)} رد\n"
            f"🚫 كلمات محظورة عامة: {len(gban)}\n"
            f"🌐 عدد الجروبات: {active_count}\n"
            f"👥 عدد المستخدمين: {users_count}\n"
            f"🎮 عدد الألعاب: 17\n\n"
            "اختر القسم:")

def owner_gban_text():
    words = db.list_global_banned_words()
    return ("🚫 *كلمات محظورة عامة*\n\n"
            f"عدد الكلمات: *{len(words)}*\n\n"
            "⚠️ الكلمات دي بتتحذف من *كل الجروبات* اللي فيها البوت")

def owner_db_text():
    return ("💾 *قاعدة البيانات*\n\n"
            "• *تصدير:* البوت هيبعتلك ملف `data.db`\n"
            "• *استعادة:* ابعت للبوت ملف `data.db`\n\n"
            "⚠️ الاستعادة هتمسح كل البيانات الحالية!")

def owner_subs_text():
    chans = db.list_default_channels()
    cur = "_لا توجد_" if not chans else "\n".join(f"• {c['title'] or c['username'] or c['channel_id']}" for c in chans)
    return ("📢 *اشتراكات البوت*\n\n"
            "القنوات الافتراضية تُطلب من أي شخص يفتح البوت في الخاص.\n\n"
            f"الحالية:\n{cur}")

def owner_ar_text():
    replies = db.list_auto_replies()
    return ("💬 *الردود التلقائية*\n\n"
            f"عدد الردود: {len(replies)}\n\n"
            "⚠️ *التطابق ذكي*\n\n"
            "🎯 *ردود مدمجة:*\n"
            "• *المالك* → يرد بمالك الجروب\n"
            "• *الأدمن* → يرد بالأدمنز")

def owner_games_text():
    games = [
        ("⚡ الأسرع", db.count_game_content(GAME_FASTEST)),
        ("🔤 رتب الحروف", db.count_game_content(GAME_SCRAMBLE)),
        ("❓ أسئلة عامة", db.count_game_content(GAME_QUESTIONS)),
        ("🇬🇧 إنجليزي", db.count_game_content(GAME_ENGLISH)),
        ("💭 كت", db.count_game_content(GAME_KET)),
        ("🕵️ الجاسوس/بكاسة", db.count_game_content(GAME_SPY)),
        ("📖 القصة المبعثرة", db.count_game_content(GAME_STORY)),
        ("🧩 أكمل النمط", db.count_game_content(GAME_PATTERN)),
        ("👀 ركز", db.count_game_content(GAME_FOCUS)),
        ("🔍 إيه المختلف", db.count_game_content(GAME_ODD)),
        ("🎯 خمن الكلمة", db.count_game_content(GAME_GUESS)),
        ("🔢 خمن الرقم", "من البوت"),
        ("🔢 احسب", "من البوت"),
        ("😀 الإيموجي", "من البوت"),
        ("⏱ مؤقت", "من البوت"),
        ("👥 المافيا", "من البوت"),
        ("🔢 ترتيب الأرقام", "من البوت"),
    ]
    lines = ["🏆 *إدارة الألعاب*\n"]
    for name, count in games:
        if isinstance(count, int):
            lines.append(f"• {name}: *{count}* عنصر")
        else:
            lines.append(f"• {name}: _{count}_")
    lines.append("\nاختر اللعبة للتحكم:")
    return "\n".join(lines)

def owner_bank_text():
    return ("🏦 *إدارة Bank Turbo*\n\n"
            "اختر القسم اللي عاوز تعدله:")

def owner_jokes_text():
    count = db.count_jokes()
    cd = db.get_bank_setting("joke_cooldown", 600)
    return (f"🎭 *إعدادات النكت*\n\n"
            f"📝 عدد النكت: *{count}*\n"
            f"⏱ كول داون النكتة: *{fmt_time(cd)}*")


def owner_reminders_text():
    rm = db.get_bank_setting("reminder_max", 604800)
    return (f"⏰ *إعدادات التذكيرات*\n\n"
            f"⏱ أقصى وقت: *{fmt_time(rm)}*")

def owner_bank_marriage_text():
    mc = db.get_bank_setting("marriage_cost", 5000)
    dr = db.get_bank_setting("divorce_refund", 3000)
    return (f"💍 *إعدادات الزواج*\n\n"
            f"💰 تكلفة الزواج: *{fmt_money(mc)}*\n"
            f"💸 استرداد الطلاق: *{fmt_money(dr)}*")


def owner_bank_children_text():
    cc = db.get_bank_setting("child_cost", 500)
    ci = db.get_bank_setting("child_income", 100)
    mx = db.get_bank_setting("max_children", 5)
    cd = db.get_bank_setting("child_cooldown", 86400)
    return (f"👶 *إعدادات الأطفال*\n\n"
            f"💰 تكلفة الطفل: *{fmt_money(cc)}*\n"
            f"💵 ربح الطفل/ساعة: *{fmt_money(ci)}*\n"
            f"👥 أقصى عدد: *{mx}*\n"
            f"⏰ الكول داون: *{fmt_time(cd)}*")


def owner_bank_props_text():
    pc = db.get_bank_setting("prop_cost", 1000)
    mn = db.get_bank_setting("prop_sell_min", 1)
    mx = db.get_bank_setting("prop_sell_max", 25)
    cd = db.get_bank_setting("prop_cooldown", 600)
    return (f"🏠 *إعدادات الممتلكات*\n\n"
            f"💰 تكلفة الممتلك: *{fmt_money(pc)}*\n"
            f"📉 أقل ربح: *{mn}%*\n"
            f"📈 أكبر ربح: *{mx}%*\n"
            f"⏰ الكول داون: *{fmt_time(cd)}*")

def owner_bank_salary_text():
    amt = db.get_bank_setting("salary_amount", 500)
    cd = db.get_bank_setting("salary_cooldown", 86400)
    return (f"💼 *الراتب*\n\n"
            f"💰 المبلغ: *{fmt_money(amt)}*\n"
            f"⏰ الكول داون: *{fmt_time(cd)}*")

def owner_bank_tip_text():
    amt = db.get_bank_setting("tip_amount", 50)
    cd = db.get_bank_setting("tip_cooldown", 21600)
    return (f"🎁 *البقشيش*\n\n"
            f"💰 المبلغ: *{fmt_money(amt)}*\n"
            f"⏰ الكول داون: *{fmt_time(cd)}*")

def owner_bank_steal_text():
    succ = db.get_bank_setting("steal_success", 40)
    fine = db.get_bank_setting("steal_fine", 50)
    smin = db.get_bank_setting("steal_min", 50)
    smax = db.get_bank_setting("steal_max", 300)
    cd = db.get_bank_setting("steal_cooldown", 600)
    return (f"🔪 *السرقة*\n\n"
            f"🎯 نسبة النجاح: *{succ}%*\n"
            f"💸 الغرامة عند الفشل: *{fmt_money(fine)}*\n"
            f"💰 أقل مبلغ مسروق: *{fmt_money(smin)}*\n"
            f"💰 أكبر مبلغ مسروق: *{fmt_money(smax)}*\n"
            f"⏰ الكول داون: *{fmt_time(cd)}*")

def owner_bank_invest_text():
    pmin = db.get_bank_setting("invest_min_pct", 1)
    pmax = db.get_bank_setting("invest_max_pct", 15)
    cd = db.get_bank_setting("invest_cooldown", 3600)
    return (f"📈 *الاستثمار*\n\n"
            f"📉 أقل ربح: *{pmin}%*\n"
            f"📈 أكبر ربح: *{pmax}%*\n"
            f"⏰ الكول داون: *{fmt_time(cd)}*")

def owner_bank_luck_text():
    win = db.get_bank_setting("luck_win_pct", 45)
    cd = db.get_bank_setting("luck_cooldown", 3600)
    return (f"🎰 *الحظ*\n\n"
            f"🎯 نسبة الفوز: *{win}%*\n"
            f"⏰ الكول داون: *{fmt_time(cd)}*")

def owner_spy_text():
    words = db.count_game_content(GAME_SPY)
    s = db.get_spy_settings(0)
    return ("🕵️ *إدارة لعبة الجاسوس/بكاسة*\n\n"
            f"📝 عدد الكلمات: *{words}*\n\n"
            f"👥 الحد الأدنى: *{s['min_players']}* لاعبين\n"
            f"👥 الحد الأقصى: *{s['max_players']}* لاعبين\n"
            f"⏱ مدة النقاش: *{s['discussion_sec']//60}* دقايق\n"
            f"🗳 مدة التصويت: *{s['voting_sec']}* ثانية\n\n"
            "اختر القسم:")

def owner_spy_settings_text():
    s = db.get_spy_settings(0)
    return ("⚙️ *إعدادات لعبة الجاسوس*\n\n"
            f"👥 الحد الأدنى: *{s['min_players']}* لاعبين\n"
            f"👥 الحد الأقصى: *{s['max_players']}* لاعبين\n"
            f"⏱ مدة النقاش: *{s['discussion_sec']//60}* دقايق\n"
            f"🗳 مدة التصويت: *{s['voting_sec']}* ثانية\n\n"
            "اضغط على أي إعداد لتعديله:")

def owner_game_text(game):
    count = db.count_game_content(game)
    name = game_name(game)
    if game == GAME_QUESTIONS:
        return (f"{name}\n\nعدد الأسئلة: *{count}*\n\n"
                "لإضافة سؤال: هتكتب السؤال، وبعدين تكتب الإجابة")
    if game == GAME_ENGLISH:
        return (f"{name}\n\nعدد الكلمات: *{count}*\n\n"
                "لإضافة كلمة: هتكتب الكلمة الإنجليزية، وبعدين المعنى بالعربي")
    if game == GAME_KET:
        return (f"{name}\n\nعدد الأسئلة: *{count}*\n\n"
                "⚠️ بتضيف أسئلة بس (مفيش إجابات)\n"
                "لإضافة: اكتب سؤال أو أكتر (كل وحدة في سطر)")
    if game == GAME_SPY:
        return owner_spy_text()
    if game == GAME_PATTERN:
        return (f"{name}\n\nعدد الأنماط: *{count}*\n\n"
                "لإضافة نمط: اكتب التسلسل (فيه ❓ مكان الناقص)، وبعدين الإجابة\n"
                "مثال: `2 - 4 - 6 - ❓ - 10` ← الإجابة: `8`")
    if game == GAME_FOCUS:
        return (f"{name}\n\nعدد العناصر: *{count}*\n\n"
                "لإضافة: اكتب السؤال بالشكل ده:\n"
                "`العناصر — السؤال` ← الإجابة (رقم)\n"
                "مثال: `🍎🍌🍓🍎🍉🍎 — كام تفاحة؟` ← الإجابة: `3`")
    if game == GAME_ODD:
        return (f"{name}\n\nعدد المجموعات: *{count}*\n\n"
                "لإضافة: اكتب الكلمات مفصولة بـ ` - ` ← الكلمة المختلفة\n"
                "مثال: `تفاح - موز - سيارة - فراولة` ← الإجابة: `سيارة`")
    if game == GAME_GUESS:
        return (f"{name}\n\nعدد الكلمات: *{count}*\n\n"
                "لإضافة: اكتب الكلمة السرية، وبعدين التلميحات (كل تلميح في سطر)")
    return (f"{name}\n\nعدد العناصر: *{count}*\n\n"
            "لإضافة: اكتب كلمة أو أكتر (كل وحدة في سطر)")

def channel_prompt_text():
    return ("📢 *أرسل القناة الآن*\n\n"
            "• يوزر القناة مثل `@MyChannel`\n"
            "• أو رابطها `https://t.me/MyChannel`\n"
            "• أو توجيه رسالة منها\n\n"
            "⚠️ يجب أن يكون البوت مشرفاً في القناة.")

def ar_trigger_prompt_text():
    return ("💬 *اكتب الكلمة اللي عاوز البوت يرد عليها*\n\n"
            "مثال: `صباح الخير`\n\n"
            "⚠️ البوت هيرد بس لما الرسالة تكون *نفس الكلمة*.")

def ar_response_prompt_text(trigger):
    return (f"✅ الكلمة: *{trigger}*\n\n📝 دلوقتي ابعت *الرد* اللي عاوز البوت يقوله:")

def gban_add_prompt_text():
    return ("🚫 *إضافة كلمات محظورة*\n\n"
            "اكتب كلمة أو أكتر (كل وحدة في سطر):\n\n"
            "مثال:\nكلمة1\nكلمة2\nكلمة3")

def game_add_prompt_text(game):
    if game == GAME_QUESTIONS:
        return ("❓ *إضافة سؤال*\n\nاكتب السؤال دلوقتي:\nمثال: `عاصمة مصر إيه؟`")
    if game == GAME_ENGLISH:
        return ("🇬🇧 *إضافة كلمة إنجليزية*\n\nاكتب الكلمة الإنجليزية:\nمثال: `Book`")
    if game == GAME_KET:
        return ("💭 *إضافة سؤال كت*\n\n"
                "اكتب سؤال أو أكتر (كل سؤال في سطر):\n\n"
                "مثال:\nإيه أكتر حاجة بتخاف منها؟\nلو سافرت مكان تروح فين؟")
    if game == GAME_PATTERN:
        return ("🧩 *إضافة نمط*\n\n"
                "اكتب التسلسل وفيه ❓ مكان الناقص:\n\n"
                "مثال: `2 - 4 - 6 - ❓ - 10`")
    if game == GAME_FOCUS:
        return ("👀 *إضافة عنصر ركز*\n\n"
                "اكتب السؤال بالشكل ده:\n"
                "`العناصر — السؤال`\n\n"
                "مثال: `🍎🍌🍓🍎🍉🍎 — كام تفاحة؟`")
    if game == GAME_ODD:
        return ("🔍 *إضافة مجموعة إيه المختلف*\n\n"
                "اكتب الكلمات مفصولة بـ ` - `:\n\n"
                "مثال: `تفاح - موز - سيارة - فراولة`")
    if game == GAME_GUESS:
        return ("🎯 *إضافة كلمة خمن الكلمة*\n\n"
                "اكتب الكلمة السرية:\n\n"
                "مثال: `قلم`")
    return (f"📝 *إضافة لـ {game_name(game)}*\n\n"
            "اكتب كلمة أو أكتر (كل وحدة في سطر):\n\n"
            "مثال:\nتفاحة\nسيارة\nبحر")

def game_answer_prompt_text(content, game):
    if game == GAME_QUESTIONS:
        return (f"السؤال: *{content}*\n\nاكتب الإجابة الصحيحة:")
    if game == GAME_ENGLISH:
        return (f"الكلمة: *{content}*\n\nاكتب المعنى بالعربي:")
    if game == GAME_PATTERN:
        return (f"التسلسل: *{content}*\n\nاكتب الإجابة (الرقم أو النمط الناقص):")
    if game == GAME_FOCUS:
        return (f"السؤال: *{content}*\n\nاكتب الإجابة (رقم):")
    if game == GAME_ODD:
        return (f"المجموعة: *{content}*\n\nاكتب الكلمة المختلفة:")
    if game == GAME_GUESS:
        return (f"الكلمة: *{content}*\n\n"
                "اكتب التلميحات (كل تلميح في سطر):\n\n"
                "مثال:\n🏫 موجودة في المدرسة\n✍️ بنستخدمها في الكتابة\n🖊️ فيها حبر")
    return "اكتب الإجابة:"

def spy_add_prompt_text():
    return ("🕵️ *إضافة كلمة سرية*\n\n"
            "اكتب كلمة أو أكتر (كل وحدة في سطر):\n\n"
            "مثال:\nتفاحة\nسيارة\nبحر")

def spy_setting_prompt_text(key):
    prompts = {
        "min": "👥 اكتب الحد الأدنى لعدد اللاعبين (3-10):",
        "max": "👥 اكتب الحد الأقصى لعدد اللاعبين (3-15):",
        "disc": "⏱ اكتب مدة النقاش بالدقايق (1-10):",
        "vote": "🗳 اكتب مدة التصويت بالثواني (30-300):",
    }
    return prompts.get(key, "اكتب القيمة الجديدة:")

def games_in_group_text():
    return ("🎮 *الألعاب المتاحة*\n\n"
            "🔢 خمن الرقم\n"
            "⚡ الأسرع\n"
            "🔤 رتب الحروف\n"
            "❓ أسئلة عامة\n"
            "🇬🇧 إنجليزي\n"
            "🔢 احسب\n"
            "😀 الإيموجي\n"
            "⏱ مؤقت\n"
            "🕵️ الجاسوس\n"
            "💭 كت\n"
            "👥 المافيا\n"
            "📖 القصة المبعثرة\n"
            "🧩 أكمل النمط\n"
            "👀 ركز\n"
            "🔍 إيه المختلف\n"
            "🎯 خمن الكلمة\n"
            "🔢 ترتيب الأرقام\n\n"
            "📌 اكتب اسم اللعبة اللي عاوزها")

def games_private_text():
    return ("🎮 *الألعاب*\n\n"
            "الألعاب بتتلعب في الجروبات بس 👇\n\n"
            "🔢 خمن الرقم\n"
            "⚡ الأسرع\n"
            "🔤 رتب الحروف\n"
            "❓ أسئلة عامة\n"
            "🇬🇧 إنجليزي\n"
            "🔢 احسب\n"
            "😀 الإيموجي\n"
            "⏱ مؤقت\n"
            "🕵️ الجاسوس\n"
            "💭 كت\n"
            "👥 المافيا\n"
            "📖 القصة المبعثرة\n"
            "🧩 أكمل النمط\n"
            "👀 ركز\n"
            "🔍 إيه المختلف\n"
            "🎯 خمن الكلمة\n"
            "🔢 ترتيب الأرقام\n\n"
            "📌 عشان تلعب:\n"
            "1. اكتب *الألعاب* في الجروب\n"
            "2. اكتب اسم اللعبة")

def protect_text(antilink, banned_count):
    al = "✅ مفعّل" if antilink else "❌ معطّل"
    return ("🛡 *الحماية*\n\n"
            f"🔗 منع الروابط: {al}\n"
            f"🚫 كلمات ممنوعة: *{banned_count}*\n\n"
            "اختر:")

def schedule_text(chat_id):
    items = db.list_scheduled(chat_id)
    return ("⏰ *الرسائل المجدولة*\n\n"
            f"عدد الرسائل: *{len(items)}*\n\n"
            "البوت هيبعت الرسائل دي كل الفترة اللي إنت حددتها")

def schedule_add_text():
    return ("📝 *إضافة رسالة مجدولة*\n\n"
            "اكتب الرسالة اللي عاوز تبعت:\n\n"
            "مثال: `اذكروا الله 🌹`")

def schedule_time_text():
    return ("⏰ *كل كام دقيقة؟*\n\n"
            "اكتب رقم (بالدقايق):\n\n"
            "مثال: `60` → كل ساعة\n`30` → كل نص ساعة")

def mention_text(chat_id):
    s = db.get_periodic_mention(chat_id)
    e = "✅ مفعل" if s["enabled"] else "❌ معطل"
    msg_preview = s["message"][:50] if s["message"] else "_مفيش نص_"
    return ("🔔 *المنشن الدوري*\n\n"
            f"الحالة: *{e}*\n"
            f"⏰ كل: *{s['interval_min']}* دقيقة\n"
            f"👥 عدد المنشن: *{s['mention_count']}*\n"
            f"✍️ النص: {msg_preview}")

def mention_time_prompt():
    return ("⏰ *كل كام دقيقة؟*\n\nاكتب رقم (بالدقايق):\nمثال: `60`")

def mention_count_prompt():
    return ("👥 *كام واحد في المنشن؟*\n\nاكتب رقم (مثلاً 5):")

def mention_text_prompt():
    return ("✍️ *نص الرسالة*\n\nاكتب النص:\nأو اكتب `بدون` لو عاوز منشن بس.")

def members_list_text(chat_id, count):
    return (f"👥 *أعضاء الجروب*\n\n"
            f"العدد: *{count}*\n\n"
            "اضغط على أي عضو لعرض بياناته:")

def messages_prompt_text():
    return ("📨 *رسائل الجروب*\n\n"
            "اكتب عاوز آخر كام رسالة؟\n\n"
            "مثال: `50`")

def games_info_text(key):
    info = {
        "number": ("🔢 *خمن الرقم*\n\nالبوت يختار رقم عشوائي بين 1 و 100\nاللي يعرف يكسب +10 جنيه\n\n📌 اكتب *خمن الرقم* في الجروب للعب"),
        "calc": ("🔢 *احسب*\n\nالبوت يختار مسألة حسابية\nاللي يحسب الناتج صح يكسب +10 جنيه\n\n📌 اكتب *احسب* في الجروب"),
        "emoji": ("😀 *الإيموجي*\n\nالبوت يبعث 2 إيموجي\nاللي يكتبهم بالظبط يكسب +10 جنيه\n\n📌 اكتب *الإيموجي* في الجروب"),
        "timer": ("⏱ *مؤقت*\n\nالبوت يختار وقت عشوائي\nاللي يدوس أقرب للوقت يكسب +10 جنيه\n\n📌 اكتب *مؤقت* في الجروب"),
        "mafia": ("👥 *المافيا*\n\nأدوار سرية: 🔪 مافيا + 🔍 محقق + 👤 مواطن\nبالليل، بالنهار، تصويت\n\n📌 اكتب *مافيا* في الجروب"),
    }
    return info.get(key, "ℹ️ معلومات اللعبة")

# ==================== قائمة الأوامر (3 صفحات) ====================
def commands_page_text(page):
    if page == 0:
        return ("🎮 *الأوامر — الألعاب*\n\n"
                "اكتب اسم اللعبة عشان تبدأ:\n\n"
                "🔢 خمن الرقم\n"
                "⚡ الأسرع\n"
                "🔤 رتب الحروف\n"
                "❓ أسئلة عامة\n"
                "🇬🇧 إنجليزي\n"
                "🔢 احسب\n"
                "😀 الإيموجي\n"
                "⏱ مؤقت\n"
                "🕵️ الجاسوس/بكاسة\n"
                "💭 كت\n"
                "👥 المافيا\n"
                "📖 القصة المبعثرة\n"
                "🧩 أكمل النمط\n"
                "👀 ركز\n"
                "🔍 إيه المختلف\n"
                "🎯 خمن الكلمة\n"
                "🔢 ترتيب الأرقام")
    elif page == 1:
        return ("🏦 *الأوامر — Bank Turbo*\n\n"
                "• إنشاء حساب بنكي\n"
                "• مسح حساب بنكي\n"
                "• فلوسي — حسابي البنكي\n"
                "• راتب — بقشيش\n"
                "• تحويل [مبلغ] (بالرد)\n"
                "• سرقة (بالرد)\n"
                "• استثمار [مبلغ]\n"
                "• حظ [مبلغ]\n\n"
                "*💍 الزواج:*\n"
                "• زوجني — زواج\n"
                "• زوجي — زوجتي\n"
                "• طلاق\n"
                "• طفل (بالرد على الزوج)\n"
                "• رزق الأطفال\n\n"
                "*🏠 الممتلكات:*\n"
                "• اشتري عربية/قصر/برج/جزيرة/طيارة\n"
                "• بيع\n\n"
                "• توب الفلوس\n"
                "• توب الحرامية")
    else:
        return ("📖 *الأوامر — إضافية*\n\n"
                "*📊 معلومات:*\n"
                "• إحصائياتي — إحصائياتك\n"
                "• بياناتي — كل بياناتك\n"
                "• توب — توب 10\n"
                "• نظام النقاط — شرح النظام\n"
                "• الوقت — الساعة الحالية\n"
                "• نكتة — ضحكة سريعة\n"
                "• ذكرني بعد 5 دقايق [حاجة]\n\n"
                "*👑 VIP:*\n"
                "• قائمة VIP / المميزين\n"
                "• رفع مميز (بالرد — مالك الجروب)\n"
                "• مسح مميز (بالرد)\n"
                "• مسح المميزين\n"
                "• التوب: 3 صفحات (فلوس/حرامية/VIP)\n\n"
                "*🛡 للمشرفين:*\n"
                "• مسح [رقم] — مسح رسايل\n"
                "• /say [نص] — البوت يبعت النص\n"
                "• حظر / كتم / تحذير (بالرد)\n"
                "• id — الآيدي")

# ============ نهاية الجزء 5 ============

# ============ بداية الجزء 6 — الأوامر + Callbacks (1) ============

# ==================== أوامر /start /stats ====================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in GROUP_TYPES:
        try: await update.message.delete()
        except: pass
        return
    if update.effective_chat.type != ChatType.PRIVATE: return
    u = update.effective_user
    db.save_user(u.id, u.first_name, u.username)
    if not await require_sub(update, ctx): return
    await update.message.reply_text(main_text(u),
        parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_kb(is_owner(u.id)))

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != ChatType.PRIVATE: return
    if not is_owner(update.effective_user.id): return
    groups = db.list_groups()
    users_count = db.count_users()
    me_id = getattr(ctx.bot, "_cached_id", None)
    if not me_id:
        me = await ctx.bot.get_me()
        me_id = me.id
        try: ctx.bot._cached_id = me_id
        except: pass
    active = []
    for g in groups:
        try:
            member = await ctx.bot.get_chat_member(g["chat_id"], me.id)
            if member.status in ("administrator", "creator"):
                active.append(g)
        except Exception:
            pass
    lines = ["📊 *إحصائيات البوت*","",
             f"👥 عدد المستخدمين: *{users_count}*",
             f"🌐 المجموعات: {len(groups)}",
             f"✅ المفعّلة: *{len(active)}*",
             f"⛔ المعطّلة: *{len(groups)-len(active)}*",
             f"💬 الردود: {len(db.list_auto_replies())}",
             f"🚫 كلمات محظورة: {len(db.list_global_banned_words())}",
             f"🎮 الألعاب: 17"]
    if active:
        lines += ["","*المفعّلة:*"]
        for g in active[:30]:
            lines.append(f"• {g['title'] or g['chat_id']} — {db.count_channels(g['chat_id'])} قناة")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

# ==================== /say ====================
async def cmd_say(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in GROUP_TYPES: return
    uid = update.effective_user.id
    if not (is_owner(uid) or await is_user_admin(ctx.bot, update.effective_chat.id, uid)):
        try: await update.message.delete()
        except: pass
        return
    text = update.message.text or ""
    m = re.match(r"^/say\s+(.+)$", text, re.DOTALL)
    if not m:
        return await update.message.reply_text("⚠️ اكتب: /say نص")
    content = m.group(1).strip()
    try: await update.message.delete()
    except: pass
    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.reply_text(content)
        except: pass
    else:
        try:
            await ctx.bot.send_message(update.effective_chat.id, content)
        except: pass

# ==================== Callbacks — الرئيسية ====================
async def cb_home(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    db.clear_pending(q.from_user.id)
    await safe_edit(q, main_text(q.from_user), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu_kb(is_owner(q.from_user.id)))

async def cb_games_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await safe_edit(q, games_private_text(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=games_menu_kb())

async def cb_bank_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await safe_edit(q, bank_main_text(q.from_user), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M([[B("🔙 رجوع", callback_data="panel:home")]]))

# ==================== أوامر البنك callbacks ====================
async def cb_bank_create_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await safe_edit(q, bank_create_help_text(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M([[B("🔙 رجوع", callback_data="bank:menu")]]))

async def cb_bank_info_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await safe_edit(q, bank_info_help_text(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M([[B("🔙 رجوع", callback_data="bank:menu")]]))

async def cb_bank_money_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await safe_edit(q, bank_money_help_text(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M([[B("🔙 رجوع", callback_data="bank:menu")]]))

async def cb_bank_salary_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await safe_edit(q, bank_salary_help_text(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M([[B("🔙 رجوع", callback_data="bank:menu")]]))

async def cb_bank_tip_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await safe_edit(q, bank_tip_help_text(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M([[B("🔙 رجوع", callback_data="bank:menu")]]))

async def cb_bank_del_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    target_uid = int(parts[2])
    if q.from_user.id != target_uid:
        return await q.answer("مش زراك.", show_alert=True)
    db.delete_bank_account(q.from_user.id)
    await q.answer("🗑 تم مسح حسابك.")
    try: await q.message.edit_text("🗑 *تم مسح حسابك البنكي بنجاح.*", parse_mode=ParseMode.MARKDOWN)
    except: pass

async def cb_bank_del_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    target_uid = int(parts[2])
    if q.from_user.id != target_uid:
        return await q.answer("مش زراك.", show_alert=True)
    await q.answer("✅ تم الإلغاء.")
    try: await q.message.edit_text("✅ تم إلغاء العملية.")
    except: pass

# ==================== إحصائيات ====================
async def cb_stats_me(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    text = await build_my_stats_global_reply(q.from_user.id, q.from_user.first_name)
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu_kb(is_owner(q.from_user.id)))

async def cb_stats_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """الصفحة 1: توب الفلوس"""
    q = update.callback_query; await q.answer()
    top = db.get_top_money(10)
    kb = M([
        [B("▶️", callback_data="top:thieves"), B("🔙 رجوع", callback_data="panel:home")],
    ])
    if not top:
        return await safe_edit(q, "🏆 *توب الفلوس*\n\n📭 لا يوجد حسابات بعد.",
                              parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    lines = ["🏆 *توب الفلوس - أغنى 10*\n"]
    medals = ["🥇","🥈","🥉"]
    for i, item in enumerate(top, 1):
        display = escape_html(item['first_name'] or "عضو")
        prefix = medals[i-1] if i <= 3 else f"{i}."
        lines.append(f"{prefix} {display} — *{fmt_money(item['balance'])}*")
    lines.append("\n_1/3_")
    await safe_edit(q, "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

# ==================== قائمة الأوامر ====================
async def cb_commands(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    page = int(q.data.split(":")[2]) if len(q.data.split(":")) > 2 else 0
    await safe_edit(q, commands_page_text(page), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=commands_kb(page))

# ==================== المالك ====================
async def cb_owner_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not can_access_owner_menu(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer(); db.clear_pending(q.from_user.id)
    # نعرض بس الأزرار المسموح بيها
    is_main = is_owner(q.from_user.id)
    rows = []
    if is_main or has_perm(q.from_user.id, "subs"):
        rows.append([B("📢 اشتراكات البوت", callback_data="owner:subs")])
    if is_main or has_perm(q.from_user.id, "ar"):
        rows.append([B("💬 الردود التلقائية", callback_data="owner:ar")])
    if is_main or has_perm(q.from_user.id, "gban"):
        rows.append([B("🚫 كلمات محظورة عامة", callback_data="owner:gban")])
    if is_main or has_perm(q.from_user.id, "games"):
        rows.append([B("🏆 إدارة الألعاب", callback_data="owner:games")])
    if is_main or has_perm(q.from_user.id, "bank"):
        rows.append([B("🏦 البنك", callback_data="owner:bank")])
    if is_main or has_perm(q.from_user.id, "groups"):
        rows.append([B("🌐 كل جروبات البوت", callback_data="owner:allgroups")])
    if is_main or has_perm(q.from_user.id, "broadcast"):
        rows.append([B("📣 بث لكل الجروبات", callback_data="owner:broadcast")])
    if is_main or has_perm(q.from_user.id, "stats"):
        rows.append([B("📊 إحصائيات البوت", callback_data="owner:stats")])
    if is_main or has_perm(q.from_user.id, "devs"):
        rows.append([B("👑 المطورين", callback_data="owner:devs")])
    if is_main or has_perm(q.from_user.id, "db"):
        rows.append([B("💾 قاعدة البيانات", callback_data="owner:db")])
    rows.append([B("🔙 رجوع", callback_data="panel:home")])
    title = "👑 *إعدادات المالك*" if is_main else "👑 *إعدادات المطور*"
    await safe_edit(q, title + "\n\nاختر القسم:", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M(rows))

# ===== إدارة البنك =====
async def cb_owner_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """زر إحصائيات البوت في إعدادات المالك"""
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    groups = db.list_groups()
    users_count = db.count_users()
    me_id = getattr(ctx.bot, "_cached_id", None)
    if not me_id:
        me = await ctx.bot.get_me()
        me_id = me.id
        try: ctx.bot._cached_id = me_id
        except: pass
    active = []
    for g in groups:
        try:
            member = await ctx.bot.get_chat_member(g["chat_id"], me_id)
            if member.status in ("administrator", "creator"):
                active.append(g)
        except Exception:
            pass
    lines = ["📊 *إحصائيات البوت*", "",
             f"👥 عدد المستخدمين: *{users_count}*",
             f"🌐 المجموعات: {len(groups)}",
             f"✅ المفعّلة: *{len(active)}*",
             f"⛔ المعطّلة: *{len(groups)-len(active)}*",
             f"💬 الردود: {len(db.list_auto_replies())}",
             f"🚫 كلمات محظورة: {len(db.list_global_banned_words())}",
             f"🎮 الألعاب: 17"]
    if active:
        lines += ["", "المفعّلة:"]
        for g in active[:30]:
            t = (g['title'] or str(g['chat_id'])).replace('*','').replace('_','').replace('`','').replace('[','').replace(']','')
            lines.append(f"• {t} — {db.count_channels(g['chat_id'])} قناة")
    await safe_edit(q, "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M([[B("🔙 رجوع", callback_data="owner:menu")]]))

# ===== إدارة المطورين =====

async def cb_owner_devs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """زر المطورين في إعدادات المالك"""
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    # نجيب المطورين
    try:
        devs = db.list_developers()
    except:
        devs = []
    # نبني النص بدون Markdown
    text = "👑 إدارة المطورين\n\n"
    text += f"👤 المالك: {OWNER_ID}\n"
    if not devs:
        text += "\n📭 لا يوجد مطورين مضافين."
    else:
        text += f"\n👥 المطورين ({len(devs)}):\n"
        for d in devs:
            uname = f"@{d['username']}" if d.get('username') else "—"
            fname = d['first_name'] or 'بدون'
            text += f"• {fname} | {d['user_id']} | {uname}\n"
    kb = M([
        [B("➕ إضافة مطور", callback_data="devs:add")],
        [B("⚙️ صلاحيات المطورين", callback_data="devs:perms_list")],
        [B("🗑 حذف مطور", callback_data="devs:del_list")],
        [B("🔙 رجوع", callback_data="owner:menu")],
    ])
    await safe_edit(q, text, reply_markup=kb)

async def cb_devs_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_DEVS_ADD, extra="devs_add")
    await safe_edit(q,
        "➕ *إضافة مطور*\n\n"
        "ابعت:\n"
        "• الآيدي (ID)\n"
        "• أو اعمل رد على رسالة المطور واكتب `add`\n\n"
        "⚠️ المطور هيقدر يشوف إعدادات المالك",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=M([[B("🔙 رجوع", callback_data="owner:devs")]]))

async def cb_devs_perms_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """عرض المطورين كأزرار لاختيار أحدهم وتعديل صلاحياته"""
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    try:
        devs = db.list_developers()
    except:
        devs = []
    if not devs:
        try:
            await q.edit_message_text(
                "⚙️ صلاحيات المطورين\n\n📭 لا يوجد مطورين مضافين.",
                reply_markup=M([[B("🔙 رجوع", callback_data="owner:devs")]]))
        except: pass
        return
    rows = []
    for d in devs:
        name = (d.get('first_name') or str(d['user_id']))[:25]
        rows.append([B(f"👤 {name}", callback_data=f"devs:perms:{d['user_id']}")])
    rows.append([B("🔙 رجوع", callback_data="owner:devs")])
    try:
        await q.edit_message_text(
            "⚙️ صلاحيات المطورين\n\nاختر مطور لعرض/تعديل صلاحياته:",
            reply_markup=M(rows))
    except Exception as e:
        log.warning(f"cb_devs_perms_list error: {e}")

async def cb_devs_perms(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """عرض صلاحيات مطور"""
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    try:
        target = int(q.data.split(":")[2])
    except (IndexError, ValueError):
        return await q.answer("⚠️ خطأ", show_alert=True)
    devs = db.list_developers()
    dev = next((d for d in devs if d["user_id"] == target), None)
    if not dev:
        return await q.answer("❌ المطور مش موجود.", show_alert=True)
    perms = db.get_all_dev_perms(target)
    fname = dev.get("first_name") or str(target)
    text = (f"⚙️ صلاحيات المطور\n\n"
            f"👤 {fname}\n"
            f"🆔 {target}\n\n"
            "اضغط على أي صلاحية لتفعيلها/تعطيلها:")
    rows = []
    for key, label in db.DEV_PERMS:
        status = "✅" if perms.get(key) else "❌"
        rows.append([B(f"{status} {label}", callback_data=f"devs:perm:{target}:{key}")])
    rows.append([B("🔙 رجوع", callback_data="owner:devs")])
    await safe_edit(q, text, reply_markup=M(rows))


async def cb_dev_perm_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """تبديل صلاحية: devs:perm:TARGET:KEY"""
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    parts = q.data.split(":")
    if len(parts) < 4:
        return await q.answer("⚠️ خطأ في البيانات", show_alert=True)
    try:
        target = int(parts[2])
        key = parts[3]
    except (IndexError, ValueError):
        return await q.answer("⚠️ خطأ", show_alert=True)
    new_val = db.toggle_dev_permission(target, key)
    await q.answer("✅ تم التفعيل" if new_val else "❌ تم التعطيل")
    # نعرض القائمة محدّثة
    try:
        devs = db.list_developers()
        dev = next((d for d in devs if d["user_id"] == target), None)
        if not dev:
            return
        perms = db.get_all_dev_perms(target)
        fname = dev.get("first_name") or str(target)
        text = (f"⚙️ صلاحيات المطور\n\n"
                f"👤 {fname}\n"
                f"🆔 {target}\n\n"
                "اضغط على أي صلاحية لتفعيلها/تعطيلها:")
        rows = []
        for k, label in db.DEV_PERMS:
            status = "✅" if perms.get(k) else "❌"
            rows.append([B(f"{status} {label}", callback_data=f"devs:perm:{target}:{k}")])
        rows.append([B("🔙 رجوع", callback_data="owner:devs")])
        await q.edit_message_text(text, reply_markup=M(rows))
    except Exception as e:
        try: await q.message.reply_text(f"⚠️ {e}")
        except: pass

async def cb_devs_del_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    try:
        devs = db.list_developers()
    except:
        devs = []
    if not devs:
        return await q.answer("📭 لا يوجد مطورين.", show_alert=True)
    rows = []
    for d in devs:
        name = (d.get('first_name') or str(d['user_id']))[:25]
        rows.append([B(f"⚙️ {name}", callback_data=f"devs:perms:{d['user_id']}")])
        rows.append([B(f"🗑 حذف {name}", callback_data=f"devs:del:{d['user_id']}")])
    rows.append([B("🔙 رجوع", callback_data="owner:devs")])
    await safe_edit(q, "📋 *المطورين*\n\nاضغط على مطور لتعديل صلاحياته:\nأو احذفه:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M(rows))

async def cb_devs_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    try:
        target = int(q.data.split(":")[2])
    except (IndexError, ValueError):
        return await q.answer("⚠️ خطأ", show_alert=True)
    try:
        db.remove_developer(target)
        await q.answer("✅ تم الحذف")
    except:
        await q.answer("❌ فشل", show_alert=True)
    # نعيد عرض القائمة
    try:
        devs = db.list_developers()
    except:
        devs = []
    if not devs:
        try:
            await q.edit_message_text("📭 لا يوجد مطورين.",
                                      reply_markup=M([[B("🔙 رجوع", callback_data="owner:devs")]]))
        except: pass
        return
    rows = []
    for d in devs:
        name = (d.get('first_name') or str(d['user_id']))[:25]
        rows.append([B(f"🗑 {name}", callback_data=f"devs:del:{d['user_id']}")])
    rows.append([B("🔙 رجوع", callback_data="owner:devs")])
    try:
        await q.edit_message_text("🗑 *اختر مطور للحذف:*", parse_mode=ParseMode.MARKDOWN, reply_markup=M(rows))
    except: pass

async def cb_owner_bank(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer(); db.clear_pending(q.from_user.id)
    await safe_edit(q, owner_bank_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_bank_kb())

async def cb_obank_marriage(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    await safe_edit(q, owner_bank_marriage_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=obank_marriage_kb())


async def cb_obank_children(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    await safe_edit(q, owner_bank_children_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=obank_children_kb())


async def cb_obank_props(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    await safe_edit(q, owner_bank_props_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=obank_props_kb())

async def cb_obank_salary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    await safe_edit(q, owner_bank_salary_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=obank_salary_kb())

async def cb_obank_tip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    await safe_edit(q, owner_bank_tip_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=obank_tip_kb())

async def cb_obank_steal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    await safe_edit(q, owner_bank_steal_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=obank_steal_kb())

async def cb_obank_invest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    await safe_edit(q, owner_bank_invest_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=obank_invest_kb())

async def cb_obank_luck(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    await safe_edit(q, owner_bank_luck_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=obank_luck_kb())

async def cb_obank_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    key = q.data.split(":")[2]
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_BANK_SETTING, extra=key)
    prompts = {
        "salary_amount": "💰 اكتب مبلغ الراتب:",
        "salary_cooldown": "⏰ اكتب كول داون الراتب بالثواني:",
        "tip_amount": "💰 اكتب مبلغ البقشيش:",
        "tip_cooldown": "⏰ اكتب كول داون البقشيش بالثواني:",
        "steal_success": "🎯 اكتب نسبة نجاح السرقة (0-100):",
        "steal_fine": "💸 اكتب الغرامة عند الفشل:",
        "steal_min": "🔽 اكتب أقل مبلغ مسروق:",
        "steal_max": "🔼 اكتب أكبر مبلغ مسروق:",
        "steal_cooldown": "⏰ اكتب كول داون السرقة بالثواني:",
        "invest_min_pct": "📉 اكتب أقل نسبة ربح (0-100):",
        "invest_max_pct": "📈 اكتب أكبر نسبة ربح (0-100):",
        "invest_cooldown": "⏰ اكتب كول داون الاستثمار بالثواني:",
        "luck_win_pct": "🎯 اكتب نسبة الفوز (0-100):",
        "luck_cooldown": "⏰ اكتب كول داون الحظ بالثواني:",
        "marriage_cost": "💰 اكتب تكلفة الزواج:",
        "divorce_refund": "💸 اكتب استرداد الطلاق:",
        "child_cost": "💰 اكتب تكلفة الطفل:",
        "child_income": "💵 اكتب ربح الطفل/ساعة:",
        "max_children": "👥 اكتب أقصى عدد أطفال:",
        "child_cooldown": "⏰ اكتب كول داون الطفل (ثواني):",
        "prop_cost": "💰 اكتب تكلفة الممتلك:",
        "prop_sell_min": "📉 اكتب أقل نسبة ربح (0-100):",
        "prop_sell_max": "📈 اكتب أكبر نسبة ربح (0-100):",
        "prop_cooldown": "⏰ اكتب كول داون الممتلكات (ثواني):",
    }
    await safe_edit(q, prompts.get(key, "✍️ اكتب القيمة الجديدة:"),
                    parse_mode=ParseMode.MARKDOWN, reply_markup=cancel_kb(PENDING_BANK_SETTING))

# ===== كلمات محظورة عامة =====
async def cb_owner_gban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer(); db.clear_pending(q.from_user.id)
    await safe_edit(q, owner_gban_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_gban_kb())

async def cb_gban_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_GLOBAL_BANNED)
    await safe_edit(q, gban_add_prompt_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=cancel_kb(PENDING_GLOBAL_BANNED))

async def cb_gban_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    items = db.list_global_banned_words()
    if not items:
        return await safe_edit(q, "🚫 لا توجد كلمات محظورة بعد.", reply_markup=owner_gban_kb())
    lines = [f"🚫 *الكلمات المحظورة عالمياً* — {len(items)}\n"]
    for it in items[:200]:
        lines.append(f"• {it['word']}")
    text = "\n".join(lines)
    if len(text) > 4000: text = text[:4000] + "\n... (طويلة)"
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN, reply_markup=owner_gban_kb())

async def cb_gban_del_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    items = db.list_global_banned_words()
    if not items:
        return await safe_edit(q, "🚫 لا توجد كلمات.", reply_markup=owner_gban_kb())
    await safe_edit(q, "🗑 *اضغط على الكلمة لحذفها:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=owner_gban_delete_kb(items))

async def cb_gban_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    item_id = int(q.data.split(":")[2])
    db.remove_global_banned_word(item_id)
    await q.answer("🗑 تم الحذف.")
    items = db.list_global_banned_words()
    if not items:
        return await safe_edit(q, "🚫 لا توجد كلمات.", reply_markup=owner_gban_kb())
    await safe_edit(q, "🗑 *اضغط على الكلمة لحذفها:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=owner_gban_delete_kb(items))

# ===== قاعدة البيانات =====
async def cb_owner_db(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    await safe_edit(q, owner_db_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_db_kb())

async def cb_owner_db_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer("📤 جاري الإرسال...")
    try:
        with open(db.DB_PATH, "rb") as f:
            await ctx.bot.send_document(q.from_user.id, f, filename="data.db",
                caption="💾 *نسخة احتياطية من قاعدة البيانات*")
    except Exception as e:
        await ctx.bot.send_message(q.from_user.id, f"❌ فشل الإرسال: {e}")

async def cb_owner_db_import(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_BROADCAST, extra="import_db")
    await safe_edit(q, "📥 *استعادة قاعدة البيانات*\n\nابعت ملف `data.db`:\n\n⚠️ البيانات هتتمسح!",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=cancel_kb(PENDING_BROADCAST))

# ===== اشتراكات البوت =====
async def cb_owner_subs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer(); db.clear_pending(q.from_user.id)
    await safe_edit(q, owner_subs_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_subs_kb())

async def cb_owner_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer(); db.set_pending(q.from_user.id, PENDING_DEFAULT)
    await safe_edit(q, channel_prompt_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=cancel_kb(PENDING_DEFAULT))

async def cb_owner_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    chans = db.list_default_channels()
    if not chans:
        return await safe_edit(q, "📋 لا توجد قنوات افتراضية.", reply_markup=owner_subs_kb())
    text = "📋 *القنوات الافتراضية*\n\n" + "\n".join(f"• {c['title'] or c['username'] or c['channel_id']}" for c in chans)
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN, reply_markup=default_channels_kb(chans))

async def cb_owner_del_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    chans = db.list_default_channels()
    if not chans:
        return await safe_edit(q, "📋 لا توجد قنوات لحذفها.", reply_markup=owner_subs_kb())
    await safe_edit(q, "🗑 *اضغط على قناة لحذفها:*", parse_mode=ParseMode.MARKDOWN, reply_markup=default_channels_kb(chans))

async def cb_owner_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    chid = int(q.data.split(":")[2])
    db.remove_default_channel(chid)
    await q.answer("🗑 تم الحذف.")
    chans = db.list_default_channels()
    if not chans:
        return await safe_edit(q, "📋 لا توجد قنوات.", reply_markup=owner_subs_kb())
    await safe_edit(q, "🗑 *اضغط على قناة لحذفها:*", parse_mode=ParseMode.MARKDOWN, reply_markup=default_channels_kb(chans))

async def cb_owner_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); db.clear_pending(q.from_user.id)
    await safe_edit(q, owner_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_menu_kb())

# ===== كل جروبات البوت =====
async def cb_owner_allgroups(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    me = await ctx.bot.get_me()
    all_groups = db.list_groups()
    groups = []
    for g in all_groups:
        try:
            bot_m = await ctx.bot.get_chat_member(g["chat_id"], me.id)
            if bot_m.status in ("administrator", "creator"):
                groups.append(g)
            else:
                # البوت مش أدمن — نشيله من الداتابيز
                db.deactivate_group(g["chat_id"])
        except Exception:
            # الجروب مش موجود — نشيله
            try: db.forget_group(g["chat_id"])
            except: pass
    if not groups:
        return await safe_edit(q, "🌐 لا توجد جروبات البوت أدمن فيها.", reply_markup=owner_menu_kb())
    text = f"🌐 *كل جروبات البوت* ({len(groups)})\n\nاضغط على جروب لفتحه:"
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN, reply_markup=all_groups_kb(groups))

async def cb_owner_goto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    g = db.get_group(cid)
    if not g:
        return await q.answer("❌ الجروب مش موجود.", show_alert=True)
    text = (f"🌐 *{g['title'] or cid}*\n\n"
            f"🆔 `{cid}`\n"
            f"الحالة: {'✅ مفعل' if g['activated'] else '⛔ معطل'}\n"
            f"القنوات: {db.count_channels(cid)}")
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=group_data_kb(cid))

async def cb_owner_open(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split(":")[2])
    link = await get_group_link(ctx.bot, cid)
    if not link:
        return await q.answer("⚠️ مفيش لينك متاح — ارفع البوت مشرف", show_alert=True)
    await q.answer()
    await ctx.bot.send_message(q.from_user.id, f"📂 [اضغط هنا لفتح الجروب]({link})",
        parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=False)

async def cb_owner_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    await q.edit_message_text("📊 *بيانات الجروب*\n\nاختر:",
        parse_mode=ParseMode.MARKDOWN, reply_markup=group_data_sub_kb(cid))

# ===== البث =====
async def cb_owner_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_BROADCAST, extra="broadcast")
    await safe_edit(q, "📣 *بث لكل الجروبات*\n\nابعت الرسالة اللي عاوز تبثها:",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=cancel_kb(PENDING_BROADCAST))

# ===== الردود التلقائية =====
async def cb_owner_ar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer(); db.clear_pending(q.from_user.id)
    await safe_edit(q, owner_ar_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_ar_kb())

async def cb_ar_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_ADD_TRIGGER)
    await safe_edit(q, ar_trigger_prompt_text(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=cancel_kb(PENDING_ADD_TRIGGER))

async def cb_ar_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    replies = db.list_auto_replies()
    if not replies:
        return await safe_edit(q, "📋 لا توجد ردود تلقائية بعد.", reply_markup=owner_ar_kb())
    lines = ["📋 *الردود التلقائية*\n"]
    for r in replies:
        lines.append(f"• *{r['trigger']}* → {r['response']}")
    text = "\n".join(lines)
    if len(text) > 4000: text = text[:4000] + "\n\n... (طويلة)"
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN, reply_markup=owner_ar_kb())

async def cb_ar_del_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    replies = db.list_auto_replies()
    if not replies:
        return await safe_edit(q, "📋 لا توجد ردود.", reply_markup=owner_ar_kb())
    await safe_edit(q, "🗑 *اضغط على الرد لحذفه:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=ar_delete_kb(replies))

async def cb_ar_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    rid = int(q.data.split(":")[2])
    db.remove_auto_reply(rid)
    await q.answer("🗑 تم الحذف.")
    replies = db.list_auto_replies()
    if not replies:
        return await safe_edit(q, "📋 لا توجد ردود.", reply_markup=owner_ar_kb())
    await safe_edit(q, "🗑 *اضغط على الرد لحذفه:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=ar_delete_kb(replies))

# ============ نهاية الجزء 6 ============

# ============ بداية الجزء 7 — إدارة الألعاب ============

# ===== إدارة الألعاب =====
async def cb_owner_jokes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer(); db.clear_pending(q.from_user.id)
    await safe_edit(q, owner_jokes_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_jokes_kb())


async def cb_jokes_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_BROADCAST, extra="jokes_add")
    await safe_edit(q,
        "➕ *إضافة نكتة*\n\n"
        "ابعت النكتة (أو أكتر، كل واحدة في سطر):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=M([[B("🔙 رجوع", callback_data="owner:jokes")]]))


async def cb_jokes_del_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    jokes = db.list_jokes()
    if not jokes:
        return await q.answer("📭 مفيش نكت.", show_alert=True)
    await safe_edit(q, "🗑 *اختر نكتة للحذف:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=owner_jokes_delete_kb(jokes))


async def cb_jokes_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    try:
        jid = int(q.data.split(":")[2])
    except:
        return await q.answer("⚠️ خطأ", show_alert=True)
    if db.remove_joke(jid):
        await q.answer("✅ تم الحذف")
    else:
        await q.answer("❌ فشل", show_alert=True)
    jokes = db.list_jokes()
    if not jokes:
        await safe_edit(q, owner_jokes_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_jokes_kb())
        return
    await safe_edit(q, "🗑 *اختر نكتة للحذف:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=owner_jokes_delete_kb(jokes))


async def cb_jokes_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    jokes = db.list_jokes()
    if not jokes:
        return await safe_edit(q, "📭 مفيش نكت.", reply_markup=owner_jokes_kb())
    lines = [f"📋 *النكت* ({len(jokes)})\n"]
    for i, j in enumerate(jokes[:50], 1):
        lines.append(f"{i}. {j['text']}")
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n..."
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN, reply_markup=owner_jokes_kb())


async def cb_jokes_cooldown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_BANK_SETTING, extra="joke_cooldown")
    await safe_edit(q, "⏱ اكتب كول داون النكتة بالثواني:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M([[B("🔙 رجوع", callback_data="owner:jokes")]]))


# ============ التذكيرات ============
async def cb_owner_reminders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer(); db.clear_pending(q.from_user.id)
    await safe_edit(q, owner_reminders_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_reminders_kb())


async def cb_reminders_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_BANK_SETTING, extra="reminder_max")
    await safe_edit(q, "⏰ اكتب أقصى وقت للتذكير بالثواني:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M([[B("🔙 رجوع", callback_data="owner:reminders")]]))

async def cb_owner_games(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer(); db.clear_pending(q.from_user.id)
    await safe_edit(q, owner_games_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_games_kb())

async def cb_og_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    # نقبل الشكلين:
    # og:fastest       → game = "fastest" (split[1])
    # og:menu:fastest  → game = "fastest" (split[2])
    parts = q.data.split(":")
    if len(parts) >= 3:
        game = parts[2]
    elif len(parts) == 2:
        game = parts[1]
    else:
        return
    await safe_edit(q, owner_game_text(game), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_game_kb(game))

async def cb_og_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    key = q.data.split(":")[2]
    await safe_edit(q, games_info_text(key), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=M([[B("🔙 رجوع", callback_data="owner:games")]]))

async def cb_og_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer("⏳ جاري التحضير...")
    try:
        game = q.data.split(":")[2]
    except IndexError:
        return
    if game in (GAME_QUESTIONS, GAME_ENGLISH, GAME_PATTERN, GAME_FOCUS, GAME_ODD, GAME_GUESS):
        db.set_pending(q.from_user.id, PENDING_ADD_GAME_WORD, extra=f"q:{game}")
    else:
        db.set_pending(q.from_user.id, PENDING_ADD_GAME_WORD, extra=game)
    await safe_edit(q, game_add_prompt_text(game), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=cancel_kb(PENDING_ADD_GAME_WORD))

async def cb_og_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    try:
        game = q.data.split(":")[2]
    except IndexError:
        await q.answer("⚠️ خطأ")
        return
    items = db.list_game_content(game)
    kb = owner_game_kb(game)
    if not items:
        try:
            await q.edit_message_text("📋 لا توجد عناصر بعد.", reply_markup=kb)
        except Exception:
            await q.message.reply_text("📋 لا توجد عناصر بعد.", reply_markup=kb)
        return
    lines = [f"📋 *{game_name(game)}* — العدد: {len(items)}\n"]
    for it in items[:200]:
        if game in (GAME_QUESTIONS, GAME_ENGLISH, GAME_PATTERN, GAME_FOCUS, GAME_ODD, GAME_GUESS):
            ans = (it["answer"] or "").replace("\n", " | ")[:30]
            lines.append(f"• {it['content']} ← {ans}")
        else:
            lines.append(f"• {it['content']}")
    text = "\n".join(lines)
    if len(text) > 4000: text = text[:4000] + "\n... (طويلة)"
    try:
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception as e:
        try:
            await q.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception as e2:
            log.warning(f"cb_og_show error: {e2}")

async def cb_og_del_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    try:
        game = q.data.split(":")[2]
    except IndexError:
        await q.answer("⚠️ خطأ")
        return
    items = db.list_game_content(game)
    kb = owner_game_kb(game)
    if not items:
        try:
            await q.edit_message_text("📋 لا توجد عناصر.", reply_markup=kb)
        except Exception:
            await q.message.reply_text("📋 لا توجد عناصر.", reply_markup=kb)
        return
    text = "🗑 *اضغط على العنصر لحذفه:*"
    del_kb = owner_game_delete_kb(game, items)
    try:
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=del_kb)
    except Exception as e:
        try:
            await q.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=del_kb)
        except Exception as e2:
            log.warning(f"cb_og_del_list error: {e2}")

async def cb_og_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    parts = q.data.split(":")
    item_id = int(parts[2])
    game = parts[3] if len(parts) > 3 else None
    db.remove_game_content(item_id)
    await q.answer("🗑 تم الحذف.")
    items = db.list_game_content(game) if game else []
    if not items:
        return await safe_edit(q, "📋 لا توجد عناصر.", reply_markup=owner_game_kb(game))
    await safe_edit(q, "🗑 *اضغط على العنصر لحذفه:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=owner_game_delete_kb(game, items))

# ===== إدارة الجاسوس =====
async def cb_og_spy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer(); db.clear_pending(q.from_user.id)
    await safe_edit(q, owner_spy_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_spy_kb())

async def cb_spy_add_word(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_SPY_WORD)
    await safe_edit(q, spy_add_prompt_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=cancel_kb(PENDING_SPY_WORD))

async def cb_spy_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    items = db.list_game_content(GAME_SPY)
    if not items:
        return await safe_edit(q, "📋 لا توجد كلمات بعد.", reply_markup=owner_spy_kb())
    lines = [f"📋 *كلمات الجاسوس* — العدد: {len(items)}\n"]
    for it in items[:200]:
        lines.append(f"• {it['content']}")
    text = "\n".join(lines)
    if len(text) > 4000: text = text[:4000] + "\n... (طويلة)"
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN, reply_markup=owner_spy_kb())

async def cb_spy_del_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    items = db.list_game_content(GAME_SPY)
    if not items:
        return await safe_edit(q, "📋 لا توجد كلمات.", reply_markup=owner_spy_kb())
    await safe_edit(q, "🗑 *اضغط على الكلمة لحذفها:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=owner_spy_delete_kb(items))

async def cb_spy_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    item_id = int(q.data.split(":")[2])
    db.remove_game_content(item_id)
    await q.answer("🗑 تم الحذف.")
    items = db.list_game_content(GAME_SPY)
    if not items:
        return await safe_edit(q, "📋 لا توجد كلمات.", reply_markup=owner_spy_kb())
    await safe_edit(q, "🗑 *اضغط على الكلمة لحذفها:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=owner_spy_delete_kb(items))

async def cb_spy_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    await q.answer()
    await safe_edit(q, owner_spy_settings_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=owner_spy_settings_kb())

async def cb_spy_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id): return await q.answer("⛔ للمالك فقط.", show_alert=True)
    key = q.data.split(":")[2]
    await q.answer()
    db.set_pending(q.from_user.id, PENDING_SPY_SETTING, extra=key)
    await safe_edit(q, spy_setting_prompt_text(key), parse_mode=ParseMode.MARKDOWN, reply_markup=cancel_kb(PENDING_SPY_SETTING))

# ===== Callbacks المافيا/الجاسوس/القصة =====
async def cb_spy_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split(":")[2])
    result = await spy_join(ctx.bot, cid, q.from_user)
    if result == "ok":
        await q.answer("✅ تم تسجيلك!")
    elif result == "already":
        await q.answer("✅ أنت داخل اللعبة بالفعل!", show_alert=False)
    elif result == "full":
        await q.answer("⚠️ اللعبة امتلت.", show_alert=True)
    elif result == "no_pm":
        await q.answer("⚠️ لازم تفتح البوت في الخاص وتدوس /start الأول!", show_alert=True)
    elif result == "not_active":
        await q.answer("⚠️ اللعبة مش شغالة.", show_alert=True)

async def cb_spy_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split(":")[2])
    g = spy_games.get(cid)
    if not g or g["state"] != "lobby":
        return await q.answer("اللعبة مش شغالة.", show_alert=True)
    settings = db.get_spy_settings(cid)
    if len(g["players"]) < settings["min_players"]:
        return await q.answer(f"⚠️ محتاجين {settings['min_players']} لاعبين على الأقل.", show_alert=True)
    await q.answer("🚀 جاري بدء اللعبة...")
    await spy_begin_game(ctx.bot, cid)

async def cb_spy_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split(":")[2])
    await q.answer("❌ تم الإلغاء.")
    await spy_cancel(ctx.bot, cid)

async def cb_spy_vote(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    cid = int(parts[2])
    voted_id = int(parts[3])
    g = spy_games.get(cid)
    if not g or g["state"] != "voting":
        return await q.answer("التصويت مش شغال.", show_alert=True)
    if q.from_user.id not in g["players"]:
        return await q.answer("إنت مش في اللعبة.", show_alert=True)
    if q.from_user.id == voted_id:
        return await q.answer("مش هينفع تصوت لنفسك!", show_alert=True)
    if q.from_user.id in g["votes"]:
        return await q.answer("إنت صوتت بالفعل!", show_alert=True)
    g["votes"][q.from_user.id] = voted_id
    await q.answer("✅ تم التصويت")
    if len(g["votes"]) >= len(g["players"]):
        await spy_end_game(ctx.bot, cid)

async def cb_story_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split(":")[2])
    result = await story_join(ctx.bot, cid, q.from_user)
    if result == "ok": await q.answer("✅ تم تسجيلك!")
    elif result == "already": await q.answer("✅ أنت داخل اللعبة بالفعل!", show_alert=False)
    elif result == "full": await q.answer("⚠️ اللعبة امتلت.", show_alert=True)
    elif result == "no_pm": await q.answer("⚠️ لازم تفتح البوت في الخاص وتدوس /start الأول!", show_alert=True)
    elif result == "not_active": await q.answer("⚠️ اللعبة مش شغالة.", show_alert=True)

async def cb_story_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split(":")[2])
    g = story_games.get(cid)
    if not g or g["state"] != "lobby":
        return await q.answer("اللعبة مش شغالة.", show_alert=True)
    if len(g["players"]) < 3:
        return await q.answer("⚠️ محتاجين 3 لاعبين على الأقل.", show_alert=True)
    await q.answer("🚀 جاري بدء اللعبة...")
    await story_begin_game(ctx.bot, cid)

async def cb_story_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split(":")[2])
    await q.answer("❌ تم الإلغاء.")
    await story_cancel(ctx.bot, cid)

async def cb_story_vote(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    cid = int(parts[2])
    voted_id = int(parts[3])
    g = story_games.get(cid)
    if not g or g["state"] != "voting":
        return await q.answer("التصويت مش شغال.", show_alert=True)
    if q.from_user.id not in g["players"]:
        return await q.answer("إنت مش في اللعبة.", show_alert=True)
    if q.from_user.id == voted_id:
        return await q.answer("مش هينفع تصوت لنفسك!", show_alert=True)
    g["votes"][q.from_user.id] = voted_id
    await q.answer("✅ تم التصويت")

async def cb_mafia_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split(":")[2])
    result = await mafia_join(ctx.bot, cid, q.from_user)
    if result == "ok": await q.answer("✅ تم تسجيلك!")
    elif result == "already": await q.answer("✅ أنت داخل اللعبة بالفعل!", show_alert=False)
    elif result == "full": await q.answer("⚠️ اللعبة امتلت.", show_alert=True)
    elif result == "no_pm": await q.answer("⚠️ لازم تفتح البوت في الخاص وتدوس /start الأول!", show_alert=True)
    elif result == "not_active": await q.answer("⚠️ اللعبة مش شغالة.", show_alert=True)

async def cb_mafia_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split(":")[2])
    g = mafia_games.get(cid)
    if not g or g["state"] != "lobby":
        return await q.answer("اللعبة مش شغالة.", show_alert=True)
    settings = db.get_mafia_settings(cid)
    if len(g["players"]) < settings["min_players"]:
        return await q.answer(f"⚠️ محتاجين {settings['min_players']} لاعبين على الأقل.", show_alert=True)
    await q.answer("🚀 جاري بدء اللعبة...")
    await mafia_begin_game(ctx.bot, cid)

async def cb_mafia_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    cid = int(q.data.split(":")[2])
    await q.answer("❌ تم الإلغاء.")
    await mafia_cancel(ctx.bot, cid)

async def cb_mafia_kill(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    cid = int(parts[2])
    target = int(parts[3])
    await q.answer("🔪 تم الاختيار")
    await mafia_action(ctx.bot, cid, q.from_user.id, "kill", target)

async def cb_mafia_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    cid = int(parts[2])
    target = int(parts[3])
    await q.answer("🔍 تم الفحص")
    await mafia_action(ctx.bot, cid, q.from_user.id, "check", target)

async def cb_mafia_vote(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    cid = int(parts[2])
    voted_id = int(parts[3])
    g = mafia_games.get(cid)
    if not g or g["state"] != "vote":
        return await q.answer("التصويت مش شغال.", show_alert=True)
    if q.from_user.id not in g["alive"]:
        return await q.answer("إنت مش من الأحياء.", show_alert=True)
    if q.from_user.id == voted_id:
        return await q.answer("مش هينفع تصوت لنفسك!", show_alert=True)
    if q.from_user.id in g["votes"]:
        return await q.answer("إنت صوتت بالفعل!", show_alert=True)
    g["votes"][q.from_user.id] = voted_id
    await q.answer("✅ تم التصويت")
    if len(g["votes"]) >= len(g["alive"]):
        await mafia_end_vote(ctx.bot, cid)

# ===== Timer + Guess hint =====
async def cb_timer_click(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    cid = int(parts[2])
    uid = q.from_user.id
    game = timer_games.get(cid)
    if not game or game.get("finished"):
        return await q.answer("⏱ انتهى المؤقت!", show_alert=True)
    if uid in game["clicks"]:
        return await q.answer("✅ أنت سجلت بالفعل!", show_alert=True)
    click_ms = (time.time() - game["start_time"]) * 1000
    game["clicks"][uid] = (q.from_user.first_name, click_ms)
    await q.answer(f"✅ تم التسجيل! ({click_ms/1000:.2f}ث)")

async def cb_guess_hint(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    cid = int(parts[2])
    game = active_games.get(cid)
    if not game or game.get("type") != "guess":
        return await q.answer("اللعبة مش شغالة.", show_alert=True)
    game["current_hint"] = min(game["current_hint"] + 1, len(game["hints"]) - 1)
    hint = game["hints"][game["current_hint"]]
    try:
        kb = M([[B("💡 تلميح", callback_data=f"guess:hint:{cid}")]])
        await q.edit_message_text(
            f"🎯 *خمن الكلمة*\n\n💡 {hint}\n\nاكتب الكلمة 👇\n⏱ عندك 60 ثانية",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except: pass
    await q.answer("💡 تلميح جديد!")

# ============ نهاية الجزء 7 ============



# ============ بداية الجزء 8 — إدارة الجروبات ============

# ===== رسائل لوحة المجموعة =====
def group_panel_text(group, ch_count):
    status = "✅ مفعل" if group["activated"] else "⛔ معطل"
    return (f"⚙️ *لوحة تحكم المجموعة*\n\n"
            f"📌 الاسم: {escape_html(group['title'] or 'بدون اسم')}\n"
            f"🆔 `{group['chat_id']}`\n"
            f"الحالة: {status}\n"
            f"📢 القنوات: *{ch_count}*\n\n"
            "اختر من الأزرار:")

def protect_full_text(chat_id):
    al = db.get_antilink(chat_id)
    bw = db.list_banned_words(chat_id)
    sched = db.list_scheduled(chat_id)
    mention = db.get_periodic_mention(chat_id)
    g = db.get_group(chat_id)
    wl = g.get("welcome_enabled", True) if g else True
    al_str = "✅ مفعّل" if al else "❌ معطّل"
    wl_str = "✅ مفعّل" if wl else "❌ معطّل"
    sch_str = "✅ مفعّل" if sched else "❌ معطّل"
    men_str = "✅ مفعّل" if mention["enabled"] else "❌ معطّل"
    return ("🛡 *الحماية*\n\n"
            f"🔗 منع الروابط: {al_str}\n"
            f"👋 الترحيب: {wl_str}\n"
            f"🚫 كلمات ممنوعة: *{len(bw)}*\n"
            f"⏰ رسائل مجدولة: {sch_str} ({len(sched)})\n"
            f"🔔 منشن دوري: {men_str}\n\n"
            "اختر:")

def schedule_show_text(chat_id):
    items = db.list_scheduled(chat_id)
    if not items:
        return "⏰ *الرسائل المجدولة*\n\n📭 لا توجد رسائل مجدولة."
    lines = [f"⏰ *الرسائل المجدولة* ({len(items)})\n"]
    for it in items:
        status = "✅" if it["enabled"] else "❌"
        lines.append(f"{status} كل {it['interval_min']} دقيقة: {it['text'][:50]}")
    return "\n".join(lines)

def mention_show_text(chat_id):
    s = db.get_periodic_mention(chat_id)
    e = "✅ مفعل" if s["enabled"] else "❌ معطل"
    msg = s["message"][:80] if s["message"] else "_مفيش نص مخصص_"
    return ("🔔 *المنشن الدوري*\n\n"
            f"الحالة: {e}\n"
            f"⏰ كل: *{s['interval_min']}* دقيقة\n"
            f"👥 عدد المنشن: *{s['mention_count']}*\n"
            f"✍️ النص: {msg}")

def channels_list_text(chat_id):
    chans = db.list_channels(chat_id)
    if not chans:
        return "📢 *قنوات الاشتراك*\n\n📭 لا توجد قنوات."
    lines = [f"📢 *قنوات الاشتراك* ({len(chans)})\n"]
    for c in chans:
        lines.append(f"• {c['title'] or c['username'] or c['channel_id']}")
    return "\n".join(lines)

def all_groups_list_text():
    groups = db.list_groups()
    if not groups:
        return "🌐 *كل جروبات البوت*\n\n📭 لا توجد جروبات."
    lines = [f"🌐 *كل جروبات البوت* ({len(groups)})\n"]
    for g in groups[:50]:
        status = "✅" if g["activated"] else "⛔"
        lines.append(f"{status} {g['title'] or g['chat_id']}")
    return "\n".join(lines)

# ===== Callback: عرض قائمة الجروبات =====
async def cb_panel_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    db.clear_pending(q.from_user.id)
    uid = q.from_user.id
    me = await ctx.bot.get_me()
    all_groups = db.list_groups()
    groups = []
    for g in all_groups:
        try:
            # لازم: المستخدم أدمن + البوت أدمن
            user_m = await ctx.bot.get_chat_member(g["chat_id"], uid)
            bot_m = await ctx.bot.get_chat_member(g["chat_id"], me.id)
            user_ok = user_m.status in ("creator", "administrator")
            bot_ok = bot_m.status in ("creator", "administrator")
            if user_ok and bot_ok:
                groups.append(g)
        except Exception:
            pass
    if not groups:
        return await safe_edit(q, "🌐 *جروباتك*\n\n📭 لا توجد جروبات أنت والبوت أدمن فيها.", parse_mode=ParseMode.MARKDOWN,
                               reply_markup=M([[B("🔙 رجوع", callback_data="panel:home")]]))
    text = f"🌐 *جروباتك* ({len(groups)})\n\nاضغط على جروب لفتح لوحة التحكم:"
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN,
                    reply_markup=groups_list_kb(groups, q.from_user.id))

# ===== Callback: فتح لوحة جروب معين =====
async def cb_panel_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    g = db.get_group(cid)
    if not g:
        return await q.answer("❌ الجروب مش موجود.", show_alert=True)
    ch_count = db.count_channels(cid)
    await safe_edit(q, group_panel_text(g, ch_count), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=group_panel_kb(g, ch_count))

# ===== Callback: نسيان جروب =====
async def cb_panel_forget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    cid = int(q.data.split(":")[2])
    db.forget_group(cid)
    await q.answer("🗑 تم نسيان الجروب.")
    groups = db.list_groups()
    if not groups:
        return await safe_edit(q, "🌐 *جروباتك*\n\n📭 لا توجد جروبات.", parse_mode=ParseMode.MARKDOWN,
                               reply_markup=M([[B("🔙 رجوع", callback_data="panel:home")]]))
    await safe_edit(q, f"🌐 *جروباتك* ({len(groups)})", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=groups_list_kb(groups, q.from_user.id))

# ===== Callback: تفعيل/تعطيل البوت في الجروب =====
async def cb_panel_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    db.activate_group(cid, q.from_user.id)
    await q.answer("✅ تم التفعيل")
    g = db.get_group(cid)
    ch_count = db.count_channels(cid)
    await safe_edit(q, group_panel_text(g, ch_count), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=group_panel_kb(g, ch_count))

async def cb_panel_off(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    db.deactivate_group(cid)
    await q.answer("⛔ تم التعطيل")
    g = db.get_group(cid)
    ch_count = db.count_channels(cid)
    await safe_edit(q, group_panel_text(g, ch_count), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=group_panel_kb(g, ch_count))

# ===== Callback: إضافة قناة للجروب =====
async def cb_panel_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    ch_count = db.count_channels(cid)
    if ch_count >= MAX_CHANNELS_PER_GROUP:
        return await q.answer(f"⚠️ الحد الأقصى {MAX_CHANNELS_PER_GROUP} قنوات.", show_alert=True)
    db.set_pending(q.from_user.id, cid, extra=None)
    await safe_edit(q, channel_prompt_text(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=cancel_kb(f"panel:g:{cid}"))

# ===== Callback: عرض قنوات الجروب =====
async def cb_panel_chs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    chans = db.list_channels(cid)
    if not chans:
        return await q.answer("📭 لا توجد قنوات.", show_alert=True)
    await safe_edit(q, channels_list_text(cid), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=channels_kb(cid, chans))

# ===== Callback: حذف قناة من الجروب =====
async def cb_panel_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    cid = int(parts[2])
    chid = int(parts[3])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    db.remove_channel(cid, chid)
    await q.answer("🗑 تم حذف القناة.")
    chans = db.list_channels(cid)
    if not chans:
        g = db.get_group(cid)
        ch_count = db.count_channels(cid)
        return await safe_edit(q, group_panel_text(g, ch_count), parse_mode=ParseMode.MARKDOWN,
                               reply_markup=group_panel_kb(g, ch_count))
    await safe_edit(q, channels_list_text(cid), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=channels_kb(cid, chans))

# ===== Callback: قائمة الحماية =====
async def cb_protect_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    await safe_edit(q, protect_full_text(cid), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=protect_kb(cid, db.get_antilink(cid)))

# ===== Callback: تفعيل/تعطيل منع الروابط =====
async def cb_protect_al(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    cur = db.get_antilink(cid)
    db.set_antilink(cid, not cur)
    await q.answer("✅ تم التفعيل" if not cur else "❌ تم التعطيل")
    await safe_edit(q, protect_full_text(cid), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=protect_kb(cid, db.get_antilink(cid)))

# ===== Callback: تفعيل/تعطيل الترحيب =====
async def cb_protect_wl(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    if len(parts) < 3:
        return await q.answer("❌ خطأ في البيانات.", show_alert=True)
    cid = int(parts[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    g = db.get_group(cid)
    if not g:
        return await q.answer("❌ الجروب مش موجود.", show_alert=True)
    cur = g.get("welcome_enabled", True)
    new_val = not cur
    db.set_welcome(cid, new_val)
    await q.answer("✅ تم تفعيل الترحيب" if new_val else "❌ تم تعطيل الترحيب")
    await safe_edit(q, protect_full_text(cid), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=protect_kb(cid, db.get_antilink(cid)))

# ===== Callback: الكلمات الممنوعة =====
async def cb_protect_bw(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    words = db.list_banned_words(cid)
    if not words:
        return await safe_edit(q,
            "🚫 *الكلمات الممنوعة*\n\n📭 لا توجد كلمات ممنوعة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=banned_words_kb(cid, []))
    text = f"🚫 *الكلمات الممنوعة* ({len(words)})\n\nاضغط على الكلمة لحذفها:"
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN,
                    reply_markup=banned_words_kb(cid, words))

# ===== Callback: إضافة كلمة ممنوعة =====
async def cb_protect_bwa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    db.set_pending(q.from_user.id, cid, extra=f"bw:{cid}")
    await safe_edit(q,
        "🚫 *إضافة كلمات ممنوعة*\n\n"
        "اكتب كلمة أو أكتر (كل وحدة في سطر):\n\n"
        "مثال:\nكلمة1\nكلمة2",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_kb(f"protect:bw:{cid}"))

# ===== Callback: حذف كلمة ممنوعة =====
async def cb_protect_bwd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    wid = int(parts[2])
    cid = int(parts[3]) if len(parts) > 3 else None
    if not cid:
        return
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    db.remove_banned_word(wid)
    await q.answer("🗑 تم الحذف")
    words = db.list_banned_words(cid)
    if not words:
        return await safe_edit(q,
            "🚫 *الكلمات الممنوعة*\n\n📭 لا توجد كلمات ممنوعة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=banned_words_kb(cid, []))
    text = f"🚫 *الكلمات الممنوعة* ({len(words)})\n\nاضغط على الكلمة لحذفها:"
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN,
                    reply_markup=banned_words_kb(cid, words))

# ===== Callback: قائمة الجدولة =====
async def cb_protect_sched(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    await safe_edit(q, schedule_show_text(cid), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=schedule_kb(cid))

# ===== Callback: إضافة رسالة مجدولة =====
async def cb_sched_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    db.set_pending(q.from_user.id, cid, extra=f"sched_text:{cid}")
    await safe_edit(q, schedule_add_text(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=cancel_kb(f"protect:sched:{cid}"))

# ===== Callback: عرض الرسائل المجدولة =====
async def cb_sched_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    await safe_edit(q, schedule_show_text(cid), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=schedule_kb(cid))

# ===== Callback: قائمة حذف الرسائل المجدولة =====
async def cb_sched_del_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    items = db.list_scheduled(cid)
    if not items:
        return await q.answer("📭 لا توجد رسائل.", show_alert=True)
    await safe_edit(q, "🗑 *اضغط على الرسالة لحذفها:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=schedule_delete_kb(cid, items))

# ===== Callback: حذف رسالة مجدولة =====
async def cb_sched_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    parts = q.data.split(":")
    cid = int(parts[2])
    sid = int(parts[3])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    db.remove_scheduled(sid)
    await q.answer("🗑 تم الحذف")
    items = db.list_scheduled(cid)
    if not items:
        return await safe_edit(q, schedule_show_text(cid), parse_mode=ParseMode.MARKDOWN,
                               reply_markup=schedule_kb(cid))
    await safe_edit(q, "🗑 *اضغط على الرسالة لحذفها:*", parse_mode=ParseMode.MARKDOWN,
                    reply_markup=schedule_delete_kb(cid, items))

# ===== Callback: قائمة المنشن الدوري =====
async def cb_protect_mention(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    s = db.get_periodic_mention(cid)
    await safe_edit(q, mention_show_text(cid), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=mention_kb(cid, s["enabled"]))

# ===== Callback: تفعيل/تعطيل المنشن =====
async def cb_mention_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    s = db.get_periodic_mention(cid)
    db.set_periodic_mention(cid, enabled=not s["enabled"])
    await q.answer("✅ تم التفعيل" if not s["enabled"] else "❌ تم التعطيل")
    s = db.get_periodic_mention(cid)
    await safe_edit(q, mention_show_text(cid), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=mention_kb(cid, s["enabled"]))

# ===== Callback: وقت المنشن =====
async def cb_mention_time(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    db.set_pending(q.from_user.id, cid, extra=f"mention_time:{cid}")
    await safe_edit(q, mention_time_prompt(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=cancel_kb(f"protect:mention:{cid}"))

# ===== Callback: عدد المنشن =====
async def cb_mention_count(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    db.set_pending(q.from_user.id, cid, extra=f"mention_count:{cid}")
    await safe_edit(q, mention_count_prompt(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=cancel_kb(f"protect:mention:{cid}"))

# ===== Callback: نص المنشن =====
async def cb_mention_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    if not (is_owner(q.from_user.id) or await is_user_admin(ctx.bot, cid, q.from_user.id)):
        return await q.answer("⛔ للمشرفين فقط.", show_alert=True)
    db.set_pending(q.from_user.id, cid, extra=f"mention_text:{cid}")
    await safe_edit(q, mention_text_prompt(), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=cancel_kb(f"protect:mention:{cid}"))

# ===== Callback: بيانات الجروب (أعضاء + رسائل) =====
async def cb_data_members(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    parts = q.data.split(":")
    cid = int(parts[2])
    members = db.list_members(cid)
    if not members:
        return await safe_edit(q, "👥 *أعضاء الجروب*\n\n📭 لا يوجد أعضاء مسجلين.",
                               parse_mode=ParseMode.MARKDOWN,
                               reply_markup=group_data_sub_kb(cid))
    # نبعت كل عضو كزر (يفتح البروفايل)
    rows = []
    for m in members[:50]:
        name = (m.get("first_name") or "")[:25]
        rows.append([B(f"👤 {name}", url=f"tg://user?id={m['user_id']}")])
    rows.append([B("🔙 رجوع", callback_data=f"owner:data:{cid}")])
    kb = M(rows)
    await safe_edit(q, f"👥 *أعضاء الجروب* ({len(members)})\n\nاضغط على أي عضو لفتح بروفايله:",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def cb_data_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    try:
        parts = q.data.split(":")
        cid = int(parts[2])
        uid = int(parts[3])
    except (IndexError, ValueError):
        return
    m = db.get_member(cid, uid)
    if not m:
        return await q.answer("❌ العضو مش موجود.", show_alert=True)
    p = db.get_points(cid, uid)
    acc = db.get_bank_account(uid)
    text = (f"👤 *بيانات العضو*\n\n"
            f"📛 الاسم: {escape_html(m['first_name'] or 'بدون')}\n"
            f"🆔 الآيدي: `{uid}`\n")
    if m.get('username'):
        text += f"👤 اليوزر: @{m['username']}\n"
    text += f"\n💰 الفلوس: *{fmt_money(p['points'])}*\n"
    text += f"🏆 الانتصارات: *{p['wins']}*\n"
    if acc:
        text += f"💳 رقم الحساب: `{acc['account_number']}`\n"
        text += f"💵 الرصيد البنكي: *{fmt_money(acc['balance'])}*\n"
    kb = M([
        [B("🔗 فتح البروفايل", url=f"tg://user?id={uid}")],
        [B("🔙 رجوع", callback_data=f"data:members:{cid}")],
    ])
    try:
        await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        try:
            await q.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except: pass

async def cb_data_messages(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    cid = int(q.data.split(":")[2])
    n_text = db.count_media_messages(cid) or 0
    # عدد الرسايل النصية
    try:
        import sqlite3
        conn = sqlite3.connect(db.DB_PATH)
        total = conn.execute("SELECT COUNT(*) FROM group_messages WHERE chat_id=?", (cid,)).fetchone()[0]
        photos = conn.execute("SELECT COUNT(*) FROM group_messages WHERE chat_id=? AND media_type='photo'", (cid,)).fetchone()[0]
        videos = conn.execute("SELECT COUNT(*) FROM group_messages WHERE chat_id=? AND media_type='video'", (cid,)).fetchone()[0]
        conn.close()
    except:
        total, photos, videos = 0, 0, 0
    text = (
        "📨 *الرسائل والوسائط*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💬 إجمالي الرسائل: *{total}*\n"
        f"🖼 صور: *{photos}*\n"
        f"🎥 فيديوهات: *{videos}*\n\n"
        "اختر النوع:"
    )
    kb = M([
        [B("📝 نصوص", callback_data=f"data:type:text:{cid}")],
        [B("🖼 صور", callback_data=f"data:type:photo:{cid}")],
        [B("🎥 فيديوهات", callback_data=f"data:type:video:{cid}")],
        [B("🔙 رجوع", callback_data=f"owner:data:{cid}")],
    ])
    await safe_edit(q, text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def cb_data_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """data:type:TYPE:CHAT_ID"""
    q = update.callback_query; await q.answer()
    if not is_owner(q.from_user.id):
        return await q.answer("⛔ للمالك فقط.", show_alert=True)
    parts = q.data.split(":")
    mtype = parts[2]
    cid = int(parts[3])
    # نحفظ الـ pending ونطلب العدد
    db.set_pending(q.from_user.id, cid, extra=f"data_count:{mtype}:{cid}")
    type_ar = {"text": "نصوص", "photo": "صور", "video": "فيديوهات"}.get(mtype, mtype)
    await safe_edit(q,
        f"📊 *{type_ar}*\n\n"
        "اكتب عدد الرسائل:\n"
        "أو اكتب `الكل` لكل الرسائل\n"
        "مثال: `20`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_kb(f"data:messages:{cid}"))

async def cb_data_media(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """للتوافق مع الكود القديم — يوجّه لـ cb_data_type photo"""
    q = update.callback_query; await q.answer()
    cid = int(q.data.split(":")[2])
    q.data = f"data:type:photo:{cid}"
    await cb_data_type(update, ctx)

# ===== Callback: الرجوع للرئيسية =====
async def cb_panel_home(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    db.clear_pending(q.from_user.id)
    await safe_edit(q, main_text(q.from_user), parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu_kb(is_owner(q.from_user.id)))

# ============ نهاية الجزء 8 ============



# ============ بداية الجزء 9 — استقبال الرسائل + main ============

# ===== دوال مساعدة =====
async def safe_edit(query, text, parse_mode=None, reply_markup=None):
    """تعديل رسالة بشكل آمن — ما تعملش رسالة جديدة أبداً"""
    try:
        await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except TelegramError as e:
        err = str(e).lower()
        # لو الرسالة مش اتغيرت → مفيش حاجة نعملها
        if "not modified" in err:
            return
        # لو الرسالة مافيهاش نص (صورة/فيديو) → نحاول edit caption
        if "no text" in err or "there is no text" in err:
            try:
                await query.edit_message_caption(caption=text, parse_mode=parse_mode, reply_markup=reply_markup)
                return
            except: pass
        # لو فشلت كل المحاولات → log فقط
        log.warning(f"safe_edit failed: {e}")

# ===== require_sub (الاشتراك الإجباري) =====
async def require_sub(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    """يتحقق من الاشتراك الإجباري في القنوات الافتراضية"""
    if update.effective_chat.type != ChatType.PRIVATE:
        return True
    uid = update.effective_user.id
    if is_owner(uid):
        return True
    chans = db.list_default_channels()
    if not chans:
        return True
    missing = await missing_channels(ctx.bot, chans, uid)
    if not missing:
        return True
    await update.message.reply_text(
        "⚠️ *لازم تشترك في القنوات الأول*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=subscribe_kb(missing, uid)
    )
    return False

async def cb_sub_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يتحقق من الاشتراك بعد ما المستخدم يدوس زر"""
    q = update.callback_query
    target_uid = int(q.data.split(":")[2])
    if q.from_user.id != target_uid:
        return await q.answer("مش زراك.", show_alert=True)
    uid = q.from_user.id
    chans = db.list_default_channels()
    missing = await missing_channels(ctx.bot, chans, uid)
    if not missing:
        await q.answer("✅ تم التحقق!")
        try: await q.message.delete()
        except: pass
        db.save_user(uid, q.from_user.first_name, q.from_user.username)
        try:
            await ctx.bot.send_message(uid, main_text(q.from_user),
                parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_kb(is_owner(uid)))
        except: pass
    else:
        await q.answer("⚠️ لسه مشتركتش في القنوات!", show_alert=True)

# ===== الترحيب =====
async def send_welcome(bot, chat_id, user):
    """يرسل رسالة ترحيب بالعضو الجديد"""
    g = db.get_group(chat_id)
    if not g or not g.get("welcome_enabled", True):
        return
    if not g["activated"]:
        return
    name = user.first_name or "عضو"
    # لو فيه جملة ترحيب مخصصة
    custom = g.get("welcome_text", "")
    if custom:
        text = custom.replace("{name}", f'<a href="tg://user?id={user.id}">{escape_html(name)}</a>')
    else:
        text = f'👋 أهلاً <a href="tg://user?id={user.id}">{escape_html(name)}</a>'
    try: await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
    except: pass

# ===== معالجة النصوص المنتظرة =====
async def handle_pending_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    """يعالج النصوص المنتظرة من المالك/الأدمن. يرجع True لو استهلك الرسالة"""
    uid = update.effective_user.id
    pending = db.get_pending(uid)
    if not pending:
        return False
    target = pending["target_chat_id"]
    extra = pending.get("extra") or ""
    text = update.message.text or ""
    if not text:
        return False

    # ===== إضافة قناة افتراضية =====
    if target == PENDING_DEFAULT:
        ch_data = await resolve_channel(ctx.bot, extract_channel_identifier(update.message))
        if not ch_data["ok"]:
            return await update.message.reply_text(ch_data["reason"]), True
        db.add_default_channel(ch_data["channel"])
        db.clear_pending(uid)
        await update.message.reply_text(
            f"✅ تم إضافة القناة: *{escape_html(ch_data['channel']['title'])}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=owner_subs_kb())
        return True

    # ===== إضافة قناة لجروب =====
    if extra.startswith("add_channel"):
        pass
    if not extra and isinstance(target, int) and target != 0:
        # PENDING_ADD_CHANNEL: أضف قناة للجروب
        ch_data = await resolve_channel(ctx.bot, extract_channel_identifier(update.message))
        if not ch_data["ok"]:
            return await update.message.reply_text(ch_data["reason"]), True
        db.add_channel(target, ch_data["channel"])
        db.clear_pending(uid)
        g = db.get_group(target)
        ch_count = db.count_channels(target)
        await update.message.reply_text(
            f"✅ تم إضافة القناة: *{escape_html(ch_data['channel']['title'])}*",
            parse_mode=ParseMode.MARKDOWN)
        return True

    # ===== إضافة رد تلقائي — المرحلة 1: الكلمة =====
    if target == PENDING_ADD_TRIGGER:
        trigger = text.strip()
        if not trigger:
            return await update.message.reply_text("⚠️ اكتب كلمة صحيحة."), True
        db.set_pending(uid, PENDING_ADD_REPLY, extra=trigger)
        await update.message.reply_text(
            ar_response_prompt_text(escape_html(trigger)),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=cancel_kb(PENDING_ADD_REPLY))
        return True

    # ===== إضافة رد تلقائي — المرحلة 2: الرد =====
    if target == PENDING_ADD_REPLY:
        trigger = extra
        response = text.strip()
        if not trigger or not response:
            db.clear_pending(uid)
            return await update.message.reply_text("⚠️ تم الإلغاء."), True
        if db.auto_reply_exists(trigger, response):
            db.clear_pending(uid)
            return await update.message.reply_text("⚠️ الرد موجود بالفعل."), True
        db.add_auto_reply(trigger, response)
        db.clear_pending(uid)
        await update.message.reply_text(
            f"✅ تم إضافة الرد:\n*{escape_html(trigger)}* → {escape_html(response)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=owner_ar_kb())
        return True

    # ===== إضافة كلمات محظورة عامة =====
    if target == PENDING_GLOBAL_BANNED:
        words = [w.strip() for w in text.splitlines() if w.strip()]
        added = 0
        for w in words:
            if not db.global_banned_word_exists(w):
                db.add_global_banned_word(w)
                added += 1
        db.clear_pending(uid)
        await update.message.reply_text(
            f"✅ تم إضافة *{added}* كلمة محظورة عامة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=owner_gban_kb())
        return True

    # ===== إضافة كلمة/سؤال للعبة =====
    if target == PENDING_ADD_GAME_WORD:
        if extra.startswith("q:"):
            game = extra[2:]
            content = text.strip()
            if not content:
                return await update.message.reply_text("⚠️ اكتب حاجة."), True
            db.set_pending(uid, PENDING_ADD_GAME_ANSWER, extra=f"{game}::{content}")
            await update.message.reply_text(
                game_answer_prompt_text(escape_html(content), game),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=cancel_kb(PENDING_ADD_GAME_ANSWER))
            return True
        else:
            game = extra
            words = [w.strip() for w in text.splitlines() if w.strip()]
            added = 0
            for w in words:
                if not db.game_content_exists(game, w):
                    db.add_game_content(game, w)
                    added += 1
            db.clear_pending(uid)
            await update.message.reply_text(
                f"✅ تم إضافة *{added}* عنصر لـ {game_name(game)}.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=owner_game_kb(game))
            return True

    # ===== إضافة إجابة لعبة (مرحلة 2) =====
    if target == PENDING_ADD_GAME_ANSWER:
        parts = extra.split("::", 1)
        game = parts[0]
        content = parts[1] if len(parts) > 1 else ""
        answer = text.strip()
        if not answer:
            return await update.message.reply_text("⚠️ اكتب إجابة."), True
        if db.game_content_exists(game, content):
            db.clear_pending(uid)
            return await update.message.reply_text("⚠️ السؤال موجود بالفعل."), True
        db.add_game_content(game, content, answer)
        db.clear_pending(uid)
        await update.message.reply_text(
            f"✅ تم إضافة السؤال والإجابة لـ {game_name(game)}.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=owner_game_kb(game))
        return True

    # ===== إضافة كلمة سرية للجاسوس =====
    if target == PENDING_SPY_WORD:
        words = [w.strip() for w in text.splitlines() if w.strip()]
        added = 0
        for w in words:
            if not db.game_content_exists(GAME_SPY, w):
                db.add_game_content(GAME_SPY, w)
                added += 1
        db.clear_pending(uid)
        await update.message.reply_text(
            f"✅ تم إضافة *{added}* كلمة سرية.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=owner_spy_kb())
        return True

    # ===== إعدادات لعبة الجاسوس =====
    if target == PENDING_SPY_SETTING:
        try: val = int(normalize_digits(text))
        except ValueError:
            return await update.message.reply_text("⚠️ اكتب رقم صحيح."), True
        if extra == "min" and 3 <= val <= 10:
            db.set_spy_setting(0, "min_players", val)
        elif extra == "max" and 3 <= val <= 15:
            db.set_spy_setting(0, "max_players", val)
        elif extra == "disc" and 1 <= val <= 10:
            db.set_spy_setting(0, "discussion_sec", val * 60)
        elif extra == "vote" and 30 <= val <= 300:
            db.set_spy_setting(0, "voting_sec", val)
        else:
            return await update.message.reply_text("⚠️ قيمة خارج النطاق."), True
        db.clear_pending(uid)
        await update.message.reply_text(
            "✅ تم حفظ الإعداد.",
            reply_markup=owner_spy_settings_kb())
        return True

    # ===== إعدادات البنك =====
    if target == PENDING_BANK_SETTING:
        try: val = int(normalize_digits(text))
        except ValueError:
            return await update.message.reply_text("⚠️ اكتب رقم صحيح."), True
        allowed = {"salary_amount","salary_cooldown","tip_amount","tip_cooldown",
                   "steal_success","steal_fine","steal_min","steal_max","steal_cooldown",
                   "invest_min_pct","invest_max_pct","invest_cooldown",
                   "luck_win_pct","luck_cooldown"}
        if extra not in allowed:
            db.clear_pending(uid)
            return await update.message.reply_text("⚠️ إعداد غير معروف."), True
        if extra in ("steal_success","invest_min_pct","invest_max_pct","luck_win_pct") and not (0 <= val <= 100):
            return await update.message.reply_text("⚠️ النسبة لازم تكون 0-100."), True
        db.set_bank_setting(extra, val)
        db.clear_pending(uid)
        await update.message.reply_text(
            f"✅ تم حفظ *{extra}* = *{val}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=owner_bank_kb())
        return True

    # ===== رسالة مجدولة — المرحلة 1: النص =====
    if extra.startswith("sched_text:"):
        cid = int(extra.split(":")[1])
        if not text.strip():
            return await update.message.reply_text("⚠️ اكتب نص."), True
        db.set_pending(uid, cid, extra=f"sched_time:{cid}::{text.strip()}")
        await update.message.reply_text(schedule_time_text(), parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=cancel_kb(f"protect:sched:{cid}"))
        return True

    # ===== رسالة مجدولة — المرحلة 2: الوقت =====
    if extra.startswith("sched_time:"):
        parts = extra.split("::", 1)
        cid = int(parts[0].split(":")[1])
        msg = parts[1] if len(parts) > 1 else ""
        try: minutes = int(normalize_digits(text))
        except ValueError:
            return await update.message.reply_text("⚠️ اكتب رقم."), True
        if minutes < 1:
            return await update.message.reply_text("⚠️ الحد الأدنى دقيقة."), True
        db.add_scheduled(cid, msg, minutes)
        db.clear_pending(uid)
        await update.message.reply_text(
            f"✅ تم جدولة الرسالة كل *{minutes}* دقيقة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=schedule_kb(cid))
        return True

    # ===== المنشن الدوري — الوقت =====
    if extra.startswith("mention_time:"):
        cid = int(extra.split(":")[1])
        try: val = int(normalize_digits(text))
        except ValueError:
            return await update.message.reply_text("⚠️ اكتب رقم."), True
        if val < 1:
            return await update.message.reply_text("⚠️ الحد الأدنى دقيقة."), True
        db.set_periodic_mention(cid, interval_min=val)
        db.clear_pending(uid)
        await update.message.reply_text(f"✅ كل *{val}* دقيقة.", parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=mention_kb(cid, db.get_periodic_mention(cid)["enabled"]))
        return True

    # ===== المنشن الدوري — العدد =====
    if extra.startswith("mention_count:"):
        cid = int(extra.split(":")[1])
        try: val = int(normalize_digits(text))
        except ValueError:
            return await update.message.reply_text("⚠️ اكتب رقم."), True
        if val < 1: val = 1
        db.set_periodic_mention(cid, mention_count=val)
        db.clear_pending(uid)
        await update.message.reply_text(f"✅ عدد المنشن: *{val}*.", parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=mention_kb(cid, db.get_periodic_mention(cid)["enabled"]))
        return True

    # ===== المنشن الدوري — النص =====
    if extra.startswith("mention_text:"):
        cid = int(extra.split(":")[1])
        msg = "" if text.strip() == "بدون" else text.strip()
        db.set_periodic_mention(cid, message=msg)
        db.clear_pending(uid)
        await update.message.reply_text("✅ تم حفظ النص.", reply_markup=mention_kb(cid, db.get_periodic_mention(cid)["enabled"]))
        return True

    # ===== الكلمات الممنوعة للجروب =====
    if extra.startswith("bw:"):
        cid = int(extra.split(":")[1])
        words = [w.strip() for w in text.splitlines() if w.strip()]
        added = 0
        for w in words:
            if not db.banned_word_exists(cid, w):
                db.add_banned_word(cid, w)
                added += 1
        db.clear_pending(uid)
        words_list = db.list_banned_words(cid)
        await update.message.reply_text(
            f"✅ تم إضافة *{added}* كلمة ممنوعة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=banned_words_kb(cid, words_list))
        return True

    # ===== عدد الرسائل (النوع + العدد) =====
    if extra.startswith("data_count:"):
        parts = extra.split(":")
        mtype = parts[1]
        cid = int(parts[2])
        # العدد
        if text.strip() in ("الكل", "كل", "all"):
            n = 200
        else:
            try: n = int(normalize_digits(text))
            except ValueError:
                return await update.message.reply_text("⚠️ اكتب رقم أو (الكل)."), True
        n = min(max(1, n), 200)
        db.clear_pending(uid)
        # نجيب الرسائل حسب النوع
        if mtype == "text":
            msgs = db.list_messages(cid, n)
            if not msgs:
                return await update.message.reply_text("📭 لا توجد نصوص."), True
            lines = [f"📝 *آخر {len(msgs)} نص*\n"]
            for m in msgs[:50]:
                t = time.strftime("%H:%M", time.localtime(m["created_at"]))
                lines.append(f"[{t}] *{escape_html(m['first_name'])}*: {escape_html((m['text'] or '')[:60])}")
            txt = "\n".join(lines)
            if len(txt) > 4000: txt = txt[:4000] + "\n..."
            await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN,
                                            reply_markup=group_data_sub_kb(cid))
        elif mtype in ("photo", "video"):
            media = db.list_media_messages(cid, mtype, n)
            if not media:
                return await update.message.reply_text(f"📭 لا توجد {mtype}."), True
            # نبعت رسالة تأكيد أول
            await update.message.reply_text(f"📤 جاري إرسال {len(media)} {mtype}...")
            sent = 0
            for m in media:
                try:
                    await ctx.bot.forward_message(
                        chat_id=uid,
                        from_chat_id=cid,
                        message_id=m["message_id"],
                        disable_notification=True)
                    sent += 1
                    await asyncio.sleep(0.3)  # نتجنب flood
                except Exception:
                    pass
            await update.message.reply_text(
                f"✅ تم إرسال *{sent}* من *{len(media)}*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=group_data_sub_kb(cid))
        return True

    # ===== بث لكل الجروبات =====
    if target == PENDING_BROADCAST and extra == "broadcast":
        groups = db.list_groups()
        sent, failed = 0, 0
        for g in groups:
            try:
                await ctx.bot.send_message(g["chat_id"], text)
                sent += 1
            except: failed += 1
        db.clear_pending(uid)
        await update.message.reply_text(
            f"📣 *تم البث*\n\n✅ نجح: {sent}\n❌ فشل: {failed}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=owner_menu_kb())
        return True

    # ===== إضافة نكتة =====
    if extra == "jokes_add":
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        added = 0
        for line in lines:
            if len(line) >= 5:
                db.add_joke(line, uid)
                added += 1
        db.clear_pending(uid)
        await update.message.reply_text(
            f"✅ تم إضافة *{added}* نكتة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=owner_jokes_kb())
        return True

    # ===== إضافة مطور =====
    if extra == "devs_add":
        # نشوف لو رسالة فيها ID
        nums = re.findall(r"\d+", normalize_digits(text))
        if not nums:
            return await update.message.reply_text("⚠️ ابعت ID صحيح."), True
        target = int(nums[0])
        if target == OWNER_ID:
            db.clear_pending(uid)
            return await update.message.reply_text("⚠️ ده المالك، مش محتاج إضافة."), True
        # نجيب معلوماته لو موجود
        try:
            u = db.get_user(target)
            first_name = u["first_name"] if u else None
            username = u["username"] if u else None
        except:
            first_name, username = None, None
        db.add_developer(target, first_name, username, uid)
        # نفعّل كل الصلاحيات افتراضي
        for key, _ in db.DEV_PERMS:
            db.set_dev_permission(target, key, False)
        db.clear_pending(uid)
        await update.message.reply_text(
            f"✅ تم إضافة المطور: `{target}`\n\n"
            "⚠️ لسه محتاج تفعّل صلاحياته من قائمة المطورين.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=M([[B("👑 المطورين", callback_data="owner:devs")]]))
        return True

    # ===== استعادة قاعدة البيانات =====
    if target == PENDING_BROADCAST and extra == "import_db":
        return False  # بيتعامل معاه في الدوال اللي تحت

    # ===== /say من النص =====
    if target == PENDING_SAY_TEXT:
        return False

    return False

# ===== معالجة الملفات (استعادة قاعدة البيانات) =====
async def handle_pending_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    uid = update.effective_user.id
    pending = db.get_pending(uid)
    if not pending:
        return False
    extra = pending.get("extra") or ""
    if extra != "import_db":
        return False
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".db"):
        await update.message.reply_text("⚠️ ابعت ملف `data.db`.")
        return True
    try:
        file = await ctx.bot.get_file(doc.file_id)
        import_path = db.DB_PATH + ".import"
        await file.download_to_drive(import_path)
        import shutil
        shutil.move(import_path, db.DB_PATH)
        db.clear_pending(uid)
        await update.message.reply_text("✅ تم استعادة قاعدة البيانات. أعد تشغيل البوت.")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل: {e}")
    return True

# ===== أوامر الجروبات =====
async def cmd_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """id — بسيط: بالرد يعرض id المردود عليه، بدون رد يعرض id اللي كتب"""
    user = update.effective_user
    if update.message and update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        text = f"🆔 `{target.id}`"
    else:
        text = f"🆔 `{user.id}`"
    try: await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except: pass

async def cmd_muted(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in GROUP_TYPES: return
    cid = update.effective_chat.id
    if not (is_owner(update.effective_user.id) or await is_user_admin(ctx.bot, cid, update.effective_user.id)):
        return
    muted = db.list_muted(cid)
    if not muted:
        return await update.message.reply_text("📭 لا يوجد مكتومين.")
    lines = [f"🔇 *المكتومين* ({len(muted)})\n"]
    for m in muted[:50]:
        lines.append(f"• {escape_html(m['first_name'])} — `{m['user_id']}`")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

async def cmd_banned(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in GROUP_TYPES: return
    cid = update.effective_chat.id
    if not (is_owner(update.effective_user.id) or await is_user_admin(ctx.bot, cid, update.effective_user.id)):
        return
    await update.message.reply_text("ℹ️ قائمة المحظورين مش متاحة حالياً.", parse_mode=ParseMode.MARKDOWN)

# ===== on_my_chat_member =====
async def on_my_chat_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.my_chat_member: return
    chat = update.my_chat_member.chat
    new = update.my_chat_member.new_chat_member.status
    if chat.type not in GROUP_TYPES: return
    if new == "administrator":
        # البوت اترفع أدمن — نفعّل الجروب تلقائياً
        db.remember_group(chat.id, chat.title or "")
        db.activate_group(chat.id, 0)
        log.info(f"✅ تفعيل تلقائي: {chat.title} ({chat.id})")
    elif new == "member":
        # البوت عضو عادي (اتنزل من الأدمن) — نعطّله
        db.remember_group(chat.id, chat.title or "")
        db.deactivate_group(chat.id)
        log.info(f"⚠️ البوت بقى عضو عادي: {chat.title} ({chat.id})")
    elif new in ("left", "kicked"):
        # البوت خرج — نشيله
        db.forget_group(chat.id)
        log.info(f"❌ البوت خرج: {chat.title} ({chat.id})")

# ===== on_group_msg — المعالج الرئيسي =====
async def on_group_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat: return
    chat = update.effective_chat
    if chat.type not in GROUP_TYPES: return
    cid = chat.id
    user = update.effective_user
    if not user: return
    text = update.message.text or update.message.caption or ""
    uid = user.id

    # 1) تسجيل الجروب والعضو
    db.remember_group(cid, chat.title or "")
    db.save_user(uid, user.first_name, user.username)
    db.save_member(cid, uid, user.first_name, user.username)

    # 2) تخزين الرسالة (للمالك) — نصوص + وسائط
    msg = update.message
    media_type = None
    if msg.photo:
        media_type = "photo"
    elif msg.video:
        media_type = "video"
    elif msg.document:
        media_type = "document"
    elif msg.voice:
        media_type = "voice"
    elif msg.audio:
        media_type = "audio"
    if (text or media_type) and not (text and text.startswith("/")):
        db.save_message(cid, uid, user.first_name, text or "", msg.message_id, media_type)

    g = db.get_group(cid)
    if not g or not g["activated"]:
        # لو مش مفعل، سجل العضو وخلاص
        return

    # 3) الكلمات المحظورة (المالك والأدمن يعدّوا)
    is_admin = is_owner(uid) or await is_user_admin(ctx.bot, cid, uid)
    # (is_admin محسوب مرة واحدة — مع كاش)
    if not is_admin:
        # كلمات محظورة عامة
        gbw = db.find_global_banned_word(text) if text else None
        if gbw:
            try: await update.message.delete()
            except: pass
            try:
                m = await ctx.bot.send_message(cid,
                    f"🚫 *ممنوع!* الكلمة دي محظورة عامة.",
                    parse_mode=ParseMode.MARKDOWN)
                delete_later(ctx.bot, cid, m.message_id, 5000)
            except: pass
            return
        # كلمات محظورة الجروب
        bw = db.find_banned_word(cid, text) if text else None
        if bw:
            try: await update.message.delete()
            except: pass
            try:
                m = await ctx.bot.send_message(cid,
                    f"🚫 *ممنوع!* كلمة محظورة في الجروب ده.",
                    parse_mode=ParseMode.MARKDOWN)
                delete_later(ctx.bot, cid, m.message_id, 5000)
            except: pass
            return
        # منع الروابط — مع استثناء المالك والأدمن والقناة
        if db.get_antilink(cid) and text:
            # نتحقق إن الرسالة من القناة المربوطة
            is_from_channel = False
            try:
                if getattr(update.message, "sender_chat", None):
                    is_from_channel = True
                # PTB 21+ بستخدم forward_origin
                fwd_origin = getattr(update.message, "forward_origin", None)
                if fwd_origin and getattr(fwd_origin, "chat", None):
                    is_from_channel = True
            except Exception:
                pass
            # المالك والأدمن عدّوا (is_admin محسوب فوق)
            if not is_admin and not is_from_channel:
                if re.search(r"(https?://|t\.me/|www\.)", text):
                    try: await update.message.delete()
                    except: pass
                    try:
                        m = await ctx.bot.send_message(cid,
                            f"🔗 *ممنوع إرسال الروابط!*",
                            parse_mode=ParseMode.MARKDOWN)
                        delete_later(ctx.bot, cid, m.message_id, 5000)
                    except: pass
                    return

    # 4) الردود التلقائية / المالك / الأدمن
    if text:
        norm = normalize_text(text)
        if norm in [normalize_text(t) for t in TRIGGER_OWNER]:
            reply = await build_owner_reply(ctx.bot, cid)
            if reply: return await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        if norm in [normalize_text(t) for t in TRIGGER_ADMIN]:
            reply = await build_admins_reply(ctx.bot, cid)
            if reply: return await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        # ردود تلقائية
        r = find_reply_for(text)
        if r:
            return await update.message.reply_text(r)

    # 5) إحصائيات
    if text and not text.startswith("/"):
        db.add_points(cid, uid, 1, count_message=True)

    # 6) الألعاب النشطة
    if text:
        await handle_active_game_reply(update, ctx, cid, uid, text)

    # 7) أوامر اللعب النصية — دايماً ننادي
    if text:
        await handle_game_trigger(update, ctx, cid, uid, text)
        # إحصائيات
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_MY_STATS]:
            return await update.message.reply_text(
                await build_my_stats_reply(cid, uid, user.first_name),
                parse_mode=ParseMode.MARKDOWN)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_HIS_STATS] and update.message.reply_to_message:
            t = update.message.reply_to_message.from_user
            return await update.message.reply_text(
                await build_my_stats_reply(cid, t.id, t.first_name),
                parse_mode=ParseMode.MARKDOWN)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_TOP]:
            # توب → نعرض توب الفلوس + زر ➡️
            top = db.get_top(cid, 10)
            kb = M([[B("🥷 توب الحرامية ➡️", callback_data="top:thieves")]])
            if not top:
                return await update.message.reply_text("📊 لا يوجد لاعبين بعد.", reply_markup=kb)
            lines = ["🏆 *توب 10*\n"]
            medals = ["🥇","🥈","🥉"]
            for i, item in enumerate(top, 1):
                try:
                    m = await ctx.bot.get_chat_member(cid, item["user_id"])
                    display = escape_html(m.user.first_name or "عضو")
                except:
                    u = db.get_user(item["user_id"])
                    display = escape_html(u["first_name"]) if u and u["first_name"] else f"عضو {item['user_id']}"
                prefix = medals[i-1] if i <= 3 else f"{i}."
                lines.append(f"{prefix} {display} — *{fmt_money(item['points'])}*")
            return await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_TOP_MONEY_BANK]:
            # توب الفلوس
            top = db.get_top_money(10)
            kb = M([[B("🥷 توب الحرامية ➡️", callback_data="top:thieves")]])
            if not top:
                return await update.message.reply_text("📊 لا يوجد حسابات بعد.", reply_markup=kb)
            lines = ["🏆 *Bank Turbo - أغنى 10 أشخاص*\n"]
            medals = ["🥇","🥈","🥉"]
            for i, item in enumerate(top, 1):
                display = escape_html(item['first_name'] or "عضو")
                prefix = medals[i-1] if i <= 3 else f"{i}."
                lines.append(f"{prefix} {display} — *{fmt_money(item['balance'])}*")
            return await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_TOP_THIEVES_2]:
            # توب الحرامية
            top = db.get_top_thieves(10)
            kb = M([[B("🏆 توب الفلوس", callback_data="top:money")]])
            if not top:
                return await update.message.reply_text("📊 مفيش حرامية لسه 😅", reply_markup=kb)
            lines = ["🥷 *Bank Turbo - أكبر 10 حرامية*\n"]
            medals = ["🥇","🥈","🥉"]
            for i, item in enumerate(top, 1):
                display = escape_html(item['first_name'] or "عضو")
                prefix = medals[i-1] if i <= 3 else f"{i}."
                lines.append(f"{prefix} {display} — سرق *{fmt_money(item['total_stolen'])}*")
            return await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_POINTS_SYSTEM]:
            # نظام النقاط
            try:
                await update.message.reply_text(points_system_text(), parse_mode=ParseMode.MARKDOWN)
            except: pass
            return
        # ===== الزواج =====
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_MARRY]:
            return await cmd_marry(update, ctx, cid, uid)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_PARTNER]:
            return await cmd_partner(update, ctx, uid)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_DIVORCE]:
            return await cmd_divorce(update, ctx, uid)
        # ===== الأطفال =====
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_CHILD]:
            return await cmd_child(update, ctx, cid, uid)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_CHILD_INCOME]:
            return await cmd_child_income(update, ctx, uid)
        # ===== الممتلكات =====
        if any(normalize_text(text).startswith(normalize_text(t)) for t in ("اشتري", "اشتريت", "شراء")):
            return await cmd_buy_property(update, ctx, uid, text)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_SELL]:
            return await cmd_sell_property(update, ctx, uid)
        # ===== VIP =====
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_VIP_LIST]:
            return await cmd_vip_list(update, ctx, cid)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_VIP_ADD]:
            return await cmd_vip_add(update, ctx, cid, uid, user)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_VIP_REMOVE]:
            return await cmd_vip_remove(update, ctx, cid, uid)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_VIP_REMOVE_ALL]:
            return await cmd_vip_remove_all(update, ctx, cid, uid)
        # ===== الوقت =====
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_TIME]:
            return await cmd_time(update, ctx)
        # ===== النكتة =====
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_JOKE]:
            return await cmd_joke(update, ctx, uid)
        # ===== التذكيرات =====
        if normalize_text(text).startswith(normalize_text("ذكرني")) or normalize_text(text).startswith(normalize_text("فكرني")):
            return await cmd_remind(update, ctx, uid, text)
        # ===== بياناتي =====
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_MY_DATA]:
            return await cmd_my_data(update, ctx, cid, uid, user)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_MY_MONEY]:
            return await update.message.reply_text(
                await build_my_money_reply(cid, uid, user.first_name),
                parse_mode=ParseMode.MARKDOWN)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_HIS_MONEY] and update.message.reply_to_message:
            t = update.message.reply_to_message.from_user
            return await update.message.reply_text(
                await build_his_money_reply(cid, t.id, t.first_name),
                parse_mode=ParseMode.MARKDOWN)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_ID]:
            return await cmd_id(update, ctx)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_GAMES]:
            await handle_games_list(update, ctx, cid)
            return
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_COMMANDS]:
            await update.message.reply_text(
                commands_page_text(0),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=commands_kb(0))
            return
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_MUTED_LIST]:
            return await cmd_muted(update, ctx)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_BANNED_LIST]:
            return await cmd_banned(update, ctx)

    # 8) أوامر الأدمن النصية (مش لازم رد)
    if text and is_admin:
        await handle_admin_text(update, ctx, cid, uid, text, user)

    # 9) Bank Turbo triggers
    if text:
        await handle_bank_trigger(update, ctx, text)

# ===== الألعاب النشطة =====
async def handle_active_game_reply(update, ctx, cid, uid, text):
    game = active_games.get(cid)
    if not game:
        return
    gtype = game["type"]
    norm = normalize_text(text)
    unorm = normalize_emoji(text)
    name = update.effective_user.first_name
    if gtype == "number":
        try: guess = int(normalize_digits(text))
        except ValueError: return
        if guess == game["answer"]:
            db.add_points(cid, uid, 10, count_message=False)
            db.add_win(cid, uid)
            await update.message.reply_text(
                f"✅ صح *{escape_html(name)}* كسبت +10 جنية",
                parse_mode=ParseMode.MARKDOWN)
            active_games.pop(cid, None)
        elif guess < game["answer"]:
            try: await update.message.reply_text("🔽 أكبر!")
            except: pass
        else:
            try: await update.message.reply_text("🔼 أصغر!")
            except: pass
    elif gtype == "fastest":
        if norm == game["answer"]:
            db.add_points(cid, uid, 10, count_message=False)
            db.add_win(cid, uid)
            await update.message.reply_text(
                f"✅ صح *{escape_html(name)}* كسبت +10 جنية",
                parse_mode=ParseMode.MARKDOWN)
            active_games.pop(cid, None)
    elif gtype in ("scramble", "questions", "english", "calc", "pattern", "focus", "odd", "guess", "sort"):
        if norm == game["answer"]:
            db.add_points(cid, uid, 10, count_message=False)
            db.add_win(cid, uid)
            await update.message.reply_text(
                f"✅ صح *{escape_html(name)}* كسبت +10 جنية",
                parse_mode=ParseMode.MARKDOWN)
            active_games.pop(cid, None)
    elif gtype == "emoji":
        if unorm == game["answer"]:
            db.add_points(cid, uid, 10, count_message=False)
            db.add_win(cid, uid)
            await update.message.reply_text(
                f"✅ صح *{escape_html(name)}* كسبت +10 جنية",
                parse_mode=ParseMode.MARKDOWN)
            active_games.pop(cid, None)

# ===== أوامر اللعب النصية =====
async def handle_games_list(update, ctx, cid):
    """يعرض قائمة الألعاب المتاحة في الجروب"""
    text = (
        "🎮 *الألعاب المتاحة*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 *ألعاب سريعة (شخص واحد يكسب):*\n"
        "• خمن الرقم\n"
        "• الأسرع\n"
        "• رتب الحروف\n"
        "• احسب\n"
        "• الإيموجي\n"
        "• مؤقت\n"
        "• أسئلة عامة\n"
        "• إنجليزي\n"
        "• أكمل النمط\n"
        "• ركز\n"
        "• إيه المختلف\n"
        "• خمن الكلمة\n"
        "• ترتيب الأرقام\n"
        "• كت\n\n"
        "👥 *ألعاب جماعية (محتاجة لاعبين):*\n"
        "• الجاسوس / بكاسة\n"
        "• المافيا\n"
        "• القصة المبعثرة\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📌 *اكتب اسم اللعبة* عشان تبدأ 👇"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ===== نهاية handle_games_list =====

async def handle_game_trigger(update, ctx, cid, uid, text):
    norm = normalize_text(text)
    if not db.get_games_enabled(cid):
        return
    async def _start(func):
        # إلغاء أي لعبة قديمة
        old = active_games.pop(cid, None)
        if old and old.get("timeout_id"):
            old["timeout_id"].cancel()
        # بدء اللعبة الجديدة
        await func(ctx.bot, cid)
        # تخزين timeout الجديد
        if cid in active_games:
            tid = asyncio.create_task(_game_timeout(cid, active_games[cid].get("type")))
            active_games[cid]["timeout_id"] = tid
    # خمن الرقم
    if norm in ("خمن الرقم", "خمن رقم", "الرقم", "رقم"):
        return await _start(start_number_game)
    # الأسرع
    if norm in ("الأسرع", "الاسرع", "أسرع", "اسرع"):
        return await _start(start_fastest_game)
    # رتب الحروف
    if norm in ("رتب الحروف", "رتب حروف", "الحروف", "حروف"):
        return await _start(start_scramble_game)
    # أسئلة عامة — تطابق ذكي (بعد normalize: ئ→ي، ة→ه، أ→ا)
    # "أسئلة عامة" → "اسيله عامه"
    if norm in ("اسيله عامه", "اسيله", "سوال", "سئال", "اسال", "الاسيله", "الاسيله العامه", "اسئله عامه", "اسئله", "سؤال"):
        return await _start(start_questions_game)
    # إنجليزي
    if norm in ("إنجليزي", "انجليزي", "English", "english"):
        return await _start(start_english_game)
    # احسب
    if norm in ("احسب", "احسبلي", "حساب"):
        return await _start(start_calc_game)
    # مؤقت
    if norm in ("مؤقت", "المؤقت", "تايمر", "timer"):
        return await _start(start_timer_game)
    if norm in [normalize_text(t) for t in TRIGGER_EMOJI]:
        return await _start(start_emoji_game)
    if norm in [normalize_text(t) for t in TRIGGER_SPY]:
        return await start_spy_lobby(ctx.bot, cid)
    if norm in [normalize_text(t) for t in TRIGGER_KET]:
        return await _start(start_ket_game)
    if norm in [normalize_text(t) for t in TRIGGER_MAFIA]:
        return await start_mafia_lobby(ctx.bot, cid)
    if norm in [normalize_text(t) for t in TRIGGER_STORY]:
        return await start_story_lobby(ctx.bot, cid)
    if norm in [normalize_text(t) for t in TRIGGER_PATTERN]:
        return await _start(start_pattern_game)
    if norm in [normalize_text(t) for t in TRIGGER_FOCUS]:
        return await _start(start_focus_game)
    if norm in [normalize_text(t) for t in TRIGGER_ODD]:
        return await _start(start_odd_game)
    if norm in [normalize_text(t) for t in TRIGGER_GUESS]:
        return await _start(start_guess_game)
    if norm in [normalize_text(t) for t in TRIGGER_SORT]:
        return await _start(start_sort_game)

async def _game_timeout(cid, expected_type=None, timeout_id=None):
    await asyncio.sleep(60)
    game = active_games.get(cid)
    if not game:
        return
    # لو النوع مختلف، معناها لعبة جديدة بدأت — منقتلش
    if expected_type is not None and game.get("type") != expected_type:
        return
    # لو فيه timeout_id مختلف، معناها لعبة جديدة بدأت
    if timeout_id is not None and game.get("timeout_id") != timeout_id:
        return
    active_games.pop(cid, None)
    try:
        await _bot_instance.send_message(cid, "⏱ انتهى وقت اللعبة!")
    except: pass

# ===== أوامر الأدمن النصية =====
async def _delete_after(bot, chat_id, message_id, seconds):
    """يحذف رسالة بعد عدد ثواني"""
    await asyncio.sleep(seconds)
    try: await bot.delete_message(chat_id, message_id)
    except: pass

# ==================== الزواج ====================
async def cmd_marry(update, ctx, cid, uid):
    """زواج"""
    MARRIAGE_COST = db.get_bank_setting("marriage_cost", 5000)
    user = update.effective_user
    # نتأكد إنه مش متجوز
    cur = db.get_marriage(uid)
    if cur:
        partner = db.get_user(cur["partner_id"])
        name = partner["first_name"] if partner else f"عضو {cur['partner_id']}"
        return await update.message.reply_text(
            f"💍 إنت متجوز بالفعل!\nزوجك: {name}",
            parse_mode=ParseMode.MARKDOWN)
    # نتأكد من الفلوس
    acc = db.get_bank_account(uid)
    if not acc:
        return await update.message.reply_text(
            "⚠️ لازم تعمل حساب بنكي الأول: *إنشاء حساب بنكي*",
            parse_mode=ParseMode.MARKDOWN)
    if acc["balance"] < MARRIAGE_COST:
        return await update.message.reply_text(
            f"⚠️ محتاج *{fmt_money(MARRIAGE_COST)}* عشان تتجوز.\n"
            f"رصيدك: {fmt_money(acc['balance'])}",
            parse_mode=ParseMode.MARKDOWN)
    # نجيب الأعضاء في الجروب
    members = db.list_members(cid)
    # نشيل نفسه والمتجوزين
    available = []
    for m in members:
        if m["user_id"] == uid:
            continue
        if db.get_marriage(m["user_id"]):
            continue
        available.append(m)
    if not available:
        return await update.message.reply_text("⚠️ مفيش حد متاح للزواج في الجروب ده 😅")
    # نختار عشوائي
    chosen = random.choice(available)
    # نخصم الفلوس
    db.deduct_bank_money(uid, MARRIAGE_COST, "marriage")
    db.set_marriage(uid, chosen["user_id"])
    # نضيف نقاط للمتزوج الجديد
    await update.message.reply_text(
        f"💍 مبروك!\n\n"
        f"<a href=\"tg://user?id={uid}\">{escape_html(user.first_name)}</a> "
        f"اتجوز "
        f"<a href=\"tg://user?id={chosen['user_id']}\">{escape_html(chosen['first_name'])}</a>\n\n"
        f"💰 دفع *{fmt_money(MARRIAGE_COST)}*",
        parse_mode=ParseMode.HTML)


async def cmd_partner(update, ctx, uid):
    """زوجي / زوجتي"""
    m = db.get_marriage(uid)
    if not m:
        return await update.message.reply_text(
            "💔 إنت مش متجوز لسه.\nاكتب *زوجني* عشان تتجوز.",
            parse_mode=ParseMode.MARKDOWN)
    partner = db.get_user(m["partner_id"])
    if not partner:
        return await update.message.reply_text(f"💍 زوجك: عضو {m['partner_id']}")
    await update.message.reply_text(
        f"💍 زوجك هو: <a href=\"tg://user?id={m['partner_id']}\">{escape_html(partner['first_name'])}</a>",
        parse_mode=ParseMode.HTML)


async def cmd_divorce(update, ctx, uid):
    """طلاق"""
    DIVORCE_REFUND = db.get_bank_setting("divorce_refund", 3000)
    m = db.get_marriage(uid)
    if not m:
        return await update.message.reply_text("💔 إنت مش متجوز أساساً 😅")
    partner = m["partner_id"]
    # نشوف الأطفال قبل الطلاق
    my_children = db.get_children(uid)
    partner_children = db.get_children(partner)
    all_children = my_children + partner_children
    has_children = len(all_children) > 0
    # ننقل الأطفال عشوائي
    moved_info = []
    if has_children:
        # نجيب أسماء الطرفين
        u1 = db.get_user(uid)
        u2 = db.get_user(partner)
        n1 = u1["first_name"] if u1 else f"عضو {uid}"
        n2 = u2["first_name"] if u2 else f"عضو {partner}"
        # نقل عشوائي
        for k in all_children:
            new_owner = random.choice([uid, partner])
            try:
                db.transfer_children_random(uid, partner)
            except: pass
        # نعرض ملخص (مش كل طفل، بس العدد لكل واحد)
        kids_1 = db.count_children(uid)
        kids_2 = db.count_children(partner)
        moved_info.append(f"👶 *{n1}:* {kids_1} طفل")
        moved_info.append(f"👶 *{n2}:* {kids_2} طفل")
    # نعمل الطلاق
    db.divorce(uid)
    # نرجّع الفلوس
    acc = db.get_bank_account(uid)
    if acc:
        db.add_bank_money(uid, DIVORCE_REFUND, "divorce_refund")
    # نبني الرسالة
    text = (
        f"💔 *تم الطلاق*\n\n"
        f"💰 استرددت: *{fmt_money(DIVORCE_REFUND)}*"
    )
    if has_children:
        text += "\n\n👶 *توزيع الأطفال:*\n" + "\n".join(moved_info)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ==================== الأطفال ====================
async def cmd_child(update, ctx, cid, uid):
    """خلف طفل"""
    CHILD_COST = db.get_bank_setting("child_cost", 500)
    MAX_CHILDREN = db.get_bank_setting("max_children", 5)
    CHILD_COOLDOWN = db.get_bank_setting("child_cooldown", 86400)
    # لازم رد على الزوج/الزوجة
    if not update.message.reply_to_message:
        return await update.message.reply_text(
            "⚠️ لازم ترد على رسالة زوجك/زوجتك عشان تخلفوا 👶",
            parse_mode=ParseMode.MARKDOWN)
    target = update.message.reply_to_message.from_user
    if not target or target.is_bot:
        return await update.message.reply_text("⚠️ مستخدم غير صالح.")
    # نتأكد إنهم متجوزين
    m = db.get_marriage(uid)
    if not m or m["partner_id"] != target.id:
        return await update.message.reply_text(
            f"😔 حرام يا أخ!\n"
            f"إنت مش متجوز <a href=\"tg://user?id={target.id}\">{escape_html(target.first_name)}</a>\n\n"
            f"الخلفة بتحصل بين المتجوزين بس 💍",
            parse_mode=ParseMode.HTML)
    # نتأكد من الأطفال
    count = db.count_children(uid)
    if count >= MAX_CHILDREN:
        return await update.message.reply_text(
            f"⚠️ وصلت للحد الأقصى ({MAX_CHILDREN} أطفال).",
            parse_mode=ParseMode.MARKDOWN)
    # طفل واحد في اليوم
    today = int(time.time()) // 86400
    kids = db.get_children(uid)
    for k in kids:
        if k["born_at"] // 86400 == today:
            return await update.message.reply_text("⚠️ إنت خلفت طفل النهاردة! استنى بكرة.")
    # نتأكد من الفلوس
    acc = db.get_bank_account(uid)
    if not acc or acc["balance"] < CHILD_COST:
        return await update.message.reply_text(
            f"⚠️ محتاج *{fmt_money(CHILD_COST)}* عشان تخلف.",
            parse_mode=ParseMode.MARKDOWN)
    # نخصم ونضيف
    db.deduct_bank_money(uid, CHILD_COST, "child")
    db.add_child(uid, target.id)
    await update.message.reply_text(
        f"👶 مبروك!\n\n"
        f"اتولد طفل جديد لـ <a href=\"tg://user?id={uid}\">{escape_html(update.effective_user.first_name)}</a> "
        f"و <a href=\"tg://user?id={target.id}\">{escape_html(target.first_name)}</a>\n\n"
        f"💰 التكلفة: *{fmt_money(CHILD_COST)}*\n"
        f"👶 عندك {count+1} طفل",
        parse_mode=ParseMode.HTML)


async def cmd_child_income(update, ctx, uid):
    """رزق الأطفال"""
    CHILD_INCOME = db.get_bank_setting("child_income", 100)
    kids = db.get_children(uid)
    if not kids:
        return await update.message.reply_text("⚠️ ماعندكش أطفال لسه.")
    total = 0
    now = int(time.time())
    for k in kids:
        # كل ساعة
        if now - k["last_income"] >= 3600:
            total += CHILD_INCOME
            db.update_child_income(k["id"], now)
    if total == 0:
        return await update.message.reply_text("⏰ استنى شوية قبل ما تجيب رزق الأطفال تاني.")
    db.add_bank_money(uid, total, "child_income")
    await update.message.reply_text(
        f"👶 *رزق الأطفال*\n\n"
        f"عدد الأطفال: *{len(kids)}*\n"
        f"💰 كسبت: *{fmt_money(total)}*",
        parse_mode=ParseMode.MARKDOWN)

# ==================== الممتلكات ====================

PROP_NAMES = {
    "car": "🚗 عربية",
    "palace": "🏠 قصر",
    "tower": "🏢 برج",
    "island": "🏝 جزيرة",
    "plane": "✈️ طيارة",
}

PROP_ALIASES = {
    "عربية": "car", "عربيه": "car", "سيارة": "car", "سياره": "car",
    "قصر": "palace", "بيت": "palace",
    "برج": "tower", "عمارة": "tower", "عماره": "tower",
    "جزيرة": "island", "جزيره": "island",
    "طيارة": "plane", "طياره": "plane", "طائرة": "plane", "طايره": "plane",
}


async def cmd_buy_property(update, ctx, uid, text):
    """شراء ممتلكات"""
    PROP_COST = db.get_bank_setting("prop_cost", 1000)
    PROP_COOLDOWN = db.get_bank_setting("prop_cooldown", 600)
    # نلاقي اسم الممتلك
    norm = normalize_text(text)
    # نشيل "اشتري"
    for prefix in ["اشتري", "اشتريت", "شراء", "اشترى"]:
        if norm.startswith(normalize_text(prefix)):
            norm = norm[len(prefix):].strip()
            break
    # نلاقي النوع
    prop_type = None
    for alias, ptype in PROP_ALIASES.items():
        if normalize_text(alias) in norm:
            prop_type = ptype
            break
    if not prop_type:
        return await update.message.reply_text(
            "⚠️ اكتب نوع الممتلك:\n"
            "مثال: `اشتري عربية` أو `اشتري قصر`",
            parse_mode=ParseMode.MARKDOWN)
    # نتأكد من الفلوس
    acc = db.get_bank_account(uid)
    if not acc or acc["balance"] < PROP_COST:
        return await update.message.reply_text(
            f"⚠️ محتاج *{fmt_money(PROP_COST)}*.",
            parse_mode=ParseMode.MARKDOWN)
    # الكول داون
    props = db.list_properties(uid)
    if props:
        last = props[0]["bought_at"]
        elapsed = int(time.time()) - last
        if elapsed < PROP_COOLDOWN:
            remaining = PROP_COOLDOWN - elapsed
            return await update.message.reply_text(
                f"⏰ استنى *{fmt_time(remaining)}* قبل ما تشتري تاني.",
                parse_mode=ParseMode.MARKDOWN)
    # نخصم
    db.deduct_bank_money(uid, PROP_COST, "property")
    db.buy_property(uid, prop_type, PROP_COST)
    pname = PROP_NAMES.get(prop_type, prop_type)
    new_acc = db.get_bank_account(uid)
    await update.message.reply_text(
        f"✅ اشتريت *{pname}*!\n\n"
        f"💰 التكلفة: {fmt_money(PROP_COST)}\n"
        f"💵 رصيدك: {fmt_money(new_acc['balance'])}",
        parse_mode=ParseMode.MARKDOWN)


async def cmd_sell_property(update, ctx, uid):
    """بيع ممتلكات"""
    props = db.list_properties(uid)
    if not props:
        return await update.message.reply_text("⚠️ ماعندكش ممتلكات.")
    # نبيع آخر ممتلك
    last = props[0]
    result = db.sell_property(last["id"])
    if not result:
        return await update.message.reply_text("❌ فشل البيع.")
    # نضيف ربح من الإعدادات
    MIN_PCT = db.get_bank_setting("prop_sell_min", 1)
    MAX_PCT = db.get_bank_setting("prop_sell_max", 25)
    pct = random.randint(MIN_PCT, MAX_PCT)
    profit_pct = last["bought_price"] * pct // 100
    total = last["bought_price"] + profit_pct
    db.add_bank_money(uid, total, "sell_property")
    pname = PROP_NAMES.get(last["prop_type"], last["prop_type"])
    new_acc = db.get_bank_account(uid)
    await update.message.reply_text(
        f"✅ بعت *{pname}*!\n\n"
        f"💰 سعر الشراء: {fmt_money(last['bought_price'])}\n"
        f"📈 الربح: *+{pct}%* ({fmt_money(profit_pct)})\n"
        f"💵 الإجمالي: *{fmt_money(total)}*\n"
        f"🏦 رصيدك: {fmt_money(new_acc['balance'])}",
        parse_mode=ParseMode.MARKDOWN)


# ==================== VIP ====================
async def cmd_vip_list(update, ctx, cid):
    """قائمة VIP"""
    vips = db.list_vips(cid)
    if not vips:
        return await update.message.reply_text("📭 مفيش أعضاء مميزين لسه.")
    lines = [f"👑 *قائمة VIP* ({len(vips)})\n"]
    for uid in vips[:50]:
        u = db.get_user(uid)
        if u:
            lines.append(f"• <a href=\"tg://user?id={uid}\">{escape_html(u['first_name'])}</a>")
        else:
            lines.append(f"• عضو {uid}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_vip_add(update, ctx, cid, uid, user):
    """رفع مميز — للمالك/المشرف بس"""
    if not (is_owner(uid) or await is_user_admin(ctx.bot, cid, uid)):
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ لازم ترد على رسالة العضو.", parse_mode=ParseMode.MARKDOWN)
    target = update.message.reply_to_message.from_user
    if not target or target.is_bot:
        return
    db.add_vip(cid, target.id, uid)
    await update.message.reply_text(
        f"👑 تم رفع <a href=\"tg://user?id={target.id}\">{escape_html(target.first_name)}</a> مميز!",
        parse_mode=ParseMode.HTML)


async def cmd_vip_remove(update, ctx, cid, uid):
    """مسح مميز — للمالك/المشرف بس"""
    if not (is_owner(uid) or await is_user_admin(ctx.bot, cid, uid)):
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ لازم ترد على رسالة العضو.", parse_mode=ParseMode.MARKDOWN)
    target = update.message.reply_to_message.from_user
    db.remove_vip(cid, target.id)
    await update.message.reply_text(
        f"✅ تم إزالة التمييز عن <a href=\"tg://user?id={target.id}\">{escape_html(target.first_name)}</a>",
        parse_mode=ParseMode.HTML)


async def cmd_vip_remove_all(update, ctx, cid, uid):
    """مسح كل المميزين"""
    if not (is_owner(uid) or await is_user_admin(ctx.bot, cid, uid)):
        return
    count = db.remove_all_vips(cid)
    await update.message.reply_text(f"✅ تم مسح *{count}* عضو مميز.",
                                    parse_mode=ParseMode.MARKDOWN)


# ==================== الوقت ====================
async def cmd_time(update, ctx):
    """الوقت الحالي"""
    now = time.time()
    t = time.strftime("%H:%M:%S", time.localtime(now))
    d = time.strftime("%Y-%m-%d", time.localtime(now))
    await update.message.reply_text(
        f"🕐 *الوقت الحالي*\n\n"
        f"⏰ الساعة: *{t}*\n"
        f"📅 التاريخ: {d}",
        parse_mode=ParseMode.MARKDOWN)


# ==================== النكتة ====================
async def cmd_joke(update, ctx, uid):
    """نكتة"""
    JOKE_COOLDOWN = db.get_bank_setting("joke_cooldown", 600)
    now = int(time.time())
    last = db.get_last_joke_time(uid)
    if now - last < JOKE_COOLDOWN:
        remaining = JOKE_COOLDOWN - (now - last)
        return await update.message.reply_text(
            f"⏰ استنى *{fmt_time(remaining)}* قبل ما تطلب نكتة تاني.",
            parse_mode=ParseMode.MARKDOWN)
    # نجيب نكتة عشوائية
    j = db.get_random_joke()
    if not j:
        return await update.message.reply_text(
            "⚠️ مفيش نكت مسجلة. المالك يقدر يضيف نكت من إعدادات الألعاب.",
            parse_mode=ParseMode.MARKDOWN)
    db.set_joke_time(uid, now)
    await update.message.reply_text(f"😂 {j['text']}")

async def cmd_joke(update, ctx, uid):
    """نكتة"""
    now = int(time.time())
    last = db.get_last_joke_time(uid)
    if now - last < 600:  # 10 دقايق
        remaining = 600 - (now - last)
        return await update.message.reply_text(
            f"⏰ استنى *{fmt_time(remaining)}* قبل ما تطلب نكتة تاني.",
            parse_mode=ParseMode.MARKDOWN)
    db.set_joke_time(uid, now)
    joke = random.choice(JOKES)
    await update.message.reply_text(f"😂 {joke}")


# ==================== التذكيرات ====================
async def cmd_remind(update, ctx, uid, text):
    """ذكرني [حاجة]"""
    # الصيغ:
    # ذكرني بعد 5 دقايق [حاجة]
    # ذكرني بعد 2 ساعات [حاجة]
    # ذكرني بعد 30 ثانية [حاجة]
    # ذكرني [حاجة] (بعد ساعة افتراضي)
    body = text
    for prefix in ["ذكرني", "ذكرنى", "فكرني"]:
        if normalize_text(body).startswith(normalize_text(prefix)):
            body = body[len(prefix):].strip()
            break
    seconds = 3600  # افتراضي ساعة
    # نشوف لو فيه "بعد X دقيقة/ساعة/ثانية"
    m = re.match(r"بعد\s+(\d+)\s*(ثانية|ثانيه|ث|دقيقة|دقيقه|د|ساعة|ساعه|س|يوم|يومين|أيام|ايام)?", body)
    if m:
        n = int(normalize_digits(m.group(1)))
        unit = m.group(2) or "دقيقة"
        unit = unit.strip()
        if unit in ("ثانية", "ثانيه", "ث"):
            seconds = n
        elif unit in ("دقيقة", "دقيقه", "د"):
            seconds = n * 60
        elif unit in ("ساعة", "ساعه", "س"):
            seconds = n * 3600
        elif unit in ("يوم", "يومين", "أيام", "ايام"):
            seconds = n * 86400
        body = body[m.end():].strip()
    if not body:
        body = "تذكير"
    if seconds < 10:
        seconds = 10
    REMINDER_MAX = db.get_bank_setting("reminder_max", 604800)
    if seconds > REMINDER_MAX:
        seconds = REMINDER_MAX
    remind_at = int(time.time()) + seconds
    db.add_reminder(update.effective_chat.id, uid, body, remind_at)
    await update.message.reply_text(
        f"⏰ *تم التذكير*\n\n"
        f"📌 {body}\n"
        f"⏱ بعد: {fmt_time(seconds)}",
        parse_mode=ParseMode.MARKDOWN)


# ==================== بياناتي ====================
async def cmd_my_data(update, ctx, cid, uid, user):
    """بياناتي"""
    p = db.get_points(cid, uid)
    acc = db.get_bank_account(uid)
    balance = acc["balance"] if acc else 0
    rank = get_bank_rank(uid) or "غير مصنف"
    # الزواج
    m = db.get_marriage(uid)
    if m:
        partner = db.get_user(m["partner_id"])
        pname = partner["first_name"] if partner else f"عضو {m['partner_id']}"
        marriage_str = f"💍 متجوز: {pname}"
    else:
        marriage_str = "💔 أعزب"
    # الأطفال
    children = db.count_children(uid)
    # الممتلكات
    props = db.list_properties(uid)
    props_str = ""
    if props:
        counts = {}
        for p in props:
            counts[p["prop_type"]] = counts.get(p["prop_type"], 0) + 1
        for ptype, cnt in counts.items():
            props_str += f"  • {PROP_NAMES.get(ptype, ptype)} × {cnt}\n"
    else:
        props_str = "  📭 مفيش ممتلكات\n"
    # VIP
    vip_mark = " 👑" if db.is_vip(cid, uid) else ""
    text = (
        f"👤 *بياناتك*{vip_mark}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📛 الاسم: {escape_html(user.first_name or '')}\n"
        f"🆔 الآيدي: `{uid}`\n"
        f"👤 اليوزر: @{user.username or '—'}\n\n"
        f"{marriage_str}\n"
        f"👶 الأطفال: *{children}*\n\n"
        f"💰 الفلوس: *{fmt_money(balance)}*\n"
        f"🏆 الانتصارات: *{p['wins']}*\n"
        f"🏅 الترتيب العام: *#{rank}*\n\n"
        f"🏠 *الممتلكات:*\n{props_str}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def handle_admin_text(update, ctx, cid, uid, text, user):
    try:
        norm = normalize_text(text)
        # ===== أمر المسح/الحذف [رقم] — يحذف الرسايل + رسالة الأمر + رسالة النتيجة =====
        del_triggers = [normalize_text(t) for t in TRIGGER_DELETE]
        is_del_cmd = norm in del_triggers or any(norm.startswith(t + " ") or norm == t for t in del_triggers)
        if is_del_cmd:
            nums = re.findall(r"\d+", normalize_digits(text))
            has_reply = bool(update.message.reply_to_message)
            if nums and (norm.startswith(("مسح اخر", "مسح آخر", "حذف اخر", "حذف آخر", "امسح اخر", "امسح آخر", "احذف اخر", "احذف آخر")) or norm.startswith("اخر") or norm.startswith("آخر")):
                # حذف [رقم] رسالة
                n = int(nums[0])
                n = min(max(1, n), 100)
                chat_id = cid
                msg_id = update.message.message_id
                # نحذف رسالة الأمر
                try: await update.message.delete()
                except: pass
                # نحذف n رسالة قبل رسالة الأمر
                deleted = 0
                for i in range(1, n + 1):
                    try:
                        await ctx.bot.delete_message(chat_id, msg_id - i)
                        deleted += 1
                    except: pass
                # نبعت رسالة النتيجة ونحذفها
                try:
                    m = await ctx.bot.send_message(chat_id, f"🧹 تم مسح *{deleted}* رسالة.", parse_mode=ParseMode.MARKDOWN)
                    await asyncio.sleep(2)
                    try: await m.delete()
                    except: pass
                except: pass
                return
            elif has_reply:
                # حذف/مسح بالرد — رسالة الأمر + الرسالة المردود عليها (بدون نتيجة)
                try: await update.message.delete()
                except: pass
                try: await update.message.reply_to_message.delete()
                except: pass
                return
            else:
                # مفيش رد ومفيش رقم — نتجاهل (عشان الجملة العادية)
                return
        # ===== باقي الأوامر — محتاج رد =====
        if not update.message.reply_to_message:
            return
        target = update.message.reply_to_message.from_user
        if not target: return
        # حظر
        if norm in [normalize_text(t) for t in TRIGGER_BAN]:
            try: await ctx.bot.ban_chat_member(cid, target.id)
            except: pass
            return await update.message.reply_text(f"⛔ تم حظر {escape_html(target.first_name)}", parse_mode=ParseMode.MARKDOWN)
        if norm in [normalize_text(t) for t in TRIGGER_UNBAN]:
            try: await ctx.bot.unban_chat_member(cid, target.id)
            except: pass
            return await update.message.reply_text(f"✅ تم فك الحظر", parse_mode=ParseMode.MARKDOWN)
        # كتم
        if norm in [normalize_text(t) for t in TRIGGER_MUTE]:
            try:
                from telegram import ChatPermissions
                await ctx.bot.restrict_chat_member(cid, target.id, ChatPermissions(can_send_messages=False))
                db.add_muted(cid, target.id, target.first_name, uid)
            except: pass
            return await update.message.reply_text(f"🔇 تم كتم {escape_html(target.first_name)}", parse_mode=ParseMode.MARKDOWN)
        if norm in [normalize_text(t) for t in TRIGGER_UNMUTE]:
            try:
                from telegram import ChatPermissions
                await ctx.bot.restrict_chat_member(cid, target.id, ChatPermissions(
                    can_send_messages=True, can_send_media_messages=True,
                    can_send_other_messages=True, can_add_web_page_previews=True))
                db.remove_muted(cid, target.id)
            except: pass
            return await update.message.reply_text(f"🔊 تم فك الكتم", parse_mode=ParseMode.MARKDOWN)
        # تحذير
        if norm in [normalize_text(t) for t in TRIGGER_WARN]:
            cnt = db.add_warning(cid, target.id)
            if cnt >= 3:
                try:
                    from telegram import ChatPermissions
                    await ctx.bot.restrict_chat_member(cid, target.id, ChatPermissions(can_send_messages=False))
                    db.add_muted(cid, target.id, target.first_name, uid)
                except: pass
                return await update.message.reply_text(f"⚠️ {escape_html(target.first_name)} وصل 3 تحذيرات وتم كتمه.", parse_mode=ParseMode.MARKDOWN)
            return await update.message.reply_text(f"⚠️ تحذير {cnt}/3 لـ {escape_html(target.first_name)}", parse_mode=ParseMode.MARKDOWN)
        if norm in [normalize_text(t) for t in TRIGGER_UNWARN]:
            db.clear_warnings(cid, target.id)
            return await update.message.reply_text(f"✅ تم إلغاء التحذيرات", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        log.warning(f"handle_admin_text error: {e}")


async def handle_bank_trigger(update, ctx, text):
    norm = normalize_text(text)
    if norm in [normalize_text(t) for t in TRIGGER_BANK_CREATE]:
        return await cmd_bank_create(update, ctx)
    if norm in [normalize_text(t) for t in TRIGGER_BANK_DELETE]:
        return await cmd_bank_delete(update, ctx)
    if norm in [normalize_text(t) for t in TRIGGER_BANK_INFO]:
        return await cmd_bank_info(update, ctx)
    if norm in [normalize_text(t) for t in TRIGGER_MY_MONEY] and update.effective_chat.type == ChatType.PRIVATE:
        return await cmd_bank_money(update, ctx)
    if norm in [normalize_text(t) for t in TRIGGER_SALARY]:
        return await cmd_salary(update, ctx)
    if norm in [normalize_text(t) for t in TRIGGER_TIP]:
        return await cmd_tip(update, ctx)
    if norm in [normalize_text(t) for t in TRIGGER_TOP_MONEY]:
        return await cmd_top_money(update, ctx)
    if norm in [normalize_text(t) for t in TRIGGER_TOP_THIEVES]:
        return await cmd_top_thieves(update, ctx)
    # تحويل مبلغ
    m = re.match(r"^(?:تحويل|تحویل)\s+(\d+)", normalize_digits(text))
    if m and update.message.reply_to_message:
        return await cmd_transfer(update, ctx, int(m.group(1)))
    # سرقة
    if norm in [normalize_text(t) for t in TRIGGER_STEAL]:
        return await cmd_steal(update, ctx)
    # استثمار مبلغ
    m = re.match(r"^(?:استثمار|استثمر)\s+(\d+)", normalize_digits(text))
    if m:
        return await cmd_invest(update, ctx, int(m.group(1)))
    # حظ مبلغ
    m = re.match(r"^(?:حظ)\s+(\d+)", normalize_digits(text))
    if m:
        return await cmd_luck(update, ctx, int(m.group(1)))
    # إضافة/خصم فلوس بالرد (للمالك فقط)
    add_match = re.search(r"(?:إضافة|اضافة|إضافه|اضافه)\s+(\d+)", normalize_digits(text))
    deduct_match = re.search(r"(?:خصم|اخصم|أخصم)\s+(\d+)", normalize_digits(text))
    m = add_match or deduct_match
    if m:
        if not is_owner(update.effective_user.id):
            return
        if not update.message.reply_to_message:
            return await update.message.reply_text("⚠️ لازم ترد على رسالة الشخص.", parse_mode=ParseMode.MARKDOWN)
        target = update.message.reply_to_message.from_user
        if not target or target.is_bot:
            return await update.message.reply_text("⚠️ مستخدم غير صالح.")
        amount = int(m.group(1))
        if amount <= 0:
            return await update.message.reply_text("⚠️ اكتب مبلغ صحيح.")
        acc = db.get_bank_account(target.id)
        if not acc:
            return await update.message.reply_text(
                f"⚠️ {escape_html(target.first_name)} ماعندوش حساب بنكي.",
                parse_mode=ParseMode.MARKDOWN)
        if deduct_match:
            ok = db.deduct_bank_money(target.id, amount, "admin_deduct")
            if not ok:
                return await update.message.reply_text(
                    f"⚠️ {escape_html(target.first_name)} رصيده مش كافي.",
                    parse_mode=ParseMode.MARKDOWN)
            new_acc = db.get_bank_account(target.id)
            return await update.message.reply_text(
                f"✅ *تم خصم {fmt_money(amount)}*\n\n"
                f"👤 من: {escape_html(target.first_name)}\n"
                f"💵 رصيده الآن: *{fmt_money(new_acc['balance'])}*",
                parse_mode=ParseMode.MARKDOWN)
        else:
            db.add_bank_money(target.id, amount, "admin_add")
            new_acc = db.get_bank_account(target.id)
            return await update.message.reply_text(
                f"✅ *تم إضافة {fmt_money(amount)}*\n\n"
                f"👤 لـ: {escape_html(target.first_name)}\n"
                f"💵 رصيده الآن: *{fmt_money(new_acc['balance'])}*",
                parse_mode=ParseMode.MARKDOWN)
    # إضافة فلوس للمستخدم بالرد (للمالك فقط)
    m = re.match(r"^(?:إضافة|اضافة|إضافه|اضافه)\s+(\d+)\s*(?:جنيه|جنيهات|جنية|جنية|ج)?$", normalize_digits(text))
    if m:
        if not is_owner(update.effective_user.id):
            return
        if not update.message.reply_to_message:
            return await update.message.reply_text("⚠️ لازم ترد على رسالة الشخص اللي عاوز تضيفه فلوس.", parse_mode=ParseMode.MARKDOWN)
        target = update.message.reply_to_message.from_user
        if not target or target.is_bot:
            return await update.message.reply_text("⚠️ مستخدم غير صالح.")
        amount = int(m.group(1))
        if amount <= 0:
            return await update.message.reply_text("⚠️ اكتب مبلغ صحيح.")
        # نضيف للبنك
        acc = db.get_bank_account(target.id)
        if not acc:
            return await update.message.reply_text(f"⚠️ {escape_html(target.first_name)} ماعندوش حساب بنكي.")
        db.add_bank_money(target.id, amount, "admin_add")
        new_acc = db.get_bank_account(target.id)
        return await update.message.reply_text(
            f"✅ *تم إضافة {fmt_money(amount)}*\n\n"
            f"👤 لـ: {escape_html(target.first_name)}\n"
            f"💵 رصيده الآن: *{fmt_money(new_acc['balance'])}*",
            parse_mode=ParseMode.MARKDOWN)

# ===== on_private_msg =====
async def on_private_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user: return
    if update.effective_chat.type != ChatType.PRIVATE: return
    uid = update.effective_user.id
    u = update.effective_user
    text = update.message.text or ""

    # تسجيل المستخدم
    db.save_user(uid, u.first_name, u.username)

    # ملف (استعادة قاعدة بيانات)
    if update.message.document:
        if await handle_pending_document(update, ctx): return

    # النصوص المنتظرة
    if await handle_pending_text(update, ctx): return

    # /start
    if text.startswith("/start"):
        if not await require_sub(update, ctx): return
        return await update.message.reply_text(main_text(u),
            parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_kb(is_owner(uid)))

    # /stats
    if text.startswith("/stats"):
        return await cmd_stats(update, ctx)

    # /say
    if text.startswith("/say"):
        return await cmd_say(update, ctx)

    # /id
    if text.startswith("/id"):
        return await cmd_id(update, ctx)

    # id بدون شرطة
    if normalize_text(text) in [normalize_text(t) for t in TRIGGER_ID]:
        return await cmd_id(update, ctx)

    # أوامر البنك مش شغالة في الخاص (فقط الجروبات)
        # إحصائيات
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_MY_STATS]:
            return await update.message.reply_text(
                await build_my_stats_global_reply(uid, u.first_name),
                parse_mode=ParseMode.MARKDOWN)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_TOP]:
            return await update.message.reply_text(
                await build_global_top_reply(ctx.bot),
                parse_mode=ParseMode.MARKDOWN)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_GAMES]:
            return await update.message.reply_text(games_private_text(), parse_mode=ParseMode.MARKDOWN)
        if normalize_text(text) in [normalize_text(t) for t in TRIGGER_COMMANDS]:
            return await update.message.reply_text(commands_page_text(0), parse_mode=ParseMode.MARKDOWN,
                                                    reply_markup=commands_kb(0))

# ===== المهام الدورية =====
async def scheduled_messages_task(ctx: ContextTypes.DEFAULT_TYPE):
    """يبعت الرسائل المجدولة"""
    try:
        items = db.list_all_scheduled()
        now = int(time.time())
        for it in items:
            interval_sec = it["interval_min"] * 60
            if now - (it["last_sent"] or 0) >= interval_sec:
                try:
                    await ctx.bot.send_message(it["chat_id"], it["text"])
                    db.update_scheduled_last_sent(it["id"], now)
                except: pass
    except Exception as e:
        log.warning(f"scheduled_messages_task error: {e}")

async def cleanup_messages_task(ctx: ContextTypes.DEFAULT_TYPE):
    """يحذف الرسائل القديمة + يبعت المنشن الدوري"""
    try:
        # تنظيف الرسائل القديمة
        db.cleanup_old_messages(days=7)
    except Exception as e:
        log.warning(f"cleanup error: {e}")
    # المنشن الدوري — الأعضاء الحاليين بس
    try:
        items = db.list_enabled_periodic()
        now = int(time.time())
        for it in items:
            interval_sec = it["interval_min"] * 60
            if now - (it["last_sent"] or 0) >= interval_sec:
                cid = it["chat_id"]
                members = db.list_members(cid)
                if not members: continue
                # نتحقق من كل عضو — لو لسه موجود
                active_members = []
                for m in members:
                    try:
                        cm = await ctx.bot.get_chat_member(cid, m["user_id"])
                        if cm.status in ("creator", "administrator", "member", "restricted"):
                            active_members.append(m)
                        else:
                            # اتشال من الجروب — نمسحه
                            db.remove_member(cid, m["user_id"])
                    except Exception:
                        # العضو مش موجود — نمسحه
                        db.remove_member(cid, m["user_id"])
                if not active_members: continue
                sample = random.sample(active_members, min(it["mention_count"], len(active_members)))
                mentions = " ".join(f"[{escape_html(m['first_name'])}](tg://user?id={m['user_id']})" for m in sample)
                msg = (it["message"] + "\n\n" if it["message"] else "") + mentions
                try:
                    await ctx.bot.send_message(cid, msg, parse_mode=ParseMode.MARKDOWN)
                    db.update_periodic_last_sent(cid, now)
                except: pass
    except Exception as e:
        log.warning(f"mention error: {e}")

# ===== main() =====
def main():
    db.init_db()
    # إضافة القنوات الافتراضية لو أول مرة
    if not db.list_default_channels() and INITIAL_DEFAULT_CHANNELS:
        for ch_id in INITIAL_DEFAULT_CHANNELS:
            db.add_default_channel({"id": ch_id, "title": "القناة الرسمية", "username": None, "link": None})
    # بناء التطبيق
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(60.0)
        .read_timeout(60.0)
        .write_timeout(60.0)
        .pool_timeout(60.0)
        .get_updates_connect_timeout(60.0)
        .get_updates_read_timeout(60.0)
        .get_updates_write_timeout(60.0)
        .get_updates_pool_timeout(60.0)
        .build()
    )

    # دالة post_init لجلب BOT_USERNAME بعد التشغيل
    async def _post_init(app):
        global BOT_USERNAME
        try:
            me = await app.bot.get_me()
            BOT_USERNAME = me.username or ""
            log.info(f"Bot username: @{BOT_USERNAME}")
        except Exception as e:
            log.warning(f"فشل جلب username: {e}")

    application.post_init = _post_init

    # ===== الأوامر =====
    application.add_handler(CommandHandler("start", cmd_start))
    # (cmd_stats اتشال)
    application.add_handler(CommandHandler("commands", cmd_commands))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("say", cmd_say))
    application.add_handler(CommandHandler("id", cmd_id))
    application.add_handler(CommandHandler("muted", cmd_muted))
    application.add_handler(CommandHandler("banned", cmd_banned))
    # ===== الرسائل =====
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & ~filters.COMMAND & filters.TEXT,
        on_private_msg))
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.Document.ALL,
        on_private_msg))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.StatusUpdate.NEW_CHAT_MEMBERS,
        lambda u, c: send_welcome(c.bot, u.effective_chat.id, u.message.new_chat_members[0]) if u.message.new_chat_members else None))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & ~filters.COMMAND,
        on_group_msg))
    application.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    # ===== Callbacks =====
    # رئيسية
    application.add_handler(CallbackQueryHandler(cb_home, pattern=r"^panel:home$"))
    application.add_handler(CallbackQueryHandler(cb_games_menu, pattern=r"^games:menu$"))
    application.add_handler(CallbackQueryHandler(cb_bank_menu, pattern=r"^bank:menu$"))
    # بنك
    application.add_handler(CallbackQueryHandler(cb_bank_create_help, pattern=r"^bank:create_help$"))
    application.add_handler(CallbackQueryHandler(cb_bank_info_help, pattern=r"^bank:info_help$"))
    application.add_handler(CallbackQueryHandler(cb_bank_money_help, pattern=r"^bank:money_help$"))
    application.add_handler(CallbackQueryHandler(cb_bank_salary_help, pattern=r"^bank:salary_help$"))
    application.add_handler(CallbackQueryHandler(cb_bank_tip_help, pattern=r"^bank:tip_help$"))
    application.add_handler(CallbackQueryHandler(cb_bank_del_confirm, pattern=r"^bank:del_confirm:"))
    application.add_handler(CallbackQueryHandler(cb_bank_del_cancel, pattern=r"^bank:del_cancel:"))
    # إحصائيات
    application.add_handler(CallbackQueryHandler(cb_stats_me, pattern=r"^stats:me$"))
    application.add_handler(CallbackQueryHandler(cb_stats_top, pattern=r"^stats:top$"))
    application.add_handler(CallbackQueryHandler(cb_top_thieves, pattern=r"^top:thieves$"))
    application.add_handler(CallbackQueryHandler(cb_top_money_btn, pattern=r"^top:money$"))
    application.add_handler(CallbackQueryHandler(cb_top_vip, pattern=r"^top:vip$"))
    # أوامر
    application.add_handler(CallbackQueryHandler(cb_commands, pattern=r"^commands:show:"))
    # (cb_points_info اتشال)
    # اشتراك
    application.add_handler(CallbackQueryHandler(cb_sub_check, pattern=r"^sub:ck:"))
    # مالك
    application.add_handler(CallbackQueryHandler(cb_owner_menu, pattern=r"^owner:menu$"))
    application.add_handler(CallbackQueryHandler(cb_owner_stats, pattern=r"^owner:stats$"))
    application.add_handler(CallbackQueryHandler(cb_owner_devs, pattern=r"^owner:devs$"))
    application.add_handler(CallbackQueryHandler(cb_devs_add, pattern=r"^devs:add$"))
    application.add_handler(CallbackQueryHandler(cb_devs_del_list, pattern=r"^devs:del_list$"))
    application.add_handler(CallbackQueryHandler(cb_devs_del, pattern=r"^devs:del:"))
    application.add_handler(CallbackQueryHandler(cb_dev_perm_toggle, pattern=r"^devs:perm:"))
    application.add_handler(CallbackQueryHandler(cb_devs_perms_list, pattern=r"^devs:perms_list$"))
    application.add_handler(CallbackQueryHandler(cb_devs_perms, pattern=r"^devs:perms:"))
    application.add_handler(CallbackQueryHandler(cb_owner_bank, pattern=r"^owner:bank$"))
    application.add_handler(CallbackQueryHandler(cb_obank_salary, pattern=r"^obank:salary$"))
    application.add_handler(CallbackQueryHandler(cb_obank_marriage, pattern=r"^obank:marriage$"))
    application.add_handler(CallbackQueryHandler(cb_obank_children, pattern=r"^obank:children$"))
    application.add_handler(CallbackQueryHandler(cb_obank_props, pattern=r"^obank:props$"))
    application.add_handler(CallbackQueryHandler(cb_obank_tip, pattern=r"^obank:tip$"))
    application.add_handler(CallbackQueryHandler(cb_obank_steal, pattern=r"^obank:steal$"))
    application.add_handler(CallbackQueryHandler(cb_obank_invest, pattern=r"^obank:invest$"))
    application.add_handler(CallbackQueryHandler(cb_obank_luck, pattern=r"^obank:luck$"))
    application.add_handler(CallbackQueryHandler(cb_obank_set, pattern=r"^obank:set:"))
    application.add_handler(CallbackQueryHandler(cb_owner_gban, pattern=r"^owner:gban$"))
    application.add_handler(CallbackQueryHandler(cb_gban_add, pattern=r"^gban:add$"))
    application.add_handler(CallbackQueryHandler(cb_gban_show, pattern=r"^gban:show$"))
    application.add_handler(CallbackQueryHandler(cb_gban_del_list, pattern=r"^gban:del_list$"))
    application.add_handler(CallbackQueryHandler(cb_gban_del, pattern=r"^gban:del:"))
    application.add_handler(CallbackQueryHandler(cb_owner_db, pattern=r"^owner:db$"))
    application.add_handler(CallbackQueryHandler(cb_owner_db_export, pattern=r"^owner:db:export$"))
    application.add_handler(CallbackQueryHandler(cb_owner_db_import, pattern=r"^owner:db:import$"))
    application.add_handler(CallbackQueryHandler(cb_owner_subs, pattern=r"^owner:subs$"))
    application.add_handler(CallbackQueryHandler(cb_owner_add, pattern=r"^owner:add$"))
    application.add_handler(CallbackQueryHandler(cb_owner_show, pattern=r"^owner:show$"))
    application.add_handler(CallbackQueryHandler(cb_owner_del_list, pattern=r"^owner:del_list$"))
    application.add_handler(CallbackQueryHandler(cb_owner_del, pattern=r"^owner:del:"))
    application.add_handler(CallbackQueryHandler(cb_owner_cancel, pattern=r"^owner:cancel:"))
    application.add_handler(CallbackQueryHandler(cb_owner_allgroups, pattern=r"^owner:allgroups$"))
    application.add_handler(CallbackQueryHandler(cb_owner_goto, pattern=r"^owner:goto:"))
    application.add_handler(CallbackQueryHandler(cb_owner_open, pattern=r"^owner:open:"))
    application.add_handler(CallbackQueryHandler(cb_owner_data, pattern=r"^owner:data:"))
    application.add_handler(CallbackQueryHandler(cb_owner_broadcast, pattern=r"^owner:broadcast$"))
    application.add_handler(CallbackQueryHandler(cb_owner_ar, pattern=r"^owner:ar$"))
    application.add_handler(CallbackQueryHandler(cb_ar_add, pattern=r"^ar:add$"))
    application.add_handler(CallbackQueryHandler(cb_ar_show, pattern=r"^ar:show$"))
    application.add_handler(CallbackQueryHandler(cb_ar_del_list, pattern=r"^ar:del_list$"))
    application.add_handler(CallbackQueryHandler(cb_ar_del, pattern=r"^ar:del:"))
    application.add_handler(CallbackQueryHandler(cb_owner_jokes, pattern=r"^owner:jokes$"))
    application.add_handler(CallbackQueryHandler(cb_owner_reminders, pattern=r"^owner:reminders$"))
    application.add_handler(CallbackQueryHandler(cb_jokes_add, pattern=r"^jokes:add$"))
    application.add_handler(CallbackQueryHandler(cb_jokes_del_list, pattern=r"^jokes:del_list$"))
    application.add_handler(CallbackQueryHandler(cb_jokes_del, pattern=r"^jokes:del:"))
    application.add_handler(CallbackQueryHandler(cb_jokes_show, pattern=r"^jokes:show$"))
    application.add_handler(CallbackQueryHandler(cb_jokes_cooldown, pattern=r"^jokes:cooldown$"))
    application.add_handler(CallbackQueryHandler(cb_reminders_set, pattern=r"^reminders:set:"))
    application.add_handler(CallbackQueryHandler(cb_owner_games, pattern=r"^owner:games$"))
    application.add_handler(CallbackQueryHandler(cb_og_info, pattern=r"^og:info:"))
    application.add_handler(CallbackQueryHandler(cb_og_add, pattern=r"^og:add:"))
    application.add_handler(CallbackQueryHandler(cb_og_show, pattern=r"^og:show:"))
    application.add_handler(CallbackQueryHandler(cb_og_del_list, pattern=r"^og:del_list:"))
    application.add_handler(CallbackQueryHandler(cb_og_del, pattern=r"^og:del:"))
    application.add_handler(CallbackQueryHandler(cb_og_spy, pattern=r"^og:spy$"))
    application.add_handler(CallbackQueryHandler(cb_og_menu, pattern=r"^og:"))
    application.add_handler(CallbackQueryHandler(cb_spy_add_word, pattern=r"^spy:add_word$"))
    application.add_handler(CallbackQueryHandler(cb_spy_show, pattern=r"^spy:show$"))
    application.add_handler(CallbackQueryHandler(cb_spy_del_list, pattern=r"^spy:del_list$"))
    application.add_handler(CallbackQueryHandler(cb_spy_del, pattern=r"^spy:del:"))
    application.add_handler(CallbackQueryHandler(cb_spy_settings, pattern=r"^spy:settings$"))
    application.add_handler(CallbackQueryHandler(cb_spy_set, pattern=r"^spy:set:"))
    # المافيا/الجاسوس/القصة
    application.add_handler(CallbackQueryHandler(cb_spy_join, pattern=r"^spy:join:"))
    application.add_handler(CallbackQueryHandler(cb_spy_start, pattern=r"^spy:start:"))
    application.add_handler(CallbackQueryHandler(cb_spy_cancel, pattern=r"^spy:cancel:"))
    application.add_handler(CallbackQueryHandler(cb_spy_vote, pattern=r"^spy:vote:"))
    application.add_handler(CallbackQueryHandler(cb_story_join, pattern=r"^story:join:"))
    application.add_handler(CallbackQueryHandler(cb_story_start, pattern=r"^story:start:"))
    application.add_handler(CallbackQueryHandler(cb_story_cancel, pattern=r"^story:cancel:"))
    application.add_handler(CallbackQueryHandler(cb_story_vote, pattern=r"^story:vote:"))
    application.add_handler(CallbackQueryHandler(cb_mafia_join, pattern=r"^mafia:join:"))
    application.add_handler(CallbackQueryHandler(cb_mafia_start, pattern=r"^mafia:start:"))
    application.add_handler(CallbackQueryHandler(cb_mafia_cancel, pattern=r"^mafia:cancel:"))
    application.add_handler(CallbackQueryHandler(cb_mafia_kill, pattern=r"^mafia:kill:"))
    application.add_handler(CallbackQueryHandler(cb_mafia_check, pattern=r"^mafia:check:"))
    application.add_handler(CallbackQueryHandler(cb_mafia_vote, pattern=r"^mafia:vote:"))
    application.add_handler(CallbackQueryHandler(cb_timer_click, pattern=r"^timer:click:"))
    application.add_handler(CallbackQueryHandler(cb_guess_hint, pattern=r"^guess:hint:"))
    # لوحة المجموعة
    application.add_handler(CallbackQueryHandler(cb_panel_list, pattern=r"^panel:list$"))
    application.add_handler(CallbackQueryHandler(cb_panel_group, pattern=r"^panel:g:"))
    application.add_handler(CallbackQueryHandler(cb_panel_forget, pattern=r"^panel:forget:"))
    application.add_handler(CallbackQueryHandler(cb_panel_on, pattern=r"^panel:on:"))
    application.add_handler(CallbackQueryHandler(cb_panel_off, pattern=r"^panel:off:"))
    application.add_handler(CallbackQueryHandler(cb_panel_add, pattern=r"^panel:add:"))
    application.add_handler(CallbackQueryHandler(cb_panel_chs, pattern=r"^panel:chs:"))
    application.add_handler(CallbackQueryHandler(cb_panel_del, pattern=r"^panel:del:"))
    application.add_handler(CallbackQueryHandler(cb_protect_menu, pattern=r"^panel:protect:"))
    application.add_handler(CallbackQueryHandler(cb_protect_al, pattern=r"^protect:al:"))
    application.add_handler(CallbackQueryHandler(cb_protect_wl, pattern=r"^protect:wl:"))
    application.add_handler(CallbackQueryHandler(cb_protect_bw, pattern=r"^protect:bw:"))
    application.add_handler(CallbackQueryHandler(cb_protect_bwa, pattern=r"^protect:bwa:"))
    application.add_handler(CallbackQueryHandler(cb_protect_bwd, pattern=r"^protect:bwd:"))
    application.add_handler(CallbackQueryHandler(cb_protect_sched, pattern=r"^protect:sched:"))
    application.add_handler(CallbackQueryHandler(cb_sched_add, pattern=r"^sched:add:"))
    application.add_handler(CallbackQueryHandler(cb_sched_show, pattern=r"^sched:show:"))
    application.add_handler(CallbackQueryHandler(cb_sched_del_list, pattern=r"^sched:del_list:"))
    application.add_handler(CallbackQueryHandler(cb_sched_del, pattern=r"^sched:del:"))
    application.add_handler(CallbackQueryHandler(cb_protect_mention, pattern=r"^protect:mention:"))
    application.add_handler(CallbackQueryHandler(cb_mention_toggle, pattern=r"^mention:toggle:"))
    application.add_handler(CallbackQueryHandler(cb_mention_time, pattern=r"^mention:time:"))
    application.add_handler(CallbackQueryHandler(cb_mention_count, pattern=r"^mention:count:"))
    application.add_handler(CallbackQueryHandler(cb_mention_text, pattern=r"^mention:text:"))
    application.add_handler(CallbackQueryHandler(cb_data_members, pattern=r"^data:members:"))
    application.add_handler(CallbackQueryHandler(cb_data_member, pattern=r"^data:member:"))
    application.add_handler(CallbackQueryHandler(cb_data_messages, pattern=r"^data:messages:"))
    application.add_handler(CallbackQueryHandler(cb_data_media, pattern=r"^data:media:"))
    application.add_handler(CallbackQueryHandler(cb_data_type, pattern=r"^data:type:"))
    # المهام الدورية
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(scheduled_messages_task, interval=60, first=10)
        job_queue.run_repeating(cleanup_messages_task, interval=3600, first=60)
    print("✅ Laila Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()


