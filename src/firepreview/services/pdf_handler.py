import fitz  # PyMuPDF
from PySide6.QtGui import QImage, QPixmap

class PDFHandler:
    def __init__(self):
        self.doc = None
        self.current_page_num = 0

    def open_file(self, file_path):
        try:
            self.doc = fitz.open(file_path)
            self.current_page_num = 0
            return True
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return False

    def get_page_count(self):
        return len(self.doc) if self.doc else 0

    def get_page_pixmap(self, page_num, dpi=150):
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return None
        
        page = self.doc[page_num]
        zoom = dpi / 72  # 72 is the default PDF DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert pixmap to QImage
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        return QPixmap.fromImage(img)

    def close(self):
        if self.doc:
            self.doc.close()
            self.doc = None
