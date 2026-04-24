"""
Вспомогательные функции для построения графиков
"""
import pandas as pd
import plotly.graph_objects as go


def create_period_chart(periods_list, values_list):
    """
    Создает график временного ряда с правильной обработкой разных типов периодов

    Args:
        periods_list: список периодов (pd.Period, pd.Timestamp, datetime.date и т.д.)
        values_list: список значений

    Returns:
        plotly.graph_objects.Figure: готовый график
    """
    if len(periods_list) == 0:
        return None

    # Форматируем периоды для отображения
    periods_str = format_periods_for_table(periods_list)

    # Создаем график с использованием graph_objects для полного контроля
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=list(range(len(periods_str))),
        y=values_list,
        mode='lines+markers',
        name='Значение',
        hovertemplate='<b>%{text}</b><br>Значение: %{y:,.2f}<extra></extra>',
        text=periods_str
    ))

    # Настраиваем оси
    fig.update_xaxes(
        tickmode='array',
        tickvals=list(range(len(periods_str))),
        ticktext=periods_str,
        title="Период"
    )

    fig.update_yaxes(title="Значение")

    fig.update_layout(
        hovermode='x unified',
        showlegend=False
    )

    return fig


def format_periods_for_table(periods_list):
    """
    Форматирует периоды для отображения в таблице

    Args:
        periods_list: список периодов

    Returns:
        list: список отформатированных строк
    """
    formatted_periods = []

    for p in periods_list:
        if isinstance(p, pd.Period):
            if p.freq == 'W':
                formatted_periods.append(f"{p.start_time.strftime('%d.%m')} - {p.end_time.strftime('%d.%m')}")
            elif p.freq == 'M':
                formatted_periods.append(p.strftime('%m.%Y'))
            else:
                formatted_periods.append(str(p))
        elif isinstance(p, (pd.Timestamp, pd.DatetimeIndex)):
            formatted_periods.append(p.strftime('%d.%m.%Y'))
        elif hasattr(p, 'strftime'):
            formatted_periods.append(p.strftime('%d.%m.%Y'))
        else:
            formatted_periods.append(str(p))

    return formatted_periods
