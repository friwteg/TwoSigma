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
        # Сбрасываем флаг после показа
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

            # Определяем тип метрики для отображения
            # Защита: config может быть строкой (например, после неверной записи в БД)
            config = metric.config if isinstance(metric.config, dict) else {}

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
                    # Кнопка для разворачивания/сворачивания
                    is_expanded = st.session_state.get(f"show_metric_{metric.id}", False)
                    button_label = "🔼 Скрыть" if is_expanded else "📊 Рассчитать"

                    if st.button(button_label, key=f"calc_{metric.id}", use_container_width=True):
                        if is_expanded:
                            # Сворачиваем
                            st.session_state[f"show_metric_{metric.id}"] = False
                        else:
                            # Разворачиваем
                            st.session_state[f"show_metric_{metric.id}"] = True
                            st.session_state[f"just_calculated_{metric.id}"] = True

                with col_delete:
                    # Кнопка удаления с подтверждением
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
                                # Очищаем все флаги
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
                # Используем контейнер с ключом для стабильности
                metric_container = st.container()

                with metric_container:
                    try:
                        df = pd.read_csv(dataset.filepath)

                        # Для метрик с временным измерением добавляем выбор группировки
                        modified_config = config.copy()

                        # Проверяем, есть ли у метрики поле даты (для графиков)
                        has_date_field = False
                        if metric.metric_type == "template":
                            fields = config.get("fields", {})
                            template_type = config.get("template")

                            # Для всех шаблонных метрик проверяем наличие date_field
                            if fields.get("date_field"):
                                has_date_field = True
                            # Для DAU, WAU, MAU, Churn, Retention всегда есть дата
                            elif template_type in ["dau", "wau", "mau", "churn", "retention"]:
                                has_date_field = True

                        # Если есть временное измерение, показываем селектор группировки
                        # НО не для DAU, WAU, MAU - у них группировка фиксированная
                        time_window = "day"  # Значение по умолчанию
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

                        # Обновляем конфигурацию с выбранной группировкой
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

                        # Вызываем расчет метрики с модифицированной конфигурацией
                        result_data = calculate_metric(df, metric.metric_type, modified_config)

                        # Проверяем, что результат содержит временные данные (для графиков)
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
                            result = calculate_metric(df, metric.metric_type, metric.config)
                            if st.session_state.get(f"just_calculated_{metric.id}", False):
                                st.toast(f"✓ Метрика рассчитана: {result}", icon="✅")
                                st.session_state[f"just_calculated_{metric.id}"] = False

                            display_simple_metric_result(result, metric.name)

                    except Exception as e:
                        st.toast(f"❌ Ошибка расчета метрики: {str(e)}", icon="❌")

            st.divider()

    # --- Плавающая кнопка сохранения в PDF (внизу справа) ---
    st.markdown("""
        <style>
        .pdf-btn {
            position: fixed;
            bottom: 28px;
            right: 28px;
            z-index: 9999;
            background-color: #ff4b4b;
            color: white;
            border: none;
            border-radius: 50px;
            padding: 14px 24px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 16px rgba(0,0,0,0.22);
            display: flex;
            align-items: center;
            gap: 8px;
            transition: background 0.2s;
        }
        .pdf-btn:hover {
            background-color: #cc3a3a;
        }
        @media print {
            section[data-testid="stSidebar"],
            .pdf-btn,
            [data-testid="stToolbar"],
            [data-testid="stDecoration"],
            [data-testid="stStatusWidget"] { display: none !important; }
            .main .block-container { padding: 0 !important; max-width: 100% !important; }
        }
        </style>
        <button class="pdf-btn" onclick="window.print()">
            📄 Сохранить PDF
        </button>
    """, unsafe_allow_html=True)


def show_create_metric_page():
    """Страница создания новой метрики"""

    # Заголовок с кнопкой возврата
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Назад", use_container_width=True):
            st.session_state["show_create_metric_page"] = False
            st.rerun()
    with col_title:
        st.title("Создать новую метрику")

    # Получаем датасеты пользователя
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

    # Выбор способа создания метрики
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
