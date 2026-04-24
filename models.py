from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

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


class UserSession(Base):
    """Модель сессии пользователя для persistent login"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)


class Experiment(Base):
    """Модель A/B эксперимента"""
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    metric_id = Column(Integer, ForeignKey("metrics.id"), nullable=False)
    status = Column(String, default="draft")  # draft, running, completed, archived
    test_type = Column(String, nullable=False)  # t-test, z-test, chi-square
    user_id_field = Column(String, nullable=False)  # название колонки с user_id
    date_field = Column(String, nullable=False)  # название колонки с датой
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    experiment_dataset_path = Column(String)  # путь к специальному датасету
    created_at = Column(DateTime, default=datetime.utcnow)
    config = Column(JSON)  # дополнительные настройки


class ExperimentGroup(Base):
    """Модель группы эксперимента"""
    __tablename__ = "experiment_groups"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    group_name = Column(String, nullable=False)  # A, B, C...
    description = Column(Text)
    is_control = Column(Integer, default=0)  # 0 = False, 1 = True (SQLite не поддерживает Boolean)
    user_count = Column(Integer, default=0)


class ExperimentUser(Base):
    """Модель пользователя в эксперименте"""
    __tablename__ = "experiment_users"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    user_id = Column(String, nullable=False)  # ID пользователя из датасета
    group_name = Column(String, nullable=False)  # A, B, C...
    assigned_at = Column(DateTime, default=datetime.utcnow)


class ExperimentResult(Base):
    """Модель результатов эксперимента"""
    __tablename__ = "experiment_results"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    group_name = Column(String, nullable=False)
    metric_value = Column(Integer)  # SQLite использует INTEGER для float
    sample_size = Column(Integer)
    std_dev = Column(Integer)  # SQLite использует INTEGER для float
    confidence_interval_lower = Column(Integer)  # SQLite использует INTEGER для float
    confidence_interval_upper = Column(Integer)  # SQLite использует INTEGER для float
    p_value = Column(Integer)  # SQLite использует INTEGER для float
    test_type = Column(String)
    is_significant = Column(Integer)  # 0 = False, 1 = True
    warning = Column(Text)
    time_series_data = Column(JSON)
    calculated_at = Column(DateTime, default=datetime.utcnow)


class Dataset(Base):
    """Модель загруженного датасета"""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rows_count = Column(Integer)
    columns_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Metric(Base):
    """Модель метрики"""
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Тип метрики: simple, user_level, time_window
    metric_type = Column(String, nullable=False)

    # Конфигурация метрики в JSON
    # Для simple: {"field": "amount", "aggregation": "sum", "filters": [...]}
    # Для user_level: {"user_field": "user_id", "value_field": "amount", "aggregation": "avg", "group_by": "user"}
    # Для time_window: {"date_field": "created_at", "value_field": "amount", "window": "day", "aggregation": "count"}
    config = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)


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


class DatasetCreate(BaseModel):
    """Схема для создания датасета"""
    name: str
    filename: str
    filepath: str
    rows_count: int
    columns_count: int


class MetricCreate(BaseModel):
    """Схема для создания метрики"""
    name: str
    description: Optional[str] = None
    dataset_id: int
    metric_type: str  # simple, user_level, time_window
    config: Dict[str, Any]


class ExperimentCreate(BaseModel):
    """Схема для создания эксперимента"""
    name: str
    description: Optional[str] = None
    dataset_id: int
    metric_id: int
    test_type: str  # t-test, z-test, chi-square
    user_id_field: str
    date_field: str
    start_date: datetime
    end_date: datetime
    config: Optional[Dict[str, Any]] = None