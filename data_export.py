"""
Экспорт данных для Telegram Analytics Bot
Создание CSV, Excel файлов с аналитикой
"""
import csv
import io
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class DataExporter:
    """Класс для экспорта данных аналитики"""
    
    def __init__(self, db):
        self.db = db
    
    async def export_messages_csv(self, group_id: int, days: int = 30) -> io.BytesIO:
        """Экспорт сообщений в CSV"""
        try:
            # Получаем сообщения за указанный период
            start_date = datetime.now() - timedelta(days=days)
            
            async with self.db.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT 
                        message_id,
                        user_id,
                        username,
                        text,
                        date,
                        views,
                        reply_to_message_id,
                        forward_from_user_id
                    FROM messages 
                    WHERE group_id = $1 AND date >= $2
                    ORDER BY date DESC
                ''', group_id, start_date)
            
            # Создаём CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовки
            writer.writerow([
                'Message ID', 'User ID', 'Username', 'Text', 'Date', 
                'Views', 'Reply To', 'Forward From'
            ])
            
            # Данные
            for row in rows:
                writer.writerow([
                    row['message_id'],
                    row['user_id'] or '',
                    row['username'] or '',
                    (row['text'] or '')[:100] + '...' if row['text'] and len(row['text']) > 100 else (row['text'] or ''),
                    row['date'].strftime('%Y-%m-%d %H:%M:%S') if row['date'] else '',
                    row['views'] or 0,
                    row['reply_to_message_id'] or '',
                    row['forward_from_user_id'] or ''
                ])
            
            # Конвертируем в BytesIO
            output.seek(0)
            csv_buffer = io.BytesIO()
            csv_buffer.write(output.getvalue().encode('utf-8'))
            csv_buffer.seek(0)
            
            return csv_buffer
            
        except Exception as e:
            logger.error(f"Ошибка экспорта сообщений в CSV: {e}")
            return None
    
    async def export_users_csv(self, group_id: int) -> io.BytesIO:
        """Экспорт пользователей в CSV"""
        try:
            async with self.db.pool.acquire() as conn:
                # Получаем статистику пользователей
                rows = await conn.fetch('''
                    SELECT 
                        u.user_id,
                        u.username,
                        u.first_name,
                        u.last_name,
                        u.first_seen,
                        u.last_seen,
                        COUNT(m.message_id) as total_messages,
                        MAX(m.date) as last_message_date
                    FROM telegram_users u
                    LEFT JOIN messages m ON u.user_id = m.user_id AND m.group_id = $1
                    WHERE u.user_id IN (
                        SELECT DISTINCT user_id FROM messages WHERE group_id = $1 AND user_id IS NOT NULL
                    )
                    GROUP BY u.user_id, u.username, u.first_name, u.last_name, u.first_seen, u.last_seen
                    ORDER BY total_messages DESC
                ''', group_id)
            
            # Создаём CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовки
            writer.writerow([
                'User ID', 'Username', 'First Name', 'Last Name', 
                'First Seen', 'Last Seen', 'Total Messages', 'Last Message'
            ])
            
            # Данные
            for row in rows:
                writer.writerow([
                    row['user_id'],
                    row['username'] or '',
                    row['first_name'] or '',
                    row['last_name'] or '',
                    row['first_seen'].strftime('%Y-%m-%d %H:%M:%S') if row['first_seen'] else '',
                    row['last_seen'].strftime('%Y-%m-%d %H:%M:%S') if row['last_seen'] else '',
                    row['total_messages'] or 0,
                    row['last_message_date'].strftime('%Y-%m-%d %H:%M:%S') if row['last_message_date'] else ''
                ])
            
            # Конвертируем в BytesIO
            output.seek(0)
            csv_buffer = io.BytesIO()
            csv_buffer.write(output.getvalue().encode('utf-8'))
            csv_buffer.seek(0)
            
            return csv_buffer
            
        except Exception as e:
            logger.error(f"Ошибка экспорта пользователей в CSV: {e}")
            return None
    
    async def export_analytics_csv(self, group_id: int, days: int = 30) -> io.BytesIO:
        """Экспорт аналитики по дням в CSV"""
        try:
            # Получаем дневную статистику
            daily_data = await self.db.get_daily_trend(group_id, days)
            
            # Создаём CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовки
            writer.writerow([
                'Date', 'Messages Count', 'Users Count', 'Messages per User'
            ])
            
            # Данные
            for row in daily_data:
                messages_per_user = row['messages_count'] / row['users_count'] if row['users_count'] > 0 else 0
                writer.writerow([
                    row['date'].strftime('%Y-%m-%d') if row['date'] else '',
                    row['messages_count'],
                    row['users_count'],
                    f"{messages_per_user:.2f}"
                ])
            
            # Конвертируем в BytesIO
            output.seek(0)
            csv_buffer = io.BytesIO()
            csv_buffer.write(output.getvalue().encode('utf-8'))
            csv_buffer.seek(0)
            
            return csv_buffer
            
        except Exception as e:
            logger.error(f"Ошибка экспорта аналитики в CSV: {e}")
            return None
    
    async def export_hourly_activity_csv(self, group_id: int, days: int = 7) -> io.BytesIO:
        """Экспорт почасовой активности в CSV"""
        try:
            # Получаем почасовую активность
            hourly_data = await self.db.get_hourly_activity(group_id, days)
            
            # Создаём CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовки
            writer.writerow(['Hour', 'Messages Count'])
            
            # Данные (все 24 часа)
            for hour in range(24):
                count = hourly_data.get(str(hour), 0)
                writer.writerow([f"{hour:02d}:00", count])
            
            # Конвертируем в BytesIO
            output.seek(0)
            csv_buffer = io.BytesIO()
            csv_buffer.write(output.getvalue().encode('utf-8'))
            csv_buffer.seek(0)
            
            return csv_buffer
            
        except Exception as e:
            logger.error(f"Ошибка экспорта почасовой активности в CSV: {e}")
            return None
    
    async def create_full_export_package(self, group_id: int, group_name: str) -> Dict[str, io.BytesIO]:
        """Создание полного пакета экспорта"""
        try:
            export_package = {}
            
            # Экспортируем разные типы данных
            messages_csv = await self.export_messages_csv(group_id, 30)
            if messages_csv:
                export_package[f"{group_name}_messages_30days.csv"] = messages_csv
            
            users_csv = await self.export_users_csv(group_id)
            if users_csv:
                export_package[f"{group_name}_users.csv"] = users_csv
            
            analytics_csv = await self.export_analytics_csv(group_id, 30)
            if analytics_csv:
                export_package[f"{group_name}_daily_analytics_30days.csv"] = analytics_csv
            
            hourly_csv = await self.export_hourly_activity_csv(group_id, 7)
            if hourly_csv:
                export_package[f"{group_name}_hourly_activity_7days.csv"] = hourly_csv
            
            return export_package
            
        except Exception as e:
            logger.error(f"Ошибка создания пакета экспорта: {e}")
            return {}
    
    def sanitize_filename(self, filename: str) -> str:
        """Очистка имени файла от недопустимых символов"""
        # Заменяем недопустимые символы
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Убираем лишние пробелы и точки
        filename = filename.strip('. ')
        
        return filename[:50]  # Ограничиваем длину
