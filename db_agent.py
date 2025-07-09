from sqlalchemy.orm import sessionmaker
from models import engine, User
from datetime import datetime

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















