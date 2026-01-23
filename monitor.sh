#!/bin/bash
# monitor.sh

echo "=== TgBot Manager Monitoring ==="
echo ""

echo "📊 Статус контейнера:"
docker compose ps
echo ""

echo "💾 Использование ресурсов:"
docker stats tgbot_manager --no-stream
echo ""

echo "💿 Размер данных:"
echo "База данных: $(du -h data/donations.db 2>/dev/null | cut -f1)"
echo "Логи: $(du -sh logs/ | cut -f1)"
echo ""

echo "📈 Статистика БД:"
docker compose exec -T tgbot sqlite3 /app/data/donations.db <<EOF
SELECT 
  'Всего пользователей: ' || COUNT(*) 
FROM donations;

SELECT 
  'Сумма донатов: ' || ROUND(SUM(amount), 2) || ' руб.' 
FROM donations;

SELECT 
  'Активных подписок: ' || COUNT(*) 
FROM donations 
WHERE sub > datetime('now');
EOF
echo ""

echo "📋 Последние 5 строк из логов:"
tail -5 logs/bot_$(date +%Y-%m-%d).log 2>/dev/null || echo "Логов пока нет"