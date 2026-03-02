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

# ===================== SAVOLLAR =====================

questions = {
    "📐 Matematika": [
        {"savol": "2 + 3 = ?", "variantlar": ["4", "5", "6", "7"], "javob": 1},
        {"savol": "10 - 4 = ?", "variantlar": ["5", "6", "7", "8"], "javob": 1},
        {"savol": "3 × 3 = ?", "variantlar": ["6", "7", "8", "9"], "javob": 3},
        {"savol": "12 ÷ 3 = ?", "variantlar": ["2", "3", "4", "5"], "javob": 2},
        {"savol": "5² = ?", "variantlar": ["10", "15", "20", "25"], "javob": 3},
    ],
    "📖 Ona tili": [
        {"savol": "'Kitob' so‘zi qaysi turkum?",
         "variantlar": ["Fe’l", "Ot", "Sifat", "Ravish"],
         "javob": 1},
        {"savol": "'Chiroyli' so‘zi qaysi turkum?",
         "variantlar": ["Fe’l", "Ot", "Sifat", "Olmosh"],
         "javob": 2},
    ],
    "🏛 O‘zbekiston tarixi": [
        {"savol": "Amir Temur qaysi asrda yashagan?",
         "variantlar": ["XIII asr", "XIV asr", "XVI asr", "XVIII asr"],
         "javob": 1},
        {"savol": "Mustaqillik yili?",
         "variantlar": ["1989", "1990", "1991", "1992"],
         "javob": 2},
    ],
}

TOTAL_QUESTIONS = 5

# ===================== START =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [
        ["📐 Matematika"],
        ["📖 Ona tili"],
        ["🏛 O‘zbekiston tarixi"],
    ]

    await update.message.reply_text(
        "📚 Majburiy Fan Test Bot\n\nFan tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )

# ===================== FAN TANLASH =====================

async def choose_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subject = update.message.text

    if subject not in questions:
        return

    context.user_data.clear()
    context.user_data["subject"] = subject
    context.user_data["score"] = 0
    context.user_data["current"] = 0

    selected = random.sample(
        questions[subject],
        min(TOTAL_QUESTIONS, len(questions[subject]))
    )

    context.user_data["question_list"] = selected

    await update.message.reply_text(
        f"📘 {subject} testi boshlandi!\n",
        reply_markup=ReplyKeyboardRemove()
    )

    await send_question(update, context)

# ===================== SAVOL =====================

async def send_question(update, context):
    index = context.user_data["current"]
    question_list = context.user_data["question_list"]

    if index >= len(question_list):
        await finish_test(update, context)
        return

    q = question_list[index]

    variants = q["variantlar"].copy()
    correct_text = variants[q["javob"]]

    random.shuffle(variants)

    correct_index = variants.index(correct_text)
    context.user_data["correct_index"] = correct_index
    context.user_data["shuffled_variants"] = variants

    text = f"{index + 1}. {q['savol']}"

    buttons = [
        [InlineKeyboardButton(v, callback_data=str(i))]
        for i, v in enumerate(variants)
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    if hasattr(update, "message") and update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

# ===================== JAVOB =====================

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected = int(query.data)
    correct = context.user_data["correct_index"]
    variants = context.user_data["shuffled_variants"]
    index = context.user_data["current"]
    q = context.user_data["question_list"][index]

    text = f"{index + 1}. {q['savol']}\n\n"

    for i, v in enumerate(variants):
        if i == correct:
            text += f"✅ {v}\n"
        elif i == selected:
            text += f"❌ {v}\n"
        else:
            text += f"{v}\n"

    if selected == correct:
        context.user_data["score"] += 1

    await query.edit_message_text(text)

    context.user_data["current"] += 1

    if context.user_data["current"] >= len(context.user_data["question_list"]):
        await finish_test(update, context)
    else:
        await send_question(update, context)

# ===================== TEST TUGASH =====================

async def finish_test(update, context):
    score = context.user_data["score"]
    total = len(context.user_data["question_list"])
    subject = context.user_data.get("subject", "")

    text = (
        f"🏁 Test tugadi!\n\n"
        f"📘 Fan: {subject}\n\n"
        f"✅ To‘g‘ri: {score}\n"
        f"❌ Noto‘g‘ri: {total - score}\n"
        f"📊 Ball: {score}/{total}"
    )

    keyboard = [
        [InlineKeyboardButton("🔁 Qayta topshirish", callback_data="retry")],
        [InlineKeyboardButton("🔙 Fanlar menyusi", callback_data="menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# ===================== MENU BUTTONS =====================

async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "retry":
        subject = context.user_data.get("subject")
        if subject:
            context.user_data.clear()
            context.user_data["subject"] = subject
            context.user_data["score"] = 0
            context.user_data["current"] = 0

            selected = random.sample(
                questions[subject],
                min(TOTAL_QUESTIONS, len(questions[subject]))
            )

            context.user_data["question_list"] = selected

            await query.message.reply_text(f"📘 {subject} testi qayta boshlandi!\n")
            await send_question(update, context)

    elif query.data == "menu":
        context.user_data.clear()
        await start(update, context)

# ===================== APP =====================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, choose_subject))
app.add_handler(CallbackQueryHandler(handle_answer))
app.add_handler(CallbackQueryHandler(handle_menu_buttons, pattern="^(retry|menu)$"))

print("Bot ishga tushdi 🚀")

# ===================== RENDER PORT =====================

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
