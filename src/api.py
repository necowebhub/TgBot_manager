import requests
from datetime import datetime
from typing import List, Dict, Optional
import json
import time


class DonationAlertsAPIException(Exception):
    pass

class DonationAlertsAuthException(DonationAlertsAPIException):
    pass

class DonationAlertsRateLimitException(DonationAlertsAPIException):
    pass

class DonationAlertsAPI:
    BASE_URL = "https://www.donationalerts.com/api/v1"
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self, access_token: str):
        if not access_token or not access_token.strip():
            raise ValueError("Access token не может быть пустым")

        self.access_token = access_token.strip()
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    def _handle_response(self, response: requests.Response) -> Dict:
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = response.status_code

            if status_code == 401:
                raise DonationAlertsAuthException(
                    "Ошибка аутентификации: неверный или истекший токен"
                ) from e
            elif status_code == 403:
                raise DonationAlertsAuthException(
                    "Доступ запрещён: недостаточно прав"
                ) from e
            elif status_code == 429:
                raise DonationAlertsRateLimitException(
                    "Превышен лимит запросов к API"
                ) from e
            elif status_code >= 500:
                raise DonationAlertsAPIException(
                    f"Ошибка сервера DonationAlerts ({status_code})"
                ) from e
            else:
                raise DonationAlertsAPIException(
                    f"Ошибка API ({status_code}): {e}"
                ) from e
        except requests.exceptions.JSONDecodeError as e:
            raise DonationAlertsAPIException(
                "Не удалось разобрать ответ от API"
            ) from e
    
    def get_donations(self, page: int = 1, retry_count: int = 0) -> Optional[Dict]:
        url = f"{self.BASE_URL}/alerts/donations"
        params = {"page": page}
        
        try:
            response = requests.get(
                url, 
                headers=self.headers, 
                params=params,
                timeout=30
            )
            return self._handle_response(response)
        
        except DonationAlertsAuthException:
            raise

        except DonationAlertsRateLimitException as e:
            if retry_count < self.MAX_RETRIES:
                wait_time = self.RETRY_DELAY * (2 ** retry_count)  # Exponential backoff
                print(f"Rate limit достигнут. Ожидание {wait_time} секунд...")
                time.sleep(wait_time)
                return self.get_donations(page, retry_count + 1)
            else:
                print(f"Превышено количество попыток при rate limit")
                raise

        except (requests.exceptions.RequestException, DonationAlertsAPIException) as e:
            if retry_count < self.MAX_RETRIES:
                print(f"Ошибка при запросе (попытка {retry_count + 1}/{self.MAX_RETRIES}): {e}")
                time.sleep(self.RETRY_DELAY)
                return self.get_donations(page, retry_count + 1)
            else:
                print(f"Критическая ошибка после {self.MAX_RETRIES} попыток: {e}")
                return None
    

    def get_all_donations_in_range(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        
        all_donations = []
        page = 1
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 3
        
        while True:
            print(f"Загрузка страницы {page}...")
            
            try:
                data = self.get_donations(page)

                if data is None:
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        print(f"Прекращение загрузки после {MAX_CONSECUTIVE_ERRORS} последовательных ошибок")
                        break
                    continue

                consecutive_errors = 0
                
                if 'data' not in data:
                    print(f"Предупреждение: отсутствует поле 'data' в ответе API")
                    break
                
                donations = data['data']
                
                if not donations:
                    print("Достигнут конец списка донатов")
                    break
                
                for donation in donations:
                    try:
                        donation_date = datetime.fromisoformat(
                            donation['created_at'].replace('Z', '+00:00')
                        )
                        
                        if start_date and donation_date < start_date:
                            print(f"Достигнута начальная дата ({start_date}), прекращаем загрузку")
                            return all_donations
                        
                        if end_date and donation_date > end_date:
                            continue
                        
                        if (not start_date or donation_date >= start_date) and (not end_date or donation_date <= end_date):

                            all_donations.append(donation)

                    except (KeyError, ValueError) as e:
                        print(f"Ошибка обработки доната: {e}")
                        continue
                
                links = data.get('links', {})
                if not links.get('next'):
                    print("Достигнута последняя страница")
                    break
                
                page += 1

                time.sleep(0.5)

            except DonationAlertsAuthException:
                raise
            except Exception as e:
                print(f"Неожиданная ошибка при обработке страницы {page}: {e}")
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print(f"Прекращение после {MAX_CONSECUTIVE_ERRORS} ошибок")
                    break
        
        print(f"Всего загружено донатов: {len(all_donations)}")
        return all_donations
    
    def format_donation(self, donation: Dict) -> Dict:
        return {
            'id': donation.get('id'),
            'донатер': donation.get('username', 'Аноним'),
            'сумма': f"{donation.get('amount', 0)} {donation.get('currency', '')}",
            'сообщение': donation.get('message', ''),
            'дата': donation.get('created_at'),
            'показано': donation.get('shown_at')
        }
    
    def export_to_json(self, donations: List[Dict], filename: str = "donations.json"):
        try:
            formatted_donations = [self.format_donation(d) for d in donations]
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(formatted_donations, f, ensure_ascii=False, indent=2)
            
            print(f"\nДанные сохранены в файл: {filename}")
        except IOError as e:
            print(f"Ошибка при сохранении файла: {e}")
            raise
