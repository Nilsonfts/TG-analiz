# 🚀 Railway Environment Variables Setup

## Обязательные переменные для работы бота

Добавьте эти переменные в Railway → Settings → Variables:

### 1. Telegram Bot Token
```
BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
```
**Как получить:** Создайте бота через @BotFather в Telegram

### 2. Telegram API Credentials  
```
TELEGRAM_API_ID=YOUR_API_ID
TELEGRAM_API_HASH=YOUR_API_HASH
```
**Как получить:** Зарегистрируйтесь на https://my.telegram.org/apps

### 3. Admin Users
```
ADMIN_USER_IDS=YOUR_TELEGRAM_USER_ID
```
**Как узнать свой ID:** Напишите боту @userinfobot

### 4. Database (автоматически предоставляется Railway)
```
DATABASE_URL=postgresql://user:pass@host:port/db
```

## Необязательные переменные

### Report Chat (для отчетов)
```
REPORT_CHAT_ID=YOUR_CHAT_ID
```

### External APIs (для расширенной аналитики)
```
TELEMETR_API_KEY=your_telemetr_key
TGSTAT_API_KEY=your_tgstat_key
```

### Debug Mode
```
DEBUG=false
LOG_LEVEL=INFO
```

## 📋 Checklist

- [ ] BOT_TOKEN добавлен
- [ ] TELEGRAM_API_ID добавлен  
- [ ] TELEGRAM_API_HASH добавлен
- [ ] ADMIN_USER_IDS добавлен
- [ ] DATABASE_URL настроен (через Railway PostgreSQL addon)

## 🔧 Как добавить в Railway

1. Зайдите в Railway Dashboard
2. Выберите ваш проект TG-analiz
3. Перейдите в Variables
4. Добавьте каждую переменную:
   - Name: BOT_TOKEN
   - Value: ваш токен от @BotFather
5. Нажмите Deploy

Railway автоматически перезапустит сервис с новыми переменными.

## ✅ После настройки

Бот будет:
- ✅ Отвечать на команды /start, /help
- ✅ Проходить Railway healthcheck  
- ✅ Анализировать каналы
- ✅ Генерировать отчеты
