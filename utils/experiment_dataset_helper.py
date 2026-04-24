"""
Вспомогательные функции для работы со специальными датасетами экспериментов

При создании A/B теста система создает специальный датасет, который содержит:
- Оригинальные данные пользователей
- Колонку experiment_group с назначенной группой (control/test)
- Только необходимые поля для расчета метрики

Это обеспечивает изоляцию данных эксперимента и ускоряет расчеты.
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List


def get_metric_fields(metric_config: dict) -> List[str]:
    """
    Определение полей датасета, необходимых для расчета метрики

    Каждый тип метрики требует свой набор полей из датасета.
    Эта функция возвращает список названий колонок, которые нужно
    включить в датасет эксперимента.

    Args:
        metric_config: Конфигурация метрики с типом и полями

    Returns:
        Список названий полей (колонок) из датасета

    Example:
        >>> config = {'template': 'revenue', 'fields': {'revenue': 'amount'}}
        >>> get_metric_fields(config)
        ['amount']
    """
    metric_type = metric_config.get('template') or metric_config.get('metric_type')
    fields = metric_config.get('fields', {})

    # Маппинг типов метрик на необходимые поля
    metric_fields_map = {
        'revenue': [fields.get('revenue')],
        'aov': [fields.get('revenue'), fields.get('order_id')],
        'arpu': [fields.get('revenue'), fields.get('user_id')],
        'conversion': [fields.get('status')],
        'dau': [fields.get('user_id')],
        'wau': [fields.get('user_id')],
        'mau': [fields.get('user_id')],
        'retention': [fields.get('user_id'), fields.get('new_user_field')],
        'churn': [fields.get('user_id')],
        'ltv': [fields.get('revenue'), fields.get('user_id')],
        'cac': [fields.get('marketing_cost'), fields.get('user_id')],
        'gmv': [fields.get('order_amount')]
    }

    return metric_fields_map.get(metric_type, [])


def create_experiment_dataset(experiment_id: int, df: pd.DataFrame, user_id_field: str,
                              date_field: str, user_groups: Dict[str, str],
                              metric_fields: List[str]) -> pd.DataFrame:
    """
    Создание специального датасета для эксперимента

    Процесс:
    1. Добавляет колонку experiment_group с назначенной группой для каждого пользователя
    2. Фильтрует только участников эксперимента (у кого есть группа)
    3. Оставляет только необходимые колонки для расчета метрики

    Args:
        experiment_id: ID эксперимента в БД
        df: Исходный датафрейм с данными пользователей
        user_id_field: Название колонки с user_id (например, 'user_id')
        date_field: Название колонки с датой (например, 'order_date')
        user_groups: Словарь {user_id: group_name}, например {'U001': 'control', 'U002': 'test'}
        metric_fields: Список полей метрики (например, ['revenue', 'status'])

    Returns:
        Датафрейм для эксперимента с колонками:
        [user_id_field, date_field, 'experiment_group', ...metric_fields]

    Example:
        >>> user_groups = {'U001': 'control', 'U002': 'test'}
        >>> df_exp = create_experiment_dataset(1, df, 'user_id', 'date', user_groups, ['revenue'])
        >>> df_exp.columns
        ['user_id', 'date', 'experiment_group', 'revenue']
    """
    # Создаем копию для безопасности
    df_copy = df.copy()

    # Добавляем колонку с группой эксперимента
    # map() присваивает каждому user_id его группу из словаря
    df_copy['experiment_group'] = df_copy[user_id_field].map(user_groups)

    # Фильтруем только участников эксперимента (у кого group не NaN)
    df_experiment = df_copy[df_copy['experiment_group'].notna()].copy()

    # Формируем список колонок для сохранения
    columns_to_keep = [user_id_field, date_field, 'experiment_group']

    # Добавляем поля метрики (если они существуют в датасете)
    for field in metric_fields:
        if field and field in df_experiment.columns and field not in columns_to_keep:
            columns_to_keep.append(field)

    # Оставляем только нужные колонки
    df_experiment = df_experiment[columns_to_keep]

    return df_experiment


def save_experiment_dataset(df: pd.DataFrame, experiment_id: int) -> str:
    """
    Сохранение специального датасета эксперимента в CSV файл

    Датасеты экспериментов хранятся в директории data/experiments/
    с именем experiment_{id}.csv

    Args:
        df: Датафрейм для сохранения
        experiment_id: ID эксперимента

    Returns:
        Путь к сохраненному файлу (например, 'data/experiments/experiment_1.csv')

    Example:
        >>> path = save_experiment_dataset(df_exp, experiment_id=1)
        >>> print(path)
        'data/experiments/experiment_1.csv'
    """
    # Создаем директорию для датасетов экспериментов
    experiments_dir = Path("data/experiments")
    experiments_dir.mkdir(parents=True, exist_ok=True)

    # Формируем путь к файлу
    filepath = experiments_dir / f"experiment_{experiment_id}.csv"

    # Сохраняем в CSV с UTF-8 кодировкой
    df.to_csv(filepath, index=False, encoding='utf-8')

    return str(filepath)


def update_experiment_dataset(experiment_id: int, new_df: pd.DataFrame, user_id_field: str,
                              date_field: str, user_groups: Dict[str, str],
                              metric_fields: List[str], experiment_dataset_path: str) -> None:
    """
    Обновление датасета эксперимента при загрузке новых данных

    Используется когда пользователь обновляет исходный датасет
    (например, добавляет данные за новые дни эксперимента).
    Пересоздает датасет эксперимента с новыми данными.

    Args:
        experiment_id: ID эксперимента
        new_df: Новый (обновленный) датафрейм
        user_id_field: Название колонки с user_id
        date_field: Название колонки с датой
        user_groups: Маппинг {user_id: group_name}
        metric_fields: Список полей для метрики
        experiment_dataset_path: Путь к существующему файлу датасета

    Note:
        Полностью заменяет старый файл новым датасетом
    """
    # Создаем обновленный датасет эксперимента
    df_experiment = create_experiment_dataset(
        experiment_id, new_df, user_id_field, date_field, user_groups, metric_fields
    )

    # Сохраняем, заменяя старый файл
    df_experiment.to_csv(experiment_dataset_path, index=False, encoding='utf-8')


def load_experiment_dataset(experiment_dataset_path: str) -> pd.DataFrame:
    """
    Загрузка датасета эксперимента из CSV файла

    Автоматически преобразует колонки с датами в datetime формат
    для корректной работы с временными рядами.

    Args:
        experiment_dataset_path: Путь к CSV файлу датасета

    Returns:
        Датафрейм с данными эксперимента

    Example:
        >>> df = load_experiment_dataset('data/experiments/experiment_1.csv')
        >>> df.columns
        ['user_id', 'order_date', 'experiment_group', 'revenue']
    """
    # Загружаем CSV
    df = pd.read_csv(experiment_dataset_path)

    # Автоматически преобразуем колонки с датами
    # Ищем текстовые колонки (кроме experiment_group) и пытаемся преобразовать в datetime
    date_columns = [col for col in df.columns
                   if col not in ['experiment_group'] and df[col].dtype == 'object']

    for col in date_columns:
        try:
            df[col] = pd.to_datetime(df[col])
        except:
            # Если не получилось преобразовать - пропускаем
            pass

    return df

