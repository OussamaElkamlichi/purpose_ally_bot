from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from models import engine, User, Goal, Subgoal, Scheduled
from datetime import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

Session = sessionmaker(bind=engine)

def add_user(telegram_id: int, name: str, rank: str ,
             prod_hours: int = 0, today_prod_hours: int = 0,
             highest_daily_prod: int = 0, challenges: int = 0):
    session = Session()
    user = User(
        telegram_id=telegram_id,
        name=name,
        rank=rank,
        prod_hours=prod_hours,
        today_prod_hours=today_prod_hours,
        highest_daily_prod=highest_daily_prod,
        challenges=challenges,
        created_at=datetime.utcnow()
    )
    session.add(user)
    name_to_return = user.name
    session.commit()
    session.close()
    return name_to_return

def get_user_by_telegram_id(telegram_id: int):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        return user  # can be None if not found
    finally:
        session.close()

def get_user_prod_hours(telegram_id: int):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            return user.prod_hours, user.rank
        else:
            return None, None  # أو raise Exception("User not found")
    finally:
        session.close()

def get_user_stats_message(telegram_id):
    session = Session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    session.close()

    if not user:
        return "❌ المستخدم غير مسجل."

    prod_hours, prod_remaining_minutes = divmod(user.prod_hours, 60)
    today_prod_hours, today_prod_remaining_minutes = divmod(user.today_prod_hours, 60)
    highest_daily_prod_hours, highest_daily_prod_remaining_minutes = divmod(user.highest_daily_prod, 60)

    return (
        f"📊 *إحصائيات {user.name}*\n\n"
        f"🏅 *الرتبة:* {user.rank}\n\n"
        f"⏳ *مجموع الاستثمار:* {prod_hours} ساعة و {prod_remaining_minutes} دقيقة\n\n"
        f"⏰ *استثمارك اليوم:* {today_prod_hours} ساعة و {today_prod_remaining_minutes} دقيقة\n\n"
        f"🚀 *أعلى استثمار لديك:* {highest_daily_prod_hours} ساعة و {highest_daily_prod_remaining_minutes} دقيقة\n\n"
        f"🎯 *عدد التحديات:* {user.challenges}\n\n"
        f"🗓️ *تاريخ الانضمام:* {user.created_at.strftime('%d/%m/%Y')}"
    )

def add_session(telegram_id: int, duration_minutes: int):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user is None:
            return 401, "يبدو أنك غير مسجل، الرجاء التسجيل بالبوت أولا عبر تشغيل الأمر #تسجيل"

        user.prod_hours = (user.prod_hours or 0) + duration_minutes
        user.today_prod_hours = (user.today_prod_hours or 0) + duration_minutes  # fix here

        session.commit()
        return 200, user.today_prod_hours
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def delete_session(telegram_id, duration):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            if duration > user.prod_hours:
                return "مدة الحذف أكبر من دقائق الإنتاج"
            user.prod_hours = user.prod_hours - duration
            user.today_prod_hours = user.today_prod_hours - duration
            session.commit()
            return f"تم حذف {duration} دقيقة"
        else:
            print(f"⚠️ User {telegram_id} not found.")
    except Exception as e:
        session.rollback()
        print(f"❌ Error subtracting prod_hours for user {telegram_id}: {e}")

def update_user_rank(telegram_id: int, new_rank: str):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.rank = new_rank
            session.commit()
            return 200
        else:
            print("❌ User not found in database.")
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to update rank: {e}")
    finally:
        session.close()

def reset():
    session = Session()
    try:
        session.query(User).update({User.today_prod_hours: 0})
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def user_check(user_id, name, rank, prod_hours: int = 0, today_prod_hours: int = 0,
             highest_daily_prod: int = 0, challenges: int = 0):
    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()
    if user:
        # Récupérer les objectifs de l'utilisateur
        goals = session.query(Goal).filter_by(user_id=user_id).all()
        total_goals = len(goals)

        if total_goals > 0:
            # Nombre d'objectifs complétés
            checked_goals = session.query(func.count(Goal.goal_id)).filter_by(
                user_id=user_id, status='done'
            ).scalar()

            if checked_goals < total_goals:
                result = {
                    "message": f"<blockquote>🍃<b>{name}</b> ،مرحباً</blockquote>\n\n"
                               f"لقد سجّلت معنا أهدافًا في السابق. ولديك أهداف مكتملة بمعدل {checked_goals}/{total_goals}\n"
                               f"<blockquote><b>البداية الجديدة تحمو جميع المعلومات</b></blockquote>",
                    "reply_markup": InlineKeyboardMarkup([
                        [InlineKeyboardButton('أريد أن أتابع 💪', callback_data='indeed')],
                        [InlineKeyboardButton('أريد بداية جديدة 🆕', callback_data='new_start')]
                    ])
                }
                return 200, result

            elif checked_goals == total_goals:
                result = {
                    "message": f"<blockquote>🍃<b>{name}</b> ،مرحباً</blockquote>\n\n"
                               f"لقد سجّلت معنا أهدافًا في السابق. ولديك جميع الأهداف مكتملة بمعدل {checked_goals}/{total_goals}\n\n"
                               f"<blockquote><b>البداية الجديدة تحمو جميع المعلومات</b></blockquote>",
                    "reply_markup": InlineKeyboardMarkup([
                        [InlineKeyboardButton('أريد بداية جديدة 🆕', callback_data='new_start')]
                    ])
                }
                return 200, result
        else:
            # Aucun objectif enregistré
            result = {
                "message": f"<blockquote>🍃<b>{name}</b> ،مرحباً</blockquote>\n\n"
                           "لقد سجّلت معنا أهدافًا في السابق. لكن دون أهداف",
                "reply_markup": InlineKeyboardMarkup([
                    [InlineKeyboardButton('أريد بداية جديدة', callback_data='new_start')]
                ])
            }
            return 200, result
    else:
        # Nouvel utilisateur → insertion
        new_user = User(
            telegram_id=user_id,
            name=name,
            rank=rank,
            prod_hours=prod_hours,
            today_prod_hours=today_prod_hours,
            highest_daily_prod=highest_daily_prod,
            challenges=challenges,
            created_at=datetime.utcnow()
        )
        session.add(new_user)
        session.commit()
        return 201, {"message": "done"}

