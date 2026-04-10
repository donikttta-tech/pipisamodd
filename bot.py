import asyncio
import random
import json
import os
from datetime import datetime, timezone
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import aiohttp

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, LabeledPrice, PreCheckoutQuery,
    BotCommand, BotCommandScopeDefault, BotCommandScopeChat,
    CallbackQuery, BufferedInputFile
)

TOKEN = "8533414196:AAEgJf1l2YxJApehqTbnBCNwLd0Jb4W50Eg"
ADMIN_ID = 8144110555
CHANNEL_USERNAME = "pipisamod"
CHANNEL_LINK = "https://t.me/pipisamod"
CHAT_LINK = "https://t.me/+-ySATAuKXL8wZjgx"
BOT_USERNAME = "pipisamodbot"
COOLDOWN_MINUTES = 30

bot = Bot(token=TOKEN)
dp  = Dispatcher()

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_FILE  = os.path.join(BASE_DIR, "data.json")
PROMO_FILE = os.path.join(BASE_DIR, "promos.json")

_session: aiohttp.ClientSession | None = None

async def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session

# ══════════════════════════════════════════════
#  ЭМОДЗИ (обычные Unicode — работают везде)
# ══════════════════════════════════════════════

class E:
    FIRE    = "🔥"
    STAR    = "⭐"
    GEM     = "💎"
    GIFT    = "🎁"
    TROPHY  = "🏆"
    PEOPLE  = "👥"
    STAT    = "📊"
    LINK    = "🔗"
    CHANNEL = "📢"
    PROMO   = "🎟"
    CHECK   = "✅"
    CROSS   = "❌"
    LOCK    = "🔒"
    WORLD   = "🌍"
    DICK    = "📏"
    CLOCK   = "⏳"
    CROWN   = "👑"
    ROCKET  = "🚀"
    ALIEN   = "👾"
    MEDAL1  = "🥇"
    MEDAL2  = "🥈"
    MEDAL3  = "🥉"
    CHART   = "📈"
    ADMIN   = "🔧"
    MONEY   = "💰"
    WARN    = "⚠️"
    INFO    = "ℹ️"
    ARROW   = "└"
    LINE    = "・"

# Иконки кнопок (custom emoji id для Telegram Premium кнопок)
class I:
    STAR    = "5471974755814717948"
    GEM     = "5471987448946420159"
    GIFT    = "5445284980978621387"
    TROPHY  = "5431815452437257407"
    PEOPLE  = "5469791106319549337"
    STAT    = "5472235439705895813"
    LINK    = "5447183459954931711"
    CHANNEL = "5472308940793580684"
    PROMO   = "5472308571754800252"
    CHECK   = "5436040291507247617"
    CROSS   = "5447644880824181073"
    WORLD   = "5431576498153807523"
    ROCKET  = "5391054323012608736"
    CROWN   = "5247133031235329609"
    ALIEN   = "5470092785094765546"

# ══════════════════════════════════════════════
#  RAW API
# ══════════════════════════════════════════════

async def _api(method: str, payload: dict) -> dict:
    session = await get_session()
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    try:
        async with session.post(url, json=payload) as resp:
            result = await resp.json()
            if not result.get("ok"):
                print(f"[API ERROR] {method}: {result.get('description')}")
            return result
    except Exception as e:
        print(f"[API EXCEPTION] {method}: {e}")
        return {"ok": False}

