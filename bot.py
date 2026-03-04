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
ADMIN_ID = 866410473
QUESTION_TIME = 20
SCORES_FILE = "scores.json"


# ================= LOAD QUESTIONS =================

def load_questions(filename):
    with open(f"questions/{filename}", "r", encoding="utf-8") as f:
        return json.load(f)

matematika = load_questions("matematika.json")
ona_tili = load_questions("ona_tili.json")
tarix = load_questions("tarix.json")


# ================= SCORE =================

def load_scores():
    if not os.path.exists(SCORES_FILE):
        return {}
    with open(SCORES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_scores(scores):
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=4)


# ================= MENUS =================

def main_menu(user_id):

    buttons = [
        ["🟢 Test boshlash"],
        ["📚 Fanlar"],
        ["🏆 Reyting"],
        ["👤 Profil"],
    ]

    if user_id == ADMIN_ID:
        buttons.append(["👑 Admin"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def subjects_menu():
    return ReplyKeyboardMarkup(
        [
            ["📐 Matematika"],
            ["📖 Ona tili"],
            ["🏛 O'zbekiston tarixi"],
            ["🔙 Orqaga"],
        ],
        resize_keyboard=True,
    )


def admin_menu():
    return ReplyKeyboardMarkup(
        [
            ["📊 Statistika"],
            ["📢 Broadcast"],
            ["🔙 Orqaga"],
        ],
        resize_keyboard=True,
    )


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    await update.message.reply_text(
        "📌 Asosiy menu:",
        reply_markup=main_menu(update.effective_user.id),
    )


# ================= PROFILE =================

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    scores = load_scores()

    if str(user.id) not in scores:
        await update.message.reply_text("Siz hali test ishlamagansiz.")
        return

    user_data = scores[str(user.id)]

    text = (
        f"👤 Profil\n\n"
        f"Ism: {user_data['name']}\n"
        f"🏆 Jami ball: {user_data['score']}"
    )

    await update.message.reply_text(text)


# ================= START TEST =================

async def start_test(update, context, question_list):

    context.user_data.clear()
    context.user_data["questions"] = question_list
    context.user_data["index"] = 0
    context.user_data["score"] = 0
    context.user_data["answered"] = False

    await update.message.reply_text(
        "📝 Test boshlandi!",
        reply_markup=ReplyKeyboardRemove(),
    )

    await send_question(update, context)


# ================= SEND QUESTION =================

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):

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
    context.user_data["time_left"] = QUESTION_TIME
    context.user_data["answered"] = False

    buttons = [
        [InlineKeyboardButton(v, callback_data=f"ans_{i}")]
        for i, v in enumerate(variants)
    ]

    text = (
        f"📘 {index+1}/{len(questions)}\n\n"
        f"{q['savol']}\n\n"
        f"⏳ {QUESTION_TIME}"
    )

    if "message_id" in context.user_data:

        await context.bot.edit_message_text(
            chat_id=context.user_data["chat_id"],
            message_id=context.user_data["message_id"],
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    else:

        msg = await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

        context.user_data["message_id"] = msg.message_id
        context.user_data["chat_id"] = msg.chat_id

    context.user_data["timer_task"] = asyncio.create_task(countdown(context))


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
                    f"📘 {context.user_data['index']+1}/"
                    f"{len(context.user_data['questions'])}\n\n"
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

    context.user_data["answered"] = True

    await asyncio.sleep(1)

    context.user_data["index"] += 1

    await send_question_dummy(context)


async def send_question_dummy(context):

    fake_update = type("obj", (), {"message": None})

    await send_question(fake_update, context)


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

    await send_question(update, context)


# ================= FINISH =================

async def finish_test(update, context):

    score = context.user_data["score"]
    total = len(context.user_data["questions"])
    user = update.effective_user

    scores = load_scores()

    if str(user.id) not in scores:
        scores[str(user.id)] = {"name": user.first_name, "score": 0}

    scores[str(user.id)]["score"] += score

    save_scores(scores)

    await context.bot.edit_message_text(
        chat_id=context.user_data["chat_id"],
        message_id=context.user_data["message_id"],
        text=(
            f"🏁 Test tugadi!\n\n"
            f"✅ To‘g‘ri: {score}\n"
            f"❌ Noto‘g‘ri: {total - score}\n"
            f"📊 Ball: {score}/{total}"
        ),
    )

    await context.bot.send_message(
        chat_id=context.user_data["chat_id"],
        text="📌 Asosiy menu:",
        reply_markup=main_menu(user.id),
    )


# ================= MENU HANDLER =================

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    user_id = update.effective_user.id

    if text == "🟢 Test boshlash":

        questions = (
            random.sample(matematika, 10)
            + random.sample(ona_tili, 10)
            + random.sample(tarix, 10)
        )

        await start_test(update, context, questions)


    elif text == "📚 Fanlar":
        await update.message.reply_text("📚 Fan tanlang:", reply_markup=subjects_menu())


    elif text == "📐 Matematika":
        await start_test(update, context, matematika)


    elif text == "📖 Ona tili":
        await start_test(update, context, ona_tili)


    elif text == "🏛 O'zbekiston tarixi":
        await start_test(update, context, tarix)


    elif text == "🏆 Reyting":

        scores = load_scores()

        if not scores:
            await update.message.reply_text("Hali reyting yo‘q.")
            return

        sorted_users = sorted(scores.values(), key=lambda x: x["score"], reverse=True)

        text = "🏆 Reyting:\n\n"

        for i, user in enumerate(sorted_users[:10], 1):
            text += f"{i}. {user['name']} — {user['score']} ball\n"

        await update.message.reply_text(text)


    elif text == "👤 Profil":
        await show_profile(update, context)


    elif text == "👑 Admin" and user_id == ADMIN_ID:
        await update.message.reply_text("👑 Admin panel:", reply_markup=admin_menu())


    elif text == "📊 Statistika" and user_id == ADMIN_ID:

        scores = load_scores()

        user_count = len(scores)

        total_score = sum(user["score"] for user in scores.values())

        await update.message.reply_text(
            f"📊 Bot statistikasi\n\n"
            f"👥 Foydalanuvchilar: {user_count}\n"
            f"🏆 Jami ishlangan ball: {total_score}"
        )


    elif text == "📢 Broadcast" and user_id == ADMIN_ID:

        context.user_data["broadcast"] = True

        await update.message.reply_text("Xabarni yuboring:")


    elif context.user_data.get("broadcast") and user_id == ADMIN_ID:

        scores = load_scores()

        for uid in scores.keys():

            try:
                await context.bot.send_message(chat_id=int(uid), text=text)

            except:
                pass

        context.user_data["broadcast"] = False

        await update.message.reply_text("Xabar yuborildi.")


    elif text == "🔙 Orqaga":
        await start(update, context)


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
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

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
print("Bot ishga tushdi 🚀")

app.run_polling(close_loop=False)

