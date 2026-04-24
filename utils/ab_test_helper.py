"""
Вспомогательные функции для A/B тестирования
"""
import numpy as np
from scipy import stats
from typing import List, Tuple


def split_users(user_ids: List[str], num_groups: int = 2, split_ratio: List[float] = None, seed: int = 42) -> dict:
    """
    Разбиение пользователей на группы для A/B теста

    Алгоритм гарантирует:
    - Каждый пользователь попадает только в одну группу
    - Разбиение детерминированное (при одном seed всегда одинаковое)
    - Все пользователи распределены по группам

    Args:
        user_ids: Список ID пользователей
        num_groups: Количество групп (по умолчанию 2: control, test)
        split_ratio: Соотношение групп (например, [0.5, 0.5] для 50/50)
        seed: Seed для воспроизводимости результатов

    Returns:
        Словарь {group_name: [user_ids]}

    Example:
        >>> split_users(['U001', 'U002', 'U003', 'U004'], num_groups=2, seed=42)
        {'A': ['U001', 'U003'], 'B': ['U002', 'U004']}
    """
    np.random.seed(seed)

    # Перемешиваем пользователей
    shuffled_users = np.array(user_ids).copy()
    np.random.shuffle(shuffled_users)

    # Определяем соотношение групп
    if split_ratio is None:
        split_ratio = [1.0 / num_groups] * num_groups

    # Названия групп: A, B, C, D...
    group_names = [chr(65 + i) for i in range(num_groups)]

    # Разбиваем на непересекающиеся группы
    groups = {}
    start_idx = 0

    for i, (group_name, ratio) in enumerate(zip(group_names, split_ratio)):
        if i == len(group_names) - 1:
            # Последняя группа получает всех оставшихся пользователей
            end_idx = len(shuffled_users)
        else:
            end_idx = start_idx + int(len(shuffled_users) * ratio)

        groups[group_name] = shuffled_users[start_idx:end_idx].tolist()
        start_idx = end_idx

    return groups


def calculate_t_test(group_a_values: List[float], group_b_values: List[float]) -> Tuple[float, bool, dict]:
    """
    Расчет t-теста Стьюдента для сравнения двух групп

    Используется для непрерывных метрик (revenue, AOV, ARPU, LTV).
    Проверяет гипотезу о равенстве средних значений в двух группах.

    Args:
        group_a_values: Значения метрики для группы A (контроль)
        group_b_values: Значения метрики для группы B (тест)

    Returns:
        Кортеж (p_value, is_significant, stats_dict):
        - p_value: Уровень значимости (вероятность ошибки)
        - is_significant: True если p < 0.05 (результат значим)
        - stats_dict: Дополнительная статистика

    Example:
        >>> calculate_t_test([100, 120, 110], [130, 140, 135])
        (0.023, True, {...})
    """
    # Проверка размера выборки
    n_a = len(group_a_values)
    n_b = len(group_b_values)

    warning = None
    if n_a < 30 or n_b < 30:
        warning = f"⚠️ Малая выборка (группа A: {n_a}, группа B: {n_b}). Результаты могут быть ненадежными."

    # Выполняем t-тест (двусторонний)
    t_statistic, p_value = stats.ttest_ind(group_a_values, group_b_values)

    # Проверяем значимость (уровень значимости 5%)
    is_significant = p_value < 0.05

    # Дополнительная статистика
    mean_a = np.mean(group_a_values)
    mean_b = np.mean(group_b_values)
    std_a = np.std(group_a_values, ddof=1)
    std_b = np.std(group_b_values, ddof=1)

    # Разница в процентах
    percent_diff = ((mean_b - mean_a) / mean_a) * 100 if mean_a != 0 else 0

    stats_dict = {
        't_statistic': t_statistic,
        'p_value': p_value,
        'is_significant': is_significant,
        'mean_a': mean_a,
        'mean_b': mean_b,
        'std_a': std_a,
        'std_b': std_b,
        'percent_diff': percent_diff,
        'warning': warning
    }

    return p_value, is_significant, stats_dict


