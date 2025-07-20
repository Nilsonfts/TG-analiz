# Развертывание на Railway - Пошаговая инструкция

## 📋 Предварительные требования

### 0. Настройка Docker (ВАЖНО!)
Railway может использовать два способа сборки: **Nixpacks** (автоматически) или **Dockerfile** (вручную).

#### Вариант 1: Использование Nixpacks (Рекомендуется для Railway)
1. **НЕ создавайте** файл `Dockerfile`
2. Убедитесь, что в корне проекта есть файл `requirements.txt`
3. Railway автоматически определит Python проект и соберет его

#### Вариант 2: Использование Dockerfile
Если хотите полный контроль над сборкой:

1. Создайте файл `Dockerfile` в корне проекта:
```dockerfile
FROM python:3.9-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы приложения
COPY . .

# Открываем порт
EXPOSE 8000

# Команда запуска
CMD ["python", "main.py"]
```

2. **Важно**: В Railway настройках установите переменную:
```
NIXPACKS_NO_DEFAULT_CACHE_DIRS=1
```

#### Решение проблемы "exit code: 127"
Если получаете эту ошибку:
1. **Удалите файл `Dockerfile`** (если используете Nixpacks)
2. Или **отключите Nixpacks** в Railway настройках
3. Убедитесь, что `requirements.txt` находится в корне проекта

