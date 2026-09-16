import os
import re
import time
import random
import sqlite3
from contextlib import closing

# DB_PATH بيتقرأ من Environment Variable لو موجود، وإلا بيستخدم "data.db" جنب الكود.
# على Railway: اعمل Volume واربطه بمسار زي /data، وحط DB_PATH=/data/data.db
# عشان الداتا متتمسحش كل ما تعمل ديبلوي جديد.
DB_PATH = os.environ.get("DB_PATH", "data.db")

# ==================== تطبيع النص ====================
def normalize_text(text):
    if not text: return ""
    t = text.strip().lower()
    t = re.sub(r'[\u064B-\u0652\u0670\u0640]', '', t)
    t = t.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    t = t.replace('ة', 'ه')
    t = t.replace('ى', 'ي')
    t = re.sub(r'^[\s\.,!؟?،؛;:\-_\*#@\u200f\u200e\u2600-\u27BF\U0001F000-\U0001FAFF\u2190-\u21FF\u2B00-\u2BFF\uFE0F\u200D]+', '', t)
    t = re.sub(r'[\s\.,!؟?،؛;:\-_\*#@\u200f\u200e\u2600-\u27BF\U0001F000-\U0001FAFF\u2190-\u21FF\u2B00-\u2BFF\uFE0F\u200D]+$', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def normalize_emoji(text):
    if not text: return ""
    return re.sub(r'\s+', '', text.strip())

# ==================== تطبيع الأرقام (عربي + إنجليزي) ====================
ARABIC_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

def normalize_digits(text):
    """يحوّل الأرقام العربية لإنجليزية"""
    if not text: return ""
    return text.translate(ARABIC_DIGITS)

def extract_number(text):
    """يستخرج رقم من النص (عربي أو إنجليزي)"""
    if not text: return None
    t = normalize_digits(str(text))
    m = re.search(r'-?\d+', t)
    if m: return int(m.group())
    return None

# ==================== الاتصال ====================
def _conn():
    return sqlite3.connect(DB_PATH, timeout=10)

def _atomic():
    """اتصال مع atomic transactions"""
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    return c

# ==================== إنشاء الجداول ====================
def init_db():
    with closing(_conn()) as c, c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY, title TEXT, activated INTEGER DEFAULT 0,
            activated_by INTEGER, activated_at INTEGER, welcome_enabled INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS channels (
            chat_id INTEGER, channel_id INTEGER, title TEXT, username TEXT, link TEXT,
            PRIMARY KEY (chat_id, channel_id)
        );
        CREATE TABLE IF NOT EXISTS default_channels (
            channel_id INTEGER PRIMARY KEY, title TEXT, username TEXT, link TEXT
        );
        CREATE TABLE IF NOT EXISTS pending (
            user_id INTEGER PRIMARY KEY, target_chat_id INTEGER, created_at INTEGER, extra TEXT
        );
        CREATE TABLE IF NOT EXISTS reminders (
            chat_id INTEGER, user_id INTEGER, last_reminder INTEGER, prompt_message_id INTEGER,
            PRIMARY KEY (chat_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS auto_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger TEXT NOT NULL,
            response TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS antilink (
            chat_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS banned_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            word TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS global_banned_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS points (
            chat_id INTEGER,
            user_id INTEGER,
            points INTEGER DEFAULT 0,
            messages INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS game_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game TEXT NOT NULL,
            content TEXT NOT NULL,
            answer TEXT
        );
        CREATE TABLE IF NOT EXISTS warnings (
            chat_id INTEGER,
            user_id INTEGER,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            last_seen INTEGER
        );
        CREATE TABLE IF NOT EXISTS game_settings (
            chat_id INTEGER PRIMARY KEY,
            games_enabled INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS group_members (
            chat_id INTEGER, user_id INTEGER, first_name TEXT, username TEXT,
            PRIMARY KEY (chat_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS known_members (
            chat_id INTEGER, user_id INTEGER,
            PRIMARY KEY (chat_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS group_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, user_id INTEGER, first_name TEXT,
            text TEXT, created_at INTEGER, message_id INTEGER,
            media_type TEXT
        );
        CREATE TABLE IF NOT EXISTS muted_members (
            chat_id INTEGER, user_id INTEGER, first_name TEXT,
            muted_by INTEGER, muted_at INTEGER,
            PRIMARY KEY (chat_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS scheduled_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, text TEXT, interval_min INTEGER,
            last_sent INTEGER, enabled INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS periodic_mentions (
            chat_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            interval_min INTEGER DEFAULT 60,
            mention_count INTEGER DEFAULT 5,
            message TEXT DEFAULT '',
            last_sent INTEGER
        );
        CREATE TABLE IF NOT EXISTS spy_settings (
            chat_id INTEGER PRIMARY KEY,
            min_players INTEGER DEFAULT 3,
            max_players INTEGER DEFAULT 10,
            discussion_sec INTEGER DEFAULT 180,
            voting_sec INTEGER DEFAULT 60
        );
        CREATE TABLE IF NOT EXISTS mafia_settings (
            chat_id INTEGER PRIMARY KEY,
            min_players INTEGER DEFAULT 5,
            max_players INTEGER DEFAULT 12,
            night_sec INTEGER DEFAULT 45,
            day_sec INTEGER DEFAULT 120,
            vote_sec INTEGER DEFAULT 60
        );
        -- ========== Bank Turbo ==========
        CREATE TABLE IF NOT EXISTS bank_accounts (
            user_id INTEGER PRIMARY KEY,
            account_number TEXT UNIQUE,
            balance INTEGER DEFAULT 0,
            last_salary INTEGER DEFAULT 0,
            last_tip INTEGER DEFAULT 0,
            last_steal INTEGER DEFAULT 0,
            last_invest INTEGER DEFAULT 0,
            last_luck INTEGER DEFAULT 0,
            total_stolen INTEGER DEFAULT 0,
            created_at INTEGER,
            first_name TEXT,
            username TEXT
        );
        CREATE TABLE IF NOT EXISTS bank_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER, to_id INTEGER,
            amount INTEGER, type TEXT,
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS bank_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)
        for alter in [
            "ALTER TABLE points ADD COLUMN wins INTEGER DEFAULT 0",
            "ALTER TABLE group_members ADD COLUMN username TEXT",
            "ALTER TABLE groups ADD COLUMN welcome_enabled INTEGER DEFAULT 1",
            "ALTER TABLE group_messages ADD COLUMN message_id INTEGER",
            "ALTER TABLE group_messages ADD COLUMN media_type TEXT",
        ]:
            try: c.execute(alter)
            except sqlite3.OperationalError: pass
        _init_bank_defaults(c)

def _init_bank_defaults(c):
    """القيم الافتراضية للبنك"""
    defaults = {
        "salary_amount": "500",
        "salary_cooldown": "43200",
        "tip_amount": "50",
        "tip_cooldown": "10800",
        "steal_success": "40",
        "steal_fine": "50",
        "steal_min": "50",
        "steal_max": "300",
        "steal_cooldown": "600",
        "invest_min_pct": "1",
        "invest_max_pct": "15",
        "invest_cooldown": "900",
        "luck_win_pct": "45",
        "luck_cooldown": "900",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO bank_settings(key,value) VALUES(?,?)", (k, v))

# ==================== المجموعات ====================
def remember_group(cid, title):
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO groups(chat_id,title) VALUES(?,?) ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title", (cid, title))

def forget_group(cid):
    with closing(_conn()) as c, c:
        for tbl in ("groups","channels","antilink","banned_words","game_settings",
                    "spy_settings","mafia_settings","scheduled_messages",
                    "periodic_mentions","muted_members","group_messages"):
            c.execute(f"DELETE FROM {tbl} WHERE chat_id=?", (cid,))

def get_group(cid):
    with closing(_conn()) as c:
        r = c.execute("SELECT chat_id,title,activated,activated_by,activated_at,welcome_enabled FROM groups WHERE chat_id=?", (cid,)).fetchone()
        if not r: return None
        return {"chat_id":r[0],"title":r[1],"activated":bool(r[2]),
                "activated_by":r[3],"activated_at":r[4],
                "welcome_enabled":bool(r[5]) if len(r) > 5 else True}

def list_groups():
    with closing(_conn()) as c:
        return [{"chat_id":r[0],"title":r[1],"activated":bool(r[2])} for r in c.execute("SELECT chat_id,title,activated FROM groups")]

def activate_group(cid, by):
    with closing(_conn()) as c, c:
        c.execute("UPDATE groups SET activated=1,activated_by=?,activated_at=? WHERE chat_id=?", (by, int(time.time()), cid))

def deactivate_group(cid):
    with closing(_conn()) as c, c:
        c.execute("UPDATE groups SET activated=0 WHERE chat_id=?", (cid,))

def set_welcome(cid, enabled):
    with closing(_conn()) as c, c:
        c.execute("UPDATE groups SET welcome_enabled=? WHERE chat_id=?", (1 if enabled else 0, cid))

def count_active_groups():
    """عدد الجروبات المفعلة"""
    with closing(_conn()) as c:
        return c.execute("SELECT COUNT(*) FROM groups WHERE activated=1").fetchone()[0]

def count_all_groups():
    """عدد كل الجروبات"""
    with closing(_conn()) as c:
        return c.execute("SELECT COUNT(*) FROM groups").fetchone()[0]

def count_groups():
    with closing(_conn()) as c:
        return c.execute("SELECT COUNT(*) FROM groups").fetchone()[0]

def count_users():
    with closing(_conn()) as c:
        return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]

# ==================== إعدادات الألعاب ====================
def get_games_enabled(chat_id):
    with closing(_conn()) as c:
        r = c.execute("SELECT games_enabled FROM game_settings WHERE chat_id=?", (chat_id,)).fetchone()
        return bool(r[0]) if r else True

def set_games_enabled(chat_id, enabled):
    with closing(_conn()) as c, c:
        c.execute("INSERT OR REPLACE INTO game_settings(chat_id,games_enabled) VALUES(?,?)",
                  (chat_id, 1 if enabled else 0))

# ==================== إعدادات الجاسوس ====================
def get_spy_settings(chat_id):
    with closing(_conn()) as c:
        r = c.execute("SELECT min_players,max_players,discussion_sec,voting_sec FROM spy_settings WHERE chat_id=?", (chat_id,)).fetchone()
    if r:
        return {"min_players":r[0],"max_players":r[1],"discussion_sec":r[2],"voting_sec":r[3]}
    return {"min_players":3,"max_players":10,"discussion_sec":180,"voting_sec":60}

def set_spy_setting(chat_id, key, value):
    allowed = {"min_players","max_players","discussion_sec","voting_sec"}
    if key not in allowed: return
    with closing(_conn()) as c, c:
        r = c.execute("SELECT chat_id FROM spy_settings WHERE chat_id=?", (chat_id,)).fetchone()
        if not r:
            c.execute("INSERT INTO spy_settings(chat_id) VALUES(?)", (chat_id,))
        c.execute(f"UPDATE spy_settings SET {key}=? WHERE chat_id=?", (value, chat_id))

# ==================== إعدادات المافيا ====================
def get_mafia_settings(chat_id):
    with closing(_conn()) as c:
        r = c.execute("SELECT min_players,max_players,night_sec,day_sec,vote_sec FROM mafia_settings WHERE chat_id=?", (chat_id,)).fetchone()
    if r:
        return {"min_players":r[0],"max_players":r[1],"night_sec":r[2],"day_sec":r[3],"vote_sec":r[4]}
    return {"min_players":5,"max_players":12,"night_sec":45,"day_sec":120,"vote_sec":60}

def set_mafia_setting(chat_id, key, value):
    allowed = {"min_players","max_players","night_sec","day_sec","vote_sec"}
    if key not in allowed: return
    with closing(_conn()) as c, c:
        r = c.execute("SELECT chat_id FROM mafia_settings WHERE chat_id=?", (chat_id,)).fetchone()
        if not r:
            c.execute("INSERT INTO mafia_settings(chat_id) VALUES(?)", (chat_id,))
        c.execute(f"UPDATE mafia_settings SET {key}=? WHERE chat_id=?", (value, chat_id))

# ==================== القنوات ====================
def add_channel(cid, ch):
    with closing(_conn()) as c, c:
        c.execute("INSERT OR REPLACE INTO channels(chat_id,channel_id,title,username,link) VALUES(?,?,?,?,?)",
                  (cid, ch["id"], ch.get("title"), ch.get("username"), ch.get("link")))

def remove_channel(cid, chid):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM channels WHERE chat_id=? AND channel_id=?", (cid, chid))

def list_channels(cid):
    with closing(_conn()) as c:
        return [{"channel_id":r[0],"title":r[1],"username":r[2],"link":r[3]} for r in
                c.execute("SELECT channel_id,title,username,link FROM channels WHERE chat_id=?", (cid,))]

def count_channels(cid):
    with closing(_conn()) as c:
        return c.execute("SELECT COUNT(*) FROM channels WHERE chat_id=?", (cid,)).fetchone()[0]

def add_default_channel(ch):
    with closing(_conn()) as c, c:
        c.execute("INSERT OR REPLACE INTO default_channels(channel_id,title,username,link) VALUES(?,?,?,?)",
                  (ch["id"], ch.get("title"), ch.get("username"), ch.get("link")))

def remove_default_channel(chid):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM default_channels WHERE channel_id=?", (chid,))

def list_default_channels():
    with closing(_conn()) as c:
        return [{"channel_id":r[0],"title":r[1],"username":r[2],"link":r[3]} for r in
                c.execute("SELECT channel_id,title,username,link FROM default_channels")]

# ==================== Pending ====================
def set_pending(uid, target, extra=None):
    with closing(_conn()) as c, c:
        c.execute("INSERT OR REPLACE INTO pending(user_id,target_chat_id,created_at,extra) VALUES(?,?,?,?)",
                  (uid, target, int(time.time()*1000), extra))

def get_pending(uid):
    with closing(_conn()) as c:
        r = c.execute("SELECT target_chat_id,created_at,extra FROM pending WHERE user_id=?", (uid,)).fetchone()
        return {"target_chat_id":r[0],"created_at":r[1],"extra":r[2]} if r else None

def clear_pending(uid):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM pending WHERE user_id=?", (uid,))

# ==================== Reminders ====================
def get_reminder(cid, uid):
    with closing(_conn()) as c:
        r = c.execute("SELECT last_reminder,prompt_message_id FROM reminders WHERE chat_id=? AND user_id=?", (cid, uid)).fetchone()
        return {"last_reminder":r[0],"prompt_message_id":r[1]} if r else None

def set_reminder(cid, uid, pmid):
    with closing(_conn()) as c, c:
        c.execute("INSERT OR REPLACE INTO reminders(chat_id,user_id,last_reminder,prompt_message_id) VALUES(?,?,?,?)",
                  (cid, uid, int(time.time()*1000), pmid))

def clear_reminder(cid, uid):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM reminders WHERE chat_id=? AND user_id=?", (cid, uid))

# ==================== الردود التلقائية ====================
def add_auto_reply(trigger, response):
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO auto_replies(trigger,response) VALUES(?,?)", (trigger, response))

def remove_auto_reply(reply_id):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM auto_replies WHERE id=?", (reply_id,))

def list_auto_replies():
    with closing(_conn()) as c:
        return [{"id":r[0],"trigger":r[1],"response":r[2]} for r in
                c.execute("SELECT id,trigger,response FROM auto_replies ORDER BY trigger,id")]

def auto_reply_exists(trigger, response):
    norm_t = normalize_text(trigger)
    norm_r = normalize_text(response)
    if not norm_t or not norm_r: return False
    with closing(_conn()) as c:
        rows = c.execute("SELECT trigger, response FROM auto_replies").fetchall()
    for (t, r) in rows:
        if normalize_text(t) == norm_t and normalize_text(r) == norm_r:
            return True
    return False

# ==================== الحماية ====================
def get_antilink(chat_id):
    with closing(_conn()) as c:
        r = c.execute("SELECT enabled FROM antilink WHERE chat_id=?", (chat_id,)).fetchone()
        return bool(r[0]) if r else False

def set_antilink(chat_id, enabled):
    with closing(_conn()) as c, c:
        c.execute("INSERT OR REPLACE INTO antilink(chat_id,enabled) VALUES(?,?)", (chat_id, 1 if enabled else 0))

def add_banned_word(chat_id, word):
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO banned_words(chat_id,word) VALUES(?,?)", (chat_id, word))

def remove_banned_word(word_id):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM banned_words WHERE id=?", (word_id,))

def list_banned_words(chat_id):
    with closing(_conn()) as c:
        return [{"id":r[0],"word":r[1]} for r in
                c.execute("SELECT id,word FROM banned_words WHERE chat_id=? ORDER BY id", (chat_id,))]

def find_banned_word(chat_id, text):
    if not text: return None
    clean = re.sub(r'[\.,!؟?،؛;:\-_\*#@\(\)\[\]\{\}\"\'`~\+\=\|\\/<>«»…]', ' ', text)
    clean = " " + clean.lower() + " "
    clean = re.sub(r'\s+', ' ', clean)
    with closing(_conn()) as c:
        rows = c.execute("SELECT word FROM banned_words WHERE chat_id=?", (chat_id,)).fetchall()
    for (w,) in rows:
        wl = w.lower().strip()
        if not wl: continue
        if f" {wl} " in clean: return w
    return None

def banned_word_exists(chat_id, word):
    norm = normalize_text(word)
    if not norm: return False
    with closing(_conn()) as c:
        rows = c.execute("SELECT word FROM banned_words WHERE chat_id=?", (chat_id,)).fetchall()
    for (w,) in rows:
        if normalize_text(w) == norm: return True
    return False

# ==================== كلمات محظورة عامة ====================
def add_global_banned_word(word):
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO global_banned_words(word) VALUES(?)", (word,))

def remove_global_banned_word(word_id):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM global_banned_words WHERE id=?", (word_id,))

def list_global_banned_words():
    with closing(_conn()) as c:
        return [{"id":r[0],"word":r[1]} for r in
                c.execute("SELECT id,word FROM global_banned_words ORDER BY id")]

def global_banned_word_exists(word):
    norm = normalize_text(word)
    if not norm: return False
    with closing(_conn()) as c:
        rows = c.execute("SELECT word FROM global_banned_words").fetchall()
    for (w,) in rows:
        if normalize_text(w) == norm: return True
    return False

def find_global_banned_word(text):
    if not text: return None
    clean = re.sub(r'[\.,!؟?،؛;:\-_\*#@\(\)\[\]\{\}\"\'`~\+\=\|\\/<>«»…]', ' ', text)
    clean = " " + clean.lower() + " "
    clean = re.sub(r'\s+', ' ', clean)
    with closing(_conn()) as c:
        rows = c.execute("SELECT word FROM global_banned_words").fetchall()
    for (w,) in rows:
        wl = w.lower().strip()
        if not wl: continue
        if f" {wl} " in clean: return w
    return None

# ==================== النقاط ====================
def add_points(chat_id, user_id, amount, count_message=True):
    with closing(_conn()) as c, c:
        r = c.execute("SELECT points,messages,wins FROM points WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
        if r:
            new_p = r[0] + amount
            new_m = r[1] + (1 if count_message else 0)
            c.execute("UPDATE points SET points=?,messages=? WHERE chat_id=? AND user_id=?", (new_p, new_m, chat_id, user_id))
        else:
            c.execute("INSERT INTO points(chat_id,user_id,points,messages,wins) VALUES(?,?,?,?,0)",
                      (chat_id, user_id, amount, 1 if count_message else 0))

def add_win(chat_id, user_id):
    with closing(_conn()) as c, c:
        r = c.execute("SELECT points,messages,wins FROM points WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
        if r:
            c.execute("UPDATE points SET wins=wins+1 WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        else:
            c.execute("INSERT INTO points(chat_id,user_id,points,messages,wins) VALUES(?,?,0,0,1)",
                      (chat_id, user_id))

def get_points(chat_id, user_id):
    with closing(_conn()) as c:
        r = c.execute("SELECT points,messages,wins FROM points WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
        return {"points":r[0],"messages":r[1],"wins":r[2]} if r else {"points":0,"messages":0,"wins":0}

def get_top(chat_id, limit=10):
    with closing(_conn()) as c:
        return [{"user_id":r[0],"points":r[1],"messages":r[2]} for r in
                c.execute("SELECT user_id,points,messages FROM points WHERE chat_id=? ORDER BY points DESC LIMIT ?", (chat_id, limit))]

def get_global_top(limit=10):
    with closing(_conn()) as c:
        rows = c.execute(
            "SELECT user_id, SUM(points) as total_p, SUM(messages) as total_m "
            "FROM points GROUP BY user_id ORDER BY total_p DESC LIMIT ?",
            (limit,)).fetchall()
    return [{"user_id":r[0],"points":r[1],"messages":r[2]} for r in rows]

def get_total_points(user_id):
    with closing(_conn()) as c:
        r = c.execute("SELECT SUM(points),SUM(messages),SUM(wins) FROM points WHERE user_id=?", (user_id,)).fetchone()
        return {"points":r[0] or 0,"messages":r[1] or 0,"wins":r[2] or 0}

def get_user_rank_global(user_id):
    with closing(_conn()) as c:
        rows = c.execute("SELECT user_id, SUM(points) as total FROM points GROUP BY user_id ORDER BY total DESC").fetchall()
    for i, (uid, _) in enumerate(rows, 1):
        if uid == user_id: return i
    return None

def get_user_rank_group(chat_id, user_id):
    with closing(_conn()) as c:
        rows = c.execute("SELECT user_id FROM points WHERE chat_id=? ORDER BY points DESC", (chat_id,)).fetchall()
    for i, (uid,) in enumerate(rows, 1):
        if uid == user_id: return i
    return None

# ==================== الألعاب ====================
def add_game_content(game, content, answer=None):
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO game_words(game,content,answer) VALUES(?,?,?)", (game, content, answer))

def remove_game_content(item_id):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM game_words WHERE id=?", (item_id,))

def list_game_content(game):
    with closing(_conn()) as c:
        return [{"id":r[0],"content":r[1],"answer":r[2]} for r in
                c.execute("SELECT id,content,answer FROM game_words WHERE game=? ORDER BY id", (game,))]

def count_game_content(game):
    with closing(_conn()) as c:
        return c.execute("SELECT COUNT(*) FROM game_words WHERE game=?", (game,)).fetchone()[0]

def game_content_exists(game, content):
    norm = normalize_text(content)
    if not norm: return False
    with closing(_conn()) as c:
        rows = c.execute("SELECT content FROM game_words WHERE game=?", (game,)).fetchall()
    for (ct,) in rows:
        if normalize_text(ct) == norm: return True
    return False

def count_all_games():
    with closing(_conn()) as c:
        r = c.execute("SELECT COUNT(DISTINCT game) FROM game_words").fetchone()
        return r[0] if r else 0

# ==================== التحذيرات ====================
def add_warning(chat_id, user_id):
    with closing(_conn()) as c, c:
        r = c.execute("SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
        if r:
            new_count = r[0] + 1
            c.execute("UPDATE warnings SET count=? WHERE chat_id=? AND user_id=?", (new_count, chat_id, user_id))
            return new_count
        else:
            c.execute("INSERT INTO warnings(chat_id,user_id,count) VALUES(?,?,1)", (chat_id, user_id))
            return 1

def get_warnings(chat_id, user_id):
    with closing(_conn()) as c:
        r = c.execute("SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
        return r[0] if r else 0

def clear_warnings(chat_id, user_id):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))

# ==================== المستخدمين ====================
def save_user(uid, first_name, username):
    with closing(_conn()) as c, c:
        r = c.execute("SELECT user_id FROM users WHERE user_id=?", (uid,)).fetchone()
        if not r:
            c.execute("INSERT INTO users(user_id,first_name,username,last_seen) VALUES(?,?,?,?)",
                      (uid, first_name, username, int(time.time())))
        else:
            c.execute("UPDATE users SET first_name=?,username=?,last_seen=? WHERE user_id=?",
                      (first_name, username, int(time.time()), uid))

def get_user(uid):
    with closing(_conn()) as c:
        r = c.execute("SELECT user_id,first_name,username FROM users WHERE user_id=?", (uid,)).fetchone()
        return {"user_id":r[0],"first_name":r[1],"username":r[2]} if r else None

def find_user_by_identifier(identifier):
    """يبحث عن مستخدم بـ username أو ID"""
    if not identifier: return None
    ident = str(identifier).strip()
    if ident.startswith("@"):
        ident = ident[1:]
    with closing(_conn()) as c:
        # ID
        if ident.isdigit():
            r = c.execute("SELECT user_id,first_name,username FROM users WHERE user_id=?", (int(ident),)).fetchone()
            if r: return {"user_id":r[0],"first_name":r[1],"username":r[2]}
        # Username
        r = c.execute("SELECT user_id,first_name,username FROM users WHERE LOWER(username)=LOWER(?)", (ident,)).fetchone()
        if r: return {"user_id":r[0],"first_name":r[1],"username":r[2]}
    return None

# ==================== أعضاء الجروبات ====================
def save_member(chat_id, user_id, first_name, username=None):
    with closing(_conn()) as c, c:
        c.execute("INSERT OR REPLACE INTO group_members(chat_id,user_id,first_name,username) VALUES(?,?,?,?)",
                  (chat_id, user_id, first_name, username))

def list_members(chat_id):
    with closing(_conn()) as c:
        return [{"user_id":r[0],"first_name":r[1],"username":r[2]} for r in
                c.execute("SELECT user_id,first_name,username FROM group_members WHERE chat_id=?", (chat_id,))]

def remove_member(chat_id, user_id):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM group_members WHERE chat_id=? AND user_id=?", (chat_id, user_id))

def get_member(chat_id, user_id):
    with closing(_conn()) as c:
        r = c.execute("SELECT first_name,username FROM group_members WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
        return {"first_name":r[0],"username":r[1]} if r else None

def is_known_member(chat_id, user_id):
    with closing(_conn()) as c:
        r = c.execute("SELECT 1 FROM known_members WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
        return bool(r)

def mark_known_member(chat_id, user_id):
    with closing(_conn()) as c, c:
        c.execute("INSERT OR IGNORE INTO known_members(chat_id,user_id) VALUES(?,?)", (chat_id, user_id))

# ==================== رسائل الجروبات ====================
def save_message(chat_id, user_id, first_name, text, message_id=None, media_type=None):
    if not text and not media_type: return
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO group_messages(chat_id,user_id,first_name,text,created_at,message_id,media_type) VALUES(?,?,?,?,?,?,?)",
                  (chat_id, user_id, first_name, (text or "")[:500], int(time.time()), message_id, media_type))

def list_media_messages(chat_id, media_type=None, limit=50):
    """يرجع رسايل الوسائط (بـ message_id)"""
    with closing(_conn()) as c:
        if media_type:
            rows = c.execute(
                "SELECT message_id, user_id, first_name, media_type, created_at FROM group_messages "
                "WHERE chat_id=? AND media_type=? AND message_id IS NOT NULL "
                "ORDER BY id DESC LIMIT ?",
                (chat_id, media_type, limit)).fetchall()
        else:
            rows = c.execute(
                "SELECT message_id, user_id, first_name, media_type, created_at FROM group_messages "
                "WHERE chat_id=? AND media_type IS NOT NULL AND message_id IS NOT NULL "
                "ORDER BY id DESC LIMIT ?",
                (chat_id, limit)).fetchall()
    return [{"message_id":r[0],"user_id":r[1],"first_name":r[2],"media_type":r[3],"created_at":r[4]} for r in rows]


def count_media_messages(chat_id, media_type=None):
    """عدد رسايل الوسائط"""
    with closing(_conn()) as c:
        if media_type:
            r = c.execute(
                "SELECT COUNT(*) FROM group_messages WHERE chat_id=? AND media_type=? AND message_id IS NOT NULL",
                (chat_id, media_type)).fetchone()
        else:
            r = c.execute(
                "SELECT COUNT(*) FROM group_messages WHERE chat_id=? AND media_type IS NOT NULL AND message_id IS NOT NULL",
                (chat_id,)).fetchone()
    return r[0] if r else 0

def list_messages(chat_id, limit=50):
    with closing(_conn()) as c:
        rows = c.execute("SELECT user_id,first_name,text,created_at FROM group_messages WHERE chat_id=? ORDER BY id DESC LIMIT ?", (chat_id, limit)).fetchall()
    return [{"user_id":r[0],"first_name":r[1],"text":r[2],"created_at":r[3]} for r in rows]

def cleanup_old_messages(days=7):
    cutoff = int(time.time()) - (days * 24 * 60 * 60)
    with closing(_conn()) as c, c:
        cur = c.execute("DELETE FROM group_messages WHERE created_at < ?", (cutoff,))
        return cur.rowcount

# ==================== المكتومين ====================
def add_muted(chat_id, user_id, first_name, muted_by):
    with closing(_conn()) as c, c:
        c.execute("INSERT OR REPLACE INTO muted_members(chat_id,user_id,first_name,muted_by,muted_at) VALUES(?,?,?,?,?)",
                  (chat_id, user_id, first_name, muted_by, int(time.time())))

def remove_muted(chat_id, user_id):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM muted_members WHERE chat_id=? AND user_id=?", (chat_id, user_id))

def list_muted(chat_id):
    with closing(_conn()) as c:
        return [{"user_id":r[0],"first_name":r[1]} for r in
                c.execute("SELECT user_id,first_name FROM muted_members WHERE chat_id=?", (chat_id,))]

# ==================== الرسائل المجدولة ====================
def add_scheduled(chat_id, text, interval_min):
    with closing(_conn()) as c, c:
        c.execute("INSERT INTO scheduled_messages(chat_id,text,interval_min,last_sent,enabled) VALUES(?,?,?,0,1)",
                  (chat_id, text, interval_min))

def remove_scheduled(sid):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM scheduled_messages WHERE id=?", (sid,))

def list_scheduled(chat_id):
    with closing(_conn()) as c:
        return [{"id":r[0],"text":r[1],"interval_min":r[2],"enabled":bool(r[3])} for r in
                c.execute("SELECT id,text,interval_min,enabled FROM scheduled_messages WHERE chat_id=?", (chat_id,))]

def update_scheduled_last_sent(sid, ts):
    with closing(_conn()) as c, c:
        c.execute("UPDATE scheduled_messages SET last_sent=? WHERE id=?", (ts, sid))

def list_all_scheduled():
    with closing(_conn()) as c:
        return [{"id":r[0],"chat_id":r[1],"text":r[2],"interval_min":r[3],"last_sent":r[4]} for r in
                c.execute("SELECT id,chat_id,text,interval_min,last_sent FROM scheduled_messages WHERE enabled=1")]

# ==================== المنشن الدوري ====================
def get_periodic_mention(chat_id):
    with closing(_conn()) as c:
        r = c.execute("SELECT enabled,interval_min,mention_count,message,last_sent FROM periodic_mentions WHERE chat_id=?", (chat_id,)).fetchone()
    if r:
        return {"enabled":bool(r[0]),"interval_min":r[1],"mention_count":r[2],"message":r[3] or "","last_sent":r[4]}
    return {"enabled":False,"interval_min":60,"mention_count":5,"message":"","last_sent":0}

def set_periodic_mention(chat_id, enabled=None, interval_min=None, mention_count=None, message=None):
    with closing(_conn()) as c, c:
        r = c.execute("SELECT chat_id FROM periodic_mentions WHERE chat_id=?", (chat_id,)).fetchone()
        if not r:
            c.execute("INSERT INTO periodic_mentions(chat_id) VALUES(?)", (chat_id,))
        if enabled is not None:
            c.execute("UPDATE periodic_mentions SET enabled=? WHERE chat_id=?", (1 if enabled else 0, chat_id))
        if interval_min is not None:
            c.execute("UPDATE periodic_mentions SET interval_min=? WHERE chat_id=?", (interval_min, chat_id))
        if mention_count is not None:
            c.execute("UPDATE periodic_mentions SET mention_count=? WHERE chat_id=?", (mention_count, chat_id))
        if message is not None:
            c.execute("UPDATE periodic_mentions SET message=? WHERE chat_id=?", (message, chat_id))

def update_periodic_last_sent(chat_id, ts):
    with closing(_conn()) as c, c:
        c.execute("UPDATE periodic_mentions SET last_sent=? WHERE chat_id=?", (ts, chat_id))

def list_enabled_periodic():
    with closing(_conn()) as c:
        return [{"chat_id":r[0],"interval_min":r[1],"mention_count":r[2],"message":r[3] or "","last_sent":r[4]} for r in
                c.execute("SELECT chat_id,interval_min,mention_count,message,last_sent FROM periodic_mentions WHERE enabled=1")]

# ==================== Bank Turbo ====================
def get_bank_setting(key, default=None):
    with closing(_conn()) as c:
        r = c.execute("SELECT value FROM bank_settings WHERE key=?", (key,)).fetchone()
        if r is None: return default
        try: return int(r[0])
        except: return r[0]

def set_bank_setting(key, value):
    with closing(_conn()) as c, c:
        c.execute("INSERT OR REPLACE INTO bank_settings(key,value) VALUES(?,?)", (key, str(value)))

def get_bank_account(user_id):
    with closing(_conn()) as c:
        r = c.execute("""SELECT user_id,account_number,balance,last_salary,last_tip,
                         last_steal,last_invest,last_luck,total_stolen,created_at,first_name,username
                         FROM bank_accounts WHERE user_id=?""", (user_id,)).fetchone()
    if not r: return None
    return {"user_id":r[0],"account_number":r[1],"balance":r[2],
            "last_salary":r[3],"last_tip":r[4],"last_steal":r[5],
            "last_invest":r[6],"last_luck":r[7],"total_stolen":r[8],
            "created_at":r[9],"first_name":r[10],"username":r[11]}

def create_bank_account(user_id, first_name, username, initial_balance=0):
    """ينشئ حساب جديد - atomic"""
    with closing(_atomic()) as c, c:
        r = c.execute("SELECT user_id FROM bank_accounts WHERE user_id=?", (user_id,)).fetchone()
        if r: return None
        for _ in range(10):
            acc_num = str(random.randint(100000, 999999))
            ex = c.execute("SELECT user_id FROM bank_accounts WHERE account_number=?", (acc_num,)).fetchone()
            if not ex: break
        else:
            return None
        c.execute("""INSERT INTO bank_accounts(user_id,account_number,balance,last_salary,last_tip,
                     last_steal,last_invest,last_luck,total_stolen,created_at,first_name,username)
                     VALUES(?,?,?,0,0,0,0,0,0,?,?,?)""",
                  (user_id, acc_num, initial_balance, int(time.time()), first_name, username))
        return acc_num

def delete_bank_account(user_id):
    with closing(_atomic()) as c, c:
        c.execute("DELETE FROM bank_accounts WHERE user_id=?", (user_id,))

def update_bank_account(user_id, **kwargs):
    """تحديث حقول الحساب"""
    allowed = {"balance","last_salary","last_tip","last_steal","last_invest",
               "last_luck","total_stolen","first_name","username"}
    fields = {k:v for k,v in kwargs.items() if k in allowed}
    if not fields: return
    with closing(_atomic()) as c, c:
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [user_id]
        c.execute(f"UPDATE bank_accounts SET {sets} WHERE user_id=?", vals)

def transfer_money(from_id, to_id, amount):
    """تحويل atomic آمن"""
    if amount <= 0 or from_id == to_id: return False, "invalid"
    with closing(_atomic()) as c:
        try:
            c.execute("BEGIN IMMEDIATE")
            r1 = c.execute("SELECT balance FROM bank_accounts WHERE user_id=?", (from_id,)).fetchone()
            r2 = c.execute("SELECT balance FROM bank_accounts WHERE user_id=?", (to_id,)).fetchone()
            if not r1 or not r2:
                c.execute("ROLLBACK")
                return False, "no_account"
            if r1[0] < amount:
                c.execute("ROLLBACK")
                return False, "insufficient"
            c.execute("UPDATE bank_accounts SET balance=balance-? WHERE user_id=?", (amount, from_id))
            c.execute("UPDATE bank_accounts SET balance=balance+? WHERE user_id=?", (amount, to_id))
            c.execute("INSERT INTO bank_transactions(from_id,to_id,amount,type,created_at) VALUES(?,?,?,?,?)",
                      (from_id, to_id, amount, "transfer", int(time.time())))
            c.execute("COMMIT")
            return True, "ok"
        except Exception as e:
            try: c.execute("ROLLBACK")
            except: pass
            return False, str(e)

def add_bank_money(user_id, amount, type_="reward"):
    """إضافة فلوس atomic"""
    if amount <= 0: return False
    with closing(_atomic()) as c, c:
        c.execute("UPDATE bank_accounts SET balance=balance+? WHERE user_id=?", (amount, user_id))
        c.execute("INSERT INTO bank_transactions(from_id,to_id,amount,type,created_at) VALUES(?,?,?,?,?)",
                  (0, user_id, amount, type_, int(time.time())))
    return True

def deduct_bank_money(user_id, amount, type_="fine"):
    """خصم فلوس atomic"""
    if amount <= 0: return False
    with closing(_atomic()) as c:
        try:
            c.execute("BEGIN IMMEDIATE")
            r = c.execute("SELECT balance FROM bank_accounts WHERE user_id=?", (user_id,)).fetchone()
            if not r or r[0] < amount:
                c.execute("ROLLBACK")
                return False
            c.execute("UPDATE bank_accounts SET balance=balance-? WHERE user_id=?", (amount, user_id))
            c.execute("INSERT INTO bank_transactions(from_id,to_id,amount,type,created_at) VALUES(?,?,?,?,?)",
                      (user_id, 0, amount, type_, int(time.time())))
            c.execute("COMMIT")
            return True
        except:
            try: c.execute("ROLLBACK")
            except: pass
            return False

def add_stolen(user_id, amount):
    with closing(_atomic()) as c, c:
        c.execute("UPDATE bank_accounts SET total_stolen=total_stolen+? WHERE user_id=?", (amount, user_id))

def get_top_money(limit=10):
    with closing(_conn()) as c:
        return [{"user_id":r[0],"balance":r[1],"first_name":r[2],"username":r[3]} for r in
                c.execute("SELECT user_id,balance,first_name,username FROM bank_accounts ORDER BY balance DESC LIMIT ?", (limit,))]

def get_top_thieves(limit=10):
    with closing(_conn()) as c:
        return [{"user_id":r[0],"total_stolen":r[1],"first_name":r[2],"username":r[3]} for r in
                c.execute("SELECT user_id,total_stolen,first_name,username FROM bank_accounts WHERE total_stolen > 0 ORDER BY total_stolen DESC LIMIT ?", (limit,))]

def find_bank_by_account(acc_num):
    with closing(_conn()) as c:
        r = c.execute("SELECT user_id,first_name,username FROM bank_accounts WHERE account_number=?", (acc_num,)).fetchone()
        return {"user_id":r[0],"first_name":r[1],"username":r[2]} if r else None

def get_all_bank_settings():
    with closing(_conn()) as c:
        return {r[0]: r[1] for r in c.execute("SELECT key,value FROM bank_settings")}


