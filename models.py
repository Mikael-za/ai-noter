# models.py
import sqlite3
import json
from datetime import datetime
from db import get_conn


class User:
    def __init__(self, username: str, password: str, user_id: int = None):
        self.userID = user_id
        self.username = username
        self.password = password

    # Регистрация нового пользователя в базе данных
    @staticmethod
    def register(username: str, password: str) -> 'User':
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, password),
            )
            conn.commit()
            user_id = cur.lastrowid
            return User(username, password, user_id)
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    # Авторизация пользователя по логину и паролю
    @staticmethod
    def login(username: str, password: str) -> 'User':
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            'SELECT userID, username, password FROM users WHERE username = ?', (username,)
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        if row['password'] != password:
            return None
        return User(row['username'], row['password'], row['userID'])

    # Получение списка всех заметок пользователя, отсортированных по дате создания
    def get_notes_list(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT noteID, title, created FROM notes WHERE userID = ? ORDER BY created DESC', (self.userID,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # Получение списка всех напоминаний пользователя, отсортированных по времени
    def get_reminders_list(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT remindID, text, startTime FROM reminders WHERE userID = ? ORDER BY startTime ASC', (self.userID,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # Получение истории AI запросов пользователя, отсортированных по дате создания
    def get_ai_history(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT requestID, prompt, created FROM ai_requests WHERE userID = ? ORDER BY created DESC', (self.userID,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]


class Note:
    def __init__(self, user_id: int, title: str = '', content=None, note_id: int = None):
        self.noteID = note_id
        self.userID = user_id
        self.title = title
        self.content = content or []
        self.created = None
        self.updated = None

    # Сохранение заметки в базу данных (создание новой или обновление существующей)
    def save(self):
        now = datetime.utcnow().isoformat()
        conn = get_conn()
        cur = conn.cursor()
        if self.noteID is None:
            cur.execute(
                'INSERT INTO notes (userID, title, content, created, updated) VALUES (?, ?, ?, ?, ?)',
                (self.userID, self.title, json.dumps(self.content, ensure_ascii=False), now, now),
            )
            self.noteID = cur.lastrowid
        else:
            cur.execute(
                'UPDATE notes SET title = ?, content = ?, updated = ? WHERE noteID = ? AND userID = ?',
                (self.title, json.dumps(self.content, ensure_ascii=False), now, self.noteID, self.userID),
            )
        conn.commit()
        conn.close()

    # Загрузка заметки из базы данных по ID с обработкой ошибок парсинга JSON
    @staticmethod
    def load_by_id(note_id: int):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT * FROM notes WHERE noteID = ?', (note_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        try:
            content = json.loads(row['content'] or '[]')
        except (json.JSONDecodeError, TypeError) as e:
            # Восстанавливаемся с пустым содержимым при ошибке парсинга
            content = []
            print(f"Ошибка парсинга JSON для заметки {row['noteID']}: {e}")
        n = Note(row['userID'], row['title'], content, row['noteID'])
        n.created = row['created']
        n.updated = row['updated']
        return n

    # Удаление заметки из базы данных
    def delete(self):
        if self.noteID is None:
            return
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM notes WHERE noteID = ? AND userID = ?', (self.noteID, self.userID))
        conn.commit()
        conn.close()


class Reminder:
    def __init__(self, user_id: int, text: str, start_time: str, remind_id: int = None):
        self.remindID = remind_id
        self.userID = user_id
        self.text = text
        self.startTime = start_time

    # Сохранение напоминания в базу данных (создание новой или обновление существующей)
    def save(self):
        conn = get_conn()
        cur = conn.cursor()
        if self.remindID is None:
            cur.execute(
                'INSERT INTO reminders (userID, text, startTime) VALUES (?, ?, ?)',
                (self.userID, self.text, self.startTime),
            )
            self.remindID = cur.lastrowid
        else:
            cur.execute(
                'UPDATE reminders SET text = ?, startTime = ? WHERE remindID = ? AND userID = ?',
                (self.text, self.startTime, self.remindID, self.userID),
            )
        conn.commit()
        conn.close()

    # Загрузка напоминания из базы данных по ID
    @staticmethod
    def load_by_id(remind_id: int):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT * FROM reminders WHERE remindID = ?', (remind_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        r = Reminder(row['userID'], row['text'], row['startTime'], row['remindID'])
        return r

    # Удаление напоминания из базы данных
    def delete(self):
        if self.remindID is None:
            return
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM reminders WHERE remindID = ? AND userID = ?', (self.remindID, self.userID))
        conn.commit()
        conn.close()


class AIRequest:
    def __init__(self, user_id: int, prompt: str, response: str = '', request_id: int = None):
        self.requestID = request_id
        self.userID = user_id
        self.prompt = prompt
        self.response = response
        self.created = None
    

    # Отправка запроса к AI API DeepSeek и сохранение результата в базу данных
    def send(self):
        import os
        import requests
        from dotenv import load_dotenv
        from datetime import datetime
        from paths import get_app_data_path

        # Загружаем .env из папки приложения (работает в обычном проекте и в exe)
        env_path = get_app_data_path() / '.env'
        load_dotenv(env_path, override=True)
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise RuntimeError('DEEPSEEK_API_KEY not found in .env')

        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Отвечайте на русском языке. Будьте краткими и чёткими. Максимальная длина ответа - 500 токенов."},
                {"role": "user", "content": self.prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7,
            "stream": False
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            try:
                data = resp.json()
                self.response = data["choices"][0]["message"]["content"]
            except (ValueError, KeyError, IndexError) as e:
                self.response = f"Ошибка парсинга ответа API: {e}"
        except requests.exceptions.HTTPError as e:
            status_code = resp.status_code if hasattr(resp, 'status_code') else 'unknown'
            self.response = f"Ошибка API: {e} (status {status_code})"
        except requests.exceptions.RequestException as e:
            self.response = f"Ошибка запроса: {e}"

        now = datetime.utcnow().isoformat()
        conn = get_conn()
        cur = conn.cursor()
        if self.requestID is None:
            cur.execute(
                'INSERT INTO ai_requests (userID, prompt, response, created) VALUES (?, ?, ?, ?)',
                (self.userID, self.prompt, self.response, now),
            )
            self.requestID = cur.lastrowid
            self.created = now
        else:
            cur.execute(
                'UPDATE ai_requests SET response = ? WHERE requestID = ? AND userID = ?',
                (self.response, self.requestID, self.userID),
            )

        conn.commit()
        conn.close()
  

    # Загрузка AI запроса из базы данных по ID
    @staticmethod
    def load_by_id(request_id: int):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT * FROM ai_requests WHERE requestID = ?', (request_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        a = AIRequest(row['userID'], row['prompt'], row['response'], row['requestID'])
        a.created = row['created']
        return a

    # Удаление AI запроса из базы данных
    def delete(self):
        if self.requestID is None:
            return
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM ai_requests WHERE requestID = ? AND userID = ?', (self.requestID, self.userID))
        conn.commit()
        conn.close()