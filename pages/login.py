"""
Страница входа и регистрации
"""
import streamlit as st
from database import get_db, create_user, authenticate_user
from models import UserCreate, UserLogin
from utils.session_manager import create_user_session, cleanup_expired_sessions


def show_login_page(cookies):
    """Страница входа"""
    st.title("📊 TwoSigma")
    st.markdown("### Вход в систему")

    # Ждем пока cookies загрузятся
    if not cookies.ready():
        st.stop()

    tab1, tab2 = st.tabs(["Вход", "Регистрация"])

    # Вкладка входа
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Имя пользователя")
            password = st.text_input("Пароль", type="password")
            remember_me = st.checkbox("Запомнить меня", value=True)
            submit = st.form_submit_button("Войти")

            if submit:
                if not username or not password:
                    st.error("Заполните все поля!")
                else:
                    try:
                        db = get_db()
                        login_data = UserLogin(username=username, password=password)
                        user = authenticate_user(db, login_data)

                        if user:
                            # Очищаем старые сессии
                            cleanup_expired_sessions(db)

                            # Создаем новую сессию
                            expires_days = 30 if remember_me else 1
                            session_token = create_user_session(db, user.id, expires_days)

                            # Сохраняем токен в cookie
                            cookies["session_token"] = session_token
                            cookies.save()

                            # Сохраняем пользователя в session_state
                            st.session_state.user = {
                                "id": user.id,
                                "username": user.username,
                                "email": user.email
                            }

                            db.close()

                            st.success(f"Добро пожаловать, {user.username}!")
                            st.rerun()
                        else:
                            db.close()
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

