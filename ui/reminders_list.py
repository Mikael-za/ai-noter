# reminders_list.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QMessageBox, QHBoxLayout
from models import Reminder

class RemindersList(QWidget):
    def __init__(self, user, scheduler=None):
        super().__init__()
        self.user = user
        self.scheduler = scheduler
        self.setWindowTitle('Напоминания')
        self._build()
        self.load()
        self.showMaximized()

    # Построение интерфейса списка напоминаний с кнопками управления
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
        
        self.btn_new = QPushButton('Создать новое напоминание')
        self.listw = QListWidget()
        self.btn_delete = QPushButton('Удалить выбранное напоминание')
        self.btn_delete.setStyleSheet("QPushButton { background-color: #dc3545; color: white; padding: 8px; }")
        self.btn_delete.clicked.connect(self.delete_reminder)
        
        v.addWidget(self.btn_new)
        v.addWidget(self.listw)
        v.addWidget(self.btn_delete)
        self.setLayout(v)

        self.btn_new.clicked.connect(self.create_reminder)
        self.listw.itemDoubleClicked.connect(self.open_reminder)
    
    # Возврат в главное меню
    def go_back(self):
        from ui.main_menu import MainMenu
        self.main_menu = MainMenu(self.user, self.scheduler)
        self.main_menu.show()
        self.close()

    # Загрузка списка напоминаний из базы данных и отображение в виджете
    def load(self):
        self.listw.clear()
        items = self.user.get_reminders_list()
        for it in items:
            lw = QListWidgetItem(f"{it['text']} — {it['startTime']}")
            lw.setData(1000, it['remindID'])
            self.listw.addItem(lw)

    # Создание нового напоминания: открытие редактора
    def create_reminder(self):
        from ui.reminder_editor import ReminderEditor
        self.editor = ReminderEditor(self.user, scheduler=self.scheduler)
        self.editor.show()
        self.close()

    # Открытие выбранного напоминания для редактирования с проверкой прав доступа
    def open_reminder(self, item: QListWidgetItem):
        remind_id = item.data(1000)
        rem = Reminder.load_by_id(remind_id)
        if not rem or rem.userID != self.user.userID:
            QMessageBox.warning(self, 'Ошибка', 'Доступ запрещён')
            return
        from ui.reminder_editor import ReminderEditor
        self.editor = ReminderEditor(self.user, rem, scheduler=self.scheduler)
        self.editor.show()
        self.close()

    # Удаление выбранного напоминания с подтверждением и проверкой прав доступа
    def delete_reminder(self):
        current_item = self.listw.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите напоминание для удаления')
            return
        
        remind_id = current_item.data(1000)
        rem = Reminder.load_by_id(remind_id)
        if not rem or rem.userID != self.user.userID:
            QMessageBox.warning(self, 'Ошибка', 'Доступ запрещён')
            return
        
        reply = QMessageBox.question(
            self, 
            'Подтверждение удаления', 
            f'Вы уверены, что хотите удалить напоминание "{current_item.text()}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            rem.delete()
            self.load()
            QMessageBox.information(self, 'Успех', 'Напоминание удалено')
