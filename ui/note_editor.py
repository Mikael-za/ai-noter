# note_editor.py
import os
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QLabel,
    QMessageBox, QScrollArea, QSizePolicy, QPlainTextEdit, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QPixmap, QMouseEvent
from models import Note
from paths import get_app_data_path

# Путь к папке с изображениями (работает в обычном проекте и в exe)
IMAGE_DIR = get_app_data_path() / "storage" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)


class AutoGrowTextEdit(QPlainTextEdit):
    def __init__(self, min_lines=1, max_lines=200):
        super().__init__()
        self.min_lines = min_lines
        self.max_lines = max_lines
        self.padding = 12
        self._delete_mode = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFrameStyle(0)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.textChanged.connect(self.adjust_height)
        QTimer.singleShot(0, self.adjust_height)

    # Автоматическое изменение высоты текстового блока в зависимости от количества строк
    def adjust_height(self):
        blocks = max(1, self.document().blockCount())
        fm = self.fontMetrics()
        line_h = fm.lineSpacing() or 16
        lines = max(self.min_lines, min(self.max_lines, blocks))
        new_h = int(lines * line_h + self.padding)
        min_h = int(self.min_lines * line_h + self.padding)
        max_h = int(self.max_lines * line_h + self.padding)
        new_h = max(min_h, min(max_h, new_h))
        self.setFixedHeight(new_h)
        if self.parentWidget() is not None:
            self.parentWidget().adjustSize()
    
    # Установка режима удаления для блока (блокировка редактирования)
    def set_delete_mode(self, enabled):
        self._delete_mode = enabled
        if enabled:
            self.setReadOnly(True)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        else:
            self.setReadOnly(False)
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    # Перехват кликов в режиме удаления для удаления блока
    def mousePressEvent(self, event):
        if self._delete_mode:
            # в режиме удаления вызываем удаление напрямую через родителя
            parent = self.parentWidget()
            while parent:
                if hasattr(parent, '_delete_block'):
                    parent._delete_block(self)
                    return
                parent = parent.parentWidget()
            return
        super().mousePressEvent(event)


