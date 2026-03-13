"""
Модуль сплитования пользователей
Детерминированный хэш-алгоритм для распределения по группам
"""
import hashlib
from typing import Dict, List, Optional
from app.ab_tests.models import Experiment, ExperimentGroup


class UserSplits:
    """Класс для детерминированного сплитования пользователей"""
    
    @staticmethod
    def hash_user(user_id: str, experiment_key: str) -> int:
        """
        Хэширование пользователя для эксперимента
        Возвращает число от 0 до 9999
        """
        key = f"{user_id}:{experiment_key}"
        hash_bytes = hashlib.md5(key.encode()).digest()
        hash_int = int.from_bytes(hash_bytes[:4], byteorder='big')
        return hash_int % 10000
    
    @staticmethod
    def get_user_group(
        user_id: str,
        experiment: Experiment
    ) -> Optional[ExperimentGroup]:
        """
        Определение группы для пользователя
        Возвращает группу или None если пользователь не попадает в эксперимент
        """
        experiment_key = f"exp_{experiment.id}_{experiment.name}"
        hash_value = UserSplits.hash_user(user_id, experiment_key)
        
        # Нормализуем до 0-100
        normalized = hash_value / 100  # 0-100
        
        # Проверяем группы по порядку
        cumulative = 0.0
        all_groups = experiment.get_all_groups()
        
        for group in all_groups:
            cumulative += group.traffic_share
            if normalized < cumulative:
                return group
        
        return None
    
    @staticmethod
    def check_flag(
        user_id: str,
        flag_name: str,
        enabled: bool,
        rollout_percentage: float = 100.0
    ) -> bool:
        """
        Проверка фича-флага для пользователя
        """
        if not enabled:
            return False
        
        if rollout_percentage >= 100:
            return True
        
        if rollout_percentage <= 0:
            return False
        
        # Детерминированная проверка rollout
        hash_value = UserSplits.hash_user(user_id, f"flag_{flag_name}")
        normalized = hash_value / 100  # 0-100
        
        return normalized < rollout_percentage
    
    @staticmethod
    def get_bucket(user_id: str, experiment_key: str, num_buckets: int = 100) -> int:
        """
        Получение бакета (корзины) для пользователя
        Используется для равномерного распределения
        """
        hash_value = UserSplits.hash_user(user_id, experiment_key)
        return hash_value % num_buckets
    
    @staticmethod
    def validate_split(
        groups: List[ExperimentGroup],
        sample_size: int = 10000
    ) -> Dict[str, float]:
        """
        Валидация распределения трафика
        Возвращает фактические доли для каждой группы
        """
        from collections import Counter
        
        counter = Counter()
        
        for i in range(sample_size):
            user_id = f"test_user_{i}"
            # Создаём мок-эксперимент для проверки
            mock_experiment = Experiment(
                name="test_split",
                control_group=groups[0] if groups else ExperimentGroup(),
                treatment_groups=groups[1:] if len(groups) > 1 else []
            )
            group = UserSplits.get_user_group(user_id, mock_experiment)
            if group:
                counter[group.name] += 1
        
        total = sum(counter.values())
        return {name: count / total * 100 for name, count in counter.items()}
