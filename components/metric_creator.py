"""
Модуль для создания метрик (SQL и визуальный конструктор)
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_db, create_metric
from models import MetricCreate
from utils.metric_templates import METRIC_TEMPLATES
from utils.chart_helper import create_period_chart, format_periods_for_table


def show_sql_metric_creator(datasets):
    """Создание метрики через SQL-запрос"""

    metric_name = st.text_input("Название метрики", placeholder="Например: Средний чек по категориям", key="sql_metric_name")

    # Выбор датасета
    dataset_options = {ds.id: f"{ds.name} ({ds.rows_count:,} строк)" for ds in datasets}
    selected_dataset_id = st.selectbox(
        "Выберите датасет",
        options=list(dataset_options.keys()),
        format_func=lambda x: dataset_options[x],
        key="sql_dataset"
    )

    selected_dataset = next(ds for ds in datasets if ds.id == selected_dataset_id)

    # Показываем структуру датасета
    with st.expander("📋 Структура датасета (первые 5 строк)"):
        try:
            df_preview = pd.read_csv(selected_dataset.filepath, nrows=5)
            st.dataframe(df_preview, use_container_width=True)
            st.markdown(f"**Доступные колонки:** {', '.join(df_preview.columns.tolist())}")
        except Exception as e:
            st.error(f"Ошибка чтения датасета: {str(e)}")

    st.markdown("### SQL-запрос")
    st.info("💡 Используйте **SQLite синтаксис**. Таблица называется `df`. Пример: `SELECT AVG(amount) as avg_check FROM df WHERE status = 'completed'`")

    with st.expander("📖 Справка по SQLite"):
        st.markdown("""
        **Основные отличия от PostgreSQL/MySQL:**
        - Даты: `DATE(column)`, `DATETIME(column)`, `strftime('%Y-%m-%d', column)`
        - Текущая дата: `DATE('now')`, `DATETIME('now')`
        - Интервалы: `DATE('now', '-30 days')`, `DATE('now', '+1 month')`
        - Приведение типов: `CAST(column AS INTEGER)` вместо `column::integer`
        - Деление: `column * 1.0 / other` для получения float

        **Примеры:**
        ```sql
        -- Данные за последние 30 дней
        SELECT * FROM df WHERE DATE(order_date) >= DATE('now', '-30 days')

        -- Группировка по дням
        SELECT DATE(order_date) as date, SUM(amount) as total
        FROM df GROUP BY DATE(order_date)

        -- Форматирование даты
        SELECT strftime('%Y-%m', order_date) as month, COUNT(*) as orders
        FROM df GROUP BY month
        ```

        📄 [Полное руководство по SQL-метрикам](SQL_METRICS_GUIDE.md)
        """)

    sql_query = st.text_area(
        "Введите SQL-запрос (SQLite синтаксис)",
        placeholder="""SELECT
    DATE(order_date) as date,
    SUM(amount) as total_revenue,
    COUNT(DISTINCT user_id) as unique_users
