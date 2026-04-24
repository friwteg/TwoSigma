"""
Вспомогательные функции для работы с временными периодами
"""
import pandas as pd
from typing import Tuple


def assign_period(df: pd.DataFrame, date_field: str, time_window: str) -> pd.DataFrame:
    """
    Присваивает периоды датафрейму на основе временного окна

    Args:
        df: Датафрейм с данными
        date_field: Название поля с датой
        time_window: Тип периода ('day', 'week', 'month')

    Returns:
        Датафрейм с добавленными колонками 'period' и 'period_str'
    """
    df = df.copy()
    df[date_field] = pd.to_datetime(df[date_field])

    if time_window == "day":
        df['period'] = df[date_field].dt.date
        df['period_str'] = df[date_field].dt.strftime('%d.%m.%Y')
    elif time_window == "week":
        df['period'] = df[date_field].dt.to_period('W')
        df['period_str'] = df['period'].apply(
            lambda x: f"{x.start_time.strftime('%d.%m')} - {x.end_time.strftime('%d.%m')}"
        )
    elif time_window == "month":
        df['period'] = df[date_field].dt.to_period('M')
        df['period_str'] = df[date_field].dt.strftime('%m.%Y')

    return df


def format_period_result(periods: list, values: list) -> dict:
    """
    Форматирует результат расчета метрики с периодами

    Args:
        periods: Список периодов
        values: Список значений

    Returns:
        Словарь с результатами
    """
    if not values:
        return {
            'periods': [],
            'values': [],
            'mean': 0,
            'total': 0,
            'count': 0,
            'no_data': True
        }

    return {
        'periods': periods,
        'values': values,
        'mean': sum(values) / len(values),
        'total': sum(values),
        'count': len(values)
    }


def calculate_metric_by_period(
    df: pd.DataFrame,
    time_window: str,
    aggregation_func
) -> Tuple[list, list]:
    """
    Группирует данные по периодам и применяет функцию агрегации

    Args:
        df: Датафрейм с колонкой 'period'
        time_window: Тип периода
        aggregation_func: Функция для расчета метрики на каждом периоде

    Returns:
        Кортеж (список периодов, список значений)
    """
    grouped_data = []
    for period in sorted(df['period'].unique()):
        period_df = df[df['period'] == period]
        value = aggregation_func(period_df)
        grouped_data.append((period, value))

    periods = [x[0] for x in grouped_data]
    values = [x[1] for x in grouped_data]

    return periods, values
