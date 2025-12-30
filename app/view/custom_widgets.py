import sys
from PyQt5.QtWidgets import QListWidget, QAbstractItemView, QListWidgetItem
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter

# Roles de datos
ROLE_ORIGINAL_INDEX = Qt.UserRole + 1
ROLE_IMAGE_DATA = Qt.UserRole + 2

class DraggableListWidget(QListWidget):
    # Nueva señal para comunicar al controlador que cayeron archivos
    filesDropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Configuración Visual
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Free) # Permitir arrastre libre
        
        # Grid y Tamaños
        self.setGridSize(QSize(160, 220)) # Un poco más grande para evitar cortes
        self.setSpacing(10)
        self.setIconSize(QSize(140, 190))
        self.setWordWrap(True)
        
        # 2. Drag & Drop
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def add_pdf_page(self, img_data, original_index):
        """Crea un item de forma robusta."""
        item = QListWidgetItem()
        
        # 1. Validar imagen
        if not img_data:
            print(f"ADVERTENCIA: Datos de imagen vacíos para pág {original_index}")
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(img_data):
            print("ERROR: No se pudo decodificar la imagen.")
            return

        icon = QIcon(pixmap)
        item.setIcon(icon)
        item.setText(f"Pág {original_index + 1}")
        item.setTextAlignment(Qt.AlignCenter)
        
        # 2. SOLUCIÓN AL RECTÁNGULO BLANCO:
        # Definimos explícitamente el tamaño que debe ocupar el ítem.
        item.setSizeHint(QSize(150, 210))
        
        # 3. Guardar datos ocultos
        item.setData(ROLE_ORIGINAL_INDEX, original_index)
        item.setData(ROLE_IMAGE_DATA, img_data)
        
        self.addItem(item)

    # --- Lógica de Reordenamiento y Drop Externo ---

    def dragEnterEvent(self, event):
        # Aceptar si son archivos del sistema
        if event.mimeData().hasUrls():
            event.accept()
        # Aceptar si es reordenamiento interno
        elif event.source() == self:
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
        # 1. Caso: Archivos Externos (Drag & Drop desde explorador)
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_paths.append(str(url.toLocalFile()))
            
            if file_paths:
                self.filesDropped.emit(file_paths)

        # 2. Caso: Reordenamiento Interno
        elif event.source() == self:
            # 1. Evitamos que Qt intente borrar los items automáticamente
            #    Le decimos "Copia esto", pero nosotros haremos el trabajo sucio.
            event.setDropAction(Qt.CopyAction)
            event.accept()
            
            # 2. Recopilar información del entorno
            # ¿Qué items se mueven?
            selected_items = self.selectedItems()
            if not selected_items:
                return

            # ¿A dónde van?
            cursor_pos = event.pos()
            item_under_mouse = self.itemAt(cursor_pos)
            
            target_index = -1
            if item_under_mouse:
                target_index = self.row(item_under_mouse)
                # Geometría: Si estamos a la derecha del centro, insertamos después (+1)
                rect = self.visualItemRect(item_under_mouse)
                center_x = rect.x() + (rect.width() / 2)
                if cursor_pos.x() > center_x:
                    target_index += 1
            else:
                # Si cae en espacio vacío
                if self.count() > 0 and cursor_pos.y() > self.visualItemRect(self.item(self.count()-1)).y():
                    target_index = self.count()
                else:
                    target_index = 0

            # 3. EXTRAER ESTADO ACTUAL (Snapshot)
            # Guardamos TODO en una lista Python. Esto es seguro y no se borra.
            current_state = []
            moved_indices = []
            
            for i in range(self.count()):
                item = self.item(i)
                data = {
                    'img': item.data(ROLE_IMAGE_DATA),
                    'idx': item.data(ROLE_ORIGINAL_INDEX),
                    'selected': item.isSelected()
                }
                current_state.append(data)
                if item.isSelected():
                    moved_indices.append(i)
            
            # 4. DELEGAR EL REDIBUJADO (Truco del QTimer)
            # Usamos QTimer.singleShot(0, ...) para que esta función se ejecute
            # INMEDIATAMENTE DESPUÉS de que termine el evento Drop actual.
            # Esto evita conflictos de memoria con Qt.
            QTimer.singleShot(0, lambda: self._perform_reorder(current_state, moved_indices, target_index))

        else:
            super().dropEvent(event)

    def _perform_reorder(self, all_data, moving_indices, target_index):
        """Esta función se ejecuta milisegundos después del drop, ya fuera del evento."""
        
        # A. Separar listas en memoria
        items_moving = [all_data[i] for i in moving_indices]
        items_staying = [all_data[i] for i in range(len(all_data)) if i not in moving_indices]
        
        # B. Ajustar índice de destino
        # Si sacamos elementos que estaban antes del target, el target disminuye
        adjustment = sum(1 for x in moving_indices if x < target_index)
        insert_pos = max(0, target_index - adjustment)
        
        # C. Insertar en la lista "staying"
        # Insertamos en orden inverso para mantener la secuencia relativa si movemos varios
        for item_data in reversed(items_moving):
            items_staying.insert(insert_pos, item_data)
            
        # D. FASE NUCLEAR: Limpiar y Redibujar
        self.clear()
        
        for data in items_staying:
            self.add_pdf_page(data['img'], data['idx'])
            
            # Restaurar selección
            if data['selected']:
                new_item = self.item(self.count() - 1)
                new_item.setSelected(True)
        
        # E. Scroll al destino
        if insert_pos < self.count():
            self.scrollToItem(self.item(insert_pos))

    def update_item_image_data(self, item_row, new_img_bytes):
        """
        Actualiza la imagen visual Y los datos ocultos de un ítem.
        Crucial para que la rotación persista al arrastrar.
        """
        item = self.item(item_row)
        if not item:
            return

        # 1. Actualizar lo visual (Icono)
        pixmap = QPixmap()
        pixmap.loadFromData(new_img_bytes)
        item.setIcon(QIcon(pixmap))
        
        # 2. Actualizar el dato oculto (Memoria para Drag & Drop)
        # Si no hacemos esto, al mover la página volverá a su estado original
        item.setData(ROLE_IMAGE_DATA, new_img_bytes)