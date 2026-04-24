"""
Компонент для создания эксперимента
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import (get_db, get_user_datasets, get_user_metrics, create_experiment,
                     create_experiment_group, create_experiment_users_bulk,
                     update_experiment_dataset_path, update_experiment_status, get_metric_by_id)
from models import ExperimentCreate
from utils.ab_test_helper import split_users
from utils.experiment_dataset_helper import get_metric_fields, create_experiment_dataset, save_experiment_dataset


def show_experiment_creator(datasets, metrics):
    """Форма создания эксперимента"""

    st.markdown("### Основная информация")

    # Название и описание
    experiment_name = st.text_input(
        "Название эксперимента",
        placeholder="Например: Тест новой кнопки оформления заказа",
        key="exp_name"
    )

    experiment_description = st.text_area(
        "Описание (опционально)",
        placeholder="Краткое описание цели эксперимента",
        key="exp_desc"
    )

    st.divider()

    # Выбор датасета
    st.markdown("### Датасет и метрика")

    dataset_options = {ds.id: f"{ds.name} ({ds.rows_count:,} строк)" for ds in datasets}
    selected_dataset_id = st.selectbox(
        "Выберите датасет",
        options=list(dataset_options.keys()),
        format_func=lambda x: dataset_options[x],
        key="exp_dataset"
    )

    selected_dataset = next(ds for ds in datasets if ds.id == selected_dataset_id)

    # Выбор метрики
    metric_options = {m.id: f"{m.name}" for m in metrics if m.dataset_id == selected_dataset_id}

    if not metric_options:
        st.warning("Для выбранного датасета нет созданных метрик. Сначала создайте метрику в разделе 'Метрики'.")
        return

    selected_metric_id = st.selectbox(
        "Выберите метрику для оценки",
        options=list(metric_options.keys()),
        format_func=lambda x: metric_options[x],
        key="exp_metric"
    )

    st.divider()

    # Тип теста
    st.markdown("### Статистический тест")

    test_type = st.selectbox(
        "Выберите тип теста",
        options=["t-test", "z-test", "chi-square"],
        help="t-test - для непрерывных метрик (Revenue, AOV), z-test - для пропорций (Conversion)",
        key="exp_test_type"
    )

    st.divider()

    # Период эксперимента
    st.markdown("### Период эксперимента")

    col_start, col_end = st.columns(2)
    with col_start:
        start_date = st.date_input(
            "Дата начала",
            value=datetime.now().date() - timedelta(days=30),
            key="exp_start_date"
        )
    with col_end:
        end_date = st.date_input(
            "Дата окончания",
            value=datetime.now().date(),
            key="exp_end_date"
        )

    if start_date >= end_date:
        st.error("Дата окончания должна быть позже даты начала!")
        return

    st.divider()

    # Поля из датасета
    st.markdown("### Поля датасета")

    # Загружаем колонки датасета
    try:
        df_preview = pd.read_csv(selected_dataset.filepath, nrows=5)
        columns = df_preview.columns.tolist()
    except Exception as e:
        st.error(f"Ошибка чтения датасета: {str(e)}")
        return

    col_user, col_date = st.columns(2)
    with col_user:
        user_id_field = st.selectbox(
            "Поле с ID пользователя",
            options=columns,
            key="exp_user_id_field"
        )
    with col_date:
        date_field = st.selectbox(
            "Поле с датой",
            options=columns,
            key="exp_date_field"
        )

    st.divider()

    # Кнопка создания
    if st.button("✅ Создать эксперимент", use_container_width=True, type="primary"):
        if not experiment_name:
            st.error("Введите название эксперимента!")
            return

        try:
            with st.spinner("Создание эксперимента..."):
                # Загружаем полный датасет
                df = pd.read_csv(selected_dataset.filepath)

                # Получаем уникальных пользователей
                unique_users = df[user_id_field].unique().tolist()

                # Фиксируем 2 группы: control и test
                num_groups = 2
                control_group = 'control'

                if len(unique_users) < 2:
                    st.error(f"Недостаточно пользователей для разбиения на группы!")
                    return

                # Разбиваем на группы (control и test)
                user_groups_dict = split_users(unique_users, num_groups=num_groups, seed=42)

                # Переименовываем группы A -> control, B -> test
                user_groups_dict = {
                    'control': user_groups_dict['A'],
                    'test': user_groups_dict['B']
                }

                # Создаем маппинг user_id → group_name
                user_to_group = {}
                for group_name, users in user_groups_dict.items():
                    for user_id in users:
                        user_to_group[user_id] = group_name

                # Получаем конфигурацию метрики
                db = get_db()
                metric = get_metric_by_id(db, selected_metric_id, st.session_state.user['id'])

                # Определяем поля для метрики
                metric_fields = get_metric_fields(metric.config)

                # Создаем эксперимент в БД
                experiment_data = ExperimentCreate(
                    name=experiment_name,
                    description=experiment_description,
                    dataset_id=selected_dataset_id,
                    metric_id=selected_metric_id,
                    test_type=test_type,
                    user_id_field=user_id_field,
                    date_field=date_field,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.max.time()),
                    config={
                        'num_groups': 2,
                        'control_group': 'control',
                        'seed': 42,
                        'metric_fields': metric_fields
                    }
                )

                experiment = create_experiment(db, experiment_data, st.session_state.user['id'])

                # Создаем группы
                for group_name, users in user_groups_dict.items():
                    is_control = (group_name == control_group)
                    create_experiment_group(
                        db, experiment.id, group_name, is_control,
                        user_count=len(users),
                        description=f"Группа {group_name}"
                    )

                # Сохраняем пользователей в эксперимент (массово)
                users_data = [(str(uid), gname) for gname, users in user_groups_dict.items() for uid in users]
                create_experiment_users_bulk(db, experiment.id, users_data)

                # Создаем специальный датасет эксперимента
                df_experiment = create_experiment_dataset(
                    experiment.id, df, user_id_field, date_field,
                    user_to_group, metric_fields
                )

                # Сохраняем специальный датасет
                experiment_path = save_experiment_dataset(df_experiment, experiment.id)

                # Обновляем путь к датасету и статус
                update_experiment_dataset_path(db, experiment.id, st.session_state.user['id'], experiment_path)
                update_experiment_status(db, experiment.id, st.session_state.user['id'], 'running')

                db.close()

                # Устанавливаем флаг для показа уведомления
                st.session_state["experiment_created"] = True
                st.session_state["experiment_created_name"] = experiment_name
                st.session_state["show_create_experiment_page"] = False

                # Сохраняем информацию о группах для экспорта
                st.session_state[f"experiment_{experiment.id}_groups"] = user_groups_dict

                st.success(f"✅ Эксперимент '{experiment_name}' успешно создан!")
                st.rerun()

        except Exception as e:
            st.error(f"Ошибка создания эксперимента: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
