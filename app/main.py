"""
TwoSigma — Платформа для A/B тестирования
Главное приложение Streamlit
"""
import sys
from pathlib import Path

# Добавляем корень проекта в path для импортов
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from datetime import datetime

from config import PAGE_TITLE, PAGE_LAYOUT, APP_DATABASE_PATH, SIGNIFICANCE_LEVEL
from app.database.connection import DatabaseConnection, create_connection_from_config
from app.ab_tests.manager import ExperimentManager
from app.ab_tests.models import (
    Experiment, ExperimentStatus, ExperimentGroup,
    MetricConfig, MetricType, FeatureFlag, ExperimentResult
)
from app.ab_tests.splits import UserSplits
from app.metrics.calculator import analyze_experiment_results, MetricsCalculator, StatisticalSignificance
from app.ui.sidebar import render_sidebar, get_page_key
from app.ui.dashboard import (
    render_dashboard_summary,
    render_experiment_card,
    render_metrics_summary,
    render_experiment_results,
    render_experiments_list
)
from app.ui.charts import create_conversion_bar_chart, create_lift_chart


# ==================== Конфигурация страницы ====================
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="🧪",
    layout=PAGE_LAYOUT,
    initial_sidebar_state="expanded"
)

# ==================== Инициализация session state ====================
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False

if 'active_experiments' not in st.session_state:
    st.session_state.active_experiments = 0

if 'experiment_manager' not in st.session_state:
    st.session_state.experiment_manager = None

# ==================== Инициализация ====================
def init_app():
    """Инициализация приложения"""
    # Инициализация менеджера экспериментов
    st.session_state.experiment_manager = ExperimentManager(str(APP_DATABASE_PATH))
    
    # Подключение к внешней БД (опционально)
    try:
        db_conn = create_connection_from_config()
        if db_conn.connect():
            st.session_state.db_connected = True
    except Exception:
        st.session_state.db_connected = False
    
    # Обновление счётчика активных экспериментов
    if st.session_state.experiment_manager:
        experiments = st.session_state.experiment_manager.get_all_experiments()
        st.session_state.active_experiments = sum(
            1 for exp in experiments if exp.status == ExperimentStatus.RUNNING
        )


# ==================== Страницы ====================

def render_dashboard():
    """Главный дашборд"""
    st.markdown("# 📊 Дашборд")
    st.markdown("Обзор всех экспериментов и ключевые метрики")
    
    manager = st.session_state.experiment_manager
    if not manager:
        st.warning("Приложение не инициализировано")
        return
    
    # Получаем все эксперименты
    experiments = manager.get_all_experiments()
    
    # Сводка
    total = len(experiments)
    active = sum(1 for e in experiments if e.status == ExperimentStatus.RUNNING)
    completed = sum(1 for e in experiments if e.status == ExperimentStatus.COMPLETED)
    
    # Подсчёт значимых результатов
    significant = 0
    for exp in experiments:
        if exp.status == ExperimentStatus.COMPLETED:
            results = manager.get_results(exp.id)
            if any(r.is_significant for r in results):
                significant += 1
    
    render_dashboard_summary(total, active, completed, significant)
    
    st.markdown("---")
    
    # Последние эксперименты
    st.markdown("### Последние эксперименты")
    
    if not experiments:
        st.info("🧪 Нет созданных экспериментов. Создайте первый эксперимент!")
    else:
        for exp in experiments[:5]:
            with st.expander(
                f"{'🔴' if exp.status == 'running' else '📝'} {exp.name} — {exp.status}",
                expanded=False
            ):
                st.write(f"**Описание:** {exp.description or 'Нет описания'}")
                st.write(f"**Создан:** {exp.created_at}")
                st.write(f"**Длительность:** {exp.planned_duration_days} дн.")
                st.write(f"**Основная метрика:** {exp.primary_metric.name}")
                
                # Кнопки управления
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if exp.status == ExperimentStatus.DRAFT:
                        if st.button("▶️ Запустить", key=f"start_{exp.id}"):
                            manager.start_experiment(exp.id)
                            st.rerun()
                
                with col2:
                    if exp.status == ExperimentStatus.RUNNING:
                        if st.button("⏸️ Пауза", key=f"pause_{exp.id}"):
                            manager.pause_experiment(exp.id)
                            st.rerun()
                
                with col3:
                    if exp.status in [ExperimentStatus.RUNNING, ExperimentStatus.PAUSED]:
                        if st.button("⏹️ Завершить", key=f"stop_{exp.id}"):
                            manager.stop_experiment(exp.id)
                            st.rerun()


