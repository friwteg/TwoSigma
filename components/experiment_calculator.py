"""
Компонент для расчета результатов A/B эксперимента
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
from utils.ab_test_helper import calculate_t_test, calculate_z_test, calculate_confidence_interval, check_sample_size
from utils.experiment_dataset_helper import load_experiment_dataset


def calculate_metric_value_with_fields(df: pd.DataFrame, metric_config: dict, user_id_field: str, metric_fields: List[str]) -> float:
    """
    Расчет значения метрики для датафрейма с использованием оригинальных названий полей

    Args:
        df: Датафрейм с данными
        metric_config: Конфигурация метрики
        user_id_field: Название колонки с user_id
        metric_fields: Список полей метрики

    Returns:
        Значение метрики
    """
    metric_type = metric_config.get('template') or metric_config.get('metric_type')
    fields = metric_config.get('fields', {})

    if not metric_fields or len(metric_fields) == 0:
        return 0

    if metric_type == 'revenue':
        # Total Revenue
        return df[metric_fields[0]].sum()

    elif metric_type == 'aov':
        # Average Order Value = Total Revenue / Total Orders
        if len(metric_fields) < 2:
            return 0
        total_revenue = df[metric_fields[0]].sum()
        total_orders = df[metric_fields[1]].nunique()
        return total_revenue / total_orders if total_orders > 0 else 0

    elif metric_type == 'arpu':
        # Average Revenue Per User
        total_revenue = df[metric_fields[0]].sum()
        total_users = df[user_id_field].nunique()
        return total_revenue / total_users if total_users > 0 else 0

    elif metric_type == 'conversion':
        # Conversion Rate
        converted = df[df[metric_fields[0]] == fields.get('success_value', 1)].shape[0]
        total = df.shape[0]
        return (converted / total * 100) if total > 0 else 0

    elif metric_type in ['dau', 'wau', 'mau']:
        # Daily/Weekly/Monthly Active Users
        return df[user_id_field].nunique()

    elif metric_type == 'retention':
        # Retention Rate
        if len(metric_fields) < 2:
            return 0
        new_users = df[df[metric_fields[1]] == 1][user_id_field].unique()
        retained_users = df[df[user_id_field].isin(new_users)].groupby(user_id_field).size()
        return (retained_users[retained_users > 1].count() / len(new_users) * 100) if len(new_users) > 0 else 0

    elif metric_type == 'churn':
        # Churn Rate
        total_users = df[user_id_field].nunique()
        active_users = df.groupby(user_id_field)[df.columns[1]].max()  # Предполагаем, что вторая колонка - дата
        churned = (datetime.now() - active_users).dt.days > 30
        return (churned.sum() / total_users * 100) if total_users > 0 else 0

    elif metric_type == 'ltv':
        # Lifetime Value
        return df.groupby(user_id_field)[metric_fields[0]].sum().mean()

    elif metric_type == 'cac':
        # Customer Acquisition Cost
        total_cost = df[metric_fields[0]].sum()
        total_users = df[user_id_field].nunique()
        return total_cost / total_users if total_users > 0 else 0

    elif metric_type == 'gmv':
        # Gross Merchandise Value
        return df[metric_fields[0]].sum()

    else:
        # Для неизвестных типов возвращаем сумму первого поля
        return df[metric_fields[0]].sum()


def calculate_metric_by_period_with_fields(df: pd.DataFrame, metric_config: dict, user_id_field: str,
                                           date_field: str, metric_fields: List[str], period: str = 'D') -> Dict[str, List]:
    """
    Расчет метрики по периодам для графика динамики

    Args:
        df: Датафрейм с данными
        metric_config: Конфигурация метрики
        user_id_field: Название колонки с user_id
        date_field: Название колонки с датой
        metric_fields: Список полей метрики
        period: Период агрегации ('D' - день, 'W' - неделя, 'M' - месяц)

    Returns:
        Словарь с периодами и значениями
    """
    df = df.copy()
    df[date_field] = pd.to_datetime(df[date_field])
    df['period'] = df[date_field].dt.to_period(period)

    periods = []
    values = []

    for period_key in sorted(df['period'].unique()):
        period_df = df[df['period'] == period_key]
        metric_value = calculate_metric_value_with_fields(period_df, metric_config, user_id_field, metric_fields)

        periods.append(str(period_key))
        values.append(metric_value)

    return {'periods': periods, 'values': values}


def calculate_metric_value(df: pd.DataFrame, metric_config: dict) -> float:
    """
    Расчет значения метрики для датафрейма

    Args:
        df: Датафрейм с данными
        metric_config: Конфигурация метрики

    Returns:
        Значение метрики
    """
    metric_type = metric_config.get('template') or metric_config.get('metric_type')
    fields = metric_config.get('fields', {})

    if metric_type == 'revenue':
        # Total Revenue
        return df['metric_field_0'].sum()

    elif metric_type == 'aov':
        # Average Order Value = Total Revenue / Total Orders
        total_revenue = df['metric_field_0'].sum()
        total_orders = df['metric_field_1'].nunique()
        return total_revenue / total_orders if total_orders > 0 else 0

    elif metric_type == 'arpu':
        # Average Revenue Per User
        total_revenue = df['metric_field_0'].sum()
        total_users = df['user_id'].nunique()
        return total_revenue / total_users if total_users > 0 else 0

    elif metric_type == 'conversion':
        # Conversion Rate
        converted = df[df['metric_field_0'] == fields.get('success_value', 1)].shape[0]
        total = df.shape[0]
        return (converted / total * 100) if total > 0 else 0

    elif metric_type in ['dau', 'wau', 'mau']:
        # Daily/Weekly/Monthly Active Users
        return df['user_id'].nunique()

    elif metric_type == 'retention':
        # Retention Rate
        new_users = df[df['metric_field_1'] == 1]['user_id'].unique()
        retained_users = df[df['user_id'].isin(new_users)].groupby('user_id').size()
        return (retained_users[retained_users > 1].count() / len(new_users) * 100) if len(new_users) > 0 else 0

    elif metric_type == 'churn':
        # Churn Rate
        total_users = df['user_id'].nunique()
        active_users = df.groupby('user_id')['date'].max()
        churned = (datetime.now() - active_users).dt.days > 30
        return (churned.sum() / total_users * 100) if total_users > 0 else 0

    elif metric_type == 'ltv':
        # Lifetime Value
        return df.groupby('user_id')['metric_field_0'].sum().mean()

    elif metric_type == 'cac':
        # Customer Acquisition Cost
        total_cost = df['metric_field_0'].sum()
        total_users = df['user_id'].nunique()
        return total_cost / total_users if total_users > 0 else 0

    elif metric_type == 'gmv':
        # Gross Merchandise Value
        return df['metric_field_0'].sum()

    else:
        # Для неизвестных типов возвращаем сумму первого поля
        return df['metric_field_0'].sum() if 'metric_field_0' in df.columns else 0


def calculate_metric_by_period(df: pd.DataFrame, metric_config: dict, period: str = 'D') -> Dict[str, List]:
    """
    Расчет метрики по периодам для графика динамики

    Args:
        df: Датафрейм с данными
        metric_config: Конфигурация метрики
        period: Период агрегации ('D' - день, 'W' - неделя, 'M' - месяц)

    Returns:
        Словарь с периодами и значениями
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['period'] = df['date'].dt.to_period(period)

    periods = []
    values = []

    for period_key in sorted(df['period'].unique()):
        period_df = df[df['period'] == period_key]
        metric_value = calculate_metric_value(period_df, metric_config)

        periods.append(str(period_key))
        values.append(metric_value)

    return {'periods': periods, 'values': values}


