import requests
from datetime import datetime
from typing import List, Dict, Optional
import json


class DonationAlertsAPI:
    """Класс для работы с API DonationAlerts"""
    
    BASE_URL = "https://www.donationalerts.com/api/v1"
    
    def __init__(self, access_token: str):
        """
        Инициализация API клиента
        
        Args:
            access_token: OAuth токен доступа
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def get_donations(self, page: int = 1) -> Dict:
        """
        Получить донаты с указанной страницы
        
        Args:
            page: Номер страницы (по умолчанию 1)
            
        Returns:
            Словарь с данными о донатах
        """
        url = f"{self.BASE_URL}/alerts/donations"
        params = {"page": page}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к API: {e}")
            return {}
    
    def get_all_donations_in_range(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Получить все донаты за указанный период
        
        Args:
            start_date: Начальная дата периода
            end_date: Конечная дата периода
            
        Returns:
            Список донатов за указанный период
        """
        all_donations = []
        page = 1
        
        while True:
            print(f"Загрузка страницы {page}...")
            data = self.get_donations(page)
            
            if not data or 'data' not in data:
                break
            
            donations = data['data']
            
            if not donations:
                break
            
            # Фильтруем донаты по дате
            for donation in donations:
                donation_date = datetime.fromisoformat(
                    donation['created_at'].replace('Z', '+00:00')
                )
                
                # Проверяем попадание в диапазон дат
                if start_date and donation_date < start_date:
                    return all_donations  # Достигли старых донатов, прекращаем
                
                if end_date and donation_date > end_date:
                    continue  # Пропускаем более новые донаты
                
                if (not start_date or donation_date >= start_date) and (not end_date or donation_date <= end_date):

                    all_donations.append(donation)
            
            # Проверяем наличие следующей страницы
            links = data.get('links', {})
            if not links.get('next'):
                break
            
            page += 1
        
        return all_donations
    
    def format_donation(self, donation: Dict) -> Dict:
        """
        Форматирование данных доната для удобного отображения
        
        Args:
            donation: Словарь с данными доната
            
        Returns:
            Отформатированный словарь с основными данными
        """
        return {
            'id': donation.get('id'),
            'донатер': donation.get('username', 'Аноним'),
            'сумма': f"{donation.get('amount', 0)} {donation.get('currency', '')}",
            'сообщение': donation.get('message', ''),
            'дата': donation.get('created_at'),
            'показано': donation.get('shown_at')
        }
    
    def export_to_json(self, donations: List[Dict], filename: str = "donations.json"):
        """
        Экспорт донатов в JSON файл
        
        Args:
            donations: Список донатов
            filename: Имя файла для сохранения
        """
        formatted_donations = [self.format_donation(d) for d in donations]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(formatted_donations, f, ensure_ascii=False, indent=2)
        
        print(f"\nДанные сохранены в файл: {filename}")
    
