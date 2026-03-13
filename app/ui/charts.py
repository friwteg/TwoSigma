"""
Визуализация данных для A/B тестов
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple


def create_conversion_bar_chart(
    control_data: Dict[str, Any],
    treatment_data: Dict[str, Any],
    title: str = "Конверсия по группам"
) -> go.Figure:
    """
    Столбчатая диаграмма конверсии с доверительными интервалами
    """
    fig = make_subplots(rows=1, cols=1)
    
    # Данные
    groups = ['Control', 'Treatment']
    conversions = [
        control_data['conversion_rate'],
        treatment_data['conversion_rate']
    ]
    ci_lower = [
        control_data['confidence_interval'][0],
        treatment_data['confidence_interval'][0]
    ]
    ci_upper = [
        control_data['confidence_interval'][1],
        treatment_data['confidence_interval'][1]
    ]
    
    # Столбцы
    fig.add_trace(go.Bar(
        x=groups,
        y=conversions,
        name='Конверсия',
        marker_color=['#1f77b4', '#2ca02c'],
        error_y=dict(
            type='data',
            symmetric=False,
            array=[ci_upper[i] - conversions[i] for i in range(2)],
            arrayminus=[conversions[i] - ci_lower[i] for i in range(2)],
            visible=True
        )
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Группа",
        yaxis_title="Конверсия",
        showlegend=False,
        template='plotly_white'
    )
    
    return fig


def create_funnel_chart(
    stages: List[str],
    values: List[int],
    title: str = "Воронка конверсии"
) -> go.Figure:
    """
    Воронка конверсии
    """
    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textposition="inside",
        textinfo="value+percent initial",
        marker={
            "color": ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728", "#9467bd"],
            "line": {"width": [2, 2, 2, 2, 2], "color": ["white", "white", "white", "white", "white"]}
        }
    ))
    
    fig.update_layout(
        title=title,
        template='plotly_white'
    )
    
    return fig


def create_time_series_chart(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    group_column: Optional[str] = None,
    title: str = "Динамика метрики"
) -> go.Figure:
    """
    График временного ряда
    """
    if group_column:
        fig = px.line(
            data,
            x=x_column,
            y=y_column,
            color=group_column,
            title=title,
            template='plotly_white',
            color_discrete_sequence=['#1f77b4', '#2ca02c']
        )
    else:
        fig = px.line(
            data,
            x=x_column,
            y=y_column,
            title=title,
            template='plotly_white'
        )
    
    fig.update_layout(
        xaxis_title=x_column,
        yaxis_title=y_column
    )
    
    return fig


def create_distribution_chart(
    control_values: np.ndarray,
    treatment_values: np.ndarray,
    title: str = "Распределение метрики"
) -> go.Figure:
    """
    Гистограмма распределения с KDE
    """
    fig = make_subplots(rows=1, cols=1)
    
    # Гистограммы
    fig.add_trace(go.Histogram(
        x=control_values,
        name='Control',
        opacity=0.6,
        marker_color='#1f77b4',
        nbinsx=30
    ))
    
    fig.add_trace(go.Histogram(
        x=treatment_values,
        name='Treatment',
        opacity=0.6,
        marker_color='#2ca02c',
        nbinsx=30
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Значение",
        yaxis_title="Частота",
        barmode='overlay',
        template='plotly_white'
    )
    
    return fig


def create_lift_chart(
    lift: float,
    confidence_interval: Tuple[float, float],
    is_significant: bool,
    title: str = "Эффект (Lift)"
) -> go.Figure:
    """
    График эффекта (lift) с доверительным интервалом
    """
    lift_percent = lift * 100
    ci_lower_percent = confidence_interval[0] * 100
    ci_upper_percent = confidence_interval[1] * 100
    
    # Цвет в зависимости от значимости
    color = '#2ca02c' if is_significant else '#d62728'
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=[0],
        y=[lift_percent],
        mode='markers+text',
        marker=dict(size=20, color=color),
        text=[f"{lift_percent:+.2f}%"],
        textposition="top center",
        textfont=dict(size=16, color=color)
    ))
    
    # Доверительный интервал
    fig.add_trace(go.Scatter(
        x=[0, 0],
        y=[ci_lower_percent, ci_upper_percent],
        mode='lines',
        line=dict(color=color, width=3),
        name='95% CI'
    ))
    
    # Нулевая линия
    fig.add_shape(
        type="line",
        x0=-0.5, y0=0, x1=0.5, y1=0,
        line=dict(color="gray", dash="dash")
    )
    
    fig.update_layout(
        title=title,
        xaxis=dict(showticklabels=False, range=[-0.5, 0.5]),
        yaxis_title="Lift (%)",
        showlegend=True,
        template='plotly_white',
        height=300
    )
    
    return fig


def create_experiment_summary_chart(
    experiment_results: List[Dict[str, Any]],
    title: str = "Результаты эксперимента"
) -> go.Figure:
    """
    Сводная диаграмма результатов эксперимента
    """
    groups = [r['group_name'] for r in experiment_results]
    metrics = [r['metric_value'] for r in experiment_results]
    sample_sizes = [r['sample_size'] for r in experiment_results]
    
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=('Конверсия по группам', 'Размер выборки')
    )
    
    # Конверсия
    fig.add_trace(go.Bar(
        x=groups,
        y=metrics,
        name='Конверсия',
        marker_color=['#1f77b4'] + ['#2ca02c'] * (len(groups) - 1)
    ), row=1, col=1)
    
    # Выборка
    fig.add_trace(go.Bar(
        x=groups,
        y=sample_sizes,
        name='Выборка',
        marker_color=['#ff7f0e'] * len(groups)
    ), row=1, col=2)
    
    fig.update_layout(
        title=title,
        showlegend=False,
        template='plotly_white',
        height=400
    )
    
    return fig


def create_power_analysis_chart(
    sample_sizes: List[int],
    effect_sizes: List[float],
    alpha: float = 0.05
) -> go.Figure:
    """
    График статистической мощности
    """
    from scipy import stats
    
    powers = []
    for n in sample_sizes:
        for effect in effect_sizes:
            ncp = effect * np.sqrt(n / 2)
            z_alpha = stats.norm.ppf(1 - alpha/2)
            power = 1 - stats.norm.cdf(z_alpha - ncp) + stats.norm.cdf(-z_alpha - ncp)
            powers.append({
                'n': n,
                'effect': effect,
                'power': power
            })
    
    df = pd.DataFrame(powers)
    
    fig = px.line(
        df,
        x='n',
        y='power',
        color='effect',
        title='Статистическая мощность теста',
        labels={'n': 'Размер выборки', 'power': 'Мощность', 'effect': 'Размер эффекта'},
        template='plotly_white'
    )
    
    # Линия 80% мощности
    fig.add_hline(y=0.8, line_dash="dash", line_color="gray", annotation_text="80% мощность")
    
    return fig


def create_heatmap_chart(
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    value_column: str,
    title: str = "Тепловая карта"
) -> go.Figure:
    """
    Тепловая карта для сегментного анализа
    """
    pivot = data.pivot(index=y_column, columns=x_column, values=value_column)
    
    fig = px.imshow(
        pivot,
        labels=dict(x=x_column, y=y_column, color=value_column),
        title=title,
        color_continuous_scale='RdYlGn'
    )
    
    fig.update_layout(template='plotly_white')
    
    return fig
