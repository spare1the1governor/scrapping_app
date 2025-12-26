"""
Главное окно приложения для скраппинга университетов
"""
#разобраться с имортами ,как да что и потом настроить сборку . еще раз внимательно рассмотреть код.
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
from datetime import datetime 
# from core.database import DatabaseSaver
# from scraper import ScrapperOptimized


# Настройка темы
ctk.set_appearance_mode("dark")  # "dark" или "light"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"


class UniversityScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Настройки окна
        self.title("🎓 Парсер университетов")
        self.geometry("900x650")
        self.minsize(800, 600)
        
        # Центрируем окно
        self.center_window()
        
        # Переменные состояния
        self.is_scraping = False
        self.excel_name = None
        self.db_path = "data/finale_info.db"
        
        # Создаём интерфейс
        self.create_widgets()
    
    def center_window(self):
        """Центрирует окно на экране"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """Создаёт все виджеты интерфейса"""
        
        # === HEADER ===
        self.header = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray85", "gray20"))
        self.header.pack(fill="x", padx=0, pady=0)
        
        self.title_label = ctk.CTkLabel(
            self.header,
            text="🎓 Сбор данных университетов Москвы и Петербурга",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=20)
        
        # === MAIN CONTENT ===
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        #--Ввод имени Excel файла--
        
        self.excel_name_label = ctk.CTkLabel(self.main_container, text="Имя Excel файла для экспорта (например, output):", font=ctk.CTkFont(size=14))
        self.excel_name_label.pack(pady=(0, 5), padx=15, anchor="w")
        self.excel_name = ctk.CTkEntry(self.main_container, width=250)
        self.excel_name.pack(pady=10)
        
        
        # --- Запуск парсинга ---
        self.scraping_frame = ctk.CTkFrame(self.main_container)
        self.scraping_frame.pack(fill="x", pady=(0, 15))
        
        self.scraping_title = ctk.CTkLabel(
            self.scraping_frame,
            text="🚀 Шаг 1: Обновить данные",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.scraping_title.pack(pady=(15, 10), padx=15, anchor="w")
        
        self.start_button = ctk.CTkButton(
            self.scraping_frame,
            text="▶ Начать парсинг",
            command=self.start_scraping,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_button.pack(pady=(0, 15))
        
        self.progress = ctk.CTkProgressBar(self.scraping_frame, width=400)
        self.progress.pack(pady=(0, 10))
        self.progress.set(0)
        
        self.status_label = ctk.CTkLabel(
            self.scraping_frame,
            text="Готов к работе",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(0, 15))
        
        # --- Экспорт ---
        self.export_frame = ctk.CTkFrame(self.main_container)
        self.export_frame.pack(fill="x", pady=(0, 15))
        
        self.export_title = ctk.CTkLabel(
            self.export_frame,
            text="Шаг 2: Экспортируйте результаты",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.export_title.pack(pady=(15, 10), padx=15, anchor="w")
        
        
        # --- Логи ---
        self.log_frame = ctk.CTkFrame(self.main_container)
        self.log_frame.pack(fill="both", expand=True)
        
        self.log_title = ctk.CTkLabel(
            self.log_frame,
            text="Процесс запущен...",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.log_title.pack(pady=(10, 5), padx=15, anchor="w")
        
        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            wrap="word",
            height=150,
            font=ctk.CTkFont(size=11, family="Consolas")
        )
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
    
    
    def start_scraping(self):
        """Запуск парсинга в отдельном потоке"""
        if not self.excel_name:
            messagebox.showwarning("Предупреждение", "Сначала выберите CSV файл!")
            return
        
        if self.is_scraping:
            messagebox.showinfo("Информация", "Парсинг уже выполняется")
            return
        
        self.is_scraping = True
        self.start_button.configure(state="disabled", text="⏸ Парсинг...")
        self.progress.set(0)
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self.scraping_worker, daemon=True)
        thread.start()
    
    def scraping_worker(self):
        """Рабочая функция парсинга (выполняется в отдельном потоке)"""
        try:
            self.log("🚀 Начало парсинга...")
            from core.scraper import ScrapperOptimized
            from core.database import DatabaseSaver
            db = DatabaseSaver(self.db_path)
            scraper = ScrapperOptimized(db)
            scraper.scrapping()
            self.excel_name=self.excel_name+".xlsx"
            db.export_to_excel_programs(self.excel_name or "exported_data.xlsx")
            
            
        except Exception as e:
            self.log(f"Ошибка: {str(e)}")
            messagebox.showerror("Ошибка", f"Произошла ошибка:\n{str(e)}")
        
        finally:
            self.is_scraping = False
            self.start_button.configure(state="normal", text="▶ Начать парсинг")
    
    
    def log(self, message):
        """Добавляет сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")


# Точка входа
# if __name__ == "__main__":
#     app = UniversityScraperApp()
#     app.mainloop()
# def create_window():    
#     db = DatabaseSaver()
#     app = UniversityScraperApp(db)
#     app.mainloop()



