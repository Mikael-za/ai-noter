# db.py
import sqlite3
from pathlib import Path
from paths import get_app_data_path

# Путь к БД (работает в обычном проекте и в exe)
DB_PATH = get_app_data_path() / 'ai_noter.db'


# Получение подключения к базе данных SQLite с настройкой row_factory для доступа по именам колонок
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Инициализация базы данных: создание всех необходимых таблиц если они не существуют
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        userID INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS notes (
        noteID INTEGER PRIMARY KEY AUTOINCREMENT,
        userID INTEGER NOT NULL,
        title TEXT,
        content TEXT,
        created TEXT,
        updated TEXT,
        FOREIGN KEY(userID) REFERENCES users(userID)
    );

    CREATE TABLE IF NOT EXISTS reminders (
        remindID INTEGER PRIMARY KEY AUTOINCREMENT,
        userID INTEGER NOT NULL,
        text TEXT,
        startTime TEXT,
        endTime TEXT,
        isDone INTEGER DEFAULT 0,
        FOREIGN KEY(userID) REFERENCES users(userID)
    );

    CREATE TABLE IF NOT EXISTS ai_requests (
        requestID INTEGER PRIMARY KEY AUTOINCREMENT,
        userID INTEGER NOT NULL,
        prompt TEXT,
        response TEXT,
        created TEXT,
        FOREIGN KEY(userID) REFERENCES users(userID)
    );
    ''')
    conn.commit()
    conn.close()