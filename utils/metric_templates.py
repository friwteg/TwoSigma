"""
Шаблоны метрик для визуального конструктора

Содержит предопределенные шаблоны популярных метрик для A/B тестирования
и продуктовой аналитики. Каждый шаблон включает:
- Название и описание метрики
- Формулу расчета
- Иконку для UI
- Список необходимых полей из датасета
"""

# ============================================================================
# МЕТРИКИ ВЫРУЧКИ И МОНЕТИЗАЦИИ
# ============================================================================

REVENUE_METRICS = {
    "revenue": {
        "name": "Revenue (Выручка)",
        "description": "Общая выручка за период",
        "formula": "SUM(выручка)",
        "icon": "💵",
        "fields": {
            "revenue": {"label": "Поле с выручкой", "type": "numeric"}
        }
    },
    "aov": {
        "name": "AOV (Average Order Value)",
        "description": "Средний чек - средняя сумма одного заказа",
        "formula": "Выручка / Количество заказов",
        "icon": "💰",
        "fields": {
            "revenue": {"label": "Поле с выручкой", "type": "numeric"},
            "order_id": {"label": "Поле с ID заказа", "type": "any"}
        }
    },
    "arpu": {
        "name": "ARPU (Average Revenue Per User)",
        "description": "Средний доход на пользователя",
        "formula": "Выручка / Количество уникальных пользователей",
        "icon": "👤",
        "fields": {
            "revenue": {"label": "Поле с выручкой", "type": "numeric"},
            "user_id": {"label": "Поле с ID пользователя", "type": "any"}
        }
    },
    "ltv": {
        "name": "LTV (Lifetime Value)",
        "description": "Пожизненная ценность клиента - общая выручка от клиента за все время",
        "formula": "SUM(выручка) на пользователя",
        "icon": "💎",
        "fields": {
            "revenue": {"label": "Поле с выручкой", "type": "numeric"},
            "user_id": {"label": "Поле с ID пользователя", "type": "any"}
        }
    },
    "gmv": {
        "name": "GMV (Gross Merchandise Value)",
        "description": "Валовая стоимость товаров - общая сумма продаж (включая отмененные)",
        "formula": "SUM(сумма заказа)",
        "icon": "📊",
        "fields": {
            "order_amount": {"label": "Поле с суммой заказа", "type": "numeric"}
        }
    },
    "cac": {
        "name": "CAC (Customer Acquisition Cost)",
        "description": "Стоимость привлечения одного клиента",
        "formula": "Расходы на маркетинг / Количество новых клиентов",
        "icon": "💸",
        "fields": {
            "marketing_cost": {"label": "Поле с расходами на маркетинг", "type": "numeric"},
            "user_id": {"label": "Поле с ID нового клиента", "type": "any"}
        }
    }
}

# ============================================================================
# МЕТРИКИ ВОВЛЕЧЕННОСТИ И АКТИВНОСТИ
# ============================================================================

ENGAGEMENT_METRICS = {
    "dau": {
        "name": "DAU (Daily Active Users)",
        "description": "Количество уникальных активных пользователей в день",
        "formula": "COUNT(DISTINCT user_id) по дням",
        "icon": "📅",
        "fields": {
            "user_id": {"label": "Поле с ID пользователя", "type": "any"},
            "date": {"label": "Поле с датой", "type": "date"}
        }
    },
    "wau": {
        "name": "WAU (Weekly Active Users)",
        "description": "Количество уникальных активных пользователей в неделю",
        "formula": "COUNT(DISTINCT user_id) по неделям",
        "icon": "📆",
        "fields": {
            "user_id": {"label": "Поле с ID пользователя", "type": "any"},
            "date": {"label": "Поле с датой", "type": "date"}
        }
    },
    "mau": {
        "name": "MAU (Monthly Active Users)",
        "description": "Количество уникальных активных пользователей в месяц",
        "formula": "COUNT(DISTINCT user_id) по месяцам",
        "icon": "📊",
        "fields": {
            "user_id": {"label": "Поле с ID пользователя", "type": "any"},
            "date": {"label": "Поле с датой", "type": "date"}
        }
    }
}

# ============================================================================
# МЕТРИКИ КОНВЕРСИИ И УДЕРЖАНИЯ
# ============================================================================

CONVERSION_METRICS = {
    "conversion": {
        "name": "Conversion Rate",
        "description": "Конверсия - процент пользователей, совершивших целевое действие",
        "formula": "(Количество конверсий / Общее количество) × 100%",
        "icon": "🎯",
        "fields": {
            "status": {"label": "Поле со статусом", "type": "any"}
        }
    },
    "retention": {
        "name": "Retention Rate",
        "description": "Процент пользователей, вернувшихся после первого визита (Day N Retention)",
        "formula": "(Вернувшиеся пользователи / Новые пользователи) × 100%",
        "icon": "🔄",
        "fields": {
            "user_id": {"label": "Поле с ID пользователя", "type": "any"},
            "date": {"label": "Поле с датой активности", "type": "date"},
            "new_user_field": {"label": "Поле с признаком нового пользователя", "type": "any"}
        }
    },
    "churn": {
        "name": "Churn Rate",
        "description": "Процент пользователей, которые перестали пользоваться продуктом",
        "formula": "(Ушедшие пользователи / Всего пользователей) × 100%",
        "icon": "📉",
        "fields": {
            "user_id": {"label": "Поле с ID пользователя", "type": "any"},
            "date": {"label": "Поле с датой активности", "type": "date"}
        }
    }
}

# ============================================================================
# ОБЪЕДИНЕННЫЙ СЛОВАРЬ ВСЕХ МЕТРИК
# ============================================================================

METRIC_TEMPLATES = {
    **REVENUE_METRICS,
    **ENGAGEMENT_METRICS,
    **CONVERSION_METRICS
}

# Словарь для быстрого получения названия метрики по ключу
TEMPLATE_NAMES = {key: value["name"] for key, value in METRIC_TEMPLATES.items()}

