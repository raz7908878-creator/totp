import os
import time
import logging
import pyotp
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import BadRequest

# --- CONFIGURATION ---
REQUIRED_CHANNEL = "@trustedearningcommunity"

# --- FLASK KEEP-ALIVE SERVER ---
# This "Fake Website" tricks Render into keeping the bot running
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_http_server():
    # Render sets the PORT environment variable. We must listen on it.
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start_keep_alive():
    t = threading.Thread(target=run_http_server)
    t.daemon = True
    t.start()

# --- BOT LOGIC ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        user_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ['member', 'creator', 'administrator']:
            return True
    except BadRequest:
        error_msg = f"⚠️ System Error: Please make me an Admin in {REQUIRED_CHANNEL}."
        await context.bot.send_message(chat_id=chat_id, text=error_msg)
        return False

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")],
        [InlineKeyboardButton("✅ I Have Joined", callback_data="check_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg_text = (
        f"⛔ **Access Denied**\n\n"
        f"You must join our channel to use this bot.\n"
        f"Join here: {REQUIRED_CHANNEL}"
    )

    if update.callback_query:
        await update.callback_query.answer("❌ You are not in the channel yet!", show_alert=True)
    else:
        await context.bot.send_message(chat_id=chat_id, text=msg_text, reply_markup=reply_markup, parse_mode='Markdown')
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_membership(update, context):
        return
    await update.message.reply_text(
        "👋 **Welcome!**\nSend me a **2FA Secret Key**, and I will generate your code.",
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "check_subscription":
        if await check_membership(update, context):
            await query.message.delete()
            await context.bot.send_message(chat_id=query.message.chat_id, text="✅ **Verified!** Send your Key now.", parse_mode='Markdown')

async def generate_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_membership(update, context):
        return
    secret_key = update.message.text.strip().replace(" ", "")
    try:
        totp = pyotp.TOTP(secret_key)
        code = totp.now()
        time_remaining = int(30 - (time.time() % 30))
        await update.message.reply_text(f"🔐 **Code:** `{code}`\n⏳ Valid for: {time_remaining}s", parse_mode='Markdown')
    except Exception:
        await update.message.reply_text("❌ **Invalid Key.**", parse_mode='Markdown')

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        print("CRITICAL ERROR: Token not found!")
    else:
        # 1. Start the fake web server first
        start_keep_alive()
        
        # 2. Start the bot
        app_bot = ApplicationBuilder().token(TOKEN).build()
        app_bot.add_handler(CommandHandler('start', start))
        app_bot.add_handler(CallbackQueryHandler(button_callback))
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_code))
        
        print("Bot is polling...")
        app_bot.run_polling()
        