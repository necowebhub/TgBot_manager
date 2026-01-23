import requests
from datetime import datetime
from typing import List, Dict, Optional
import json
import time
from logger_config import setup_logger

logger = setup_logger(__name__)


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
            logger.error("Попытка инициализации API с пустым токеном")
            raise ValueError("Access token не может быть пустым")

        self.access_token = access_token.strip()
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        logger.info("DonationAlertsAPI инициализирован")

    def _handle_response(self, response: requests.Response) -> Dict:
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = response.status_code

            if status_code == 401:
                logger.error(f"Ошибка аутентификации (401): неверный или истекший токен")
                raise DonationAlertsAuthException(
                    "Ошибка аутентификации: неверный или истекший токен"
                ) from e
            elif status_code == 403:
                logger.error(f"Доступ запрещён (403): недостаточно прав")
                raise DonationAlertsAuthException(
                    "Доступ запрещён: недостаточно прав"
                ) from e
            elif status_code == 429:
                logger.warning(f"Превышен лимит запросов к API (429)")
                raise DonationAlertsRateLimitException(
                    "Превышен лимит запросов к API"
                ) from e
            elif status_code >= 500:
                logger.error(f"Ошибка сервера DonationAlerts ({status_code})")
                raise DonationAlertsAPIException(
                    f"Ошибка сервера DonationAlerts ({status_code})"
                ) from e
            else:
                logger.error(f"Ошибка API ({status_code}): {e}")
                raise DonationAlertsAPIException(
                    f"Ошибка API ({status_code}): {e}"
                ) from e
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"Не удалось разобрать ответ от API: {e}")
            raise DonationAlertsAPIException(
                "Не удалось разобрать ответ от API"
            ) from e
    
    def get_donations(self, page: int = 1, retry_count: int = 0) -> Optional[Dict]:
        url = f"{self.BASE_URL}/alerts/donations"
        params = {"page": page}
        
        try:
            logger.debug(f"Запрос донатов: страница {page}, попытка {retry_count + 1}")
            response = requests.get(
                url, 
                headers=self.headers, 
                params=params,
                timeout=30
            )

            # debug: что ушло
            logger.debug("Request headers: %s", response.request.headers)
            logger.debug("Request url: %s", response.request.url)

            # debug: что вернулось
            logger.debug("Response status: %s", response.status_code)
            logger.debug("Response body: %s", response.text)
            return self._handle_response(response)
        
        except DonationAlertsAuthException:
            raise

        except DonationAlertsRateLimitException as e:
            if retry_count < self.MAX_RETRIES:
                wait_time = self.RETRY_DELAY * (2 ** retry_count)
                logger.warning(f"Rate limit достигнут. Ожидание {wait_time} секунд...")
                time.sleep(wait_time)
                return self.get_donations(page, retry_count + 1)
            else:
                logger.error(f"Превышено количество попыток при rate limit")
                raise

        except (requests.exceptions.RequestException, DonationAlertsAPIException) as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(f"Ошибка при запросе (попытка {retry_count + 1}/{self.MAX_RETRIES}): {e}")
                time.sleep(self.RETRY_DELAY)
                return self.get_donations(page, retry_count + 1)
            else:
                logger.error(f"Критическая ошибка после {self.MAX_RETRIES} попыток: {e}")
                return None
    

    def get_all_donations_in_range(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        
        logger.info(f"Начало загрузки донатов за период: {start_date} - {end_date}")
        all_donations = []
        page = 1
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 3
        
        while True:
            logger.info(f"Загрузка страницы {page}...")
            
            try:
                data = self.get_donations(page)

                if data is None:
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        logger.error(f"Прекращение загрузки после {MAX_CONSECUTIVE_ERRORS} последовательных ошибок")
                        break
                    continue

                consecutive_errors = 0
                
                if 'data' not in data:
                    logger.warning(f"Отсутствует поле 'data' в ответе API")
                    break
                
                donations = data['data']
                
                if not donations:
                    logger.info("Достигнут конец списка донатов")
                    break
                
                for donation in donations:
                    try:
                        donation_date = datetime.fromisoformat(
                            donation['created_at'].replace('Z', '+00:00')
                        )
                        
                        if start_date and donation_date < start_date:
                            logger.info(f"Достигнута начальная дата ({start_date}), прекращаем загрузку")
                            return all_donations
                        
                        if end_date and donation_date > end_date:
                            continue
                        
                        if (not start_date or donation_date >= start_date) and (not end_date or donation_date <= end_date):
                            all_donations.append(donation)

                    except (KeyError, ValueError) as e:
                        logger.error(f"Ошибка обработки доната: {e}, данные: {donation}")
                        continue
                
                links = data.get('links', {})
                if not links.get('next'):
                    logger.info("Достигнута последняя страница")
                    break
                
                page += 1
                time.sleep(0.5)

            except DonationAlertsAuthException:
                raise
            except Exception as e:
                logger.error(f"Неожиданная ошибка при обработке страницы {page}: {e}", exc_info=True)
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.error(f"Прекращение после {MAX_CONSECUTIVE_ERRORS} ошибок")
                    break
        
        logger.info(f"Всего загружено донатов: {len(all_donations)}")
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
            
            logger.info(f"Данные сохранены в файл: {filename}")
        except IOError as e:
            logger.error(f"Ошибка при сохранении файла: {e}", exc_info=True)
            raise