FROM df
WHERE DATE(order_date) >= DATE('now', '-30 days')
GROUP BY DATE(order_date)
ORDER BY date DESC""",
        height=200,
        key="sql_query"
    )

    # Кнопка для тестирования запроса
    col_test, col_create = st.columns([1, 1])

    with col_test:
        if st.button("🧪 Протестировать запрос", use_container_width=True):
            if not sql_query:
                st.error("Введите SQL-запрос!")
            else:
                try:
                    import sqlite3

                    # Загружаем датасет
                    df = pd.read_csv(selected_dataset.filepath)

                    # Создаем временную БД в памяти
                    conn = sqlite3.connect(':memory:')
                    df.to_sql('df', conn, index=False, if_exists='replace')

                    # Выполняем запрос
                    result_df = pd.read_sql_query(sql_query, conn)
                    conn.close()

                    st.success("✓ Запрос выполнен успешно!")
                    st.dataframe(result_df, use_container_width=True)

                    # Если результат содержит числовые данные, пытаемся построить график
                    if len(result_df.columns) >= 2:
                        numeric_cols = result_df.select_dtypes(include=['number']).columns.tolist()
                        if len(numeric_cols) > 0:
                            # Берем первую колонку как ось X, первую числовую как Y
                            x_col = result_df.columns[0]
                            y_col = numeric_cols[0]

                            st.markdown("#### Визуализация")
                            chart_df = result_df[[x_col, y_col]].copy()

                            # Пытаемся преобразовать X в дату для правильной сортировки
                            try:
                                chart_df[x_col] = pd.to_datetime(chart_df[x_col])
                                chart_df = chart_df.sort_values(x_col)
                            except:
                                pass

                            # Используем Plotly для правильной сортировки
                            fig = px.line(chart_df, x=x_col, y=y_col, markers=True)
                            fig.update_layout(
                                xaxis_title=x_col,
                                yaxis_title=y_col,
                                hovermode='x unified'
                            )
                            st.plotly_chart(fig, use_container_width=True)

                except Exception as e:
                    st.error(f"Ошибка выполнения запроса: {str(e)}")

    description = st.text_area("Описание метрики (опционально)", placeholder="Краткое описание того, что измеряет эта метрика", key="sql_description")

    with col_create:
        if st.button("✅ Сохранить метрику в реестр", use_container_width=True, type="primary", key="sql_create_btn"):
            if not metric_name:
                st.error("Введите название метрики!")
            elif not sql_query:
                st.error("Введите SQL-запрос!")
            else:
                try:
                    db = get_db()
                    metric_data = MetricCreate(
                        name=metric_name,
                        description=description if description else None,
                        dataset_id=selected_dataset_id,
                        metric_type="sql",
                        config={"sql_query": sql_query}
                    )
                    create_metric(db, metric_data, st.session_state.user['id'])
                    db.close()

                    # Устанавливаем флаг для показа уведомления
                    st.session_state["metric_created"] = True
                    st.session_state["metric_created_name"] = metric_name

                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Ошибка создания метрики: {str(e)}")


def show_constructor_metric_creator(datasets):
    """Создание метрики через визуальный конструктор с готовыми шаблонами"""

    st.markdown("### Выберите тип метрики")

    # Отображаем карточки метрик в сетке
    cols = st.columns(3)

    for idx, (key, template) in enumerate(METRIC_TEMPLATES.items()):
        with cols[idx % 3]:
            if st.button(
                f"{template['icon']} {template['name']}",
                key=f"template_{key}",
                use_container_width=True,
                help=template['description']
            ):
                st.session_state["selected_metric_template"] = key

    # Если выбран шаблон, показываем форму настройки
    if "selected_metric_template" in st.session_state:
        selected_key = st.session_state["selected_metric_template"]
        template = METRIC_TEMPLATES[selected_key]

        st.divider()
        st.markdown(f"### {template['icon']} {template['name']}")
        st.info(f"**Описание:** {template['description']}\n\n**Формула:** `{template['formula']}`")

        # Название метрики
        metric_name = st.text_input(
            "Название метрики",
            value=template['name'],
            key=f"template_metric_name_{selected_key}"
        )

        # Выбор датасета
        dataset_options = {ds.id: f"{ds.name} ({ds.rows_count:,} строк)" for ds in datasets}
        selected_dataset_id = st.selectbox(
            "Выберите датасет",
            options=list(dataset_options.keys()),
            format_func=lambda x: dataset_options[x],
            key="template_dataset"
        )

        # Загружаем колонки датасета
        selected_dataset = next(ds for ds in datasets if ds.id == selected_dataset_id)
        try:
            df_preview = pd.read_csv(selected_dataset.filepath, nrows=5)
            columns = df_preview.columns.tolist()
        except Exception as e:
            st.error(f"Ошибка чтения датасета: {str(e)}")
            columns = []

        st.divider()
        st.markdown("#### Настройка полей")

        # Собираем значения полей
        field_values = {}
        for field_key, field_info in template['fields'].items():
            field_values[field_key] = st.selectbox(
                field_info['label'],
                options=columns,
                key=f"field_{field_key}"
            )

        # Для Conversion Rate добавляем выпадающий список с уникальными значениями статуса
        if selected_key == "conversion" and "status" in field_values:
            status_column = field_values["status"]
            try:
                df_full = pd.read_csv(selected_dataset.filepath)
                unique_statuses = sorted(df_full[status_column].dropna().unique().tolist())
                field_values["success_value"] = st.selectbox(
                    "Значение успешной конверсии",
                    options=unique_statuses,
                    key="conversion_success_value"
                )
            except Exception as e:
                st.error(f"Ошибка загрузки уникальных значений: {str(e)}")
                field_values["success_value"] = st.text_input(
                    "Значение успешной конверсии",
                    placeholder="Введите значение вручную",
                    key="conversion_success_value_manual"
                )

        # Для всех остальных метрик добавляем опциональное поле даты для построения графика
        if selected_key in ["revenue", "aov", "arpu", "conversion", "gmv", "ltv", "cac"]:
            st.markdown("#### Временное измерение (опционально)")
            add_time_dimension = st.checkbox("Показать динамику по периодам", value=True, key=f"add_time_{selected_key}")

            if add_time_dimension:
                # Добавляем выбор поля с датой
                date_field = st.selectbox(
                    "Поле с датой",
                    options=columns,
                    key=f"date_field_{selected_key}"
                )
                field_values["date_field"] = date_field

        # Для Retention Rate добавляем выпадающий список с уникальными значениями нового пользователя
        if selected_key == "retention" and "new_user_field" in field_values:
            new_user_field_column = field_values["new_user_field"]
            try:
                df_full = pd.read_csv(selected_dataset.filepath)
                unique_values = sorted(df_full[new_user_field_column].dropna().unique().tolist())
                field_values["new_user_value"] = st.selectbox(
                    "Значение для нового пользователя",
                    options=unique_values,
                    key="retention_new_user_value"
                )
            except Exception as e:
                st.error(f"Ошибка загрузки уникальных значений: {str(e)}")
                field_values["new_user_value"] = st.text_input(
                    "Значение для нового пользователя",
                    placeholder="Введите значение вручную",
                    key="retention_new_user_value_manual"
                )

        # Для Retention Rate добавляем параметр retention_day (вместо retention_days)
        if selected_key == "retention":
            st.markdown("#### Настройки удержания")
            retention_day = st.number_input(
                "День для проверки Retention (Day N)",
                min_value=1,
                max_value=365,
                value=7,
                help="Какой день проверять: Day 1, Day 7, Day 30 и т.д.",
                key="retention_day"
            )
            field_values["retention_day"] = retention_day

        # Для Churn Rate добавляем параметр порога неактивности
        if selected_key == "churn":
            st.markdown("#### Настройки оттока")
            churn_days = st.number_input(
                "Порог неактивности (дней)",
                min_value=1,
                max_value=365,
                value=30,
                help="Сколько дней неактивности считается оттоком",
                key="churn_days"
            )
            field_values["churn_days"] = churn_days

        description = st.text_area(
            "Описание метрики (опционально)",
            placeholder="Дополнительные детали о метрике",
            key="template_description"
        )

        st.divider()

        # Кнопка предпросмотра
        col_preview, col_cancel = st.columns([1, 1])

        with col_preview:
            if st.button("🔍 Предпросмотр метрики", use_container_width=True, type="secondary"):
                st.session_state[f"preview_metric_{selected_key}"] = True

        with col_cancel:
            if st.button("← Выбрать другую метрику", use_container_width=True):
                del st.session_state["selected_metric_template"]
                if f"preview_metric_{selected_key}" in st.session_state:
                    del st.session_state[f"preview_metric_{selected_key}"]
                st.rerun()

        # Показываем предпросмотр метрики
        if st.session_state.get(f"preview_metric_{selected_key}", False):
            st.divider()
            st.markdown("### 📊 Предпросмотр метрики")

            try:
                from components.metric_calculator import calculate_metric

                # Загружаем данные
                df_full = pd.read_csv(selected_dataset.filepath)

                # Формируем конфигурацию для предпросмотра
                preview_config = {
                    "template": selected_key,
                    "fields": field_values
                }

                # Добавляем селектор группировки для метрик с временным измерением
                # Но НЕ для churn, retention, dau, wau, mau - у них группировка встроена
                has_date_field = False
                if field_values.get("date_field") and selected_key not in ["churn", "retention", "dau", "wau", "mau"]:
                    has_date_field = True

                if has_date_field:
                    preview_time_window = st.selectbox(
                        "Группировка для предпросмотра",
                        options=["day", "week", "month"],
                        format_func=lambda x: {"day": "По дням", "week": "По неделям", "month": "По месяцам"}[x],
                        key=f"preview_time_window_{selected_key}"
                    )
                    preview_config["fields"]["time_window"] = preview_time_window
                # Для churn и retention добавляем time_window по умолчанию
                elif selected_key in ["churn", "retention"]:
                    preview_config["fields"]["time_window"] = "day"
                # Для DAU добавляем time_window = day
                elif selected_key == "dau":
                    preview_config["fields"]["time_window"] = "day"

                # Рассчитываем метрику
                result_data = calculate_metric(df_full, "template", preview_config)

                # Отображаем результат
                if isinstance(result_data, dict) and 'periods' in result_data:
                    if result_data.get('no_data') or result_data['count'] == 0:
                        st.warning("⚠️ Нет данных для отображения")
                    else:
                        # Показываем основные показатели (кроме Conversion Rate)
                        if selected_key != "conversion":
                            col_avg, col_sum, col_periods = st.columns(3)
                            with col_avg:
                                st.metric("Среднее за период", f"{result_data['mean']:,.2f}")
                            with col_sum:
                                st.metric("Сумма за весь период", f"{result_data['total']:,.2f}")
                            with col_periods:
                                st.metric("Количество периодов", result_data['count'])

                        # График
                        st.markdown("#### Динамика по периодам")

                        fig = create_period_chart(result_data['periods'], result_data['values'])
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Нет данных для отображения")

                        # Таблица с данными
                        with st.expander("Показать детальную таблицу"):
                            formatted_periods = format_periods_for_table(result_data['periods'])
                            display_df = pd.DataFrame({
                                'Период': formatted_periods,
                                'Значение': [f"{v:,.2f}" for v in result_data['values']]
                            })
                            st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    # Простое значение
                    st.success(f"Результат: **{result_data}**")
                    st.markdown("---")
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.markdown(f"<div style='text-align: center; padding: 40px; background-color: #f0f2f6; border-radius: 10px;'><h1 style='font-size: 48px; margin: 0;'>{result_data}</h1><p style='color: #666; margin-top: 10px;'>{metric_name}</p></div>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Ошибка расчета метрики: {str(e)}")

            st.divider()

            # Кнопка сохранения после предпросмотра
            if st.button("✅ Сохранить метрику в реестр", use_container_width=True, type="primary", key="template_save_btn"):
                if not metric_name:
                    st.error("Введите название метрики!")
                else:
                    try:
                        # Формируем конфигурацию в зависимости от типа метрики
                        config = {
                            "template": selected_key,
                            "fields": field_values
                        }

                        db = get_db()
                        metric_data = MetricCreate(
                            name=metric_name,
                            description=description if description else template['description'],
                            dataset_id=selected_dataset_id,
                            metric_type="template",
                            config=config
                        )
                        create_metric(db, metric_data, st.session_state.user['id'])
                        db.close()

                        # Устанавливаем флаг для показа уведомления
                        st.session_state["metric_created"] = True
                        st.session_state["metric_created_name"] = metric_name
                        st.session_state["show_create_metric_page"] = False
                        del st.session_state["selected_metric_template"]
                        if f"preview_metric_{selected_key}" in st.session_state:
                            del st.session_state[f"preview_metric_{selected_key}"]

                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Ошибка создания метрики: {str(e)}")
