from flask import Flask, request, jsonify
from main import application
import asyncio
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update, delete, select
from models import DailySession, Goal, PollMappings, Subgoal, engine, User
from telegram import Update, Bot
from telegram.constants import ParseMode
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
def fetch_and_prepare_goals():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = loop.create_task(_async_send_polls_for_all_users())
        else:
            loop.run_until_complete(_async_send_polls_for_all_users())
        return jsonify({"status": "success", "message": "✅ Polls sent to all users"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

async def _async_send_polls_for_all_users():
    session = Session()
    try:
        # Fetch all users (adjust model/field names accordingly)
        users = session.query(User).all()

        for user in users:
            user_id = user.telegram_id
            # Prepare goals data per user
            my_list = await _fetch_user_goals(session, user_id)
            username = getattr(user, "username", None)

            # Compose mention text: prefer username, else fallback to user_id mention
            mention = f"[User](tg://user?id={user_id})"

            await send_poll(bot, user_id, 18, my_list, session, mention)

    finally:
        session.close()


async def _fetch_user_goals(session, user_id):
    my_list = {}
    try:
        goals = session.query(Goal).filter(
            Goal.user_id == user_id,
            Goal.status != 'done'
        ).all()

        for goal in goals:
            subgoals_data = []

            subgoals = session.query(Subgoal).filter(
                Subgoal.goal_id == goal.goal_id,
                Subgoal.status != 'done'
            ).all()

            for sub in subgoals:
                subgoals_data.append({
                    "subgoal_title": sub.subgoal_title,
                    "status": sub.status
                })

                daily_session = DailySession(
                    user_id=user_id,
                    goal_id=sub.subgoal_id,
                    status="started"
                )
                session.add(daily_session)

            my_list[goal.goal_title] = {
                "goal_id": goal.goal_id,
                "subgoals": subgoals_data
            }

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"❌ Error fetching goals for user {user_id}: {e}")

    return my_list


async def send_poll(bot, user_id, thread_id, my_list, session, mention):
    if not my_list:
        await bot.send_message(
            chat_id=user_id,
            message_thread_id=thread_id,
            text=f"<blockquote>🎉 بارك الله! لقد أنجزت جميع أهدافك!</blockquote>\n\n"
                 f"<b>{mention} هل تريد أن توقف التنبيهات اليومية؟</b>",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        for goal_title, goal_data in my_list.items():
            goal_id = goal_data["goal_id"]
            sub_goals = goal_data["subgoals"]
            options = [sub["subgoal_title"] for sub in sub_goals]

            if len(options) < 2:
                options.extend(["لا يمكن إرسال تصويت", "بخيار واحد فقط، لذا نضيف هذين"])

            # Prepend mention in the question:
            question = f"{mention} - {goal_title}"

            sent_poll = await bot.send_poll(
                chat_id=-1002782644259,  # Your group chat ID
                message_thread_id=thread_id,
                question=question,
                options=options,
                is_anonymous=False,
                allows_multiple_answers=True,
            )

            poll_record = PollMappings(
                poll_id=sent_poll.poll.id,
                goal_id=goal_id,
                user_id=user_id
            )
            session.add(poll_record)
        session.commit()

    except Exception as e:
        session.rollback()
        print(f"❌ Failed to send poll for user {user_id}, goal '{goal_title}': {e}")
