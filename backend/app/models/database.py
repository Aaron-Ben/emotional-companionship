"""Database configuration and models for emotional companionship system."""

import os
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 使用 SQLite 数据库
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./emotional_companionship.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DiaryTable(Base):
    """日记数据库表"""
    __tablename__ = "diaries"

    id = Column(String, primary_key=True, index=True)
    character_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    date = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    emotions = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
