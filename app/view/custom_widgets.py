import sys
from PyQt5.QtWidgets import QListWidget, QAbstractItemView, QListWidgetItem
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter

ROLE_ORIGINAL_INDEX = Qt.UserRole + 1
ROLE_IMAGE_DATA = Qt.UserRole + 2

class DraggableListWidget(QListWidget):
    filesDropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Free)
        
        # --- CORRECCIÓN DE ESPACIO PARA VERTICALES ---
        
        # 1. GridSize: Aumentamos la altura total de la celda a 270 (antes 240)
        #    Esto da mucho aire abajo.
        self.setGridSize(QSize(160, 270)) 
        
        self.setSpacing(10)
        
        # 2. IconSize: Limitamos la altura de la imagen a 180 (antes 190)
        #    Cálculo: 270 (Total) - 180 (Imagen) = 90px libres para texto.
        self.setIconSize(QSize(140, 180))
        
        self.setWordWrap(True)
        
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def add_pdf_page(self, img_data, label_text, original_index):
        item = QListWidgetItem()
        
        if not img_data:
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(img_data):
            return

        icon = QIcon(pixmap)
        item.setIcon(icon)
        
        item.setText(label_text)
        item.setTextAlignment(Qt.AlignCenter)
        
        # 3. SizeHint: Debe coincidir casi con el GridSize para reservar el espacio
        item.setSizeHint(QSize(150, 260))
        
        item.setData(ROLE_ORIGINAL_INDEX, original_index)
        item.setData(ROLE_IMAGE_DATA, img_data)
        
        self.addItem(item)

    # --- Drag & Drop (Código intacto) ---

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.source() == self:
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        elif event.source() == self:
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            file_paths = [str(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
            if file_paths:
                self.filesDropped.emit(file_paths)

        elif event.source() == self:
            event.setDropAction(Qt.CopyAction)
            event.accept()
            
            selected_items = self.selectedItems()
            if not selected_items: return

            cursor_pos = event.pos()
            item_under_mouse = self.itemAt(cursor_pos)
            
            target_index = -1
            if item_under_mouse:
                target_index = self.row(item_under_mouse)
                rect = self.visualItemRect(item_under_mouse)
                if cursor_pos.x() > rect.x() + (rect.width() / 2):
                    target_index += 1
            else:
                if self.count() > 0 and cursor_pos.y() > self.visualItemRect(self.item(self.count()-1)).y():
                    target_index = self.count()
                else:
                    target_index = 0

            current_state = []
            moved_indices = []
            for i in range(self.count()):
                item = self.item(i)
                data = {
                    'img': item.data(ROLE_IMAGE_DATA),
                    'idx': item.data(ROLE_ORIGINAL_INDEX),
                    'label': item.text(), 
                    'selected': item.isSelected()
                }
                current_state.append(data)
                if item.isSelected():
                    moved_indices.append(i)
            
            QTimer.singleShot(0, lambda: self._perform_reorder(current_state, moved_indices, target_index))

        else:
            super().dropEvent(event)

    def _perform_reorder(self, all_data, moving_indices, target_index):
        items_moving = [all_data[i] for i in moving_indices]
        items_staying = [all_data[i] for i in range(len(all_data)) if i not in moving_indices]
        
        adjustment = sum(1 for x in moving_indices if x < target_index)
        insert_pos = max(0, target_index - adjustment)
        
        for item_data in reversed(items_moving):
            items_staying.insert(insert_pos, item_data)
            
        self.clear()
        
        for data in items_staying:
            self.add_pdf_page(data['img'], data['label'], data['idx'])
            
            if data['selected']:
                new_item = self.item(self.count() - 1)
                new_item.setSelected(True)
        
        if insert_pos < self.count():
            self.scrollToItem(self.item(insert_pos))

    def update_item_image_data(self, item_row, new_img_bytes):
        item = self.item(item_row)
        if not item: return
        pixmap = QPixmap()
        pixmap.loadFromData(new_img_bytes)
        item.setIcon(QIcon(pixmap))
        item.setData(ROLE_IMAGE_DATA, new_img_bytes)