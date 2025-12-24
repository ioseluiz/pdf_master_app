import sys
from PyQt5.QtWidgets import QApplication
from app.model.pdf_manager import PDFModel
from app.view.main_window import MainWindow
from app.controller.main_controller import MainController

def main():
    app = QApplication(sys.argv)

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
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()