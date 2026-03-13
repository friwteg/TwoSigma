"""
Модели данных для A/B тестов
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ExperimentStatus(str, Enum):
    """Статусы эксперимента"""
    DRAFT = "draft"           # Черновик
    RUNNING = "running"       # Активный
    PAUSED = "paused"         # На паузе
    COMPLETED = "completed"   # Завершён
    STOPPED = "stopped"       # Остановлен


class ExperimentGroup(BaseModel):
    """Группа в эксперименте"""
    name: str = Field(..., description="Название группы (control/treatment)")
    description: str = Field("", description="Описание группы")
    traffic_share: float = Field(50.0, ge=0, le=100, description="Доля трафика в %")
    weight: float = Field(1.0, ge=0, description="Вес группы для сплитования")


class MetricType(str, Enum):
    """Типы метрик"""
    CONVERSION = "conversion"      # Конверсия
    CTR = "ctr"                    # Click-Through Rate
    REVENUE = "revenue"            # Средний чек
    RETENTION = "retention"        # Удержание
    CUSTOM = "custom"              # Кастомная метрика


class MetricConfig(BaseModel):
    """Конфигурация метрики"""
    name: str = Field(..., description="Название метрики")
    metric_type: MetricType = Field(MetricType.CUSTOM, description="Тип метрики")
    event_name: str = Field(..., description="Название события в БД")
    numerator: Optional[str] = Field(None, description="Числитель (для кастомных метрик)")
    denominator: Optional[str] = Field(None, description="Знаменатель (для кастомных метрик)")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Фильтры для метрики")


class Experiment(BaseModel):
    """Модель эксперимента"""
    id: Optional[int] = Field(None, description="ID эксперимента")
    name: str = Field(..., min_length=1, max_length=200, description="Название эксперимента")
    description: str = Field("", description="Описание эксперимента")
    status: ExperimentStatus = Field(ExperimentStatus.DRAFT, description="Статус")
    
    # Даты
    created_at: datetime = Field(default_factory=datetime.now, description="Дата создания")
    started_at: Optional[datetime] = Field(None, description="Дата запуска")
    ended_at: Optional[datetime] = Field(None, description="Дата завершения")
    planned_duration_days: int = Field(14, ge=1, le=365, description="Планируемая длительность (дней)")
    
    # Группы
    control_group: ExperimentGroup = Field(
        default_factory=lambda: ExperimentGroup(name="control", description="Контрольная группа"),
        description="Контрольная группа"
    )
    treatment_groups: List[ExperimentGroup] = Field(
        default_factory=list,
        description="Тестовые группы"
    )
    
    # Метрики
    primary_metric: MetricConfig = Field(..., description="Основная метрика")
    secondary_metrics: List[MetricConfig] = Field(
        default_factory=list,
        description="Дополнительные метрики"
    )
    
    # Параметры
    significance_level: float = Field(0.05, ge=0.001, le=0.1, description="Уровень значимости (alpha)")
    min_sample_size: int = Field(100, ge=10, description="Минимальный размер выборки")
    minimum_detectable_effect: float = Field(0.05, ge=0.01, le=1, description="Минимальный обнаружимый эффект (MDE)")
    
    # Сегментация
    audience_filter: Dict[str, Any] = Field(
        default_factory=dict,
        description="Фильтр аудитории"
    )
    
    class Config:
        use_enum_values = True
    
    def get_all_groups(self) -> List[ExperimentGroup]:
        """Получить все группы эксперимента"""
        return [self.control_group] + self.treatment_groups
    
    def total_traffic_share(self) -> float:
        """Общая доля трафика"""
        return sum(g.traffic_share for g in self.get_all_groups())
    
    def is_valid(self) -> tuple[bool, str]:
        """Валидация эксперимента"""
        total = self.total_traffic_share()
        if not (99.9 <= total <= 100.1):
            return False, f"Сумма долей трафика должна быть 100%, сейчас: {total}%"
        
        if not self.treatment_groups:
            return False, "Должна быть хотя бы одна тестовая группа"
        
        return True, "OK"


class ExperimentResult(BaseModel):
    """Результаты эксперимента"""
    experiment_id: int
    group_name: str
    
    # Метрики
    sample_size: int = Field(..., description="Размер выборки")
    events_count: int = Field(0, description="Количество событий")
    metric_value: float = Field(..., description="Значение метрики")
    
    # Статистика
    p_value: Optional[float] = Field(None, description="p-value")
    confidence_interval: Optional[tuple[float, float]] = Field(None, description="Доверительный интервал")
    is_significant: bool = Field(False, description="Статистически значимо")
    relative_diff: Optional[float] = Field(None, description="Относительная разница к контролю")
    absolute_diff: Optional[float] = Field(None, description="Абсолютная разница к контролю")
    
    # Мета
    calculated_at: datetime = Field(default_factory=datetime.now)


class FeatureFlag(BaseModel):
    """Модель фича-флага"""
    id: Optional[int] = Field(None, description="ID флага")
    name: str = Field(..., min_length=1, max_length=100, description="Название флага")
    description: str = Field("", description="Описание")
    enabled: bool = Field(False, description="Включён ли флаг")
    rollout_percentage: float = Field(0, ge=0, le=100, description="Процент rollout")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Условия активации")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