def calculate_z_test(conversions_a: int, total_a: int, conversions_b: int, total_b: int) -> Tuple[float, bool, dict]:
    """
    Расчет z-теста для сравнения пропорций (конверсий)

    Используется для метрик типа Conversion Rate, Retention, Churn.
    Проверяет гипотезу о равенстве пропорций в двух группах.

    Args:
        conversions_a: Количество конверсий в группе A (контроль)
        total_a: Общее количество попыток в группе A
        conversions_b: Количество конверсий в группе B (тест)
        total_b: Общее количество попыток в группе B

    Returns:
        Кортеж (p_value, is_significant, stats_dict):
        - p_value: Уровень значимости
        - is_significant: True если p < 0.05
        - stats_dict: Дополнительная статистика

    Example:
        >>> calculate_z_test(80, 100, 90, 100)  # 80% vs 90% конверсия
        (0.045, True, {...})
    """
    # Пропорции конверсий
    p_a = conversions_a / total_a if total_a > 0 else 0
    p_b = conversions_b / total_b if total_b > 0 else 0

    # Объединенная пропорция (pooled proportion)
    p_pooled = (conversions_a + conversions_b) / (total_a + total_b)

    # Стандартная ошибка
    se = np.sqrt(p_pooled * (1 - p_pooled) * (1/total_a + 1/total_b))

    # Z-статистика
    z_statistic = (p_b - p_a) / se if se > 0 else 0

    # P-value (двусторонний тест)
    p_value = 2 * (1 - stats.norm.cdf(abs(z_statistic)))

    # Проверяем значимость
    is_significant = p_value < 0.05

    # Разница в процентных пунктах
    percent_diff = (p_b - p_a) * 100

    warning = None
    if total_a < 30 or total_b < 30:
        warning = f"⚠️ Малая выборка (группа A: {total_a}, группа B: {total_b}). Результаты могут быть ненадежными."

    stats_dict = {
        'z_statistic': z_statistic,
        'p_value': p_value,
        'is_significant': is_significant,
        'conversion_rate_a': p_a,
        'conversion_rate_b': p_b,
        'percent_diff': percent_diff,
        'warning': warning
    }

    return p_value, is_significant, stats_dict


def calculate_confidence_interval(mean: float, std: float, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Расчет доверительного интервала для среднего значения

    Доверительный интервал показывает диапазон, в котором с заданной
    вероятностью находится истинное среднее значение метрики.

    Args:
        mean: Среднее значение метрики
        std: Стандартное отклонение
        n: Размер выборки
        confidence: Уровень доверия (по умолчанию 0.95 для 95%)

    Returns:
        Кортеж (нижняя_граница, верхняя_граница)

    Example:
        >>> calculate_confidence_interval(100, 15, 50, 0.95)
        (95.7, 104.3)  # С вероятностью 95% истинное среднее в этом диапазоне
    """
    # Стандартная ошибка среднего
    se = std / np.sqrt(n)

    # t-критическое значение для заданного уровня доверия
    t_critical = stats.t.ppf((1 + confidence) / 2, n - 1)

    # Границы доверительного интервала
    margin_of_error = t_critical * se
    lower_bound = mean - margin_of_error
    upper_bound = mean + margin_of_error

    return lower_bound, upper_bound


def check_sample_size(n: int, min_size: int = 30) -> Tuple[bool, str]:
    """
    Проверка достаточности размера выборки для статистических тестов

    Минимальный размер выборки 30 - это эмпирическое правило для
    применения центральной предельной теоремы.

    Args:
        n: Размер выборки
        min_size: Минимальный рекомендуемый размер (по умолчанию 30)

    Returns:
        Кортеж (достаточно_ли, предупреждение):
        - достаточно_ли: True если n >= min_size
        - предупреждение: Текст предупреждения или None

    Example:
        >>> check_sample_size(25)
        (False, '⚠️ Малая выборка (n=25). Рекомендуется минимум 30 наблюдений.')
    """
    if n < min_size:
        return False, f"⚠️ Малая выборка (n={n}). Рекомендуется минимум {min_size} наблюдений."
    return True, None


def select_test_type(metric_type: str) -> str:
    """
    Автоматический выбор типа статистического теста по типу метрики

    Args:
        metric_type: Тип метрики (revenue, conversion, и т.д.)

    Returns:
        Рекомендуемый тип теста ('t-test' или 'z-test')

    Example:
        >>> select_test_type('revenue')
        't-test'
        >>> select_test_type('conversion')
        'z-test'
    """
    # Непрерывные метрики - используем t-test
    continuous_metrics = ['revenue', 'aov', 'arpu', 'ltv', 'gmv']

    # Пропорции и конверсии - используем z-test
    proportion_metrics = ['conversion', 'retention', 'churn']

    if metric_type in continuous_metrics:
        return 't-test'
    elif metric_type in proportion_metrics:
        return 'z-test'
    else:
        # По умолчанию t-test
        return 't-test'
