import streamlit as st
import pandas as pd
from streamlit_cookies_manager import EncryptedCookieManager
from pathlib import Path
from database import init_db, get_db, get_user_datasets, get_user_metrics, get_user_by_id
from pages.login import show_login_page
from pages.datasets import show_datasets_page
from pages.metrics import show_metrics_page
from pages.experiments import show_experiments_page
from pages.tutorial import show_tutorial_page
from utils.session_manager import get_session_by_token, update_session_activity, is_session_valid

# Настройка страницы
st.set_page_config(
    page_title="TwoSigma - A/B Testing Platform",
    page_icon="📊",
    layout="wide"
)

# Инициализация БД при первом запуске
init_db()

# Создание директории для загруженных файлов
UPLOAD_DIR = Path("uploaded_datasets")
UPLOAD_DIR.mkdir(exist_ok=True)

# Инициализация cookie manager
cookies = EncryptedCookieManager(
    prefix="twosigma_",
    password="your-secret-key-change-this-in-production"
)

# Инициализация состояния сессии
if "user" not in st.session_state:
    st.session_state.user = None

# Попытка автологина из cookie
if st.session_state.user is None and cookies.ready():
    session_token = cookies.get("session_token")

    if session_token:
        try:
            db = get_db()
            user_session = get_session_by_token(db, session_token)

            if user_session and is_session_valid(user_session):
                # Восстанавливаем пользователя
                user = get_user_by_id(db, user_session.user_id)

                if user:
                    st.session_state.user = {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email
                    }

                    # Обновляем время последней активности
                    update_session_activity(db, user_session.id)
            else:
                # Токен невалиден - удаляем cookie
                if "session_token" in cookies:
                    del cookies["session_token"]
                    cookies.save()

            db.close()
        except Exception as e:
            # Игнорируем ошибки при автологине
            pass


def show_main_page():
    """Главная страница после входа"""
    # Инициализация текущей страницы
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Главная"

    # Боковая панель с информацией о пользователе
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['username']}")

        st.divider()

        # Навигация с красивыми кнопками
        st.markdown("### Навигация")

        # Стили для кнопок навигации
        nav_style = """
        <style>
        div[data-testid="stButton"] > button {
            width: 100%;
            text-align: left;
            padding: 12px 16px;
            border-radius: 8px;
            border: none;
            margin-bottom: 8px;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        div[data-testid="stButton"] > button:hover {
            transform: translateX(4px);
        }
        </style>
        """
        st.markdown(nav_style, unsafe_allow_html=True)

        # Кнопки навигации
        if st.button("🏠  Главная", key="nav_home", use_container_width=True):
            st.session_state.current_page = "Главная"
            st.rerun()

        if st.button("📁  Датасеты", key="nav_datasets", use_container_width=True):
            st.session_state.current_page = "Датасеты"
            st.rerun()

        if st.button("📊  Метрики", key="nav_metrics", use_container_width=True):
            st.session_state.current_page = "Метрики"
            st.rerun()

        if st.button("🧪  Эксперименты", key="nav_experiments", use_container_width=True):
            st.session_state.current_page = "Эксперименты"
            st.rerun()

        st.divider()

        if st.button("🚪 Выйти", use_container_width=True):
            # Удаляем сессию из БД
            if cookies.ready():
                session_token = cookies.get("session_token")
                if session_token:
                    try:
                        from utils.session_manager import delete_session_by_token
                        db = get_db()
                        delete_session_by_token(db, session_token)
                        db.close()
                    except:
                        pass

                # Удаляем cookie
                if "session_token" in cookies:
                    del cookies["session_token"]
                    cookies.save()

            # Очищаем session_state
            st.session_state.user = None
            st.session_state.current_page = "Главная"
            st.rerun()

    page = st.session_state.current_page

    # Роутинг страниц
    if page == "Датасеты":
        show_datasets_page()
    elif page == "Метрики":
        show_metrics_page()
    elif page == "Эксперименты":
        show_experiments_page()
    elif page == "Обучение":
        show_tutorial_page()
    else:
        # Главная страница
        st.title("📊 TwoSigma")
        st.markdown("Аналитическая платформа для A/B-тестирования")

        st.header(f"Добро пожаловать, {st.session_state.user['username']}!")

        st.markdown("""
        ### Возможности платформы:
        - 🧪 Создание и управление экспериментами
        - 📈 Расчёт метрик и статистической значимости
        - 📊 Интерактивные дашборды и визуализация
        - 🔄 Детерминированное сплитование пользователей
        """)

        # Статистика
        db = get_db()
        datasets_count = len(get_user_datasets(db, st.session_state.user['id']))
        metrics_count = len(get_user_metrics(db, st.session_state.user['id']))

        from database import get_user_experiments
        experiments = get_user_experiments(db, st.session_state.user['id'])
        active_experiments = len([e for e in experiments if e.status in ['draft', 'running']])
        completed_experiments = len([e for e in experiments if e.status == 'completed'])
        db.close()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Активных экспериментов", active_experiments)
        with col2:
            st.metric("Завершённых экспериментов", completed_experiments)
        with col3:
            st.metric("Загруженных датасетов", datasets_count)
        with col4:
            st.metric("Созданных метрик", metrics_count)

        # Кнопка обучения внизу справа
        st.markdown("<br>" * 3, unsafe_allow_html=True)
        col_left, col_right = st.columns([3, 1])
        with col_right:
            if st.button("📚 Обучение", key="tutorial_bottom", use_container_width=True, type="secondary"):
                st.session_state.current_page = "Обучение"
                st.rerun()


# Основная логика приложения
if st.session_state.user is None:
    show_login_page(cookies)
else:
    show_main_page()
