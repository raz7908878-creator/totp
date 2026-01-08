import os
import time
import asyncio
import logging
import pyotp
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import BadRequest

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **24/7 TOTP Authenticator**\n\n"
        "Send me your **Secret Key** (Base32) to generate a code.\n"
        "I will show a live timer for the code validity."
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

def get_progress_bar(seconds_left, total_seconds=30):
    """Creates a visual progress bar string"""
    percent = seconds_left / total_seconds
    filled_length = int(10 * percent)
    bar = '🟩' * filled_length + '⬜' * (10 - filled_length)
    return bar

async def generate_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secret_key = update.message.text.strip().replace(" ", "")

    try:
        totp = pyotp.TOTP(secret_key)
        # Get the code for the CURRENT time slot
        code = totp.now()
        
        # Calculate exactly how many seconds are left in this 30s window
        # TOTP works in 30s windows based on Unix time
        time_remaining = 30 - (time.time() % 30)
        
        # Send the initial message
        formatted_code = f"{code[:3]} {code[3:]}" # Split 123456 into 123 456 for readability
        msg = await update.message.reply_text(
            f"🔐 **Your Code:**\n`{code}`\n\n"
            f"⏳ Expires in: {int(time_remaining)}s\n"
            f"{get_progress_bar(time_remaining)}",
            parse_mode='Markdown'
        )

        # LIVE TIMER LOOP
        # We update every 3 seconds to avoid Telegram 'FloodWait' limits
        while time_remaining > 0:
            await asyncio.sleep(3) # Wait 3 seconds
            
            # Recalculate remaining time
            time_remaining = 30 - (time.time() % 30)
            
            # If the window has flipped (time_remaining jumped back to ~30), stop.
            if time_remaining > 28: 
                break 

            # Update the message UI
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    text=f"🔐 **Your Code:**\n`{code}`\n\n"
                         f"⏳ Expires in: {int(time_remaining)}s\n"
                         f"{get_progress_bar(time_remaining)}",
                    parse_mode='Markdown'
                )
            except BadRequest:
                # This happens if the message content is exactly the same 
                # or user deleted the chat. We ignore it.
                pass

        # When loop finishes (Code expired)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=f"❌ **Code Expired**\n`{code}`\n\n"
                 f"Send key again for a new code.",
            parse_mode='Markdown'
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ **Invalid Key.**\nPlease ensure it is a valid Base32 secret key.",
            parse_mode='Markdown'
        )

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    if not TOKEN:
        print("Error: TELEGRAM_TOKEN not found.")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler('start', start))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_code))
        
        print("Bot is running...")
        app.run_polling()