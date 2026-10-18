from collections import OrderedDict
import fitz  # PyMuPDF
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPixmap

class PDFHandler:
    SIZE_LABEL_UNKNOWN = "PDFサイズ: -"
    BASE_RENDER_DPI = 150
    MAX_DYNAMIC_DPI = 600
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
        self._pixmap_cache = OrderedDict()
        self._cache_limit = 3
        self._clip_cache = OrderedDict()
        self._clip_cache_limit = 6

    def open_file(self, file_path):
        try:
            self.doc = fitz.open(file_path)
            self.current_page_num = 0
            self._pixmap_cache.clear()
            self._clip_cache.clear()
            return True
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return False

    def get_page_count(self):
        return len(self.doc) if self.doc else 0

    def get_page_pixmap(self, page_num, dpi=150, grayscale=False):
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return None
        
        cache_key = (page_num, dpi, grayscale)
        if cache_key in self._pixmap_cache:
            # Move to end (most recently used)
            pixmap = self._pixmap_cache.pop(cache_key)
            self._pixmap_cache[cache_key] = pixmap
            return pixmap

        page = self.doc[page_num]
        zoom = dpi / 72  # 72 is the default PDF DPI
        mat = fitz.Matrix(zoom, zoom)
        if grayscale:
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_Grayscale8).copy()
        else:
            pix = page.get_pixmap(matrix=mat)
            # Convert pixmap to QImage (use .copy() to ensure safe memory ownership)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(img)
        
        # Insert and enforce size limit
        self._pixmap_cache[cache_key] = pixmap
        if len(self._pixmap_cache) > self._cache_limit:
            self._pixmap_cache.popitem(last=False)  # Pop oldest (first item)
        return pixmap

    def get_page_clip_pixmap(
        self,
        page_num: int,
        clip_rect_scene: QRectF,
        dpi: int = 300,
        base_dpi: int = BASE_RENDER_DPI,
        grayscale: bool = False,
    ):
        """指定されたシーン座標領域（base_dpi基準）のみを高解像度でラスタライズして返す。

        Returns:
            tuple[QPixmap, QRectF] | None: (高解像度QPixmap, base_dpiシーン座標系での正確な配置QRectF)
        """
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return None
        if dpi <= 0 or base_dpi <= 0:
            return None

        target_dpi = min(int(round(dpi)), self.MAX_DYNAMIC_DPI)
        if isinstance(clip_rect_scene, QRectF):
            rx, ry, rw, rh = (
                clip_rect_scene.x(),
                clip_rect_scene.y(),
                clip_rect_scene.width(),
                clip_rect_scene.height(),
            )
        else:
            rx, ry, rw, rh = clip_rect_scene

        if rw <= 0 or rh <= 0:
            return None

        page = self.doc[page_num]
        page_rect = page.rect
        scale_to_pt = 72.0 / float(base_dpi)

        fitz_clip = fitz.Rect(
            page_rect.x0 + rx * scale_to_pt,
            page_rect.y0 + ry * scale_to_pt,
            page_rect.x0 + (rx + rw) * scale_to_pt,
            page_rect.y0 + (ry + rh) * scale_to_pt,
        ) & page_rect

        if fitz_clip.is_empty or fitz_clip.width <= 0 or fitz_clip.height <= 0:
            return None

        zoom = float(target_dpi) / 72.0
        mat = fitz.Matrix(zoom, zoom)
        full_irect = (page_rect * mat).irect
        clip_irect = (fitz_clip * mat).irect

        cache_key = (
            page_num,
            target_dpi,
            bool(grayscale),
            clip_irect.x0,
            clip_irect.y0,
            clip_irect.x1,
            clip_irect.y1,
        )
        if cache_key in self._clip_cache:
            cached = self._clip_cache.pop(cache_key)
            self._clip_cache[cache_key] = cached
            return cached

        if grayscale:
            pix = page.get_pixmap(matrix=mat, clip=fitz_clip, colorspace=fitz.csGRAY)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_Grayscale8).copy()
        else:
            pix = page.get_pixmap(matrix=mat, clip=fitz_clip)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(img)

        scene_scale = float(base_dpi) / float(target_dpi)
        pix_x0 = pix.irect[0]
        pix_y0 = pix.irect[1]
        scene_x = (pix_x0 - full_irect.x0) * scene_scale
        scene_y = (pix_y0 - full_irect.y0) * scene_scale
        scene_w = pix.width * scene_scale
        scene_h = pix.height * scene_scale
        actual_scene_rect = QRectF(scene_x, scene_y, scene_w, scene_h)

        result = (pixmap, actual_scene_rect)
        self._clip_cache[cache_key] = result
        if len(self._clip_cache) > self._clip_cache_limit:
            self._clip_cache.popitem(last=False)
        return result

    def get_page_size_mm(self, page_num):
        """指定ページのサイズをミリメートルで返す。

        Returns:
            tuple[float, float] | None: (幅mm, 高さmm)。無効なページは None。
        """
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return None
        page = self.doc[page_num]
        rect = page.rect
        width_mm = rect.width * self._POINTS_TO_MM
        height_mm = rect.height * self._POINTS_TO_MM
        return width_mm, height_mm

    def get_page_size_label(self, page_num):
        """指定ページのサイズ表示文字列を返す（A判規格名またはmm表記）。

        Returns:
            str: 例) "PDFサイズ: A4" / "PDFサイズ: 210×297 mm"
        """
        size_mm = self.get_page_size_mm(page_num)
        if not size_mm:
            return self.SIZE_LABEL_UNKNOWN
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
            self._pixmap_cache.clear()
            self._clip_cache.clear()
