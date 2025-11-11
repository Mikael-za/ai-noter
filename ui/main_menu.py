# main_menu.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
    QSpacerItem, QSizePolicy, QDialog, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from pathlib import Path
import os
from dotenv import load_dotenv
from paths import get_app_data_path

class MainMenu(QWidget):
    def __init__(self, user, scheduler=None):
        super().__init__()
        self.user = user
        # Планировщик напоминаний передаётся из LoginWindow
        self.scheduler = scheduler
        self.setWindowTitle('AI Noter')
        self._build()
        self.showMaximized()
        # Убираем фокус с кнопок после показа окна
        self.setFocus()

    # Построение интерфейса главного меню с кнопками навигации
    def _build(self):
        v = QVBoxLayout()
        v.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        top_spacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        v.addItem(top_spacer)
        
        self.greeting = QLabel(f'Здравствуйте, {self.user.username}')
        self.greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        greeting_font = QFont()
        greeting_font.setPointSize(16)
        self.greeting.setFont(greeting_font)
        
        self.btn_notes = QPushButton('Заметки')
        self.btn_reminders = QPushButton('Напоминания')
        self.btn_ai = QPushButton('Искусственный интеллект')
        self.btn_logout = QPushButton('Выход')
        
        # Кнопка для добавления API ключа (показывается только если ключа нет)
        self.btn_add_key = QPushButton('🔑 Добавить API ключ DeepSeek')
        self.btn_add_key.setStyleSheet("""
            QPushButton {
                background-color: #e3f2fd;
                border: 2px solid #90caf9;
                border-radius: 5px;
                color: #1565c0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #bbdefb;
            }
        """)
        
        button_font = QFont()
        button_font.setPointSize(12)
        
        for btn in [self.btn_notes, self.btn_reminders, self.btn_ai, self.btn_logout, self.btn_add_key]:
            btn.setFixedWidth(300)
            btn.setFont(button_font)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        v.addWidget(self.greeting)
        v.addSpacing(20)
        
        # Показываем кнопку добавления ключа только если ключа нет
        if not self.has_deepseek_key():
            v.addWidget(self.btn_add_key)
            v.addSpacing(10)
        
        v.addWidget(self.btn_notes)
        v.addWidget(self.btn_reminders)
        v.addWidget(self.btn_ai)
        v.addWidget(self.btn_logout)
        
        bottom_spacer = QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        v.addItem(bottom_spacer)
        
        self.setLayout(v)
        
        self.setMinimumWidth(250)
        self.setMinimumHeight(400)

        self.btn_notes.clicked.connect(self.open_notes)
        self.btn_reminders.clicked.connect(self.open_reminders)
        self.btn_ai.clicked.connect(self.open_ai)
        self.btn_logout.clicked.connect(self.logout)
        self.btn_add_key.clicked.connect(self.add_deepseek_key)


    # Открытие окна со списком заметок
    def open_notes(self):
        from ui.notes_list import NotesList
        self.notes = NotesList(self.user, self.scheduler)
        self.notes.show()
        self.close()

    # Открытие окна со списком напоминаний
    def open_reminders(self):
        from ui.reminders_list import RemindersList
        self.rm = RemindersList(self.user, self.scheduler)
        self.rm.show()
        self.close()

    # Открытие окна со списком AI запросов
    def open_ai(self):
        from ui.ai_list import AIList
        self.aiw = AIList(self.user, self.scheduler)
        self.aiw.show()
        self.close()

    # Выход из аккаунта и возврат к окну входа
    def logout(self):
        # Уничтожаем планировщик напоминаний при выходе из аккаунта
        if self.scheduler:
            self.scheduler.timer.stop()
            self.scheduler.deleteLater()
            self.scheduler = None
        
        from ui.login import LoginWindow
        self.login = LoginWindow()
        self.login.show()
        self.close()

    # Проверка наличия ключа DeepSeek в .env файле
    def has_deepseek_key(self):
        # Загружаем .env из папки приложения (работает в обычном проекте и в exe)
        env_path = get_app_data_path() / '.env'
        load_dotenv(env_path, override=True)
        api_key = os.getenv('DEEPSEEK_API_KEY')
        # Проверяем, что ключ не пустой и не равен значению по умолчанию
        return api_key and api_key.strip() and api_key.strip() != 'your_api_key_here'

    # Сохранение ключа DeepSeek в .env файл
    def save_deepseek_key(self, api_key: str):
        # Путь к .env файлу (работает в обычном проекте и в exe)
        env_path = get_app_data_path() / '.env'
        
        # Читаем существующий файл, если он есть
        env_content = []
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.readlines()
        else:
            # Если файл не существует, добавляем заголовок с комментариями
            env_content = [
                '# DeepSeek API Key\n',
                '# Получите свой API ключ на https://www.deepseek.com/\n',
                '# Вы можете обратиться в Telegram @coawy для получения API-ключа для тестирования проекта\n'
            ]
        
        # Ищем строку с DEEPSEEK_API_KEY
        key_found = False
        for i, line in enumerate(env_content):
            if line.strip().startswith('DEEPSEEK_API_KEY='):
                env_content[i] = f'DEEPSEEK_API_KEY={api_key}\n'
                key_found = True
                break
        
        # Если ключ не найден, добавляем его
        if not key_found:
            # Удаляем пустые строки в конце
            while env_content and env_content[-1].strip() == '':
                env_content.pop()
            env_content.append(f'DEEPSEEK_API_KEY={api_key}\n')
        
        # Записываем обратно в файл
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(env_content)

    # Диалог для добавления API ключа DeepSeek
    def add_deepseek_key(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Добавить API ключ DeepSeek')
        dialog.setFixedWidth(400)
        
        layout = QVBoxLayout()
        
        info_label = QLabel(
            'Введите ваш API ключ DeepSeek.\n'
            'Получить ключ можно на https://www.deepseek.com/\n'
            'Или обратитесь в Telegram @coawy для тестирования проекта.'
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                border: 1px solid #90caf9;
                border-radius: 5px;
                padding: 10px;
                color: #1565c0;
            }
        """)
        
        key_input = QLineEdit()
        key_input.setPlaceholderText('Введите ваш API ключ')
        key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton('Сохранить')
        btn_cancel = QPushButton('Отмена')
        
        def on_save():
            api_key = key_input.text().strip()
            if not api_key:
                QMessageBox.warning(dialog, 'Ошибка', 'Введите API ключ')
                return
            dialog.accept()
        
        btn_save.clicked.connect(on_save)
        btn_cancel.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        
        layout.addWidget(info_label)
        layout.addWidget(key_input)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            api_key = key_input.text().strip()
            try:
                self.save_deepseek_key(api_key)
                QMessageBox.information(self, 'Успешно', 'API ключ сохранен в .env файл')
                # Скрываем кнопку и перестраиваем интерфейс
                self.btn_add_key.hide()
                # Обновляем переменные окружения
                env_path = get_app_data_path() / '.env'
                load_dotenv(env_path, override=True)
            except Exception as e:
                QMessageBox.warning(self, 'Ошибка', f'Не удалось сохранить ключ: {e}')
