import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import logging
from typing import Dict, List, Any, Optional

# Настройка для работы без GUI
import matplotlib
matplotlib.use('Agg')

logger = logging.getLogger(__name__)

# Настройка стиля
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class ChartGenerator:
    """Генератор графиков для Telegram аналитики"""
    
    def __init__(self):
        # Настройка шрифтов для поддержки русского языка
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        
    def create_activity_chart(self, hourly_data: Dict[str, int], title: str = "Активность по часам") -> io.BytesIO:
        """Создание графика активности по часам"""
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Подготовка данных
            hours = list(range(24))
            activity = [hourly_data.get(str(h), 0) for h in hours]
            
            # Создание графика
            bars = ax.bar(hours, activity, color='skyblue', alpha=0.7, edgecolor='navy', linewidth=0.5)
            
            # Оформление
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Час дня', fontsize=12)
            ax.set_ylabel('Количество сообщений', fontsize=12)
            ax.set_xticks(hours)
            ax.grid(True, alpha=0.3)
            
            # Добавляем значения на столбцы
            for bar, value in zip(bars, activity):
                if value > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                           str(value), ha='center', va='bottom', fontsize=9)
            
            plt.tight_layout()
            
            # Сохранение в BytesIO
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Ошибка создания графика активности: {e}")
            plt.close()
            return None
    
    def create_top_users_chart(self, top_users: List[Dict], title: str = "Топ активных пользователей") -> io.BytesIO:
        """Создание графика топ пользователей"""
        try:
            if not top_users:
                return None
                
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Подготовка данных
            usernames = []
            messages = []
            
            for user in top_users[:10]:  # Топ 10
                username = user.get('username') or f"User_{user.get('user_id', 'Unknown')}"
                if len(username) > 15:
                    username = username[:12] + "..."
                usernames.append(username)
                messages.append(user.get('message_count', 0))
            
            # Создание горизонтального графика
            bars = ax.barh(usernames, messages, color='lightcoral', alpha=0.8, edgecolor='darkred')
            
            # Оформление
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Количество сообщений', fontsize=12)
            ax.grid(True, alpha=0.3, axis='x')
            
            # Добавляем значения
            for bar, value in zip(bars, messages):
                ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                       str(value), ha='left', va='center', fontsize=10)
            
            plt.tight_layout()
            
            # Сохранение в BytesIO
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Ошибка создания графика топ пользователей: {e}")
            plt.close()
            return None
    
    def create_daily_trend_chart(self, daily_stats: List[Dict], title: str = "Динамика активности") -> io.BytesIO:
        """Создание графика динамики по дням"""
        try:
            if not daily_stats or len(daily_stats) < 2:
                return None
                
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # Подготовка данных
            dates = [stat['date'] for stat in daily_stats]
            messages = [stat['messages_count'] for stat in daily_stats]
            users = [stat['users_count'] for stat in daily_stats]
            
            # График сообщений
            ax1.plot(dates, messages, marker='o', linewidth=2, markersize=6, 
                    color='blue', label='Сообщения')
            ax1.set_title('Количество сообщений по дням', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Сообщения', fontsize=12)
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            
            # График пользователей
            ax2.plot(dates, users, marker='s', linewidth=2, markersize=6, 
                    color='green', label='Активные пользователи')
            ax2.set_title('Количество активных пользователей по дням', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Пользователи', fontsize=12)
            ax2.set_xlabel('Дата', fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
            # Поворот подписей дат
            for ax in [ax1, ax2]:
                ax.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            # Сохранение в BytesIO
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Ошибка создания графика динамики: {e}")
            plt.close()
            return None
    
    def create_weekly_heatmap(self, hourly_data_by_days: Dict[str, Dict[str, int]], 
                             title: str = "Тепловая карта активности") -> io.BytesIO:
        """Создание тепловой карты активности по дням недели и часам"""
        try:
            # Создаем матрицу 7x24 (дни недели x часы)
            days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
            hours = list(range(24))
            
            # Инициализируем матрицу нулями
            heatmap_data = np.zeros((7, 24))
            
            # Заполняем данными (если есть)
            for day_idx, day in enumerate(days):
                day_data = hourly_data_by_days.get(day, {})
                for hour in hours:
                    heatmap_data[day_idx][hour] = day_data.get(str(hour), 0)
            
            # Создаем график
            fig, ax = plt.subplots(figsize=(16, 8))
            
            # Тепловая карта
            sns.heatmap(heatmap_data, 
                       xticklabels=hours,
                       yticklabels=days,
                       annot=True, 
                       fmt='g',
                       cmap='YlOrRd',
                       cbar_kws={'label': 'Количество сообщений'},
                       ax=ax)
            
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('Час дня', fontsize=12)
            ax.set_ylabel('День недели', fontsize=12)
            
            plt.tight_layout()
            
            # Сохранение в BytesIO
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Ошибка создания тепловой карты: {e}")
            plt.close()
            return None
    
    def create_summary_dashboard(self, stats: Dict[str, Any], title: str = "Сводная панель") -> io.BytesIO:
        """Создание сводного дашборда"""
        try:
            fig = plt.figure(figsize=(16, 12))
            
            # 1. Общая статистика (текст)
            ax1 = plt.subplot(2, 3, 1)
            ax1.axis('off')
            ax1.text(0.1, 0.8, f"📊 Общая статистика", fontsize=16, fontweight='bold')
            ax1.text(0.1, 0.6, f"💬 Сообщений: {stats.get('total_messages', 0)}", fontsize=12)
            ax1.text(0.1, 0.5, f"👥 Пользователей: {stats.get('total_users', 0)}", fontsize=12)
            ax1.text(0.1, 0.4, f"📈 Среднее в день: {stats.get('avg_daily', 0):.1f}", fontsize=12)
            ax1.text(0.1, 0.3, f"🏆 Самый активный: {stats.get('top_user', 'N/A')}", fontsize=12)
            
            # 2. Активность по часам (мини-версия)
            if 'hourly_activity' in stats:
                ax2 = plt.subplot(2, 3, 2)
                hours = list(range(24))
                activity = [stats['hourly_activity'].get(str(h), 0) for h in hours]
                ax2.bar(hours, activity, color='lightblue', alpha=0.7)
                ax2.set_title('Активность по часам', fontsize=12, fontweight='bold')
                ax2.set_xlabel('Час')
                ax2.set_ylabel('Сообщения')
                ax2.grid(True, alpha=0.3)
            
            # 3. Топ пользователи (мини-версия)
            if 'top_users' in stats and stats['top_users']:
                ax3 = plt.subplot(2, 3, 3)
                top_5 = stats['top_users'][:5]
                usernames = [user.get('username', f"User_{user.get('user_id', 'Unknown')}")[:10] 
                           for user in top_5]
                messages = [user.get('message_count', 0) for user in top_5]
                ax3.barh(usernames, messages, color='lightcoral', alpha=0.8)
                ax3.set_title('Топ-5 пользователей', fontsize=12, fontweight='bold')
                ax3.set_xlabel('Сообщения')
            
            # 4. Динамика (если есть данные за несколько дней)
            if 'daily_trend' in stats and len(stats['daily_trend']) > 1:
                ax4 = plt.subplot(2, 3, (4, 5))
                dates = [day['date'] for day in stats['daily_trend']]
                messages = [day['messages_count'] for day in stats['daily_trend']]
                ax4.plot(dates, messages, marker='o', linewidth=2, color='green')
                ax4.set_title('Динамика активности', fontsize=12, fontweight='bold')
                ax4.set_ylabel('Сообщения')
                ax4.grid(True, alpha=0.3)
                ax4.tick_params(axis='x', rotation=45)
            
            # 6. Инфо
            ax6 = plt.subplot(2, 3, 6)
            ax6.axis('off')
            ax6.text(0.1, 0.8, f"🤖 Telegram Analytics", fontsize=14, fontweight='bold')
            ax6.text(0.1, 0.6, f"📅 Отчёт от: {datetime.now().strftime('%d.%m.%Y %H:%M')}", fontsize=10)
            ax6.text(0.1, 0.5, f"🎯 Группа: {stats.get('group_name', 'N/A')}", fontsize=10)
            ax6.text(0.1, 0.4, f"⏱️ Период: {stats.get('period', 'N/A')}", fontsize=10)
            
            plt.suptitle(title, fontsize=18, fontweight='bold')
            plt.tight_layout()
            
            # Сохранение в BytesIO
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Ошибка создания сводного дашборда: {e}")
            plt.close()
            return None
