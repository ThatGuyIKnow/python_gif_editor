import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QFileDialog,
    QLabel, QFormLayout, QSpinBox, QDoubleSpinBox, QHBoxLayout
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl, QPoint, QSize, pyqtSignal
from PyQt5.QtGui import QMovie, QTransform, QPixmap, QPainter, QPen, QColor
import math

class DraggableWidget(QWidget):
    selected = pyqtSignal(object)
    def __init__(self, child_widget, is_gif=False, is_image=False, parent=None, image_pixmap=None, source_path=None):
        super().__init__(parent)
        self.child_widget = child_widget
        self.is_gif = is_gif
        self.is_image = is_image
        self._rotation = 0.0
        self._current_width = child_widget.sizeHint().width()
        self._current_height = child_widget.sizeHint().height()
        self.selected_flag = False
        self.source_path = source_path
        layout = QVBoxLayout(self)
        layout.addWidget(self.child_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self._drag_active = False
        self._drag_offset = QPoint()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._image_pixmap = image_pixmap if is_image else None
        if self.is_gif:
            self._original_movie = None
            self._connect_gif_frame_updater()
            self._label = self.child_widget
            self._last_rotated = None
        if self.is_image:
            self._label = self.child_widget
            self._update_image_frame()
    def _connect_gif_frame_updater(self):
        if isinstance(self.child_widget, QLabel) and self.child_widget.movie():
            self._original_movie = self.child_widget.movie()
            self._original_movie.frameChanged.connect(self._update_gif_frame)
    @staticmethod
    def _bounding_box_size(orig_w, orig_h, angle_deg):
        angle_rad = math.radians(angle_deg)
        cos_a = abs(math.cos(angle_rad))
        sin_a = abs(math.sin(angle_rad))
        new_w = orig_w * cos_a + orig_h * sin_a
        new_h = orig_w * sin_a + orig_h * cos_a
        return int(math.ceil(new_w)), int(math.ceil(new_h))
    def _update_gif_frame(self):
        frame = self._original_movie.currentPixmap()
        orig_w, orig_h = self._current_width, self._current_height
        angle = self._rotation
        if not frame.isNull():
            scaled_frame = frame.scaled(
                orig_w, orig_h,
                Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            if angle != 0:
                transform = QTransform().rotate(angle)
                rotated_pixmap = scaled_frame.transformed(
                    transform, Qt.SmoothTransformation)
                bbox_w, bbox_h = self._bounding_box_size(orig_w, orig_h, angle)
                self._label.setFixedSize(bbox_w, bbox_h)
                composed_pixmap = QPixmap(bbox_w, bbox_h)
                composed_pixmap.fill(Qt.transparent)
                p = QPainter(composed_pixmap)
                x = (bbox_w - rotated_pixmap.width()) // 2
                y = (bbox_h - rotated_pixmap.height()) // 2
                p.drawPixmap(x, y, rotated_pixmap)
                p.end()
                self._label.setPixmap(composed_pixmap)
                self.setFixedSize(bbox_w, bbox_h)
            else:
                self._label.setFixedSize(orig_w, orig_h)
                self._label.setPixmap(scaled_frame)
                self.setFixedSize(orig_w, orig_h)
    def _update_image_frame(self):
        if self._image_pixmap is None:
            return
        orig_w, orig_h = self._current_width, self._current_height
        angle = self._rotation
        scaled_frame = self._image_pixmap.scaled(
            orig_w, orig_h,
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        if angle != 0:
            transform = QTransform().rotate(angle)
            rotated_pixmap = scaled_frame.transformed(transform, Qt.SmoothTransformation)
            bbox_w, bbox_h = self._bounding_box_size(orig_w, orig_h, angle)
            self._label.setFixedSize(bbox_w, bbox_h)
            composed_pixmap = QPixmap(bbox_w, bbox_h)
            composed_pixmap.fill(Qt.transparent)
            p = QPainter(composed_pixmap)
            x = (bbox_w - rotated_pixmap.width()) // 2
            y = (bbox_h - rotated_pixmap.height()) // 2
            p.drawPixmap(x, y, rotated_pixmap)
            p.end()
            self._label.setPixmap(composed_pixmap)
            self.setFixedSize(bbox_w, bbox_h)
        else:
            self._label.setFixedSize(orig_w, orig_h)
            self._label.setPixmap(scaled_frame)
            self.setFixedSize(orig_w, orig_h)
    def set_new_size(self, width, height):
        self._current_width = width
        self._current_height = height
        if self.is_gif:
            self._update_gif_frame()
        elif self.is_image:
            self._update_image_frame()
        else:
            self.setFixedSize(QSize(width, height))
            self.child_widget.setFixedSize(QSize(width, height))
    def set_rotation(self, angle_degrees):
        self._rotation = angle_degrees
        if self.is_gif:
            self._update_gif_frame()
        elif self.is_image:
            self._update_image_frame()
    def set_selected(self, val):
        self.selected_flag = val
        self.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self)
            self._drag_active = True
            self._drag_offset = event.pos()
            event.accept()
        else:
            event.ignore()
    def mouseMoveEvent(self, event):
        if self._drag_active:
            new_pos = self.parent().mapFromGlobal(self.mapToGlobal(event.pos() - self._drag_offset))
            new_x = min(max(0, new_pos.x()), self.parent().width() - self.width())
            new_y = min(max(0, new_pos.y()), self.parent().height() - self.height())
            self.move(new_x, new_y)
            event.accept()
        else:
            event.ignore()
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = False
            event.accept()
        else:
            event.ignore()
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.selected_flag:
            painter = QPainter(self)
            pen = QPen(QColor(0, 120, 215), 4)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(2, 2, -2, -2))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Draggable Video & GIF Player (Multi)")
        self.setGeometry(100, 100, 900, 700)
        self.media_players = []
        self.draggable_widgets = []
        self.current_gif = None
        self.selected_widget = None
        self.controls = {}
        open_button = QPushButton("Open Video/GIF/Image")
        open_button.clicked.connect(self.open_media)
        self.up_button = QPushButton("Bring Forward")
        self.up_button.clicked.connect(self.bring_forward)
        self.down_button = QPushButton("Send Backward")
        self.down_button.clicked.connect(self.send_backward)
        self.export_button = QPushButton("Export Layout as JSON")
        self.export_button.clicked.connect(self.export_layout)
        self.info_label = QLabel(
            "Open multiple videos, gifs or images to play. Drag any around.\n"
            "Resize and rotate the selected one using controls below. Use the buttons to reorder layers."
        )
        self.info_label.setWordWrap(True)
        self.controls_layout = QFormLayout()
        self.add_controls_ui()
        button_bar = QHBoxLayout()
        button_bar.addWidget(self.up_button)
        button_bar.addWidget(self.down_button)
        button_bar.addWidget(self.export_button)
        layout = QVBoxLayout()
        layout.addWidget(open_button)
        layout.addWidget(self.info_label)
        layout.addLayout(button_bar)
        layout.addLayout(self.controls_layout)
        layout.addStretch(1)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
    def add_controls_ui(self):
        self.controls['width'] = QSpinBox()
        self.controls['width'].setRange(100, 1920)
        self.controls['width'].setValue(320)
        self.controls['width'].valueChanged.connect(self.apply_controls)
        self.controls['height'] = QSpinBox()
        self.controls['height'].setRange(100, 1080)
        self.controls['height'].setValue(240)
        self.controls['height'].valueChanged.connect(self.apply_controls)
        self.controls['rotation'] = QDoubleSpinBox()
        self.controls['rotation'].setRange(-180.0, 180.0)
        self.controls['rotation'].setSingleStep(1.0)
        self.controls['rotation'].setValue(0.0)
        self.controls['rotation'].valueChanged.connect(self.apply_controls)
        self.controls_layout.addRow("Width:", self.controls['width'])
        self.controls_layout.addRow("Height:", self.controls['height'])
        self.controls_layout.addRow("Rotation (deg):", self.controls['rotation'])
    def open_media(self):
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Open Video, GIF, or Image File", "",
                "Media Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.gif *.jpg *.jpeg *.png *.bmp *.tif *.tiff);;All Files (*)")
        if file_path:
            self.add_media(file_path)
    def is_gif_file(self, file_path):
        _, ext = os.path.splitext(file_path)
        return ext.strip().lower() == ".gif"
    def is_image_file(self, file_path):
        ext = os.path.splitext(file_path)[1].strip().lower()
        return ext in [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"]
    def add_media(self, file_path):
        w = self.controls['width'].value()
        h = self.controls['height'].value()
        angle = self.controls['rotation'].value()
        is_gif = self.is_gif_file(file_path)
        is_image = self.is_image_file(file_path)
        if is_gif:
            label = QLabel(self)
            label.setMinimumSize(100, 100)
            label.setAlignment(Qt.AlignCenter)
            movie = QMovie(file_path)
            label.setMovie(movie)
            movie.start()
            draggable = DraggableWidget(label, is_gif=True, parent=self, source_path=file_path)
        elif is_image:
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                return
            label = QLabel(self)
            label.setMinimumSize(100, 100)
            label.setAlignment(Qt.AlignCenter)
            draggable = DraggableWidget(label, is_gif=False, is_image=True, parent=self, image_pixmap=pixmap, source_path=file_path)
        else:
            video_widget = QVideoWidget(self)
            video_widget.setMinimumSize(100, 100)
            media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
            media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
            media_player.setVideoOutput(video_widget)
            media_player.play()
            draggable = DraggableWidget(video_widget, is_gif=False, parent=self, source_path=file_path)
            self.media_players.append(media_player)
        draggable.set_new_size(w, h)
        draggable.set_rotation(angle)
        draggable.move(50 + 20 * len(self.draggable_widgets), 100 + 20 * len(self.draggable_widgets))
        draggable.show()
        draggable.selected.connect(self.set_selected_widget)
        self.draggable_widgets.append(draggable)
        self.set_selected_widget(draggable)
    def set_selected_widget(self, widget):
        if self.selected_widget is not None:
            self.selected_widget.set_selected(False)
        self.selected_widget = widget
        if widget is not None:
            widget.set_selected(True)
            self.controls['width'].blockSignals(True)
            self.controls['height'].blockSignals(True)
            self.controls['rotation'].blockSignals(True)
            self.controls['width'].setValue(widget._current_width)
            self.controls['height'].setValue(widget._current_height)
            self.controls['rotation'].setValue(widget._rotation)
            self.controls['width'].blockSignals(False)
            self.controls['height'].blockSignals(False)
            self.controls['rotation'].blockSignals(False)
    def apply_controls(self):
        if not self.selected_widget:
            return
        w = self.controls['width'].value()
        h = self.controls['height'].value()
        angle = self.controls['rotation'].value()
        self.selected_widget.set_new_size(w, h)
        self.selected_widget.set_rotation(angle)
    def bring_forward(self):
        if self.selected_widget is None:
            return
        idx = self.draggable_widgets.index(self.selected_widget)
        if idx < len(self.draggable_widgets) - 1:
            self.draggable_widgets[idx], self.draggable_widgets[idx+1] = self.draggable_widgets[idx+1], self.draggable_widgets[idx]
            self.draggable_widgets[idx].raise_()
            self.draggable_widgets[idx+1].raise_()
            self.draggable_widgets[idx+1].raise_()
    def send_backward(self):
        if self.selected_widget is None:
            return
        idx = self.draggable_widgets.index(self.selected_widget)
        if idx > 0:
            self.draggable_widgets[idx], self.draggable_widgets[idx-1] = self.draggable_widgets[idx-1], self.draggable_widgets[idx]
            self.draggable_widgets[idx].raise_()
            self.draggable_widgets[idx-1].lower()
    def export_layout(self):
        export_data = []
        for order, widget in enumerate(self.draggable_widgets):
            entry = {
                "path": widget.source_path,
                "type": "gif" if widget.is_gif else ("image" if widget.is_image else "video"),
                "x": widget.x(),
                "y": widget.y(),
                "width": widget._current_width,
                "height": widget._current_height,
                "rotation_degrees": widget._rotation,
                "order": order
            }
            export_data.append(entry)
        file_dialog = QFileDialog(self)
        save_path, _ = file_dialog.getSaveFileName(self, "Export Layout JSON", "layout_export.json","JSON Files (*.json)")
        if save_path:
            with open(save_path, "w") as f:
                json.dump(export_data, f, indent=2)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
