import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📐 Matematika"],
        ["📖 Ona tili"],
        ["🏛 O'zbekiston tarixi"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "📚 Majburiy Fan Test Bot\n\nFan tanlang:",
        reply_markup=reply_markup
    )

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

print("Test Bot ishga tushdi 🚀")

app.run_polling()
