#!/bin/bash
# docker-manage.sh

set -e

case "$1" in
  build)
    echo "🔨 Сборка Docker образа..."
    docker-compose build
    ;;
  
  start)
    echo "🚀 Запуск бота..."
    docker-compose up -d
    echo "✅ Бот запущен!"
    ;;
  
  stop)
    echo "🛑 Остановка бота..."
    docker-compose stop
    echo "✅ Бот остановлен!"
    ;;
  
  restart)
    echo "🔄 Перезапуск бота..."
    docker-compose restart
    echo "✅ Бот перезапущен!"
    ;;
  
  logs)
    echo "📋 Логи бота (Ctrl+C для выхода):"
    docker-compose logs -f
    ;;
  
  shell)
    echo "🐚 Вход в контейнер..."
    docker-compose exec tgbot /bin/bash
    ;;
  
  status)
    echo "📊 Статус контейнера:"
    docker-compose ps
    ;;
  
  clean)
    echo "🧹 Очистка (удаление контейнера)..."
    docker-compose down
    echo "✅ Контейнер удален!"
    ;;
  
  rebuild)
    echo "🔄 Пересборка с нуля..."
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    echo "✅ Бот пересобран и запущен!"
    ;;
  
  backup)
    echo "💾 Создание backup базы данных..."
    mkdir -p backups
    cp data/donations.db "backups/donations_$(date +%Y%m%d_%H%M%S).db"
    echo "✅ Backup создан в директории backups/"
    ;;
  
  *)
    echo "Использование: $0 {build|start|stop|restart|logs|shell|status|clean|rebuild|backup}"
    exit 1
    ;;
esac