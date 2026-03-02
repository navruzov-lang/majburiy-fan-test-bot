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

# ================== SAVOLLAR ==================

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


# ================== START ==================

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


# ================== FAN TANLASH ==================

async def choose_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fan = update.message.text

    if fan not in questions:
        return

    context.user_data.clear()
    context.user_data["subject"] = fan
    context.user_data["score"] = 0
    context.user_data["current"] = 0

    selected_questions = random.sample(
        questions[fan],
        min(TOTAL_QUESTIONS, len(questions[fan]))
    )

    context.user_data["question_list"] = selected_questions

    await update.message.reply_text(
        f"📘 {fan} testi boshlandi!\n",
        reply_markup=ReplyKeyboardRemove()
    )

    await send_question(update, context)


# ================== SAVOL YUBORISH ==================

async def send_question(update, context):
    index = context.user_data["current"]
    question_list = context.user_data["question_list"]

    if index >= len(question_list):
        await finish_test(update, context)
        return

    q = question_list[index]
    text = f"{index + 1}. {q['savol']}"

    buttons = []
    for i, variant in enumerate(q["variantlar"]):
        buttons.append([InlineKeyboardButton(variant, callback_data=str(i))])

    reply_markup = InlineKeyboardMarkup(buttons)

    # MUHIM QISM 👇
    if hasattr(update, "message") and update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)


# ================== JAVOB ==================

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected = int(query.data)
    index = context.user_data["current"]
    q = context.user_data["question_list"][index]

    correct = q["javob"]

    new_text = f"{index + 1}. {q['savol']}\n\n"

    for i, variant in enumerate(q["variantlar"]):
        if i == correct:
            new_text += f"✅ {variant}\n"
        elif i == selected:
            new_text += f"❌ {variant}\n"
        else:
            new_text += f"{variant}\n"

    if selected == correct:
        context.user_data["score"] += 1

    await query.edit_message_text(new_text)

    context.user_data["current"] += 1

    # Oxirgi savol bo‘lsa
    if context.user_data["current"] >= len(context.user_data["question_list"]):
        await finish_test(update, context)
    else:
        await send_question(update, context)


# ================== TEST TUGASH ==================

async def finish_test(update, context):
    score = context.user_data["score"]
    total = len(context.user_data["question_list"])

    result_text = (
        f"🏁 Test tugadi!\n\n"
        f"✅ To‘g‘ri: {score}\n"
        f"❌ Noto‘g‘ri: {total - score}\n"
        f"📊 Ball: {score}/{total}"
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(result_text)
    else:
        await update.message.reply_text(result_text)

    context.user_data.clear()


# ================== APP ==================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, choose_subject))
app.add_handler(CallbackQueryHandler(handle_answer))

print("Bot ishga tushdi 🚀")


# ================== RENDER PORT ==================

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
