"""
Вспомогательные функции для отображения результатов метрик
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.chart_helper import create_period_chart, format_periods_for_table


def display_period_metric_result(result_data: dict, metric_name: str, metric_id: int = None, metric_type: str = None) -> None:
    """
    Отображает результат метрики с временными периодами

    Args:
        result_data: Словарь с ключами periods, values, mean, total, count
        metric_name: Название метрики
        metric_id: ID метрики для уникальных ключей
        metric_type: Тип метрики (для определения, показывать ли агрегаты)
    """
    if result_data.get('no_data') or result_data['count'] == 0:
        st.warning("⚠️ Нет данных для отображения")
        return

    # Для Conversion Rate показываем только график, без агрегатов
    if metric_type != "conversion":
        # Основные показатели
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


def display_sql_metric_result(metric_config: dict, df: pd.DataFrame, metric_id: int = None) -> None:
    """
    Отображает результат SQL-метрики

    Args:
        metric_config: Конфигурация метрики с SQL-запросом
        df: Датафрейм с данными
        metric_id: ID метрики для уникальных ключей
    """
    import sqlite3

    try:
        conn = sqlite3.connect(':memory:')
        df.to_sql('df', conn, index=False, if_exists='replace')
        result_df = pd.read_sql_query(metric_config["sql_query"], conn)
        conn.close()

        # Если результат содержит числовые данные, пытаемся построить график
        if len(result_df.columns) >= 2:
            numeric_cols = result_df.select_dtypes(include=['number']).columns.tolist()
            if len(numeric_cols) > 0:
                # Берем первую колонку как ось X
                x_col = result_df.columns[0]

                # Показываем основные показатели для первой числовой колонки
                first_numeric = numeric_cols[0]
                values = result_df[first_numeric].tolist()

                if values:
                    col_avg, col_sum, col_periods = st.columns(3)
                    with col_avg:
                        st.metric("Среднее за период", f"{sum(values) / len(values):,.2f}")
                    with col_sum:
                        st.metric("Сумма за весь период", f"{sum(values):,.2f}")
                    with col_periods:
                        st.metric("Количество периодов", len(values))

                st.markdown("#### Динамика по периодам")

                # Строим график для каждой числовой колонки
                for y_col in numeric_cols:
                    chart_df = result_df[[x_col, y_col]].copy()

                    # Пытаемся преобразовать X в дату для правильной сортировки
                    try:
                        chart_df[x_col] = pd.to_datetime(chart_df[x_col])
                        chart_df = chart_df.sort_values(x_col)
                    except:
                        pass

                    # Используем Plotly для линейного графика
                    fig = px.line(chart_df, x=x_col, y=y_col, markers=True)
                    fig.update_layout(
                        xaxis_title=x_col,
                        yaxis_title=y_col,
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, use_container_width=True)

        # Показываем результат в expander, как и для шаблонных метрик
        with st.expander("Показать детальную таблицу"):
            st.dataframe(result_df, use_container_width=True)
    except Exception as e:
        st.error(f"Ошибка выполнения SQL: {str(e)}")


def display_simple_metric_result(result: str, metric_name: str) -> None:
    """
    Отображает результат простой метрики (одно значение)

    Args:
        result: Результат расчета метрики
        metric_name: Название метрики
    """
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"<div style='text-align: center; padding: 40px; background-color: #f0f2f6; "
            f"border-radius: 10px;'><h1 style='font-size: 48px; margin: 0;'>{result}</h1>"
            f"<p style='color: #666; margin-top: 10px;'>{metric_name}</p></div>",
            unsafe_allow_html=True
        )

