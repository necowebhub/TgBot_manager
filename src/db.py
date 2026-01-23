import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager
from api import DonationAlertsAPI
from logger_config import setup_logger

logger = setup_logger(__name__)


class DonationDB:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.getenv('DB_PATH', '/app/data/donations.db')

        self.db_path = db_path

        logger.info(f"Инициализация БД: {db_path}")
        self._init_database()
    
    def _init_database(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
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
            conn.commit()
        logger.info("База данных инициализирована")
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _calculate_sub_date(self, base_date, amount):
        months_to_add = int(amount // 200)
        logger.debug(f"Расчет даты подписки: база={base_date}, сумма={amount}, месяцев={months_to_add}")

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
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT id, amount, sub FROM donations WHERE message = ?',
                    (message,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    donation_id = existing[0]
                    old_amount = existing[1]
                    old_sub = existing[2]

                    new_amount = old_amount + amount

                    if old_sub:
                        new_sub = self._calculate_sub_date(old_sub, amount)
                    else:
                        new_sub = self._calculate_sub_date(datetime.now(), amount)

                    cursor.execute('''
                        UPDATE donations 
                        SET amount = ?, last_date = ?, sub = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE message = ?
                    ''', (new_amount, last_date, new_sub, message))
                    conn.commit()
                    logger.info(f"Обновлен донат ID {donation_id}: {message[:50]}... (сумма: {old_amount} -> {new_amount})")
                    return ('updated', donation_id)
                else:
                    sub_date = self._calculate_sub_date(datetime.now(), amount)
                    
                    cursor.execute('''
                        INSERT INTO donations (message, amount, last_date, sub)
                        VALUES (?, ?, ?, ?)
                    ''', (message, amount, last_date, sub_date))
                    conn.commit()
                    logger.info(f"Добавлен новый донат ID {cursor.lastrowid}: {message[:50]}... (сумма: {amount})")
                    return ('inserted', cursor.lastrowid)
                    
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении доната '{message[:50]}...': {e}", exc_info=True)
            return (None, None)
    
    def save_donations_batch(self, donations):
        stats = {
            'inserted': 0,
            'updated': 0,
            'failed': 0,
            'total': len(donations)
        }
        
        logger.info(f"Начало пакетного сохранения {stats['total']} донатов")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                for donation in donations:
                    message = donation.get('message', '')
                    amount = donation.get('amount', 0)
                    last_date = donation.get('last_date', '')
                    
                    if not message:
                        stats['failed'] += 1
                        continue
                    
                    try:
                        cursor.execute(
                            'SELECT id, amount, sub FROM donations WHERE message = ?',
                            (message,)
                        )
                        existing = cursor.fetchone()
                        
                        if existing:
                            donation_id = existing[0]
                            old_amount = existing[1]
                            old_sub = existing[2]

                            new_amount = old_amount + amount

                            if old_sub:
                                new_sub = self._calculate_sub_date(old_sub, amount)
                            else:
                                new_sub = self._calculate_sub_date(datetime.now(), amount)

                            cursor.execute('''
                                UPDATE donations 
                                SET amount = ?, last_date = ?, sub = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE message = ?
                            ''', (new_amount, last_date, new_sub, message))
                            stats['updated'] += 1
                        else:
                            sub_date = self._calculate_sub_date(datetime.now(), amount)
                            
                            cursor.execute('''
                                INSERT INTO donations (message, amount, last_date, sub)
                                VALUES (?, ?, ?, ?)
                            ''', (message, amount, last_date, sub_date))
                            stats['inserted'] += 1

                    except sqlite3.Error as e:
                        logger.error(f"Ошибка при обработке доната '{message[:50]}...': {e}")
                        stats['failed'] += 1
                
                conn.commit()
                logger.info(f"Пакетное сохранение завершено: добавлено={stats['inserted']}, обновлено={stats['updated']}, ошибок={stats['failed']}")

        except sqlite3.Error as e:
            logger.error(f"Критическая ошибка при пакетном сохранении: {e}", exc_info=True)
            stats['failed'] = stats['total']
            stats['inserted'] = 0
            stats['updated'] = 0

        return stats
    
    def get_all_donations(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM donations ORDER BY last_date DESC')
            result = cursor.fetchall()
            logger.debug(f"Получено всех донатов: {len(result)}")
            return result
    
    def _escape_like_pattern(self, pattern):
        escape_chars = ['%', '_', '[', ']']
        for char in escape_chars:
            pattern = pattern.replace(char, f'\\{char}')
        return pattern
    
    def _validate_username(self, username):
        if not username or not isinstance(username, str):
            return False
        
        if len(username) < 1 or len(username) > 100:
            return False

        if '\x00' in username:
            return False
        
        return True
    
    def get_user_donations(self, username):
        if not self._validate_username(username):
            logger.warning(f"Невалидный username: '{username}'")
            return []
        
        username = username.strip()
        safe_username = self._escape_like_pattern(username)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT amount, last_date, sub
                FROM donations 
                WHERE message LIKE ? ESCAPE '\\'
            ''', (f'%{safe_username}%',))
            result = cursor.fetchall()
            logger.debug(f"Найдено донатов для пользователя '{username}': {len(result)}")
            return result
    
    def get_user_donations_exact(self, username):
        if not self._validate_username(username):
            logger.warning(f"Невалидный username: '{username}'")
            return []
        
        username = username.strip()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT amount, last_date, sub
                FROM donations 
                WHERE message = ? OR message LIKE ? ESCAPE '\\'
            ''', (username, f'%@{self._escape_like_pattern(username)}%'))
            result = cursor.fetchall()
            logger.debug(f"Найдено донатов (точное совпадение) для пользователя '{username}': {len(result)}")
            return result
    
    def get_expired_subscriptions(self):
        current_time = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, message, sub
                FROM donations
                WHERE sub < ?
            ''', (current_time,))
            result = cursor.fetchall()
            logger.info(f"Найдено истекших подписок: {len(result)}")
            return result


def process_donations(start_date, end_date, ACCESS_TOKEN):
    logger.info(f"Получение донатов за период: {start_date} - {end_date}")
    
    api = DonationAlertsAPI(ACCESS_TOKEN)
    donations_data = api.get_all_donations_in_range(start_date, end_date)
    
    if not donations_data:
        logger.info("Донаты не найдены")
        return
    
    db = DonationDB()
    stats = db.save_donations_batch(donations_data)
    
    return stats


def user_donations(username):
    logger.info(f"Получение донатов пользователя: {username}")
    db = DonationDB()
    return db.get_user_donations(username)


def get_expired_users():
    db = DonationDB()
    return db.get_expired_subscriptions()
