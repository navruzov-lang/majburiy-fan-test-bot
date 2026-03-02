import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

questions = {
    "📐 Matematika": {
        "savol": "2 + 3 = ?",
        "variantlar": ["4", "5", "6", "7"],
        "javob": "B",
    },
    "📖 Ona tili": {
        "savol": "‘Kitob’ so‘zi qaysi turkumga kiradi?",
        "variantlar": ["Fe’l", "Ot", "Sifat", "Ravish"],
        "javob": "B",
    },
    "🏛 O'zbekiston tarixi": {
        "savol": "Amir Temur qaysi asrda yashagan?",
        "variantlar": ["XIII asr", "XIV asr", "XVI asr", "XVIII asr"],
        "javob": "B",
    },
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📐 Matematika"],
        ["📖 Ona tili"],
        ["🏛 O'zbekiston tarixi"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "📚 Majburiy Fan Test Bot\n\nFan tanlang:",
        reply_markup=reply_markup,
    )


async def handle_fan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fan = update.message.text

    if fan in questions:
        savol = questions[fan]

        text = savol["savol"] + "\n\n"
        harflar = ["A", "B", "C", "D"]

        for i, v in enumerate(savol["variantlar"]):
            text += f"{harflar[i]}) {v}\n"

        context.user_data["correct"] = savol["javob"]

        keyboard = [["A", "B"], ["C", "D"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(text, reply_markup=reply_markup)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = update.message.text
    correct = context.user_data.get("correct")

    if correct:
        if user_answer == correct:
            await update.message.reply_text("✅ To‘g‘ri!")
        else:
            await update.message.reply_text(f"❌ Noto‘g‘ri! To‘g‘ri javob: {correct}")

        context.user_data["correct"] = None


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fan))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

print("Test Bot ishga tushdi 🚀")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")


def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


threading.Thread(target=run_web).start()

app.run_polling()