class NoteEditor(QWidget):
    def __init__(self, user, note: Note = None, scheduler=None):
        super().__init__()
        self.user = user
        self.note = note
        self.scheduler = scheduler
        self.setWindowTitle("Редактор заметки")
        self.blocks = []
        # список меток с изображениями для ресайза
        self._image_labels = []
        # режим удаления блоков
        self._delete_mode = False
        # флаг для предотвращения параллельных удалений
        self._deleting_block = False
        self._build_ui()
        self.showMaximized()
        if self.note:
            self.load_note()

    # Построение интерфейса редактора заметок с поддержкой текстовых блоков и изображений
    def _build_ui(self):
        v = QVBoxLayout()
        
        # Кнопка возврата в левом верхнем углу
        top_layout = QHBoxLayout()
        self.btn_nav_back = QPushButton('←')
        self.btn_nav_back.setFixedSize(30, 30)
        self.btn_nav_back.setStyleSheet("QPushButton { border: none; font-size: 18px; }")
        self.btn_nav_back.clicked.connect(self.back)
        top_layout.addWidget(self.btn_nav_back)
        top_layout.addStretch()
        v.addLayout(top_layout)
        
        self.title = QLineEdit()
        self.title.setPlaceholderText("Заголовок")
        # область прокрутки с контейнером блоков
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(8)
        # добавляем нижний отступ, чтобы контент не перекрывался кнопками
        # отступ должен быть достаточным для всех кнопок внизу
        self.container_layout.setContentsMargins(0, 0, 0, 100)
        self.container_layout.addStretch(1)
        self.scroll.setWidget(self.container)

        self.txt = None  # будет первым текстовым блоком внутри scroll
        self.btn_add_text = QPushButton("Добавить текст")
        self.btn_add_photo = QPushButton("Добавить фото")
        self.btn_delete_block = QPushButton("Удалить блок")
        self.btn_save = QPushButton("Сохранить")

        # раскладка кнопок 
        v.addWidget(self.title)
        v.addWidget(self.scroll)
        v.addWidget(self.btn_add_text)
        v.addWidget(self.btn_add_photo)
        v.addWidget(self.btn_delete_block)
        v.addWidget(self.btn_save)
        self.setLayout(v)

        # подключаем сигналы (lambda чтобы не получать bool)
        self.btn_add_text.clicked.connect(lambda: self.add_text_block())
        self.btn_add_photo.clicked.connect(lambda: self.add_image_block())
        self.btn_delete_block.clicked.connect(self.toggle_delete_mode)
        self.btn_save.clicked.connect(self.save_note)
        
        # устанавливаем обработчик событий для контейнера и scroll area
        self.container.installEventFilter(self)
        self.scroll.viewport().installEventFilter(self)

    # Добавление нового текстового блока в заметку
    def add_text_block(self, text=""):
        te = AutoGrowTextEdit(min_lines=1, max_lines=200)
        te.setPlainText(text)
        # вставляем перед растягивающим элемент (последним)
        idx = self.container_layout.count() - 1
        self.container_layout.insertWidget(idx, te)
        # устанавливаем обработчик событий для клика
        te.installEventFilter(self)
        QTimer.singleShot(0, te.adjust_height)
        return te

    # Добавление нового блока с изображением в заметку с выбором файла через диалог
    def add_image_block(self, path=None, auto_add_text=False):
        if not path:
            fpath, _ = QFileDialog.getOpenFileName(
                self, "Выберите изображение", filter="Images (*.png *.jpg *.bmp *.jpeg)"
            )
            if not fpath:
                return
            path = fpath

        pix_orig = QPixmap(path)
        if pix_orig.isNull():
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить изображение: {path}")
            return

        # создаём метку и сохраняем оригинал + аспект
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lbl.original_pixmap = pix_orig
        # защитимся от деления на ноль
        w = pix_orig.width() or 1
        h = pix_orig.height() or 1
        lbl.aspect_ratio = w / h
        lbl.img_path = path  # исходный путь (для сохранения)
        # масштабируем под текущую ширину контейнера
        self._resize_image(lbl)

        idx = self.container_layout.count() - 1
        self.container_layout.insertWidget(idx, lbl)
        # регистрируем в списке для ресайза
        self._image_labels.append(lbl)
        # устанавливаем обработчик событий для клика
        lbl.installEventFilter(self)
        # опционально добавляем текстовый блок после изображения (только при ручном добавлении)
        if auto_add_text:
            te = self.add_text_block()
            te.setFocus()
        return lbl

    # Загрузка существующей заметки из базы данных и отображение всех блоков
    def load_note(self):
        self.title.setText(self.note.title)
        # очищаем контейнер (удаляем виджеты)
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.container_layout.addStretch(1)
        # очистим список изображений
        self._image_labels = []
        # наполняем блоками из note.content
        for b in self.note.content:
            t = b.get("type")
            if t == "text":
                self.add_text_block(b.get("content", ""))
            elif t == "image":
                rel = b.get("content", "")
                # в базе хранится относительный путь (как в первом коде)
                base = get_app_data_path()
                p = base / rel if rel else None
                if p and p.exists():
                    # передаём строковый путь, без автоматического добавления текста при загрузке
                    self.add_image_block(str(p), auto_add_text=False)
                else:
                    lbl = QLabel(f"⚠️ Изображение не найдено: {rel}")
                    lbl.setStyleSheet("color: red; font-style: italic; padding:4px;")
                    idx = self.container_layout.count() - 1
                    self.container_layout.insertWidget(idx, lbl)
                    # устанавливаем обработчик событий для клика
                    lbl.installEventFilter(self)

    # Сохранение заметки: сбор всех блоков, копирование изображений в storage и запись в БД
    def save_note(self):
        title = self.title.text().strip()
        # собираем блоки из виджетов контейнера в правильном порядке
        data = []
        for i in range(self.container_layout.count() - 1):  # пропускаем последний stretch
            item = self.container_layout.itemAt(i)
            w = item.widget()
            if w is None:
                continue
            if isinstance(w, AutoGrowTextEdit):
                txt = w.toPlainText().strip()
                if txt:
                    data.append({"type": "text", "content": txt})
            elif isinstance(w, QLabel):
                path = getattr(w, "img_path", "")
                if path:
                    # перед сохранением — убедимся, что изображение находится в IMAGE_DIR
                    src = Path(path)
                    try:
                        if not src.exists():
                            # если фото было ссылкой на несуществующий файл, пропустить
                            continue
                        fname = os.path.basename(path)
                        dest = IMAGE_DIR / f"{int(src.stat().st_mtime)}_{fname}"
                        if not dest.exists():
                            shutil.copy(path, dest)
                        # Сохраняем относительный путь от корня приложения
                        base = get_app_data_path()
                        rel = str(dest.relative_to(base))
                        data.append({"type": "image", "content": rel})
                    except PermissionError:
                        QMessageBox.warning(self, "Ошибка", "Нет прав доступа для сохранения изображения. Проверьте права доступа к папке storage/images.")
                        return
                    except OSError as e:
                        if "No space left" in str(e) or "errno 28" in str(e):
                            QMessageBox.warning(self, "Ошибка", "Недостаточно места на диске для сохранения изображения.")
                        else:
                            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить изображение: {e}")
                        return
                    except Exception as e:
                        QMessageBox.warning(self, "Ошибка", f"Неожиданная ошибка при сохранении изображения: {e}")
                        return
        # если нет заголовка и нет содержимого — предупреждение
        if not title and not data:
            QMessageBox.warning(self, "Ошибка", "Заметка пуста")
            return
        # сохраняем через models.Note (как в первом коде)
        if self.note is None:
            n = Note(self.user.userID, title, data)
        else:
            n = self.note
            n.title = title
            n.content = data
        n.save()
        QMessageBox.information(self, "OK", "Сохранено")
        from ui.notes_list import NotesList
        self.listw = NotesList(self.user, self.scheduler)
        self.listw.show()
        self.close()

    # Возврат к списку заметок
    def back(self):
        from ui.notes_list import NotesList
        self.listw = NotesList(self.user, self.scheduler)
        self.listw.show()
        self.close()

    # Пересчет размеров изображений при изменении размера окна
    def resizeEvent(self, event):
        super().resizeEvent(event)
        for lbl in list(self._image_labels):
            self._resize_image(lbl)

    # Масштабирование изображения под ширину видимой области с сохранением пропорций
    def _resize_image(self, lbl):
        if not hasattr(lbl, "original_pixmap"):
            return
        # ширина доступной области для изображения (немного отступа)
        try:
            avail_w = max(100, self.scroll.viewport().width() - 20)
        except Exception:
            avail_w = 600
        # вычисляем высоту с учётом aspect_ratio
        new_w = int(avail_w)
        new_h = max(20, int(new_w / (getattr(lbl, "aspect_ratio", 1) or 1)))
        scaled = lbl.original_pixmap.scaled(
            new_w, new_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        lbl.setPixmap(scaled)
        lbl.setFixedHeight(scaled.height())
    
    # Переключение режима удаления блоков: включение/выключение визуальных индикаторов
    def toggle_delete_mode(self):
        # если выходим из режима удаления
        if self._delete_mode:
            self._delete_mode = False
            self.btn_delete_block.setText("Удалить блок")
            self.btn_delete_block.setStyleSheet("")
            # возвращаем обычный стиль
            self._update_blocks_style()
            return
        
        # проверяем, есть ли блоки для удаления
        has_blocks = False
        for i in range(self.container_layout.count() - 1):  # пропускаем последний stretch
            item = self.container_layout.itemAt(i)
            w = item.widget()
            if w is not None:
                if isinstance(w, AutoGrowTextEdit):
                    has_blocks = True
                    break
                elif isinstance(w, QLabel) and hasattr(w, "img_path"):
                    # учитываем только QLabel с изображениями, не сообщения об ошибках
                    has_blocks = True
                    break
        
        if not has_blocks:
            QMessageBox.warning(self, "Ошибка", "Нет блоков для удаления")
            return
        
        # включаем режим удаления
        self._delete_mode = True
        self.btn_delete_block.setText("Отменить удаление")
        self.btn_delete_block.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; }")
        # обновляем визуальное отображение блоков
        self._update_blocks_style()
        QMessageBox.information(self, "Режим удаления", "Нажмите на блок, который хотите удалить")
    
    # Обновление визуального стиля всех блоков в зависимости от режима удаления
    def _update_blocks_style(self):
        for i in range(self.container_layout.count() - 1):  # пропускаем последний stretch
            item = self.container_layout.itemAt(i)
            w = item.widget()
            if w is None:
                continue
            # обрабатываем только реальные блоки контента
            if isinstance(w, AutoGrowTextEdit):
                if self._delete_mode:
                    w.setStyleSheet("border: 2px dashed #ff6b6b; padding: 4px;")
                    w.setCursor(Qt.CursorShape.PointingHandCursor)
                    w.set_delete_mode(True)
                else:
                    w.setStyleSheet("")
                    w.setCursor(Qt.CursorShape.IBeamCursor)
                    w.set_delete_mode(False)
            elif isinstance(w, QLabel) and hasattr(w, "img_path"):
                # обрабатываем только QLabel с изображениями, не сообщения об ошибках
                if self._delete_mode:
                    w.setStyleSheet("border: 2px dashed #ff6b6b; padding: 4px;")
                    w.setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    w.setStyleSheet("")
                    w.setCursor(Qt.CursorShape.ArrowCursor)
    
    # Обработка событий клика для удаления блоков в режиме удаления
    def eventFilter(self, obj, event):
        if self._delete_mode and isinstance(event, QMouseEvent) and event.type() == QEvent.Type.MouseButtonPress:
            # если клик был по блоку в контейнере
            if isinstance(obj, AutoGrowTextEdit) or (isinstance(obj, QLabel) and hasattr(obj, "img_path")):
                # проверяем, что это не заголовок (заголовок не в контейнере, но на всякий случай)
                if obj == self.title:
                    return False
                
                # удаляем блок
                self._delete_block(obj)
                return True  # перехватываем событие, чтобы не обрабатывалось дальше
            
            # если клик был по viewport scroll area, преобразуем координаты
            if obj == self.scroll.viewport():
                pos = event.pos()
                # используем глобальные координаты для более точного определения виджета
                global_pos = self.scroll.viewport().mapToGlobal(pos)
                container_pos = self.container.mapFromGlobal(global_pos)
                widget = self.container.childAt(container_pos)
                if widget and (isinstance(widget, AutoGrowTextEdit) or (isinstance(widget, QLabel) and hasattr(widget, "img_path"))):
                    if widget != self.title:
                        self._delete_block(widget)
                        return True
                return False
            
            # если клик был по контейнеру, находим виджет под курсором
            if obj == self.container:
                pos = event.pos()
                widget = self.container.childAt(pos)
                if widget and (isinstance(widget, AutoGrowTextEdit) or (isinstance(widget, QLabel) and hasattr(widget, "img_path"))):
                    if widget != self.title:
                        self._delete_block(widget)
                        return True
                return False
        
        return super().eventFilter(obj, event)
    
    # Удаление указанного блока из заметки с защитой от параллельных удалений
    def _delete_block(self, widget):
        # защита от параллельных удалений
        if self._deleting_block:
            return
        
        if not (isinstance(widget, AutoGrowTextEdit) or (isinstance(widget, QLabel) and hasattr(widget, "img_path"))):
            return
        
        # проверяем, что виджет ещё существует в layout
        if self.container_layout.indexOf(widget) == -1:
            return
        
        self._deleting_block = True
        try:
            # если это изображение, удаляем из списка
            if isinstance(widget, QLabel) and hasattr(widget, "img_path"):
                if widget in self._image_labels:
                    self._image_labels.remove(widget)
            
            # удаляем виджет из layout
            self.container_layout.removeWidget(widget)
            widget.deleteLater()
            
            # проверяем, остались ли ещё блоки
            has_blocks = False
            for i in range(self.container_layout.count() - 1):
                item = self.container_layout.itemAt(i)
                w = item.widget()
                if w is not None:
                    if isinstance(w, AutoGrowTextEdit):
                        has_blocks = True
                        break
                    elif isinstance(w, QLabel) and hasattr(w, "img_path"):
                        has_blocks = True
                        break
            
            # выходим из режима удаления только если блоков не осталось
            if not has_blocks:
                self._delete_mode = False
                self.btn_delete_block.setText("Удалить блок")
                self.btn_delete_block.setStyleSheet("")
            
            self._update_blocks_style()
            QMessageBox.information(self, "Удалено", "Блок удалён")
        finally:
            self._deleting_block = False