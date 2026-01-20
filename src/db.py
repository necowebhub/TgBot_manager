import sqlite3
from datetime import datetime
from api import DonationAlertsAPI


class DonationDB:
    def __init__(self, db_path='donations.db'):
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self._connect()
        self._create_table()
    
    def _connect(self):
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
    
    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                last_date TEXT NOT NULL,
                sub TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.connection.commit()
    
    def save_donation(self, message, amount, date):
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
        self.cursor.execute('SELECT * FROM donations ORDER BY date DESC')
        return self.cursor.fetchall()
    
    def get_user_donations(self, username):
        self.cursor.execute('''
            SELECT amount, date, sub
            FROM donations 
            WHERE message LIKE ?
        ''', (f'%{username}%',))
        return self.cursor.fetchall()
    
    def close(self):
        if self.connection:
            self.connection.close()


def process_donations(start_date, end_date, ACCESS_TOKEN):
    print(f"Получение донатов за период: {start_date} - {end_date}")
    
    api = DonationAlertsAPI(ACCESS_TOKEN)
    
    donations_data = api.get_all_donations_in_range(start_date, end_date)
    
    if not donations_data:
        print("Донаты не найдены")
        return
    
    db = DonationDB()
    
    try:
        stats = db.save_donations_batch(donations_data)
        """
        print("\n=== Статистика обработки ===")
        print(f"Всего обработано: {stats['total']}")
        print(f"Добавлено новых: {stats['inserted']}")
        print(f"Обновлено: {stats['updated']}")
        print(f"Ошибок: {stats['failed']}")
        """
        return stats    
    finally:
        db.close()

def user_donations(username):
    print(f"Получение донатов пользователя {username}")
    db = DonationDB()

    try:
        stats = db.get_user_donations(username)
        return stats
    finally:
        db.close()