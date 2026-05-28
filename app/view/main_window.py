from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QMessageBox, QComboBox,
                             QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from .styles import DARK_THEME
from .custom_widgets import DraggableListWidget

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("PDF Master - Combinar y Editar")
        self.resize(1000, 700)
        self.setMinimumSize(850, 580)
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

        # --- Área Principal ---
        self.pages_list = DraggableListWidget()
        self.pages_list.filesDropped.connect(self.controller.handle_dropped_files)
        main_layout.addWidget(self.pages_list)

        # --- Barra de Progreso (oculta por defecto) ---
        self.progress_widget = QWidget()
        progress_layout = QHBoxLayout(self.progress_widget)
        progress_layout.setContentsMargins(4, 0, 4, 0)
        progress_layout.setSpacing(8)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(14)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3c3f41;
                border: 1px solid #555;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #3a7ca5;
                border-radius: 3px;
            }
        """)

        progress_layout.addWidget(self.progress_label, 1)
        progress_layout.addWidget(self.progress_bar, 2)
        self.progress_widget.setVisible(False)
        main_layout.addWidget(self.progress_widget)

        # --- Barra de Herramientas ---
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
        
        # --- SELECTOR DE CALIDAD (ESTILO CORREGIDO) ---
        self.combo_quality = QComboBox()
        self.combo_quality.addItems([
            "Calidad: Standard (Balanceado)",
            "Calidad: Alta (Original)",
            "Calidad: Baja (Archivo Pequeño)"
        ])
        
        # MODIFICACIÓN: Estilo explícito para la lista desplegable
        self.combo_quality.setStyleSheet("""
            QComboBox {
                background-color: #3c3f41;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
                min-width: 160px;
            }
            
            /* Estilo para la lista desplegable interna */
            QComboBox QAbstractItemView {
                background-color: #3c3f41; /* Fondo oscuro igual al combo */
                color: white;              /* Texto blanco */
                selection-background-color: #3a7ca5; /* Azul al pasar el mouse */
                selection-color: white;
                border: 1px solid #555;
            }
            
            /* Flecha */
            QComboBox::drop-down {
                border: 0px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white; /* Dibujamos una flecha simple con CSS */
                margin-right: 10px;
            }
        """)
        
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
        
        toolbar_layout.addWidget(self.combo_quality)
        toolbar_layout.addWidget(self.btn_save)
        toolbar_layout.addWidget(self.btn_clear)
        
        main_layout.addLayout(toolbar_layout)
        main_layout.addSpacing(10)

        # Footer
        self.lbl_copyright = QLabel("© Ing. Jose Luis Muñoz")
        self.lbl_copyright.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_copyright.setStyleSheet("font-size: 11px; color: #808080; margin-bottom: 5px;")
        main_layout.addWidget(self.lbl_copyright)

    # --- Diálogos y Helpers ---
    def show_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar PDFs", "", "PDF Files (*.pdf)")
        return files

    def show_save_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", "nuevo_documento.pdf", "PDF Files (*.pdf)")
        return path

    def get_selected_quality_code(self):
        """Traduce la selección del usuario a un código interno."""
        index = self.combo_quality.currentIndex()
        if index == 1: return 'high'
        if index == 2: return 'low'
        return 'standard'

    def show_message(self, title, text, type="info"):
        if type == "error":
            QMessageBox.critical(self, title, text)
        else:
            QMessageBox.information(self, title, text)
            
    def update_pages_view(self, pages_data):
        self.pages_list.clear()
        for idx, (img_bytes, label) in enumerate(pages_data):
            self.pages_list.add_pdf_page(img_bytes, label, idx)
            
    def get_current_order(self):
        count = self.pages_list.count()
        order = []
        for i in range(count):
            item = self.pages_list.item(i)
            original_index = item.data(Qt.ItemDataRole.UserRole + 1)
            order.append(original_index)
        return order
        
    def get_selected_indices(self):
        indices = [item.data(Qt.ItemDataRole.UserRole + 1) for item in self.pages_list.selectedItems()]
        indices.sort(reverse=True)
        return indices

    # --- Progreso de carga ---
    def show_progress(self, value, maximum, label=""):
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
        self.progress_label.setText(label)
        self.progress_widget.setVisible(True)

    def show_progress_complete(self):
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_label.setText("Carga completada")
        QTimer.singleShot(2500, self.hide_progress)

    def hide_progress(self):
        self.progress_widget.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("")