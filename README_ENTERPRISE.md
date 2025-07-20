# 📊 Telegram Channel Analytics Bot - Enterprise Edition

Профессиональный бот для аналитики Telegram каналов с автоматическим сбором данных, генерацией отчетов и системой уведомлений.

## 🌟 Ключевые возможности

### 📈 Продвинутая аналитика
- **Многоканальный мониторинг** - отслеживание неограниченного количества каналов одновременно
- **Исторические данные** - полная история изменений с возможностью анализа трендов за любой период
- **Внешние API** - интеграция с Telemetr.me и TGStat.ru для расширенной аналитики
- **Качественные метрики** - оценка качества контента и engagement rate

### 📊 Визуализация и отчеты
- **Matplotlib графики** - профессиональные диаграммы роста, просмотров, сравнений
- **CSV экспорт** - полная выгрузка данных в удобном формате для анализа
- **Автоматические отчеты** - еженедельные и месячные сводки по email/Telegram
- **Сравнительная аналитика** - анализ нескольких каналов одновременно

### 🔔 Умная система уведомлений
- **Адаптивные алерты** - уведомления о резких изменениях метрик (±20% подписчики, -30% просмотры)
- **Настраиваемые пороги** - гибкие условия срабатывания для каждого канала
- **Мониторинг активности** - уведомления о длительном отсутствии новых постов

### 🔄 Автоматизация
- **APScheduler** - надежный планировщик для сбора данных и отчетов
- **Многоуровневые задачи** - ежедневные (02:00), еженедельные (пн 04:00), месячные (1 число 05:00)
- **Восстановление после ошибок** - автоматическая повторная обработка неудачных задач

## 🏗️ Техническая архитектура

### Современный стек технологий
- **Python 3.11+** с async/await
- **aiogram 3.x** для современного API Telegram Bot
- **SQLAlchemy 2.x** с асинхронным ORM
- **PostgreSQL** с JSONB для гибкого хранения
- **Alembic** для миграций базы данных
- **Pydantic** для валидации конфигурации

### Модульная архитектура

```
src/
├── config.py              # Centralized Pydantic settings
├── bot/                   # Main bot class with dependency injection
├── collectors/            # Data collection abstraction
│   ├── __init__.py       # BaseCollector with rate limiting
│   ├── telegram_collector.py    # Telethon integration
│   └── external_collectors.py   # Telemetr.me, TGStat.ru APIs
├── db/                    # Database layer
│   └── models.py         # SQLAlchemy models with proper relations
├── scheduler/             # Task automation
│   └── __init__.py       # APScheduler service with health monitoring
├── reports/               # Report generation
│   ├── __init__.py       # Matplotlib chart generation
│   └── export_service.py # Multi-format data export
├── handlers/              # Bot command handlers
│   └── __init__.py       # Admin-protected commands with inline keyboards
└── utils/
    └── logging.py        # Structured JSON logging with Sentry
```

## 🚀 Production Deployment

### Railway (Рекомендуется)

1. **Подключение репозитория**
   ```bash
   git clone <your-repo>
   cd TG-analiz
   ```

2. **Конфигурация переменных окружения**
   ```env
   # Essential
   BOT_TOKEN=1234567890:AAEhBOweik9-w7h_SeHh5JdwFhxQ6t5T6q4
   ADMIN_USER_ID=123456789
   DATABASE_URL=postgresql://user:pass@hostname:5432/db
   
   # Telegram API (для сбора данных)
   API_ID=12345678
   API_HASH=abcdef1234567890abcdef1234567890
   
   # External APIs (опционально)
   TELEMETR_API_KEY=your_telemetr_key_here
   TGSTAT_API_KEY=your_tgstat_key_here
   
   # Monitoring (опционально)
   SENTRY_DSN=https://your-sentry-dsn
   
   # Scheduler timing (UTC)
   DAILY_COLLECT_HOUR=2
   WEEKLY_REPORT_DAY=0
   MONTHLY_REPORT_DAY=1
   ```

3. **Инициализация**
   ```bash
   python scripts/init_db.py
   python main_v2.py
   ```

### Docker развертывание

```bash
# Build and run
docker build -t telegram-analytics .
docker run -d --env-file .env -p 8000:8000 telegram-analytics

# Health check
curl http://localhost:8000/health
```

## 🔧 Администрирование

### Команды администратора

- `/add @channel_username` - Добавить канал в мониторинг
- `/remove @channel_username` - Удалить канал
- `/list` - Показать все отслеживаемые каналы
- `/stats @channel_username [days]` - Детальная статистика за период
- `/export @channel_username [csv|json]` - Экспорт данных
- `/health` - Проверка состояния системы
- `/alerts configure` - Настройка уведомлений

### Пользовательские команды

- `/start` - Приветствие и инструкции
- `/help` - Справка по доступным командам

## 📊 База данных

### Оптимизированная схема

```sql
-- Каналы с метаданными
channels (id, channel_id, username, title, description, is_active, created_at)

-- Ежедневная статистика подписчиков
members_daily (channel_id, date, members_count, members_growth, collected_at)

-- Ежедневная статистика просмотров  
views_daily (channel_id, date, avg_views, total_views, posts_count, collected_at)

-- Детали постов для глубокой аналитики
posts (channel_id, post_id, text, views, forwards, reactions, posted_at)

-- Упоминания между каналами
mentions (channel_id, mentioned_channel_id, post_id, mention_type, context)

-- Оценки качества контента
quality_scores (channel_id, date, quality_score, engagement_rate, activity_score)

-- Очередь отчетов для асинхронной обработки
reports_queue (report_type, channel_id, parameters, status, result_data)
```

