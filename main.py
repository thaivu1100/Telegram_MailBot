#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
telegram_mailbot_v2.py — bản sửa nâng cấp
- Đã chuyển sang dùng Replit DB (Ổn định 24/7, không mất dữ liệu)
- Đã thêm Keep-Alive (Dùng Flask)
- Kiểm tra người dùng, Thêm Donate, Lệnh /thongke
"""

import telebot
import requests
import random
import string
import time
import re
import threading
from flask import Flask 
from replit import db # <<< THAY THẾ SQLITE BẰNG REPLIT DB
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===== CẤU HÌNH ===== #
BOT_TOKEN = "8206084388:AAGnE9FhjAeXWEyPt4wExZ1un2pf5OivjrA"
ADMIN_TG_ID = 6327666718 # ID Telegram của bạn

GROUPS = {
    "nhom1": {"title": "💬 Nhóm 1", "username": "@keokiemtienmienphiuytin", "link": "https://t.me/keokiemtienmienphiuytin"},
    "nhom2": {"title": "💬 Nhóm 2", "username": "@keokiemtienfreeuytinso1", "link": "https://t.me/keokiemtienfreeuytinso1"},
    "nhom3": {"title": "💬 Nhóm 3", "username": "@thongbaoruttienkiemtienanvat", "link": "https://t.me/thongbaoruttienkiemtienanvat"},
    "nhom4": {"title": "💬 Nhóm 4", "username": "@nhomchatvuivenhamn", "link": "https://t.me/nhomchatvuivenhamn"},
}

MAILTM_BASE = "https://api.mail.tm"
SMS_PROVIDER = "sms24"

bot = telebot.TeleBot(BOT_TOKEN)

# ===== DATABASE (Sử dụng Replit DB) ===== #

# Khởi tạo DB nếu chưa có (Replit DB là một Dict/JSON)
def init_db():
    if "verified_users" not in db:
        db["verified_users"] = [] # Danh sách username đã xác minh
    if "mails_count" not in db:
        db["mails_count"] = 0 # Số lượng mail đã tạo
    if "phones_count" not in db:
        db["phones_count"] = 0 # Số lượng phone đã cấp

def is_verified(username):
    if not username:
        return False
    # Kiểm tra username có trong danh sách verified_users không
    return username.lower() in db["verified_users"]

def add_verified(username):
    username_lower = username.lower()
    if username_lower not in db["verified_users"]:
        # Thêm username vào danh sách
        db["verified_users"].append(username_lower)

# Hàm mới: Lưu mail đã tạo và cập nhật thống kê
def save_created_mail(tg_id, email, password, token, expires_at):
    # Tăng biến đếm tổng số mail
    db["mails_count"] += 1
    # Bạn có thể lưu chi tiết mail nếu cần, nhưng để đơn giản, ta chỉ lưu thống kê

# Hàm mới: Lưu phone đã cấp và cập nhật thống kê
def save_created_phone(tg_id, phone, service):
    # Tăng biến đếm tổng số phone
    db["phones_count"] += 1
    # Bạn có thể lưu chi tiết phone nếu cần, nhưng để đơn giản, ta chỉ lưu thống kê

# Hàm mới: Đếm người dùng đã xác minh
def count_verified_users():
    return len(db["verified_users"])

# Hàm mới: Đếm số lượng mail đã tạo
def count_created_mails():
    return db["mails_count"]

# Hàm mới: Đếm số lượng số điện thoại đã cấp
def count_created_phones():
    return db["phones_count"]


# ===== NHÓM VÀ CÁC HÀM KHÁC (GIỮ NGUYÊN) ===== #

def is_user_in_all_groups(bot, user_id):
    for _, g in GROUPS.items():
        try:
            member = bot.get_chat_member(g['username'], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except:
            return False
    return True

def join_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    for _, g in GROUPS.items():
        markup.add(InlineKeyboardButton(g['title'], url=g['link']))
    markup.add(InlineKeyboardButton("✅ Tôi đã tham gia đủ nhóm", callback_data="check_join"))
    return markup

# ===== MAIL.TM ===== #
def pick_domain():
    try:
        r = requests.get(f"{MAILTM_BASE}/domains", timeout=10)
        r.raise_for_status()
        data = r.json()
        members = data.get("hydra:member") or []
        if members:
            d = members[0]
            if isinstance(d, dict):
                return d.get("domain") or d.get("id")
            return str(d)
    except Exception:
        pass
    return "1secmail.org"

def random_localpart(n=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

def create_mailtm_account():
    try:
        domain = pick_domain()
        local = random_localpart(8)
        email = f"{local}@{domain}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        requests.post(f"{MAILTM_BASE}/accounts", json={"address": email, "password": password}, timeout=10)
        token_resp = requests.post(f"{MAILTM_BASE}/token", json={"address": email, "password": password}, timeout=10)
        token_resp.raise_for_status()
        token = token_resp.json().get("token")
        expires_at = int(time.time()) + 3600
        return email, password, token, expires_at
    except Exception:
        return None, None, None, None

# ===== MENU HANDLERS (GIỮ NGUYÊN) ===== #
@bot.message_handler(commands=['start'])
def cmd_start(m):
    username = m.from_user.username
    if is_verified(username) and is_user_in_all_groups(bot, m.from_user.id):
        send_main_menu(m.chat.id)
        return
    bot.send_message(m.chat.id, "👋 Xin chào!\nĐể sử dụng bot, bạn cần tham gia đủ nhóm sau:", reply_markup=join_keyboard())

@bot.message_handler(commands=['thongke'])
def cmd_thongke(m):
    if m.from_user.id != ADMIN_TG_ID:
        bot.send_message(m.chat.id, "❌ Lệnh này chỉ dành cho Admin.")
        return

    try:
        total_users = count_verified_users()
        total_mails = count_created_mails()
        total_phones = count_created_phones()

        stats_msg = (
            "📊 **BÁO CÁO THỐNG KÊ BOT** 📊\n\n"
            f"👤 **Tổng số người dùng (Đã xác minh):** `{total_users}`\n"
            f"📧 **Số Mail đã tạo:** `{total_mails}`\n"
            f"📱 **Số SĐT đã cấp:** `{total_phones}`\n\n"
            "_(Thống kê sử dụng Replit DB, dữ liệu vĩnh viễn)_"
        )
        
        bot.send_message(m.chat.id, stats_msg, parse_mode="Markdown")

    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Lỗi khi truy vấn thống kê: {e}")

def send_main_menu(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📧 GetMail (No Pass)", "🔐 GetMail (With Pass)")
    markup.add("📩 Check Inbox Mail", "📱 GetPhone")
    markup.add("📲 Check SMS Phone", "💖 Donate cho Admin")
    bot.send_message(chat_id, "🎉 Bạn đã xác minh! Chọn chức năng:", reply_markup=markup)

# ===== CALLBACK ===== #
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    username = call.from_user.username
    if not username:
        bot.send_message(call.message.chat.id, "⚠️ Vui lòng đặt username Telegram để xác minh.")
        return
    if is_user_in_all_groups(bot, call.from_user.id):
        add_verified(username)
        bot.send_message(call.message.chat.id, "✅ Xác minh thành công! Bạn có thể sử dụng bot.")
        send_main_menu(call.message.chat.id)
    else:
        bot.send_message(call.message.chat.id, "❌ Bạn chưa tham gia đủ nhóm.", reply_markup=join_keyboard())

# ===== HANDLE MENU ===== #
@bot.message_handler(func=lambda m: True)
def handle_menu(m):
    username = m.from_user.username
    if not username or not is_verified(username) or not is_user_in_all_groups(bot, m.from_user.id):
        bot.send_message(m.chat.id, "⚠️ Bạn cần tham gia đủ nhóm trước khi dùng bot.", reply_markup=join_keyboard())
        return

    txt = m.text.strip()

    if txt == "📧 GetMail (No Pass)" or txt == "🔐 GetMail (With Pass)":
        email, pwd, token, exp = create_mailtm_account()
        if not email:
            bot.reply_to(m, "❌ Không thể tạo mail, thử lại sau.")
            return
        
        # LƯU MAIL VÀO DB
        save_created_mail(m.from_user.id, email, pwd, token, exp)
        
        msg = f"📨 Mail: `{email}`"
        if txt == "🔐 GetMail (With Pass)":
            msg += f"\n🔑 Mật khẩu: `{pwd}`"
        msg += "\nDùng 📩 Check Inbox Mail để xem thư đến."
        bot.reply_to(m, msg, parse_mode="Markdown")

        send_donate_notice(m.chat.id)

    elif txt == "📱 GetPhone":
        phone = "+84" + str(random.randint(900000000, 999999999))
        
        # LƯU PHONE VÀO DB
        save_created_phone(m.from_user.id, phone, SMS_PROVIDER)
        
        bot.reply_to(m, f"📞 Số đã cấp: `{phone}`\nDùng '📲 Check SMS Phone' để xem tin nhắn.", parse_mode="Markdown")

        send_donate_notice(m.chat.id)

    elif txt == "💖 Donate cho Admin":
        send_donate_notice(m.chat.id)

    else:
        bot.reply_to(m, "Vui lòng chọn chức năng trong menu.")

# ===== DONATE VÀ KEEP ALIVE (GIỮ NGUYÊN) ===== #
def send_donate_notice(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📷 Xem mã QR Donate", callback_data="donate_qr"))
    bot.send_message(
        chat_id,
        "💡 Đây là bot phi lợi nhuận, admin tạo để mọi người dùng tiện.\n"
        "Nếu bạn thấy hữu ích, hãy donate ủng hộ để duy trì và phát triển bot nhé ❤️",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "donate_qr")
def callback_donate_qr(call):
    # File ID cố định
    QR_FILE_ID = "AgACAgUAAxkBAAIBJ2j_eZfuzAa1NoLeMbeibddEO1fDAAKqC2sbyzEAAVRTFL4NLU8wNAEAAwIAA3kAAzYE" 
    
    bot.send_photo(
        call.message.chat.id,
        QR_FILE_ID, 
        caption="💖 **Ủng hộ Admin:**\nNgân hàng: **Agribank**\nSTK: `3211205464270`\nChủ TK: **VU DINH THAI**",
        parse_mode="Markdown"
    )

# ===== KEEP ALIVE FUNCTION ===== #
def keep_alive():
    t = threading.Thread(target=run_flask_app)
    t.start()

def run_flask_app():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return "Bot is running on Telegram! Uptime check successful."

    # Chạy ứng dụng Flask trên cổng 8080 (hoặc cổng mặc định của Replit)
    app.run(host='0.0.0.0', port=8080)

# ===== MAIN ===== #
if __name__ == "__main__":
    init_db()
    
    # BẮT ĐẦU: Chạy máy chủ keep-alive
    keep_alive() 
    
    print("✅ Bot đang chạy...")
    bot.infinity_polling()
