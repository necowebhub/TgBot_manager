import sqlite3
from datetime import datetime
from api import get_all_donations_in_range


class DonationDB:
    def __init__(self, db_path='donations.db'):
        """Инициализация подключения к БД"""
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self._connect()
        self._create_table()
    
    def _connect(self):
        """Создание подключения к БД"""
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
    
    def _create_table(self):
        """Создание таблицы для донатов, если её нет"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.connection.commit()
    
    def save_donation(self, message, amount, date):
        """
        Сохранение или обновление доната в БД
        
        Args:
            message: Сообщение донатера
            amount: Сумма доната
            date: Дата доната
        
        Returns:
            tuple: (action, donation_id) где action - 'inserted' или 'updated'
        """
        try:
            # Проверяем, существует ли запись с таким сообщением
            self.cursor.execute(
                'SELECT id, amount, date FROM donations WHERE message = ?',
                (message,)
            )
            existing = self.cursor.fetchone()
            
            if existing:
                # Обновляем существующую запись
                donation_id = existing[0]
                self.cursor.execute('''
                    UPDATE donations 
                    SET amount = ?, date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE message = ?
                ''', (amount, date, message))
                self.connection.commit()
                return ('updated', donation_id)
            else:
                # Вставляем новую запись
                self.cursor.execute('''
                    INSERT INTO donations (message, amount, date)
                    VALUES (?, ?, ?)
                ''', (message, amount, date))
                self.connection.commit()
                return ('inserted', self.cursor.lastrowid)
                
        except sqlite3.Error as e:
            print(f"Ошибка при сохранении доната: {e}")
            self.connection.rollback()
            return (None, None)
    
    def save_donations_batch(self, donations):
        """
        Сохранение пакета донатов
        
        Args:
            donations: Список словарей с ключами 'message', 'amount', 'date'
        
        Returns:
            dict: Статистика сохранения
        """
        stats = {
            'inserted': 0,
            'updated': 0,
            'failed': 0,
            'total': len(donations)
        }
        
        for donation in donations:
            message = donation.get('message', '')
            amount = donation.get('amount', 0)
            date = donation.get('date', '')
            
            if not message:
                stats['failed'] += 1
                continue
            
            action, _ = self.save_donation(message, amount, date)
            
            if action == 'inserted':
                stats['inserted'] += 1
            elif action == 'updated':
                stats['updated'] += 1
            else:
                stats['failed'] += 1
        
        return stats
    
    def get_all_donations(self):
        """Получение всех донатов из БД"""
        self.cursor.execute('SELECT * FROM donations ORDER BY date DESC')
        return self.cursor.fetchall()
    
    def close(self):
        """Закрытие соединения с БД"""
        if self.connection:
            self.connection.close()


def process_donations(start_date, end_date):
    """
    Основная функция обработки донатов
    
    Args:
        start_date: Начальная дата периода
        end_date: Конечная дата периода
    """
    print(f"Получение донатов за период: {start_date} - {end_date}")
    
    # Получаем данные из API
    donations_data = get_all_donations_in_range(start_date, end_date)
    
    if not donations_data:
        print("Донаты не найдены")
        return
    
    # Инициализируем БД
    db = DonationDB()
    
    try:
        # Сохраняем донаты
        stats = db.save_donations_batch(donations_data)
        
        # Выводим статистику
        print("\n=== Статистика обработки ===")
        print(f"Всего обработано: {stats['total']}")
        print(f"Добавлено новых: {stats['inserted']}")
        print(f"Обновлено: {stats['updated']}")
        print(f"Ошибок: {stats['failed']}")
        
    finally:
        db.close()


if __name__ == '__main__':
    # Пример использования
    # Укажите нужный период
    start_date = '2024-01-01'
    end_date = '2024-12-31'
    
    process_donations(start_date, end_date)
