import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from core.database import DatabaseSaver
import logging  

class ScrapperOptimized:
    def __init__(self, db, delay=1.0): 
        self.db = db
        self.delay = delay # 1 сек между запросами
        self.session = self._create_session()
        self.total_saved = 0
        self.total_errors = 0
    
    def _create_session(self):
        """Создаёт сессию с повторными попытками"""
        session = requests.Session() #создаем переиспользуемую сессию 
        retry = Retry(
            total=3,#кол-во попыток
            backoff_factor=0.5,#время между попытками 
            status_forcelist=[500, 502, 503, 504]# повторные попытки при ошибках сервера
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)#привязка адаптера к протоколам
        session.mount('https://', adapter)
        return session
    
    def _get_page(self, url):
        """Безопасный запрос страницы с задержкой"""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logging.error(f"   Ошибка загрузки {url}: {e}")
            return None
    
    def _get_total_pages(self, soup):
        """Определяет количество страниц"""
        page_block = soup.find("ul", class_="pagination")
        if page_block:
            numbers = [int(num) for num in re.findall(r'\d+', page_block.text)]
            return max(numbers) if numbers else 1
        return 1
    
    def _parse_program_block(self, block, city_name, university_name):
        """Парсит один блок программы"""
        try:
            textt = block.find("div", class_="col-md-2")
            if not textt:
                return None
            textt = textt.get_text(strip=True)
            
            def safe_search(pattern):
                match = re.search(pattern, textt)
                return match.group(1) if match else None
            
            # Проверяем обязательные поля
            title = block.find(class_='newItemSpPrTitle')
            osnBlock = block.find("div", class_="osnBlockInfoSm")
            cost_block = block.find(class_='col-md-12 col-sm-4 col-xs-4 mg10Prm')
            
            # Ищем количество платных мест
            paid_funded = safe_search(r"Уточните у вуза\s*(\d+)")
            if not paid_funded:
                paid_funded = safe_search(r"по программе\s*(\d+)")
            
            if not all([title, osnBlock, cost_block]):
                return None
            
            faculty_link = osnBlock.find("a")
            if not faculty_link:
                return None
            
            return {
                'derection_names': title.text.strip(),
                'city_name': city_name,
                'faculty': faculty_link.get_text(strip=True).split("|", 1)[-1].strip(),
                'university_name': university_name,
                'ege': osnBlock.get_text(strip=True).split(":")[1] if ":" in osnBlock.get_text() else "",
                'cost': cost_block.text.replace('Стоимость', '').replace('₽минимальная стоимость по программе (руб/год)', '').strip(),
                'points_for_budget': safe_search(r"\(руб/год\)Бюджетот (\d+|\?)"),
                'budget_funded': safe_search(r"конкурс\)\s*(\d+)"),
                'points_for_contract': safe_search(r"Платноеот\s*(\d+)"),
                'contract_funded': paid_funded
            }
        except Exception as e:
            logging.error(f" Ошибка парсинга блока: {e}")
            return None
    
    def _parse_university_page(self, soup, page_num, total_pages, city_name, university_name):
        """Парсит одну страницу университета"""
        all_blocks = soup.find_all('div', class_='newBlockSpecProg')
        
        page_results = []
        
        for block in all_blocks:
            # На последней странице проверяем, не закончились ли актуальные программы
            if page_num == total_pages:
                previous_h3 = block.find_previous("h3")
                if previous_h3 and "Программы, на которые не ведется набор" in previous_h3.text:
                    break
            
            program_data = self._parse_program_block(block, city_name, university_name)
            if program_data:
                page_results.append(program_data)
        
        return page_results
    
    def scrape_university(self, uni_id, university_name, city_name):
        """Парсит один университет"""
        
        logging.info(f"\n Обработка: {university_name} ({uni_id})")
        
        # Получаем первую страницу
        first_url = f'https://vuzopedia.ru/vuz/{uni_id}/programs/bakispec?page=1'
        first_soup = self._get_page(first_url)
        
        if not first_soup:
            logging.error(f"   Не удалось загрузить первую страницу")
            self.total_errors += 1
            return 0
        
        # Определяем количество страниц
        total_pages = self._get_total_pages(first_soup)
        logging.debug(f" Найдено страниц: {total_pages}")
        
        uni_total = 0
        
        # Парсим все страницы
        for page_num in range(1, total_pages + 1):
            url = f'https://vuzopedia.ru/vuz/{uni_id}/programs/bakispec?page={page_num}'
            
            # Используем уже загруженную первую страницу
            soup = first_soup if page_num == 1 else self._get_page(url)
            
            if not soup:
                continue
            
            # Парсим программы на странице
            page_results = self._parse_university_page(
                soup, page_num, total_pages, city_name, university_name
            )
            
            # Сохраняем батчами (по страницам)
            if page_results:
                try:
                    self.db.save_all_data(page_results)
                    uni_total += len(page_results)
                    logging.debug(f"  Страница {page_num}/{total_pages}: сохранено {len(page_results)} программ")
                except Exception as e:
                    logging.error(f"  Ошибка сохранения страницы {page_num}: {e}")
                    self.total_errors += 1
        
        logging.debug(f"  Итого по вузу: {uni_total} программ")
        self.total_saved += uni_total
        return uni_total
    
    def scrape_all(self, csv_file="necessary_notes.csv"):
        """Парсит все университеты из CSV"""
        logging.basicConfig(level=logging.INFO,filename='scraper.log',filemode='w')
        logging.info(" Начало скраппинга...")
        
        project_root = os.path.dirname(os.path.abspath(__file__))
        csv_file = os.path.join(project_root, "data", csv_file)
        
        try:
            df = pd.read_csv(csv_file)
            logging.info(f"Загружено университетов: {len(df)}")
        except Exception as e:
            logging.error(f" Ошибка чтения CSV: {e}")
            return
        
        start_time = time.time()
        
        for i in range(len(df)):
            series = df.iloc[i, 0:3]
            uni_id = series[0]
            university_name = series[1]
            city_name = series[2]
            self.scrape_university(uni_id, university_name, city_name)
        
        elapsed = time.time() - start_time

        logging.info(f"\n{'='*60}")
        logging.info(f"✅ Скраппинг завершён!")
        logging.info(f" Всего сохранено программ: {self.total_saved}")
        logging.info(f"Ошибок: {self.total_errors}")
        logging.info(f" Время выполнения: {elapsed:.1f} сек ({elapsed/60:.1f} мин)")
        
        self.db.close()


# Использование:
def scrapping():    
    db = DatabaseSaver()
    scraper = ScrapperOptimized(db)  
    scraper.scrape_all()


