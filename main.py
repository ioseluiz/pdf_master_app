import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from app.model.pdf_manager import PDFModel
from app.view.main_window import MainWindow
from app.controller.main_controller import MainController

def main():
    app = QApplication(sys.argv)

    # Icono de la aplicación (ventana + barra de tareas)
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Instanciamos componentes MVC
    model = PDFModel()
    controller = MainController()
    
    # Inyectamos dependencias
    # La vista necesita el controlador para conectar botones
    view = MainWindow(controller) 
    
    # El controlador necesita acceso a ambos
    controller.set_model(model)
    controller.set_view(view)

    view.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()