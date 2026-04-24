"""
Компонент для отображения результатов A/B эксперимента
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict


def display_results_table(results: Dict[str, Dict], metric_name: str):
    """
    Отображение таблицы с результатами эксперимента

    Args:
        results: Словарь с результатами для каждой группы
        metric_name: Название метрики
    """
    st.markdown("### 📊 Сравнение групп")

    # Подготовка данных для таблицы
    table_data = []
    for group_name, result in sorted(results.items(), key=lambda x: (x[0] != 'control', x[0])):
        # Пропускаем служебные ключи
        if group_name.startswith('_'):
            continue

        row = {
            'Группа': f"{group_name.capitalize()} {'(контроль)' if result['is_control'] else '(тест)'}",
            'Размер выборки': f"{result['sample_size']:,}",
            f'{metric_name}': f"{result['metric_value']:.2f}",
            'Std Dev': f"{result['std_dev']:.2f}",
            'Разница с контролем': f"{result.get('difference_percent', 0):+.2f}%" if not result['is_control'] else '-',
            'p-value': f"{result.get('p_value', 0):.4f}" if result.get('p_value') is not None else '-',
            'Значимость': '✅ Да' if result.get('is_significant') else '❌ Нет' if result.get('p_value') is not None else '-'
        }
        table_data.append(row)

    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True, hide_index=True)

    # Предупреждения
    warnings = []
    for group_name, result in results.items():
        # Пропускаем служебные ключи
        if group_name.startswith('_'):
            continue
        if result.get('warning'):
            warnings.append(f"⚠️ Группа {group_name}: {result['warning']}")

    if warnings:
        st.warning('\n\n'.join(warnings))


def display_bar_chart(results: Dict[str, Dict], metric_name: str):
    """
    Отображение столбчатой диаграммы сравнения групп

    Args:
        results: Словарь с результатами для каждой группы
        metric_name: Название метрики
    """
    st.markdown("### 📊 Столбчатая диаграмма")

    # Подготовка данных
    groups = []
    values = []
    errors = []
    colors = []

    for group_name, result in sorted(results.items(), key=lambda x: (x[0] != 'control', x[0])):
        # Пропускаем служебные ключи
        if group_name.startswith('_'):
            continue

        groups.append(group_name.capitalize())
        values.append(result['metric_value'])

        # Ошибка = половина доверительного интервала
        error = (result['confidence_interval_upper'] - result['confidence_interval_lower']) / 2
        errors.append(error)

        # Цвет: контрольная группа - синий, остальные - зеленый/красный в зависимости от значимости
        if result['is_control']:
            colors.append('#1f77b4')  # синий
        elif result.get('is_significant'):
            if result.get('difference_percent', 0) > 0:
                colors.append('#2ca02c')  # зеленый (улучшение)
            else:
                colors.append('#d62728')  # красный (ухудшение)
        else:
            colors.append('#ff7f0e')  # оранжевый (не значимо)

    # Создание графика
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=groups,
        y=values,
        error_y=dict(
            type='data',
            array=errors,
            visible=True
        ),
        marker_color=colors,
        text=[f"{v:.2f}" for v in values],
        textposition='outside'
    ))

    fig.update_layout(
        title=f'Сравнение групп по метрике {metric_name}',
        xaxis_title='Группа',
        yaxis_title=metric_name,
        showlegend=False,
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)


def display_time_series_chart(results: Dict[str, Dict], metric_name: str):
    """
    Отображение графика динамики метрики по времени

    Args:
        results: Словарь с результатами для каждой группы
        metric_name: Название метрики
    """
    st.markdown("### 📈 Динамика метрики по времени")

    # Проверяем, есть ли временные ряды
    has_time_series = any(
        result.get('time_series')
        for key, result in results.items()
        if not key.startswith('_') and isinstance(result, dict)
    )

    if not has_time_series:
        st.info("Временные ряды недоступны для этой метрики")
        return

    # Создание графика
    fig = go.Figure()

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

    for idx, (group_name, result) in enumerate(sorted(results.items(), key=lambda x: (x[0] != 'control', x[0]))):
        # Пропускаем служебные ключи
        if group_name.startswith('_'):
            continue

        time_series = result.get('time_series')
        if not time_series:
            continue

        periods = time_series.get('periods', [])
        values = time_series.get('values', [])

        if not periods or not values:
            continue

        fig.add_trace(go.Scatter(
            x=periods,
            y=values,
            mode='lines+markers',
            name=f"Группа {group_name.capitalize()}",
            line=dict(color=colors[idx % len(colors)], width=2),
            marker=dict(size=6)
        ))

    fig.update_layout(
        title=f'Динамика {metric_name} по группам',
        xaxis_title='Период',
        yaxis_title=metric_name,
        hovermode='x unified',
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig, use_container_width=True)


def display_statistical_summary(results: Dict[str, Dict], test_type: str):
    """
    Отображение статистической сводки

    Args:
        results: Словарь с результатами для каждой группы
        test_type: Тип статистического теста
    """
    st.markdown("### 📐 Статистическая сводка")

    # Информация о тесте
    test_descriptions = {
        't-test': "t-тест Стьюдента для сравнения средних значений непрерывных метрик",
        'z-test': "z-тест для сравнения пропорций (конверсий) с большими выборками",
        'chi-square': "Хи-квадрат тест для категориальных данных"
    }

    st.markdown(f"**Используемый тест:** {test_type}")
    st.markdown(f"*{test_descriptions.get(test_type, 'Неизвестный тип теста')}*")

    st.markdown("---")

    # Интерпретация результатов
    control_group = next((g for g, r in results.items() if not g.startswith('_') and isinstance(r, dict) and r.get('is_control')), None)

    if not control_group:
        st.warning("Контрольная группа не определена")
        return

    st.markdown("**Интерпретация результатов:**")

    # Проверяем, неполный ли эксперимент
    if results.get('_experiment_incomplete'):
        st.warning(results.get('_incomplete_warning', 'Эксперимент еще не завершен'))
        st.info("📊 Показаны промежуточные результаты на основе доступных данных. Статистические тесты будут доступны после загрузки полных данных.")
        return

    for group_name, result in sorted(results.items(), key=lambda x: (x[0] != 'control', x[0])):
        # Пропускаем служебные ключи
        if group_name.startswith('_'):
            continue

        if result['is_control']:
            continue

        p_value = result.get('p_value')
        is_significant = result.get('is_significant', False)
        difference = result.get('difference_percent', 0)

        if p_value is None:
            continue

        # Формируем текст интерпретации
        if is_significant:
            if difference > 0:
                interpretation = f"✅ Группа **{group_name.capitalize()}** показала **статистически значимое улучшение** на **{difference:+.2f}%** по сравнению с контрольной группой (p-value = {p_value:.4f} < 0.05)"
            else:
                interpretation = f"⚠️ Группа **{group_name.capitalize()}** показала **статистически значимое ухудшение** на **{difference:+.2f}%** по сравнению с контрольной группой (p-value = {p_value:.4f} < 0.05)"
        else:
            interpretation = f"❌ Группа **{group_name.capitalize()}** показала изменение на **{difference:+.2f}%**, но результат **не является статистически значимым** (p-value = {p_value:.4f} >= 0.05)"

        st.markdown(interpretation)

    st.markdown("---")
    st.info("💡 **Примечание:** Результат считается статистически значимым при p-value < 0.05 (уровень значимости 95%)")


def display_experiment_results(results: Dict[str, Dict], metric_name: str, test_type: str):
    """
    Полное отображение результатов эксперимента

    Args:
        results: Словарь с результатами для каждой группы
        metric_name: Название метрики
        test_type: Тип статистического теста
    """
    # Таблица сравнения
    display_results_table(results, metric_name)

    st.divider()

    # Столбчатая диаграмма
    display_bar_chart(results, metric_name)

    st.divider()

    # График динамики
    display_time_series_chart(results, metric_name)

    st.divider()

    # Статистическая сводка
    display_statistical_summary(results, test_type)
