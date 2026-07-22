import io
from PIL import Image, ImageEnhance, ImageFilter
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPen, QColor, QBrush, QCursor, QPixmap
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsScene, QGraphicsDropShadowEffect

class ImageLayerItem(QGraphicsObject):
    # Signal emitted when position or size of this layer changes
    changed = Signal()

    def __init__(self, pixmap, filename, file_data, is_background=False, parent=None):
        super().__init__(parent)
        self.original_pixmap = pixmap
        self.pixmap = pixmap
        self.filename = filename
        self.file_data = file_data
        self.processed_file_data = file_data
        self.processed_mime_type = None
        self.is_background = is_background
        
        self.rect = QRectF(0, 0, pixmap.width(), pixmap.height())
        self.active_handle = None
        self.start_pos = None
        self.start_rect = None
        self.start_scene_pos = None
        self.start_aspect_ratio = pixmap.width() / max(1.0, pixmap.height())
        self.keep_aspect_ratio = True  # Default to keeping aspect ratio
        
        # Visibility effect settings
        self.effect_type = "none"  # "none", "shadow", "glow"
        self.effect_radius = 15
        self.shadow_effect = None
        
        # Image adjustment values
        self.blur_val = 0        # 0 ~ 30
        self.brightness_val = 0  # -100 ~ 100
        self.contrast_val = 0    # -100 ~ 100
        self.temp_val = 0        # -100 ~ 100
        self._pil_base_image = None
        
        # Configure flags for interactive manipulation
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def _get_base_image(self):
        if self._pil_base_image is None:
            try:
                self._pil_base_image = Image.open(io.BytesIO(self.file_data)).convert("RGBA")
            except Exception:
                return None
        return self._pil_base_image.copy()

    def apply_image_adjustments(self, blur=None, brightness=None, contrast=None, temp=None):
        if blur is not None:
            self.blur_val = blur
        if brightness is not None:
            self.brightness_val = brightness
        if contrast is not None:
            self.contrast_val = contrast
        if temp is not None:
            self.temp_val = temp

        # If all filter values are default, reset to original data
        if self.blur_val == 0 and self.brightness_val == 0 and self.contrast_val == 0 and self.temp_val == 0:
            self.processed_file_data = self.file_data
            self.pixmap = self.original_pixmap
            self.update()
            self.changed.emit()
            return

        try:
            img = self._get_base_image()
            if img is None:
                return

            # 1. Brightness Adjustment
            if self.brightness_val != 0:
                factor = 1.0 + (self.brightness_val / 100.0)
                img = ImageEnhance.Brightness(img).enhance(max(0.0, factor))

            # 2. Contrast Adjustment
            if self.contrast_val != 0:
                factor = 1.0 + (self.contrast_val / 100.0)
                img = ImageEnhance.Contrast(img).enhance(max(0.0, factor))

            # 3. Temperature Adjustment (Warmth: Red/Yellow vs Cool: Blue/Cyan)
            if self.temp_val != 0:
                r, g, b, a = img.split()
                t = self.temp_val / 100.0
                if t > 0:  # Warm
                    r = r.point(lambda p: min(255, int(p * (1.0 + t * 0.25))))
                    b = b.point(lambda p: max(0, int(p * (1.0 - t * 0.25))))
                else:      # Cool
                    abs_t = abs(t)
                    b = b.point(lambda p: min(255, int(p * (1.0 + abs_t * 0.25))))
                    r = r.point(lambda p: max(0, int(p * (1.0 - abs_t * 0.25))))
                img = Image.merge("RGBA", (r, g, b, a))

            # 4. Blur Filter
            if self.blur_val > 0:
                img = img.filter(ImageFilter.GaussianBlur(radius=self.blur_val))

            # Smart Compression based on Alpha Channel (Reduces size from 19MB -> 1.5MB)
            buf = io.BytesIO()
            has_alpha = False
            if img.mode == "RGBA":
                extrema = img.split()[-1].getextrema()
                if extrema != (255, 255):  # Contains transparent pixels
                    has_alpha = True

            if has_alpha:
                img.save(buf, format="PNG", compress_level=9, optimize=True)
                self.processed_mime_type = "image/png"
            else:
                rgb_img = img.convert("RGB")
                rgb_img.save(buf, format="JPEG", quality=90, optimize=True)
                self.processed_mime_type = "image/jpeg"

            self.processed_file_data = buf.getvalue()

            new_pixmap = QPixmap()
            new_pixmap.loadFromData(self.processed_file_data)
            self.pixmap = new_pixmap
            self.update()
            self.changed.emit()
        except Exception:
            pass

    def reset_image_adjustments(self):
        self.blur_val = 0
        self.brightness_val = 0
        self.contrast_val = 0
        self.temp_val = 0
        self.processed_file_data = self.file_data
        self.processed_mime_type = None
        self.pixmap = self.original_pixmap
        self.update()
        self.changed.emit()

    def apply_effect(self, effect_type=None, radius=None):
        if effect_type is not None:
            self.effect_type = effect_type
        if radius is not None:
            self.effect_radius = radius

        if self.effect_type == "shadow":
            if not self.shadow_effect:
                self.shadow_effect = QGraphicsDropShadowEffect()
            self.shadow_effect.setColor(QColor(0, 0, 0, 190))
            self.shadow_effect.setBlurRadius(self.effect_radius)
            self.shadow_effect.setOffset(3, 3)
            self.setGraphicsEffect(self.shadow_effect)
        elif self.effect_type == "glow":
            if not self.shadow_effect:
                self.shadow_effect = QGraphicsDropShadowEffect()
            self.shadow_effect.setColor(QColor(0, 210, 255, 220))
            self.shadow_effect.setBlurRadius(self.effect_radius)
            self.shadow_effect.setOffset(0, 0)
            self.setGraphicsEffect(self.shadow_effect)
        else:
            self.setGraphicsEffect(None)
            
        self.update()
        self.changed.emit()

    def boundingRect(self):
        # Pad bounding box to make space for handles and prevent rendering artifacts
        return self.rect.adjusted(-10, -10, 10, 10)

    def paint(self, painter, option, widget):
        # Draw the main image scaled to target rect
        painter.drawPixmap(self.rect.toRect(), self.pixmap)
        
        # Overlay selections outline and resize handles when selected
        if self.isSelected():
            # Draw dash border
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 120, 215), 1.5, Qt.PenStyle.DashLine))
            painter.drawRect(self.rect)
            
            # Draw 8 resize handles
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.setPen(QPen(QColor(0, 120, 215), 1))
            handles = self.get_handle_rects()
            for handle_rect in handles.values():
                painter.drawRect(handle_rect)

    def get_handle_rects(self):
        """Returns bounding rectangles of the 8 resize handles in local space."""
        r = self.rect
        w, h = 8, 8
        half = w / 2
        return {
            'tl': QRectF(r.left() - half, r.top() - half, w, h),
            'tm': QRectF(r.center().x() - half, r.top() - half, w, h),
            'tr': QRectF(r.right() - half, r.top() - half, w, h),
            'mr': QRectF(r.right() - half, r.center().y() - half, w, h),
            'br': QRectF(r.right() - half, r.bottom() - half, w, h),
            'bm': QRectF(r.center().x() - half, r.bottom() - half, w, h),
            'bl': QRectF(r.left() - half, r.bottom() - half, w, h),
            'ml': QRectF(r.left() - half, r.center().y() - half, w, h),
        }

    def clear_cache(self):
        self._pil_base_image = None

    def mousePressEvent(self, event):
        pos = event.pos()
        handles = self.get_handle_rects()
        for key, rect in handles.items():
            if rect.contains(pos):
                self.active_handle = key
                self.start_pos = event.scenePos()
                self.start_rect = QRectF(self.rect)
                self.start_scene_pos = self.scenePos()
                self.start_aspect_ratio = self.start_rect.width() / max(0.001, self.start_rect.height())
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.active_handle:
            delta = event.scenePos() - self.start_pos
            min_size = 10.0
            
            dx = delta.x()
            dy = delta.y()
            
            is_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            keep_aspect = self.keep_aspect_ratio or is_shift
            aspect = self.start_aspect_ratio if self.start_aspect_ratio > 0 else 1.0
            handle = self.active_handle
            
            if keep_aspect:
                if handle in ('br', 'bl', 'tr', 'tl'):
                    if handle == 'br':
                        w_cand = max(min_size, self.start_rect.width() + dx)
                        h_cand = w_cand / aspect
                        if h_cand < min_size:
                            h_cand = min_size
                            w_cand = h_cand * aspect
                        new_w, new_h = w_cand, h_cand
                        off_x, off_y = 0.0, 0.0
                    elif handle == 'bl':
                        w_cand = max(min_size, self.start_rect.width() - dx)
                        h_cand = w_cand / aspect
                        if h_cand < min_size:
                            h_cand = min_size
                            w_cand = h_cand * aspect
                        new_w, new_h = w_cand, h_cand
                        off_x = self.start_rect.width() - new_w
                        off_y = 0.0
                    elif handle == 'tr':
                        w_cand = max(min_size, self.start_rect.width() + dx)
                        h_cand = w_cand / aspect
                        if h_cand < min_size:
                            h_cand = min_size
                            w_cand = h_cand * aspect
                        new_w, new_h = w_cand, h_cand
                        off_x = 0.0
                        off_y = self.start_rect.height() - new_h
                    elif handle == 'tl':
                        w_cand = max(min_size, self.start_rect.width() - dx)
                        h_cand = w_cand / aspect
                        if h_cand < min_size:
                            h_cand = min_size
                            w_cand = h_cand * aspect
                        new_w, new_h = w_cand, h_cand
                        off_x = self.start_rect.width() - new_w
                        off_y = self.start_rect.height() - new_h
                else:
                    if handle in ('tm', 'bm'):
                        h_cand = max(min_size, self.start_rect.height() + (dy if handle == 'bm' else -dy))
                        w_cand = h_cand * aspect
                        new_w, new_h = w_cand, h_cand
                        off_x = (self.start_rect.width() - new_w) / 2.0
                        off_y = (self.start_rect.height() - new_h) if handle == 'tm' else 0.0
                    else:  # 'ml', 'mr'
                        w_cand = max(min_size, self.start_rect.width() + (dx if handle == 'mr' else -dx))
                        h_cand = w_cand / aspect
                        new_w, new_h = w_cand, h_cand
                        off_x = (self.start_rect.width() - new_w) if handle == 'ml' else 0.0
                        off_y = (self.start_rect.height() - new_h) / 2.0
            else:
                new_w = self.start_rect.width()
                new_h = self.start_rect.height()
                off_x, off_y = 0.0, 0.0
                
                if 't' in handle:
                    proposed_h = self.start_rect.height() - dy
                    if proposed_h >= min_size:
                        new_h = proposed_h
                        off_y = dy
                if 'b' in handle:
                    proposed_h = self.start_rect.height() + dy
                    if proposed_h >= min_size:
                        new_h = proposed_h
                if 'l' in handle:
                    proposed_w = self.start_rect.width() - dx
                    if proposed_w >= min_size:
                        new_w = proposed_w
                        off_x = dx
                if 'r' in handle:
                    proposed_w = self.start_rect.width() + dx
                    if proposed_w >= min_size:
                        new_w = proposed_w
                        
            self.prepareGeometryChange()
            self.rect = QRectF(0, 0, new_w, new_h)
            self.setPos(self.start_scene_pos.x() + off_x, self.start_scene_pos.y() + off_y)
            self.update()
            self.changed.emit()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.active_handle:
            self.active_handle = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def hoverMoveEvent(self, event):
        pos = event.pos()
        handles = self.get_handle_rects()
        for key, rect in handles.items():
            if rect.contains(pos):
                # Set corresponding resize cursor shape
                if key in ('tl', 'br'):
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif key in ('tr', 'bl'):
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                elif key in ('tm', 'bm'):
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                elif key in ('ml', 'mr'):
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                event.accept()
                return
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange or change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.changed.emit()
        return super().itemChange(change, value)


