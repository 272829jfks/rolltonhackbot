#!/usr/bin/env python3
"""
RolltonHack Telegram bot — captcha, language, sell token.
Admin: set env TELEGRAM_BOT_TOKEN and ADMIN_CHAT_ID
SBP: set SBP_HINT text (your phone/card for transfer)
Stars: amount 150 (Telegram Stars) via invoice
RUB: 300 via manual SBP + admin /approve
"""
import hashlib
import json
import os
import random
import secrets
import string
import time
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "").strip()  # your telegram user id
SBP_HINT = os.environ.get("SBP_HINT", "СБП перевод 300₽ — напишите админу реквизиты в @rolltonvsky")
HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "bot_state.json")
TOKEN_FILE = os.path.join(HERE, "tokens.json")
API = "https://api.telegram.org/bot%s/" % TOKEN

# in-memory + disk
def load_state():
    if os.path.isfile(STATE_FILE):
        try:
            return json.load(open(STATE_FILE, "r", encoding="utf-8"))
        except Exception:
            pass
    return {"users": {}, "offset": 0}

def save_state(st):
    json.dump(st, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def load_tokens():
    if os.path.isfile(TOKEN_FILE):
        try:
            return json.load(open(TOKEN_FILE, "r", encoding="utf-8"))
        except Exception:
            pass
    return {"tokens": []}

def save_tokens(data):
    json.dump(data, open(TOKEN_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def api(method, **params):
    if not TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN")
    data = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
    req = urllib.request.Request(API + method, data=data)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def send(chat_id, text, reply_markup=None):
    params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    return api("sendMessage", **params)

def gen_token():
    return "RH-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))

def math_captcha():
    a, b = random.randint(2, 12), random.randint(2, 12)
    op = random.choice(["+", "*", "-"])
    if op == "+":
        ans = a + b
        q = f"{a}+{b}"
    elif op == "*":
        ans = a * b
        q = f"{a}*{b}"
    else:
        if a < b:
            a, b = b, a
        ans = a - b
        q = f"{a}-{b}"
    return q, ans

T = {
    "en": {
        "captcha": "Solve: <b>{}</b> = ?",
        "bad_captcha": "Wrong. New example:",
        "pick_lang": "Choose bot language:",
        "hello": "Welcome to RolltonHack support bot.\nAccess = analysis tool license token.",
        "buy": "Buy access — 300 RUB\n• Card / SBP: 300₽\n• Telegram Stars: 150 ⭐",
        "btn_buy": "Buy access",
        "btn_stars": "Pay 150 Stars",
        "btn_sbp": "Pay 300₽ SBP",
        "device": "Your device?",
        "btn_win": "Windows",
        "btn_and": "Android",
        "sbp": "Transfer 300₽ via SBP.\n{}\nThen send /paid to this bot. Admin will confirm and send token.",
        "wait_admin": "Payment pending admin confirmation.",
        "token": "Your token:\n<code>{}</code>\nEnter it when the app asks for access code.",
        "win_help": "Windows: unzip, run start.bat, enter token, open chess.com via debug Chrome.",
        "and_help": "Android: install Violentmonkey in Kiwi/Firefox, add rolltonhack.mobile.user.js from the package, open chess.com.",
        "no_file": "Package files are delivered by admin after payment.",
    },
    "ru": {
        "captcha": "Реши пример: <b>{}</b> = ?",
        "bad_captcha": "Неверно. Новый пример:",
        "pick_lang": "Выбери язык бота:",
        "hello": "Привет. Это бот доступа RolltonHack.\nПосле оплаты выдаётся токен для запуска.",
        "buy": "Купить доступ — 300 ₽\n• Карта / СБП: 300₽\n• Telegram Stars: 150 ⭐",
        "btn_buy": "Купить доступ",
        "btn_stars": "Оплатить 150 Stars",
        "btn_sbp": "Оплатить 300₽ СБП",
        "device": "Твоё устройство?",
        "btn_win": "Windows",
        "btn_and": "Android",
        "sbp": "Переведи 300₽ по СБП.\n{}\nПотом напиши /paid. Админ подтвердит и пришлёт токен.",
        "wait_admin": "Ожидаем подтверждение оплаты админом.",
        "token": "Твой токен:\n<code>{}</code>\nВведи его при запуске приложения.",
        "win_help": "Windows: распакуй zip → start.bat → введи токен → Chrome с отладкой → chess.com",
        "and_help": "Android: Kiwi/Firefox + Violentmonkey → поставь rolltonhack.mobile.user.js → chess.com",
        "no_file": "Файлы пакета выдаёт админ после оплаты.",
    },
}

def tr(uid, key):
    st = load_state()
    lang = (st["users"].get(str(uid)) or {}).get("lang", "ru")
    return T.get(lang, T["ru"]).get(key, key)

def issue_token(uid, device):
    tok = gen_token()
    data = load_tokens()
    data.setdefault("tokens", []).append(tok)
    data.setdefault("issued", []).append({"token": tok, "uid": uid, "device": device, "ts": int(time.time())})
    save_tokens(data)
    return tok

def handle_message(msg):
    chat = msg["chat"]["id"]
    uid = str(msg.from_user.id if hasattr(msg, 'from_user') else msg["from"]["id"])
    text = (msg.get("text") or "").strip()
    st = load_state()
    u = st["users"].setdefault(uid, {"step": "captcha"})

    # admin commands
    if ADMIN_CHAT_ID and str(chat) == str(ADMIN_CHAT_ID):
        if text.startswith("/approve "):
            target = text.split(maxsplit=1)[1].strip()
            tu = st["users"].get(target)
            if not tu:
                send(chat, "user not found")
                return
            device = tu.get("device", "windows")
            tok = issue_token(target, device)
            send(int(target), tr(target, "token").format(tok))
            send(int(target), tr(target, "win_help") if device == "windows" else tr(target, "and_help"))
            send(chat, f"OK token for {target}: {tok}")
            tu["step"] = "done"
            save_state(st)
            return
        if text == "/tokens":
            send(chat, json.dumps(load_tokens(), ensure_ascii=False)[:3500])
            return

    # captcha
    if u.get("step") == "captcha" or "captcha_ans" not in u:
        if "captcha_ans" not in u:
            q, a = math_captcha()
            u["captcha_ans"] = a
            u["step"] = "captcha"
            save_state(st)
            send(chat, (T["ru"]["captcha"] if u.get("lang") != "en" else T["en"]["captcha"]).format(q))
            return
        try:
            if int(text) != int(u["captcha_ans"]):
                q, a = math_captcha()
                u["captcha_ans"] = a
                save_state(st)
                lang = u.get("lang", "ru")
                send(chat, T[lang]["bad_captcha"] + "\n" + T[lang]["captcha"].format(q))
                return
        except Exception:
            q, a = math_captcha()
            u["captcha_ans"] = a
            save_state(st)
            send(chat, T["ru"]["captcha"].format(q))
            return
        u["step"] = "lang"
        del u["captcha_ans"]
        save_state(st)
        send(chat, "Choose language / Выбери язык:", reply_markup={
            "keyboard": [[{"text": "English"}, {"text": "Русский"}]],
            "resize_keyboard": True,
        })
        return

    if u.get("step") == "lang":
        if text.lower().startswith("eng"):
            u["lang"] = "en"
        else:
            u["lang"] = "ru"
        u["step"] = "hello"
        save_state(st)
        send(chat, tr(uid, "hello"), reply_markup={
            "keyboard": [[{"text": tr(uid, "btn_buy")}]],
            "resize_keyboard": True,
        })
        return

    if u.get("step") in ("hello", "buy") and (text == tr(uid, "btn_buy") or text.lower() in ("buy", "купить", "купить доступ")):
        u["step"] = "pay"
        save_state(st)
        send(chat, tr(uid, "buy"), reply_markup={
            "keyboard": [
                [{"text": tr(uid, "btn_stars")}],
                [{"text": tr(uid, "btn_sbp")}],
            ],
            "resize_keyboard": True,
        })
        return

    if u.get("step") == "pay":
        if "star" in text.lower() or "⭐" in text or "150" in text:
            # Stars invoice
            try:
                api(
                    "sendInvoice",
                    chat_id=chat,
                    title="RolltonHack Access",
                    description="License token 30 days",
                    payload="rh_access_" + uid,
                    currency="XTR",
                    prices=json.dumps([{"label": "Access", "amount": 150}]),
                    provider_token="",  # empty for Stars
                )
            except Exception as e:
                send(chat, f"Stars invoice error: {e}\nUse SBP or contact admin.")
            u["step"] = "device"
            save_state(st)
            send(chat, tr(uid, "device"), reply_markup={
                "keyboard": [[{"text": tr(uid, "btn_win")}, {"text": tr(uid, "btn_and")}]],
                "resize_keyboard": True,
            })
            return
        # SBP
        u["step"] = "wait_sbp"
        save_state(st)
        send(chat, tr(uid, "sbp").format(SBP_HINT))
        if ADMIN_CHAT_ID:
            send(int(ADMIN_CHAT_ID), f"SBP pending from uid={uid} chat={chat}. /approve {uid}")
        return

    if u.get("step") == "wait_sbp" and text.startswith("/paid"):
        send(chat, tr(uid, "wait_admin"))
        if ADMIN_CHAT_ID:
            send(int(ADMIN_CHAT_ID), f"User {uid} claims paid. /approve {uid}")
        return

    if u.get("step") in ("device", "pay", "wait_sbp"):
        low = text.lower()
        if "android" in low or "андр" in low:
            u["device"] = "android"
        elif "win" in low or "винд" in low:
            u["device"] = "windows"
        if u.get("device") and u.get("step") == "device":
            # if stars already paid path without admin — still need successful_payment update
            send(chat, tr(uid, "wait_admin") if not u.get("paid") else "")
            if u.get("paid"):
                tok = issue_token(uid, u["device"])
                send(chat, tr(uid, "token").format(tok))
                send(chat, tr(uid, "win_help") if u["device"] == "windows" else tr(uid, "and_help"))
                u["step"] = "done"
            save_state(st)
            return

    if text == "/start":
        st["users"][uid] = {"step": "captcha"}
        save_state(st)
        q, a = math_captcha()
        st["users"][uid]["captcha_ans"] = a
        save_state(st)
        send(chat, T["ru"]["captcha"].format(q))
        return

    send(chat, "/start")


def handle_update(upd):
    if "message" in upd:
        # successful_payment (Stars)
        msg = upd["message"]
        if "successful_payment" in msg:
            uid = str(msg["from"]["id"])
            chat = msg["chat"]["id"]
            st = load_state()
            u = st["users"].setdefault(uid, {})
            u["paid"] = True
            u["step"] = "device"
            save_state(st)
            send(chat, tr(uid, "device"), reply_markup={
                "keyboard": [[{"text": tr(uid, "btn_win")}, {"text": tr(uid, "btn_and")}]],
                "resize_keyboard": True,
            })
            return
        if "pre_checkout_query" in upd:
            return
        handle_message(msg)
    if "pre_checkout_query" in upd:
        api("answerPreCheckoutQuery", pre_checkout_query_id=upd["pre_checkout_query"]["id"], ok=True)


def main():
    if not TOKEN:
        print("Set TELEGRAM_BOT_TOKEN env var (from @BotFather)")
        print("Optional: ADMIN_CHAT_ID, SBP_HINT")
        sys_exit = __import__("sys").exit
        sys_exit(1)
    print("RolltonHack bot running...")
    st = load_state()
    offset = st.get("offset", 0)
    while True:
        try:
            res = api("getUpdates", offset=offset, timeout=50)
            for upd in res.get("result") or []:
                offset = upd["update_id"] + 1
                st["offset"] = offset
                save_state(st)
                try:
                    handle_update(upd)
                except Exception as e:
                    print("handle", e)
        except Exception as e:
            print("poll", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