### 1. Создание Telegram бота
1. Откройте [@BotFather](https://t.me/botfather) в Telegram
2. Выполните команду `/newbot`
3. Введите имя бота (например: "My Analytics Bot")
4. Введите username бота (например: "my_analytics_bot")
5. **Сохраните полученный токен** (например: `1234567890:ABCdefGHIjklMNOpqrSTUVwxyz`)

### 2. Получение API credentials
1. Перейдите на [my.telegram.org](https://my.telegram.org)
2. Войдите с помощью номера телефона
3. Перейдите в "API development tools"
4. Создайте новое приложение:
   - App title: "TG Analytics"
   - Short name: "tg_analytics"
   - Platform: Other
5. **Сохраните `api_id` и `api_hash`**

### 3. Получение своего Telegram ID
1. Напишите [@userinfobot](https://t.me/userinfobot)
2. **Сохраните ваш ID** (например: `123456789`)

## 🚀 Развертывание на Railway

### Шаг 1: Подготовка репозитория
```bash
# Клонируйте репозиторий (если еще не сделали)
git clone <your-repo-url>
cd TG-analiz

# ВЫБЕРИТЕ ОДИН ИЗ ВАРИАНТОВ:
# Вариант A: Nixpacks (рекомендуется) - удалите Dockerfile если есть
rm Dockerfile

# Вариант B: Dockerfile - создайте его по инструкции выше

# Убедитесь, что requirements.txt в корне проекта
ls requirements.txt

# Протестируйте локально (опционально)
python scripts/test_config.py
```

### Шаг 2: Настройка Railway проекта
1. Зайдите на [railway.app](https://railway.app)
2. Нажмите "Start a New Project"
3. Выберите "Deploy from GitHub repo"
4. Выберите ваш репозиторий `TG-analiz`

### Шаг 3: Добавление базы данных
1. В Railway проекте нажмите "+ New"
2. Выберите "Database"
3. Выберите "PostgreSQL"
4. Дождитесь создания базы данных

### Шаг 4: Настройка переменных окружения
В Railway проекте перейдите в настройки основного сервиса и добавьте переменные:

**Обязательные переменные:**
```
BOT_TOKEN=ваш_токен_от_botfather
API_ID=ваш_api_id
API_HASH=ваш_api_hash
ADMIN_USERS=ваш_telegram_id
```

**Дополнительные переменные:**
```
TIMEZONE=Europe/Moscow
REPORTS_CHAT_ID=ваш_telegram_id
PORT=8000
```

**Если используете Dockerfile, добавьте:**
```
NIXPACKS_NO_DEFAULT_CACHE_DIRS=1
```

> ⚠️ **Важно**: `DATABASE_URL` заполнится автоматически Railway после создания PostgreSQL базы

### Шаг 5: Деплой
1. Railway автоматически начнет деплой после настройки переменных
2. Следите за логами во вкладке "Logs"
3. Дождитесь успешного завершения деплоя

### Шаг 6: Проверка работоспособности
1. Откройте URL вашего приложения в Railway
2. Вы должны увидеть: "Telegram Analytics Bot is running"
3. Проверьте health check: `https://ваш-домен.railway.app/health`

### Шаг 7: Настройка бота
1. Найдите вашего бота в Telegram по username
2. Нажмите "Start" или введите `/start`
3. Если все настроено правильно, вы получите приветственное сообщение

## 📊 Добавление групп для мониторинга

### Способ 1: Через Railway CLI (рекомендуется)
1. Установите Railway CLI:
   ```bash
   npm install -g @railway/cli
   # или
   curl -fsSL https://railway.app/install.sh | sh
   ```

2. Войдите в Railway:
   ```bash
   railway login
   ```

3. Подключитесь к проекту:
   ```bash
   railway link
   ```

4. Добавьте группу:
   ```bash
   railway run python scripts/manage_groups.py add имя_группы
   ```

### Способ 2: Через базу данных
1. Подключитесь к PostgreSQL через Railway dashboard
2. Выполните SQL запрос:
   ```sql
   INSERT INTO telegram_groups (group_id, username, title, description, members_count, is_active)
   VALUES (-1001234567890, 'group_username', 'Название группы', 'Описание', 0, true);
   ```

## 🔧 Мониторинг и отладка

### Просмотр логов
1. В Railway перейдите во вкладку "Logs"
2. Фильтруйте по уровню (INFO, ERROR, WARNING)
3. Следите за сообщениями о сборе данных и отправке отчетов

### Основные индикаторы работы
- **"Бот инициализирован успешно"** - бот запустился
- **"Планировщик запущен"** - расписание настроено
- **"HTTP сервер запущен на порту 8000"** - health checks работают
- **"Данные аналитики собраны успешно"** - сбор данных происходит

### Частые проблемы и решения

**Проблема: "exit code: 127" или "pip: command not found"**
```
Решение: 
1. УДАЛИТЕ файл Dockerfile если хотите использовать Nixpacks
2. Или установите переменную NIXPACKS_NO_DEFAULT_CACHE_DIRS=1
3. Убедитесь, что requirements.txt в корне проекта
4. Перезапустите деплой в Railway
```

**Проблема: "Конфликт между Dockerfile и Nixpacks"**
```
Решение:
1. Выберите ОДИН способ сборки
2. Либо удалите Dockerfile (для Nixpacks)
3. Либо отключите Nixpacks в настройках
```

**Проблема: "Нет прав администратора"**
```
Решение: Проверьте переменную ADMIN_USERS в Railway settings
```

**Проблема: "Database connection failed"**
```
Решение: 
1. Убедитесь, что PostgreSQL база создана
2. Проверьте, что DATABASE_URL установлена автоматически
3. Перезапустите деплой
```

**Проблема: "FloodWaitError"**
```
Решение: Это нормальное ограничение Telegram API
Бот автоматически подождет и повторит запрос
```

**Проблема: "Группа стала приватной"**
```
Решение: 
1. Убедитесь, что бот добавлен в группу как администратор
2. Проверьте права бота в настройках группы
```

**Проблема: "Build failed with Nixpacks"**
```
Решение:
1. Проверьте, что requirements.txt корректный
2. Убедитесь, что нет конфликтующего Dockerfile
3. Очистите кеш Railway и попробуйте снова
```

## 📅 Расписание работы

После успешного деплоя бот будет автоматически:
- **Каждый час**: собирать аналитические данные
- **Ежедневно в 09:00**: отправлять дневные отчеты подписчикам
- **Понедельник в 09:00**: отправлять недельные отчеты
- **1 число в 09:00**: отправлять месячные отчеты

## 🎯 Первые шаги после развертывания

1. **Протестируйте основные команды:**
   ```
   /start
   /help
   /daily
   ```

2. **Подпишитесь на отчеты:**
   ```
   /subscribe daily
   ```

3. **Добавьте группы для мониторинга**

4. **Проверьте health check через 24 часа**

## 🔄 Обновление бота

1. Внесите изменения в код
2. Закоммитьте и запушьте в GitHub:
   ```bash
   git add .
   git commit -m "Update bot features"
   git push
   ```
3. Railway автоматически развернет обновления

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи в Railway
2. Убедитесь, что все переменные окружения настроены
3. Проверьте health check endpoint
4. Убедитесь, что выбран правильный способ сборки (Nixpacks ИЛИ Dockerfile)
5. Проверьте, что requirements.txt находится в корне проекта
6. Создайте Issue в GitHub репозитории
