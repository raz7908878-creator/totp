import os
import time
import logging
import pyotp
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # No membership check needed anymore
    await update.message.reply_text(
        "👋 **Welcome!**\nSend me a **2FA Secret Key**, and I will generate your code.",
        parse_mode='Markdown'
    )

async def generate_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # No membership check needed anymore
    secret_key = update.message.text.strip().replace(" ", "")
    
    try:
        # Generate the TOTP code
        totp = pyotp.TOTP(secret_key)
        code = totp.now()
        
        # Calculate remaining validity time
        time_remaining = int(30 - (time.time() % 30))
        
        await update.message.reply_text(
            f"🔐 **Code:** `{code}`\n⏳ Valid for: {time_remaining}s", 
            parse_mode='Markdown'
        )
    except Exception:
        # Handle invalid keys (e.g. malformed base32 strings)
        await update.message.reply_text("❌ **Invalid Key.** Please check your secret.", parse_mode='Markdown')

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        print("CRITICAL ERROR: Token not found!")
    else:
        # 1. Start the fake web server first
        start_keep_alive()
        
        # 2. Start the bot
        app_bot = ApplicationBuilder().token(TOKEN).build()
        
        # Handlers
        app_bot.add_handler(CommandHandler('start', start))
        # Filters text that is NOT a command
        app_bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_code))
        
        print("Bot is polling...")
        app_bot.run_polling()