### Индексы для производительности

- Составные индексы на `(channel_id, date)` для быстрых временных запросов
- B-tree индексы на `username`, `is_active`, `status`
- Уникальные ограничения для предотвращения дублирования

## 🔄 Автоматизация и мониторинг

### Расписание задач

| Задача | Время | Описание |
|--------|--------|----------|
| **Ежедневный сбор** | 02:00 UTC | Подписчики, просмотры, новые посты |
| **Еженедельные отчеты** | Пн 04:00 UTC | Сводка изменений за неделю |
| **Месячная аналитика** | 1 число 05:00 UTC | Подробный анализ за месяц |
| **Проверка алертов** | Каждые 30 мин | Мониторинг пороговых значений |

### Health Monitoring

- **HTTP endpoint** `/health` для Railway health checks
- **Structured logging** с JSON форматом для ELK стека
- **Sentry integration** для автоматического уведомления об ошибках
- **Graceful shutdown** с proper cleanup ресурсов

## 🔒 Безопасность и надежность

### Контроль доступа
- **Admin-only commands** проверка ADMIN_USER_ID для всех управляющих команд
- **Input validation** Pydantic схемы для всех входящих данных
- **SQL injection protection** через SQLAlchemy ORM

### Rate Limiting и устойчивость
- **API rate limiting** автоматические задержки для Telegram API
- **Retry mechanisms** экспоненциальная задержка при временных ошибках
- **Circuit breaker** отключение недоступных внешних API
- **Graceful error handling** логирование ошибок без остановки бота

### Backup и восстановление
- **Database migrations** версионированные изменения схемы через Alembic
- **Configuration as code** все настройки в environment variables
- **Stateless design** возможность быстрого перезапуска

## 📈 Performance и масштабирование

### Оптимизации
- **Bulk inserts** для ежедневного импорта данных
- **Connection pooling** эффективное использование PostgreSQL
- **Lazy loading** отложенная загрузка связанных объектов
- **Query optimization** использование индексов и EXPLAIN планов

### Метрики производительности
- Время сбора данных с одного канала: ~2-3 секунды
- Пропускная способность: 100+ каналов за 5 минут
- Размер БД: ~1MB на канал в месяц исторических данных
- Memory footprint: ~50-100MB RAM

## 🧪 Разработка и тестирование

### Локальная разработка

```bash
# Setup
git clone <repo>
cd TG-analiz
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Environment
cp .env.example .env
# Edit .env with your values

# Database
python scripts/init_db.py
alembic upgrade head

# Run
python main_v2.py
```

### Тестирование

```bash
# Unit tests
pytest tests/ -v

# With coverage
pytest --cov=src tests/

# Integration tests
pytest tests/integration/ -v
```

### Добавление новых коллекторов

```python
from src.collectors import BaseCollector

class NewAPICollector(BaseCollector):
    def __init__(self, api_key: str):
        super().__init__(rate_limit=1.0)  # 1 request per second
        self.api_key = api_key
    
    async def collect_channel_data(self, channel_id: int) -> Dict:
        async with self.rate_limiter:
            # Your collection logic
            return {"members": 1000, "views": 5000}
```

### Создание миграций

```bash
# После изменения моделей
alembic revision --autogenerate -m "Add new analytics table"

# Применение
alembic upgrade head

# Откат
alembic downgrade -1
```

## 🎯 Production Checklist

### Перед развертыванием

- [ ] ✅ Переменные окружения настроены
- [ ] ✅ База данных PostgreSQL создана
- [ ] ✅ Telegram Bot токен получен от @BotFather
- [ ] ✅ API credentials получены от my.telegram.org
- [ ] ✅ ADMIN_USER_ID указан корректно
- [ ] ✅ Health endpoint отвечает на `/health`

### После развертывания

- [ ] ✅ Добавить первый канал: `/add @channel_name`
- [ ] ✅ Проверить сбор данных: `/stats @channel_name`
- [ ] ✅ Настроить алерты: `/alerts configure`
- [ ] ✅ Мониторить логи в Sentry/Railway

## 🆘 Troubleshooting

### Частые проблемы

**"Database connection failed"**
- Проверьте DATABASE_URL формат: `postgresql://user:pass@host:port/db`
- Убедитесь что PostgreSQL доступен

**"Bot API error 401"**
- Проверьте BOT_TOKEN от @BotFather
- Убедитесь что бот не заблокирован

**"Channel not found"**
- Добавьте бота в канал как администратора
- Используйте точный @username канала

**"Telethon auth error"**
- Проверьте API_ID и API_HASH от my.telegram.org
- Пройдите авторизацию в Telethon session

### Логи и диагностика

```bash
# Railway logs
railway logs --tail

# Local logs
tail -f logs/bot.log

# Health check
curl https://your-app.railway.app/health
```

## 📞 Поддержка

- **GitHub Issues** для багов и feature requests
- **Logs monitoring** автоматическое уведомление через Sentry
- **Health monitoring** Railway automatic restarts при падении
- **Documentation** полная документация в коде

---

**🚀 Enterprise-ready Telegram Analytics Bot**

*Разработано для стабильной работы 24/7 с полным логированием, мониторингом и автоматическим восстановлением.*
