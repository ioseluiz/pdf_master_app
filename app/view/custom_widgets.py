from PyQt6.QtWidgets import QListWidget, QAbstractItemView, QListWidgetItem
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap

ROLE_ORIGINAL_INDEX = Qt.ItemDataRole.UserRole + 1


class DraggableListWidget(QListWidget):
    filesDropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        # Static: items en posiciones de grid fijo → hit-testing O(1) en lugar de O(n)
        self.setMovement(QListWidget.Movement.Static)
        # Todos los items tienen el mismo tamaño → Qt evita recalcular layout por item
        self.setUniformItemSizes(True)

        self.setGridSize(QSize(160, 270))
        self.setSpacing(10)
        self.setIconSize(QSize(140, 180))
        self.setWordWrap(True)

        # Scroll por píxel: más suave al navegar listas grandes
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def add_pdf_page(self, img_data, label_text, original_index):
        if not img_data:
            return
        pixmap = QPixmap()
        if not pixmap.loadFromData(img_data):
            return

        item = QListWidgetItem()
        item.setIcon(QIcon(pixmap))
        item.setText(label_text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setSizeHint(QSize(150, 260))
        item.setData(ROLE_ORIGINAL_INDEX, original_index)
        self.addItem(item)

    # --- Drag & Drop ---

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.source() == self:
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        elif event.source() == self:
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            file_paths = [str(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
            if file_paths:
                self.filesDropped.emit(file_paths)

        elif event.source() == self:
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()

            selected_items = self.selectedItems()
            if not selected_items:
                return

            cursor_pos = event.position().toPoint()
            item_under_mouse = self.itemAt(cursor_pos)

            if item_under_mouse:
                target_index = self.row(item_under_mouse)
                rect = self.visualItemRect(item_under_mouse)
                if cursor_pos.x() > rect.x() + (rect.width() / 2):
                    target_index += 1
            elif self.count() > 0 and cursor_pos.y() > self.visualItemRect(self.item(self.count() - 1)).y():
                target_index = self.count()
            else:
                target_index = 0

            # Capture references now; use them after Qt finishes event processing
            QTimer.singleShot(0, lambda: self._perform_reorder(list(selected_items), target_index))

        else:
            super().dropEvent(event)

    def _perform_reorder(self, items_to_move, target_index):
        # Resolve current rows (may differ from drop-time rows after Qt processing)
        moving_rows = sorted([self.row(item) for item in items_to_move if self.row(item) >= 0])
        if not moving_rows:
            return

        taken = []
        for row in reversed(moving_rows):
            taken.insert(0, self.takeItem(row))

        adjustment = sum(1 for r in moving_rows if r < target_index)
        insert_pos = max(0, target_index - adjustment)

        for i, item in enumerate(taken):
            self.insertItem(insert_pos + i, item)
            item.setSelected(True)

        if taken:
            self.scrollToItem(taken[0])

    def update_item_image_data(self, item_row, new_img_bytes):
        item = self.item(item_row)
        if not item:
            return
        pixmap = QPixmap()
        pixmap.loadFromData(new_img_bytes)
        item.setIcon(QIcon(pixmap))

    def remove_pages_by_original_index(self, original_indices_to_delete):
        """Elimina items por índice de modelo y corrige los índices restantes sin re-renderizar."""
        deleted_set = set(original_indices_to_delete)
        sorted_deleted = sorted(deleted_set)

        rows_to_remove = [
            i for i in range(self.count())
            if self.item(i).data(ROLE_ORIGINAL_INDEX) in deleted_set
        ]
        for row in reversed(rows_to_remove):
            self.takeItem(row)

        for i in range(self.count()):
            item = self.item(i)
            old_idx = item.data(ROLE_ORIGINAL_INDEX)
            shift = sum(1 for d in sorted_deleted if d < old_idx)
            item.setData(ROLE_ORIGINAL_INDEX, old_idx - shift)
