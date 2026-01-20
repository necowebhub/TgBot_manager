import sqlite3
from datetime import datetime, timedelta
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
    
    def _calculate_sub_date(self, base_date, amount):
        months_to_add = int(amount // 200)

        if isinstance(base_date, str):
            base_date = datetime.fromisoformat(base_date.replace('Z', '+00:00'))
        elif not isinstance(base_date, datetime):
            base_date = datetime.now()

        new_date = base_date
        for _ in range(months_to_add):
            month = new_date.month
            year = new_date.year

            if month == 12:
                month = 1
                year += 1
            else:
                month += 1

            day = min(new_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])

            new_date = new_date.replace(year=year, month=month, day=day)

        return new_date.isoformat()
    
    def save_donation(self, message, amount, last_date):
        try:
            self.cursor.execute(
                'SELECT id, amount, sub FROM donations WHERE message = ?',
                (message,)
            )
            existing = self.cursor.fetchone()
            
            if existing:
                donation_id = existing[0]
                old_amount = existing[1]
                old_sub = existing[2]

                new_amount = old_amount + amount

                if old_sub:
                    new_sub = self._calculate_sub_date(old_sub, amount)
                else:
                    new_sub = self._calculate_sub_date(datetime.now(), amount)

                self.cursor.execute('''
                    UPDATE donations 
                    SET amount = ?, last_date = ?, sub = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE message = ?
                ''', (new_amount, last_date, new_sub, message))
                self.connection.commit()
                return ('updated', donation_id)
            else:
                sub_date = self._calculate_sub_date(datetime.now(), amount)
                
                self.cursor.execute('''
                    INSERT INTO donations (message, amount, last_date, sub)
                    VALUES (?, ?, ?, ?)
                ''', (message, amount, last_date, sub_date))
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
            last_date = donation.get('last_date', '')
            
            if not message:
                stats['failed'] += 1
                continue
            
            action, _ = self.save_donation(message, amount, last_date)
            
            if action == 'inserted':
                stats['inserted'] += 1
            elif action == 'updated':
                stats['updated'] += 1
            else:
                stats['failed'] += 1
        
        return stats
    
    def get_all_donations(self):
        self.cursor.execute('SELECT * FROM donations ORDER BY last_date DESC')
        return self.cursor.fetchall()
    
    def get_user_donations(self, username):
        self.cursor.execute('''
            SELECT amount, last_date, sub
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