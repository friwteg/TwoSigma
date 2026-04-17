from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, EmailStr

Base = declarative_base()


# SQLAlchemy модели (для БД)
class User(Base):
    """Модель пользователя в базе данных"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Experiment(Base):
    """Модель эксперимента в базе данных"""
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="draft")  # draft, active, completed


# Pydantic модели (для валидации данных)
class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    username: str
    password: str