class EditorCanvas(QGraphicsScene):
    # Signals for selections changed
    selection_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QBrush(QColor(240, 240, 240)))
        self.selectionChanged.connect(self.on_selection_changed)
        
        self.canvas_width = 1920
        self.canvas_height = 1080
        self.canvas_rect_item = None
        self.update_canvas_boundary()

    def update_canvas_boundary(self):
        """Draws the visual bounding border of the active canvas size."""
        if self.canvas_rect_item:
            self.removeItem(self.canvas_rect_item)
            
        self.setSceneRect(-50, -50, self.canvas_width + 100, self.canvas_height + 100)
        
        # Add white canvas rect with a subtle shadow/outline
        self.canvas_rect_item = self.addRect(
            0, 0, self.canvas_width, self.canvas_height,
            QPen(QColor(180, 180, 180), 1),
            QBrush(QColor(255, 255, 255))
        )
        self.canvas_rect_item.setZValue(-9999) # Always keep canvas background at the very bottom

        if hasattr(self, 'guideline_item') and self.guideline_item:
            self.removeItem(self.guideline_item)

        # Draw Cyan Dash Guideline for actual Output boundary overlay
        self.guideline_item = self.addRect(
            0, 0, self.canvas_width, self.canvas_height,
            QPen(QColor(0, 210, 255, 220), 2, Qt.PenStyle.DashLine),
            QBrush(Qt.BrushStyle.NoBrush)
        )
        self.guideline_item.setZValue(9999) # Top-most guideline layer
        self.guideline_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    def set_canvas_size(self, width, height):
        self.canvas_width = width
        self.canvas_height = height
        self.update_canvas_boundary()
        
        # Resize background layer if it exists
        for item in self.items():
            if isinstance(item, ImageLayerItem) and item.is_background:
                item.prepareGeometryChange()
                item.rect = QRectF(0, 0, width, height)
                item.update()
                item.changed.emit()

    def on_selection_changed(self):
        self.selection_updated.emit()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            selected_items = [item for item in self.selectedItems() if isinstance(item, ImageLayerItem)]
            if selected_items:
                step = 10 if bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1
                dx, dy = 0, 0
                if key == Qt.Key.Key_Left:
                    dx = -step
                elif key == Qt.Key.Key_Right:
                    dx = step
                elif key == Qt.Key.Key_Up:
                    dy = -step
                elif key == Qt.Key.Key_Down:
                    dy = step
                
                for item in selected_items:
                    item.setPos(item.x() + dx, item.y() + dy)
                    item.changed.emit()
                event.accept()
                return
        super().keyPressEvent(event)
