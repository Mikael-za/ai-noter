# ai_list.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox
class AIList(QWidget):
    def __init__(self, user, scheduler=None):
        super().__init__()
        self.user = user
        self.scheduler = scheduler
        self.setWindowTitle('Искусственный интеллект')
        self._build()
        self.load()
        self.showMaximized()

    # Построение интерфейса списка AI запросов с кнопками управления
    def _build(self):
        v = QVBoxLayout()
        
        # Кнопка возврата в левом верхнем углу
        top_layout = QHBoxLayout()
        self.btn_back = QPushButton('←')
        self.btn_back.setFixedSize(30, 30)
        self.btn_back.setStyleSheet("QPushButton { border: none; font-size: 18px; }")
        self.btn_back.clicked.connect(self.go_back)
        top_layout.addWidget(self.btn_back)
        top_layout.addStretch()
        v.addLayout(top_layout)
        
        self.btn_new = QPushButton('Создать новый запрос')
        self.listw = QListWidget()
        self.btn_delete = QPushButton('Удалить выбранный запрос')
        self.btn_delete.setStyleSheet("QPushButton { background-color: #dc3545; color: white; padding: 8px; }")
        self.btn_delete.clicked.connect(self.delete_request)
        
        v.addWidget(self.btn_new)
        v.addWidget(self.listw)
        v.addWidget(self.btn_delete)
        self.setLayout(v)

        self.btn_new.clicked.connect(self.create_request)
        self.listw.itemDoubleClicked.connect(self.open_request)
    
    # Возврат в главное меню
    def go_back(self):
        from ui.main_menu import MainMenu
        self.main_menu = MainMenu(self.user, self.scheduler)
        self.main_menu.show()
        self.close()

    # Загрузка списка AI запросов из базы данных и отображение в виджете (сокращение длинных промптов)
    def load(self):
        self.listw.clear()
        items = self.user.get_ai_history()
        for it in items:
            prompt = (it['prompt'][:20] + '...') if len(it['prompt']) > 20 else it['prompt']
            lw = QListWidgetItem(f"{prompt} — {it['created']}")
            lw.setData(1000, it['requestID'])
            self.listw.addItem(lw)

    # Создание нового AI запроса: открытие окна запроса
    def create_request(self):
        from ui.ai_request import AIRequestWindow
        self.req = AIRequestWindow(self.user, scheduler=self.scheduler)
        self.req.show()
        self.close()

    # Открытие выбранного AI запроса для просмотра с проверкой прав доступа
    def open_request(self, item: QListWidgetItem):
        req_id = item.data(1000)
        from models import AIRequest
        r = AIRequest.load_by_id(req_id)
        if not r or r.userID != self.user.userID:
            QMessageBox.warning(self, 'Ошибка', 'Доступ запрещён')
            return
        from ui.ai_request import AIRequestWindow
        self.req = AIRequestWindow(self.user, r, scheduler=self.scheduler)
        self.req.show()
        self.close()

    # Удаление выбранного AI запроса с подтверждением и проверкой прав доступа
    def delete_request(self):
        current_item = self.listw.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите запрос для удаления')
            return
        
        req_id = current_item.data(1000)
        from models import AIRequest
        r = AIRequest.load_by_id(req_id)
        if not r or r.userID != self.user.userID:
            QMessageBox.warning(self, 'Ошибка', 'Доступ запрещён')
            return
        
        reply = QMessageBox.question(
            self, 
            'Подтверждение удаления', 
            f'Вы уверены, что хотите удалить запрос "{current_item.text()}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            r.delete()
            self.load()
            QMessageBox.information(self, 'Успех', 'Запрос удалён')
