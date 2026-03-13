"""
Боковая панель навигации
"""
import streamlit as st


def render_sidebar() -> str:
    """
    Отрисовка боковой панели
    Возвращает выбранную страницу
    """
    with st.sidebar:
        st.markdown("# 🧪 TwoSigma")
        st.markdown("### Платформа A/B тестирования")
        st.markdown("---")
        
        # Навигация
        page = st.radio(
            "Навигация",
            [
                "📊 Дашборд",
                "🧪 Эксперименты",
                "➕ Новый эксперимент",
                "🚩 Feature Flags",
                "📈 Аналитика",
                "⚙️ Настройки"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Информация о текущем статусе
        st.markdown("### Статус системы")
        
        # Подключение к БД
        db_status = st.session_state.get('db_connected', False)
        st.metric(
            label="База данных",
            value="✅ Подключено" if db_status else "❌ Не подключено",
            label_visibility="collapsed"
        )
        
        # Активные эксперименты
        active_experiments = st.session_state.get('active_experiments', 0)
        st.metric(
            label="Активные эксперименты",
            value=active_experiments,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Быстрые действия
        st.markdown("### Быстрые действия")
        
        if st.button("🔄 Обновить данные", use_container_width=True):
            st.rerun()
        
        if st.button("📥 Импорт данных", use_container_width=True):
            st.info("Функция импорта в разработке")
        
        # Footer
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: gray; font-size: 0.8em;'>
                TwoSigma v0.1.0<br>
                Аналог TriSigma
            </div>
            """,
            unsafe_allow_html=True
        )
    
    return page


def get_page_key(page: str) -> str:
    """Преобразование названия страницы в ключ"""
    page_map = {
        "📊 Дашборд": "dashboard",
        "🧪 Эксперименты": "experiments",
        "➕ Новый эксперимент": "new_experiment",
        "🚩 Feature Flags": "feature_flags",
        "📈 Аналитика": "analytics",
        "⚙️ Настройки": "settings"
    }
    return page_map.get(page, "dashboard")
