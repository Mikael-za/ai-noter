# paths.py
"""
Утилита для определения путей к ресурсам проекта.
Работает как в обычном режиме разработки, так и в собранном exe через PyInstaller.
"""
import sys
from pathlib import Path


def get_base_path():
    """
    Возвращает базовый путь проекта.
    В режиме PyInstaller (--onefile) возвращает путь к временной папке с ресурсами.
    В обычном режиме возвращает корень проекта (родительскую папку от paths.py).
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Режим PyInstaller --onefile: ресурсы во временной папке
        return Path(sys._MEIPASS)
    else:
        # Обычный режим: корень проекта
        return Path(__file__).parent


def get_resource_path(relative_path: str) -> Path:
    """
    Возвращает абсолютный путь к ресурсу относительно корня проекта.
    
    Args:
        relative_path: Относительный путь к ресурсу (например, "alarm.wav", "storage/images")
    
    Returns:
        Path: Абсолютный путь к ресурсу
    """
    base_path = get_base_path()
    return base_path / relative_path


def get_app_data_path() -> Path:
    """
    Возвращает путь для хранения данных приложения (БД, storage).
    В режиме PyInstaller это папка рядом с exe файлом.
    В обычном режиме это корень проекта.
    """
    if getattr(sys, 'frozen', False):
        # В режиме exe - папка рядом с исполняемым файлом
        return Path(sys.executable).parent
    else:
        # В обычном режиме - корень проекта
        return Path(__file__).parent

