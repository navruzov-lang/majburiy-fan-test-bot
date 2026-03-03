import os
import json
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
SCORES_FILE = "scores.json"

# ================= SCORE SYSTEM =================

def load_scores():
    if not os.path.exists(SCORES_FILE):
        return {}
    with open(SCORES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_scores(scores):
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=4)

# ================= LOAD QUESTIONS =================

def load_questions(filename):
    with open(f"questions/{filename}", "r", encoding="utf-8") as f:
        return json.load(f)

matematika = load_questions("matematika.json")
ona_tili = load_questions("ona_tili.json")
tarix = load_questions("tarix.json")

# ================= ASOSIY MENU =================

def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["🟢 Test boshlash"],
            ["📚 Fanlar"],
            ["🏆 Reyting"],
        ],
        resize_keyboard=True,
    )

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "📌 Asosiy menu:",
        reply_markup=main_menu(),
    )

# ================= REYTING =================

async def show_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scores = load_scores()

    if not scores:
        await update.message.reply_text("Hali reyting yo‘q.")
        return

    sorted_users = sorted(
        scores.values(),
        key=lambda x: x["score"],
        reverse=True
    )[:10]

    text = "🏆 TOP 10 Reyting:\n\n"
    for i, user in enumerate(sorted_users, start=1):
        text += f"{i}. {user['name']} — {user['score']} ball\n"

    await update.message.reply_text(text)

# ================= FANLAR MENU =================

async def show_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📐 Matematika"],
        ["📖 Ona tili"],
        ["🏛 Oʻzbekiston tarixi"],
        ["🔙 Orqaga"],
    ]
    await update.message.reply_text(
        "📚 Fan tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )

# ================= TEST BOSHLASH =================

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🟢 Test boshlash":
        questions = (
            random.sample(matematika, min(10, len(matematika))) +
            random.sample(ona_tili, min(10, len(ona_tili))) +
            random.sample(tarix, min(10, len(tarix)))
        )
        random.shuffle(questions)
        await start_test(update, context, questions)

    elif text == "📚 Fanlar":
        await show_subjects(update, context)

    elif text == "🏆 Reyting":
        await show_rating(update, context)

    elif text == "📐 Matematika":
        await start_test(update, context, matematika)

    elif text == "📖 Ona tili":
        await start_test(update, context, ona_tili)

    elif text == "🏛 Oʻzbekiston tarixi":
        await start_test(update, context, tarix)

    elif text == "🔙 Orqaga":
        await start(update, context)

# ================= TEST FUNKSIYASI =================

async def start_test(update, context, question_list):
    context.user_data.clear()
    context.user_data["questions"] = question_list
    context.user_data["index"] = 0
    context.user_data["score"] = 0

    await update.message.reply_text(
        "📝 Test boshlandi!",
        reply_markup=ReplyKeyboardRemove(),
    )

    await send_question(update, context)

# ================= SAVOL =================

async def send_question(update: Update, context):
    index = context.user_data["index"]
    questions = context.user_data["questions"]

    if index >= len(questions):
        await finish_test(update, context)
        return

    q = questions[index]
    variants = q["variantlar"].copy()
    correct_text = variants[q["javob"]]
    random.shuffle(variants)

    context.user_data["correct"] = variants.index(correct_text)

    buttons = [
        [InlineKeyboardButton(v, callback_data=f"ans_{i}")]
        for i, v in enumerate(variants)
    ]

    message = (
        update.callback_query.message
        if update.callback_query
        else update.message
    )

    await message.reply_text(
        f"{index+1}. {q['savol']}",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ================= JAVOB =================

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected = int(query.data.split("_")[1])
    correct = context.user_data.get("correct")

    if selected == correct:
        context.user_data["score"] += 1

    context.user_data["index"] += 1

    await send_question(update, context)

# ================= TEST TUGADI =================

async def finish_test(update: Update, context):
    score = context.user_data["score"]
    total = len(context.user_data["questions"])

    user = update.callback_query.from_user

    scores = load_scores()
    uid = str(user.id)

    if uid not in scores:
        scores[uid] = {"name": user.first_name, "score": 0}

    scores[uid]["score"] += score
    save_scores(scores)

    await update.callback_query.message.reply_text(
        f"🏁 Test tugadi!\n\n"
        f"✅ To‘g‘ri: {score}\n"
        f"❌ Noto‘g‘ri: {total - score}\n"
        f"📊 Ball: {score}/{total}",
        reply_markup=main_menu(),
    )

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
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
app.add_handler(CallbackQueryHandler(handle_answer, pattern="^ans_"))

print("Bot ishga tushdi 🚀")
app.run_polling(close_loop=False)
