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
SCORES_FILE = "scores.json"
QUESTION_TIME = 20


# ================= SCORE =================

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


# ================= MENU =================

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
    await update.message.reply_text("📌 Asosiy menu:", reply_markup=main_menu())


# ================= TEST BOSHLASH =================

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


# ================= SEND QUESTION =================

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
    context.user_data["variants"] = variants
    context.user_data["answered"] = False
    context.user_data["time_left"] = QUESTION_TIME

    buttons = [
        [InlineKeyboardButton(v, callback_data=f"ans_{i}")]
        for i, v in enumerate(variants)
    ]

    text = (
        f"📘 {index+1}/{len(questions)}\n\n"
        f"{q['savol']}\n\n"
        f"⏳ {QUESTION_TIME} soniya"
    )

    if update.callback_query:
        msg = await update.callback_query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        msg = await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    context.user_data["message_id"] = msg.message_id
    context.user_data["chat_id"] = msg.chat_id

    context.user_data["timer_task"] = asyncio.create_task(
        countdown(context)
    )


# ================= COUNTDOWN =================

async def countdown(context: ContextTypes.DEFAULT_TYPE):
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
                    f"📘 {context.user_data['index']+1}/"
                    f"{len(context.user_data['questions'])}\n\n"
                    f"{context.user_data['questions'][context.user_data['index']]['savol']}\n\n"
                    f"⏳ {context.user_data['time_left']} soniya"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(v, callback_data=f"ans_{i}")]
                    for i, v in enumerate(context.user_data["variants"])
                ]),
            )
        except:
            return

    # vaqt tugadi
    context.user_data["answered"] = True
    await show_correct_answer(context)


# ================= JAVOB =================

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if context.user_data["answered"]:
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
    await send_question(update, context)


# ================= SHOW CORRECT =================

async def show_correct_answer(context):
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

    await asyncio.sleep(1)
    context.user_data["index"] += 1
    await send_question_from_timer(context)


async def send_question_from_timer(context):
    fake_update = Update(update_id=0)
    await send_question(fake_update, context)


# ================= FINISH =================

async def finish_test(update: Update, context):
    score = context.user_data["score"]
    total = len(context.user_data["questions"])

    user = update.effective_user
    scores = load_scores()
    uid = str(user.id)

    if uid not in scores:
        scores[uid] = {"name": user.first_name, "score": 0}

    scores[uid]["score"] += score
    save_scores(scores)

    await context.bot.send_message(
        chat_id=context.user_data["chat_id"],
        text=(
            f"🏁 Test tugadi!\n\n"
            f"✅ To‘g‘ri: {score}\n"
            f"❌ Noto‘g‘ri: {total - score}\n"
            f"📊 Ball: {score}/{total}"
        ),
        reply_markup=main_menu(),
    )


# ================= MENU HANDLER =================

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🟢 Test boshlash":
        questions = (
            random.sample(matematika, 10) +
            random.sample(ona_tili, 10) +
            random.sample(tarix, 10)
        )
        await start_test(update, context, questions)

    elif text == "📚 Fanlar":
        await update.message.reply_text("Fan tanlash hali soddalashtirilgan versiyada.")

    elif text == "🏆 Reyting":
        scores = load_scores()
        if not scores:
            await update.message.reply_text("Hali reyting yo‘q.")
            return

        sorted_users = sorted(
            scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )[:10]

        text = "🏆 Reyting:\n\n"
        for i, u in enumerate(sorted_users, 1):
            text += f"{i}. {u['name']} — {u['score']} ball\n"

        await update.message.reply_text(text)


# ================= RENDER KEEP ALIVE =================

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
