"""
Утилиты для управления пользовательскими сессиями

Обеспечивает функциональность "запомнить меня" через cookie-based аутентификацию.
Каждая сессия имеет уникальный токен и срок действия.
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import UserSession


def create_user_session(db: Session, user_id: int, expires_days: int = 30) -> str:
    """
    Создание новой сессии для пользователя

    Генерирует уникальный UUID токен и сохраняет его в БД.
    Токен используется для автоматической авторизации при повторном входе.

    Args:
        db: Сессия БД SQLAlchemy
        user_id: ID пользователя
        expires_days: Количество дней до истечения сессии (по умолчанию 30)

    Returns:
        session_token: Уникальный токен сессии (UUID)

    Example:
        >>> token = create_user_session(db, user_id=1, expires_days=7)
        >>> print(token)
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
    """
    # Генерируем криптографически стойкий уникальный токен
    session_token = str(uuid.uuid4())

    # Вычисляем дату истечения сессии
    expires_at = datetime.utcnow() + timedelta(days=expires_days)

    # Создаем запись сессии в БД
    db_session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )

    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    return session_token


def get_session_by_token(db: Session, session_token: str) -> UserSession | None:
    """
    Получение сессии по токену

    Используется для проверки валидности токена из cookie
    и восстановления информации о пользователе.

    Args:
        db: Сессия БД SQLAlchemy
        session_token: Токен сессии из cookie

    Returns:
        UserSession: Объект сессии или None если токен не найден

    Example:
        >>> session = get_session_by_token(db, token)
        >>> if session and is_session_valid(session):
        >>>     print(f"User ID: {session.user_id}")
    """
    return db.query(UserSession).filter(
        UserSession.session_token == session_token
    ).first()


def update_session_activity(db: Session, session_id: int) -> None:
    """
    Обновление времени последней активности сессии

    Вызывается при каждом запросе авторизованного пользователя
    для отслеживания активности и возможного продления сессии.

    Args:
        db: Сессия БД SQLAlchemy
        session_id: ID сессии в БД

    Note:
        Не продлевает срок действия сессии, только обновляет last_activity
    """
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if session:
        session.last_activity = datetime.utcnow()
        db.commit()


def delete_session_by_token(db: Session, session_token: str) -> bool:
    """
    Удаление сессии по токену (выход из системы)

    Используется при явном выходе пользователя из системы.
    После удаления токен становится невалидным.

    Args:
        db: Сессия БД SQLAlchemy
        session_token: Токен сессии для удаления

    Returns:
        bool: True если сессия была удалена, False если не найдена

    Example:
        >>> if delete_session_by_token(db, token):
        >>>     print("Вы вышли из системы")
    """
    session = db.query(UserSession).filter(
        UserSession.session_token == session_token
    ).first()

    if session:
        db.delete(session)
        db.commit()
        return True

    return False


def delete_user_sessions(db: Session, user_id: int) -> int:
    """
    Удаление всех сессий пользователя

    Используется для принудительного выхода пользователя со всех устройств.
    Полезно при смене пароля или подозрении на компрометацию аккаунта.

    Args:
        db: Сессия БД SQLAlchemy
        user_id: ID пользователя

    Returns:
        int: Количество удаленных сессий

    Example:
        >>> count = delete_user_sessions(db, user_id=1)
        >>> print(f"Удалено {count} активных сессий")
    """
    count = db.query(UserSession).filter(UserSession.user_id == user_id).delete()
    db.commit()
    return count


def cleanup_expired_sessions(db: Session) -> int:
    """
    Удаление всех истекших сессий из БД

    Рекомендуется запускать периодически (например, раз в день)
    для очистки БД от устаревших записей.

    Args:
        db: Сессия БД SQLAlchemy

    Returns:
        int: Количество удаленных сессий

    Example:
        >>> # Запуск в cron или при старте приложения
        >>> count = cleanup_expired_sessions(db)
        >>> print(f"Очищено {count} истекших сессий")
    """
    count = db.query(UserSession).filter(
        UserSession.expires_at < datetime.utcnow()
    ).delete()
    db.commit()
    return count


def is_session_valid(session: UserSession) -> bool:
    """
    Проверка валидности сессии по сроку действия

    Args:
        session: Объект сессии из БД

    Returns:
        bool: True если сессия еще действительна, False если истекла

    Example:
        >>> session = get_session_by_token(db, token)
        >>> if session and is_session_valid(session):
        >>>     # Сессия валидна, можно авторизовать пользователя
        >>>     user = get_user_by_id(db, session.user_id)
    """
    return session.expires_at > datetime.utcnow()

