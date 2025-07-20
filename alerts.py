"""
Система алертов для Telegram Analytics Bot
Отслеживает всплески и аномалии в активности
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Alert:
    """Модель алерта"""
    alert_type: str
    group_id: int
    group_name: str
    message: str
    value: float
    threshold: float
    timestamp: datetime

class AlertSystem:
    """Система мониторинга и алертов"""
    
    def __init__(self, db, bot):
        self.db = db
        self.bot = bot
        self.alert_settings = {
            'viral_multiplier': 3.0,  # Всплеск активности в N раз
            'drop_threshold': 0.5,    # Падение активности до N от нормы
            'new_users_threshold': 10, # Количество новых пользователей за час
            'spam_threshold': 50,     # Количество сообщений от одного пользователя за час
        }
        self.last_checks = {}
    
    async def check_activity_spikes(self, group_id: int, group_name: str) -> List[Alert]:
        """Проверка всплесков активности"""
        alerts = []
        
        try:
            # Получаем данные за последние 2 часа и за предыдущие 24 часа для сравнения
            now = datetime.now()
            last_hour = now - timedelta(hours=1)
            last_24h = now - timedelta(hours=24)
            
            # Активность за последний час
            recent_stats = await self.db.get_daily_stats(group_id, now)
            recent_count = recent_stats.get('messages_count', 0)
            
            # Средняя активность за предыдущие 24 часа (по часам)
            hourly_data = await self.db.get_hourly_activity(group_id, days=1)
            if hourly_data:
                avg_hourly = sum(hourly_data.values()) / max(len(hourly_data), 1)
                
                # Проверяем всплеск активности
                if recent_count > avg_hourly * self.alert_settings['viral_multiplier']:
                    alerts.append(Alert(
                        alert_type="viral_spike",
                        group_id=group_id,
                        group_name=group_name,
                        message=f"🔥 ВСПЛЕСК АКТИВНОСТИ!\n📈 {recent_count} сообщений за час\n📊 Обычно: {avg_hourly:.1f}/час\n🚀 Превышение в {recent_count/avg_hourly:.1f}x раз!",
                        value=recent_count,
                        threshold=avg_hourly * self.alert_settings['viral_multiplier'],
                        timestamp=now
                    ))
                
                # Проверяем падение активности
                elif recent_count < avg_hourly * self.alert_settings['drop_threshold'] and avg_hourly > 5:
                    alerts.append(Alert(
                        alert_type="activity_drop",
                        group_id=group_id,
                        group_name=group_name,
                        message=f"📉 ПАДЕНИЕ АКТИВНОСТИ\n📈 {recent_count} сообщений за час\n📊 Обычно: {avg_hourly:.1f}/час\n⚠️ Активность упала на {((avg_hourly - recent_count) / avg_hourly * 100):.1f}%",
                        value=recent_count,
                        threshold=avg_hourly * self.alert_settings['drop_threshold'],
                        timestamp=now
                    ))
            
        except Exception as e:
            logger.error(f"Ошибка проверки активности для группы {group_id}: {e}")
        
        return alerts
    
    async def check_new_users_spike(self, group_id: int, group_name: str) -> List[Alert]:
        """Проверка всплеска новых пользователей"""
        alerts = []
        
        try:
            # Получаем новых пользователей за последний час
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            
            # Здесь можно добавить запрос к БД для подсчёта новых пользователей
            # Пока что упрощённая версия
            
        except Exception as e:
            logger.error(f"Ошибка проверки новых пользователей для группы {group_id}: {e}")
        
        return alerts
    
    async def check_spam_activity(self, group_id: int, group_name: str) -> List[Alert]:
        """Проверка на спам активность"""
        alerts = []
        
        try:
            # Получаем топ пользователей за последний час
            now = datetime.now()
            stats = await self.db.get_daily_stats(group_id, now)
            
            if stats and stats.get('top_users'):
                for user in stats['top_users'][:3]:  # Проверяем топ-3
                    message_count = user.get('message_count', 0)
                    if message_count > self.alert_settings['spam_threshold']:
                        username = user.get('username', f"User {user.get('user_id', 'Unknown')}")
                        alerts.append(Alert(
                            alert_type="spam_detection",
                            group_id=group_id,
                            group_name=group_name,
                            message=f"🚨 ПОДОЗРЕНИЕ НА СПАМ\n👤 Пользователь: @{username}\n📊 {message_count} сообщений за час\n⚠️ Превышен лимит {self.alert_settings['spam_threshold']} сообщений/час",
                            value=message_count,
                            threshold=self.alert_settings['spam_threshold'],
                            timestamp=now
                        ))
            
        except Exception as e:
            logger.error(f"Ошибка проверки спама для группы {group_id}: {e}")
        
        return alerts
    
    async def check_all_groups(self) -> List[Alert]:
        """Проверка всех активных групп"""
        all_alerts = []
        
        try:
            groups = await self.db.get_active_groups()
            
            for group in groups:
                group_alerts = []
                
                # Проверяем разные типы алертов
                group_alerts.extend(await self.check_activity_spikes(group.group_id, group.title))
                group_alerts.extend(await self.check_spam_activity(group.group_id, group.title))
                
                all_alerts.extend(group_alerts)
                
                # Делаем небольшую паузу между группами
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Ошибка проверки групп для алертов: {e}")
        
        return all_alerts
    
    async def send_alert(self, alert: Alert, admin_users: List[int]):
        """Отправка алерта администраторам"""
        try:
            alert_message = f"""
🚨 **АЛЕРТ СИСТЕМЫ МОНИТОРИНГА**

🏷️ **Группа:** {alert.group_name}
⏰ **Время:** {alert.timestamp.strftime('%d.%m.%Y %H:%M')}
🔍 **Тип:** {alert.alert_type}

{alert.message}

📋 **Детали:**
• Значение: {alert.value}
• Порог: {alert.threshold}
• ID группы: {alert.group_id}
            """
            
            for admin_id in admin_users:
                try:
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=alert_message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Алерт отправлен администратору {admin_id}")
                except Exception as e:
                    logger.error(f"Ошибка отправки алерта администратору {admin_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка отправки алерта: {e}")
    
    async def run_monitoring_cycle(self, admin_users: List[int]):
        """Запуск цикла мониторинга"""
        try:
            logger.info("🚨 Запуск цикла мониторинга алертов...")
            
            alerts = await self.check_all_groups()
            
            if alerts:
                logger.info(f"Найдено {len(alerts)} алертов")
                for alert in alerts:
                    await self.send_alert(alert, admin_users)
            else:
                logger.info("Алертов не найдено - всё спокойно")
                
        except Exception as e:
            logger.error(f"Ошибка в цикле мониторинга: {e}")
    
    def update_settings(self, new_settings: Dict[str, float]):
        """Обновление настроек алертов"""
        self.alert_settings.update(new_settings)
        logger.info(f"Настройки алертов обновлены: {self.alert_settings}")
