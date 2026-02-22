FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание директории для данных
RUN mkdir -p /data
ENV DATABASE_PATH=/data/elaim.db

# Запуск
CMD ["python", "bot.py"]
