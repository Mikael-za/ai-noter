# login.py
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QSpacerItem, QSizePolicy, QApplication
)
from models import User
from reminder_watcher import ReminderScheduler


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('AI Noter — Вход')
        self._build()
        self.showMaximized()

    # Построение интерфейса окна входа с полями логина и пароля
    def _build(self):
        outer_layout = QVBoxLayout()
        outer_layout.addStretch()

        # Центральный блок с логином и паролем
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)

        self.lbl = QLabel('Логин')
        self.edit_login = QLineEdit()

        self.lbl2 = QLabel('Пароль')
        self.edit_pass = QLineEdit()
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)

        self.btn_login = QPushButton('Войти')
        self.btn_reg = QPushButton('Регистрация')

        # Горизонтальное расположение кнопок
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(self.btn_reg)
        btn_layout.addStretch()

        form_layout.addWidget(self.lbl)
        form_layout.addWidget(self.edit_login)
        form_layout.addWidget(self.lbl2)
        form_layout.addWidget(self.edit_pass)
        form_layout.addLayout(btn_layout)

        # Немного пространства сверху и снизу, чтобы выглядело естественно
        form_layout.setContentsMargins(20, 20, 20, 20)

        # Оборачиваем в дополнительный вертикальный слой для центрирования
        outer_layout.addLayout(form_layout)
        outer_layout.addStretch()
        self.setLayout(outer_layout)

        # Сигналы
        self.btn_login.clicked.connect(self.on_login)
        self.btn_reg.clicked.connect(self.on_register)

    # Обработка попытки входа: проверка данных и открытие главного меню
    def on_login(self):
        username = self.edit_login.text().strip()
        password = self.edit_pass.text()
        if not username or not password:
            QMessageBox.warning(self, 'Ошибка', 'Заполните логин и пароль')
            return

        user = User.login(username, password)
        if not user:
            QMessageBox.warning(self, 'Ошибка', 'Неверный логин или пароль')
            return

        # Создаём планировщик напоминаний после успешного логина
        scheduler = ReminderScheduler(user)
        # Устанавливаем родителя как QApplication, чтобы планировщик жил независимо от окон
        scheduler.setParent(QApplication.instance())
        
        from ui.main_menu import MainMenu
        self.main = MainMenu(user, scheduler)
        self.main.show()
        self.close()

    # Обработка регистрации нового пользователя
    def on_register(self):
        username = self.edit_login.text().strip()
        password = self.edit_pass.text()
        if not username or not password:
            QMessageBox.warning(self, 'Ошибка', 'Заполните логин и пароль')
            return

        user = User.register(username, password)
        if not user:
            QMessageBox.warning(self, 'Ошибка', 'Пользователь с таким логином уже существует')
            return

        QMessageBox.information(self, 'OK', 'Пользователь создан')
        # После регистрации автоматически логинимся (on_login создаст планировщик)
        self.on_login()
