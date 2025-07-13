from sqlalchemy import Column,text, TIMESTAMP, Integer, String, DateTime, create_engine, inspect, BigInteger, ForeignKey, Text, func
from sqlalchemy.orm import declarative_base
from datetime import datetime
import json
import os

Base = declarative_base()

DB_USER = 'OussamaNoobie'
DB_PASS = 'alhamdulillah'
DB_NAME = 'OussamaNoobie$default'

DATABASE_URL = 'mysql+pymysql://OussamaNoobie:alhamdulillah@OussamaNoobie.mysql.pythonanywhere-services.com/OussamaNoobie$default'
engine = create_engine(DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=10,
    max_overflow=5
)

base_dir = os.path.dirname(__file__)
json_path = os.path.join(base_dir, 'ranks.json')

with open(json_path, encoding='utf-8') as f:
    ranks = json.load(f)

default_rank = next(iter(ranks))

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String(100))
    rank = Column(String(100), default=default_rank)
    prod_hours = Column(Integer, default=0)
    today_prod_hours = Column(Integer, default=0)
    highest_daily_prod = Column(Integer, default=0)
    challenges = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Goal(Base):
    __tablename__ = 'goals'

    goal_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id', ondelete='CASCADE'), nullable=False)

    goal_title = Column(String(255), nullable=False)
    goal_description = Column(Text, nullable=True)

    status = Column(String(50), default='not_started')

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    target_date = Column(DateTime, nullable=True)



class Subgoal(Base):
    __tablename__ = 'subgoals'

    subgoal_id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(Integer, ForeignKey('goals.goal_id', ondelete='CASCADE'), nullable=False)

    subgoal_title = Column(String(255), nullable=False)
    subgoal_description = Column(Text, nullable=True)

    duration = Column(Integer, nullable=True)
    status = Column(String(50), default='not_started')

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    target_date = Column(DateTime, nullable=True)

class Scheduled(Base):
    __tablename__ = "scheduled"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), unique=True, index=True)
    type = Column(String(50), nullable=True)
    cron_pattern = Column(String(60), nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    job_id = Column(String(255), nullable=True)

def create_tables():
    Base.metadata.create_all(engine)
    print("✅ Tables created.")

def show_tables():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("📋 Tables in your database:")
    for table in tables:
        print(f" - {table}")
    return tables

# This allows you to run `python models.py` to create tables
if __name__ == '__main__':
    create_tables()
