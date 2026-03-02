import os
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
TOTAL_QUESTIONS = 5   # hozir 5 qilib turamiz (stabil uchun)

# ================= SAVOLLAR =================

questions = {
    "📐 Matematika": [
        {"savol": "2 + 3 = ?", "variantlar": ["4", "5", "6", "7"], "javob": 1},
        {"savol": "10 - 4 = ?", "variantlar": ["5", "6", "7", "8"], "javob": 1},
        {"savol": "3 × 3 = ?", "variantlar": ["6", "7", "8", "9"], "javob": 3},
        {"savol": "5² = ?", "variantlar": ["10", "15", "20", "25"], "javob": 3},
        {"savol": "12 ÷ 3 = ?", "variantlar": ["2", "3", "4", "5"], "javob": 2},
    ],
    "📖 Ona tili": [
        {"savol": "'Kitob' so‘zi qaysi turkum?",
         "variantlar": ["Fe’l", "Ot", "Sifat", "Ravish"], "javob": 1},
        {"savol": "'Chiroyli' so‘zi qaysi turkum?",
         "variantlar": ["Olmosh", "Sifat", "Ot", "Fe’l"], "javob": 1},
    ],
    "🏛 Oʻzbekiston tarixi": [
        {"savol": "Amir Temur qaysi asrda yashagan?",
         "variantlar": ["XIII", "XIV", "XVI", "XVIII"], "javob": 1},
        {"savol": "O‘zbekiston mustaqilligi qachon e’lon qilingan?",
         "variantlar": ["1990", "1991", "1992", "1993"], "javob": 1},
    ],
}

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [
        ["📐 Matematika"],
        ["📖 Ona tili"],
        ["🏛 Oʻzbekiston tarixi"],
    ]

    await update.message.reply_text(
        "📚 Fan tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )

# ================= FAN TANLASH =================

async def choose_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subject = update.message.text

    if subject not in questions:
        return

    context.user_data.clear()
    context.user_data["subject"] = subject
    context.user_data["score"] = 0
    context.user_data["current"] = 0
    context.user_data["question_list"] = random.sample(
        questions[subject],
        min(TOTAL_QUESTIONS, len(questions[subject]))
    )

    await update.message.reply_text(
        f"{subject} testi boshlandi!",
        reply_markup=ReplyKeyboardRemove()
    )

    await send_question(update, context)

# ================= SAVOL =================

async def send_question(update, context):
    index = context.user_data["current"]
    q = context.user_data["question_list"][index]

    variants = q["variantlar"].copy()
    correct_text = variants[q["javob"]]
    random.shuffle(variants)

    context.user_data["correct_index"] = variants.index(correct_text)
    context.user_data["variants"] = variants

    buttons = [
        [InlineKeyboardButton(v, callback_data=f"answer_{i}")]
        for i, v in enumerate(variants)
    ]

    markup = InlineKeyboardMarkup(buttons)

    # MUHIM: universal reply
    if hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.message.reply_text(
            f"{index+1}. {q['savol']}",
            reply_markup=markup
        )
    else:
        await update.message.reply_text(
            f"{index+1}. {q['savol']}",
            reply_markup=markup
        )

# ================= JAVOB =================

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected = int(query.data.split("_")[1])
    correct = context.user_data["correct_index"]

    if selected == correct:
        context.user_data["score"] += 1

    context.user_data["current"] += 1

    if context.user_data["current"] >= len(context.user_data["question_list"]):
        await finish_test(update, context)
    else:
        await send_question(update, context)

# ================= TEST TUGADI =================

async def finish_test(update, context):
    query = update.callback_query

    score = context.user_data["score"]
    total = len(context.user_data["question_list"])

    text = f"🏁 Test tugadi!\n\nBall: {score}/{total}"

    buttons = [
        [InlineKeyboardButton("🔁 Qayta topshirish", callback_data="retry")],
        [InlineKeyboardButton("🔙 Fanlar menyusi", callback_data="menu")]
    ]

    await query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= MENU =================

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "retry":
        subject = context.user_data["subject"]

        context.user_data.clear()
        context.user_data["subject"] = subject
        context.user_data["score"] = 0
        context.user_data["current"] = 0
        context.user_data["question_list"] = random.sample(
            questions[subject],
            min(TOTAL_QUESTIONS, len(questions[subject]))
        )

        await query.message.reply_text(f"{subject} testi qayta boshlandi!")
        await send_question(update, context)

    elif query.data == "menu":
        await start(query, context)

# ================= RENDER SERVER =================

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

# ================= APP =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, choose_subject))
app.add_handler(CallbackQueryHandler(handle_menu, pattern="^(retry|menu)$"))
app.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer_"))

print("Bot ishga tushdi 🚀")
app.run_polling()
