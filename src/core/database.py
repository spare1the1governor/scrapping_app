'''
Модуль для сохранения данных в базу данных и экспорта в Excel'''
import sqlite3
import pandas as pd
from pathlib import Path
from data.mapping import mapping_320



class DatabaseSaver:
    def __init__(self, db_path: Path | None = None):

        if db_path is None:
            project_root = Path(__file__).resolve().parents[2]
            db_path = project_root / "data" / "final_info.db"

        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self.create_final_table()

    
    
    def create_final_table(self):
        """Создает итоговую таблицу в БД"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS final_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                direction_names TEXT,
                city_name TEXT,
                faculty TEXT,
                faculty_id TEXT,
                university_name TEXT,
                ege TEXT,
                cost TEXT,
                points_for_budget TEXT,
                budget_funded TEXT,
                points_for_contract TEXT,
                contract_funded TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    
    def save_all_data(self,scrapping_list) :
     """"Сохраняет все данные из списка скраппинга в БД"""   
     cursor= self.conn.cursor()
     #тк бд промежуточное хранилище использую одну таблицу , очищая перед новым запуском 
     cursor.execute('DELETE FROM final_info')
     
     to_isert=[]
     for data in scrapping_list:
         to_isert.append((
             data['direction_names'],
             data['city_name'],
             data['faculty'],
             data['faculty_id'],
             data['university_name'],
             data['ege'],
             data['cost'],
             data['points_for_budget'],
             data['budget_funded'],
             data['points_for_contract'],
             data['contract_funded']
         ))
     try: 
            cursor.executemany('''
                INSERT INTO final_info 
                (direction_names, city_name, faculty,faculty_id, university_name, ege, cost, points_for_budget, budget_funded, points_for_contract, contract_funded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
            ''', to_isert)
            self.conn.commit()
            print(f"  Успешно сохранено {len(scrapping_list)} записей в итоговую таблицу")
     except Exception as e:
            print(f"  Ошибка при сохранении батча в итоговую таблицу: {e}")
        
    def export_to_excel_programs(self, filename):
        """Экспортирует данные из БД в CSV"""
        df = pd.read_sql_query("SELECT * FROM final_info", self.conn)
        #деление на обязательные егэ и по выбору
        df[['ege','ege_1']] = df['ege'].str.rsplit(',', n=1, expand=True)
        try: 
            tmp = df["faculty"].map(mapping_320).apply(pd.Series)
            tmp.columns = ["faculty_macro", "faculty"]# переименование колонок          
            df[["faculty_macro", "faculty"]] = tmp  
        except Exception as e:
            print(f" Ошибка при маппинге факультетов: {e}")    
            
        df = df.rename(columns={'direction_names': 'направление', 'city_name': 'город', 'faculty': 'факультет', 'faculty_id': '№ направления',
                           'university_name': 'университет', 'ege': 'обязательные ЕГЭ', 'ege_1': 'ЕГЭ по выбору', 'cost': 'стоимость', 'points_for_budget': 'баллы для бюджета',
                           'budget_funded': 'бюджетные места', 'points_for_contract': 'баллы для контракта', 'contract_funded': 'контрактные места'})
        df.to_excel(filename, index=False)

        print(f"Данные экспортированы в {filename}") 
        
        
    def close(self):
        self.conn.close()
   