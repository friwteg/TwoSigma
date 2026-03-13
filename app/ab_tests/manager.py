"""
Менеджер экспериментов — CRUD операции и управление тестами
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from app.ab_tests.models import (
    Experiment, ExperimentStatus, ExperimentGroup, 
    MetricConfig, MetricType, ExperimentResult, FeatureFlag
)


class ExperimentManager:
    """Управление экспериментами (создание, чтение, обновление, удаление)"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Получение подключения к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Инициализация таблиц БД"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица экспериментов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    planned_duration_days INTEGER DEFAULT 14,
                    significance_level REAL DEFAULT 0.05,
                    min_sample_size INTEGER DEFAULT 100,
                    minimum_detectable_effect REAL DEFAULT 0.05,
                    audience_filter TEXT DEFAULT '{}',
                    control_group_config TEXT,
                    treatment_groups_config TEXT,
                    primary_metric_config TEXT NOT NULL,
                    secondary_metrics_config TEXT DEFAULT '[]'
                )
            """)
            
            # Таблица результатов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id INTEGER NOT NULL,
                    group_name TEXT NOT NULL,
                    sample_size INTEGER NOT NULL,
                    events_count INTEGER DEFAULT 0,
                    metric_value REAL NOT NULL,
                    p_value REAL,
                    confidence_interval_lower REAL,
                    confidence_interval_upper REAL,
                    is_significant BOOLEAN DEFAULT 0,
                    relative_diff REAL,
                    absolute_diff REAL,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
                )
            """)
            
            # Таблица фича-флагов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feature_flags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    enabled BOOLEAN DEFAULT 0,
                    rollout_percentage REAL DEFAULT 0,
                    conditions TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    # ==================== Experiment CRUD ====================
    
    def create_experiment(self, experiment: Experiment) -> int:
        """Создание нового эксперимента"""
        is_valid, message = experiment.is_valid()
        if not is_valid:
            raise ValueError(message)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experiments (
                    name, description, status, planned_duration_days,
                    significance_level, min_sample_size, minimum_detectable_effect,
                    audience_filter, control_group_config, treatment_groups_config,
                    primary_metric_config, secondary_metrics_config
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment.name,
                experiment.description,
                experiment.status,
                experiment.planned_duration_days,
                experiment.significance_level,
                experiment.min_sample_size,
                experiment.minimum_detectable_effect,
                json.dumps(experiment.audience_filter),
                json.dumps(experiment.control_group_config),
                json.dumps([g.dict() for g in experiment.treatment_groups]),
                json.dumps(experiment.primary_metric_config),
                json.dumps([m.dict() for m in experiment.secondary_metrics])
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_experiment(self, experiment_id: int) -> Optional[Experiment]:
        """Получение эксперимента по ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_experiment(row)
    
    def get_all_experiments(self) -> List[Experiment]:
        """Получение всех экспериментов"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experiments ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_experiment(row) for row in rows]
    
    def update_experiment(self, experiment_id: int, updates: Dict[str, Any]) -> bool:
        """Обновление эксперимента"""
        allowed_fields = {
            'name', 'description', 'status', 'started_at', 'ended_at',
            'planned_duration_days', 'significance_level', 'min_sample_size',
            'minimum_detectable_effect', 'audience_filter'
        }
        
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not filtered_updates:
            return False
        
        set_clause = ", ".join(f"{k} = ?" for k in filtered_updates.keys())
        values = list(filtered_updates.values()) + [experiment_id]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE experiments SET {set_clause} WHERE id = ?
            """, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_experiment(self, experiment_id: int) -> bool:
        """Удаление эксперимента"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
            cursor.execute("DELETE FROM experiment_results WHERE experiment_id = ?", (experiment_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def start_experiment(self, experiment_id: int) -> bool:
        """Запуск эксперимента"""
        return self.update_experiment(experiment_id, {
            "status": ExperimentStatus.RUNNING,
            "started_at": datetime.now()
        })
    
    def stop_experiment(self, experiment_id: int) -> bool:
        """Остановка эксперимента"""
        return self.update_experiment(experiment_id, {
            "status": ExperimentStatus.COMPLETED,
            "ended_at": datetime.now()
        })
    
    def pause_experiment(self, experiment_id: int) -> bool:
        """Пауза эксперимента"""
        return self.update_experiment(experiment_id, {"status": ExperimentStatus.PAUSED})
    
    # ==================== Results ====================
    
    def save_result(self, result: ExperimentResult) -> int:
        """Сохранение результата эксперимента"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experiment_results (
                    experiment_id, group_name, sample_size, events_count,
                    metric_value, p_value, confidence_interval_lower,
                    confidence_interval_upper, is_significant, relative_diff, absolute_diff
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.experiment_id,
                result.group_name,
                result.sample_size,
                result.events_count,
                result.metric_value,
                result.p_value,
                result.confidence_interval[0] if result.confidence_interval else None,
                result.confidence_interval[1] if result.confidence_interval else None,
                result.is_significant,
                result.relative_diff,
                result.absolute_diff
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_results(self, experiment_id: int) -> List[ExperimentResult]:
        """Получение результатов эксперимента"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM experiment_results 
                WHERE experiment_id = ? 
                ORDER BY calculated_at DESC
            """, (experiment_id,))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                ci = None
                if row["confidence_interval_lower"] and row["confidence_interval_upper"]:
                    ci = (row["confidence_interval_lower"], row["confidence_interval_upper"])
                
                results.append(ExperimentResult(
                    experiment_id=row["experiment_id"],
                    group_name=row["group_name"],
                    sample_size=row["sample_size"],
                    events_count=row["events_count"],
                    metric_value=row["metric_value"],
                    p_value=row["p_value"],
                    confidence_interval=ci,
                    is_significant=bool(row["is_significant"]),
                    relative_diff=row["relative_diff"],
                    absolute_diff=row["absolute_diff"],
                    calculated_at=row["calculated_at"]
                ))
            
            return results
    
    # ==================== Feature Flags ====================
    
    def create_feature_flag(self, flag: FeatureFlag) -> int:
        """Создание фича-флага"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feature_flags (name, description, enabled, rollout_percentage, conditions)
                VALUES (?, ?, ?, ?, ?)
            """, (
                flag.name, flag.description, flag.enabled,
                flag.rollout_percentage, json.dumps(flag.conditions)
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_feature_flag(self, name: str) -> Optional[FeatureFlag]:
        """Получение фича-флага по названию"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feature_flags WHERE name = ?", (name,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return FeatureFlag(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                enabled=bool(row["enabled"]),
                rollout_percentage=row["rollout_percentage"],
                conditions=json.loads(row["conditions"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
    
    def get_all_feature_flags(self) -> List[FeatureFlag]:
        """Получение всех фича-флагов"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feature_flags ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            return [
                FeatureFlag(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    enabled=bool(row["enabled"]),
                    rollout_percentage=row["rollout_percentage"],
                    conditions=json.loads(row["conditions"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in rows
            ]
    
    def update_feature_flag(self, flag_id: int, updates: Dict[str, Any]) -> bool:
        """Обновление фича-флага"""
        updates["updated_at"] = datetime.now()
        
        if "conditions" in updates:
            updates["conditions"] = json.dumps(updates["conditions"])
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [flag_id]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE feature_flags SET {set_clause} WHERE id = ?
            """, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_feature_flag(self, flag_id: int) -> bool:
        """Удаление фича-флага"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM feature_flags WHERE id = ?", (flag_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ==================== Helpers ====================
    
    def _row_to_experiment(self, row: sqlite3.Row) -> Experiment:
        """Преобразование строки БД в модель Experiment"""
        return Experiment(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            status=row["status"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            planned_duration_days=row["planned_duration_days"],
            significance_level=row["significance_level"],
            min_sample_size=row["min_sample_size"],
            minimum_detectable_effect=row["minimum_detectable_effect"],
            audience_filter=json.loads(row["audience_filter"]),
            control_group=ExperimentGroup(**json.loads(row["control_group_config"])) if row["control_group_config"] else ExperimentGroup(),
            treatment_groups=[ExperimentGroup(**g) for g in json.loads(row["treatment_groups_config"])],
            primary_metric=MetricConfig(**json.loads(row["primary_metric_config"])),
            secondary_metrics=[MetricConfig(**m) for m in json.loads(row["secondary_metrics_config"])]
        )
