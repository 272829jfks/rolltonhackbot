#!/usr/bin/env python3
"""RolltonHack Telegram bot — fixed captcha + Railway-friendly state."""
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
SBP_HINT = os.environ.get(
    "SBP_HINT",
    "Перевод 300₽ на карту — укажи реквизиты в переменной SBP_HINT",
)
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.environ.get("TOKEN_FILE", os.path.join(HERE, "tokens.json"))
API = "https://api.telegram.org/bot%s/" % TOKEN

# In-memory (survives while process is up — important for Railway)
USERS = {}  # uid -> dict
OFFSET = 0


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
        print("send error", e)
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
    op = random.choice(["+", "-"])
    if op == "+":
        return f"{a}+{b}", a + b
    if a < b:
        a, b = b, a
    return f"{a}-{b}", a - b


T = {
    "en": {
        "captcha": "Solve: {} = ?",
        "bad": "Wrong. Try again: {} = ?",
        "lang": "Choose language:",
        "hello": "Welcome to RolltonHack.\nBuy access to get a license token.",
        "buy": "Access: 300 RUB (card) or 150 Stars.",
        "btn_buy": "Buy access",
        "btn_stars": "Pay 150 Stars",
        "btn_card": "Pay 300 RUB card",
        "device": "Your device?",
        "btn_win": "Windows",
        "btn_and": "Android",
        "card": "Transfer 300 RUB:\n{}\nThen send /paid",
        "wait": "Waiting for admin confirmation.",
        "token": "Your token:\n<code>{}</code>\nEnter it when the app asks for the code.",
        "win": "Windows: unzip → start.bat → enter token → Chrome debug → chess.com",
        "and": "Android: Kiwi/Firefox + Violentmonkey → rolltonhack.mobile.user.js → chess.com",
    },
    "ru": {
        "captcha": "Реши пример: {} = ?",
        "bad": "Неверно. Ещё раз: {} = ?",
        "lang": "Выбери язык:",
        "hello": "Привет. Это бот доступа RolltonHack.\nПосле оплаты выдаётся токен.",
        "buy": "Доступ: 300 ₽ (карта) или 150 Stars.",
        "btn_buy": "Купить доступ",
        "btn_stars": "Оплатить 150 Stars",
        "btn_card": "Оплатить 300 ₽ картой",
        "device": "Твоё устройство?",
        "btn_win": "Windows",
        "btn_and": "Android",
        "card": "Переведи 300 ₽:\n{}\nПотом напиши /paid",
        "wait": "Ждём подтверждение админа.",
        "token": "Твой токен:\n<code>{}</code>\nВведи при запуске приложения.",
        "win": "Windows: zip → start.bat → токен → Chrome с отладкой → chess.com",
        "and": "Android: Kiwi/Firefox + Violentmonkey → userscript → chess.com",
    },
}


def tr(u, key):
    lang = u.get("lang") or "ru"
    return T.get(lang, T["ru"]).get(key, key)


def issue_token(uid, device):
    tok = gen_token()
    data = load_tokens()
    data.setdefault("tokens", []).append(tok)
    data.setdefault("issued", []).append(
        {"token": tok, "uid": uid, "device": device, "ts": int(time.time())}
    )
    save_tokens(data)
    return tok


def user(uid):
    uid = str(uid)
    if uid not in USERS:
        USERS[uid] = {"step": "captcha"}
    return USERS[uid]


def start_captcha(chat_id, u):
    q, a = math_captcha()
    u["step"] = "captcha"
    u["ans"] = a
    send(chat_id, tr(u, "captcha").format(q))


