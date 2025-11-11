# reminder_watcher.py
from PyQt6.QtCore import QObject, QTimer, QUrl
from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtMultimedia import QSoundEffect
from datetime import datetime
from pathlib import Path
from models import Reminder
from db import get_conn
from paths import get_resource_path

class ReminderScheduler(QObject):
    # Инициализация планировщика напоминаний
    # user: объект текущего авторизованного пользователя, должен иметь атрибут userID
    # interval_ms: интервал проверки в миллисекундах (по умолчанию 5 секунд)
    # sound_file: путь к звуковому файлу (относительно корня проекта)
    def __init__(self, user, interval_ms: int = 5000, sound_file: str = "alarm.wav"):
        super().__init__()
        self.user = user
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check)
        self.timer.start(interval_ms)

        # Настройка звука (если файла нет - play() просто ничего не сделает)
        self.sound = QSoundEffect(self)
        try:
            # Получаем путь к звуковому файлу (работает в обычном проекте и в exe)
            sound_path = get_resource_path(sound_file)
            if sound_path.exists():
                self.sound.setSource(QUrl.fromLocalFile(str(sound_path.resolve())))
                self.sound.setVolume(0.8)
        except Exception:
            # безопасно проигнорируем ошибку при инициализации звука
            pass

    # Проверка базы данных на наличие напоминаний, которые должны быть показаны сейчас
    def _check(self):
        now_iso = datetime.now().isoformat()
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT remindID, text FROM reminders WHERE userID = ? AND startTime <= ?",
                (self.user.userID, now_iso),
            )
            rows = cur.fetchall()
            for row in rows:
                remind_id = row["remindID"]
                text = row["text"] or ""
                # Показываем уведомление и звук
                self._show_reminder(text)
                # Удаляем напоминание — используем класс Reminder (без изменений)
                r = Reminder.load_by_id(remind_id)
                if r:
                    r.delete()
        finally:
            conn.commit()
            conn.close()

    # Показ уведомления о напоминании с воспроизведением звука
    def _show_reminder(self, text: str):
        try:
            self.sound.play()
        except Exception:
            pass

        # информационное уведомление по центру (QMessageBox)
        msg = QMessageBox()
        msg.setWindowTitle("Напоминание")
        msg.setText(text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        # блокирующий вызов, покажет сообщение в центре активного окна
        msg.exec()
