#!/bin/bash

# Скрипт для быстрого запуска приложения

echo "🚀 Запуск Task Tracker..."

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker для продолжения."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose для продолжения."
    exit 1
fi

# Сборка и запуск
echo "📦 Сборка Docker образа..."
docker-compose build

echo "🔧 Инициализация базы данных..."
docker-compose up -d

echo "⏳ Ожидание запуска сервера..."
sleep 5

echo "✅ Приложение запущено!"
echo ""
echo "🌐 Откройте в браузере: http://localhost:8000"
echo ""
echo "📝 Для создания проектника выполните:"
echo "   docker-compose exec web python create_project_manager.py"
echo ""
echo "📊 Просмотр логов:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Остановка:"
echo "   docker-compose down"