def calculate_experiment_results(experiment, metric, test_type: str = None) -> Dict[str, Dict]:
    """
    Расчет результатов эксперимента для всех групп

    Args:
        experiment: Объект эксперимента из БД
        metric: Объект метрики из БД
        test_type: Тип статистического теста (если None, берется из experiment.test_type)

    Returns:
        Словарь с результатами для каждой группы
    """
    # Загружаем специальный датасет эксперимента
    df = load_experiment_dataset(experiment.experiment_dataset_path)

    # Получаем названия колонок из эксперимента
    user_id_field = experiment.user_id_field
    date_field = experiment.date_field

    # Фильтруем по периоду эксперимента
    df[date_field] = pd.to_datetime(df[date_field])
    df_filtered = df[
        (df[date_field] >= experiment.start_date) &
        (df[date_field] <= experiment.end_date)
    ]

    # Проверяем, есть ли данные за весь период эксперимента
    experiment_incomplete = False
    if df_filtered.empty:
        # Если нет данных вообще - используем все доступные данные
        df_filtered = df.copy()
        experiment_incomplete = True
    else:
        # Проверяем, есть ли данные до конца эксперимента (включительно)
        max_date_in_data = df_filtered[date_field].max()
        # Преобразуем в дату без времени для корректного сравнения
        max_date_only = pd.to_datetime(max_date_in_data).date()
        end_date_only = pd.to_datetime(experiment.end_date).date()

        if max_date_only < end_date_only:
            experiment_incomplete = True

    # Определяем тип теста
    if test_type is None:
        test_type = experiment.test_type

    # Получаем уникальные группы
    groups = df_filtered['experiment_group'].unique()

    # Определяем контрольную группу
    control_group = experiment.config.get('control_group', 'control')

    results = {}
    control_data = None

    # Флаг неполных данных для возврата
    results['_experiment_incomplete'] = experiment_incomplete
    if experiment_incomplete:
        results['_incomplete_warning'] = "⚠️ Эксперимент еще не завершен или данные неполные. Дождитесь окончания эксперимента и загрузите обновленные данные для получения финальных результатов."

    # Получаем поля метрики из конфигурации эксперимента
    metric_fields = experiment.config.get('metric_fields', [])

    # Рассчитываем метрику для каждой группы
    for group_name in sorted(groups):
        group_df = df_filtered[df_filtered['experiment_group'] == group_name]

        # Основное значение метрики
        metric_value = calculate_metric_value_with_fields(group_df, metric.config, user_id_field, metric_fields)

        # Размер выборки
        # Для конверсии - количество записей (попыток), для остальных - уникальные пользователи
        if metric.config.get('template') == 'conversion':
            sample_size = len(group_df)
        else:
            sample_size = group_df[user_id_field].nunique()

        # Получаем значения для статистики
        if metric.config.get('template') in ['revenue', 'aov', 'arpu', 'ltv']:
            # Для непрерывных метрик - берем значения по пользователям
            if metric_fields and len(metric_fields) > 0:
                user_values = group_df.groupby(user_id_field)[metric_fields[0]].sum().values
            else:
                user_values = np.array([metric_value])
        elif metric.config.get('template') == 'conversion':
            # Для конверсии - считаем количество конверсий
            success_value = metric.config.get('fields', {}).get('success_value', 1)
            if metric_fields and len(metric_fields) > 0:
                conversions = group_df[group_df[metric_fields[0]] == success_value].shape[0]
            else:
                conversions = 0
            user_values = np.array([conversions, sample_size - conversions])
        else:
            # Для остальных - берем все значения
            if metric_fields and len(metric_fields) > 0:
                user_values = group_df[metric_fields[0]].values
            else:
                user_values = np.array([metric_value])

        # Стандартное отклонение
        std_dev = np.std(user_values, ddof=1) if len(user_values) > 1 else 0

        # Доверительный интервал
        ci_lower, ci_upper = calculate_confidence_interval(metric_value, std_dev, sample_size)

        # Проверка размера выборки
        _, sample_warning = check_sample_size(sample_size)

        # Временной ряд для графика
        time_series = calculate_metric_by_period_with_fields(group_df, metric.config, user_id_field, date_field, metric_fields, period='D')

        result = {
            'group_name': group_name,
            'metric_value': metric_value,
            'sample_size': sample_size,
            'std_dev': std_dev,
            'confidence_interval_lower': ci_lower,
            'confidence_interval_upper': ci_upper,
            'user_values': user_values,
            'warning': sample_warning,
            'time_series': time_series,
            'is_control': (group_name == control_group)
        }

        results[group_name] = result

        # Сохраняем контрольную группу для сравнения
        if group_name == control_group:
            control_data = result

    # Рассчитываем статистические тесты относительно контрольной группы
    if control_data:
        for group_name, result in results.items():
            # Пропускаем служебные ключи
            if group_name.startswith('_'):
                continue

            if group_name == control_group:
                result['p_value'] = None
                result['is_significant'] = False
                result['difference_percent'] = 0
                continue

            # Выбираем тест
            # Для конверсии всегда используем z-test, независимо от настроек
            if metric.config.get('template') == 'conversion':
                control_conversions = int(control_data['user_values'][0])
                control_total = control_data['sample_size']
                test_conversions = int(result['user_values'][0])
                test_total = result['sample_size']

                p_value, is_significant, _ = calculate_z_test(
                    control_conversions, control_total,
                    test_conversions, test_total
                )
            elif test_type == 't-test':
                p_value, is_significant, _ = calculate_t_test(
                    control_data['user_values'],
                    result['user_values']
                )
            elif test_type == 'z-test':
                # Для z-теста нужны конверсии и размеры выборок
                if metric.config.get('template') == 'conversion':
                    control_conversions = int(control_data['user_values'][0])
                    control_total = control_data['sample_size']
                    test_conversions = int(result['user_values'][0])
                    test_total = result['sample_size']

                    p_value, is_significant, _ = calculate_z_test(
                        control_conversions, control_total,
                        test_conversions, test_total
                    )
                else:
                    # Если метрика не конверсия, используем t-test
                    p_value, is_significant, _ = calculate_t_test(
                        control_data['user_values'],
                        result['user_values']
                    )
            else:
                # chi-square пока не реализован, используем t-test
                p_value, is_significant, _ = calculate_t_test(
                    control_data['user_values'],
                    result['user_values']
                )

            # Разница в процентах
            if control_data['metric_value'] != 0:
                difference_percent = ((result['metric_value'] - control_data['metric_value']) /
                                    control_data['metric_value'] * 100)
            else:
                difference_percent = 0

            result['p_value'] = p_value
            result['is_significant'] = is_significant
            result['difference_percent'] = difference_percent
            result['test_type'] = test_type

    return results
