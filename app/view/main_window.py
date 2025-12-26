from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
from .styles import DARK_THEME
from .custom_widgets import DraggableListWidget

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("PDF Master - Combinar y Editar")
        self.resize(1000, 700)
        self.setStyleSheet(DARK_THEME)
        
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # --- Header ---
        header_layout = QHBoxLayout()
        title = QLabel("Editor de PDF")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # --- Área Principal (Drag & Drop) ---
        self.pages_list = DraggableListWidget()
        main_layout.addWidget(self.pages_list)

        # --- Barra de Herramientas (Botones) ---
        toolbar_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("📂 Agregar PDF(s)")
        self.btn_add.clicked.connect(self.controller.handle_add_pdf)
        
        self.btn_delete = QPushButton("🗑️ Borrar Seleccionadas")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(self.controller.handle_delete_page)

        self.btn_rotate_left = QPushButton("⟲ Rotar Izq")
        self.btn_rotate_left.clicked.connect(self.controller.handle_rotate_left)

        self.btn_rotate_right = QPushButton("⟳ Rotar Der")
        self.btn_rotate_right.clicked.connect(self.controller.handle_rotate_right)
        
        self.btn_save = QPushButton("💾 Guardar Nuevo PDF")
        self.btn_save.clicked.connect(self.controller.handle_save_pdf)
        
        self.btn_clear = QPushButton("🔄 Limpiar Todo")
        self.btn_clear.clicked.connect(self.controller.handle_clear)

        toolbar_layout.addWidget(self.btn_add)
        toolbar_layout.addWidget(self.btn_delete)
        toolbar_layout.addSpacing(20) 
        toolbar_layout.addWidget(self.btn_rotate_left)
        toolbar_layout.addWidget(self.btn_rotate_right)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.btn_clear)
        toolbar_layout.addWidget(self.btn_save)
        
        main_layout.addLayout(toolbar_layout)

        # Separador visual (opcional, para dar aire)
        main_layout.addSpacing(10)

        # Footer de Copyright
        self.lbl_copyright = QLabel("© Ing. Jose Luis Muñoz")
        self.lbl_copyright.setAlignment(Qt.AlignCenter)
        # Estilo sutil: letra más pequeña y color grisáceo para no distraer
        self.lbl_copyright.setStyleSheet("font-size: 11px; color: #808080; margin-bottom: 5px;")
        
        main_layout.addWidget(self.lbl_copyright)

    # --- Diálogos ---
    def show_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar PDFs", "", "PDF Files (*.pdf)")
        return files

    def show_save_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "nuevo_documento.pdf", "PDF Files (*.pdf)")
        return path

    def show_message(self, title, text, type="info"):
        if type == "error":
            QMessageBox.critical(self, title, text)
        else:
            QMessageBox.information(self, title, text)
            
    def update_pages_view(self, images_data):
        """Recibe una lista de bytes de imágenes y repuebla la lista."""
        self.pages_list.clear()
        for idx, img_bytes in enumerate(images_data):
            self.pages_list.add_pdf_page(img_bytes, idx)
            
    def get_current_order(self):
        count = self.pages_list.count()
        order = []
        for i in range(count):
            item = self.pages_list.item(i)
            # USAR +1 AQUÍ TAMBIÉN
            original_index = item.data(Qt.UserRole + 1)
            order.append(original_index)
        return order
        
    def get_selected_indices(self):
        """Devuelve una lista de índices visuales seleccionados para borrar."""
        # Necesitamos borrarlos de atrás hacia adelante para no romper índices
        rows = [self.pages_list.row(item) for item in self.pages_list.selectedItems()]
        rows.sort(reverse=True)
        return rows