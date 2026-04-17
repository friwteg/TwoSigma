import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, User, Experiment, UserCreate, UserLogin

# Путь к базе данных SQLite
DATABASE_URL = "sqlite:///./twosigma.db"

# Создание движка БД
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Создание всех таблиц в базе данных"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Получение сессии БД"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass


def hash_password(password: str) -> str:
    """Хеширование пароля с помощью SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(db: Session, user_data: UserCreate) -> User:
    """Создание нового пользователя"""
    # Проверяем, существует ли пользователь
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()

    if existing_user:
        raise ValueError("Пользователь с таким именем или email уже существует")

    # Создаём нового пользователя
    hashed_pwd = hash_password(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_pwd
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, login_data: UserLogin) -> User | None:
    """Проверка логина и пароля пользователя"""
    user = db.query(User).filter(User.username == login_data.username).first()

    if not user:
        return None

    # Проверяем пароль
    hashed_pwd = hash_password(login_data.password)
    if user.hashed_password != hashed_pwd:
        return None

    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Получение пользователя по ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_experiments(db: Session, user_id: int):
    """Получение всех экспериментов пользователя"""
    return db.query(Experiment).filter(Experiment.user_id == user_id).all()