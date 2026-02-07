"""Database configuration and models for emotional companionship system."""

import os
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime
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


class DiaryFileTable(Base):
    """日记表"""
    __tablename__ = "diary_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(Text, unique=True, nullable=False, index=True)
    diary_name = Column(String, nullable=False, index=True)
    checksum = Column(String, nullable=False)
    mtime = Column(Integer, nullable=False)
    size = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
