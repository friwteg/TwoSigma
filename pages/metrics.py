"""
Страница управления метриками
"""
import streamlit as st
import pandas as pd
from database import get_db, get_user_datasets, get_user_metrics, delete_metric
from components.metric_calculator import calculate_metric
from components.metric_creator import show_sql_metric_creator, show_constructor_metric_creator
from utils.metric_templates import TEMPLATE_NAMES
from utils.metric_display import display_period_metric_result, display_sql_metric_result, display_simple_metric_result


def _get_config(metric) -> dict:
    """
    Безопасно возвращает конфигурацию метрики как словарь.
    Если metric.config является строкой (например, сериализованный JSON)
    или None — возвращает пустой словарь, избегая AttributeError.
    """
    import json
    cfg = metric.config
    if isinstance(cfg, dict):
        return cfg
    if isinstance(cfg, str):
        try:
            parsed = json.loads(cfg)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def show_metrics_page():
    """Страница управления метриками"""

    # Проверяем, находимся ли мы на странице создания метрики
    if st.session_state.get("show_create_metric_page", False):
        show_create_metric_page()
        return

    # Заголовок с кнопкой создания
    col_title, col_button = st.columns([3, 1])
    with col_title:
        st.title("📊 Метрики")
    with col_button:
        if st.button("➕ Добавить новую метрику", use_container_width=True, type="primary"):
            st.session_state["show_create_metric_page"] = True
            st.rerun()

    # Получаем датасеты пользователя
    db = get_db()
    datasets = get_user_datasets(db, st.session_state.user['id'])
    metrics = get_user_metrics(db, st.session_state.user['id'])
    db.close()

    if not datasets:
        st.warning("Сначала загрузите датасет в разделе 'Датасеты'")
        return

    # Показываем уведомление о создании метрики
    if st.session_state.get("metric_created"):
        st.success(f"✅ Метрика '{st.session_state.get('metric_created_name')}' успешно создана!", icon="🎉")
        del st.session_state["metric_created"]
        del st.session_state["metric_created_name"]

    if not metrics:
        st.info("У вас пока нет созданных метрик. Нажмите кнопку 'Добавить новую метрику' для создания первой метрики.")
    else:
        # Сортируем метрики по ID в обратном порядке (новые сверху)
        metrics_sorted = sorted(metrics, key=lambda x: x.id, reverse=True)

        for metric in metrics_sorted:
            # Получаем информацию о датасете
            dataset = next((ds for ds in datasets if ds.id == metric.dataset_id), None)

            # Безопасно получаем конфигурацию
            config = _get_config(metric)

            # Определяем тип метрики для отображения
            if metric.metric_type == "template":
                template_key = config.get("template")
                metric_type_label = TEMPLATE_NAMES.get(template_key, "Шаблонная метрика")
            elif metric.metric_type == "sql":
                metric_type_label = "SQL-запрос"
            else:
                metric_type_label = metric.metric_type

            # Компактная карточка метрики
            with st.container():
                col_icon, col_name, col_type, col_calc, col_delete = st.columns([0.3, 3, 2, 1, 1])

                with col_icon:
                    st.markdown("### 📊")

                with col_name:
                    st.markdown(f"### {metric.name}")

                with col_type:
                    st.markdown(f"<div style='padding-top: 8px; color: #666;'>{metric_type_label}</div>", unsafe_allow_html=True)

                with col_calc:
                    is_expanded = st.session_state.get(f"show_metric_{metric.id}", False)
                    button_label = "🔼 Скрыть" if is_expanded else "📊 Рассчитать"

                    if st.button(button_label, key=f"calc_{metric.id}", use_container_width=True):
                        if is_expanded:
                            st.session_state[f"show_metric_{metric.id}"] = False
                        else:
                            st.session_state[f"show_metric_{metric.id}"] = True
                            st.session_state[f"just_calculated_{metric.id}"] = True

                with col_delete:
                    if st.button("🗑️", key=f"delete_metric_{metric.id}", use_container_width=True, help="Удалить метрику"):
                        st.session_state[f"confirm_delete_{metric.id}"] = True

                # Подтверждение удаления
                if st.session_state.get(f"confirm_delete_{metric.id}", False):
                    st.warning("⚠️ Вы уверены, что хотите удалить эту метрику?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ Да, удалить", key=f"confirm_yes_{metric.id}", use_container_width=True):
                            try:
                                db = get_db()
                                delete_metric(db, metric.id, st.session_state.user['id'])
                                db.close()
                                if f"show_metric_{metric.id}" in st.session_state:
                                    del st.session_state[f"show_metric_{metric.id}"]
                                if f"confirm_delete_{metric.id}" in st.session_state:
                                    del st.session_state[f"confirm_delete_{metric.id}"]
                                st.toast("✓ Метрика удалена", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.toast(f"❌ Ошибка удаления: {str(e)}", icon="❌")
                    with col_no:
                        if st.button("❌ Отмена", key=f"confirm_no_{metric.id}", use_container_width=True):
                            st.session_state[f"confirm_delete_{metric.id}"] = False

            # Расчет метрики (показывается только если развернуто)
            if st.session_state.get(f"show_metric_{metric.id}", False):
                metric_container = st.container()

                with metric_container:
                    try:
                        df = pd.read_csv(dataset.filepath)

                        # Безопасно получаем конфигурацию для расчёта
                        config = _get_config(metric)
                        modified_config = config.copy()

                        # Проверяем, есть ли у метрики поле даты (для графиков)
                        has_date_field = False
                        if metric.metric_type == "template":
                            fields = config.get("fields", {})
                            template_type = config.get("template")

                            if fields.get("date_field"):
                                has_date_field = True
                            elif template_type in ["dau", "wau", "mau", "churn", "retention"]:
                                has_date_field = True

                        # Если есть временное измерение, показываем селектор группировки
                        time_window = "day"
                        if has_date_field and config.get("template") not in ["dau", "wau", "mau"]:
                            time_window = st.selectbox(
                                "Группировка",
                                options=["day", "week", "month"],
                                format_func=lambda x: {"day": "По дням", "week": "По неделям", "month": "По месяцам"}[x],
                                key=f"time_window_{metric.id}",
                                index={"day": 0, "week": 1, "month": 2}.get(
                                    config.get("fields", {}).get("time_window", "day"), 0
                                )
                            )

                        if metric.metric_type == "template":
                            if "fields" not in modified_config:
                                modified_config["fields"] = {}
                            modified_config["fields"]["time_window"] = time_window

                        # Для churn добавляем выбор временного окна
                        if config.get("template") == "churn":
                            churn_days = st.number_input(
                                "Временное окно оттока (дней)",
                                min_value=1,
                                max_value=365,
                                value=config.get("fields", {}).get("churn_days", 30),
                                key=f"churn_days_{metric.id}",
                                help="Сколько дней неактивности считается оттоком"
                            )
                            if "fields" not in modified_config:
                                modified_config["fields"] = {}
                            modified_config["fields"]["churn_days"] = churn_days

                        # Для retention добавляем выбор дня проверки
                        elif config.get("template") == "retention":
                            retention_day = st.number_input(
                                "День для проверки Retention (Day N)",
                                min_value=1,
                                max_value=365,
                                value=config.get("fields", {}).get("retention_day", 7),
                                key=f"retention_day_{metric.id}",
                                help="Какой день проверять: Day 1, Day 7, Day 30 и т.д."
                            )
                            if "fields" not in modified_config:
                                modified_config["fields"] = {}
                            modified_config["fields"]["retention_day"] = retention_day

                        result_data = calculate_metric(df, metric.metric_type, modified_config)

                        if isinstance(result_data, dict) and 'periods' in result_data:
                            if result_data.get('no_data') or result_data['count'] == 0:
                                if st.session_state.get(f"just_calculated_{metric.id}", False):
                                    st.toast("⚠️ Нет данных для отображения", icon="⚠️")
                                    st.session_state[f"just_calculated_{metric.id}"] = False
                            else:
                                if st.session_state.get(f"just_calculated_{metric.id}", False):
                                    st.toast("✓ Метрика рассчитана успешно", icon="✅")
                                    st.session_state[f"just_calculated_{metric.id}"] = False

                                display_period_metric_result(result_data, metric.name, metric.id, config.get("template"))

                        elif metric.metric_type == "sql":
                            if st.session_state.get(f"just_calculated_{metric.id}", False):
                                st.toast("✓ SQL-запрос выполнен успешно", icon="✅")
                                st.session_state[f"just_calculated_{metric.id}"] = False

                            display_sql_metric_result(config, df, metric.id)

                        else:
                            result = calculate_metric(df, metric.metric_type, config)
                            if st.session_state.get(f"just_calculated_{metric.id}", False):
                                st.toast(f"✓ Метрика рассчитана: {result}", icon="✅")
                                st.session_state[f"just_calculated_{metric.id}"] = False

                            display_simple_metric_result(result, metric.name)

                    except Exception as e:
                        st.toast(f"❌ Ошибка расчета метрики: {str(e)}", icon="❌")

            st.divider()


def show_create_metric_page():
    """Страница создания новой метрики"""

    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Назад", use_container_width=True):
            st.session_state["show_create_metric_page"] = False
            st.rerun()
    with col_title:
        st.title("Создать новую метрику")

    db = get_db()
    datasets = get_user_datasets(db, st.session_state.user['id'])
    db.close()

    if not datasets:
        st.warning("Сначала загрузите датасет в разделе 'Датасеты'")
        if st.button("Перейти к датасетам"):
            st.session_state.current_page = "Датасеты"
            st.session_state["show_create_metric_page"] = False
            st.rerun()
        return

    st.divider()

    creation_method = st.radio(
        "Способ создания метрики",
        options=["constructor", "sql"],
        format_func=lambda x: {
            "constructor": "🔧 Визуальный конструктор",
            "sql": "💻 SQL-запрос"
        }[x],
        horizontal=True,
        key="create_method"
    )

    st.divider()

    if creation_method == "sql":
        show_sql_metric_creator(datasets)
    else:
        show_constructor_metric_creator(datasets)
