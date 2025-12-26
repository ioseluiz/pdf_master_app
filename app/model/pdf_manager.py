import fitz  # PyMuPDF
import io

class PDFModel:
    def __init__(self):
        self.current_doc = fitz.open()  # Documento vacío al inicio
        self.page_mapping = [] # Lista para rastrear el origen de cada página

    def load_pdf(self, filepath):
        """Carga un PDF y lo agrega al documento actual (fusión)."""
        new_doc = fitz.open(filepath)
        self.current_doc.insert_pdf(new_doc)
        new_doc.close()

    def get_page_count(self):
        return len(self.current_doc)

    def get_page_image(self, page_index):
        """Renderiza una página específica como bytes de imagen para la UI."""
        if page_index < 0 or page_index >= len(self.current_doc):
            return None
            
        page = self.current_doc.load_page(page_index)
        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5)) # Escala al 50% para preview rápido
        
        # Convertir a formato compatible con Qt (bytes PNG)
        img_bytes = pix.tobytes("png")
        return img_bytes

    def reorder_and_save(self, new_order_indices, output_path):
        """Crea un nuevo PDF basado en el nuevo orden de índices y lo guarda."""
        new_doc = fitz.open()
        
        # Copiamos las páginas en el nuevo orden
        for index in new_order_indices:
            new_doc.insert_pdf(self.current_doc, from_page=index, to_page=index)
            
        new_doc.save(output_path)
        new_doc.close()

    def delete_page(self, index):
        """Elimina una página del documento en memoria."""
        self.current_doc.delete_page(index)

    def rotate_page(self, page_index, clockwise=True):
        """Rota una página 90 grados a la derecha o izquierda."""
        if page_index < 0 or page_index >= len(self.current_doc):
            return

        page = self.current_doc[page_index]
        # Obtenemos rotación actual
        current_rot = page.rotation
        
        # Calculamos nueva rotación
        if clockwise:
            new_rot = (current_rot + 90) % 360
        else:
            new_rot = (current_rot - 90) % 360
            
        page.set_rotation(new_rot)