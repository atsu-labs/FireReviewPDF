import fitz  # PyMuPDF
from PySide6.QtGui import QImage, QPixmap

class PDFHandler:
    _POINTS_TO_MM = 25.4 / 72.0
    _ISO_A_SIZES_MM = {
        "A0": (841, 1189),
        "A1": (594, 841),
        "A2": (420, 594),
        "A3": (297, 420),
        "A4": (210, 297),
        "A5": (148, 210),
        "A6": (105, 148),
    }
    _SIZE_MATCH_TOLERANCE_MM = 3.0

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

    def get_page_size_mm(self, page_num):
        """指定ページのサイズをミリメートルで返す。"""
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return None
        page = self.doc[page_num]
        rect = page.rect
        width_mm = rect.width * self._POINTS_TO_MM
        height_mm = rect.height * self._POINTS_TO_MM
        return width_mm, height_mm

    def get_page_size_label(self, page_num):
        """指定ページのサイズ表示文字列を返す（A判規格名またはmm表記）。"""
        size_mm = self.get_page_size_mm(page_num)
        if not size_mm:
            return "PDFサイズ: -"
        width_mm, height_mm = size_mm
        short_side, long_side = sorted((width_mm, height_mm))
        for name, (std_short, std_long) in self._ISO_A_SIZES_MM.items():
            if (abs(short_side - std_short) <= self._SIZE_MATCH_TOLERANCE_MM
                and abs(long_side - std_long) <= self._SIZE_MATCH_TOLERANCE_MM):
                return f"PDFサイズ: {name}"
        return f"PDFサイズ: {width_mm:.0f}×{height_mm:.0f} mm"

    def close(self):
        if self.doc:
            self.doc.close()
            self.doc = None