def goals_seeding(goals_list, user_id):
    session = Session()
    try:
        for main_goal, sub_goals in goals_list.items():
            # Insert main goal
            goal_obj = Goal(
                user_id=user_id,
                goal_title=main_goal,
                goal_description=None,
                status="not_started",
                target_date=None
            )
            session.add(goal_obj)
            session.flush()  # To get goal_obj.id
            # Insert each sub-goal
            for sub_goal in sub_goals:
                subgoal_obj = Subgoal(
                    goal_id=goal_obj.goal_id,
                    subgoal_title=sub_goal,
                    subgoal_description="None",
                    duration="None",
                    status="not_started",
                    target_date="None"
                )
                session.add(subgoal_obj)
        session.commit()
        return "تم الإدخال"
    except Exception as err:
        session.rollback()
        return f"Error: {err}"
    finally:
        session.close()

def show_demo_db(user_id):
    session = Session()
    my_list = {}
    try:
        goals = session.query(Goal).filter_by(user_id=user_id).all()
        for goal in goals:
            # Fetch subgoals for the current main goal
            subgoals = session.query(Subgoal).filter_by(goal_id=goal.goal_id).all()
            subgoals_list = [
                {"subgoal_title": subgoal.subgoal_title, "status": subgoal.status}
                for subgoal in subgoals
            ]
            my_list[goal.goal_title] = subgoals_list
        return my_list
    except Exception as err:
        return f"Error: {err}"
    finally:
        session.close()

def edit_prep(user_id: int):
    session = Session()
    try:
        main_list = []

        # Récupérer les objectifs principaux
        main_goals = session.query(Goal).filter(Goal.user_id == user_id).all()

        for goal in main_goals:
            main_list.append({
                "type": "main",
                "id": goal.goal_id,
                "text": goal.goal_title
            })

            # Récupérer les sous-objectifs liés à ce goal
            subgoals = session.query(Subgoal).filter(Subgoal.goal_id == goal.goal_id).all()
            for sub in subgoals:
                main_list.append({
                    "type": "sub",
                    "id": sub.subgoal_id,
                    "text": sub.subgoal_title
                })

        return main_list
    except Exception as e:
        return f"Error: {e}"
    finally:
        session.close()

def updateGoal(user_id, new_goal_text, goal_type, goal_id, old_goal_text=None):
    session = Session()
    try:
        if goal_type == "main":
            goal = session.query(Goal).filter(Goal.goal_id == goal_id, Goal.user_id == user_id).first()
            if not goal:
                return "الهدف الرئيسي غير موجود."
            goal.goal_title = new_goal_text

        elif goal_type == "sub":
            subgoal = session.query(Subgoal).filter(Subgoal.subgoal_id == goal_id).join(Goal).filter(Goal.user_id == user_id).first()
            if not subgoal:
                return "الهدف الفرعي غير موجود."
            subgoal.subgoal_title = new_goal_text

        else:
            return "نوع الهدف غير معروف."

        session.commit()
        return "تم تحديث الهدف بنجاح."
    except Exception as e:
        session.rollback()
        return f"فشل التحديث: {str(e)}"
    finally:
        session.close()

def cron_seed(user_id, type, params, jobId):
    session = Session()
    try:
        scheduled = session.query(Scheduled).filter(Scheduled.user_id == user_id).first()

        if scheduled:
            scheduled.type = type
            scheduled.cron_pattern = params
            scheduled.job_id = jobId
            session.commit()
            return True  # ou: session.is_modified(scheduled)
        else:
            new_schedule = Scheduled(
                user_id=user_id,
                type=type,
                cron_pattern=params,
                job_id=jobId
            )
            session.add(new_schedule)
            session.commit()
            return True
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def get_goals(user_id: int):
    session = Session()
    try:
        my_list = {}

        # Récupérer les goals de l'utilisateur
        goals = session.query(Goal).filter_by(user_id=user_id).all()

        for goal in goals:
            subgoals_data = []

            # Récupérer les subgoals liés à ce goal
            subgoals = session.query(Subgoal).filter_by(goal_id=goal.goal_id).all()

            for sub in subgoals:
                subgoals_data.append({
                    "subgoal_id": sub.id,
                    "subgoal_title": sub.subgoal_title,
                    "status": sub.status
                })

            my_list[goal.goal_title] = {
                "goal_id": goal.goal_id,
                "main_status": goal.status,
                "subgoals": subgoals_data
            }

        print(my_list)
        return 200, my_list
    except Exception as e:
        print(f"An error occurred: {e}")
        return 500, str(e)
    finally:
        session.close()

def destroy_user(user_id):
    session = Session()
    try:
        # Recherche de l'utilisateur par username_id
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user:
            session.delete(user)
            session.commit()
            return 200
        else:
            return 500
    except Exception as err:
        print("Error:", err)
        session.rollback()
        return 500
    finally:
        session.close()