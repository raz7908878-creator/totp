import os
import logging
import pyotp
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **24/7 TOTP Bot is Online!**\n\n"
        "Send me a 2FA Secret Key (Base32 format) and I will give you the code.",
        parse_mode='Markdown'
    )

async def generate_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip().replace(" ", "")
    
    try:
        totp = pyotp.TOTP(user_text)
        code = totp.now()
        
        # Send code in mono-space for easy copying
        await update.message.reply_text(f"`{code}`", parse_mode='Markdown')
        
    except Exception:
        await update.message.reply_text("❌ Invalid Key. Please check your secret.")

if __name__ == '__main__':
    # Cloud platforms store secrets in Environment Variables
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    if not TOKEN:
        print("CRITICAL ERROR: Token not found!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler('start', start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_code))
        
        print("Bot is polling...")
        app.run_polling()