def render_experiments():
    """Страница списка экспериментов"""
    st.markdown("# 🧪 Эксперименты")
    st.markdown("Управление всеми экспериментами")
    
    manager = st.session_state.experiment_manager
    if not manager:
        st.warning("Приложение не инициализировано")
        return
    
    experiments = manager.get_all_experiments()
    render_experiments_list(experiments)
    
    st.markdown("---")
    
    # Детали выбранного эксперимента
    st.markdown("### Детали эксперимента")
    
    experiment_ids = [f"{exp.id}: {exp.name}" for exp in experiments]
    
    if not experiment_ids:
        st.info("Нет экспериментов для просмотра")
        return
    
    selected = st.selectbox("Выберите эксперимент", experiment_ids)
    
    if selected:
        exp_id = int(selected.split(":")[0])
        exp = manager.get_experiment(exp_id)
        
        if exp:
            st.markdown(f"#### {exp.name}")
            st.write(exp.description or "Нет описания")
            
            # Статус
            st.metric("Статус", exp.status)
            
            # Группы
            st.markdown("##### Группы")
            cols = st.columns(len(exp.get_all_groups()))
            for i, group in enumerate(exp.get_all_groups()):
                with cols[i]:
                    st.metric(
                        group.name.capitalize(),
                        f"{group.traffic_share}%"
                    )
            
            # Метрики
            st.markdown("##### Метрики")
            st.write(f"**Основная:** {exp.primary_metric.name} ({exp.primary_metric.metric_type})")
            
            if exp.secondary_metrics:
                secondary = ", ".join(m.name for m in exp.secondary_metrics)
                st.write(f"**Дополнительные:** {secondary}")
            
            # Результаты
            results = manager.get_results(exp.id)
            if results:
                st.markdown("##### Результаты")
                for result in results:
                    st.write(
                        f"**{result.group_name}:** {result.metric_value:.4f} "
                        f"(n={result.sample_size}, p={result.p_value:.4f if result.p_value else 'N/A'})"
                    )


