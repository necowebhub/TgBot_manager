# Dockerfile
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    sqlite3 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование requirements.txt
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всего проекта
COPY . .

# Создание директории для логов
RUN mkdir -p /app/logs

# Создание директории для базы данных
RUN mkdir -p /app/data

# Установка переменной окружения для часового пояса
ENV TZ=Europe/Moscow

# Запуск бота
CMD ["python", "src/main.py"]