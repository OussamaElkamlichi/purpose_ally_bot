from flask import Flask, request, jsonify
from main import application
import asyncio
from telegram import Update
from db_agent import reset

flask_app = Flask(__name__)

@flask_app.route('/webhook/', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)

        async def handle():
            await application.initialize()
            await application.process_update(update)
            await application.shutdown()  # 🧼 important for flushing outgoing messages

        asyncio.run(handle())

        return "ok"
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return f"Error: {e}", 500

@flask_app.route('/reset', methods=['GET'])
def reset_route():
    try:
        reset()
        return jsonify({"status": "success", "message": "today_prod_hours reset to 0 for all users"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500