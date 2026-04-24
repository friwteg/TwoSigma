"""
Модуль для расчета метрик
"""
import pandas as pd
import sqlite3
from utils.period_helper import assign_period, format_period_result, calculate_metric_by_period


def calculate_metric(df: pd.DataFrame, metric_type: str, config: dict):
    """Расчет метрики на основе конфигурации"""

    if metric_type == "template":
        # Шаблонные метрики
        template = config.get("template")
        fields = config.get("fields", {})
        if template == "revenue":
            # Revenue = SUM(выручка)
            revenue_field = fields.get("revenue")
            date_field = fields.get("date_field")
            time_window = fields.get("time_window")

            # Если есть временное измерение, строим график
            if date_field and time_window:
                df[date_field] = pd.to_datetime(df[date_field])

                if time_window == "day":
                    df['period'] = df[date_field].dt.date
                elif time_window == "week":
                    df['period'] = df[date_field].dt.to_period('W')
                elif time_window == "month":
                    df['period'] = df[date_field].dt.to_period('M')

                # Группируем и сортируем по периоду
                grouped = df.groupby('period').agg({
                    revenue_field: 'sum'
                }).sort_index()

                periods = grouped.index.tolist()
                values = grouped[revenue_field].tolist()

                if not values:
                    return {
                        'periods': [],
                        'values': [],
                        'mean': 0,
                        'total': 0,
                        'count': 0,
                        'no_data': True
                    }

                return {
                    'periods': periods,
                    'values': values,
                    'mean': sum(values) / len(values) if values else 0,
                    'total': sum(values),
                    'count': len(values)
                }
            else:
                # Без временного измерения - одно значение
                return f"{df[revenue_field].sum():,.2f}"

        elif template == "aov":
            # AOV = Выручка / Количество заказов
            revenue_field = fields.get("revenue")
            order_id_field = fields.get("order_id")
            date_field = fields.get("date_field")
            time_window = fields.get("time_window")

            # Если есть временное измерение, строим график
            if date_field and time_window:
                df[date_field] = pd.to_datetime(df[date_field])

                if time_window == "day":
                    df['period'] = df[date_field].dt.date
                    df['period_str'] = df[date_field].dt.strftime('%d.%m.%Y')
                elif time_window == "week":
                    df['period'] = df[date_field].dt.to_period('W')
                    df['period_str'] = df['period'].apply(lambda x: f"{x.start_time.strftime('%d.%m')} - {x.end_time.strftime('%d.%m')}")
                elif time_window == "month":
                    df['period'] = df[date_field].dt.to_period('M')
                    df['period_str'] = df[date_field].dt.strftime('%m.%Y')

                # Группируем и сортируем по периоду
                grouped_data = []
                for period in sorted(df['period'].unique()):
                    period_df = df[df['period'] == period]
                    total_revenue = period_df[revenue_field].sum()
                    total_orders = period_df[order_id_field].nunique()
                    aov = total_revenue / total_orders if total_orders > 0 else 0
                    grouped_data.append((period, aov))

                periods = [x[0] for x in grouped_data]
                values = [x[1] for x in grouped_data]

                if not values:
                    return {
                        'periods': [],
                        'values': [],
                        'mean': 0,
                        'total': 0,
                        'count': 0,
                        'no_data': True
                    }

                return {
                    'periods': periods,
                    'values': values,
                    'mean': sum(values) / len(values) if values else 0,
                    'total': sum(values),
                    'count': len(values)
                }
            else:
                # Без временного измерения - одно значение
                total_revenue = df[revenue_field].sum()
                total_orders = df[order_id_field].nunique()
                return f"{total_revenue / total_orders if total_orders > 0 else 0:,.2f}"

        elif template == "arpu":
            # ARPU = Выручка / Количество уникальных пользователей
            revenue_field = fields.get("revenue")
            user_id_field = fields.get("user_id")
            date_field = fields.get("date_field")
            time_window = fields.get("time_window")

            # Если есть временное измерение, строим график
            if date_field and time_window:
                df[date_field] = pd.to_datetime(df[date_field])

                if time_window == "day":
                    df['period'] = df[date_field].dt.date
                    df['period_str'] = df[date_field].dt.strftime('%d.%m.%Y')
                elif time_window == "week":
                    df['period'] = df[date_field].dt.to_period('W')
                    df['period_str'] = df['period'].apply(lambda x: f"{x.start_time.strftime('%d.%m')} - {x.end_time.strftime('%d.%m')}")
                elif time_window == "month":
                    df['period'] = df[date_field].dt.to_period('M')
                    df['period_str'] = df[date_field].dt.strftime('%m.%Y')

                # Группируем и сортируем по периоду
                grouped_data = []
                for period in sorted(df['period'].unique()):
                    period_df = df[df['period'] == period]
                    total_revenue = period_df[revenue_field].sum()
                    total_users = period_df[user_id_field].nunique()
                    arpu = total_revenue / total_users if total_users > 0 else 0
                    grouped_data.append((period, arpu))

                periods = [x[0] for x in grouped_data]
                values = [x[1] for x in grouped_data]

                if not values:
                    return {
                        'periods': [],
                        'values': [],
                        'mean': 0,
                        'total': 0,
                        'count': 0,
                        'no_data': True
                    }

                return {
                    'periods': periods,
                    'values': values,
                    'mean': sum(values) / len(values) if values else 0,
                    'total': sum(values),
                    'count': len(values)
                }
            else:
                # Без временного измерения - одно значение
                total_revenue = df[revenue_field].sum()
                total_users = df[user_id_field].nunique()
                return f"{total_revenue / total_users if total_users > 0 else 0:,.2f}"

        elif template == "conversion":
            # Conversion Rate = (Конверсии / Всего) × 100%
            status_field = fields.get("status")
            success_value = fields.get("success_value")
            date_field = fields.get("date_field")
            time_window = fields.get("time_window")

            # Если есть временное измерение, строим график
            if date_field and time_window:
                df[date_field] = pd.to_datetime(df[date_field])

                if time_window == "day":
                    df['period'] = df[date_field].dt.date
                    df['period_str'] = df[date_field].dt.strftime('%d.%m.%Y')
                elif time_window == "week":
                    df['period'] = df[date_field].dt.to_period('W')
                    df['period_str'] = df['period'].apply(lambda x: f"{x.start_time.strftime('%d.%m')} - {x.end_time.strftime('%d.%m')}")
                elif time_window == "month":
                    df['period'] = df[date_field].dt.to_period('M')
                    df['period_str'] = df[date_field].dt.strftime('%m.%Y')

                # Группируем и сортируем по периоду
                grouped_data = []
                for period in sorted(df['period'].unique()):
                    period_df = df[df['period'] == period]
                    total = len(period_df)
                    conversions = len(period_df[period_df[status_field] == success_value])
                    conversion_rate = (conversions / total * 100) if total > 0 else 0
                    grouped_data.append((period, conversion_rate))

                periods = [x[0] for x in grouped_data]
                values = [x[1] for x in grouped_data]

                if not values:
                    return {
                        'periods': [],
                        'values': [],
                        'mean': 0,
                        'total': 0,
                        'count': 0,
                        'no_data': True
                    }

                return {
                    'periods': periods,
                    'values': values,
                    'mean': sum(values) / len(values) if values else 0,
                    'total': sum(values),
                    'count': len(values)
                }
            else:
                # Без временного измерения - одно значение
                total = len(df)
                conversions = len(df[df[status_field] == success_value])
                return f"{(conversions / total * 100) if total > 0 else 0:.2f}%"

        elif template == "gmv":
            # GMV = SUM(сумма заказа)
            order_amount_field = fields.get("order_amount")
            date_field = fields.get("date_field")
            time_window = fields.get("time_window")

            # Если есть временное измерение, строим график
            if date_field and time_window:
                df[date_field] = pd.to_datetime(df[date_field])

                if time_window == "day":
                    df['period'] = df[date_field].dt.date
                    df['period_str'] = df[date_field].dt.strftime('%d.%m.%Y')
                elif time_window == "week":
                    df['period'] = df[date_field].dt.to_period('W')
                    df['period_str'] = df['period'].apply(lambda x: f"{x.start_time.strftime('%d.%m')} - {x.end_time.strftime('%d.%m')}")
                elif time_window == "month":
                    df['period'] = df[date_field].dt.to_period('M')
                    df['period_str'] = df[date_field].dt.strftime('%m.%Y')

                # Группируем и сортируем по периоду
                grouped = df.groupby('period').agg({
                    order_amount_field: 'sum'
                }).sort_index()

                periods = grouped.index.tolist()
                values = grouped[order_amount_field].tolist()

                if not values:
                    return {
                        'periods': [],
                        'values': [],
                        'mean': 0,
                        'total': 0,
                        'count': 0,
                        'no_data': True
                    }

                return {
                    'periods': periods,
                    'values': values,
                    'mean': sum(values) / len(values) if values else 0,
                    'total': sum(values),
                    'count': len(values)
                }
            else:
                # Без временного измерения - одно значение
                return f"{df[order_amount_field].sum():,.2f}"

        elif template == "ltv":
            # LTV = SUM(выручка) на пользователя (среднее)
            revenue_field = fields.get("revenue")
            user_id_field = fields.get("user_id")
            date_field = fields.get("date_field")
            time_window = fields.get("time_window")

            # Если есть временное измерение, строим график
            if date_field and time_window:
                df[date_field] = pd.to_datetime(df[date_field])

                if time_window == "day":
                    df['period'] = df[date_field].dt.date
                    df['period_str'] = df[date_field].dt.strftime('%d.%m.%Y')
                elif time_window == "week":
                    df['period'] = df[date_field].dt.to_period('W')
                    df['period_str'] = df['period'].apply(lambda x: f"{x.start_time.strftime('%d.%m')} - {x.end_time.strftime('%d.%m')}")
                elif time_window == "month":
                    df['period'] = df[date_field].dt.to_period('M')
                    df['period_str'] = df[date_field].dt.strftime('%m.%Y')

                # Группируем и сортируем по периоду
                grouped_data = []
                for period in sorted(df['period'].unique()):
                    period_df = df[df['period'] == period]
                    user_revenue = period_df.groupby(user_id_field)[revenue_field].sum()
                    avg_ltv = user_revenue.mean()
                    grouped_data.append((period, avg_ltv))

                periods = [x[0] for x in grouped_data]
                values = [x[1] for x in grouped_data]

                if not values:
                    return {
                        'periods': [],
                        'values': [],
                        'mean': 0,
                        'total': 0,
                        'count': 0,
                        'no_data': True
                    }

                return {
                    'periods': periods,
                    'values': values,
                    'mean': sum(values) / len(values) if values else 0,
                    'total': sum(values),
                    'count': len(values)
                }
            else:
                # Без временного измерения - одно значение
                user_revenue = df.groupby(user_id_field)[revenue_field].sum()
                return f"{user_revenue.mean():,.2f}"

        elif template == "cac":
            # CAC = Расходы на маркетинг / Количество новых клиентов
            marketing_cost_field = fields.get("marketing_cost")
            user_id_field = fields.get("user_id")
            date_field = fields.get("date_field")
            time_window = fields.get("time_window")

            # Если есть временное измерение, строим график
            if date_field and time_window:
                df[date_field] = pd.to_datetime(df[date_field])

                if time_window == "day":
                    df['period'] = df[date_field].dt.date
                    df['period_str'] = df[date_field].dt.strftime('%d.%m.%Y')
                elif time_window == "week":
                    df['period'] = df[date_field].dt.to_period('W')
                    df['period_str'] = df['period'].apply(lambda x: f"{x.start_time.strftime('%d.%m')} - {x.end_time.strftime('%d.%m')}")
                elif time_window == "month":
                    df['period'] = df[date_field].dt.to_period('M')
                    df['period_str'] = df[date_field].dt.strftime('%m.%Y')

                # Группируем и сортируем по периоду
                grouped_data = []
                for period in sorted(df['period'].unique()):
                    period_df = df[df['period'] == period]
                    total_cost = period_df[marketing_cost_field].sum()
                    total_customers = period_df[user_id_field].nunique()
                    cac = total_cost / total_customers if total_customers > 0 else 0
                    grouped_data.append((period, cac))

                periods = [x[0] for x in grouped_data]
                values = [x[1] for x in grouped_data]

                if not values:
                    return {
                        'periods': [],
                        'values': [],
                        'mean': 0,
                        'total': 0,
                        'count': 0,
                        'no_data': True
                    }

                return {
                    'periods': periods,
                    'values': values,
                    'mean': sum(values) / len(values) if values else 0,
                    'total': sum(values),
                    'count': len(values)
                }
            else:
                # Без временного измерения - одно значение
                total_cost = df[marketing_cost_field].sum()
                total_customers = df[user_id_field].nunique()
                return f"{total_cost / total_customers if total_customers > 0 else 0:,.2f}"

        elif template == "dau":
            # DAU = COUNT(DISTINCT user_id) по дням (всегда по дням)
            user_id_field = fields.get("user_id")
            date_field = fields.get("date")

            df[date_field] = pd.to_datetime(df[date_field])
            df['period'] = df[date_field].dt.date

            # Группируем и сортируем по периоду
            grouped = df.groupby('period').agg({
                user_id_field: 'nunique'
            }).sort_index()

            periods = grouped.index.tolist()
            values = grouped[user_id_field].tolist()

            if not values:
                return {
                    'periods': [],
                    'values': [],
                    'mean': 0,
                    'total': 0,
                    'count': 0,
                    'no_data': True
                }

            return {
                'periods': periods,
                'values': values,
                'mean': sum(values) / len(values) if values else 0,
                'total': sum(values),
                'count': len(values)
            }

        elif template == "wau":
            # WAU = COUNT(DISTINCT user_id) по неделям (всегда по неделям)
            user_id_field = fields.get("user_id")
            date_field = fields.get("date")

            df[date_field] = pd.to_datetime(df[date_field])
            df['period'] = df[date_field].dt.to_period('W')

            # Группируем и сортируем по периоду
            grouped = df.groupby('period').agg({
                user_id_field: 'nunique'
            }).sort_index()

            periods = grouped.index.tolist()
            values = grouped[user_id_field].tolist()

            if not values:
                return {
                    'periods': [],
                    'values': [],
                    'mean': 0,
                    'total': 0,
                    'count': 0,
                    'no_data': True
                }

            return {
                'periods': periods,
                'values': values,
                'mean': sum(values) / len(values) if values else 0,
                'total': sum(values),
                'count': len(values)
            }

        elif template == "mau":
            # MAU = COUNT(DISTINCT user_id) по месяцам (всегда по месяцам)
            user_id_field = fields.get("user_id")
            date_field = fields.get("date")

            df[date_field] = pd.to_datetime(df[date_field])
            df['period'] = df[date_field].dt.to_period('M')

            # Группируем и сортируем по периоду
            grouped = df.groupby('period').agg({
                user_id_field: 'nunique'
            }).sort_index()

            periods = grouped.index.tolist()
            values = grouped[user_id_field].tolist()

            if not values:
                return {
                    'periods': [],
                    'values': [],
                    'mean': 0,
                    'total': 0,
                    'count': 0,
                    'no_data': True
                }

            return {
                'periods': periods,
                'values': values,
                'mean': sum(values) / len(values) if values else 0,
                'total': sum(values),
                'count': len(values)
            }

        elif template == "retention":
            # Retention Rate = процент пользователей, вернувшихся после первого визита
            user_id_field = fields.get("user_id")
            date_field = fields.get("date")
            new_user_field = fields.get("new_user_field")
            new_user_value = fields.get("new_user_value")
            retention_day = fields.get("retention_day", 7)  # День для проверки (Day 7 по умолчанию)
            time_window = fields.get("time_window", "day")

            df[date_field] = pd.to_datetime(df[date_field])

            # Определяем новых пользователей
            # Вариант 1: Если есть поле с признаком
            if new_user_field and new_user_value:
                # Приводим типы для корректного сравнения
                try:
                    # Пробуем преобразовать в число
                    new_user_value_converted = pd.to_numeric(new_user_value)
                    df[new_user_field] = pd.to_numeric(df[new_user_field], errors='coerce')
                except:
                    # Если не получилось, оставляем как строку
                    new_user_value_converted = str(new_user_value)
                    df[new_user_field] = df[new_user_field].astype(str)

                # Находим строки с новыми пользователями
                new_users_df = df[df[new_user_field] == new_user_value_converted].copy()

                # Получаем список ID новых пользователей
                new_user_ids = new_users_df[user_id_field].unique()

                # Берем ПЕРВУЮ активность каждого нового пользователя из ВСЕГО датасета
                all_activities_of_new_users = df[df[user_id_field].isin(new_user_ids)].copy()
                new_users_cohorts = all_activities_of_new_users.groupby(user_id_field)[date_field].min().reset_index()
                new_users_cohorts.columns = [user_id_field, 'cohort_date']
            else:
                # Вариант 2: Автоматически - первая активность = новый пользователь
                new_users_cohorts = df.groupby(user_id_field)[date_field].min().reset_index()
                new_users_cohorts.columns = [user_id_field, 'cohort_date']

            # Максимальная дата для корректного расчета
            max_date = df[date_field].max()
            max_relevant_date = max_date - pd.Timedelta(days=retention_day)

            # Фильтруем когорты, для которых можно посчитать retention_day
            new_users_cohorts = new_users_cohorts[new_users_cohorts['cohort_date'] <= max_relevant_date].copy()

            if len(new_users_cohorts) == 0:
                return {
                    'periods': [],
                    'values': [],
                    'mean': 0,
                    'total': 0,
                    'count': 0,
                    'no_data': True
                }

            # Джойним к основному датафрейму
            df_with_cohort = df.merge(new_users_cohorts, on=user_id_field, how='inner')

            # Вычисляем день относительно когорты
            df_with_cohort['days_since_cohort'] = (
                df_with_cohort[date_field] - df_with_cohort['cohort_date']
            ).dt.days

            # Находим пользователей, активных в пределах retention_day дней
            active_on_day_n = df_with_cohort[
                (df_with_cohort['days_since_cohort'] > 0) &
                (df_with_cohort['days_since_cohort'] <= retention_day)
            ][[user_id_field, 'cohort_date']].drop_duplicates()

            # Присваиваем периоды ПЕРЕД группировкой
            if time_window == "day":
                new_users_cohorts['period'] = new_users_cohorts['cohort_date'].dt.date
                new_users_cohorts['period_str'] = new_users_cohorts['cohort_date'].dt.strftime('%d.%m.%Y')
                active_on_day_n['period'] = active_on_day_n['cohort_date'].dt.date
            elif time_window == "week":
                new_users_cohorts['period'] = new_users_cohorts['cohort_date'].dt.to_period('W')
                new_users_cohorts['period_str'] = new_users_cohorts['period'].apply(
                    lambda x: f"{x.start_time.strftime('%d.%m')} - {x.end_time.strftime('%d.%m')}"
                )
                active_on_day_n['period'] = active_on_day_n['cohort_date'].dt.to_period('W')
            elif time_window == "month":
                new_users_cohorts['period'] = new_users_cohorts['cohort_date'].dt.to_period('M')
                new_users_cohorts['period_str'] = new_users_cohorts['cohort_date'].dt.strftime('%m.%Y')
                active_on_day_n['period'] = active_on_day_n['cohort_date'].dt.to_period('M')

            # Считаем новых пользователей по периодам
            new_by_period = new_users_cohorts.groupby(['period', 'period_str']).agg({
                user_id_field: 'count'
            }).reset_index()
            new_by_period.columns = ['period', 'period_str', 'new_users']

            # Считаем активных в Day N по периодам
            active_by_period = active_on_day_n.groupby('period').agg({
                user_id_field: 'count'
            }).reset_index()
            active_by_period.columns = ['period', 'active_users']

            # Джойним
            retention_by_period = new_by_period.merge(active_by_period, on='period', how='left')
            retention_by_period['active_users'] = retention_by_period['active_users'].fillna(0)
            retention_by_period['retention_rate'] = (
                retention_by_period['active_users'] / retention_by_period['new_users'] * 100
            )

            # Сортируем по периоду для правильного порядка на графике
            retention_by_period = retention_by_period.sort_values('period').reset_index(drop=True)

            # Format for output - возвращаем period (даты), а не period_str (строки)
            periods = retention_by_period['period'].tolist()
            values = retention_by_period['retention_rate'].tolist()

            return {
                'periods': periods,
                'values': values,
                'mean': retention_by_period['retention_rate'].mean() if len(values) > 0 else 0,
                'total': retention_by_period['retention_rate'].sum(),
                'count': len(periods)
            }

        elif template == "churn":
            # Churn Rate = процент пользователей, которые перестали быть активными
            user_id_field = fields.get("user_id")
            date_field = fields.get("date")
            churn_days = fields.get("churn_days", 30)
            time_window = fields.get("time_window", "day")

            df[date_field] = pd.to_datetime(df[date_field])

            # Get unique user-date combinations
            df_unique = df[[user_id_field, date_field]].drop_duplicates(keep='first').copy()
            df_unique = df_unique.sort_values([user_id_field, date_field]).reset_index(drop=True)

            # Find next event for each user
            df_unique['next_event_date'] = df_unique.groupby(user_id_field)[date_field].shift(-1)
            df_unique['days_till_next_event'] = (
                df_unique['next_event_date'] - df_unique[date_field]
            ).dt.days

            # Calculate max relevant date
            max_date = df[date_field].max()
            max_relevant_date = max_date - pd.Timedelta(days=churn_days)

            # Assign periods BEFORE filtering (CRITICAL!)
            if time_window == "day":
                df_unique['period'] = df_unique[date_field].dt.date
                df_unique['period_str'] = df_unique[date_field].dt.strftime('%d.%m.%Y')
            elif time_window == "week":
                df_unique['period'] = df_unique[date_field].dt.to_period('W')
                df_unique['period_str'] = df_unique['period'].apply(
                    lambda x: f"{x.start_time.strftime('%d.%m')} - {x.end_time.strftime('%d.%m')}"
                )
            elif time_window == "month":
                df_unique['period'] = df_unique[date_field].dt.to_period('M')
                df_unique['period_str'] = df_unique[date_field].dt.strftime('%m.%Y')

            # Filter to relevant dates
            df_relevant = df_unique[df_unique[date_field] <= max_relevant_date].copy()

            # Check for empty data
            if len(df_relevant) == 0:
                return {
                    'periods': [],
                    'values': [],
                    'mean': 0,
                    'total': 0,
                    'count': 0,
                    'no_data': True
                }

            # Mark churned users (vectorized - faster than lambda)
            df_relevant['is_churned'] = (
                df_relevant['days_till_next_event'].isna() |
                (df_relevant['days_till_next_event'] >= churn_days)
            ).astype(int)

            # Aggregate by period - CRITICAL: need to count unique users per period
            # First, take one row per user per period (in case user active multiple times)
            df_period_user = df_relevant.groupby(['period', 'period_str', user_id_field]).agg({
                'is_churned': 'max'  # If churnedу in any activity in period, mark as churned
            }).reset_index()

            # Then aggregate by period
            churn_by_period = df_period_user.groupby(['period', 'period_str']).agg({
                'is_churned': 'sum',
                user_id_field: 'count'
            }).reset_index()
            churn_by_period.columns = ['period', 'period_str', 'churned', 'total']
            churn_by_period['churn_rate'] = (
                churn_by_period['churned'] / churn_by_period['total'] * 100
            )

            # Сортируем по периоду для правильного порядка на графике
            churn_by_period = churn_by_period.sort_values('period').reset_index(drop=True)

            # Format for output - возвращаем period (даты), а не period_str (строки)
            periods = churn_by_period['period'].tolist()
            values = churn_by_period['churn_rate'].tolist()

            return {
                'periods': periods,
                'values': values,
                'mean': churn_by_period['churn_rate'].mean() if len(values) > 0 else 0,
                'total': churn_by_period['churn_rate'].sum(),
                'count': len(periods)
            }

        else:
            return "Неизвестный шаблон метрики"

    elif metric_type == "sql":
        # SQL-метрика
        import sqlite3

        try:
            # Создаем временную БД в памяти
            conn = sqlite3.connect(':memory:')
            df.to_sql('df', conn, index=False, if_exists='replace')

            # Выполняем запрос
            result_df = pd.read_sql_query(config["sql_query"], conn)
            conn.close()

            # Если результат - одна ячейка, возвращаем её значение
            if result_df.shape == (1, 1):
                return f"{result_df.iloc[0, 0]:,.2f}"
            else:
                # Возвращаем всю таблицу как строку
                return result_df.to_string(index=False)

        except Exception as e:
            return f"Ошибка выполнения SQL: {str(e)}"

    else:
        return "Неизвестный тип метрики"

    return "Не удалось рассчитать"