def handle_message(msg):
    chat = msg["chat"]["id"]
    fr = msg.get("from") or {}
    uid = str(fr.get("id") or chat)
    text = (msg.get("text") or "").strip()
    u = user(uid)

    # --- admin ---
    if ADMIN_CHAT_ID and str(chat) == str(ADMIN_CHAT_ID):
        if text.startswith("/approve "):
            target = text.split(maxsplit=1)[1].strip()
            tu = USERS.get(target) or {"lang": "ru", "device": "windows"}
            device = tu.get("device") or "windows"
            tok = issue_token(target, device)
            send(int(target), tr(tu, "token").format(tok))
            send(int(target), tr(tu, "win") if device == "windows" else tr(tu, "and"))
            send(chat, f"OK {target}: {tok}")
            tu["step"] = "done"
            return
        if text == "/tokens":
            send(chat, json.dumps(load_tokens(), ensure_ascii=False)[:3500])
            return

    # --- /start always resets captcha once ---
    if text == "/start":
        start_captcha(chat, u)
        return

    # --- captcha (only one answer expected) ---
    if u.get("step") == "captcha":
        if "ans" not in u:
            start_captcha(chat, u)
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
        # success — leave captcha permanently
        u.pop("ans", None)
        u["step"] = "lang"
        send(
            chat,
            tr(u, "lang"),
            reply_markup={
                "keyboard": [[{"text": "English"}, {"text": "Русский"}]],
                "resize_keyboard": True,
            },
        )
        return

    # --- language ---
    if u.get("step") == "lang":
        if text.lower().startswith("eng"):
            u["lang"] = "en"
        else:
            u["lang"] = "ru"
        u["step"] = "hello"
        send(
            chat,
            tr(u, "hello"),
            reply_markup={
                "keyboard": [[{"text": tr(u, "btn_buy")}]],
                "resize_keyboard": True,
            },
        )
        return

    # --- buy menu ---
    if u.get("step") in ("hello", "buy"):
        if text == tr(u, "btn_buy") or "куп" in text.lower() or text.lower() == "buy access":
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
            except Exception as e:
                send(chat, f"Stars error: {e}\nUse card payment.")
            u["step"] = "device"
            send(
                chat,
                tr(u, "device"),
                reply_markup={
                    "keyboard": [[{"text": tr(u, "btn_win")}, {"text": tr(u, "btn_and")}]],
                    "resize_keyboard": True,
                },
            )
            return
        # card
        u["step"] = "wait_pay"
        send(chat, tr(u, "card").format(SBP_HINT))
        if ADMIN_CHAT_ID:
            send(int(ADMIN_CHAT_ID), f"Card pay pending uid={uid}. After check: /approve {uid}")
        return

    if u.get("step") == "wait_pay" and text.startswith("/paid"):
        send(chat, tr(u, "wait"))
        if ADMIN_CHAT_ID:
            send(int(ADMIN_CHAT_ID), f"User {uid} /paid. /approve {uid}")
        return

    if u.get("step") in ("device", "wait_pay"):
        low = text.lower()
        if "android" in low or "андр" in low:
            u["device"] = "android"
            u["step"] = "wait_pay"
            send(chat, tr(u, "wait") if not u.get("paid") else "")
            if u.get("paid"):
                tok = issue_token(uid, "android")
                send(chat, tr(u, "token").format(tok))
                send(chat, tr(u, "and"))
                u["step"] = "done"
            return
        if "win" in low or "винд" in low:
            u["device"] = "windows"
            u["step"] = "wait_pay"
            if u.get("paid"):
                tok = issue_token(uid, "windows")
                send(chat, tr(u, "token").format(tok))
                send(chat, tr(u, "win"))
                u["step"] = "done"
            else:
                send(chat, tr(u, "wait"))
            return

    # fallback
    if u.get("step") == "done":
        send(chat, tr(u, "token").format("(уже выдан)") if False else "OK. /start to restart.")
        return
    start_captcha(chat, u)


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
        u["step"] = "device"
        send(
            msg["chat"]["id"],
            tr(u, "device"),
            reply_markup={
                "keyboard": [[{"text": tr(u, "btn_win")}, {"text": tr(u, "btn_and")}]],
                "resize_keyboard": True,
            },
        )
        return
    handle_message(msg)


def main():
    global OFFSET
    if not TOKEN:
        print("Set TELEGRAM_BOT_TOKEN")
        raise SystemExit(1)
    print("RolltonHack bot running...", flush=True)
    # drop pending updates so old /start flood does not replay
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
