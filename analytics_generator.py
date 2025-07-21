import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io
import numpy as np
from typing import Optional, Dict, Any

async def generate_channel_analytics_image(real_stats: Optional[Dict[str, Any]] = None) -> io.BytesIO:
    """
    Генерирует PNG изображение с РЕАЛЬНОЙ аналитикой канала
    """
    # Настройка шрифтов для поддержки русского языка
    plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Tahoma']
    plt.rcParams['axes.unicode_minus'] = False
    
    # Создаем фигуру с соотношением сторон 4:3
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('📊 РЕАЛЬНАЯ Аналитика Telegram-канала', fontsize=20, fontweight='bold', y=0.95)
    
    # ИСПОЛЬЗУЕМ ТОЛЬКО РЕАЛЬНЫЕ ДАННЫЕ!
    if real_stats and isinstance(real_stats, dict):
        channel_name = real_stats.get('title', 'Неизвестный канал')
        current_subscribers = real_stats.get('participants_count', 0)
        total_views = real_stats.get('total_views', 0)
        total_reactions = real_stats.get('total_reactions', 0)
        total_forwards = real_stats.get('total_forwards', 0)
        posts_count = real_stats.get('posts', 0)
        er_value = real_stats.get('er', 0.0)
        
        # Защита от None значений
        current_subscribers = int(current_subscribers or 0)
        total_views = int(total_views or 0)
        total_reactions = int(total_reactions or 0)
        total_forwards = int(total_forwards or 0)
        posts_count = int(posts_count or 0)
        er_value = float(er_value or 0.0)
    else:
        # Если нет данных - показываем что данных нет!
        channel_name = 'НЕТ ДАННЫХ'
        current_subscribers = 0
        total_views = 0
        total_reactions = 0
        total_forwards = 0
        posts_count = 0
        er_value = 0.0
    
    # 1. График реальных метрик вместо "роста подписчиков"
    ax1.set_title('� Реальные метрики контента', fontsize=14, fontweight='bold')
    
    if posts_count > 0:
        # Показываем РЕАЛЬНЫЕ данные о контенте
        metrics_names = ['Посты', 'Просмотры\n(тыс.)', 'Реакции', 'Репосты']
        metrics_values = [
            posts_count,
            total_views // 1000 if total_views > 1000 else total_views,
            total_reactions,
            total_forwards
        ]
        
        bars = ax1.bar(metrics_names, metrics_values, color=['#2196F3', '#4CAF50', '#FF9800', '#9C27B0'], alpha=0.8)
        ax1.set_ylabel('Количество', fontsize=12)
        
        # Добавляем значения на столбцы
        for bar, value in zip(bars, metrics_values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + max(height*0.01, 1),
                    f'{int(value)}', ha='center', va='bottom', fontweight='bold')
    else:
        ax1.text(0.5, 0.5, 'НЕТ ДАННЫХ О ПОСТАХ', ha='center', va='center', 
                transform=ax1.transAxes, fontsize=16, color='red', fontweight='bold')
        ax1.set_xlim(0, 1)
        ax1.set_ylim(0, 1)
    
    # 2. РЕАЛЬНЫЙ Engagement Rate
    ax2.set_title('🎯 Engagement Rate (РЕАЛЬНЫЙ)', fontsize=14, fontweight='bold')
    
    if current_subscribers > 0 and posts_count > 0:
        # Профессиональный расчет ER
        total_engagement = total_reactions + total_forwards
        er_percentage = (total_engagement / current_subscribers) * 100
        
        # Показываем компоненты ER
        components = ['Реакции', 'Репосты', 'ER %']
        values = [
            total_reactions / max(current_subscribers, 1) * 100,
            total_forwards / max(current_subscribers, 1) * 100,
            er_percentage
        ]
        colors = ['#FF9800', '#9C27B0', '#4CAF50']
        
        bars = ax2.bar(components, values, color=colors, alpha=0.8)
        ax2.set_ylabel('Процент от аудитории', fontsize=12)
        
        # Добавляем значения на столбцы
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + max(height*0.01, 0.01),
                    f'{value:.2f}%', ha='center', va='bottom', fontweight='bold')
    else:
        ax2.text(0.5, 0.5, 'НЕТ ДАННЫХ ДЛЯ ER', ha='center', va='center', 
                transform=ax2.transAxes, fontsize=16, color='red', fontweight='bold')
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
    
    # 3. РЕАЛЬНАЯ статистика контента (вместо "активности по дням")
    ax3.set_title('� Эффективность контента', fontsize=14, fontweight='bold')
    
    if posts_count > 0 and total_views > 0:
        # Реальные маркетинговые метрики
        avg_views_per_post = total_views / posts_count
        avg_reactions_per_post = total_reactions / posts_count
        avg_forwards_per_post = total_forwards / posts_count
        
        metrics = ['Ср. просмотры', 'Ср. реакции', 'Ср. репосты']
        values = [avg_views_per_post, avg_reactions_per_post, avg_forwards_per_post]
        
        ax3.bar(metrics, values, color='#9C27B0', alpha=0.7)
        ax3.set_ylabel('Среднее на пост', fontsize=12)
        ax3.grid(True, alpha=0.3, axis='y')
        
        # Добавляем значения
        for i, value in enumerate(values):
            ax3.text(i, value + max(value*0.01, 1), f'{int(value)}', 
                    ha='center', va='bottom', fontweight='bold')
    else:
        ax3.text(0.5, 0.5, 'НЕТ ДАННЫХ О КОНТЕНТЕ', ha='center', va='center', 
                transform=ax3.transAxes, fontsize=16, color='red', fontweight='bold')
        ax3.set_xlim(0, 1)
        ax3.set_ylim(0, 1)
    
    # 4. РЕАЛЬНЫЕ ключевые метрики
    ax4.set_title('🎯 РЕАЛЬНЫЕ Ключевые метрики', fontsize=14, fontweight='bold')
    ax4.axis('off')
    
    # ТОЛЬКО РЕАЛЬНЫЕ РАСЧЕТЫ!
    if current_subscribers > 0 and posts_count > 0:
        total_subs = f"{current_subscribers:,}"
        total_engagement = total_reactions + total_forwards
        er_rate = f"{(total_engagement / current_subscribers * 100):.2f}%"
        avg_views_per_post = int(total_views / posts_count) if posts_count > 0 else 0
        
        # VTR (View Through Rate) - сколько % аудитории видит посты
        vtr_rate = f"{(total_views / posts_count / current_subscribers * 100):.1f}%" if posts_count > 0 else "0%"
        
        metrics_text = f"""
📺 Канал: {channel_name}
👥 Подписчиков: {total_subs}

� РЕАЛЬНЫЕ МЕТРИКИ:
   • Постов проанализировано: {posts_count}
   • Общие просмотры: {total_views:,}
   • Общие реакции: {total_reactions:,}
   • Общие репосты: {total_forwards:,}

💡 ПРОФЕССИОНАЛЬНЫЕ КПИ:
   • ER (Engagement Rate): {er_rate}
   • VTR (View Through Rate): {vtr_rate}
   • Средние просмотры/пост: {avg_views_per_post:,}
   
� Данные получены через Telethon API
"""
    else:
        metrics_text = f"""
📺 Канал: {channel_name}
👥 Подписчиков: {current_subscribers:,}

❌ НЕТ ДАННЫХ ДЛЯ АНАЛИЗА:
   • Нет доступа к истории постов
   • Или канал без контента
   • Или ошибка API

🔧 Проверьте:
   • Настройки Telethon
   • Права доступа к каналу
   • Наличие постов в канале
"""
    
    ax4.text(0.05, 0.95, metrics_text, transform=ax4.transAxes, fontsize=12,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.3))
    
    # Настройка общего стиля
    plt.tight_layout()
    fig.patch.set_facecolor('white')
    
    # Добавляем водяной знак
    fig.text(0.95, 0.02, 'Generated by TG Analytics Bot', 
             ha='right', va='bottom', fontsize=8, alpha=0.5)
    
    # Сохраняем в BytesIO
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    
    return buf
