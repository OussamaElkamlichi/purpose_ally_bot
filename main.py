from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler

app = Flask(__name__)

TOKEN = "8147668562:AAGEAgFhF2ghuRXYp3q4-AtPLoHhsYfQ2Sc"
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0, use_context=True)

# ✅ Define /start handler
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome! This bot is running via webhook 💡")

# ✅ Register handler
dispatcher.add_handler(CommandHandler("start", start))

# ✅ Webhook route
@app.route(f"/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

# ✅ Simple check route
@app.route("/", methods=["GET"])
def index():
    return "Nigga you good?", 200
