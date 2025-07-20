# Используем образ Ubuntu 20.04
FROM ubuntu:20.04

# Устанавливаем Python и pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Создаем символическую ссылку для python и pip
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN --mount=type=cache,id=s/caed778b-954c-46ae-a48d-e3bfbc8beb47-/root/cache/pip,target=/root/.cache/pip pip install -r requirements.txt

# Копируем остальные файлы приложения
COPY . .

# Команда запуска
CMD ["python", "main.py"]
