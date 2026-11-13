#!/usr/bin/env python3
"""RolltonHack bot: lang → captcha → buy; card bank tips; admin panel."""
import json
import os
import random
import secrets
import string
import time
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "").strip()
# same master as app license, or set ADMIN_TOKEN env
ADMIN_TOKEN = os.environ.get(
    "ADMIN_TOKEN", "adminrolltonvsky2345ghfgrgdtrhgytyr5ryhgf"
).strip()
CARD_HINT = os.environ.get(
    "SBP_HINT",
    "Карта: укажи номер в переменной SBP_HINT на Railway",
)
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.environ.get("TOKEN_FILE", os.path.join(HERE, "tokens.json"))
API = "https://api.telegram.org/bot%s/" % TOKEN

USERS = {}
OFFSET = 0
ADMINS = set()  # uid strings after admin login
if ADMIN_CHAT_ID:
    ADMINS.add(str(ADMIN_CHAT_ID))


def api(method, **params):
    data = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
    req = urllib.request.Request(API + method, data=data)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def send(chat_id, text, reply_markup=None):
    params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    try:
        return api("sendMessage", **params)
    except Exception as e:
        print("send", e)
        return None


def load_tokens():
    if os.path.isfile(TOKEN_FILE):
        try:
            return json.load(open(TOKEN_FILE, "r", encoding="utf-8"))
        except Exception:
            pass
    return {"tokens": [], "issued": []}


