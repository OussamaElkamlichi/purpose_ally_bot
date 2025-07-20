from flask import Flask, request, jsonify
from main import application
import asyncio
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update, delete, select, func
from models import DailySession, Goal, PollMappings, Subgoal, engine, User
from telegram import Update, Bot
from telegram.constants import ParseMode
from db_agent import reset

# Define your Telegram bot token here
TOKEN = ""

flask_app = Flask(__name__)
bot = application.bot
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
    
@flask_app.route('/custom_message', methods=['GET'])
def custom_message():
    async def inner():
        await bot.send_message(
            chat_id=-1002782644259,
            message_thread_id=18,
            reply_to_message_id=644,
            text=(
                "سيتم إرجاع رتبتك في الحال\n\n"
            ),
            parse_mode=ParseMode.HTML
        )

    asyncio.run(inner())
    return jsonify({"status": "✅ formal-funny reply sent", "reply_to": 642})


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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_send_polls_for_all_users())
        return jsonify({"status": "success", "message": "✅ stats sent to all users"})
    except Exception as e:
        return jsonify({"status": "X__X", "message": str(e)}), 500
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
            mention = f'<a href="tg://user?id={user_id}">{user.name}</a>'

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
            message_thread_id=18,
            text=f"<blockquote>🎉 بارك الله! لقد أنجزت جميع أهدافك!</blockquote>\n\n"
                 f"<b>{mention} هل تريد أن توقف التنبيهات اليومية؟</b>",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        sent_intro = False  # ✅ هذا هو المفتاح

        for goal_title, goal_data in my_list.items():
            goal_id = goal_data["goal_id"]
            sub_goals = goal_data["subgoals"]
            options = [sub["subgoal_title"] for sub in sub_goals]

            if len(options) < 2:
                options.extend(["لا يمكن إرسال تصويت", "بخيار واحد فقط، لذا نضيف هذين"])

            # ✅ أرسل الرسالة التعريفية مرة واحدة فقط
            if not sent_intro:
                await bot.send_message(
                    chat_id=-1002782644259,
                    message_thread_id=18,
                    text=f"{mention} - تفضل بتسجيل تقدمك لليوم مشكورًا 👇",
                    parse_mode="HTML"
                )
                sent_intro = True

            # أرسل التصويت
            question = f"{goal_title}"
            sent_poll = await bot.send_poll(
                chat_id=-1002782644259,
                message_thread_id=18,
                question=question,
                options=options,
                is_anonymous=False,
                allows_multiple_answers=True,
            )

            # سجل التصويت في قاعدة البيانات
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

@flask_app.route('/weekly_stats', methods=['GET'])
def fetch_and_prepare_stats():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_send_stats_for_all_users())
        return jsonify({"status": "success", "message": "✅ stats sent to all users"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

async def _async_send_stats_for_all_users():
    session = Session()
    try:
        users = session.query(User).all()
        for user in users:
            await send_stats(user.telegram_id, user.name)
    finally:
        session.close()

def progress_bar(percentage, length=20):
    percentage = min(percentage, 100)  # Prevent values over 100%
    completed = int((percentage / 100) * length)
    return "█" * completed + "░" * (length - completed) + f" {percentage:.1f}%"


async def send_stats(user_id, name):
    try:
        # Fetch data from the database
        total_goals, total_assigned_subgoals, completed_subgoals, completed_sessions, total_sessions = await fetch_weekly_data(user_id)

        # Calculate progress percentages (handle division by zero)
        goal_progress = (completed_subgoals / total_assigned_subgoals * 100) if total_assigned_subgoals > 0 else 0
        session_progress = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        mention = f'<a href="tg://user?id={user_id}">{name}</a>'
        report_message = (
            f"📊 <b>تقرير التقدم الأسبوعي الخاص بـ{mention}</b> 📊\n\n"
            f"🏆 <b>الأهداف الرئيسية:</b> {total_goals} هدف\n"
            f"🎯 <b>الأهداف الفرعية المكتملة:</b> {completed_subgoals} هدف فرعي\n"
            f"🕒 <b>الجلسات اليومية المكتملة:</b> {completed_sessions}/{total_sessions}\n\n"
            "🚀 <b>تقدم الأهداف:</b>\n"
            f"{progress_bar(goal_progress)}\n\n"
            "📅 <b>تقدم الجلسات اليومية:</b>\n"
            f"{progress_bar(session_progress)}\n\n"
            "✅ <b>استمر في العمل الجيد!</b> 💪"
        )   


        # Send the report message
        await bot.send_message(chat_id=-1002782644259, message_thread_id=18,  text=report_message, parse_mode="HTML")
    except Exception as e:
        print(f"Error in weekly_cron: {e}")

async def fetch_weekly_data(user_id):
    session = Session()
    try:
        # Total goals
        total_goals = session.query(func.count()).select_from(Goal).filter(Goal.user_id == user_id).scalar()

        # Total assigned subgoals (subgoals where goal belongs to the user)
        total_assigned_subgoals = session.query(func.count()).select_from(Subgoal).join(Goal).filter(Goal.user_id == user_id).scalar()

        # Completed subgoals for that user
        completed_subgoals = session.query(func.count()).select_from(Subgoal).join(Goal).filter(
            Goal.user_id == user_id,
            Subgoal.status == 'done'
        ).scalar()

        # Completed daily sessions
        completed_sessions = session.query(func.count()).select_from(DailySession).filter(
            DailySession.user_id == user_id,
            DailySession.status == 'done'
        ).scalar()

        # Total daily sessions
        total_sessions = session.query(func.count()).select_from(DailySession).filter(
            DailySession.user_id == user_id
        ).scalar()

        print(total_goals, total_assigned_subgoals, completed_subgoals, completed_sessions, total_sessions)
        return total_goals, total_assigned_subgoals, completed_subgoals, completed_sessions, total_sessions

    except Exception as e:
        print(f"Database error: {e}")
        return 0, 0, 0, 0, 0

    finally:
        session.close()