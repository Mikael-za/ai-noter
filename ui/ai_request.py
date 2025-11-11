# ai_request.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QMessageBox, QApplication
)

from PyQt6.QtCore import Qt, QTimer
import os
from dotenv import load_dotenv
from models import AIRequest
from paths import get_app_data_path
import threading

class AIRequestWindow(QWidget):
    def __init__(self, user, request: AIRequest = None, scheduler=None):
        super().__init__()
        self.user = user
        self.request = request
        self.scheduler = scheduler
        self._sending = False  # Флаг для предотвращения повторных отправок
        self.setWindowTitle('AI — Чат')
        self._build()
        self.showMaximized()
        if self.request:
            self.load()

    # Построение интерфейса окна AI запроса с полями для промпта и ответа
    def _build(self):
        main_layout = QVBoxLayout()
        
        # Кнопка возврата в левом верхнем углу
        top_layout = QHBoxLayout()
        self.btn_nav_back = QPushButton('←')
        self.btn_nav_back.setFixedSize(30, 30)
        self.btn_nav_back.setStyleSheet("QPushButton { border: none; font-size: 18px; }")
        self.btn_nav_back.clicked.connect(self.back)
        top_layout.addWidget(self.btn_nav_back)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # Сообщение пользователя
        self.lbl_user = QLabel(f"{self.user.username}")
        self.lbl_user.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.prompt = QTextEdit()
        self.prompt.setPlaceholderText("Введите ваш запрос...")

        # Ответ нейросети
        self.lbl_response = QTextEdit()
        self.lbl_response.setReadOnly(True)
        self.lbl_response.setPlaceholderText("Ответ нейросети появится здесь...")
        self.btn_copy = QPushButton("Копировать")
        self.btn_copy.clicked.connect(self.copy_response)

        # Кнопки действий
        self.btn_send = QPushButton('Отправить')
        self.btn_send.clicked.connect(self.send)

        main_layout.addWidget(self.lbl_user)
        main_layout.addWidget(self.prompt)
        main_layout.addWidget(self.lbl_response)
        main_layout.addWidget(self.btn_copy, alignment=Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.btn_send)

        self.setLayout(main_layout)

    # Загрузка существующего AI запроса в форму для просмотра
    def load(self):
        self.prompt.setPlainText(self.request.prompt)
        self.lbl_response.setMarkdown(self.request.response or '')

    # Отправка AI запроса: валидация промпта, запуск запроса в отдельном потоке и периодическая проверка ответа
    def send(self):
        # Предотвращаем повторные отправки
        if self._sending:
            return
        
        text = self.prompt.toPlainText().strip()
        if not text:
            self.lbl_response.setMarkdown('**Ошибка:** заполните запрос')
            return

        # Проверка длины промпта
        MAX_PROMPT_LENGTH = 5000
        MAX_WORDS = 1000
        
        if len(text) > MAX_PROMPT_LENGTH:
            self.lbl_response.setMarkdown(
                f'**Ошибка:** превышено количество символов. Максимум: {MAX_PROMPT_LENGTH} символов.'
            )
            return
        
        word_count = len(text.split())
        if word_count > MAX_WORDS:
            self.lbl_response.setMarkdown(
                f'**Ошибка:** превышено количество слов. Максимум: {MAX_WORDS} слов. Текущее количество: {word_count}.'
            )
            return

        # Проверяем наличие ключа до любой попытки отправки
        # Загружаем .env из папки приложения (работает в обычном проекте и в exe)
        env_path = get_app_data_path() / '.env'
        load_dotenv(env_path, override=True)
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            self.lbl_response.setMarkdown(
                "**Ошибка:** отсутствует ключ `DEEPSEEK_API_KEY`. Добавьте его в файл `.env`."
            )
            return

        # Блокируем повторные отправки
        self._sending = True
        self.btn_send.setEnabled(False)
        self.btn_send.setText('Отправка...')
        self.lbl_response.setMarkdown("_Запрос отправлен, подождите, пожалуйста..._")

        # создаём объект запроса
        self.request = AIRequest(self.user.userID, text)

        # запускаем отправку запроса в отдельном потоке
        threading.Thread(target=self._send_request_thread, daemon=True).start()

        # запускаем таймер для проверки ответа
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_response)
        self.check_timer.start(2000)  # проверка каждые 2 секунды

    # Выполнение отправки запроса к AI API в отдельном потоке для неблокирующей работы UI
    def _send_request_thread(self):
        try:
            self.request.send()  # вызов метода send, который логирует и пишет в БД
        except Exception as e:
            # Если запрос не был сохранен в БД, сохраняем ошибку напрямую
            if not self.request.requestID:
                self.request.response = f"Ошибка при отправке: {e}"
                # Сохраняем ошибку в БД
                from datetime import datetime
                from db import get_conn
                now = datetime.utcnow().isoformat()
                conn = get_conn()
                cur = conn.cursor()
                cur.execute(
                    'INSERT INTO ai_requests (userID, prompt, response, created) VALUES (?, ?, ?, ?)',
                    (self.request.userID, self.request.prompt, self.request.response, now),
                )
                self.request.requestID = cur.lastrowid
                self.request.created = now
                conn.commit()
                conn.close()
            else:
                # Если запрос уже был сохранен, просто обновляем ответ
                self.request.response = f"Ошибка при отправке: {e}"
                from db import get_conn
                conn = get_conn()
                cur = conn.cursor()
                cur.execute(
                    'UPDATE ai_requests SET response = ? WHERE requestID = ? AND userID = ?',
                    (self.request.response, self.request.requestID, self.request.userID),
                )
                conn.commit()
                conn.close()
            print(f"[AIRequestWindow] Ошибка отправки запроса: {e}")
            # Разблокируем кнопку при ошибке
            self._sending = False
            # Используем QTimer для безопасного обновления UI из другого потока
            QTimer.singleShot(0, lambda: (
                self.btn_send.setEnabled(True),
                self.btn_send.setText('Отправить')
            ))

    # Периодическая проверка наличия ответа от AI API и обновление интерфейса
    def check_response(self):
        if not self.request or not self.request.requestID:
            return
        updated_request = AIRequest.load_by_id(self.request.requestID)
        if updated_request and updated_request.response:
            self.lbl_response.setMarkdown(updated_request.response)
            self.check_timer.stop()
            # Разблокируем кнопку отправки
            self._sending = False
            self.btn_send.setEnabled(True)
            self.btn_send.setText('Отправить')

    # Копирование ответа AI в буфер обмена
    def copy_response(self):
        text = self.lbl_response.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "Скопировано", "Ответ скопирован в буфер обмена")

    # Остановка таймера при закрытии окна
    def closeEvent(self, event):
        if hasattr(self, 'check_timer'):
            self.check_timer.stop()
        super().closeEvent(event)

    # Возврат к списку AI запросов
    def back(self):
        if hasattr(self, 'check_timer'):
            self.check_timer.stop()
        from ui.ai_list import AIList
        self.listw = AIList(self.user, self.scheduler)
        self.listw.show()
        self.close()