from flask import Flask, request, jsonify
from main import application
import asyncio
from sqlalchemy.orm import sessionmaker, update, delete, select
from models import DailySession, Goal, PollMappings, Subgoal, engine
from telegram import Update, Bot
from db_agent import reset

# Define your Telegram bot token here
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

flask_app = Flask(__name__)

Session = sessionmaker(bind=engine)
session = Session()

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
    
@flask_app.route('/send_polls', methods=['GET'])
async def fetch_and_prepare_goals(user_id):
    try:
        my_list = {}

        # 1. Récupérer les objectifs principaux non terminés
        goals = session.query(Goal).filter(
            Goal.user_id == user_id,
            Goal.status != 'done'
        ).all()

        for goal in goals:
            subgoals_data = []

            # 2. Récupérer les sous-objectifs non terminés
            subgoals = session.query(Subgoal).filter(
                Subgoal.goal_id == goal.id,
                Subgoal.status != 'done'
            ).all()

            for sub in subgoals:
                # Ajouter dans la liste à envoyer
                subgoals_data.append({
                    "subgoal_title": sub.subgoal_title,
                    "status": sub.status
                })

            my_list[goal.goal_title] = {
                "goal_id": goal.id,
                "subgoals": subgoals_data
            }

            daily_session = DailySession(
                    user_id=user_id,
                    goal_id=sub.id,  
                    status="started"
                )
            session.add(daily_session)

        # 4. Commit après la boucle
        session.commit()
        # 5. Envoyer le sondage via bot
        bot = Bot(token=TOKEN)
        await send_poll(bot, user_id, my_list)

    except Exception as e:
        session.rollback()
        print(f"❌ Error during fetch_and_prepare_goals: {e}")
    finally:
        session.close()
 
async def send_poll(bot, user_id, my_list):
    if not my_list:
        await bot.send_message(
            user_id,
            "<blockquote>🎉 بارك الله! لقد أنجزت جميع أهدافك!</blockquote>\n\n"
            "<b>هل تريد أن توقف التنبيهات اليومية؟</b>",
            parse_mode='HTML'
        )
        return

    try:
        for goal_title, goal_data in my_list.items():
            goal_id = goal_data["goal_id"]
            sub_goals = goal_data["subgoals"]
            options = [sub["subgoal_title"] for sub in sub_goals]

            # Ajouter deux options si une seule
            if len(options) < 2:
                options.extend(["لا يمكن إرسال تصويت", "بخيار واحد فقط، لذا نضيف هذين"])

            sent_poll = await bot.send_poll(
                chat_id=user_id,
                question=goal_title,
                options=options,
                is_anonymous=False,
                allows_multiple_answers=True,
            )

            # Sauvegarder dans la table polls
            poll_record = PollMappings(
                poll_id=sent_poll.poll.id,
                goal_id=goal_id,
                user_id=user_id
            )
            session.add(poll_record)

        await session.commit()

    except Exception as e:
        await session.rollback()
        print(f"❌ Failed to send poll for goal '{goal_title}': {e}")

