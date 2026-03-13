"""
Дашборды для A/B тестов
"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Any
from app.ui.charts import (
    create_conversion_bar_chart,
    create_lift_chart,
    create_experiment_summary_chart,
    create_time_series_chart
)


def render_experiment_card(experiment: Dict[str, Any]) -> None:
    """
    Карточка эксперимента для дашборда
    """
    status_emoji = {
        'draft': '📝',
        'running': '🔴',
        'paused': '⏸️',
        'completed': '✅',
        'stopped': '⏹️'
    }
    
    status_labels = {
        'draft': 'Черновик',
        'running': 'Активен',
        'paused': 'На паузе',
        'completed': 'Завершён',
        'stopped': 'Остановлен'
    }
    
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"### {status_emoji.get(experiment['status'], '🧪')} {experiment['name']}")
            if experiment.get('description'):
                st.markdown(f"_{experiment['description']}_")
        
        with col2:
            st.metric(
                label="Статус",
                value=status_labels.get(experiment['status'], experiment['status'])
            )
        
        with col3:
            st.metric(
                label="Длительность",
                value=f"{experiment.get('planned_duration_days', 14)} дн."
            )


def render_metrics_summary(metrics_data: Dict[str, Any]) -> None:
    """
    Сводка по метрикам
    """
    st.markdown("### 📊 Ключевые метрики")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Конверсия (Control)",
            value=f"{metrics_data.get('control_conversion', 0):.2%}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="Конверсия (Treatment)",
            value=f"{metrics_data.get('treatment_conversion', 0):.2%}",
            delta=f"{metrics_data.get('relative_diff', 0):+.2%}"
        )
    
    with col3:
        st.metric(
            label="P-value",
            value=f"{metrics_data.get('p_value', 1):.4f}",
            delta="Значимо" if metrics_data.get('is_significant') else "Не значимо",
            delta_color="inverse" if metrics_data.get('is_significant') else "normal"
        )
    
    with col4:
        st.metric(
            label="Размер выборки",
            value=f"{metrics_data.get('sample_size', 0):,}"
        )


def render_experiment_results(results: Dict[str, Any]) -> None:
    """
    Визуализация результатов эксперимента
    """
    st.markdown("### 📈 Результаты")
    
    # Основной график
    if 'control' in results and 'treatment' in results:
        fig = create_conversion_bar_chart(
            results['control'],
            results['treatment'],
            title="Сравнение конверсии"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Lift chart
    if 'statistics' in results:
        stats = results['statistics']
        lift = stats.get('relative_difference', 0)
        ci = (
            stats.get('absolute_difference', 0) - 0.02,
            stats.get('absolute_difference', 0) + 0.02
        )
        
        fig_lift = create_lift_chart(
            lift=lift,
            confidence_interval=ci,
            is_significant=stats.get('is_significant', False),
            title="Эффект от изменения"
        )
        st.plotly_chart(fig_lift, use_container_width=True)


def render_experiments_list(experiments: List[Dict[str, Any]]) -> None:
    """
    Список всех экспериментов
    """
    st.markdown("### 🧪 Все эксперименты")
    
    if not experiments:
        st.info("Нет созданных экспериментов")
        return
    
    # Таблица экспериментов
    df_data = []
    for exp in experiments:
        df_data.append({
            'ID': exp.get('id', 'N/A'),
            'Название': exp.get('name', 'Без названия'),
            'Статус': exp.get('status', 'unknown'),
            'Создан': exp.get('created_at', 'N/A'),
            'Длительность': f"{exp.get('planned_duration_days', 14)} дн."
        })
    
    df = pd.DataFrame(df_data)
    
    # Стилизация статусов
    def style_status(status):
        colors = {
            'draft': 'background-color: #f0f0f0',
            'running': 'background-color: #ffcccc',
            'paused': 'background-color: #fff3cd',
            'completed': 'background-color: #d4edda',
            'stopped': 'background-color: #f8d7da'
        }
        return colors.get(status, '')
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


def render_dashboard_summary(
    total_experiments: int,
    active_experiments: int,
    completed_experiments: int,
    significant_results: int
) -> None:
    """
    Сводный дашборд
    """
    st.markdown("## 📊 Обзор экспериментов")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Всего экспериментов",
            value=total_experiments
        )
    
    with col2:
        st.metric(
            label="Активные",
            value=active_experiments,
            delta=f"{active_experiments}/{total_experiments}" if total_experiments > 0 else None
        )
    
    with col3:
        st.metric(
            label="Завершённые",
            value=completed_experiments
        )
    
    with col4:
        st.metric(
            label="Значимые результаты",
            value=significant_results,
            delta=f"{significant_results/completed_experiments:.0%}" if completed_experiments > 0 else None
        )


def render_time_series(data: pd.DataFrame, metric: str) -> None:
    """
    График временного ряда для метрики
    """
    st.markdown(f"### 📈 Динамика: {metric}")
    
    if data.empty:
        st.info("Нет данных для отображения")
        return
    
    fig = create_time_series_chart(
        data=data,
        x_column='date',
        y_column=metric,
        group_column='group' if 'group' in data.columns else None,
        title=f"Динамика метрики '{metric}'"
    )
    
    st.plotly_chart(fig, use_container_width=True)
