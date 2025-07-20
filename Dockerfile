FROM python:3.10-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы приложения
COPY . .

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Открываем порт
EXPOSE $PORT

# Команда запуска
CMD ["python", "main.py"]
