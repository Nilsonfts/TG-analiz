#!/usr/bin/env python3
"""
ИСПРАВЛЕНИЯ МАРКЕТИНГА: Критические ошибки в аналитике устранены!

Основные исправления:
1. ER (Engagement Rate) теперь рассчитывается правильно: реакции/подписчики, а не реакции/просмотры
2. Добавлены реальные маркетинговые метрики
3. Исправлена временная логика для SMM отчетов
4. Улучшены расчеты конверсий и активности
"""

# Правильный расчет ER (Engagement Rate) для Telegram каналов
def calculate_correct_er(total_reactions: int, total_posts: int, subscribers: int) -> str:
    """
    Правильный расчет ER для Telegram:
    ER = (Среднее количество реакций на пост / Количество подписчиков) × 100%
    
    Это ИНДУСТРИАЛЬНЫЙ СТАНДАРТ!
    """
    if subscribers <= 0 or total_posts <= 0:
        return "0.00%"
    
    avg_reactions_per_post = total_reactions / total_posts
    er = (avg_reactions_per_post / subscribers) * 100
    return f"{er:.2f}%"

# Правильные бенчмарки ER для Telegram каналов
def get_er_rating(er_percentage: float, subscribers: int) -> str:
    """
    Оценка ER согласно индустрии:
    - Мега-каналы (100k+): 1-3% = отлично
    - Большие каналы (10k-100k): 3-7% = отлично  
    - Средние каналы (1k-10k): 7-15% = отлично
    - Малые каналы (<1k): 15%+ = отлично
    """
    if subscribers >= 100000:
        if er_percentage >= 3: return "🔥 Отлично"
        elif er_percentage >= 1.5: return "✅ Хорошо"
        elif er_percentage >= 1: return "⚠️ Средне"
        else: return "❌ Плохо"
    elif subscribers >= 10000:
        if er_percentage >= 7: return "🔥 Отлично"
        elif er_percentage >= 4: return "✅ Хорошо"
        elif er_percentage >= 2: return "⚠️ Средне"
        else: return "❌ Плохо"
    elif subscribers >= 1000:
        if er_percentage >= 15: return "🔥 Отлично"
        elif er_percentage >= 10: return "✅ Хорошо"
        elif er_percentage >= 5: return "⚠️ Средне"
        else: return "❌ Плохо"
    else:
        if er_percentage >= 20: return "🔥 Отлично"
        elif er_percentage >= 15: return "✅ Хорошо"
        elif er_percentage >= 10: return "⚠️ Средне"
        else: return "❌ Плохо"

# Правильный расчет VTR (View Through Rate)
def calculate_vtr(total_views: int, subscribers: int) -> str:
    """
    VTR = Общие просмотры / Подписчики × 100%
    Показывает, какой процент аудитории видит контент
    """
    if subscribers <= 0:
        return "0.00%"
    
    vtr = (total_views / subscribers) * 100
    return f"{vtr:.1f}%"

# Правильный расчет охвата (Reach Rate)
def calculate_reach_rate(unique_views: int, subscribers: int) -> str:
    """
    Reach Rate = Уникальные просмотры / Подписчики × 100%
    """
    if subscribers <= 0:
        return "0.00%"
    
    reach = (unique_views / subscribers) * 100
    return f"{reach:.1f}%"

# Температура канала (активность аудитории)
def calculate_channel_temperature(er: float, vtr: float, subscribers: int) -> dict:
    """
    Расчет температуры канала на основе ER и VTR
    """
    # Нормализуем метрики по размеру аудитории
    if subscribers >= 100000:
        er_weight = er / 3.0  # Для мега-каналов ER 3% = максимум
        vtr_weight = vtr / 50.0  # VTR 50% = максимум
    elif subscribers >= 10000:
        er_weight = er / 7.0
        vtr_weight = vtr / 70.0
    elif subscribers >= 1000:
        er_weight = er / 15.0
        vtr_weight = vtr / 90.0
    else:
        er_weight = er / 20.0
        vtr_weight = vtr / 100.0
    
    # Общая температура (0-5)
    temperature = min(5, (er_weight + vtr_weight) * 2.5)
    
    fire_emojis = "🔥" * int(temperature)
    cold_emojis = "⬜" * (5 - int(temperature))
    
    return {
        "value": temperature,
        "display": f"{fire_emojis}{cold_emojis}",
        "rating": f"({int(temperature)}/5)"
    }

# Анализ лучшего времени публикации
def analyze_posting_times(posts_data: list) -> dict:
    """
    Анализ эффективности времени публикации
    posts_data: [{"hour": int, "views": int, "reactions": int, "subscribers": int}]
    """
    hourly_stats = {}
    
    for post in posts_data:
        hour = post["hour"]
        if hour not in hourly_stats:
            hourly_stats[hour] = {"views": 0, "reactions": 0, "posts": 0, "subscribers": post["subscribers"]}
        
        hourly_stats[hour]["views"] += post["views"]
        hourly_stats[hour]["reactions"] += post["reactions"]
        hourly_stats[hour]["posts"] += 1
    
    # Рассчитываем ER для каждого часа
    hour_er = {}
    for hour, stats in hourly_stats.items():
        if stats["posts"] > 0 and stats["subscribers"] > 0:
            avg_reactions = stats["reactions"] / stats["posts"]
            er = (avg_reactions / stats["subscribers"]) * 100
            hour_er[hour] = er
    
    # Топ-3 часа
    sorted_hours = sorted(hour_er.items(), key=lambda x: x[1], reverse=True)[:3]
    
    return {
        "best_hours": sorted_hours,
        "all_hours": hour_er
    }

print("✅ Модуль правильных маркетинговых расчетов загружен!")
print("🎯 Основные исправления:")
print("   • ER рассчитывается от подписчиков, не от просмотров")
print("   • Добавлены индустриальные бенчмарки")
print("   • Температура канала учитывает размер аудитории")
print("   • Анализ времени публикации основан на реальном ER")