def save_tokens(data):
    try:
        json.dump(data, open(TOKEN_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception as e:
        print("save_tokens", e)


def gen_token():
    return "RH-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))


def math_captcha():
    a, b = random.randint(2, 9), random.randint(1, 9)
    if random.choice([0, 1]) == 0:
        return f"{a}+{b}", a + b
    if a < b:
        a, b = b, a
    return f"{a}-{b}", a - b


# Bank tips — real auto SBP-link to personal card is impossible without merchant.
# We give clear transfer instructions per bank.
BANK_HELP = {
    "sber": (
        "🟢 <b>Сбербанк</b>\n"
        "1. Открой Сбер → Платежи → На карту в другом банке / перевод по номеру карты\n"
        "2. Сумма <b>300 ₽</b>\n"
        "3. Карта получателя:\n<code>{card}</code>\n"
        "4. После перевода нажми /paid"
    ),
    "tinkoff": (
        "🟡 <b>Т‑Банк (Тинькофф)</b>\n"
        "1. Приложение → Платежи → На карту\n"
        "2. Вставь номер карты, сумма <b>300 ₽</b>\n"
        "3. Карта:\n<code>{card}</code>\n"
        "4. После перевода /paid"
    ),
    "vtb": (
        "🔵 <b>ВТБ</b>\n"
        "1. Платежи → Перевод на карту другого банка\n"
        "2. Сумма <b>300 ₽</b>, карта:\n<code>{card}</code>\n"
        "3. После перевода /paid"
    ),
    "alfa": (
        "🔴 <b>Альфа‑Банк</b>\n"
        "1. Переводы → На карту в другой банк\n"
        "2. <b>300 ₽</b>, карта:\n<code>{card}</code>\n"
        "3. После перевода /paid"
    ),
    "other": (
        "💳 <b>Другой банк</b>\n"
        "Перевод на карту <b>300 ₽</b>:\n<code>{card}</code>\n"
        "Через СБП (если карта привязана к телефону) или перевод по номеру карты.\n"
        "После перевода нажми /paid"
    ),
}

T = {
    "en": {
        "lang": "Choose language / Выбери язык:",
        "captcha": "Solve: {} = ?",
        "bad": "Wrong. Try: {} = ?",
        "hello": "RolltonHack access.\nPay → device → token.",
        "buy": "Access: 300 RUB (card) or 150 Stars.",
        "btn_buy": "Buy access",
        "btn_stars": "Pay 150 Stars",
        "btn_card": "Pay 300 RUB card",
        "bank": "Which bank do you pay from?",
        "device": "Your device?",
        "btn_win": "Windows",
        "btn_and": "Android",
        "token": "Your token:\n<code>{}</code>",
        "win": "Windows: start.bat → enter token → Chrome debug → chess.com",
        "and": "Android: userscript in Kiwi/Firefox → chess.com",
        "need_pay": "Pay first, then /paid or complete Stars.",
        "admin_ask": "Enter admin token:",
        "admin_ok": "Admin OK. Commands:\n/tokens — list\n/stats — count\n/broadcast text — message all known users (session only)",
        "admin_bad": "Wrong admin token.",
        "btn_admin": "I am admin",
        "btn_help": "Помощь",   # en: "Help"
"help": "По всем вопросам: Telegram @rolltonvsky",
    },
    "ru": {
        "lang": "Выбери язык / Choose language:",
        "captcha": "Реши пример: {} = ?",
        "bad": "Неверно. Ещё раз: {} = ?",
        "hello": "Бот доступа RolltonHack.\nОплата → устройство → токен.",
        "buy": "Доступ: 300 ₽ (карта) или 150 Stars.",
        "btn_buy": "Купить доступ",
        "btn_stars": "Оплатить 150 Stars",
        "btn_card": "Оплатить 300 ₽ картой",
        "bank": "С какого банка платишь?",
        "device": "Твоё устройство?",
        "btn_win": "Windows",
        "btn_and": "Android",
        "token": "Твой токен:\n<code>{}</code>",
        "win": "Windows: start.bat → токен → Chrome с отладкой → chess.com",
        "and": "Android: userscript в Kiwi/Firefox → chess.com",
        "need_pay": "Сначала оплати, потом /paid или Stars.",
        "admin_ask": "Введи токен админа:",
        "admin_ok": "Админ OK. Команды:\n/tokens — список\n/stats — число\n/broadcast текст",
        "admin_bad": "Неверный токен админа.",
        "btn_admin": "Я админ",
        "btn_help": "Помощь",   # en: "Help"
"help": "По всем вопросам: Telegram @rolltonvsky",
    },
}


def tr(u, key):
    return T.get(u.get("lang") or "ru", T["ru"]).get(key, key)


def issue_token(uid, device):
    tok = gen_token()
    data = load_tokens()
    data.setdefault("tokens", []).append(tok)
    data.setdefault("issued", []).append(
        {"token": tok, "uid": str(uid), "device": device, "ts": int(time.time())}
    )
    save_tokens(data)
    return tok


def deliver(chat_id, u, uid, device):
    u["device"] = device
    tok = issue_token(uid, device)
    u["step"] = "done"
    u["paid"] = True
    send(chat_id, tr(u, "token").format(tok))
    send(chat_id, tr(u, "win") if device == "windows" else tr(u, "and"))
    if ADMIN_CHAT_ID:
        try:
            send(int(ADMIN_CHAT_ID), f"Issued {tok} → {uid} ({device})")
        except Exception:
            pass


def user(uid):
    uid = str(uid)
    if uid not in USERS:
        USERS[uid] = {"step": "lang", "lang": "ru"}
    return USERS[uid]


def ask_device(chat_id, u):
    u["step"] = "device"
    send(
        chat_id,
        tr(u, "device"),
        reply_markup={
            "keyboard": [[{"text": tr(u, "btn_win")}, {"text": tr(u, "btn_and")}]],
            "resize_keyboard": True,
        },
    )


def main_kb(u):
    return {
        "keyboard": [
            [{"text": tr(u, "btn_buy")}],
            [{"text": tr(u, "btn_admin")}],
            [{"text": tr(u, "btn_help")}],
        ],
        "resize_keyboard": True,
    }


def handle_message(msg):
    chat = msg["chat"]["id"]
    fr = msg.get("from") or {}
    uid = str(fr.get("id") or chat)
    text = (msg.get("text") or "").strip()
    u = user(uid)

    # --- admin commands if already authed ---
    if uid in ADMINS:
        if text == "/tokens":
            send(chat, json.dumps(load_tokens(), ensure_ascii=False)[:3500])
            return
        if text == "/stats":
            d = load_tokens()
            send(chat, f"tokens: {len(d.get('tokens') or [])}\nissued: {len(d.get('issued') or [])}\nsession users: {len(USERS)}")
            return
        if text.startswith("/broadcast "):
            body = text.split(maxsplit=1)[1]
            n = 0
            for ouid in list(USERS.keys()):
                try:
                    send(int(ouid), body)
                    n += 1
                except Exception:
                    pass
            send(chat, f"sent: {n}")
            return

    if text == "/start":
        u.clear()
        u["step"] = "lang"
        u["lang"] = "ru"
        send(
            chat,
            "Choose language / Выбери язык:",
            reply_markup={
                "keyboard": [[{"text": "English"}, {"text": "Русский"}]],
                "resize_keyboard": True,
            },
        )
        return

    # language FIRST
    if u.get("step") == "lang":
        if text.lower().startswith("eng"):
            u["lang"] = "en"
        elif "рус" in text.lower() or text.lower() == "ru":
            u["lang"] = "ru"
        else:
            send(
                chat,
                "English / Русский",
                reply_markup={
                    "keyboard": [[{"text": "English"}, {"text": "Русский"}]],
                    "resize_keyboard": True,
                },
            )
            return
        q, a = math_captcha()
        u["step"] = "captcha"
        u["ans"] = a
        send(chat, tr(u, "captcha").format(q))
        return

    if u.get("step") == "captcha":
        if "ans" not in u:
            q, a = math_captcha()
            u["ans"] = a
            send(chat, tr(u, "captcha").format(q))
            return
        try:
            ok = int(text.replace(" ", "")) == int(u["ans"])
        except Exception:
            ok = False
        if not ok:
            q, a = math_captcha()
            u["ans"] = a
            send(chat, tr(u, "bad").format(q))
            return
        u.pop("ans", None)
        u["step"] = "hello"
        send(chat, tr(u, "hello"), reply_markup=main_kb(u))
        return

    # admin entry
    if text == tr(u, "btn_admin") or text.lower() in ("я админ", "i am admin", "/admin"):
        u["step"] = "admin_auth"
        send(chat, tr(u, "admin_ask"))
        return

    if u.get("step") == "admin_auth":
        if text.strip() == ADMIN_TOKEN:
            ADMINS.add(uid)
            u["step"] = "hello"
            send(chat, tr(u, "admin_ok"), reply_markup=main_kb(u))
        else:
            u["step"] = "hello"
            send(chat, tr(u, "admin_bad"), reply_markup=main_kb(u))
        return

    if u.get("step") in ("hello", "buy"):
        if text == tr(u, "btn_buy") or "куп" in text.lower() or "buy" in text.lower():
            u["step"] = "pay"
            send(
                chat,
                tr(u, "buy"),
                reply_markup={
                    "keyboard": [
                        [{"text": tr(u, "btn_stars")}],
                        [{"text": tr(u, "btn_card")}],
                    ],
                    "resize_keyboard": True,
                },
            )
            return

    if u.get("step") == "pay":
        low = text.lower()
        if "star" in low or "⭐" in text or "150" in text:
            try:
                api(
                    "sendInvoice",
                    chat_id=chat,
                    title="RolltonHack Access",
                    description="License token",
                    payload="rh_" + uid,
                    currency="XTR",
                    prices=json.dumps([{"label": "Access", "amount": 150}]),
                    provider_token="",
                )
                u["step"] = "wait_stars"
                send(chat, "⭐ Оплати счёт. После оплаты — устройство и токен.")
            except Exception as e:
                send(chat, f"Stars error: {e}")
            return
        if "карт" in low or "card" in low or "300" in text:
            u["step"] = "bank"
            send(
                chat,
                tr(u, "bank"),
                reply_markup={
                    "keyboard": [
                        [{"text": "Сбер"}, {"text": "Т-Банк"}],
                        [{"text": "ВТБ"}, {"text": "Альфа"}],
                        [{"text": "Другой банк"}],
                    ],
                    "resize_keyboard": True,
                },
            )
            return

    if u.get("step") == "bank":
        low = text.lower().replace("ё", "е")
        key = "other"
        if "сбер" in low or "sber" in low:
            key = "sber"
        elif "тин" in low or "т-банк" in low or "tink" in low or "т банк" in low:
            key = "tinkoff"
        elif "втб" in low or "vtb" in low:
            key = "vtb"
        elif "альф" in low or "alfa" in low:
            key = "alfa"
        msg_txt = BANK_HELP[key].format(card=CARD_HINT)
        msg_txt += (
            "\n\n⚠️ Бот не открывает платёж в банке сам — "
            "нужен перевод вручную на указанную карту (без договора мерчанта автоссылка СБП недоступна)."
        )
        u["step"] = "wait_card"
        send(chat, msg_txt)
        return

    if u.get("step") == "wait_card" and text.startswith("/paid"):
        u["paid"] = True
        ask_device(chat, u)
        return

    if u.get("step") == "device":
        if not u.get("paid"):
            send(chat, tr(u, "need_pay"))
            return
        low = text.lower()
        if "android" in low or "андр" in low:
            deliver(chat, u, uid, "android")
            return
        if "win" in low or "винд" in low:
            deliver(chat, u, uid, "windows")
            return
        ask_device(chat, u)
        return

    if u.get("step") == "done":
        send(chat, "Токен уже выдан. /start — сначала.")
        return
    
    if text == tr(u, "btn_help") or text.lower() in ("помощь", "help"):
    send(chat, tr(u, "help"), reply_markup=main_kb(u))
    return

    if text.strip() == ADMIN_TOKEN:
    ADMINS.add(uid)
    u["step"] = "hello"
    u["paid"] = True
    send(chat, tr(u, "admin_ok"), reply_markup=main_kb(u))
    # тест выдачи:
    deliver(chat, u, uid, "windows")  # или спроси устройство
    return

    if uid in ADMINS:
    u["paid"] = True
    ask_device(chat, u)
    return

    # fallback
    if u.get("step") == "hello":
        send(chat, tr(u, "hello"), reply_markup=main_kb(u))
        return
    u["step"] = "lang"
    send(
        chat,
        "Choose language / Выбери язык:",
        reply_markup={"keyboard": [[{"text": "English"}, {"text": "Русский"}]], "resize_keyboard": True},
    )


def handle_update(upd):
    if "pre_checkout_query" in upd:
        try:
            api(
                "answerPreCheckoutQuery",
                pre_checkout_query_id=upd["pre_checkout_query"]["id"],
                ok=True,
            )
        except Exception as e:
            print("pre_checkout", e)
        return
    msg = upd.get("message") or upd.get("edited_message")
    if not msg:
        return
    if "successful_payment" in msg:
        fr = msg.get("from") or {}
        uid = str(fr.get("id") or msg["chat"]["id"])
        u = user(uid)
        u["paid"] = True
        ask_device(msg["chat"]["id"], u)
        return
    handle_message(msg)


def main():
    global OFFSET
    if not TOKEN:
        print("Set TELEGRAM_BOT_TOKEN")
        raise SystemExit(1)
    print("RolltonHack bot running...", flush=True)
    try:
        res = api("getUpdates", offset=-1, timeout=0)
        for upd in res.get("result") or []:
            OFFSET = upd["update_id"] + 1
    except Exception as e:
        print("offset", e)
    while True:
        try:
            res = api("getUpdates", offset=OFFSET, timeout=50)
            for upd in res.get("result") or []:
                OFFSET = upd["update_id"] + 1
                try:
                    handle_update(upd)
                except Exception as e:
                    print("handle", e)
        except Exception as e:
            print("poll", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
