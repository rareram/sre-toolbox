from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPen, QColor, QBrush, QCursor
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsScene

class ImageLayerItem(QGraphicsObject):
    # Signal emitted when position or size of this layer changes
    changed = Signal()

    def __init__(self, pixmap, filename, file_data, is_background=False, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.filename = filename
        self.file_data = file_data
        self.is_background = is_background
        
        self.rect = QRectF(0, 0, pixmap.width(), pixmap.height())
        self.active_handle = None
        self.start_pos = None
        self.start_rect = None
        self.start_scene_pos = None
        
        # Configure flags based on whether it is a background or an overlay
        if is_background:
            self.setFlags(
                QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
            )
        else:
            self.setFlags(
                QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
            )
            self.setAcceptHoverEvents(True)

    def boundingRect(self):
        # Pad bounding box to make space for handles and prevent rendering artifacts
        if self.is_background:
            return self.rect
        return self.rect.adjusted(-10, -10, 10, 10)

    def paint(self, painter, option, widget):
        # Draw the main image scaled to target rect
        painter.drawPixmap(self.rect.toRect(), self.pixmap)
        
        # Overlay selections outline and resize handles for non-background layers
        if self.isSelected() and not self.is_background:
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

    def mousePressEvent(self, event):
        if not self.is_background:
            pos = event.pos()
            handles = self.get_handle_rects()
            for key, rect in handles.items():
                if rect.contains(pos):
                    self.active_handle = key
                    self.start_pos = event.scenePos()
                    self.start_rect = QRectF(self.rect)
                    self.start_scene_pos = self.scenePos()
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.active_handle:
            delta = event.scenePos() - self.start_pos
            min_size = 10
            
            new_w = self.start_rect.width()
            new_h = self.start_rect.height()
            off_x = 0.0
            off_y = 0.0
            
            dx = delta.x()
            dy = delta.y()
            
            # Handle height adjustments
            if 't' in self.active_handle:
                proposed_h = self.start_rect.height() - dy
                if proposed_h >= min_size:
                    new_h = proposed_h
                    off_y = dy
            if 'b' in self.active_handle:
                proposed_h = self.start_rect.height() + dy
                if proposed_h >= min_size:
                    new_h = proposed_h
            
            # Handle width adjustments
            if 'l' in self.active_handle:
                proposed_w = self.start_rect.width() - dx
                if proposed_w >= min_size:
                    new_w = proposed_w
                    off_x = dx
            if 'r' in self.active_handle:
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
        if not self.is_background:
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
