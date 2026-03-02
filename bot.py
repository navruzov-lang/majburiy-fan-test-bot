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
TOTAL_QUESTIONS = 10

# ================= SAVOLLAR =================

questions = {

    "📐 Matematika": [
        {"savol": "√49 = ?", "variantlar": ["6", "7", "8", "9"], "javob": 1},
        {"savol": "3² + 4² = ?", "variantlar": ["25", "49", "7", "5"], "javob": 0},
        {"savol": "2x = 10. x = ?", "variantlar": ["2", "3", "5", "10"], "javob": 2},
        {"savol": "15% of 200 = ?", "variantlar": ["20", "25", "30", "35"], "javob": 2},
        {"savol": "7 × 8 = ?", "variantlar": ["54", "56", "58", "60"], "javob": 1},
        {"savol": "144 ÷ 12 = ?", "variantlar": ["10", "11", "12", "13"], "javob": 2},
        {"savol": "5³ = ?", "variantlar": ["15", "25", "75", "125"], "javob": 3},
        {"savol": "1/2 + 1/4 = ?", "variantlar": ["1/6", "3/4", "3/2", "1/8"], "javob": 1},
        {"savol": "x + 7 = 15. x = ?", "variantlar": ["6", "7", "8", "9"], "javob": 2},
        {"savol": "Perimetri tomoni 5 sm kvadrat P = ?", "variantlar": ["10", "15", "20", "25"], "javob": 2},
        {"savol": "10 - 4 = ?", "variantlar": ["5", "6", "7", "8"], "javob": 1},
        {"savol": "3 × 3 = ?", "variantlar": ["6", "7", "8", "9"], "javob": 3},
    ],

    "📖 Ona tili": [
        {"savol": "'Kitob' so‘zi qaysi turkum?",
         "variantlar": ["Fe’l", "Ot", "Sifat", "Ravish"], "javob": 1},
        {"savol": "'Chiroyli' so‘zi qaysi turkum?",
         "variantlar": ["Olmosh", "Sifat", "Ot", "Fe’l"], "javob": 1},
        {"savol": "Ega qaysi gap bo‘lagi?",
         "variantlar": ["Asosiy", "Ikkinchi darajali", "Hol", "Aniqlovchi"], "javob": 0},
        {"savol": "'Yaxshi o‘qidi' qaysi zamon?",
         "variantlar": ["Hozirgi", "O‘tgan", "Kelasi", "Shart"], "javob": 1},
        {"savol": "Fe’l nimani bildiradi?",
         "variantlar": ["Harakat", "Narsa", "Belgini", "Son"], "javob": 0},
        {"savol": "Ot nimani bildiradi?",
         "variantlar": ["Harakat", "Belgini", "Narsa", "Hol"], "javob": 2},
    ],

    "🏛 Oʻzbekiston tarixi": [
        {"savol": "Amir Temur qaysi asrda yashagan?",
         "variantlar": ["XIII", "XIV", "XVI", "XVIII"], "javob": 1},
        {"savol": "Amir Temur tug‘ilgan yil?",
         "variantlar": ["1336", "1320", "1340", "1350"], "javob": 0},
        {"savol": "O‘zbekiston mustaqilligi qachon e’lon qilingan?",
         "variantlar": ["1990", "1991", "1992", "1993"], "javob": 1},
        {"savol": "Temuriylar poytaxti?",
         "variantlar": ["Buxoro", "Samarqand", "Xiva", "Qo‘qon"], "javob": 1},
        {"savol": "Jadidchilik qachon boshlangan?",
         "variantlar": ["XIX asr oxiri", "XVIII", "XVII", "XXI"], "javob": 0},
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

    buttons = [[InlineKeyboardButton(v, callback_data=f"answer_{i}")]
               for i, v in enumerate(variants)]

    markup = InlineKeyboardMarkup(buttons)

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
    variants = context.user_data["variants"]
    index = context.user_data["current"]
    q = context.user_data["question_list"][index]

    text = f"{index+1}. {q['savol']}\n\n"

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
        await send_question(query, context)

# ================= TUGASH =================

async def finish_test(update, context):
    score = context.user_data["score"]
    total = len(context.user_data["question_list"])
    subject = context.user_data["subject"]

    text = (
        f"🏁 Test tugadi!\n\n"
        f"Fan: {subject}\n"
        f"To‘g‘ri: {score}\n"
        f"Noto‘g‘ri: {total-score}\n"
        f"Ball: {score}/{total}"
    )

    buttons = [
        [InlineKeyboardButton("🔁 Qayta topshirish", callback_data="retry")],
        [InlineKeyboardButton("🔙 Fanlar menyusi", callback_data="menu")]
    ]

    markup = InlineKeyboardMarkup(buttons)

    await update.callback_query.message.reply_text(text, reply_markup=markup)

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
        await send_question(query, context)

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
