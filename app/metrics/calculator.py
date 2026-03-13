"""
Калькулятор метрик для A/B тестов
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from scipy import stats


class MetricsCalculator:
    """Класс для расчёта основных метрик A/B тестов"""
    
    @staticmethod
    def calculate_conversion_rate(events: pd.DataFrame, event_column: str, user_column: str = "user_id") -> float:
        """
        Расчёт конверсии
        events: DataFrame с событиями
        event_column: колонка с названием события
        user_column: колонка с ID пользователя
        """
        if events.empty:
            return 0.0
        
        unique_users = events[user_column].nunique()
        if unique_users == 0:
            return 0.0
        
        conversions = events[events[event_column] == 1][user_column].nunique()
        return conversions / unique_users
    
    @staticmethod
    def calculate_ctr(impressions: int, clicks: int) -> float:
        """Расчёт CTR"""
        if impressions == 0:
            return 0.0
        return clicks / impressions
    
    @staticmethod
    def calculate_revenue(events: pd.DataFrame, revenue_column: str = "revenue") -> float:
        """Расчёт среднего чека (ARPU)"""
        if events.empty:
            return 0.0
        
        total_revenue = events[revenue_column].sum()
        unique_users = events["user_id"].nunique()
        
        if unique_users == 0:
            return 0.0
        
        return total_revenue / unique_users
    
    @staticmethod
    def calculate_retention(
        cohort_data: pd.DataFrame,
        cohort_column: str = "cohort",
        retained_column: str = "retained"
    ) -> Dict[str, float]:
        """
        Расчёт retention по когортам
        Возвращает dict {когорта: retention_rate}
        """
        retention = {}
        
        for cohort in cohort_data[cohort_column].unique():
            cohort_users = cohort_data[cohort_data[cohort_column] == cohort]
            total = cohort_users["user_id"].nunique()
            retained = cohort_users[cohort_users[retained_column] == 1]["user_id"].nunique()
            
            retention[str(cohort)] = retained / total if total > 0 else 0.0
        
        return retention
    
    @staticmethod
    def calculate_custom_metric(
        events: pd.DataFrame,
        numerator_expr: str,
        denominator_expr: Optional[str] = None
    ) -> float:
        """
        Расчёт кастомной метрики по выражениям
        numerator_expr: выражение для числителя (например, "sum(revenue)")
        denominator_expr: выражение для знаменателя (например, "count(user_id)")
        """
        try:
            numerator = events.eval(numerator_expr)
            if isinstance(numerator, (int, float)):
                num_value = numerator
            else:
                num_value = numerator.sum()
            
            if denominator_expr:
                denominator = events.eval(denominator_expr)
                if isinstance(denominator, (int, float)):
                    den_value = denominator
                else:
                    den_value = denominator.sum() if len(denominator) > 0 else 0
                
                if den_value == 0:
                    return 0.0
                
                return num_value / den_value
            
            return num_value
        
        except Exception as e:
            print(f"Ошибка расчёта кастомной метрики: {e}")
            return 0.0


class StatisticalSignificance:
    """Класс для расчёта статистической значимости"""
    
    @staticmethod
    def two_proportion_z_test(
        control_events: int,
        control_total: int,
        treatment_events: int,
        treatment_total: int
    ) -> tuple[float, float, float]:
        """
        Двухвыборочный z-тест для пропорций (конверсий)
        Возвращает: (z_statistic, p_value, relative_diff)
        """
        if control_total == 0 or treatment_total == 0:
            return 0.0, 1.0, 0.0
        
        p1 = control_events / control_total
        p2 = treatment_events / treatment_total
        
        # Объединённая пропорция
        p_pool = (control_events + treatment_events) / (control_total + treatment_total)
        
        if p_pool == 0 or p_pool == 1:
            return 0.0, 1.0, (p2 - p1) / p1 if p1 > 0 else 0.0
        
        # Стандартная ошибка
        se = np.sqrt(p_pool * (1 - p_pool) * (1/control_total + 1/treatment_total))
        
        if se == 0:
            return 0.0, 1.0, (p2 - p1) / p1 if p1 > 0 else 0.0
        
        # Z-статистика
        z = (p2 - p1) / se
        
        # p-value (двусторонний тест)
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))
        
        # Относительная разница
        relative_diff = (p2 - p1) / p1 if p1 > 0 else 0.0
        
        return z, p_value, relative_diff
    
    @staticmethod
    def t_test_independent(
        control_values: np.ndarray,
        treatment_values: np.ndarray
    ) -> tuple[float, float]:
        """
        Двухвыборочный t-тест Стьюдента
        Возвращает: (t_statistic, p_value)
        """
        if len(control_values) == 0 or len(treatment_values) == 0:
            return 0.0, 1.0
        
        t_stat, p_value = stats.ttest_ind(control_values, treatment_values, equal_var=False)
        return float(t_stat), float(p_value)
    
    @staticmethod
    def mann_whitney_u_test(
        control_values: np.ndarray,
        treatment_values: np.ndarray
    ) -> tuple[float, float]:
        """
        U-тест Манна-Уитни (непараметрический)
        Возвращает: (u_statistic, p_value)
        """
        if len(control_values) == 0 or len(treatment_values) == 0:
            return 0.0, 1.0
        
        u_stat, p_value = stats.mannwhitneyu(control_values, treatment_values, alternative='two-sided')
        return float(u_stat), float(p_value)
    
    @staticmethod
    def calculate_confidence_interval(
        proportion: float,
        n: int,
        confidence_level: float = 0.95
    ) -> tuple[float, float]:
        """
        Расчёт доверительного интервала для пропорции
        Возвращает: (lower_bound, upper_bound)
        """
        if n == 0:
            return 0.0, 0.0
        
        # Критическое значение z
        alpha = 1 - confidence_level
        z_critical = stats.norm.ppf(1 - alpha/2)
        
        # Стандартная ошибка
        se = np.sqrt(proportion * (1 - proportion) / n)
        
        # Доверительный интервал
        lower = max(0, proportion - z_critical * se)
        upper = min(1, proportion + z_critical * se)
        
        return lower, upper
    
    @staticmethod
    def calculate_effect_size(
        control_mean: float,
        control_std: float,
        treatment_mean: float,
        treatment_std: float,
        control_n: int,
        treatment_n: int
    ) -> float:
        """
        Расчёт размера эффекта (Cohen's d)
        """
        # Объединённое стандартное отклонение
        pooled_std = np.sqrt(
            ((control_n - 1) * control_std**2 + (treatment_n - 1) * treatment_std**2) /
            (control_n + treatment_n - 2)
        )
        
        if pooled_std == 0:
            return 0.0
        
        return (treatment_mean - control_mean) / pooled_std
    
    @staticmethod
    def calculate_power(
        effect_size: float,
        n1: int,
        n2: int,
        alpha: float = 0.05
    ) -> float:
        """
        Расчёт статистической мощности теста
        """
        # Приближённый расчёт мощности
        n_eff = (n1 * n2) / (n1 + n2)
        ncp = effect_size * np.sqrt(n_eff)
        
        # Критическое значение
        z_alpha = stats.norm.ppf(1 - alpha/2)
        
        # Мощность
        power = 1 - stats.norm.cdf(z_alpha - ncp) + stats.norm.cdf(-z_alpha - ncp)
        
        return power


def analyze_experiment_results(
    control_data: pd.DataFrame,
    treatment_data: pd.DataFrame,
    event_column: str = "converted",
    user_column: str = "user_id",
    significance_level: float = 0.05
) -> Dict[str, Any]:
    """
    Комплексный анализ результатов эксперимента
    """
    calculator = MetricsCalculator()
    stats_calc = StatisticalSignificance()
    
    # Расчёт конверсий
    control_conversion = calculator.calculate_conversion_rate(control_data, event_column, user_column)
    treatment_conversion = calculator.calculate_conversion_rate(treatment_data, event_column, user_column)
    
    # Размеры выборок
    control_n = control_data[user_column].nunique()
    treatment_n = treatment_data[user_column].nunique()
    
    # Количество конверсий
    control_events = control_data[control_data[event_column] == 1][user_column].nunique()
    treatment_events = treatment_data[treatment_data[event_column] == 1][user_column].nunique()
    
    # Статистический тест
    z_stat, p_value, relative_diff = stats_calc.two_proportion_z_test(
        control_events, control_n,
        treatment_events, treatment_n
    )
    
    # Доверительные интервалы
    control_ci = stats_calc.calculate_confidence_interval(control_conversion, control_n)
    treatment_ci = stats_calc.calculate_confidence_interval(treatment_conversion, treatment_n)
    
    return {
        "control": {
            "sample_size": control_n,
            "events": control_events,
            "conversion_rate": control_conversion,
            "confidence_interval": control_ci
        },
        "treatment": {
            "sample_size": treatment_n,
            "events": treatment_events,
            "conversion_rate": treatment_conversion,
            "confidence_interval": treatment_ci
        },
        "statistics": {
            "z_statistic": z_stat,
            "p_value": p_value,
            "relative_difference": relative_diff,
            "absolute_difference": treatment_conversion - control_conversion,
            "is_significant": p_value < significance_level,
            "significance_level": significance_level
        }
    }