async def send_raw(
    chat_id,
    text: str,
    reply_markup: dict = None,
    parse_mode: str = "HTML",
    reply_to: int = None,
) -> dict:
    p = {
        "chat_id": str(chat_id),
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        p["reply_markup"] = reply_markup
    if reply_to:
        p["reply_to_message_id"] = reply_to
    return await _api("sendMessage", p)

async def edit_raw(
    chat_id,
    message_id: int,
    text: str,
    reply_markup: dict = None,
    parse_mode: str = "HTML",
) -> dict:
    p = {
        "chat_id": str(chat_id),
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        p["reply_markup"] = reply_markup
    return await _api("editMessageText", p)

async def answer_cb(
    callback_query_id: str,
    text: str = "",
    show_alert: bool = False,
) -> dict:
    return await _api("answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert,
    })

async def send_photo_raw(
    chat_id,
    photo_bytes: bytes,
    caption: str = "",
    parse_mode: str = "HTML",
) -> dict:
    session = await get_session()
    url  = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    data = aiohttp.FormData()
    data.add_field("chat_id",    str(chat_id))
    data.add_field("caption",    caption)
    data.add_field("parse_mode", parse_mode)
    data.add_field(
        "photo", photo_bytes,
        filename="stats.png",
        content_type="image/png",
    )
    try:
        async with session.post(url, data=data) as resp:
            return await resp.json()
    except Exception as e:
        print(f"[send_photo_raw] {e}")
        return {"ok": False}

# ══════════════════════════════════════════════
#  КОНСТРУКТОР КНОПОК
# ══════════════════════════════════════════════

def ibtn(
    text: str,
    callback: str = None,
    url: str = None,
    style: str = None,
    icon_id: str = None,
) -> dict:
    b = {"text": text}
    if callback: b["callback_data"] = callback
    if url:      b["url"] = url
    if style:    b["style"] = style
    if icon_id:  b["icon_custom_emoji_id"] = icon_id
    return b

def ikb(*rows) -> dict:
    return {"inline_keyboard": list(rows)}

# ══════════════════════════════════════════════
#  ЕЖЕДНЕВНЫЕ БОНУСЫ
# ══════════════════════════════════════════════

DAILY_BONUSES = {
    1: {"attempts": 2,  "size": 0,  "desc": "2 попытки"},
    2: {"attempts": 5,  "size": 0,  "desc": "5 попыток"},
    3: {"attempts": 2,  "size": 10, "desc": "+10 см и 2 попытки"},
    4: {"attempts": 0,  "size": 20, "desc": "+20 см"},
    5: {"attempts": 0,  "size": 25, "desc": "+25 см"},
    6: {"attempts": 1,  "size": 15, "desc": "+1 попытка и +15 см"},
    7: {"attempts": 0,  "size": 30, "desc": "+30 см"},
}

# ══════════════════════════════════════════════
#  ДАННЫЕ
# ══════════════════════════════════════════════

def load_data() -> dict:
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[load_data] {e}")
    return {}

def save_data(data: dict):
    try:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        os.rename(tmp, DATA_FILE)
    except IOError as e:
        print(f"[save_data] {e}")

def load_promos() -> dict:
    try:
        if os.path.exists(PROMO_FILE):
            with open(PROMO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[load_promos] {e}")
    return {}

def save_promos(p: dict):
    try:
        tmp = PROMO_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, indent=2)
        if os.path.exists(PROMO_FILE):
            os.remove(PROMO_FILE)
        os.rename(tmp, PROMO_FILE)
    except IOError as e:
        print(f"[save_promos] {e}")

# ══════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════

def now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()

def safe_ts(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            pass
        try:
            dt = datetime.strptime(v, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            pass
    return None

def fmt_ts(v) -> str:
    ts = safe_ts(v)
    if ts is None:
        return "Никогда"
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return "Никогда"

def get_global(data: dict, user_id: int) -> dict:
    uid = str(user_id)
    data.setdefault("_global", {})
    data["_global"].setdefault(uid, {})
    g = data["_global"][uid]
    g.setdefault("banned",           False)
    g.setdefault("name",             "")
    g.setdefault("pending_attempts", 0)
    g.setdefault("referred_by",      None)
    g.setdefault("referrals",        [])
    g.setdefault("ref_confirmed",    False)
    g.setdefault("daily_streak",     0)
    g.setdefault("last_daily",       None)
    return g

def is_banned(data: dict, user_id: int) -> bool:
    return get_global(data, user_id).get("banned", False)

def ensure_user(data: dict, chat_id, user_id: int, user_name: str) -> dict:
    cid = str(chat_id)
    uid = str(user_id)
    data.setdefault(cid, {})
    data[cid].setdefault(uid, {
        "name": user_name, "size": 0,
        "last_used": None, "extra_attempts": 0,
    })
    u = data[cid][uid]
    u["name"]      = user_name
    u["last_used"] = safe_ts(u.get("last_used"))
    g = get_global(data, user_id)
    if g.get("pending_attempts", 0) > 0:
        u["extra_attempts"] = u.get("extra_attempts", 0) + g["pending_attempts"]
        g["pending_attempts"] = 0
    g["name"] = user_name
    return u

def add_attempts_anywhere(data: dict, user_id: int, amount: int):
    uid   = str(user_id)
    added = False
    for cid, cd in data.items():
        if cid == "_global":
            continue
        if uid in cd:
            cd[uid]["extra_attempts"] = cd[uid].get("extra_attempts", 0) + amount
            added = True
    if not added:
        g = get_global(data, user_id)
        g["pending_attempts"] = g.get("pending_attempts", 0) + amount

def add_size_anywhere(data: dict, user_id: int, amount: int):
    uid = str(user_id)
    for cid, cd in data.items():
        if cid == "_global":
            continue
        if uid in cd:
            cd[uid]["size"] = cd[uid].get("size", 0) + amount

# ══════════════════════════════════════════════
#  ПРОВЕРКИ
# ══════════════════════════════════════════════

async def check_bio(user_id: int) -> bool:
    try:
        chat = await bot.get_chat(user_id)
        bio  = getattr(chat, "bio", None) or ""
        return BOT_USERNAME.lower() in bio.lower()
    except Exception:
        return True

async def check_sub(user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return m.status not in ("left", "kicked", "banned")
    except Exception:
        return True

async def require_sub(chat_id, user_id: int) -> bool:
    """Возвращает True если подписан, иначе отправляет блокирующее сообщение и возвращает False."""
    if await check_sub(user_id):
        return True
    kb = ikb(
        [ibtn("📢 Подписаться на канал", url=CHANNEL_LINK,
              style="primary", icon_id=I.CHANNEL)],
        [ibtn("✅ Я подписался", callback="check_sub",
              style="success", icon_id=I.CHECK)],
    )
    await send_raw(
        chat_id,
        f"{E.LOCK} <b>Подписка обязательна!</b>\n\n"
        f"Чтобы пользоваться ботом, подпишись на канал:\n"
        f"{E.CHANNEL} {CHANNEL_LINK}\n\n"
        f"После подписки нажми кнопку ниже 👇",
        reply_markup=kb,
    )
    return False

# ══════════════════════════════════════════════
#  РЕФЕРАЛЬНАЯ СИСТЕМА
# ══════════════════════════════════════════════

async def confirm_referral(data: dict, user_id: int):
    g = get_global(data, user_id)
    if g.get("ref_confirmed"):
        return
    inv_id = g.get("referred_by")
    if not inv_id:
        return
    g["ref_confirmed"] = True
    add_attempts_anywhere(data, user_id, 1)
    gi = get_global(data, inv_id)
    s  = str(user_id)
    if s not in gi.get("referrals", []):
        gi.setdefault("referrals", []).append(s)
    add_attempts_anywhere(data, inv_id, 2)
    save_data(data)
    try:
        await send_raw(
            inv_id,
            f"{E.CROWN} Твой друг <b>{g.get('name', 'Друг')}</b> подтверждён!\n"
            f"{E.PROMO} Начислено <b>+2 попытки</b>!\n"
            f"{E.PEOPLE} Приглашено: <b>{len(gi.get('referrals', []))} чел.</b>",
        )
    except Exception:
        pass

# ══════════════════════════════════════════════
#  FSM
# ══════════════════════════════════════════════

_states: dict = {}

def set_state(uid: int, state: str):
    _states[uid] = state

def get_st(uid: int) -> str:
    return _states.get(uid, "")

def clr_state(uid: int):
    _states.pop(uid, None)

# ══════════════════════════════════════════════
#  КОМАНДЫ МЕНЮ
# ══════════════════════════════════════════════

async def set_commands():
    cmds = [
        BotCommand(command="start",      description="Запустить бота"),
        BotCommand(command="dick",       description="Изменить размер писюна"),
        BotCommand(command="nick",       description="Сменить никнейм (/nick НовыйНик)"),
        BotCommand(command="daily",      description="Ежедневный бонус"),
        BotCommand(command="top",        description="Рейтинги — чат / глобальный / топ чатов"),
        BotCommand(command="stats",      description="Моя статистика"),
        BotCommand(command="stats_img",  description="Статистика картинкой"),
        BotCommand(command="ref",        description="Реферальная система"),
        BotCommand(command="promo",      description="Ввести промокод"),
        BotCommand(command="buy",        description="Купить доп. попытки"),
        BotCommand(command="help",       description="Помощь"),
    ]
    await bot.set_my_commands(cmds, scope=BotCommandScopeDefault())
    try:
        await bot.set_my_commands(
            cmds + [BotCommand(command="admin", description="Админ панель")],
            scope=BotCommandScopeChat(chat_id=ADMIN_ID),
        )
    except Exception as e:
        print(f"[set_commands admin] {e}")

# ══════════════════════════════════════════════
#  ГЕНЕРАЦИЯ КАРТИНКИ
# ══════════════════════════════════════════════

def generate_stats_image(
    name: str, size: int, rank, last_used: str, extra: int, streak: int
) -> BytesIO:
    W, H = 800, 520
    MARGIN = 28
    PURPLE_DARK  = (14,  6,  42)
    PURPLE_MID   = (28, 12,  80)
    PURPLE_CARD  = (20,  8,  58)
    PURPLE_LIGHT = (160, 80, 255)
    ACCENT_GOLD  = (255, 200,  60)
    ACCENT_CYAN  = ( 80, 210, 255)
    ACCENT_GREEN = ( 80, 255, 160)
    ACCENT_ORNG  = (255, 145,  55)
    TEXT_DIM     = (140, 120, 200)
    TEXT_WHITE   = (255, 255, 255)
    BG_TOP       = ( 8,   4,  28)
    BG_BOT       = (18,  10,  50)

    img  = Image.new("RGB", (W, H), BG_TOP)
    draw = ImageDraw.Draw(img)

    # — фон: вертикальный градиент —
    for y in range(H):
        t = y / H
        r = int(BG_TOP[0] + (BG_BOT[0]-BG_TOP[0])*t)
        g = int(BG_TOP[1] + (BG_BOT[1]-BG_TOP[1])*t)
        b = int(BG_TOP[2] + (BG_BOT[2]-BG_TOP[2])*t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # — звёзды —
    rng = random.Random(42)
    for _ in range(180):
        sx = rng.randint(0, W)
        sy = rng.randint(0, H)
        br = rng.randint(40, 200)
        sz = rng.choice([0, 0, 0, 1])
        draw.ellipse([sx-sz, sy-sz, sx+sz, sy+sz],
                     fill=(br, br, min(br+60, 255)))

    # — внешняя рамка —
    draw.rounded_rectangle([MARGIN, MARGIN, W-MARGIN, H-MARGIN],
                            radius=24, outline=PURPLE_LIGHT, width=2)

    # — загрузка шрифтов —
    bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    reg_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    def lf(paths, sz):
        for p in paths:
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
        return ImageFont.load_default()

    f_title  = lf(bold_paths, 16)
    f_name   = lf(bold_paths, 28)
    f_label  = lf(reg_paths,  13)
    f_value  = lf(bold_paths, 22)
    f_small  = lf(reg_paths,  12)
    f_streak = lf(bold_paths, 14)

    # ── ШАПКА ──────────────────────────────────────────────
    HDR_Y1, HDR_Y2 = MARGIN, MARGIN + 72
    draw.rounded_rectangle([MARGIN, HDR_Y1, W-MARGIN, HDR_Y2],
                            radius=20, fill=PURPLE_CARD)
    # блики по краям
    draw.rounded_rectangle([MARGIN, HDR_Y1, MARGIN+6, HDR_Y2],
                            radius=4, fill=PURPLE_LIGHT)
    draw.rounded_rectangle([W-MARGIN-6, HDR_Y1, W-MARGIN, HDR_Y2],
                            radius=4, fill=PURPLE_LIGHT)

    draw.text((W//2, HDR_Y1+18), "STATISTIKA",
              font=f_title, fill=TEXT_DIM, anchor="mm")

    disp = (name if len(name) <= 24 else name[:21] + "...").upper()
    draw.text((W//2, HDR_Y1+48), disp,
              font=f_name, fill=TEXT_WHITE, anchor="mm")

    # ── 4 КАРТОЧКИ СТАТЫ ────────────────────────────────────
    cards = [
        ("RAZMER PISYUNA", f"{size} CM",  PURPLE_LIGHT),
        ("MESTO V CHATE",  f"#{rank}",    ACCENT_GOLD),
        ("POSLED. IGRA",   last_used,     ACCENT_CYAN),
        ("DOF. POPYTKI",   f"{extra}",    ACCENT_GREEN),
    ]
    C_MARGIN = MARGIN + 8
    GAP      = 10
    ROWS     = 2
    COLS     = 2
    cw = (W - 2*C_MARGIN - (COLS-1)*GAP) // COLS
    ch = 88
    CARD_Y0  = HDR_Y2 + 14

    for i, (label, value, accent) in enumerate(cards):
        col = i % COLS
        row = i // COLS
        x1  = C_MARGIN + col*(cw+GAP)
        y1  = CARD_Y0  + row*(ch+GAP)
        x2, y2 = x1+cw, y1+ch

        draw.rounded_rectangle([x1, y1, x2, y2], radius=16, fill=PURPLE_MID)
        # левая цветная полоска
        draw.rounded_rectangle([x1, y1, x1+5, y2], radius=4, fill=accent)
        # метка
        draw.text((x1+18, y1+16), label, font=f_label, fill=TEXT_DIM)
        # значение
        draw.text((x1+18, y1+42), value, font=f_value, fill=TEXT_WHITE)
        # декоративная точка-акцент справа-снизу
        draw.ellipse([x2-22, y2-22, x2-10, y2-10], fill=accent+(60,) if False else accent)

    # ── СТРИК-БАР ──────────────────────────────────────────
    STR_Y1 = CARD_Y0 + ROWS*(ch+GAP) + 4
    STR_Y2 = STR_Y1 + 58
    draw.rounded_rectangle([C_MARGIN, STR_Y1, W-C_MARGIN, STR_Y2],
                            radius=14, fill=PURPLE_MID)
    draw.rounded_rectangle([C_MARGIN, STR_Y1, C_MARGIN+5, STR_Y2],
                            radius=4, fill=ACCENT_ORNG)

    # текст стрика
    draw.text((C_MARGIN+18, STR_Y1+10), "DAILY STRIK",
              font=f_label, fill=TEXT_DIM)
    draw.text((C_MARGIN+18, STR_Y1+30), f"{streak}  /  7",
              font=f_streak, fill=ACCENT_ORNG)

    # прогресс-бар
    BAR_X1 = C_MARGIN + 160
    BAR_X2 = W - C_MARGIN - 14
    BAR_Y1 = STR_Y1 + 20
    BAR_Y2 = STR_Y1 + 38
    draw.rounded_rectangle([BAR_X1, BAR_Y1, BAR_X2, BAR_Y2],
                            radius=8, fill=PURPLE_DARK)
    filled_w = int((BAR_X2 - BAR_X1) * min(streak, 7) / 7)
    if filled_w > 0:
        draw.rounded_rectangle([BAR_X1, BAR_Y1, BAR_X1+filled_w, BAR_Y2],
                                radius=8, fill=ACCENT_ORNG)
    # метки дней над баром (7 точек)
    seg = (BAR_X2 - BAR_X1) / 7
    for d in range(1, 8):
        dot_x = int(BAR_X1 + seg*(d-0.5))
        clr = ACCENT_GOLD if d <= streak else TEXT_DIM
        draw.ellipse([dot_x-3, BAR_Y1-8, dot_x+3, BAR_Y1-2], fill=clr)

    # ── ПОДПИСЬ ────────────────────────────────────────────
    FTR_Y = H - MARGIN - 26
    draw.rounded_rectangle([C_MARGIN, FTR_Y, W-C_MARGIN, FTR_Y+22],
                            radius=8, fill=PURPLE_DARK)
    draw.text((W//2, FTR_Y+11), f"@{BOT_USERNAME}  |  t.me/pipisamod",
              font=f_small, fill=TEXT_DIM, anchor="mm")

    # ── НИЖНЯЯ ЛИНИЯ ГРАДИЕНТ ──────────────────────────────
    for x in range(MARGIN, W-MARGIN):
        t   = (x - MARGIN) / (W - 2*MARGIN)
        col = (int(80+160*t), 28, int(220-80*t))
        draw.line([(x, H-MARGIN-2), (x, H-MARGIN)], fill=col)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ══════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════

@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid   = message.from_user.id
    uname = message.from_user.full_name
    args  = message.text.split(maxsplit=1)
    ref_p = args[1].strip() if len(args) > 1 else ""

    data = load_data()
    g    = get_global(data, uid)
    g["name"] = uname

    if ref_p.startswith("ref_") and not g.get("referred_by"):
        try:
            inv_id = int(ref_p[4:])
            if inv_id != uid:
                g["referred_by"] = inv_id
                save_data(data)
                await send_raw(
                    message.chat.id,
                    f"{E.CROWN} Ты пришёл по реферальной ссылке!\n"
                    f"{E.PROMO} Подпишись на канал и сыграй /dick "
                    f"— получишь <b>+1 попытку</b>!",
                )
        except ValueError:
            pass
    else:
        save_data(data)

    me = await bot.get_me()
    kb = ikb(
        [ibtn("➕ Добавить в группу",
              url=f"https://t.me/{me.username}?startgroup=true",
              style="primary", icon_id=I.ROCKET)],
        [
            ibtn("📢 Канал", url=CHANNEL_LINK, icon_id=I.CHANNEL),
            ibtn("💬 Чат",   url=CHAT_LINK),
        ],
    )
    await send_raw(
        message.chat.id,
        f"{E.ALIEN} Привет! Я <b>PipisaMod</b> — бот для чатов!\n\n"
        f"{E.DICK} Каждые <b>30 минут</b> используй /dick в группе\n"
        f"{E.GIFT} Ежедневный бонус: /daily\n"
        f"{E.PEOPLE} Реферальная система: /ref\n"
        f"{E.GEM} Купить попытки: /buy (только в ЛС)\n\n"
        f"{E.ROCKET} Добавь меня в свою группу!",
        reply_markup=kb,
    )

# ══════════════════════════════════════════════
#  /help
# ══════════════════════════════════════════════

@dp.message(Command("help"))
async def cmd_help(message: Message):
    me = await bot.get_me()
    text, kb = await _send_help_page(message.chat.id, "game", me.username)
    await send_raw(message.chat.id, text, reply_markup=kb)

async def _send_help_page(chat_id, page: str, bot_username: str):
    pages = {
        "game": (
            f"🎮 <b>ИГРА</b>\n\n"
            f"{E.DICK} /dick — Померяться писюном\n"
            f"   └ Кулдаун 30 мин, шанс роста или уменьшения\n\n"
            f"✏️ /nick <i>НИК</i> — Сменить никнейм\n"
            f"   └ Ник должен быть уникальным, макс. 32 символа\n\n"
            f"{E.GIFT} /daily — Ежедневный бонус\n"
            f"   └ Стрик до 7 дней, нужен @{BOT_USERNAME} в био"
        ),
        "ratings": (
            f"{E.TROPHY} <b>РЕЙТИНГИ</b>\n\n"
            f"🏅 /top — Топ писюнов\n"
            f"   └ 3 режима: топ чата / глобальный / топ чатов\n\n"
            f"   Переключай режимы кнопками прямо в сообщении"
        ),
        "profile": (
            f"{E.STAT} <b>ПРОФИЛЬ</b>\n\n"
            f"{E.STAT} /stats — Статистика текстом\n"
            f"   └ Размер, место, стрик, попытки\n\n"
            f"🖼 /stats_img — Статистика картинкой\n"
            f"   └ Красивая карточка игрока\n\n"
            f"{E.PEOPLE} /ref — Реферальная система\n"
            f"   └ +2 попытки тебе, +1 другу"
        ),
        "shop": (
            f"{E.GEM} <b>МАГАЗИН И БОНУСЫ</b>\n\n"
            f"{E.PROMO} /promo — Активировать промокод\n"
            f"   └ Вводи коды из канала\n\n"
            f"{E.GEM} /buy — Купить доп. попытки за ⭐\n"
            f"   └ Только в личных сообщениях с ботом\n\n"
            f"   1 попытка — 3⭐ | 3 попытки — 8⭐ | 5 попыток — 12⭐"
        ),
        "links": (
            f"{E.CHANNEL} <b>ССЫЛКИ</b>\n\n"
            f"📢 Канал: {CHANNEL_LINK}\n"
            f"💬 Чат: {CHAT_LINK}\n\n"
            f"➕ Добавить бота в группу:\n"
            f"   t.me/{bot_username}?startgroup=true"
        ),
    }
    nav = {
        "game":    ("",        "ratings"),
        "ratings": ("game",    "profile"),
        "profile": ("ratings", "shop"),
        "shop":    ("profile", "links"),
        "links":   ("shop",    ""),
    }
    labels = {
        "game":    "🎮 Игра",
        "ratings": "🏆 Рейтинги",
        "profile": "📊 Профиль",
        "shop":    "💎 Магазин",
        "links":   "🔗 Ссылки",
    }
    prev_p, next_p = nav[page]
    total  = len(pages)
    cur_n  = list(pages.keys()).index(page) + 1

    # Строка навигации
    nav_row = []
    if prev_p:
        nav_row.append(ibtn(f"◀ {labels[prev_p]}", callback=f"help_{prev_p}"))
    if next_p:
        nav_row.append(ibtn(f"{labels[next_p]} ▶", callback=f"help_{next_p}"))

    # Строка быстрого выбора раздела
    quick_row1 = [
        ibtn("🎮" if page != "game"    else "[ 🎮 ]", callback="help_game"),
        ibtn("🏆" if page != "ratings" else "[ 🏆 ]", callback="help_ratings"),
        ibtn("📊" if page != "profile" else "[ 📊 ]", callback="help_profile"),
        ibtn("💎" if page != "shop"    else "[ 💎 ]", callback="help_shop"),
        ibtn("🔗" if page != "links"   else "[ 🔗 ]", callback="help_links"),
    ]

    rows = [quick_row1]
    if nav_row:
        rows.append(nav_row)

    kb = ikb(*rows)
    text = (
        f"{E.CROWN} <b>Помощь PipisaMod</b>  "
        f"<i>[{cur_n}/{total}]</i>\n"
        f"{'─' * 22}\n\n"
        + pages[page]
    )
    return text, kb

@dp.callback_query(F.data.startswith("help_"))
async def cb_help_nav(callback: CallbackQuery):
    page = callback.data[5:]   # "help_game" → "game"
    valid = {"game", "ratings", "profile", "shop", "links"}
    if page not in valid:
        await answer_cb(callback.id)
        return
    me = await bot.get_me()
    text, kb = await _send_help_page(0, page, me.username)
    await edit_raw(callback.message.chat.id, callback.message.message_id,
                   text, reply_markup=kb)
    await answer_cb(callback.id)

# ══════════════════════════════════════════════
#  /daily
# ══════════════════════════════════════════════

@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    if not await require_sub(message.chat.id, message.from_user.id):
        return
    data = load_data()
    g    = get_global(data, message.from_user.id)
    cur  = g.get("daily_streak", 0)

    lines = [f"{E.GIFT} <b>Ежедневные бонусы PipisaMod:</b>\n"]
    for day, bonus in DAILY_BONUSES.items():
        if day < cur:
            marker = "✅"
        elif day == cur:
            marker = "▶️"
        else:
            marker = "⬜"
        lines.append(f"{marker} День {day}: <b>{bonus['desc']}</b>")

    lines.append(
        f"\n{E.LOCK} Требуется <code>@{BOT_USERNAME}</code> в описании профиля!"
    )

    kb = ikb(
        [ibtn("🎁 Получить бонус",
              callback=f"claim_daily_{message.from_user.id}",
              style="success", icon_id=I.GIFT)],
    )
    await send_raw(message.chat.id, "\n".join(lines), reply_markup=kb)

# ══════════════════════════════════════════════
#  /dick
# ══════════════════════════════════════════════

@dp.message(Command("dick"))
async def cmd_dick(message: Message):
    if message.chat.type == "private":
        me = await bot.get_me()
        kb = ikb([ibtn("➕ Добавить в группу",
                       url=f"https://t.me/{me.username}?startgroup=true",
                       style="primary", icon_id=I.ROCKET)])
        await send_raw(message.chat.id,
                       f"{E.CROSS} Команда работает только в группах!",
                       reply_markup=kb)
        return

    uid   = message.from_user.id
    uname = message.from_user.full_name

    if not await require_sub(message.chat.id, uid):
        return

    data = load_data()
    if is_banned(data, uid):
        await send_raw(message.chat.id, "🚫 Ты заблокирован.")
        return

    ud  = ensure_user(data, message.chat.id, uid, uname)
    now = now_ts()
    lu  = ud.get("last_used")
    ex  = ud.get("extra_attempts", 0)
    cds = COOLDOWN_MINUTES * 60

    if lu is not None and (now - lu) < cds and ex <= 0:
        rem  = cds - (now - lu)
        mins = int(rem // 60)
        secs = int(rem % 60)
        await send_raw(
            message.chat.id,
            f"{E.CLOCK} <a href='tg://user?id={uid}'>{uname}</a>, "
            f"подожди ещё <b>{mins}м {secs}с</b>!\n\n"
            f"{E.DICK} Текущий размер: <b>{ud['size']} см</b>\n"
            f"{E.GEM} Купить доп. попытки: /buy",
        )
        return

    used_extra = False
    if lu is not None and (now - lu) < cds and ex > 0:
        ud["extra_attempts"] -= 1
        used_extra = True

    # Веса: рост 90, уменьшение 50 — т.е. ~64% вырастет, ~36% уменьшится
    grew = random.choices([True, False], weights=[90, 50], k=1)[0]
    if grew:
        change = random.randint(5, 25)
    else:
        change = random.randint(1, 5)

    ud["size"]     += change if grew else -change
    ud["last_used"] = now

    g = get_global(data, uid)
    if not g.get("ref_confirmed") and g.get("referred_by"):
        await confirm_referral(data, uid)

    save_data(data)

    ex_now  = ud.get("extra_attempts", 0)
    ex_line = (f"\n{E.PROMO} Осталось доп. попыток: <b>{ex_now}</b>"
               if ex_now > 0 else "")
    ul = " <i>(доп. попытка)</i>" if used_extra else ""

    if grew:
        result_line = (
            f"твой писюн вырос на <b>+{change} см</b>!{ul}\n"
            f"Теперь он равен <b>{ud['size']} см</b>. 📈"
        )
    else:
        result_line = (
            f"твой писюн усох на <b>-{change} см</b>!{ul}\n"
            f"Теперь он равен <b>{ud['size']} см</b>. 📉"
        )

    await send_raw(
        message.chat.id,
        f"{E.DICK} <a href='tg://user?id={uid}'>{uname}</a>, "
        f"{result_line}\n"
        f"{E.CLOCK} Следующая попытка через <b>{COOLDOWN_MINUTES} мин</b>"
        f"{ex_line}",
    )

# ══════════════════════════════════════════════
#  /top  (объединённый: чат / глобал / топ чатов)
# ══════════════════════════════════════════════

def _top_kb(active: str) -> dict:
    """Кнопки переключения топа, активная выделена."""
    def btn(label, cb, is_active):
        text = f"[ {label} ]" if is_active else label
        return ibtn(text, callback=cb,
                    style="primary" if is_active else None)
    return ikb([
        btn("🏅 Топ чата",    "top_chat",   active == "chat"),
        btn("🌍 Глобальный",  "top_global", active == "global"),
        btn("🏙 Топ чатов",   "top_chats",  active == "chats"),
    ])

async def _build_top_chat(chat_id) -> str:
    cid  = str(chat_id)
    data = load_data()
    if cid not in data or not data[cid]:
        return f"{E.STAT} В этом чате ещё нет игроков!"
    su     = sorted(data[cid].items(), key=lambda x: x[1].get("size", 0), reverse=True)
    medals = [E.MEDAL1, E.MEDAL2, E.MEDAL3]
    lines  = [f"{E.TROPHY} <b>Топ 10 писюнов чата</b>\n"]
    for i, (_, ud) in enumerate(su[:10]):
        m = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{m} {ud.get('name','?')} — <b>{ud.get('size',0)} см</b>")
    return "\n".join(lines)

async def _build_top_global() -> str:
    data = load_data()
    au   = {}
    for cid, cd in data.items():
        if cid == "_global":
            continue
        for uid, ud in cd.items():
            if uid not in au or au[uid].get("size", 0) < ud.get("size", 0):
                au[uid] = ud
    if not au:
        return f"{E.WORLD} Глобальная статистика пуста!"
    su     = sorted(au.items(), key=lambda x: x[1].get("size", 0), reverse=True)
    medals = [E.MEDAL1, E.MEDAL2, E.MEDAL3]
    lines  = [f"{E.WORLD} <b>Глобальный топ 10</b>\n"]
    for i, (_, ud) in enumerate(su[:10]):
        m = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{m} {ud.get('name','?')} — <b>{ud.get('size',0)} см</b>")
    return "\n".join(lines)

async def _build_top_chats() -> str:
    data = load_data()
    chat_scores = []
    for cid, cd in data.items():
        if cid == "_global":
            continue
        total_cm     = sum(ud.get("size", 0) for ud in cd.values() if isinstance(ud, dict))
        player_count = len(cd)
        if total_cm <= 0:
            continue
        try:
            chat_info = await bot.get_chat(int(cid))
            chat_name = chat_info.title or f"Чат {cid}"
        except Exception:
            chat_name = f"Чат {cid}"
        chat_scores.append((chat_name, total_cm, player_count))
    if not chat_scores:
        return f"{E.WORLD} Статистика чатов пуста!"
    chat_scores.sort(key=lambda x: x[1], reverse=True)
    medals = [E.MEDAL1, E.MEDAL2, E.MEDAL3]
    lines  = [f"🏙 <b>Топ чатов по суммарному размеру</b>\n"]
    for i, (name, total, players) in enumerate(chat_scores[:10]):
        m = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{m} <b>{name}</b>\n   📏 {total} см | 👥 {players} игр.")
    return "\n".join(lines)

@dp.message(Command("top"))
async def cmd_top(message: Message):
    if not await require_sub(message.chat.id, message.from_user.id):
        return
    # По умолчанию — топ чата (если группа), иначе глобальный
    if message.chat.type != "private":
        text = await _build_top_chat(message.chat.id)
        active = "chat"
    else:
        text = await _build_top_global()
        active = "global"
    await send_raw(message.chat.id, text, reply_markup=_top_kb(active))

# Оставляем старые команды как алиасы → редиректят на /top
@dp.message(Command("top_dick"))
async def cmd_top_dick(message: Message):
    await cmd_top(message)

@dp.message(Command("global_top"))
async def cmd_global_top(message: Message):
    if not await require_sub(message.chat.id, message.from_user.id):
        return
    text = await _build_top_global()
    await send_raw(message.chat.id, text, reply_markup=_top_kb("global"))

@dp.message(Command("top_chats"))
async def cmd_top_chats(message: Message):
    if not await require_sub(message.chat.id, message.from_user.id):
        return
    text = await _build_top_chats()
    await send_raw(message.chat.id, text, reply_markup=_top_kb("chats"))

# Callbacks переключения топа
@dp.callback_query(F.data == "top_chat")
async def cb_top_chat(callback: CallbackQuery):
    if callback.message.chat.type == "private":
        await answer_cb(callback.id, "Топ чата доступен только в группе!", True)
        return
    text = await _build_top_chat(callback.message.chat.id)
    await edit_raw(callback.message.chat.id, callback.message.message_id,
                   text, reply_markup=_top_kb("chat"))
    await answer_cb(callback.id)

@dp.callback_query(F.data == "top_global")
async def cb_top_global(callback: CallbackQuery):
    text = await _build_top_global()
    await edit_raw(callback.message.chat.id, callback.message.message_id,
                   text, reply_markup=_top_kb("global"))
    await answer_cb(callback.id)

@dp.callback_query(F.data == "top_chats")
async def cb_top_chats(callback: CallbackQuery):
    text = await _build_top_chats()
    await edit_raw(callback.message.chat.id, callback.message.message_id,
                   text, reply_markup=_top_kb("chats"))
    await answer_cb(callback.id)

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.chat.type == "private":
        await send_raw(message.chat.id,
                       f"{E.CROSS} Команда работает только в группах!")
        return
    if not await require_sub(message.chat.id, message.from_user.id):
        return

    cid  = str(message.chat.id)
    uid  = str(message.from_user.id)
    data = load_data()

    if cid not in data or uid not in data[cid]:
        await send_raw(message.chat.id,
                       f"{E.CROSS} Ты ещё не играл! Используй /dick")
        return

    ud   = data[cid][uid]
    su   = sorted(data[cid].items(),
                  key=lambda x: x[1].get("size", 0), reverse=True)
    rank = next((i+1 for i,(u,_) in enumerate(su) if u == uid), "?")
    ex   = ud.get("extra_attempts", 0)
    g    = get_global(data, message.from_user.id)
    st   = g.get("daily_streak", 0)

    lu  = safe_ts(ud.get("last_used"))
    now = now_ts()
    cds = COOLDOWN_MINUTES * 60
    if lu and (now - lu) < cds:
        rem  = cds - (now - lu)
        mins = int(rem // 60)
        secs = int(rem % 60)
        cd_line = f"{E.CLOCK} Следующая попытка через: <b>{mins}м {secs}с</b>"
    else:
        cd_line = f"{E.CHECK} Попытка: <b>доступна прямо сейчас!</b>"

    ex_line = (f"{E.PROMO} Доп. попытки: <b>{ex} шт.</b>"
               if ex > 0 else f"{E.PROMO} Доп. попытки: <b>0</b>")

    kb = ikb(
        [ibtn("🖼 Статистика картинкой",
              callback="get_stats_img",
              style="primary", icon_id=I.STAT)],
    )
    await send_raw(
        message.chat.id,
        f"{E.STAT} <b>Статистика игрока</b>\n\n"
        f"👤 Имя: <b>{ud.get('name','?')}</b>\n"
        f"{E.DICK} Размер: <b>{ud.get('size',0)} см</b>\n"
        f"{E.TROPHY} Место в чате: <b>{rank}</b>\n"
        f"{E.FIRE} Стрик дней: <b>{st}/7</b>\n"
        f"{ex_line}\n"
        f"{cd_line}",
        reply_markup=kb,
    )

# ══════════════════════════════════════════════
#  /stats_img
# ══════════════════════════════════════════════

async def _send_stats_img(chat_id, user_id: int, src_chat_id):
    uid  = str(user_id)
    cid  = str(src_chat_id)
    data = load_data()

    if cid not in data or uid not in data[cid]:
        await send_raw(chat_id,
                       f"{E.CROSS} Ты ещё не играл! Используй /dick")
        return

    ud   = data[cid][uid]
    su   = sorted(data[cid].items(),
                  key=lambda x: x[1].get("size", 0), reverse=True)
    rank = next((i+1 for i,(u,_) in enumerate(su) if u == uid), "?")
    g    = get_global(data, user_id)
    st   = g.get("daily_streak", 0)

    buf = generate_stats_image(
        name=ud.get("name","?"),     size=ud.get("size",0),
        rank=rank,                   last_used=fmt_ts(ud.get("last_used")),
        extra=ud.get("extra_attempts",0), streak=st,
    )
    await send_photo_raw(
        chat_id, buf.read(),
        caption=f"📊 Статистика <b>{ud.get('name','?')}</b>",
    )

@dp.message(Command("stats_img"))
async def cmd_stats_img(message: Message):
    if message.chat.type == "private":
        await send_raw(message.chat.id,
                       f"{E.CROSS} Команда работает только в группах!")
        return
    if not await require_sub(message.chat.id, message.from_user.id):
        return
    await _send_stats_img(
        message.chat.id, message.from_user.id, message.chat.id
    )

# ══════════════════════════════════════════════
#  /ref
# ══════════════════════════════════════════════

@dp.message(Command("ref"))
async def cmd_ref(message: Message):
    if not await require_sub(message.chat.id, message.from_user.id):
        return
    uid  = message.from_user.id
    data = load_data()
    g    = get_global(data, uid)
    me   = await bot.get_me()

    ref_link  = f"https://t.me/{me.username}?start=ref_{uid}"
    refs      = g.get("referrals", [])
    share_url = (
        f"https://t.me/share/url"
        f"?url={ref_link}"
        f"&text=Присоединяйся%20к%20PipisaMod!"
    )

    kb = ikb(
        [ibtn("🔗 Поделиться ссылкой", url=share_url,
              style="primary", icon_id=I.LINK)],
        [
            ibtn("👥 Мои рефералы",
                 callback=f"my_refs_{uid}", icon_id=I.PEOPLE),
            ibtn("🏆 Топ рефералов",
                 callback="top_refs",       icon_id=I.TROPHY),
        ],
    )
    await send_raw(
        message.chat.id,
        f"{E.PEOPLE} <b>ПРИГЛАСИТЬ ДРУЗЕЙ</b>\n"
        f"{E.LINE * 14}\n\n"
        f"{E.GIFT} Бонусы за приглашение:\n"
        f"• Ты: <b>+2 попытки</b> за каждого друга\n"
        f"• Друг: <b>+1 попытку</b>\n\n"
        f"{E.LINK} Твоя ссылка:\n"
        f"{E.ARROW} <code>{ref_link}</code>\n\n"
        f"{E.PEOPLE} Приглашено: <b>{len(refs)} чел.</b>\n\n"
        f"{E.INFO} <i>Друг должен подписаться на канал и сыграть /dick.</i>",
        reply_markup=kb,
    )

# ══════════════════════════════════════════════
#  /buy
# ══════════════════════════════════════════════

@dp.message(Command("buy"))
async def cmd_buy(message: Message):
    if not await require_sub(message.chat.id, message.from_user.id):
        return
    if message.chat.type != "private":
        await send_raw(
            message.chat.id,
            f"{E.GEM} Покупка доступна только в <b>личных сообщениях</b>!",
        )
        return

    kb = ikb(
        [ibtn("1 попытка — 3 ⭐",  callback="buy_1",
              style="primary", icon_id=I.STAR)],
        [ibtn("3 попытки — 8 ⭐",  callback="buy_3",
              style="primary", icon_id=I.STAR)],
        [ibtn("5 попыток — 12 ⭐", callback="buy_5",
              style="success", icon_id=I.STAR)],
    )
    await send_raw(
        message.chat.id,
        f"{E.GEM} <b>Купить попытки за Telegram Stars:</b>\n\n"
        f"{E.STAR} 1 попытка  — 3 Stars\n"
        f"{E.STAR} 3 попытки  — 8 Stars\n"
        f"{E.STAR} 5 попыток  — 12 Stars\n\n"
        f"Выбери пакет {E.ARROW}",
        reply_markup=kb,
    )

# ══════════════════════════════════════════════
#  /promo
# ══════════════════════════════════════════════

@dp.message(Command("promo"))
async def cmd_promo(message: Message):
    if not await require_sub(message.chat.id, message.from_user.id):
        return
    set_state(message.from_user.id, "wait_promo")
    await send_raw(message.chat.id, f"{E.PROMO} Введи промокод:")

# ══════════════════════════════════════════════
#  /nick
# ══════════════════════════════════════════════

@dp.message(Command("nick"))
async def cmd_nick(message: Message):
    if not await require_sub(message.chat.id, message.from_user.id):
        return
    uid  = message.from_user.id
    args = message.text.split(maxsplit=1)

    if len(args) < 2 or not args[1].strip():
        await send_raw(
            message.chat.id,
            f"📝 <b>Смена никнейма</b>\n\n"
            f"Использование: <code>/nick НовыйНик</code>\n"
            f"Пример: <code>/nick КрутойИгрок</code>",
        )
        return

    new_nick = args[1].strip()

    if len(new_nick) > 32:
        await send_raw(message.chat.id,
                       f"{E.CROSS} Ник слишком длинный (макс. 32 символа).")
        return

    data = load_data()

    # Проверка на уникальность
    for cid, cd in data.items():
        if cid == "_global":
            continue
        for uid_str, ud in cd.items():
            if ud.get("name", "").lower() == new_nick.lower() and int(uid_str) != uid:
                await send_raw(message.chat.id,
                               f"{E.CROSS} Ник <b>{new_nick}</b> уже занят!")
                return

    # Проверка в _global
    for uid_str, gd in data.get("_global", {}).items():
        if gd.get("name", "").lower() == new_nick.lower() and int(uid_str) != uid:
            await send_raw(message.chat.id,
                           f"{E.CROSS} Ник <b>{new_nick}</b> уже занят!")
            return

    old_nick = message.from_user.full_name
    # Обновляем имя везде
    g = get_global(data, uid)
    old_nick = g.get("name", old_nick)
    g["name"] = new_nick

    uid_str = str(uid)
    for cid, cd in data.items():
        if cid == "_global":
            continue
        if uid_str in cd:
            cd[uid_str]["name"] = new_nick

    save_data(data)
    await send_raw(
        message.chat.id,
        f"✏️ Ник изменён!\n"
        f"{E.ARROW} <b>{old_nick}</b> → <b>{new_nick}</b>",
    )

# ══════════════════════════════════════════════
#  /admin
# ══════════════════════════════════════════════

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await send_raw(message.chat.id, f"{E.CROSS} У тебя нет доступа.")
        return
    if message.chat.type != "private":
        await send_raw(message.chat.id,
                       f"{E.LOCK} Доступно только в ЛС с ботом.")
        return

    data  = load_data()
    total = set()
    for cid, cd in data.items():
        if cid == "_global":
            continue
        total.update(cd.keys())

    promos = load_promos()
    kb = ikb(
        [
            ibtn("🔨 Забанить",  callback="adm_ban",
                 style="danger",  icon_id=I.CROSS),
            ibtn("✅ Разбанить", callback="adm_unban",
                 style="success", icon_id=I.CHECK),
        ],
        [ibtn("🎁 Выдать попытки", callback="adm_give",
              style="primary", icon_id=I.GIFT)],
        [
            ibtn("➕ Промокод", callback="adm_promo_add",
                 style="success", icon_id=I.PROMO),
            ibtn("❌ Удалить",  callback="adm_promo_del",
                 style="danger",  icon_id=I.CROSS),
        ],
        [ibtn("📋 Список промокодов", callback="adm_promo_list")],
        [
            ibtn("📣 Рассылка всем",  callback="adm_broadcast",
                 style="primary", icon_id=I.CHANNEL),
            ibtn("💌 МП (реф. задание)", callback="adm_mp_task",
                 style="success", icon_id=I.GIFT),
        ],
    )
    await send_raw(
        message.chat.id,
        f"{E.CROWN} <b>Админ панель PipisaMod</b>\n\n"
        f"👤 Игроков: <b>{len(total)}</b>\n"
        f"{E.PROMO} Промокодов: <b>{len(promos)}</b>",
        reply_markup=kb,
    )

# ══════════════════════════════════════════════
#  CALLBACKS
# ══════════════════════════════════════════════

@dp.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery):
    if await check_sub(callback.from_user.id):
        await edit_raw(
            callback.message.chat.id,
            callback.message.message_id,
            f"{E.CHECK} Отлично! Теперь используй /dick в группе.",
        )
        await answer_cb(callback.id)
    else:
        await answer_cb(callback.id, "❌ Ты ещё не подписался!", True)

@dp.callback_query(F.data.startswith("claim_daily_"))
async def cb_claim_daily(callback: CallbackQuery):
    owner_id = int(callback.data.split("_")[2])
    if callback.from_user.id != owner_id:
        await answer_cb(callback.id, "а ну не трожь меня!", True)
        return

    uid  = callback.from_user.id
    data = load_data()
    g    = get_global(data, uid)

    if not await check_bio(uid):
        await answer_cb(
            callback.id,
            f"Добавь @{BOT_USERNAME} в описание профиля!",
            True,
        )
        return

    last = safe_ts(g.get("last_daily"))
    now  = now_ts()
    if last and (now - last) < 86400:
        rem   = 86400 - (now - last)
        hours = int(rem // 3600)
        mins  = int((rem % 3600) // 60)
        await answer_cb(callback.id,
                        f"⏳ Следующий бонус через {hours}ч {mins}м", True)
        return

    streak = (g.get("daily_streak", 0) % 7) + 1
    bonus  = DAILY_BONUSES[streak]
    g["daily_streak"] = streak
    g["last_daily"]   = now

    if bonus["attempts"] > 0:
        add_attempts_anywhere(data, uid, bonus["attempts"])
    if bonus["size"] > 0:
        add_size_anywhere(data, uid, bonus["size"])
    save_data(data)

    lines = [f"{E.GIFT} <b>Ежедневный бонус — День {streak}</b>\n"]
    if bonus["size"] > 0:
        lines.append(f"{E.DICK} +{bonus['size']} см к писюну")
    if bonus["attempts"] > 0:
        lines.append(f"{E.PROMO} +{bonus['attempts']} доп. попыток")

    nd = (streak % 7) + 1
    lines.append(
        f"\n📅 Завтра (день {nd}): <b>{DAILY_BONUSES[nd]['desc']}</b>"
    )

    await edit_raw(
        callback.message.chat.id,
        callback.message.message_id,
        "\n".join(lines),
    )
    await answer_cb(callback.id, "✅ Бонус получен!")

@dp.callback_query(F.data == "get_stats_img")
async def cb_stats_img(callback: CallbackQuery):
    if callback.message.chat.type == "private":
        await answer_cb(callback.id, "❌ Только в группах!", True)
        return
    await _send_stats_img(
        callback.message.chat.id,
        callback.from_user.id,
        callback.message.chat.id,
    )
    await answer_cb(callback.id)

@dp.callback_query(F.data.startswith("my_refs_"))
async def cb_my_refs(callback: CallbackQuery):
    owner_id = int(callback.data.split("_")[2])
    if callback.from_user.id != owner_id:
        await answer_cb(callback.id, "а ну не трожь меня!", True)
        return

    data = load_data()
    g    = get_global(data, owner_id)
    refs = g.get("referrals", [])

    if not refs:
        await answer_cb(callback.id, "У тебя пока нет рефералов!", True)
        return

    lines = [f"{E.PEOPLE} <b>Твои рефералы ({len(refs)} чел.):</b>\n"]
    for i, uid_str in enumerate(refs[:20], 1):
        g2   = data.get("_global", {}).get(uid_str, {})
        name = g2.get("name", f"ID {uid_str}")
        lines.append(f"{i}. {name}")
    if len(refs) > 20:
        lines.append(f"\n...и ещё {len(refs)-20} чел.")

    await send_raw(callback.from_user.id, "\n".join(lines))
    await answer_cb(callback.id)

@dp.callback_query(F.data == "top_refs")
async def cb_top_refs(callback: CallbackQuery):
    data  = load_data()
    g_all = data.get("_global", {})

    scores = [
        (uid_str, gd.get("name", f"ID {uid_str}"),
         len(gd.get("referrals", [])))
        for uid_str, gd in g_all.items()
        if gd.get("referrals")
    ]

    if not scores:
        await answer_cb(callback.id, "Рефералов пока нет!", True)
        return

    scores.sort(key=lambda x: x[2], reverse=True)
    medals = [E.MEDAL1, E.MEDAL2, E.MEDAL3]
    lines  = [f"{E.TROPHY} <b>Топ по рефералам:</b>\n"]
    for i, (_, name, cnt) in enumerate(scores[:10]):
        m = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{m} {name} — <b>{cnt} чел.</b>")

    await send_raw(callback.from_user.id, "\n".join(lines))
    await answer_cb(callback.id)

@dp.callback_query(F.data == "mp_task_get")
async def cb_mp_task_get(callback: CallbackQuery):
    uid  = callback.from_user.id
    data = load_data()
    me   = await bot.get_me()

    ref_link  = f"https://t.me/{me.username}?start=ref_{uid}"
    share_url = (
        f"https://t.me/share/url"
        f"?url={ref_link}"
        f"&text=Присоединяйся%20к%20PipisaMod!%20%F0%9F%94%A5"
    )
    g    = get_global(data, uid)
    refs = g.get("referrals", [])

    kb = ikb(
        [ibtn("🔗 Поделиться ссылкой", url=share_url,
              style="primary", icon_id=I.LINK)],
    )
    await send_raw(
        uid,
        f"🎯 <b>Твоё задание</b>\n\n"
        f"{E.PEOPLE} Пригласи друга по своей ссылке!\n\n"
        f"{E.LINK} Твоя реф. ссылка:\n"
        f"{E.ARROW} <code>{ref_link}</code>\n\n"
        f"{E.PEOPLE} Уже приглашено: <b>{len(refs)} чел.</b>\n\n"
        f"{E.INFO} <i>За каждого подтверждённого друга тебе автоматически "
        f"зачисляются бонусные попытки.</i>",
        reply_markup=kb,
    )
    await answer_cb(callback.id, "📎 Ссылка отправлена!")

@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy(callback: CallbackQuery):
    if callback.message.chat.type != "private":
        await answer_cb(callback.id, "а ну не трожь меня!", True)
        return
    pkgs = {
        "buy_1": (1,  3,  "1 дополнительная попытка"),
        "buy_3": (3,  8,  "3 дополнительные попытки"),
        "buy_5": (5, 12,  "5 дополнительных попыток"),
    }
    attempts, stars, label = pkgs[callback.data]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"🎟 {label}",
        description=f"Покупка {label} для /dick в PipisaMod",
        payload=f"attempts_{attempts}_{callback.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label=label, amount=stars)],
        provider_token="",
    )
    await answer_cb(callback.id)

@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)

@dp.message(F.successful_payment)
async def on_payment(message: Message):
    parts    = message.successful_payment.invoice_payload.split("_")
    attempts = int(parts[1])
    data     = load_data()
    add_attempts_anywhere(data, message.from_user.id, attempts)
    save_data(data)
    await send_raw(
        message.chat.id,
        f"{E.CHECK} Оплата прошла!\n"
        f"{E.PROMO} Начислено <b>{attempts}</b> доп. попыток.\n"
        f"Используй /dick в группе!",
    )

@dp.callback_query(F.data.startswith("adm_"))
async def cb_admin(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await answer_cb(callback.id, "а ну не трожь меня!", True)
        return

    a = callback.data
    if a == "adm_ban":
        set_state(callback.from_user.id, "adm_ban")
        await send_raw(callback.from_user.id,
                       f"{E.CROSS} Введи <b>ID</b> для бана:")
    elif a == "adm_unban":
        set_state(callback.from_user.id, "adm_unban")
        await send_raw(callback.from_user.id,
                       f"{E.CHECK} Введи <b>ID</b> для разбана:")
    elif a == "adm_give":
        set_state(callback.from_user.id, "adm_give")
        await send_raw(callback.from_user.id,
                       f"{E.GIFT} Формат: <code>ID количество</code>")
    elif a == "adm_promo_add":
        set_state(callback.from_user.id, "adm_promo_add")
        await send_raw(
            callback.from_user.id,
            f"{E.PROMO} Формат: <code>КОД попытки макс</code>\n"
            f"Пример: <code>SUPER 3 100</code>",
        )
    elif a == "adm_promo_del":
        set_state(callback.from_user.id, "adm_promo_del")
        await send_raw(callback.from_user.id,
                       f"{E.CROSS} Введи код промокода:")
    elif a == "adm_promo_list":
        promos = load_promos()
        if not promos:
            await send_raw(callback.from_user.id, "📋 Промокодов нет.")
        else:
            lines = [f"{E.PROMO} <b>Промокоды:</b>\n"]
            for code, pd in promos.items():
                used  = len(pd.get("used_by", []))
                max_u = pd.get("max_uses", 1)
                att   = pd.get("attempts", 1)
                lines.append(
                    f"🔑 <code>{code}</code> — {att} поп. | {used}/{max_u}"
                )
            await send_raw(callback.from_user.id, "\n".join(lines))
    elif a == "adm_broadcast":
        set_state(callback.from_user.id, "adm_broadcast")
        await send_raw(
            callback.from_user.id,
            f"📣 <b>Рассылка всем пользователям</b>\n\n"
            f"Введи текст сообщения (поддерживается HTML):\n"
            f"<i>Например: &lt;b&gt;Новость!&lt;/b&gt; Текст...</i>",
        )
    elif a == "adm_mp_task":
        # Сразу рассылаем реф. задание
        data     = load_data()
        all_uids = set()
        for cid, cd in data.items():
            if cid == "_global":
                continue
            all_uids.update(cd.keys())
        all_uids.update(data.get("_global", {}).keys())

        sent, failed = 0, 0
        me = await bot.get_me()
        for uid_str in all_uids:
            try:
                target_id = int(uid_str)
                if is_banned(data, target_id):
                    continue
                task_kb = ikb(
                    [ibtn("🔗 Получить реферальную ссылку", callback="mp_task_get",
                          style="success", icon_id=I.LINK)],
                )
                await send_raw(
                    target_id,
                    f"🎯 <b>ЗАДАНИЕ ОТ АДМИНИСТРАТОРА</b>\n\n"
                    f"{E.PEOPLE} Пригласи друга по реферальной ссылке\n"
                    f"и получи бонусные попытки бесплатно!\n\n"
                    f"{E.CHECK} Друг должен подписаться на канал\n"
                    f"и сыграть /dick — тогда попытки зачислятся.\n\n"
                    f"🔥 Нажми кнопку ниже, чтобы получить свою ссылку!",
                    reply_markup=task_kb,
                )
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)

        await send_raw(
            callback.from_user.id,
            f"💌 <b>МП-рассылка завершена!</b>\n\n"
            f"{E.CHECK} Доставлено: <b>{sent}</b>\n"
            f"{E.CROSS} Не доставлено: <b>{failed}</b>",
        )

    await answer_cb(callback.id)

# ══════════════════════════════════════════════
#  FSM ТЕКСТ
# ══════════════════════════════════════════════

@dp.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message):
    uid = message.from_user.id
    st  = get_st(uid)
    if not st:
        return

    if st == "wait_promo":
        clr_state(uid)
        code   = message.text.strip().upper()
        promos = load_promos()
        if code not in promos:
            await send_raw(message.chat.id,
                           f"{E.CROSS} Промокод не найден.")
            return
        promo   = promos[code]
        used_by = promo.get("used_by", [])
        if str(uid) in used_by:
            await send_raw(message.chat.id,
                           f"{E.CROSS} Ты уже использовал этот промокод.")
            return
        if len(used_by) >= promo.get("max_uses", 1):
            await send_raw(message.chat.id, f"{E.CROSS} Промокод исчерпан.")
            return
        att = promo.get("attempts", 1)
        used_by.append(str(uid))
        promo["used_by"] = used_by
        save_promos(promos)
        data = load_data()
        add_attempts_anywhere(data, uid, att)
        save_data(data)
        await send_raw(
            message.chat.id,
            f"{E.CHECK} Промокод активирован!\n"
            f"{E.PROMO} Начислено <b>{att}</b> доп. попыток.",
        )
        return

    if uid != ADMIN_ID:
        return

    if st == "adm_ban":
        clr_state(uid)
        try:
            target = int(message.text.strip())
            data   = load_data()
            get_global(data, target)["banned"] = True
            save_data(data)
            await send_raw(message.chat.id,
                           f"{E.CROSS} <b>{target}</b> заблокирован.")
        except ValueError:
            await send_raw(message.chat.id,
                           f"{E.CROSS} Введи числовой ID.")

    elif st == "adm_unban":
        clr_state(uid)
        try:
            target = int(message.text.strip())
            data   = load_data()
            get_global(data, target)["banned"] = False
            save_data(data)
            await send_raw(message.chat.id,
                           f"{E.CHECK} <b>{target}</b> разблокирован.")
        except ValueError:
            await send_raw(message.chat.id,
                           f"{E.CROSS} Введи числовой ID.")

    elif st == "adm_give":
        clr_state(uid)
        try:
            p        = message.text.strip().split()
            target   = int(p[0])
            attempts = int(p[1])
            data     = load_data()
            add_attempts_anywhere(data, target, attempts)
            save_data(data)
            await send_raw(
                message.chat.id,
                f"{E.CHECK} <b>{target}</b> получил <b>{attempts}</b> попыток.",
            )
        except (ValueError, IndexError):
            await send_raw(message.chat.id,
                           f"{E.CROSS} Формат: <code>ID количество</code>")

    elif st == "adm_promo_add":
        clr_state(uid)
        try:
            p = message.text.strip().split()
            if len(p) < 2:
                raise ValueError
            code = p[0].upper()
            att  = int(p[1])
            mx   = int(p[2]) if len(p) > 2 else 1
            promos = load_promos()
            promos[code] = {"attempts": att, "max_uses": mx, "used_by": []}
            save_promos(promos)
            await send_raw(
                message.chat.id,
                f"{E.CHECK} Промокод <code>{code}</code> создан!\n"
                f"{E.PROMO} {att} поп. | макс. {mx} исп.",
            )
        except (ValueError, IndexError):
            await send_raw(message.chat.id,
                           f"{E.CROSS} Пример: <code>SUPER 3 100</code>")

    elif st == "adm_promo_del":
        clr_state(uid)
        code   = message.text.strip().upper()
        promos = load_promos()
        if code in promos:
            del promos[code]
            save_promos(promos)
            await send_raw(message.chat.id,
                           f"{E.CHECK} <code>{code}</code> удалён.")
        else:
            await send_raw(message.chat.id,
                           f"{E.CROSS} Промокод не найден.")

    elif st == "adm_broadcast":
        clr_state(uid)
        text = message.text.strip()
        if not text:
            await send_raw(message.chat.id, f"{E.CROSS} Пустое сообщение.")
            return

        data     = load_data()
        all_uids = set()
        for cid, cd in data.items():
            if cid == "_global":
                continue
            all_uids.update(cd.keys())
        # Также берём из _global (пользователи без чатов)
        all_uids.update(data.get("_global", {}).keys())

        sent, failed = 0, 0
        status_msg = await send_raw(
            message.chat.id,
            f"📣 Рассылка запущена... (0/{len(all_uids)})",
        )

        for i, uid_str in enumerate(all_uids, 1):
            try:
                target_id = int(uid_str)
                if is_banned(data, target_id):
                    continue
                await send_raw(target_id, f"📣 <b>Сообщение от администратора:</b>\n\n{text}")
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)  # Flood control

        await send_raw(
            message.chat.id,
            f"📣 <b>Рассылка завершена!</b>\n\n"
            f"{E.CHECK} Доставлено: <b>{sent}</b>\n"
            f"{E.CROSS} Не доставлено: <b>{failed}</b>",
        )

# ══════════════════════════════════════════════
#  ПРИВЕТСТВИЕ В ГРУППЕ
# ══════════════════════════════════════════════

@dp.message(F.new_chat_members)
async def new_members(message: Message):
    me = await bot.get_me()
    for m in message.new_chat_members:
        if m.id == me.id:
            await send_raw(
                message.chat.id,
                f"{E.ALIEN} Привет! Я <b>PipisaMod</b>!\n\n"
                f"{E.DICK} /dick — каждые 30 минут\n"
                f"{E.GIFT} /daily — ежедневный бонус\n"
                f"{E.PEOPLE} /ref — реферальная система\n\n"
                f"{E.CHANNEL} {CHANNEL_LINK}\n"
                f"❓ /help",
            )

# ══════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════

async def on_startup():
    await get_session()
    await set_commands()
    print("✅ PipisaMod запущен!")

async def on_shutdown():
    global _session
    if _session and not _session.closed:
        await _session.close()
    print("🛑 Бот остановлен.")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )

if __name__ == "__main__":
    asyncio.run(main())