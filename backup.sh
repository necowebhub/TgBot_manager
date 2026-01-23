#!/bin/bash
# backup.sh

BACKUP_DIR="/opt/tgbot_manager/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE="/opt/tgbot_manager/data/donations.db"

# Создание директории для backup
mkdir -p "$BACKUP_DIR"

# Backup базы данных
echo "📦 Создание backup..."
cp "$DB_FILE" "$BACKUP_DIR/donations_$DATE.db"

# Сжатие
gzip "$BACKUP_DIR/donations_$DATE.db"

echo "✅ Backup создан: donations_$DATE.db.gz"

# Удаление backups старше 30 дней
find "$BACKUP_DIR" -name "donations_*.db.gz" -mtime +30 -delete

echo "🧹 Старые backups удалены"