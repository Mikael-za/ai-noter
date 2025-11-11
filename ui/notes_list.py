# notes_list.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt
from models import Note

class NotesList(QWidget):
    def __init__(self, user, scheduler=None):
        super().__init__()
        self.user = user
        self.scheduler = scheduler
        self.setWindowTitle('Заметки')
        self._build()
        self.load()
        self.showMaximized()

    # Построение интерфейса списка заметок с кнопками управления
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
        
        self.btn_new = QPushButton('Создать новую заметку')
        self.listw = QListWidget()
        self.btn_delete = QPushButton('Удалить выбранную заметку')
        self.btn_delete.setStyleSheet("QPushButton { background-color: #dc3545; color: white; padding: 8px; }")
        self.btn_delete.clicked.connect(self.delete_note)
        
        v.addWidget(self.btn_new)
        v.addWidget(self.listw)
        v.addWidget(self.btn_delete)
        self.setLayout(v)

        self.btn_new.clicked.connect(self.create_note)
        self.listw.itemDoubleClicked.connect(self.open_note)
    
    # Возврат в главное меню
    def go_back(self):
        from ui.main_menu import MainMenu
        self.main_menu = MainMenu(self.user, self.scheduler)
        self.main_menu.show()
        self.close()

    # Загрузка списка заметок из базы данных и отображение в виджете
    def load(self):
        self.listw.clear()
        items = self.user.get_notes_list()
        for it in items:
            lw = QListWidgetItem(f"{it['title'] or '(Без названия)'} — {it['created']}")
            lw.setData(1000, it['noteID'])
            self.listw.addItem(lw)

    # Создание новой заметки: открытие редактора
    def create_note(self):
        from ui.note_editor import NoteEditor
        self.editor = NoteEditor(self.user, scheduler=self.scheduler)
        self.editor.show()
        self.close()

    # Открытие выбранной заметки для редактирования с проверкой прав доступа
    def open_note(self, item: QListWidgetItem):
        note_id = item.data(1000)
        note = Note.load_by_id(note_id)
        if not note or note.userID != self.user.userID:
            QMessageBox.warning(self, 'Ошибка', 'Доступ запрещён')
            return
        from ui.note_editor import NoteEditor
        self.editor = NoteEditor(self.user, note, scheduler=self.scheduler)
        self.editor.show()
        self.close()

    # Удаление выбранной заметки с подтверждением и проверкой прав доступа
    def delete_note(self):
        current_item = self.listw.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'Предупреждение', 'Выберите заметку для удаления')
            return
        
        note_id = current_item.data(1000)
        note = Note.load_by_id(note_id)
        if not note or note.userID != self.user.userID:
            QMessageBox.warning(self, 'Ошибка', 'Доступ запрещён')
            return
        
        reply = QMessageBox.question(
            self, 
            'Подтверждение удаления', 
            f'Вы уверены, что хотите удалить заметку "{current_item.text()}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            note.delete()
            self.load()
            QMessageBox.information(self, 'Успех', 'Заметка удалена')
