import hashlib
from contextlib import contextmanager
from typing import Generator
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import (Base, User, Experiment, Dataset, Metric,
                    ExperimentGroup, ExperimentUser, ExperimentResult,
                    UserCreate, UserLogin, DatasetCreate, MetricCreate, ExperimentCreate)
from config import DATABASE_URL

# Миграция БД перед созданием engine
import sqlite3
from pathlib import Path

db_path = Path("twosigma.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Проверяем, существует ли колонка last_updated
        cursor.execute("PRAGMA table_info(datasets)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'last_updated' not in columns:
            # Добавляем колонку
            cursor.execute("ALTER TABLE datasets ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            # Обновляем существующие записи
            cursor.execute("UPDATE datasets SET last_updated = created_at WHERE last_updated IS NULL")
            conn.commit()
            print("✓ Миграция: колонка last_updated добавлена в таблицу datasets")
    except Exception as e:
        print(f"Ошибка миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

# Создание движка БД
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Создание всех таблиц в базе данных"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """
    Получение сессии БД

    ВАЖНО: Вызывающий код должен закрыть сессию вручную через db.close()
    Для автоматического управления используйте get_db_context()
    """
    return SessionLocal()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для автоматического управления сессией БД

    Использование:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


def get_user_experiments(db: Session, user_id: int) -> list[Experiment]:
    """Получение всех экспериментов пользователя"""
    return db.query(Experiment).filter(Experiment.user_id == user_id).all()


def create_dataset(db: Session, dataset_data: DatasetCreate, user_id: int) -> Dataset:
    """Создание записи о загруженном датасете"""
    # Проверяем, существует ли датасет с таким именем у пользователя
    existing_dataset = db.query(Dataset).filter(
        Dataset.user_id == user_id,
        Dataset.name == dataset_data.name
    ).first()

    if existing_dataset:
        raise ValueError(f"Датасет с именем '{dataset_data.name}' уже существует")

    db_dataset = Dataset(
        name=dataset_data.name,
        filename=dataset_data.filename,
        filepath=dataset_data.filepath,
        user_id=user_id,
        rows_count=dataset_data.rows_count,
        columns_count=dataset_data.columns_count
    )

    db.add(db_dataset)
    db.commit()
    db.refresh(db_dataset)
    return db_dataset


def get_user_datasets(db: Session, user_id: int) -> list[Dataset]:
    """Получение всех датасетов пользователя"""
    return db.query(Dataset).filter(Dataset.user_id == user_id).all()


def delete_dataset(db: Session, dataset_id: int, user_id: int) -> bool:
    """Удаление датасета"""
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == user_id
    ).first()

    if dataset:
        db.delete(dataset)
        db.commit()
        return True
    return False


def create_metric(db: Session, metric_data: MetricCreate, user_id: int) -> Metric:
    """Создание метрики"""
    # Проверяем, существует ли метрика с таким именем у пользователя
    existing_metric = db.query(Metric).filter(
        Metric.user_id == user_id,
        Metric.name == metric_data.name
    ).first()

    if existing_metric:
        raise ValueError(f"Метрика с именем '{metric_data.name}' уже существует")

    # Проверяем, что датасет принадлежит пользователю
    dataset = db.query(Dataset).filter(
        Dataset.id == metric_data.dataset_id,
        Dataset.user_id == user_id
    ).first()

    if not dataset:
        raise ValueError("Датасет не найден")

    db_metric = Metric(
        name=metric_data.name,
        description=metric_data.description,
        dataset_id=metric_data.dataset_id,
        user_id=user_id,
        metric_type=metric_data.metric_type,
        config=metric_data.config
    )

    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    return db_metric


def get_user_metrics(db: Session, user_id: int) -> list[Metric]:
    """Получение всех метрик пользователя"""
    return db.query(Metric).filter(Metric.user_id == user_id).all()


def get_metric_by_id(db: Session, metric_id: int, user_id: int) -> Metric | None:
    """Получение метрики по ID"""
    return db.query(Metric).filter(
        Metric.id == metric_id,
        Metric.user_id == user_id
    ).first()


def delete_metric(db: Session, metric_id: int, user_id: int) -> bool:
    """Удаление метрики"""
    metric = db.query(Metric).filter(
        Metric.id == metric_id,
        Metric.user_id == user_id
    ).first()

    if metric:
        db.delete(metric)
        db.commit()
        return True
    return False


def update_dataset_file(db: Session, dataset_id: int, user_id: int, new_filepath: str, rows_count: int, columns_count: int) -> Dataset:
    """Обновление файла датасета"""
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == user_id
    ).first()

    if not dataset:
        raise ValueError("Датасет не найден")

    dataset.filepath = new_filepath
    dataset.rows_count = rows_count
    dataset.columns_count = columns_count
    dataset.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(dataset)
    return dataset


# Функции для работы с экспериментами

def create_experiment(db: Session, experiment_data: ExperimentCreate, user_id: int) -> Experiment:
    """Создание эксперимента"""
    # Проверяем, что датасет принадлежит пользователю
    dataset = db.query(Dataset).filter(
        Dataset.id == experiment_data.dataset_id,
        Dataset.user_id == user_id
    ).first()

    if not dataset:
        raise ValueError("Датасет не найден")

    # Проверяем, что метрика принадлежит пользователю
    metric = db.query(Metric).filter(
        Metric.id == experiment_data.metric_id,
        Metric.user_id == user_id
    ).first()

    if not metric:
        raise ValueError("Метрика не найдена")

    db_experiment = Experiment(
        user_id=user_id,
        name=experiment_data.name,
        description=experiment_data.description,
        dataset_id=experiment_data.dataset_id,
        metric_id=experiment_data.metric_id,
        status="draft",
        test_type=experiment_data.test_type,
        user_id_field=experiment_data.user_id_field,
        date_field=experiment_data.date_field,
        start_date=experiment_data.start_date,
        end_date=experiment_data.end_date,
        config=experiment_data.config
    )

    db.add(db_experiment)
    db.commit()
    db.refresh(db_experiment)
    return db_experiment


def get_user_experiments(db: Session, user_id: int) -> list[Experiment]:
    """Получение всех экспериментов пользователя"""
    return db.query(Experiment).filter(Experiment.user_id == user_id).order_by(Experiment.created_at.desc()).all()


def get_experiment_by_id(db: Session, experiment_id: int, user_id: int) -> Experiment | None:
    """Получение эксперимента по ID"""
    return db.query(Experiment).filter(
        Experiment.id == experiment_id,
        Experiment.user_id == user_id
    ).first()


def update_experiment_status(db: Session, experiment_id: int, user_id: int, status: str) -> Experiment:
    """Обновление статуса эксперимента"""
    experiment = db.query(Experiment).filter(
        Experiment.id == experiment_id,
        Experiment.user_id == user_id
    ).first()

    if not experiment:
        raise ValueError("Эксперимент не найден")

    experiment.status = status
    db.commit()
    db.refresh(experiment)
    return experiment


def update_experiment_dataset_path(db: Session, experiment_id: int, user_id: int, dataset_path: str) -> Experiment:
    """Обновление пути к специальному датасету эксперимента"""
    experiment = db.query(Experiment).filter(
        Experiment.id == experiment_id,
        Experiment.user_id == user_id
    ).first()

    if not experiment:
        raise ValueError("Эксперимент не найден")

    experiment.experiment_dataset_path = dataset_path
    db.commit()
    db.refresh(experiment)
    return experiment


def delete_experiment(db: Session, experiment_id: int, user_id: int) -> bool:
    """Удаление эксперимента"""
    experiment = db.query(Experiment).filter(
        Experiment.id == experiment_id,
        Experiment.user_id == user_id
    ).first()

    if experiment:
        # Удаляем связанные данные
        db.query(ExperimentGroup).filter(ExperimentGroup.experiment_id == experiment_id).delete()
        db.query(ExperimentUser).filter(ExperimentUser.experiment_id == experiment_id).delete()
        db.query(ExperimentResult).filter(ExperimentResult.experiment_id == experiment_id).delete()

        db.delete(experiment)
        db.commit()
        return True
    return False


def create_experiment_group(db: Session, experiment_id: int, group_name: str, is_control: bool, user_count: int = 0, description: str = None) -> ExperimentGroup:
    """Создание группы эксперимента"""
    db_group = ExperimentGroup(
        experiment_id=experiment_id,
        group_name=group_name,
        description=description,
        is_control=1 if is_control else 0,
        user_count=user_count
    )

    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


def get_experiment_groups(db: Session, experiment_id: int) -> list[ExperimentGroup]:
    """Получение всех групп эксперимента"""
    return db.query(ExperimentGroup).filter(ExperimentGroup.experiment_id == experiment_id).all()


def create_experiment_user(db: Session, experiment_id: int, user_id: str, group_name: str) -> ExperimentUser:
    """Добавление пользователя в эксперимент"""
    db_exp_user = ExperimentUser(
        experiment_id=experiment_id,
        user_id=user_id,
        group_name=group_name
    )

    db.add(db_exp_user)
    return db_exp_user


def create_experiment_users_bulk(db: Session, experiment_id: int, users_data: list[tuple[str, str]]) -> None:
    """Массовое добавление пользователей в эксперимент

    Args:
        users_data: список кортежей (user_id, group_name)
    """
    exp_users = [
        ExperimentUser(experiment_id=experiment_id, user_id=uid, group_name=gname)
        for uid, gname in users_data
    ]

    db.bulk_save_objects(exp_users)
    db.commit()


def get_experiment_users(db: Session, experiment_id: int, group_name: str = None) -> list[ExperimentUser]:
    """Получение пользователей эксперимента

    Args:
        experiment_id: ID эксперимента
        group_name: Фильтр по группе (опционально)
    """
    query = db.query(ExperimentUser).filter(ExperimentUser.experiment_id == experiment_id)

    if group_name:
        query = query.filter(ExperimentUser.group_name == group_name)

    return query.all()


def save_experiment_results(db: Session, experiment_id: int, results_data: dict) -> ExperimentResult:
    """Сохранение результатов эксперимента"""
    db_result = ExperimentResult(
        experiment_id=experiment_id,
        group_name=results_data['group_name'],
        metric_value=results_data.get('metric_value'),
        sample_size=results_data.get('sample_size'),
        std_dev=results_data.get('std_dev'),
        confidence_interval_lower=results_data.get('confidence_interval_lower'),
        confidence_interval_upper=results_data.get('confidence_interval_upper'),
        p_value=results_data.get('p_value'),
        test_type=results_data.get('test_type'),
        is_significant=1 if results_data.get('is_significant') else 0,
        warning=results_data.get('warning'),
        time_series_data=results_data.get('time_series_data')
    )

    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result


def get_experiment_results(db: Session, experiment_id: int) -> list[ExperimentResult]:
    """Получение результатов эксперимента"""
    return db.query(ExperimentResult).filter(ExperimentResult.experiment_id == experiment_id).all()


def get_active_experiments_for_dataset(db: Session, dataset_id: int) -> list[Experiment]:
    """Получение активных экспериментов для датасета"""
    return db.query(Experiment).filter(
        Experiment.dataset_id == dataset_id,
        Experiment.status.in_(['running', 'draft'])
    ).all()