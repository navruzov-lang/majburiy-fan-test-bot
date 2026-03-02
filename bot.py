import os
import random
import sqlite3
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

# ================= DATABASE =================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    username TEXT,
    subject TEXT,
    best_score INTEGER,
    total_tests INTEGER
)
""")
conn.commit()

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
        {"savol": "10 - 4 = ?", "variantlar": ["5", "6", "7", "8"], "javob": 1},
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

    text = f"{index+1}. {q['savol']}"

    # 🔥 MUHIM QISM
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)

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

# ================= TUGASH =================

async def finish_test(update, context):
    query = update.callback_query
    user = query.from_user

    score = context.user_data["score"]
    subject = context.user_data["subject"]

    cursor.execute(
        "INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?)",
        (user.id, user.username, subject, score, 1),
    )

    cursor.execute(
        "UPDATE users SET 
            best_score = CASE WHEN best_score < ? THEN ? ELSE best_score END,
            total_tests = total_tests + 1
         WHERE user_id=? AND subject=?",
        (score, score, user.id, subject),
    )

    conn.commit()

    text = f"🏁 Test tugadi!\n\nBall: {score}/{len(context.user_data['question_list'])}"

    buttons = [
        [InlineKeyboardButton("🔁 Qayta topshirish", callback_data="retry")],
        [InlineKeyboardButton("🔙 Fanlar menyusi", callback_data="menu")]
    ]

    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

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

# ================= REYTING =================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subject = "📐 Matematika"

    cursor.execute(
        "SELECT username, best_score FROM users WHERE subject=? ORDER BY best_score DESC LIMIT 10",
        (subject,),
    )

    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("Hali reyting yo‘q.")
        return

    text = "🏆 Top 10 Reyting\n\n"
    for i, row in enumerate(rows, start=1):
        text += f"{i}. @{row[0]} — {row[1]} ball\n"

    await update.message.reply_text(text)

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
app.add_handler(CommandHandler("reyting", leaderboard))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, choose_subject))
app.add_handler(CallbackQueryHandler(handle_menu, pattern="^(retry|menu)$"))
app.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer_"))

print("Bot ishga tushdi 🚀")
app.run_polling()
