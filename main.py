# main.py
import sys
from PyQt6.QtWidgets import QApplication
from db import init_db
from ui.login import LoginWindow



# Инициализация приложения: создание базы данных и запуск окна входа
def main():
    init_db()
    app = QApplication(sys.argv)
    win = LoginWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()