def render_new_experiment():
    """Страница создания нового эксперимента"""
    st.markdown("# ➕ Новый эксперимент")
    st.markdown("Создание и настройка A/B теста")
    
    manager = st.session_state.experiment_manager
    if not manager:
        st.warning("Приложение не инициализировано")
        return
    
    with st.form("new_experiment_form"):
        st.markdown("### Основная информация")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Название эксперимента*", placeholder="Например: Новая кнопка покупки")
            description = st.text_area("Описание", placeholder="Опишите цель эксперимента...")
        
        with col2:
            planned_duration = st.number_input(
                "Планируемая длительность (дней)*",
                min_value=1,
                max_value=365,
                value=14
            )
            significance_level = st.selectbox(
                "Уровень значимости (alpha)",
                options=[0.01, 0.05, 0.1],
                index=1
            )
        
        st.markdown("### Группы")
        
        col1, col2 = st.columns(2)
        
        with col1:
            control_name = st.text_input("Название контрольной группы", value="control")
            control_desc = st.text_input("Описание контрольной группы", value="Текущая версия")
        
        with col2:
            treatment_name = st.text_input("Название тестовой группы*", value="treatment")
            treatment_desc = st.text_input("Описание тестовой группы", value="Новая версия")
        
        traffic_col1, traffic_col2 = st.columns(2)
        
        with traffic_col1:
            control_traffic = st.slider(
                "Доля трафика контрольной группы (%)",
                min_value=0,
                max_value=100,
                value=50
            )
        
        with traffic_col2:
            treatment_traffic = 100 - control_traffic
            st.info(f"Доля тестовой группы: {treatment_traffic}%")
        
        st.markdown("### Метрики")
        
        metric_type = st.selectbox(
            "Тип основной метрики*",
            options=[
                MetricType.CONVERSION.value,
                MetricType.CTR.value,
                MetricType.REVENUE.value,
                MetricType.RETENTION.value,
                MetricType.CUSTOM.value
            ]
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            metric_name = st.text_input("Название метрики*", placeholder="conversion_rate")
            event_name = st.text_input("Название события в БД*", placeholder="purchase")
        
        with col2:
            min_sample = st.number_input(
                "Минимальный размер выборки*",
                min_value=10,
                value=100
            )
            mde = st.number_input(
                "Минимальный обнаружимый эффект (MDE)",
                min_value=0.01,
                max_value=1.0,
                value=0.05,
                format="%.2f"
            )
        
        # Отправка формы
        submitted = st.form_submit_button("🚀 Создать эксперимент", use_container_width=True)
        
        if submitted:
            if not name or not treatment_name or not metric_name or not event_name:
                st.error("Заполните все обязательные поля (отмечены *)")
            elif control_traffic + treatment_traffic != 100:
                st.error("Сумма долей трафика должна быть 100%")
            else:
                try:
                    # Создаём модель эксперимента
                    experiment = Experiment(
                        name=name,
                        description=description,
                        planned_duration_days=planned_duration,
                        significance_level=significance_level,
                        min_sample_size=min_sample,
                        minimum_detectable_effect=mde,
                        control_group=ExperimentGroup(
                            name=control_name,
                            description=control_desc,
                            traffic_share=control_traffic
                        ),
                        treatment_groups=[
                            ExperimentGroup(
                                name=treatment_name,
                                description=treatment_desc,
                                traffic_share=treatment_traffic
                            )
                        ],
                        primary_metric=MetricConfig(
                            name=metric_name,
                            metric_type=metric_type,
                            event_name=event_name
                        )
                    )
                    
                    # Сохраняем
                    exp_id = manager.create_experiment(experiment)
                    
                    st.success(f"✅ Эксперимент создан! ID: {exp_id}")
                    st.balloons()
                    
                    # Предлагаем запустить
                    if st.button("▶️ Запустить эксперимент"):
                        manager.start_experiment(exp_id)
                        st.rerun()
                
                except Exception as e:
                    st.error(f"Ошибка при создании: {e}")


def render_feature_flags():
    """Страница управления feature flags"""
    st.markdown("# 🚩 Feature Flags")
    st.markdown("Управление фича-флагами")
    
    manager = st.session_state.experiment_manager
    if not manager:
        st.warning("Приложение не инициализировано")
        return
    
    # Список флагов
    flags = manager.get_all_feature_flags()
    
    st.markdown("### Существующие флаги")
    
    if not flags:
        st.info("Нет созданных feature flags")
    else:
        for flag in flags:
            with st.expander(
                f"{'✅' if flag.enabled else '❌'} {flag.name}",
                expanded=False
            ):
                st.write(f"**Описание:** {flag.description or 'Нет описания'}")
                st.write(f"**Rollout:** {flag.rollout_percentage}%")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    new_enabled = st.checkbox(
                        "Включён",
                        value=flag.enabled,
                        key=f"enabled_{flag.id}"
                    )
                
                with col2:
                    new_rollout = st.slider(
                        "Rollout %",
                        min_value=0,
                        max_value=100,
                        value=int(flag.rollout_percentage),
                        key=f"rollout_{flag.id}"
                    )
                
                if st.button("💾 Сохранить", key=f"save_{flag.id}"):
                    manager.update_feature_flag(flag.id, {
                        "enabled": new_enabled,
                        "rollout_percentage": new_rollout
                    })
                    st.success("Сохранено!")
                
                if st.button("🗑️ Удалить", key=f"delete_{flag.id}"):
                    manager.delete_feature_flag(flag.id)
                    st.rerun()
    
    st.markdown("---")
    
    # Создание нового флага
    st.markdown("### Новый feature flag")
    
    with st.form("new_flag_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            flag_name = st.text_input("Название*", placeholder="show_new_checkout")
            flag_desc = st.text_area("Описание", placeholder="Показать новый процесс оплаты...")
        
        with col2:
            flag_enabled = st.checkbox("Включён сразу", value=False)
            flag_rollout = st.slider(
                "Начальный rollout %",
                min_value=0,
                max_value=100,
                value=0
            )
        
        submitted = st.form_submit_button("➕ Создать флаг")
        
        if submitted:
            if not flag_name:
                st.error("Введите название флага")
            else:
                try:
                    flag = FeatureFlag(
                        name=flag_name,
                        description=flag_desc,
                        enabled=flag_enabled,
                        rollout_percentage=flag_rollout
                    )
                    
                    manager.create_feature_flag(flag)
                    st.success(f"✅ Флаг '{flag_name}' создан!")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Ошибка: {e}")


def render_analytics():
    """Страница аналитики"""
    st.markdown("# 📈 Аналитика")
    st.markdown("Детальный анализ результатов экспериментов")
    
    manager = st.session_state.experiment_manager
    if not manager:
        st.warning("Приложение не инициализировано")
        return
    
    experiments = manager.get_all_experiments()
    
    if not experiments:
        st.info("Нет экспериментов для анализа")
        return
    
    # Выбор эксперимента
    experiment_ids = [f"{exp.id}: {exp.name}" for exp in experiments]
    selected = st.selectbox("Выберите эксперимент", experiment_ids)
    
    if not selected:
        return
    
    exp_id = int(selected.split(":")[0])
    exp = manager.get_experiment(exp_id)
    
    if not exp:
        return
    
    st.markdown(f"### Анализ: {exp.name}")
    
    # Загрузка данных для анализа (симуляция)
    st.markdown("#### Данные для анализа")
    
    col1, col2 = st.columns(2)
    
    with col1:
        control_n = st.number_input(
            "Размер контрольной группы",
            min_value=0,
            value=1000,
            key="control_n"
        )
        control_events = st.number_input(
            "Конверсии в контрольной группе",
            min_value=0,
            value=100,
            key="control_events"
        )
    
    with col2:
        treatment_n = st.number_input(
            "Размер тестовой группы",
            min_value=0,
            value=1000,
            key="treatment_n"
        )
        treatment_events = st.number_input(
            "Конверсии в тестовой группе",
            min_value=0,
            value=120,
            key="treatment_events"
        )
    
    if st.button("🔬 Рассчитать"):
        # Анализ
        results = analyze_experiment_results(
            control_data=pd.DataFrame({
                'user_id': range(control_n),
                'converted': [1] * control_events + [0] * (control_n - control_events)
            }),
            treatment_data=pd.DataFrame({
                'user_id': range(treatment_n),
                'converted': [1] * treatment_events + [0] * (treatment_n - treatment_events)
            }),
            significance_level=exp.significance_level
        )
        
        # Отображение результатов
        render_metrics_summary({
            'control_conversion': results['control']['conversion_rate'],
            'treatment_conversion': results['treatment']['conversion_rate'],
            'relative_diff': results['statistics']['relative_difference'],
            'p_value': results['statistics']['p_value'],
            'is_significant': results['statistics']['is_significant'],
            'sample_size': results['control']['sample_size'] + results['treatment']['sample_size']
        })
        
        # Визуализация
        render_experiment_results(results)
        
        # Сохранение результатов
        if st.button("💾 Сохранить результаты"):
            for group_name, data in [('control', results['control']), ('treatment', results['treatment'])]:
                result = ExperimentResult(
                    experiment_id=exp_id,
                    group_name=group_name,
                    sample_size=data['sample_size'],
                    events_count=data['events'],
                    metric_value=data['conversion_rate'],
                    p_value=results['statistics']['p_value'],
                    confidence_interval=data['confidence_interval'],
                    is_significant=results['statistics']['is_significant'],
                    relative_diff=results['statistics']['relative_difference'],
                    absolute_diff=results['statistics']['absolute_difference']
                )
                manager.save_result(result)
            
            st.success("Результаты сохранены!")


def render_settings():
    """Страница настроек"""
    st.markdown("# ⚙️ Настройки")
    st.markdown("Конфигурация платформы")
    
    st.markdown("### Подключение к базе данных")
    
    with st.form("db_config_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            db_type = st.selectbox(
                "Тип БД",
                options=["sqlite", "postgresql", "mysql"],
                index=0
            )
            db_host = st.text_input("Хост", value="localhost")
            db_port = st.text_input("Порт", value="5432")
        
        with col2:
            db_name = st.text_input("Имя базы данных", value="")
            db_user = st.text_input("Пользователь", value="")
            db_password = st.text_input("Пароль", type="password", value="")
        
        submitted = st.form_submit_button("💾 Сохранить и подключиться")
        
        if submitted:
            # Сохранение в .env (в реальном приложении)
            st.success(f"Настройки сохранены! Тип БД: {db_type}")
            st.info("Для применения настроек перезапустите приложение")
    
    st.markdown("---")
    
    st.markdown("### Статистические настройки")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_alpha = st.selectbox(
            "Уровень значимости (alpha)",
            options=[0.01, 0.05, 0.1],
            index=1
        )
    
    with col2:
        new_min_sample = st.number_input(
            "Минимальный размер выборки по умолчанию",
            min_value=10,
            value=100
        )
    
    if st.button("Сохранить статистические настройки"):
        st.success("Настройки сохранены!")
    
    st.markdown("---")
    
    st.markdown("### О системе")
    st.info("""
    **TwoSigma** — платформа для A/B тестирования
    
    Версия: 0.1.0
    
    Аналог платформы TriSigma от Авито
    
    **Технологии:**
    - Streamlit — UI
    - SQLAlchemy — работа с БД
    - SciPy — статистический анализ
    - Plotly — визуализация
    """)


# ==================== Главное приложение ====================

def main():
    """Главная функция приложения"""
    # Инициализация
    init_app()
    
    # Рендеринг сайдбара
    page = render_sidebar()
    page_key = get_page_key(page)
    
    # Роутинг по страницам
    pages = {
        "dashboard": render_dashboard,
        "experiments": render_experiments,
        "new_experiment": render_new_experiment,
        "feature_flags": render_feature_flags,
        "analytics": render_analytics,
        "settings": render_settings
    }
    
    # Отображение выбранной страницы
    render_func = pages.get(page_key, render_dashboard)
    render_func()


if __name__ == "__main__":
    main()
