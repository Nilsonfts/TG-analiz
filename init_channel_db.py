#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных для аналитики каналов
"""
import asyncio
import logging
import os
import random
import sys
from datetime import datetime, timedelta

# Добавляем путь к модулям
sys.path.append(os.path.dirname(__file__))

from channel_analytics import ChannelAnalytics
from config import Config
from database import Database

# Создаем экземпляр конфигурации
config = Config()
DB_CONFIG = {"database_url": config.database_url}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_channel_db():
    """Инициализация БД и добавление тестовых данных для канала"""

    try:
        # Подключение к БД
        db = Database(
            f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )
        await db.init_db()
        logger.info("✅ База данных подключена")

        # Инициализация аналитики каналов
        analytics = ChannelAnalytics(db)
        logger.info("✅ Аналитика каналов инициализирована")

        # Добавление тестового канала
        channel_id = -1001234567890
        channel_title = "Тестовый Канал Analytics"
        channel_username = "test_analytics_channel"

        try:
            await analytics.add_or_update_channel(
                channel_id=channel_id,
                title=channel_title,
                username=channel_username,
                subscribers_count=15000,
                description="Тестовый канал для демонстрации аналитики",
            )
            logger.info(f"✅ Канал {channel_title} добавлен")
        except Exception as e:
            logger.warning(f"Канал уже существует или ошибка: {e}")

        # Генерация тестовых данных за последние 30 дней
        logger.info("📊 Генерирую тестовые данные...")

        base_date = datetime.now() - timedelta(days=30)

        for day in range(30):
            date = base_date + timedelta(days=day)

            # Имитация роста подписчиков
            base_gain = 50 + random.randint(-20, 40)
            base_loss = 10 + random.randint(0, 15)

            # Выходные дни - меньше активности
            if date.weekday() >= 5:  # Суббота/воскресенье
                base_gain = int(base_gain * 0.7)
                base_loss = int(base_loss * 0.8)

            try:
                await analytics.record_subscriber_change(
                    channel_id=channel_id,
                    subscribers_gained=base_gain,
                    subscribers_lost=base_loss,
                    date=date.date(),
                )
            except Exception as e:
                logger.debug(f"Данные за {date.date()} уже существуют: {e}")

            # Генерация почасовых данных для последних 7 дней
            if day >= 23:  # Последние 7 дней
                for hour in range(24):
                    # Имитация активности по часам (пики в 12:00, 18:00, 21:00)
                    base_views = 100
                    if hour in [12, 18, 21]:
                        base_views *= 1.5
                    elif hour in [8, 9, 19, 20, 22]:
                        base_views *= 1.2
                    elif hour in [0, 1, 2, 3, 4, 5]:
                        base_views *= 0.3

                    views = int(base_views + random.randint(-30, 50))
                    story_views = int(views * 0.3 + random.randint(-10, 20))

                    try:
                        await analytics.record_hourly_views(
                            channel_id=channel_id,
                            hour_of_day=hour,
                            total_views=max(0, views),
                            story_views=max(0, story_views),
                            date=date.date(),
                        )
                    except Exception:
                        logger.debug(
                            f"Почасовые данные за {date.date()} {hour}:00 уже существуют"
                        )

        # Генерация данных о источниках трафика
        traffic_sources = [
            ("url", 0.25),
            ("search", 0.20),
            ("groups", 0.20),
            ("channels", 0.25),
            ("private_chats", 0.10),
        ]

        total_monthly_subs = 1200
        total_monthly_views = 50000

        for source, percentage in traffic_sources:
            subs = int(total_monthly_subs * percentage)
            views = int(total_monthly_views * percentage)

            try:
                await analytics.record_traffic_source(
                    channel_id=channel_id,
                    source_type=source,
                    subscribers_count=subs,
                    views_count=views,
                    date=datetime.now().date(),
                )
            except Exception as e:
                logger.debug(f"Данные о трафике {source} уже существуют: {e}")

        logger.info("✅ Тестовые данные успешно сгенерированы")

        # Проверка данных
        summary = await analytics.get_channel_summary(channel_id)
        if summary:
            logger.info("📊 Сводка канала:")
            logger.info(f"   • Название: {summary.get('title')}")
            logger.info(f"   • Подписчики: {summary.get('subscribers_count'):,}")
            logger.info(f"   • Рост за период: {summary.get('subscriber_growth'):+d}")
            logger.info(f"   • Общие просмотры: {summary.get('total_views'):,}")

        logger.info("🎉 Инициализация завершена успешно!")

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(init_channel_db())
        print("\n✅ База данных для аналитики каналов готова к работе!")
        print("🚀 Теперь можно запускать бота: python main.py")
    except KeyboardInterrupt:
        print("\n❌ Инициализация прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)
