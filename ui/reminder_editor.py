# reminder_editor.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QMessageBox, QCalendarWidget, QSpinBox, QLabel
from datetime import datetime
from models import Reminder

class ReminderEditor(QWidget):
    def __init__(self, user, reminder: Reminder = None, scheduler=None):
        super().__init__()
        self.user = user
        self.reminder = reminder
        self.scheduler = scheduler
        self.setWindowTitle('Редактирование напоминания')
        self._build_ui()
        self.showMaximized()
        if self.reminder:
            self._load_data()
        else:
            self._set_default_datetime()

    # Построение интерфейса редактора напоминаний с календарем и выбором времени
    def _build_ui(self):
        v = QVBoxLayout()
        
        # Кнопка возврата в левом верхнем углу
        top_layout = QHBoxLayout()
        self.btn_nav_back = QPushButton('←')
        self.btn_nav_back.setFixedSize(30, 30)
        self.btn_nav_back.setStyleSheet("QPushButton { border: none; font-size: 18px; }")
        self.btn_nav_back.clicked.connect(self._back)
        top_layout.addWidget(self.btn_nav_back)
        top_layout.addStretch()
        v.addLayout(top_layout)
        
        self.title = QLineEdit()
        v.addWidget(QLabel("Название напоминания:"))
        v.addWidget(self.title)

        self.calendar = QCalendarWidget()
        v.addWidget(QLabel("Выберите дату:"))
        v.addWidget(self.calendar)

        h_time = QHBoxLayout()
        self.hours = QSpinBox()
        self.hours.setRange(0, 23)
        self.minutes = QSpinBox()
        self.minutes.setRange(0, 59)
        h_time.addWidget(QLabel("Часы:"))
        h_time.addWidget(self.hours)
        h_time.addWidget(QLabel("Минуты:"))
        h_time.addWidget(self.minutes)
        v.addLayout(h_time)

        self.btn_save = QPushButton('Сохранить')
        v.addWidget(self.btn_save)
        self.setLayout(v)

        self.btn_save.clicked.connect(self._save)

    # Установка текущей даты и времени по умолчанию для нового напоминания
    def _set_default_datetime(self):
        now = datetime.now()
        self.calendar.setSelectedDate(now.date())
        self.hours.setValue(now.hour)
        self.minutes.setValue(now.minute)

    # Загрузка данных существующего напоминания в форму редактирования
    def _load_data(self):
        self.title.setText(self.reminder.text)
        try:
            dt = datetime.fromisoformat(self.reminder.startTime)
            self.calendar.setSelectedDate(dt.date())
            self.hours.setValue(dt.hour)
            self.minutes.setValue(dt.minute)
        except Exception:
            self._set_default_datetime()

    # Сохранение напоминания: валидация данных и запись в базу данных
    def _save(self):
        text = self.title.text().strip()
        date = self.calendar.selectedDate()
        dt = datetime(
            year=date.year(),
            month=date.month(),
            day=date.day(),
            hour=self.hours.value(),
            minute=self.minutes.value()
        )

        if not text:
            QMessageBox.warning(self, 'Ошибка', 'Название пустое')
            return
        if dt <= datetime.now():
            QMessageBox.warning(self, 'Ошибка', 'Дата и время уже прошли')
            return

        iso = dt.isoformat()
        if self.reminder is None:
            r = Reminder(self.user.userID, text, iso)
        else:
            r = self.reminder
            r.text = text
            r.startTime = iso
        r.save()
        QMessageBox.information(self, 'OK', 'Сохранено')

        try:
            from ui.reminders_list import RemindersList
            self.rl = RemindersList(self.user, self.scheduler)
            self.rl.show()
        except Exception:
            pass
        self.close()

    # Возврат к списку напоминаний
    def _back(self):
        try:
            from ui.reminders_list import RemindersList
            self.rl = RemindersList(self.user, self.scheduler)
            self.rl.show()
        except Exception:
            pass
        self.close()