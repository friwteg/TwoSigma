import streamlit as st
from database import init_db, get_db, create_user, authenticate_user
from models import UserCreate, UserLogin

# Настройка страницы
st.set_page_config(
    page_title="TwoSigma - A/B Testing Platform",
    page_icon="📊",
    layout="wide"
)

# Инициализация БД при первом запуске
init_db()

# Инициализация состояния сессии
if "user" not in st.session_state:
    st.session_state.user = None


def show_login_page():
    """Страница входа"""
    st.title("📊 TwoSigma")
    st.markdown("### Вход в систему")

    tab1, tab2 = st.tabs(["Вход", "Регистрация"])

    # Вкладка входа
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Имя пользователя")
            password = st.text_input("Пароль", type="password")
            submit = st.form_submit_button("Войти")

            if submit:
                if not username or not password:
                    st.error("Заполните все поля!")
                else:
                    try:
                        db = get_db()
                        login_data = UserLogin(username=username, password=password)
                        user = authenticate_user(db, login_data)
                        db.close()

                        if user:
                            st.session_state.user = {
                                "id": user.id,
                                "username": user.username,
                                "email": user.email
                            }
                            st.success(f"Добро пожаловать, {user.username}!")
                            st.rerun()
                        else:
                            st.error("Неверное имя пользователя или пароль")
                    except Exception as e:
                        st.error(f"Ошибка: {str(e)}")

    # Вкладка регистрации
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Имя пользователя", key="reg_username")
            new_email = st.text_input("Email", key="reg_email")
            new_password = st.text_input("Пароль", type="password", key="reg_password")
            new_password_confirm = st.text_input("Подтвердите пароль", type="password", key="reg_password_confirm")
            submit_reg = st.form_submit_button("Зарегистрироваться")

            if submit_reg:
                if not new_username or not new_email or not new_password:
                    st.error("Заполните все поля!")
                elif new_password != new_password_confirm:
                    st.error("Пароли не совпадают!")
                elif len(new_password) < 6:
                    st.error("Пароль должен быть не менее 6 символов!")
                else:
                    try:
                        db = get_db()
                        user_data = UserCreate(
                            username=new_username,
                            email=new_email,
                            password=new_password
                        )
                        user = create_user(db, user_data)
                        db.close()

                        st.success(f"Аккаунт создан! Теперь войдите с именем '{user.username}'")
                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Ошибка регистрации: {str(e)}")


def show_main_page():
    """Главная страница после входа"""
    # Боковая панель с информацией о пользователе
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['username']}")
        st.markdown(f"📧 {st.session_state.user['email']}")
        if st.button("Выйти"):
            st.session_state.user = None
            st.rerun()

    # Основной контент
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

    # Статистика (пока заглушка)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Активных экспериментов", "0")
    with col2:
        st.metric("Завершённых экспериментов", "0")
    with col3:
        st.metric("Всего пользователей", "0")

    st.info("Функционал создания экспериментов будет добавлен на следующем этапе!")


# Основная логика приложения
if st.session_state.user is None:
    show_login_page()
else:
    show_main_page()