# 🛠️ Решение проблем Docker и Railway деплоя

## ❌ Проблема: Docker build failed при установке зависимостей

### Симптомы:
```
✕ [5/7] RUN pip install --upgrade pip &&     pip install --no-cache-dir -r requirements.txt 
process "/bin/sh -c pip install --upgrade pip &&     pip install --no-cache-dir -r requirements.txt" did not complete successfully: exit code: 1
```

### 🔧 Решение:

#### 1. Системные зависимости для matplotlib
Обновленный `Dockerfile` включает все необходимые системные пакеты:

```dockerfile
# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    pkg-config \
    libfreetype6-dev \
    libpng-dev \
    libjpeg-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*
```

#### 2. Стабильные версии пакетов
Обновлен `requirements.txt` с проверенными совместимыми версиями:

```
aiogram==3.7.0
aiohttp==3.9.5
sqlalchemy==2.0.30
matplotlib==3.8.4
plotly==5.17.0
```

#### 3. Минимальная версия без визуализации
Если проблемы с matplotlib продолжаются, используйте `requirements.minimal`:

```bash
# Переименовать файлы
mv requirements.txt requirements.full
mv requirements.minimal requirements.txt

# Пересобрать
docker build -t telegram-analytics .
```

## 🚀 Варианты деплоя

### Вариант 1: Docker с полными возможностями
```bash
# Использовать основной Dockerfile
docker build -t telegram-analytics .
docker run --env-file .env -p 8000:8000 telegram-analytics
```

### Вариант 2: Railway с минимальными зависимостями  
```bash
# 1. Переключиться на минимальные зависимости
mv requirements.txt requirements.full
mv requirements.minimal requirements.txt

# 2. Commit и push
git add .
git commit -m "fix: Use minimal requirements for Railway deployment"
git push origin main

# 3. Railway автоматически пересоберет
```

### Вариант 3: Nixpacks вместо Docker
Обновить `railway.json`:

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python main_v2.py"
  }
}
```

## 📋 Быстрое решение проблем

### 1. Ошибки компиляции matplotlib
```bash
# В Dockerfile добавить:
RUN apt-get install -y build-essential python3-dev
```

### 2. Ошибки памяти при сборке
```bash
# Использовать минимальные требования
cp requirements.minimal requirements.txt
```

### 3. Проблемы с Python версией
```bash
# В Dockerfile изменить на:
FROM python:3.11-slim  # вместо 3.12
```

### 4. Railway timeout
```bash
# Увеличить timeout в railway.json:
"healthcheckTimeout": 60
```

## ✅ Проверка работоспособности

### Локальная проверка:
```bash
# Тест Docker сборки
docker build -t test-build .

# Тест установки зависимостей
pip install -r requirements.txt

# Тест запуска
python main_v2.py
```

### Railway проверка:
```bash
# Проверить логи
railway logs --tail

# Проверить health endpoint
curl https://your-app.railway.app/health
```

## 🎯 Рекомендуемая последовательность

1. **Попробовать основной Dockerfile** - включает все возможности
2. **Если ошибки компиляции** - использовать `requirements.minimal`  
3. **Если продолжаются проблемы** - переключиться на Nixpacks
4. **Для production** - вернуться к полной версии после стабилизации

## 📞 Диагностика

### Проверить логи сборки:
```bash
# Railway
railway logs --tail

# Docker
docker build -t test . --progress=plain
```

### Проверить версии:
```bash
python --version  # Должно быть 3.11+
pip --version     # Должно быть 21.0+
```

### Проверить системные зависимости:
```bash
# В контейнере
apt list --installed | grep -E "(gcc|python|dev)"
```

---

**💡 Главное:** Система работает стабильно с обновленными Dockerfile и requirements.txt. Проблемы возникают только при сборке в ресурсоограниченных средах.
