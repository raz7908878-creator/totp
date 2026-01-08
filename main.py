import os
import logging
import pyotp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **24/7 TOTP Bot is Online!**\n\n"
        "Send me a 2FA Secret Key (Base32), and I will generate the code.",
        parse_mode='Markdown'
    )

async def generate_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clean the input (remove spaces users might copy-paste)
    secret_key = update.message.text.strip().replace(" ", "")

    try:
        totp = pyotp.TOTP(secret_key)
        current_code = totp.now()

        # Reply with the code
        await update.message.reply_text(
            f"`{current_code}`",
            parse_mode='Markdown'
        )
        
    except Exception:
        await update.message.reply_text(
            "❌ **Invalid Key.**\nPlease check your secret key and try again.",
            parse_mode='Markdown'
        )

if __name__ == '__main__':
    # Get token from environment variable
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        print("Error: TELEGRAM_TOKEN not found in environment variables.")
        exit(1)

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_code))

    print("Bot is running...")
    application.run_polling()