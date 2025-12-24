# app/view/styles.py

DARK_THEME = """
QMainWindow {
    background-color: #2b2b2b;
}
QWidget {
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    color: #e0e0e0;
}

QMessageBox {
    background-color: #f0f0f0; /* Fondo claro para el diálogo */
}
QMessageBox QLabel {
    color: #000000; /* Texto NEGRO forzado para asegurar lectura */
    background-color: transparent;
}
QMessageBox QPushButton {
    background-color: #3a7ca5;
    color: white;
    padding: 5px 15px;
}

QListWidget {
    background-color: #3c3f41;
    border: 2px dashed #555;
    border-radius: 8px;
    padding: 10px;
}
QListWidget::item {
    background-color: #4b4b4b;
    margin: 5px;
    border-radius: 5px;
    /* Un poco de padding interno para que el texto no toque el borde */
    padding: 5px; 
}
QListWidget::item:selected {
    background-color: #3a7ca5;
    border: 1px solid #6db3df;
}
QPushButton {
    background-color: #3a7ca5;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #4a8cb5;
}
QPushButton:pressed {
    background-color: #2a6c95;
}
QPushButton#dangerBtn {
    background-color: #d9534f;
}
QPushButton#dangerBtn:hover {
    background-color: #c9302c;
}
"""