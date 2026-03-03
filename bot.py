import os
import json
import random
import asyncio
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
QUESTION_TIME = 20
SCORES_FILE = "scores.json"


# ================= LOAD QUESTIONS =================

def load_questions(filename):
    with open(f"questions/{filename}", "r", encoding="utf-8") as f:
        return json.load(f)

matematika = load_questions("matematika.json")
ona_tili = load_questions("ona_tili.json")
tarix = load_questions("tarix.json")


# ================= SCORE SYSTEM =================

def load_scores():
    if not os.path.exists(SCORES_FILE):
        return {}
    with open(SCORES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_scores(scores):
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=4)


# ================= MAIN MENU =================

def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["🟢 Test boshlash"],
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


# ================= TEST START =================

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    questions = (
        random.sample(matematika, 10) +
        random.sample(ona_tili, 10) +
        random.sample(tarix, 10)
    )

    context.user_data["questions"] = questions
    context.user_data["index"] = 0
    context.user_data["score"] = 0

    await update.message.reply_text(
        "📝 Test boshlandi!",
        reply_markup=ReplyKeyboardRemove(),
    )

    await send_question(context, update.effective_chat.id)


# ================= SEND QUESTION =================

async def send_question(context, chat_id):
    index = context.user_data["index"]
    questions = context.user_data["questions"]

    if index >= len(questions):
        await finish_test(context, chat_id)
        return

    q = questions[index]
    variants = q["variantlar"].copy()
    correct_text = variants[q["javob"]]
    random.shuffle(variants)

    context.user_data["correct"] = variants.index(correct_text)
    context.user_data["variants"] = variants
    context.user_data["time_left"] = QUESTION_TIME
    context.user_data["answered"] = False

    buttons = [
        [InlineKeyboardButton(v, callback_data=f"ans_{i}")]
        for i, v in enumerate(variants)
    ]

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"📘 {index+1}/30\n\n"
            f"{q['savol']}\n\n"
            f"⏳ {QUESTION_TIME}"
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    context.user_data["chat_id"] = chat_id
    context.user_data["message_id"] = msg.message_id

    context.user_data["timer_task"] = asyncio.create_task(
        countdown(context)
    )


# ================= COUNTDOWN =================

async def countdown(context):
    while context.user_data["time_left"] > 0:
        await asyncio.sleep(1)

        if context.user_data["answered"]:
            return

        context.user_data["time_left"] -= 1

        try:
            await context.bot.edit_message_text(
                chat_id=context.user_data["chat_id"],
                message_id=context.user_data["message_id"],
                text=(
                    f"📘 {context.user_data['index']+1}/30\n\n"
                    f"{context.user_data['questions'][context.user_data['index']]['savol']}\n\n"
                    f"⏳ {context.user_data['time_left']}"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(v, callback_data=f"ans_{i}")]
                    for i, v in enumerate(context.user_data["variants"])
                ]),
            )
        except:
            return

    # ⛔ vaqt tugadi
    context.user_data["answered"] = True

    await show_correct(context)

    await asyncio.sleep(1)

    context.user_data["index"] += 1
    await send_question(context, context.user_data["chat_id"])


# ================= HANDLE ANSWER =================

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if context.user_data.get("answered"):
        return

    context.user_data["answered"] = True

    if "timer_task" in context.user_data:
        context.user_data["timer_task"].cancel()

    selected = int(query.data.split("_")[1])
    correct = context.user_data["correct"]
    variants = context.user_data["variants"]

    buttons = []

    for i, v in enumerate(variants):
        if i == correct:
            buttons.append([InlineKeyboardButton(f"✅ {v}", callback_data="done")])
        elif i == selected:
            buttons.append([InlineKeyboardButton(f"❌ {v}", callback_data="done")])
        else:
            buttons.append([InlineKeyboardButton(v, callback_data="done")])

    if selected == correct:
        context.user_data["score"] += 1

    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    await asyncio.sleep(1)

    context.user_data["index"] += 1
    await send_question(context, query.message.chat.id)


# ================= SHOW CORRECT =================

async def show_correct(context):
    correct = context.user_data["correct"]
    variants = context.user_data["variants"]

    buttons = []

    for i, v in enumerate(variants):
        if i == correct:
            buttons.append([InlineKeyboardButton(f"✅ {v}", callback_data="done")])
        else:
            buttons.append([InlineKeyboardButton(v, callback_data="done")])

    await context.bot.edit_message_reply_markup(
        chat_id=context.user_data["chat_id"],
        message_id=context.user_data["message_id"],
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ================= FINISH =================

async def finish_test(context, chat_id):
    score = context.user_data["score"]
    total = 30

    scores = load_scores()
    uid = str(chat_id)

    if uid not in scores:
        scores[uid] = {"score": 0}

    scores[uid]["score"] += score
    save_scores(scores)

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🏁 Test tugadi!\n\n"
            f"✅ To‘g‘ri: {score}\n"
            f"❌ Noto‘g‘ri: {total - score}\n"
            f"📊 Ball: {score}/{total}"
        ),
        reply_markup=main_menu(),
    )


# ================= RATING =================

async def show_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scores = load_scores()

    if not scores:
        await update.message.reply_text("Hali reyting yo‘q.")
        return

    sorted_users = sorted(
        scores.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )[:10]

    text = "🏆 Reyting:\n\n"

    for i, (uid, data) in enumerate(sorted_users, 1):
        text += f"{i}. ID {uid} — {data['score']} ball\n"

    await update.message.reply_text(text)


# ================= MENU HANDLER =================

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🟢 Test boshlash":
        await start_test(update, context)

    elif text == "🏆 Reyting":
        await show_rating(update, context)


# ================= KEEP ALIVE =================

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
