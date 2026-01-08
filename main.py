import os
import time
import logging
import pyotp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import BadRequest

# --- CONFIGURATION ---
REQUIRED_CHANNEL = "@trustedearningcommunity"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Checks if the user is a member of the required channel.
    Returns True if member, False otherwise.
    """
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
        if update.callback_query:
            await update.callback_query.message.reply_text(error_msg)
        else:
            await context.bot.send_message(chat_id=chat_id, text=error_msg)
        return False

    # Not a member? Send Join Button
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel to Use Bot", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}")],
        [InlineKeyboardButton("✅ I Have Joined", callback_data="check_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg_text = (
        f"⛔ **Access Denied**\n\n"
        f"You must join our official channel to use this bot.\n"
        f"Join here: {REQUIRED_CHANNEL}"
    )

    if update.callback_query:
        await update.callback_query.answer("❌ You are not in the channel yet!", show_alert=True)
    else:
        await context.bot.send_message(chat_id=chat_id, text=msg_text, reply_markup=reply_markup, parse_mode='Markdown')
    return False

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_membership(update, context):
        return

    await update.message.reply_text(
        "👋 **Welcome to Trusted Earning Community Bot!**\n\n"
        "Send me a **2FA Secret Key** (Base32 format), and I will generate your code immediately.",
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "check_subscription":
        if await check_membership(update, context):
            await query.message.delete()
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="✅ **Verified!** Send me your Secret Key now.",
                parse_mode='Markdown'
            )

async def generate_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check subscription first
    if not await check_membership(update, context):
        return

    secret_key = update.message.text.strip().replace(" ", "")

    try:
        totp = pyotp.TOTP(secret_key)
        code = totp.now()
        
        # Calculate seconds remaining just for info (Static, no live update)
        time_remaining = int(30 - (time.time() % 30))
        
        # Simple, fast reply
        await update.message.reply_text(
            f"🔐 **Your Code:** `{code}`\n"
            f"⏳ Valid for approx: {time_remaining}s",
            parse_mode='Markdown'
        )

    except Exception:
        await update.message.reply_text(
            "❌ **Invalid Key.**\nPlease ensure it is a valid Base32 secret key.",
            parse_mode='Markdown'
        )

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    if not TOKEN:
        print("CRITICAL ERROR: Token not found!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), generate_code))
        
        print("Bot is polling...")
        app.run_polling()
        