"""
Страница управления датасетами
"""
import streamlit as st
import pandas as pd
import os
from pathlib import Path
from database import get_db, create_dataset, get_user_datasets, delete_dataset, update_dataset_file
from models import DatasetCreate
from config import UPLOAD_DIR, CSV_SEPARATORS, CSV_ENCODINGS, MAX_ROWS_PREVIEW

# Директория для загруженных файлов
UPLOAD_DIR.mkdir(exist_ok=True)


def show_datasets_page():
    """Страница управления датасетами"""
    st.title("📁 Мои датасеты")

    # Загрузка нового файла
    st.subheader("Загрузить новый датасет")

    with st.form("upload_form"):
        dataset_name = st.text_input("Название датасета")
        uploaded_file = st.file_uploader("Выберите CSV файл", type=['csv', 'tsv', 'txt'])

        col1, col2 = st.columns(2)
        with col1:
            separator = st.selectbox(
                "Разделитель",
                options=list(CSV_SEPARATORS.keys()),
                format_func=lambda x: CSV_SEPARATORS[x]
            )
        with col2:
            encoding = st.selectbox(
                "Кодировка",
                options=list(CSV_ENCODINGS.keys()),
                format_func=lambda x: CSV_ENCODINGS[x]
            )

        submit = st.form_submit_button("Загрузить")

        if submit:
            if not dataset_name:
                st.error("Введите название датасета!")
            elif not uploaded_file:
                st.error("Выберите файл для загрузки!")
            else:
                try:
                    # Читаем CSV с указанными параметрами
                    df = pd.read_csv(uploaded_file, sep=separator, encoding=encoding)

                    # Сохраняем файл
                    user_dir = UPLOAD_DIR / str(st.session_state.user['id'])
                    user_dir.mkdir(exist_ok=True)

                    filepath = user_dir / uploaded_file.name
                    df.to_csv(filepath, index=False, encoding='utf-8')

                    # Сохраняем информацию в БД
                    db = get_db()
                    dataset_data = DatasetCreate(
                        name=dataset_name,
                        filename=uploaded_file.name,
                        filepath=str(filepath),
                        rows_count=len(df),
                        columns_count=len(df.columns)
                    )
                    create_dataset(db, dataset_data, st.session_state.user['id'])
                    db.close()

                    st.success(f"Датасет '{dataset_name}' успешно загружен!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except UnicodeDecodeError:
                    st.error(f"Ошибка кодировки! Попробуйте выбрать другую кодировку.")
                except pd.errors.ParserError:
                    st.error(f"Ошибка парсинга! Проверьте правильность выбранного разделителя.")
                except Exception as e:
                    st.error(f"Ошибка при загрузке файла: {str(e)}")

    st.divider()

    # Список загруженных датасетов
    st.subheader("Загруженные датасеты")

    db = get_db()
    datasets = get_user_datasets(db, st.session_state.user['id'])
    db.close()

    if not datasets:
        st.info("У вас пока нет загруженных датасетов")
    else:
        for dataset in datasets:
            col_name, col_view, col_update, col_delete = st.columns([3, 1, 1, 1])

            with col_name:
                st.markdown(f"### 📊 {dataset.name}")

            with col_view:
                if st.button("Просмотр", key=f"view_{dataset.id}"):
                    st.session_state[f"show_dataset_{dataset.id}"] = True

            with col_update:
                if st.button("Обновить", key=f"update_{dataset.id}"):
                    st.session_state[f"show_update_{dataset.id}"] = True

            with col_delete:
                if st.button("Удалить", key=f"delete_{dataset.id}"):
                    try:
                        # Удаляем файл
                        if os.path.exists(dataset.filepath):
                            os.remove(dataset.filepath)

                        # Удаляем запись из БД
                        db = get_db()
                        delete_dataset(db, dataset.id, st.session_state.user['id'])
                        db.close()

                        st.success("Датасет удалён!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка удаления: {str(e)}")

            # Информация о датасете
            st.markdown(f"**Файл:** {dataset.filename}")

            # Показываем дату последнего обновления
            last_updated_str = dataset.last_updated.strftime('%d.%m.%Y %H:%M') if dataset.last_updated else dataset.created_at.strftime('%d.%m.%Y %H:%M')
            st.markdown(
                f"**Строк:** {dataset.rows_count:,} | "
                f"**Столбцов:** {dataset.columns_count} | "
                f"**Загружен:** {dataset.created_at.strftime('%d.%m.%Y %H:%M')} | "
                f"**Обновлён:** {last_updated_str}"
            )

            # Форма обновления датасета
            if st.session_state.get(f"show_update_{dataset.id}", False):
                with st.form(f"update_form_{dataset.id}"):
                    st.markdown("#### Обновить датасет")
                    updated_file = st.file_uploader("Выберите новый CSV файл", type=['csv', 'tsv', 'txt'], key=f"file_{dataset.id}")

                    col1, col2 = st.columns(2)
                    with col1:
                        separator = st.selectbox(
                            "Разделитель",
                            options=list(CSV_SEPARATORS.keys()),
                            format_func=lambda x: CSV_SEPARATORS[x],
                            key=f"sep_{dataset.id}"
                        )
                    with col2:
                        encoding = st.selectbox(
                            "Кодировка",
                            options=list(CSV_ENCODINGS.keys()),
                            format_func=lambda x: CSV_ENCODINGS[x],
                            key=f"enc_{dataset.id}"
                        )

                    col_submit, col_cancel = st.columns(2)
                    with col_submit:
                        submit_update = st.form_submit_button("Обновить", use_container_width=True)
                    with col_cancel:
                        cancel_update = st.form_submit_button("Отмена", use_container_width=True)

                    if cancel_update:
                        st.session_state[f"show_update_{dataset.id}"] = False
                        st.rerun()

                    if submit_update:
                        if not updated_file:
                            st.error("Выберите файл для загрузки!")
                        else:
                            try:
                                # Читаем новый CSV
                                df = pd.read_csv(updated_file, sep=separator, encoding=encoding)

                                # Сохраняем файл (заменяем старый)
                                df.to_csv(dataset.filepath, index=False, encoding='utf-8')

                                # Обновляем информацию в БД
                                db = get_db()
                                update_dataset_file(db, dataset.id, st.session_state.user['id'],
                                                   dataset.filepath, len(df), len(df.columns))

                                # Обновляем специальные датасеты для активных экспериментов
                                from database import get_active_experiments_for_dataset, get_experiment_users, get_metric_by_id
                                from utils.experiment_dataset_helper import update_experiment_dataset

                                active_experiments = get_active_experiments_for_dataset(db, dataset.id)

                                if active_experiments:
                                    st.info(f"Обновление {len(active_experiments)} активных экспериментов...")

                                    for exp in active_experiments:
                                        try:
                                            # Получаем маппинг пользователей в группы
                                            exp_users = get_experiment_users(db, exp.id)
                                            user_groups = {eu.user_id: eu.group_name for eu in exp_users}

                                            # Получаем поля метрики
                                            metric = get_metric_by_id(db, exp.metric_id, st.session_state.user['id'])
                                            from utils.experiment_dataset_helper import get_metric_fields
                                            metric_fields = get_metric_fields(metric.config)

                                            # Обновляем специальный датасет эксперимента
                                            update_experiment_dataset(
                                                exp.id, df, exp.user_id_field, exp.date_field,
                                                user_groups, metric_fields, exp.experiment_dataset_path
                                            )

                                        except Exception as e:
                                            st.warning(f"Не удалось обновить эксперимент '{exp.name}': {str(e)}")

                                db.close()

                                st.success(f"Датасет '{dataset.name}' успешно обновлён!")
                                st.session_state[f"show_update_{dataset.id}"] = False
                                st.rerun()
                            except UnicodeDecodeError:
                                st.error(f"Ошибка кодировки! Попробуйте выбрать другую кодировку.")
                            except pd.errors.ParserError:
                                st.error(f"Ошибка парсинга! Проверьте правильность выбранного разделителя.")
                            except Exception as e:
                                st.error(f"Ошибка при обновлении файла: {str(e)}")

            # Показываем данные если нажата кнопка просмотра
            if st.session_state.get(f"show_dataset_{dataset.id}", False):
                try:
                    df = pd.read_csv(dataset.filepath)
                    st.dataframe(df.head(MAX_ROWS_PREVIEW), use_container_width=True)
                except Exception as e:
                    st.error(f"Ошибка чтения файла: {str(e)}")

            st.divider()

