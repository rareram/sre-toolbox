import sys
import os
import base64
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QPixmap, QIcon, QImage, QColor, QPainter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QSpinBox, QListWidget,
    QListWidgetItem, QGraphicsView, QFileDialog, QFrame, QAbstractItemView,
    QMessageBox, QGroupBox, QRadioButton, QToolTip, QCheckBox, QSlider
)

from editor import EditorCanvas, ImageLayerItem
from exporter import export_to_svg

class CustomGraphicsView(QGraphicsView):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            scene = self.scene()
            if scene:
                scene.keyPressEvent(event)
                if event.isAccepted():
                    return
        super().keyPressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SVG Converter")
        #self.setWindowIcon(QIcon("icon.png"))
        self.resize(1200, 800)
        
        # Apply premium dark theme styling via QSS
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e24;
            }
            QWidget {
                color: #e2e2e7;
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 13px;
            }
            QFrame#panel {
                background-color: #121216;
                border: 1px solid #2d2d34;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #0078d7;
                border: none;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                background-color: #0086f0;
            }
            QPushButton:pressed {
                background-color: #006bbd;
            }
            QPushButton#secondary_btn {
                background-color: #2d2d34;
                color: #e2e2e7;
                border: 1px solid #3e3e46;
            }
            QPushButton#secondary_btn:hover {
                background-color: #3e3e46;
            }
            QPushButton#danger_btn {
                background-color: #a82020;
                color: white;
            }
            QPushButton#danger_btn:hover {
                background-color: #c92a2a;
            }
            QLabel {
                font-weight: 500;
            }
            QLabel#title {
                font-size: 18px;
                font-weight: bold;
                color: white;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #25252b;
                border: 1px solid #3e3e46;
                border-radius: 4px;
                padding: 4px;
                color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QListWidget {
                background-color: #121216;
                border: 1px solid #2d2d34;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                background-color: #1a1a20;
                border: 1px solid #25252b;
                border-radius: 4px;
                margin: 2px 0px;
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                border-color: #0086f0;
                color: white;
            }
            QGraphicsView {
                background-color: #1a1a20;
                border: 1px solid #2d2d34;
                border-radius: 8px;
            }
        """)

        self.selected_graphics_item = None
        self.block_property_updates = False
        
        # Debounce timer for smooth slider filtering
        self.adj_timer = QTimer(self)
        self.adj_timer.setSingleShot(True)
        self.adj_timer.timeout.connect(self._do_apply_adjustments)
        
        self.setup_ui()

    def setup_ui(self):
        # Main central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header Toolbar
        header_layout = QHBoxLayout()
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        
        header_title = QLabel("SVG Converter")
        header_title.setObjectName("title")
        header_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        
        header_subtitle = QLabel("Grafana Login Background Generator")
        header_subtitle.setStyleSheet("font-size: 12px; color: #00d2ff; font-weight: 500;")
        
        title_box.addWidget(header_title)
        title_box.addWidget(header_subtitle)
        
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        self.export_btn = QPushButton("SVG 파일 변환 저장")
        self.export_btn.clicked.connect(self.on_export_clicked)
        header_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(header_layout)
        
        # 3-Pane Body Layout
        body_layout = QHBoxLayout()
        
        # Left Panel (Controls and Layers)
        left_panel = QFrame()
        left_panel.setObjectName("panel")
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Resolution Setting Group
        res_group = QGroupBox("캔버스 해상도")
        res_layout = QVBoxLayout(res_group)
        self.res_combo = QComboBox()
        self.res_combo.addItems([
            "FHD (1920x1080) *Grafana 권장",
            "2K (2560x1440)",
            "4K (3840x2160)",
            "사용자 지정 (Custom)"
        ])
        self.res_combo.currentIndexChanged.connect(self.on_resolution_changed)
        res_layout.addWidget(self.res_combo)
        
        # Custom Resolution inputs
        custom_res_layout = QHBoxLayout()
        self.custom_w = QSpinBox()
        self.custom_w.setRange(100, 10000)
        self.custom_w.setValue(1920)
        self.custom_w.setEnabled(False)
        self.custom_w.valueChanged.connect(self.on_custom_res_edited)
        
        self.custom_h = QSpinBox()
        self.custom_h.setRange(100, 10000)
        self.custom_h.setValue(1080)
        self.custom_h.setEnabled(False)
        self.custom_h.valueChanged.connect(self.on_custom_res_edited)
        
        custom_res_layout.addWidget(QLabel("W:"))
        custom_res_layout.addWidget(self.custom_w)
        custom_res_layout.addWidget(QLabel("H:"))
        custom_res_layout.addWidget(self.custom_h)
        res_layout.addLayout(custom_res_layout)
        
        self.recommend_lbl = QLabel("💡 Grafana 로그인 배경사이즈는은 FHD 권장")
        self.recommend_lbl.setWordWrap(True)
        self.recommend_lbl.setToolTip("Grafana 로그인 화면 제작 시 표준 FHD(1920x1080) 해상도가 가장 잘 맞습니다.")
        self.recommend_lbl.setStyleSheet("color: #00d2ff; font-size: 11px; margin-top: 4px;")
        res_layout.addWidget(self.recommend_lbl)
        
        left_layout.addWidget(res_group)
        
        # Add Layer Group
        layer_btn_group = QGroupBox("레이어 추가")
        layer_btn_layout = QVBoxLayout(layer_btn_group)
        self.set_bg_btn = QPushButton("배경 이미지 설정")
        self.set_bg_btn.setObjectName("secondary_btn")
        self.set_bg_btn.clicked.connect(self.on_set_background_clicked)
        
        self.add_overlay_btn = QPushButton("오버레이 이미지 추가")
        self.add_overlay_btn.setObjectName("secondary_btn")
        self.add_overlay_btn.clicked.connect(self.on_add_overlay_clicked)
        
        layer_btn_layout.addWidget(self.set_bg_btn)
        layer_btn_layout.addWidget(self.add_overlay_btn)
        left_layout.addWidget(layer_btn_group)
        
        # Background Reset Group
        bg_reset_group = QGroupBox("배경 배치 초기화")
        bg_reset_layout = QVBoxLayout(bg_reset_group)
        
        self.reset_bg_fit_btn = QPushButton("캔버스 꽉 맞춤 리셋")
        self.reset_bg_fit_btn.setObjectName("secondary_btn")
        self.reset_bg_fit_btn.clicked.connect(self.reset_background_fit)
        
        self.reset_bg_aspect_btn = QPushButton("원본비율 중앙 정렬 리셋")
        self.reset_bg_aspect_btn.setObjectName("secondary_btn")
        self.reset_bg_aspect_btn.clicked.connect(self.reset_background_aspect_center)
        
        bg_reset_layout.addWidget(self.reset_bg_fit_btn)
        bg_reset_layout.addWidget(self.reset_bg_aspect_btn)
        left_layout.addWidget(bg_reset_group)
        
        # Layer List Group
        layer_list_group = QGroupBox("레이어 목록 (Z-Index)")
        layer_list_layout = QVBoxLayout(layer_list_group)
        
        self.layer_list = QListWidget()
        self.layer_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.layer_list.model().rowsMoved.connect(self.on_layers_reordered)
        self.layer_list.itemSelectionChanged.connect(self.on_list_selection_changed)
        layer_list_layout.addWidget(self.layer_list)
        
        self.delete_layer_btn = QPushButton("선택 레이어 삭제")
        self.delete_layer_btn.setObjectName("danger_btn")
        self.delete_layer_btn.clicked.connect(self.on_delete_layer_clicked)
        layer_list_layout.addWidget(self.delete_layer_btn)
        
        left_layout.addWidget(layer_list_group)
        
        # Center Canvas Panel
        self.canvas = EditorCanvas()
        self.canvas.selection_updated.connect(self.on_scene_selection_changed)
        
        self.view = CustomGraphicsView(self.canvas)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Fit View button on top of canvas
        canvas_container = QWidget()
        canvas_container_layout = QVBoxLayout(canvas_container)
        canvas_container_layout.setContentsMargins(0, 0, 0, 0)
        
        canvas_toolbar = QHBoxLayout()
        self.fit_btn = QPushButton("화면에 맞추기 (Fit View)")
        self.fit_btn.setObjectName("secondary_btn")
        self.fit_btn.clicked.connect(self.fit_view)
        canvas_toolbar.addWidget(self.fit_btn)
        canvas_toolbar.addStretch()
        
        canvas_container_layout.addLayout(canvas_toolbar)
        canvas_container_layout.addWidget(self.view)
        
        # Right Panel (Properties and Formatting)
        right_panel = QFrame()
        right_panel.setObjectName("panel")
        right_panel.setFixedWidth(280)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Position and Size properties
        prop_group = QGroupBox("레이어 속성")
        prop_layout = QGridLayout(prop_group)
        
        self.prop_x = QSpinBox()
        self.prop_x.setRange(-5000, 5000)
        self.prop_x.valueChanged.connect(self.on_property_edited)
        
        self.prop_y = QSpinBox()
        self.prop_y.setRange(-5000, 5000)
        self.prop_y.valueChanged.connect(self.on_property_edited)
        
        self.prop_w = QSpinBox()
        self.prop_w.setRange(1, 10000)
        self.prop_w.valueChanged.connect(self.on_property_edited)
        
        self.prop_h = QSpinBox()
        self.prop_h.setRange(1, 10000)
        self.prop_h.valueChanged.connect(self.on_property_edited)
        
        prop_layout.addWidget(QLabel("X:"), 0, 0)
        prop_layout.addWidget(self.prop_x, 0, 1)
        prop_layout.addWidget(QLabel("Y:"), 0, 2)
        prop_layout.addWidget(self.prop_y, 0, 3)
        
        prop_layout.addWidget(QLabel("W:"), 1, 0)
        prop_layout.addWidget(self.prop_w, 1, 1)
        prop_layout.addWidget(QLabel("H:"), 1, 2)
        prop_layout.addWidget(self.prop_h, 1, 3)
        
        self.prop_keep_aspect = QCheckBox("비율 고정 (Keep Aspect)")
        self.prop_keep_aspect.setChecked(True)
        self.prop_keep_aspect.toggled.connect(self.on_keep_aspect_toggled)
        prop_layout.addWidget(self.prop_keep_aspect, 2, 0, 1, 4)
        
        # Visibility Effect (Shadow / Glow)
        prop_layout.addWidget(QLabel("효과:"), 3, 0)
        self.prop_effect_combo = QComboBox()
        self.prop_effect_combo.addItems(["없음 (None)", "그림자 (Shadow)", "네온 글로우 (Glow)"])
        self.prop_effect_combo.currentIndexChanged.connect(self.on_effect_edited)
        prop_layout.addWidget(self.prop_effect_combo, 3, 1, 1, 3)
        
        prop_layout.addWidget(QLabel("반경:"), 4, 0)
        self.prop_effect_slider = QSlider(Qt.Orientation.Horizontal)
        self.prop_effect_slider.setRange(5, 50)
        self.prop_effect_slider.setValue(15)
        self.prop_effect_slider.valueChanged.connect(self.on_effect_edited)
        prop_layout.addWidget(self.prop_effect_slider, 4, 1, 1, 3)
        
        right_layout.addWidget(prop_group)
        
        # Alignment helpers
        align_group = QGroupBox("캔버스 정렬")
        align_layout = QGridLayout(align_group)
        
        self.align_l_btn = QPushButton("좌측")
        self.align_l_btn.setObjectName("secondary_btn")
        self.align_l_btn.clicked.connect(lambda: self.align_item('left'))
        
        self.align_hc_btn = QPushButton("수평중앙")
        self.align_hc_btn.setObjectName("secondary_btn")
        self.align_hc_btn.clicked.connect(lambda: self.align_item('h_center'))
        
        self.align_r_btn = QPushButton("우측")
        self.align_r_btn.setObjectName("secondary_btn")
        self.align_r_btn.clicked.connect(lambda: self.align_item('right'))
        
        self.align_t_btn = QPushButton("상단")
        self.align_t_btn.setObjectName("secondary_btn")
        self.align_t_btn.clicked.connect(lambda: self.align_item('top'))
        
        self.align_vc_btn = QPushButton("수직중앙")
        self.align_vc_btn.setObjectName("secondary_btn")
        self.align_vc_btn.clicked.connect(lambda: self.align_item('v_center'))
        
        self.align_b_btn = QPushButton("하단")
        self.align_b_btn.setObjectName("secondary_btn")
        self.align_b_btn.clicked.connect(lambda: self.align_item('bottom'))
        
        align_layout.addWidget(self.align_l_btn, 0, 0)
        align_layout.addWidget(self.align_hc_btn, 0, 1)
        align_layout.addWidget(self.align_r_btn, 0, 2)
        
        align_layout.addWidget(self.align_t_btn, 1, 0)
        align_layout.addWidget(self.align_vc_btn, 1, 1)
        align_layout.addWidget(self.align_b_btn, 1, 2)
        
        right_layout.addWidget(align_group)
        
        # Image Adjustments Group (Blur, Brightness, Contrast, Temperature)
        adj_group = QGroupBox("이미지 보정 필터")
        adj_layout = QGridLayout(adj_group)
        
        # 1. Blur Slider
        adj_layout.addWidget(QLabel("블러:"), 0, 0)
        self.adj_blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.adj_blur_slider.setRange(0, 30)
        self.adj_blur_slider.setValue(0)
        self.adj_blur_slider.valueChanged.connect(self.on_adjustment_changed)
        adj_layout.addWidget(self.adj_blur_slider, 0, 1, 1, 3)
        
        # 2. Brightness Slider
        adj_layout.addWidget(QLabel("밝기:"), 1, 0)
        self.adj_bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.adj_bright_slider.setRange(-100, 100)
        self.adj_bright_slider.setValue(0)
        self.adj_bright_slider.valueChanged.connect(self.on_adjustment_changed)
        adj_layout.addWidget(self.adj_bright_slider, 1, 1, 1, 3)
        
        # 3. Contrast Slider
        adj_layout.addWidget(QLabel("명암:"), 2, 0)
        self.adj_contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.adj_contrast_slider.setRange(-100, 100)
        self.adj_contrast_slider.setValue(0)
        self.adj_contrast_slider.valueChanged.connect(self.on_adjustment_changed)
        adj_layout.addWidget(self.adj_contrast_slider, 2, 1, 1, 3)
        
        # 4. Temperature Slider
        adj_layout.addWidget(QLabel("색온도:"), 3, 0)
        self.adj_temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.adj_temp_slider.setRange(-100, 100)
        self.adj_temp_slider.setValue(0)
        self.adj_temp_slider.valueChanged.connect(self.on_adjustment_changed)
        adj_layout.addWidget(self.adj_temp_slider, 3, 1, 1, 3)
        
        # Reset Adjustments Button
        self.adj_reset_btn = QPushButton("보정 초기화")
        self.adj_reset_btn.setObjectName("secondary_btn")
        self.adj_reset_btn.clicked.connect(self.on_adjustment_reset)
        adj_layout.addWidget(self.adj_reset_btn, 4, 0, 1, 4)
        
        right_layout.addWidget(adj_group)
        
        # Conversion mode (Base64 vs Vectorizing disabled)
        conv_group = QGroupBox("SVG 변환 필터")
        conv_layout = QVBoxLayout(conv_group)
        
        self.base64_radio = QRadioButton("Base64 무손실 결합 (활성)")
        self.base64_radio.setChecked(True)
        
        self.vector_radio = QRadioButton("벡터라이징(트레이싱) (보류)")
        self.vector_radio.setEnabled(False)
        self.vector_radio.setToolTip("벡터화 엔진은 현재 준비 중입니다.")
        
        conv_layout.addWidget(self.base64_radio)
        conv_layout.addWidget(self.vector_radio)
        right_layout.addWidget(conv_group)
        
        # Quick Shortcuts Help Box
        help_group = QGroupBox("💡 단축 조작 팁")
        help_layout = QVBoxLayout(help_group)
        help_text = QLabel(
            "• <b>방향키</b>: 선택 레이어 1px 미세 이동<br>"
            "• <b>Shift + 방향키</b>: 10px 고속 이동<br>"
            "• <b>Shift + 드래그</b>: 비율 고정 리사이즈<br>"
            "• <b>W / H 입력</b>: 정밀 수치 직접 수정"
        )
        help_text.setStyleSheet("color: #a0a0b0; font-size: 12px; line-height: 150%;")
        help_layout.addWidget(help_text)
        right_layout.addWidget(help_group)
        
        right_layout.addStretch()
        
        # Assemble body layout
        body_layout.addWidget(left_panel)
        body_layout.addWidget(canvas_container, 1)
        body_layout.addWidget(right_panel)
        
        main_layout.addLayout(body_layout)
        
        # Bottom Guide / Info Bar
        guide_bar = QFrame()
        guide_bar.setObjectName("guide_bar")
        guide_bar.setStyleSheet("""
            QFrame#guide_bar {
                background-color: #16161a;
                border-top: 1px solid #2d2d38;
                border-radius: 4px;
            }
            QLabel {
                font-size: 12px;
                color: #b0b0c0;
            }
        """)
        guide_layout = QHBoxLayout(guide_bar)
        guide_layout.setContentsMargins(15, 8, 15, 8)
        guide_layout.setSpacing(25)
        
        tip1_lbl = QLabel("<b style='color:#00d2ff;'>💡 방향키</b> 1px 이동 &nbsp;|&nbsp; <b style='color:#00d2ff;'>Shift + 방향키</b> 10px 고속 이동")
        tip2_lbl = QLabel("<b style='color:#00d2ff;'>📐 Shift + 드래그</b> 비율 고정 리사이즈")
        tip3_lbl = QLabel("<b style='color:#00d2ff;'>🖱️ 마우스</b> 배치 & 핸들 크기 조절")
        
        guide_layout.addWidget(tip1_lbl)
        guide_layout.addWidget(tip2_lbl)
        guide_layout.addWidget(tip3_lbl)
        guide_layout.addStretch()
        
        main_layout.addWidget(guide_bar)
        
        # Default state
        self.show_properties(None)
        
        # Single shot timer to fit the view once UI is rendered
        QTimer.singleShot(100, self.fit_view)

    # Resolution combo changes
    def on_resolution_changed(self, index):
        if index == 0:   # FHD
            w, h = 1920, 1080
            self.custom_w.setEnabled(False)
            self.custom_h.setEnabled(False)
            self.recommend_lbl.setVisible(True)
        elif index == 1: # 2K
            w, h = 2560, 1440
            self.custom_w.setEnabled(False)
            self.custom_h.setEnabled(False)
            self.recommend_lbl.setVisible(False)
        elif index == 2: # 4K
            w, h = 3840, 2160
            self.custom_w.setEnabled(False)
            self.custom_h.setEnabled(False)
            self.recommend_lbl.setVisible(False)
        else:            # Custom
            w = self.custom_w.value()
            h = self.custom_h.value()
            self.custom_w.setEnabled(True)
            self.custom_h.setEnabled(True)
            self.recommend_lbl.setVisible(False)
            
        self.canvas.set_canvas_size(w, h)
        self.fit_view()

    def on_custom_res_edited(self):
        w = self.custom_w.value()
        h = self.custom_h.value()
        self.canvas.set_canvas_size(w, h)

    def fit_view(self):
        """Autoscale graphics scene to fit within the editor view boundary."""
        self.view.fitInView(
            self.canvas.sceneRect().adjusted(20, 20, -20, -20),
            Qt.AspectRatioMode.KeepAspectRatio
        )

    # Background Loading
    def on_set_background_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "배경 이미지 선택", "",
            "이미지 파일 (*.png *.jpg *.jpeg *.svg *.webp)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
                
            pixmap = QPixmap()
            if not pixmap.loadFromData(file_data):
                QMessageBox.critical(self, "오류", "이미지를 불러올 수 없습니다.")
                return
                
            filename = os.path.basename(file_path)
            
            # Remove existing background layer if any
            for item in self.canvas.items():
                if isinstance(item, ImageLayerItem) and item.is_background:
                    self.canvas.removeItem(item)
                    self.remove_from_list(item)
                    
            # Create background item (Preserve aspect ratio & cover canvas centered)
            bg_item = ImageLayerItem(
                pixmap, filename, file_data, is_background=True
            )
            self.canvas.addItem(bg_item)
            
            pw = pixmap.width()
            ph = pixmap.height()
            cw = self.canvas.canvas_width
            ch = self.canvas.canvas_height
            
            ratio = pw / max(1.0, ph)
            w = cw
            h = w / ratio
            if h < ch:
                h = ch
                w = h * ratio
                
            x = (cw - w) / 2.0
            y = (ch - h) / 2.0
            
            bg_item.setPos(x, y)
            bg_item.prepareGeometryChange()
            bg_item.rect = QRectF(0, 0, w, h)
            bg_item.start_aspect_ratio = ratio
            bg_item.update()
            
            # Add to list widget as bottom layer
            list_item = QListWidgetItem(f"배경: {filename}")
            list_item.setData(Qt.ItemDataRole.UserRole, bg_item)
            
            # In our list, background should be placed at the very bottom
            self.layer_list.addItem(list_item)
            self.layer_list.setCurrentItem(list_item)
            self.update_layer_z_indices()
            self.show_properties(bg_item)
            
            bg_item.changed.connect(self.update_properties_from_item)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"배경을 설정하는 도중 오류가 발생했습니다: {str(e)}")

    # Overlay Loading
    def on_add_overlay_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "오버레이 이미지 추가", "",
            "이미지 파일 (*.png *.jpg *.jpeg *.svg *.webp)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
                
            pixmap = QPixmap()
            if not pixmap.loadFromData(file_data):
                QMessageBox.critical(self, "오류", "이미지를 불러올 수 없습니다.")
                return
                
            filename = os.path.basename(file_path)
            
            # Create resizable overlay item
            item = ImageLayerItem(
                pixmap, filename, file_data, is_background=False
            )
            self.canvas.addItem(item)
            
            # Position at center of canvas
            cx = (self.canvas.canvas_width - pixmap.width()) / 2
            cy = (self.canvas.canvas_height - pixmap.height()) / 2
            item.setPos(max(0, cx), max(0, cy))
            
            # Add to list widget as top layer (index 0)
            list_item = QListWidgetItem(f"레이어: {filename}")
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.layer_list.insertItem(0, list_item)
            self.layer_list.setCurrentItem(list_item)
            
            self.update_layer_z_indices()
            
            item.changed.connect(self.update_properties_from_item)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"레이어를 추가하는 도중 오류가 발생했습니다: {str(e)}")

    def on_delete_layer_clicked(self):
        selected_list_items = self.layer_list.selectedItems()
        if not selected_list_items:
            return
            
        list_item = selected_list_items[0]
        graphics_item = list_item.data(Qt.ItemDataRole.UserRole)
        
        # Remove from canvas
        self.canvas.removeItem(graphics_item)
        # Remove from list widget
        self.layer_list.takeItem(self.layer_list.row(list_item))
        
        self.update_layer_z_indices()
        
        # Automatically select the top-most remaining layer if any
        if self.layer_list.count() > 0:
            self.layer_list.setCurrentRow(0)
        else:
            self.show_properties(None)

    def remove_from_list(self, graphics_item):
        for row in range(self.layer_list.count()):
            item = self.layer_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == graphics_item:
                self.layer_list.takeItem(row)
                break

    def update_layer_z_indices(self):
        # Photoshop/Figma layers list order (Top-most item is index 0)
        # Z-value of item should decrease as index increases.
        count = self.layer_list.count()
        for row in range(count):
            item = self.layer_list.item(row)
            graphics_item = item.data(Qt.ItemDataRole.UserRole)
            graphics_item.setZValue(count - 1 - row)

    def on_layers_reordered(self, parent, start, end, destination, row):
        # Slight delay to allow internal move in ListWidget to finalize
        QTimer.singleShot(50, self.update_layer_z_indices)

    # Selection changes
    def on_scene_selection_changed(self):
        self.layer_list.blockSignals(True)
        self.layer_list.clearSelection()
        
        selected_items = self.canvas.selectedItems()
        if selected_items:
            active_item = selected_items[0]
            for row in range(self.layer_list.count()):
                list_item = self.layer_list.item(row)
                if list_item.data(Qt.ItemDataRole.UserRole) == active_item:
                    list_item.setSelected(True)
                    break
            self.show_properties(active_item)
        else:
            self.show_properties(None)
            
        self.layer_list.blockSignals(False)

    def on_list_selection_changed(self):
        self.canvas.blockSignals(True)
        self.canvas.clearSelection()
        
        selected_list_items = self.layer_list.selectedItems()
        if selected_list_items:
            graphics_item = selected_list_items[0].data(Qt.ItemDataRole.UserRole)
            graphics_item.setSelected(True)
            self.show_properties(graphics_item)
        else:
            self.show_properties(None)
            
        self.canvas.blockSignals(False)

    # Properties panel syncing
    def show_properties(self, item):
        self.selected_graphics_item = item
        if not item:
            self.prop_x.setEnabled(False)
            self.prop_y.setEnabled(False)
            self.prop_w.setEnabled(False)
            self.prop_h.setEnabled(False)
            self.prop_keep_aspect.setEnabled(False)
            self.prop_effect_combo.setEnabled(False)
            self.prop_effect_slider.setEnabled(False)
            self.adj_blur_slider.setEnabled(False)
            self.adj_bright_slider.setEnabled(False)
            self.adj_contrast_slider.setEnabled(False)
            self.adj_temp_slider.setEnabled(False)
            self.adj_reset_btn.setEnabled(False)
            self.prop_x.setValue(0)
            self.prop_y.setValue(0)
            self.prop_w.setValue(0)
            self.prop_h.setValue(0)
            return
            
        self.block_property_updates = True
        
        # All layers (including background) can be manipulated
        self.prop_x.setEnabled(True)
        self.prop_y.setEnabled(True)
        self.prop_w.setEnabled(True)
        self.prop_h.setEnabled(True)
        self.prop_keep_aspect.setEnabled(True)
        self.prop_effect_combo.setEnabled(True)
        self.prop_effect_slider.setEnabled(True)
        
        self.prop_x.setValue(int(item.x()))
        self.prop_y.setValue(int(item.y()))
        self.prop_w.setValue(int(item.rect.width()))
        self.prop_h.setValue(int(item.rect.height()))
        
        self.prop_keep_aspect.blockSignals(True)
        self.prop_keep_aspect.setChecked(item.keep_aspect_ratio)
        self.prop_keep_aspect.blockSignals(False)
        
        self.prop_effect_combo.blockSignals(True)
        self.prop_effect_slider.blockSignals(True)
        
        if item.effect_type == "shadow":
            self.prop_effect_combo.setCurrentIndex(1)
        elif item.effect_type == "glow":
            self.prop_effect_combo.setCurrentIndex(2)
        else:
            self.prop_effect_combo.setCurrentIndex(0)
            
        self.prop_effect_slider.setValue(item.effect_radius)
        
        self.prop_effect_combo.blockSignals(False)
        self.prop_effect_slider.blockSignals(False)
        
        # All items (including background) can use image filter controls
        self.adj_blur_slider.setEnabled(True)
        self.adj_bright_slider.setEnabled(True)
        self.adj_contrast_slider.setEnabled(True)
        self.adj_temp_slider.setEnabled(True)
        self.adj_reset_btn.setEnabled(True)
        
        self.adj_blur_slider.blockSignals(True)
        self.adj_bright_slider.blockSignals(True)
        self.adj_contrast_slider.blockSignals(True)
        self.adj_temp_slider.blockSignals(True)
        
        self.adj_blur_slider.setValue(item.blur_val)
        self.adj_bright_slider.setValue(item.brightness_val)
        self.adj_contrast_slider.setValue(item.contrast_val)
        self.adj_temp_slider.setValue(item.temp_val)
        
        self.adj_blur_slider.blockSignals(False)
        self.adj_bright_slider.blockSignals(False)
        self.adj_contrast_slider.blockSignals(False)
        self.adj_temp_slider.blockSignals(False)
        
        self.block_property_updates = False

    def on_effect_edited(self):
        if not self.selected_graphics_item or self.block_property_updates:
            return
        idx = self.prop_effect_combo.currentIndex()
        eff_map = {0: "none", 1: "shadow", 2: "glow"}
        eff_type = eff_map.get(idx, "none")
        radius = self.prop_effect_slider.value()
        
        self.selected_graphics_item.apply_effect(eff_type, radius)

    def on_adjustment_changed(self):
        if not self.selected_graphics_item or self.block_property_updates:
            return
        self.adj_timer.start(50)

    def _do_apply_adjustments(self):
        if not self.selected_graphics_item:
            return
        blur = self.adj_blur_slider.value()
        bright = self.adj_bright_slider.value()
        contrast = self.adj_contrast_slider.value()
        temp = self.adj_temp_slider.value()
        
        self.selected_graphics_item.apply_image_adjustments(blur, bright, contrast, temp)

    def on_adjustment_reset(self):
        if not self.selected_graphics_item:
            return
        self.selected_graphics_item.reset_image_adjustments()
        self.show_properties(self.selected_graphics_item)

    def update_properties_from_item(self):
        if self.selected_graphics_item:
            self.show_properties(self.selected_graphics_item)

    def on_keep_aspect_toggled(self, checked):
        if self.selected_graphics_item and not self.block_property_updates:
            self.selected_graphics_item.keep_aspect_ratio = checked

    def on_property_edited(self):
        if not self.selected_graphics_item or self.block_property_updates:
            return
            
        self.selected_graphics_item.changed.disconnect(self.update_properties_from_item)
        
        sender = self.sender()
        x = self.prop_x.value()
        y = self.prop_y.value()
        w = self.prop_w.value()
        h = self.prop_h.value()
        
        if self.selected_graphics_item.keep_aspect_ratio and self.selected_graphics_item.start_aspect_ratio > 0:
            aspect = self.selected_graphics_item.start_aspect_ratio
            if sender == self.prop_w:
                h = max(1, int(round(w / aspect)))
                self.prop_h.blockSignals(True)
                self.prop_h.setValue(h)
                self.prop_h.blockSignals(False)
            elif sender == self.prop_h:
                w = max(1, int(round(h * aspect)))
                self.prop_w.blockSignals(True)
                self.prop_w.setValue(w)
                self.prop_w.blockSignals(False)
        
        self.selected_graphics_item.setPos(x, y)
        self.selected_graphics_item.prepareGeometryChange()
        self.selected_graphics_item.rect = QRectF(0, 0, w, h)
        self.selected_graphics_item.update()
        
        self.selected_graphics_item.changed.connect(self.update_properties_from_item)

    # Alignments
    def align_item(self, direction):
        item = self.selected_graphics_item
        if not item or item.is_background:
            return
            
        cw = self.canvas.canvas_width
        ch = self.canvas.canvas_height
        iw = item.rect.width()
        ih = item.rect.height()
        
        x = item.x()
        y = item.y()
        
        if direction == 'left':
            x = 0
        elif direction == 'h_center':
            x = (cw - iw) / 2
        elif direction == 'right':
            x = cw - iw
        elif direction == 'top':
            y = 0
        elif direction == 'v_center':
            y = (ch - ih) / 2
        elif direction == 'bottom':
            y = ch - ih
            
        item.setPos(x, y)
        self.show_properties(item)

    def reset_background_fit(self):
        for item in self.canvas.items():
            if isinstance(item, ImageLayerItem) and item.is_background:
                cw = self.canvas.canvas_width
                ch = self.canvas.canvas_height
                item.setPos(0, 0)
                item.prepareGeometryChange()
                item.rect = QRectF(0, 0, cw, ch)
                if item.rect.height() > 0:
                    item.start_aspect_ratio = item.rect.width() / item.rect.height()
                item.update()
                item.changed.emit()
                self.show_properties(item)
                break

    def reset_background_aspect_center(self):
        for item in self.canvas.items():
            if isinstance(item, ImageLayerItem) and item.is_background:
                pw = item.pixmap.width()
                ph = item.pixmap.height()
                cw = self.canvas.canvas_width
                ch = self.canvas.canvas_height
                
                ratio = pw / max(1.0, ph)
                w = cw
                h = w / ratio
                if h < ch:
                    h = ch
                    w = h * ratio
                
                x = (cw - w) / 2.0
                y = (ch - h) / 2.0
                
                item.setPos(x, y)
                item.prepareGeometryChange()
                item.rect = QRectF(0, 0, w, h)
                item.start_aspect_ratio = ratio
                item.update()
                item.changed.emit()
                self.show_properties(item)
                break

    # Exporting
    def on_export_clicked(self):
        # We need at least one layer to export
        if self.layer_list.count() == 0:
            QMessageBox.warning(self, "경고", "캔버스에 내보낼 이미지 레이어가 없습니다.")
            return
            
        output_path, _ = QFileDialog.getSaveFileName(
            self, "SVG 저장", "g8_login_dark.svg", "SVG 파일 (*.svg)"
        )
        if not output_path:
            return
            
        try:
            # Gather all graphics items sorted by Z-index (bottom to top)
            # Higher Z-index items should be drawn LAST in SVG so they appear on top.
            # Z-values are set based on list index in update_layer_z_indices (Z = count - 1 - row).
            # So bottom layer (background) has lowest Z, top overlay has highest Z.
            items = []
            for row in range(self.layer_list.count()):
                list_item = self.layer_list.item(row)
                graphics_item = list_item.data(Qt.ItemDataRole.UserRole)
                items.append(graphics_item)
                
            # Reverse order of layers list so that lowest Z item is exported first
            items.reverse()
            
            export_to_svg(
                self.canvas.canvas_width,
                self.canvas.canvas_height,
                items,
                output_path
            )
            QMessageBox.information(
                self, "성공",
                f"성공적으로 SVG 파일로 변환 저장되었습니다:\n{output_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"SVG 저장 실패: {str(e)}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Refit canvas to view when window size changes
        QTimer.singleShot(100, self.fit_view)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            focused_widget = QApplication.focusWidget()
            if not isinstance(focused_widget, QSpinBox):
                if hasattr(self, 'canvas') and self.canvas:
                    self.canvas.keyPressEvent(event)
                    if event.isAccepted():
                        return
        super().keyPressEvent(event)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
