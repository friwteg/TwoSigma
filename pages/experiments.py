"""
Страница управления экспериментами
"""
import streamlit as st
from database import get_db, get_user_experiments, get_user_datasets, get_user_metrics


def show_experiments_page():
    """Страница управления экспериментами"""

    # Проверяем, находимся ли мы на странице создания эксперимента
    if st.session_state.get("show_create_experiment_page", False):
        show_create_experiment_page()
        return

    # Заголовок с кнопкой создания
    col_title, col_button = st.columns([3, 1])
    with col_title:
        st.title("🧪 Эксперименты")
    with col_button:
        if st.button("➕ Создать эксперимент", use_container_width=True, type="primary"):
            st.session_state["show_create_experiment_page"] = True
            st.rerun()

    # Получаем эксперименты пользователя
    db = get_db()
    experiments = get_user_experiments(db, st.session_state.user['id'])
    db.close()

    # Показываем уведомление о создании эксперимента
    if st.session_state.get("experiment_created"):
        st.success(f"✅ Эксперимент '{st.session_state.get('experiment_created_name')}' успешно создан!", icon="🎉")
        # Сбрасываем флаг после показа
        del st.session_state["experiment_created"]
        del st.session_state["experiment_created_name"]

    if not experiments:
        st.info("У вас пока нет созданных экспериментов. Нажмите кнопку 'Создать эксперимент' для создания первого эксперимента.")
    else:
        # Сортируем эксперименты по ID в обратном порядке (новые сверху)
        experiments_sorted = sorted(experiments, key=lambda x: x.id, reverse=True)

        for experiment in experiments_sorted:
            # Компактная карточка эксперимента
            with st.container():
                col_icon, col_name, col_status, col_view, col_delete = st.columns([0.3, 3, 1.5, 1, 1])

                with col_icon:
                    st.markdown("### 🧪")

                with col_name:
                    st.markdown(f"### {experiment.name}")

                with col_status:
                    status_emoji = {
                        "draft": "📝",
                        "running": "▶️",
                        "completed": "✅",
                        "archived": "📦"
                    }
                    status_text = {
                        "draft": "Черновик",
                        "running": "Активен",
                        "completed": "Завершён",
                        "archived": "Архив"
                    }
                    st.markdown(
                        f"<div style='padding-top: 8px; color: #666;'>{status_emoji.get(experiment.status, '❓')} {status_text.get(experiment.status, experiment.status)}</div>",
                        unsafe_allow_html=True
                    )

                with col_view:
                    # Кнопка для просмотра результатов
                    is_expanded = st.session_state.get(f"show_experiment_{experiment.id}", False)
                    button_label = "🔼 Скрыть" if is_expanded else "📊 Результаты"

                    if st.button(button_label, key=f"view_{experiment.id}", use_container_width=True):
                        if is_expanded:
                            st.session_state[f"show_experiment_{experiment.id}"] = False
                        else:
                            st.session_state[f"show_experiment_{experiment.id}"] = True
                        st.rerun()

                with col_delete:
                    # Кнопка удаления с подтверждением
                    if st.button("🗑️", key=f"delete_experiment_{experiment.id}", use_container_width=True, help="Удалить эксперимент"):
                        st.session_state[f"confirm_delete_exp_{experiment.id}"] = True

                # Подтверждение удаления
                if st.session_state.get(f"confirm_delete_exp_{experiment.id}", False):
                    st.warning("⚠️ Вы уверены, что хотите удалить этот эксперимент?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ Да, удалить", key=f"confirm_yes_exp_{experiment.id}", use_container_width=True):
                            try:
                                from database import delete_experiment
                                import os

                                db = get_db()
                                # Удаляем специальный датасет эксперимента
                                if experiment.experiment_dataset_path and os.path.exists(experiment.experiment_dataset_path):
                                    os.remove(experiment.experiment_dataset_path)

                                delete_experiment(db, experiment.id, st.session_state.user['id'])
                                db.close()

                                # Очищаем все флаги
                                if f"show_experiment_{experiment.id}" in st.session_state:
                                    del st.session_state[f"show_experiment_{experiment.id}"]
                                if f"confirm_delete_exp_{experiment.id}" in st.session_state:
                                    del st.session_state[f"confirm_delete_exp_{experiment.id}"]

                                st.toast("✓ Эксперимент удалён", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.toast(f"❌ Ошибка удаления: {str(e)}", icon="❌")
                    with col_no:
                        if st.button("❌ Отмена", key=f"confirm_no_exp_{experiment.id}", use_container_width=True):
                            st.session_state[f"confirm_delete_exp_{experiment.id}"] = False
                            st.rerun()

            # Информация об эксперименте
            st.markdown(f"**Описание:** {experiment.description or 'Нет описания'}")
            st.markdown(
                f"**Период:** {experiment.start_date.strftime('%d.%m.%Y')} - {experiment.end_date.strftime('%d.%m.%Y')} | "
                f"**Тип теста:** {experiment.test_type} | "
                f"**Создан:** {experiment.created_at.strftime('%d.%m.%Y %H:%M')}"
            )

            # Просмотр результатов (показывается только если развернуто)
            if st.session_state.get(f"show_experiment_{experiment.id}", False):
                # Показываем информацию о группах и кнопки экспорта
                from database import get_experiment_groups, get_experiment_users

                db = get_db()
                groups = get_experiment_groups(db, experiment.id)

                st.markdown("#### Группы эксперимента")

                for group in groups:
                    col_group_name, col_count, col_export = st.columns([2, 1, 2])

                    with col_group_name:
                        control_badge = " (контроль)" if group.is_control else ""
                        st.markdown(f"**Группа {group.group_name}{control_badge}**")

                    with col_count:
                        st.markdown(f"{group.user_count:,} пользователей")

                    with col_export:
                        # Кнопка копирования ID в буфер
                        if st.button(f"📋 Скопировать ID группы {group.group_name}", key=f"copy_{experiment.id}_{group.group_name}"):
                            # Получаем пользователей группы
                            exp_users = get_experiment_users(db, experiment.id, group.group_name)
                            user_ids = [str(eu.user_id) for eu in exp_users]
                            user_ids_str = ','.join(user_ids)

                            # Копируем в буфер через JavaScript
                            st.write(f"```\n{user_ids_str}\n```")
                            st.success(f"✓ Скопируйте ID из поля выше")

                # Кнопка скачивания всех групп
                st.markdown("---")
                if st.button("📥 Скачать все группы (CSV)", key=f"download_all_{experiment.id}", use_container_width=True):
                    import pandas as pd
                    import io

                    # Получаем всех пользователей
                    all_users = get_experiment_users(db, experiment.id)

                    # Создаем DataFrame
                    export_data = [
                        {'user_id': eu.user_id, 'group': eu.group_name}
                        for eu in all_users
                    ]
                    export_df = pd.DataFrame(export_data)

                    # Конвертируем в CSV
                    csv_buffer = io.StringIO()
                    export_df.to_csv(csv_buffer, index=False)
                    csv_str = csv_buffer.getvalue()

                    # Кнопка скачивания
                    st.download_button(
                        label="💾 Скачать CSV",
                        data=csv_str,
                        file_name=f"experiment_{experiment.id}_groups.csv",
                        mime="text/csv",
                        key=f"download_btn_{experiment.id}"
                    )

                db.close()

                st.markdown("---")

                # Кнопка расчета результатов
                if st.button("🔬 Рассчитать результаты", key=f"calculate_{experiment.id}", use_container_width=True, type="primary"):
                    try:
                        from components.experiment_calculator import calculate_experiment_results
                        from database import get_metric_by_id, save_experiment_results

                        with st.spinner("Расчет результатов..."):
                            db = get_db()
                            metric = get_metric_by_id(db, experiment.metric_id, st.session_state.user['id'])

                            # Рассчитываем результаты
                            results = calculate_experiment_results(experiment, metric)

                            # Проверяем, полные ли данные
                            experiment_incomplete = results.get('_experiment_incomplete', False)
                            incomplete_warning = results.get('_incomplete_warning', '')

                            # Сохраняем результаты в БД (пропускаем служебные ключи)
                            for group_name, result in results.items():
                                # Пропускаем служебные ключи
                                if group_name.startswith('_'):
                                    continue

                                import json
                                results_data = {
                                    'group_name': group_name,
                                    'metric_value': result['metric_value'],
                                    'sample_size': result['sample_size'],
                                    'std_dev': result['std_dev'],
                                    'confidence_interval_lower': result['confidence_interval_lower'],
                                    'confidence_interval_upper': result['confidence_interval_upper'],
                                    'p_value': result.get('p_value'),
                                    'test_type': result.get('test_type', experiment.test_type),
                                    'is_significant': result.get('is_significant', False),
                                    'warning': result.get('warning'),
                                    'time_series_data': json.dumps(result.get('time_series', {}))
                                }
                                save_experiment_results(db, experiment.id, results_data)

                            db.close()

                            # Сохраняем результаты в session_state для отображения
                            st.session_state[f"results_{experiment.id}"] = results

                            # Показываем соответствующее сообщение
                            if experiment_incomplete:
                                st.warning(incomplete_warning)
                            else:
                                st.success("✅ Результаты рассчитаны!")
                            st.rerun()

                    except Exception as e:
                        st.error(f"Ошибка расчета результатов: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

                # Отображение результатов (если они есть)
                if st.session_state.get(f"results_{experiment.id}"):
                    from components.experiment_display import display_experiment_results
                    from database import get_metric_by_id

                    db = get_db()
                    metric = get_metric_by_id(db, experiment.metric_id, st.session_state.user['id'])
                    db.close()

                    results = st.session_state[f"results_{experiment.id}"]
                    display_experiment_results(results, metric.name, experiment.test_type)

                    # Кнопка завершения эксперимента
                    st.markdown("---")
                    if experiment.status != 'completed':
                        if st.button("✅ Закончить эксперимент", type="primary", key=f"complete_{experiment.id}"):
                            from database import update_experiment_status
                            db = get_db()
                            try:
                                update_experiment_status(db, experiment.id, st.session_state.user['id'], 'completed')
                                st.success("Эксперимент успешно завершен!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Ошибка при завершении эксперимента: {str(e)}")
                            finally:
                                db.close()
                    else:
                        st.info("✅ Эксперимент завершен")

            st.divider()


def show_create_experiment_page():
    """Страница создания нового эксперимента"""

    # Заголовок с кнопкой возврата
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Назад", use_container_width=True):
            st.session_state["show_create_experiment_page"] = False
            st.rerun()
    with col_title:
        st.title("Создать новый эксперимент")

    # Получаем датасеты и метрики пользователя
    db = get_db()
    datasets = get_user_datasets(db, st.session_state.user['id'])
    metrics = get_user_metrics(db, st.session_state.user['id'])
    db.close()

    if not datasets:
        st.warning("Сначала загрузите датасет в разделе 'Датасеты'")
        if st.button("Перейти к датасетам"):
            st.session_state.current_page = "Датасеты"
            st.session_state["show_create_experiment_page"] = False
            st.rerun()
        return

    if not metrics:
        st.warning("Сначала создайте метрику в разделе 'Метрики'")
        if st.button("Перейти к метрикам"):
            st.session_state.current_page = "Метрики"
            st.session_state["show_create_experiment_page"] = False
            st.rerun()
        return

    st.divider()

    # Показываем форму создания эксперимента
    from components.experiment_creator import show_experiment_creator
    show_experiment_creator(datasets, metrics)
