import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from database import Database

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Класс для генерации отчетов"""
    
    def __init__(self, database: Database):
        self.db = database
    
    async def generate_daily_report(self, date: datetime = None) -> str:
        """Генерация дневного отчета"""
        if not date:
            date = datetime.now() - timedelta(days=1)  # Вчерашний день
        
        try:
            groups = await self.db.get_active_groups()
            report_lines = [
                f"📊 <b>Дневной отчет за {date.strftime('%d.%m.%Y')}</b>\n"
            ]
            
            total_messages = 0
            total_users = 0
            
            for group in groups:
                stats = await self.db.get_daily_stats(group.group_id, date)
                
                if stats['messages_count'] > 0:
                    total_messages += stats['messages_count']
                    total_users += stats['users_count']
                    
                    report_lines.append(
                        f"🔹 <b>{group.title or 'Группа без названия'}</b>\n"
                        f"   💬 Сообщений: {stats['messages_count']}\n"
                        f"   👥 Активных пользователей: {stats['users_count']}\n"
                    )
                    
                    # Топ-3 пользователя
                    if stats['top_users']:
                        report_lines.append("   🏆 Топ активных:")
                        for i, user in enumerate(stats['top_users'][:3], 1):
                            username = user['username'] or f"User {user['user_id']}"
                            report_lines.append(f"     {i}. @{username} - {user['message_count']} сообщений")
                        report_lines.append("")
            
            # Общая статистика
            report_lines.extend([
                f"📈 <b>Общая статистика:</b>",
                f"💬 Всего сообщений: {total_messages}",
                f"👥 Всего активных пользователей: {total_users}",
                f"📱 Отслеживаемых групп: {len(groups)}"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Ошибка при генерации дневного отчета: {e}")
            return "❌ Ошибка при генерации отчета"
    
    async def generate_weekly_report(self, end_date: datetime = None) -> str:
        """Генерация недельного отчета"""
        if not end_date:
            end_date = datetime.now()
        
        start_date = end_date - timedelta(days=7)
        
        try:
            groups = await self.db.get_active_groups()
            report_lines = [
                f"📊 <b>Недельный отчет</b>",
                f"📅 {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
            ]
            
            total_messages = 0
            total_users_set = set()
            
            for group in groups:
                group_messages = 0
                group_users = set()
                
                # Собираем статистику за каждый день недели
                current_date = start_date
                while current_date <= end_date:
                    stats = await self.db.get_daily_stats(group.group_id, current_date)
                    group_messages += stats['messages_count']
                    
                    # Добавляем уникальных пользователей
                    for user in stats['top_users']:
                        group_users.add(user['user_id'])
                        total_users_set.add(user['user_id'])
                    
                    current_date += timedelta(days=1)
                
                if group_messages > 0:
                    total_messages += group_messages
                    
                    report_lines.append(
                        f"🔹 <b>{group.title or 'Группа без названия'}</b>\n"
                        f"   💬 Сообщений за неделю: {group_messages}\n"
                        f"   👥 Уникальных пользователей: {len(group_users)}\n"
                    )
            
            # Общая статистика
            report_lines.extend([
                f"📈 <b>Итого за неделю:</b>",
                f"💬 Всего сообщений: {total_messages}",
                f"👥 Уникальных пользователей: {len(total_users_set)}",
                f"📱 Активных групп: {len([g for g in groups if total_messages > 0])}"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Ошибка при генерации недельного отчета: {e}")
            return "❌ Ошибка при генерации отчета"
    
    async def generate_monthly_report(self, end_date: datetime = None) -> str:
        """Генерация месячного отчета"""
        if not end_date:
            end_date = datetime.now()
        
        start_date = end_date - timedelta(days=30)
        
        try:
            groups = await self.db.get_active_groups()
            report_lines = [
                f"📊 <b>Месячный отчет</b>",
                f"📅 {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
            ]
            
            total_messages = 0
            total_users_set = set()
            group_stats = []
            
            for group in groups:
                group_messages = 0
                group_users = set()
                daily_stats = []
                
                # Собираем статистику за каждый день месяца
                current_date = start_date
                while current_date <= end_date:
                    stats = await self.db.get_daily_stats(group.group_id, current_date)
                    group_messages += stats['messages_count']
                    daily_stats.append(stats['messages_count'])
                    
                    for user in stats['top_users']:
                        group_users.add(user['user_id'])
                        total_users_set.add(user['user_id'])
                    
                    current_date += timedelta(days=1)
                
                if group_messages > 0:
                    total_messages += group_messages
                    
                    # Вычисляем средние значения
                    avg_daily = group_messages / 30
                    max_daily = max(daily_stats) if daily_stats else 0
                    
                    group_stats.append({
                        'group': group,
                        'messages': group_messages,
                        'users': len(group_users),
                        'avg_daily': avg_daily,
                        'max_daily': max_daily
                    })
            
            # Сортируем группы по активности
            group_stats.sort(key=lambda x: x['messages'], reverse=True)
            
            for stat in group_stats:
                report_lines.append(
                    f"🔹 <b>{stat['group'].title or 'Группа без названия'}</b>\n"
                    f"   💬 Сообщений за месяц: {stat['messages']}\n"
                    f"   👥 Уникальных пользователей: {stat['users']}\n"
                    f"   📊 Среднее в день: {stat['avg_daily']:.1f}\n"
                    f"   🔥 Максимум в день: {stat['max_daily']}\n"
                )
            
            # Общая статистика
            avg_daily_total = total_messages / 30 if total_messages > 0 else 0
            
            report_lines.extend([
                f"📈 <b>Итого за месяц:</b>",
                f"💬 Всего сообщений: {total_messages}",
                f"👥 Уникальных пользователей: {len(total_users_set)}",
                f"📊 Среднее сообщений в день: {avg_daily_total:.1f}",
                f"📱 Активных групп: {len(group_stats)}"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Ошибка при генерации месячного отчета: {e}")
            return "❌ Ошибка при генерации отчета"
