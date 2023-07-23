import os
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QScrollArea, QGridLayout, QProgressBar
from PyQt5.QtGui import QPixmap, QMovie
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PIL import Image

class ImageProcessorThread(QThread):
    progress_changed = pyqtSignal(int)
    processing_finished = pyqtSignal()

    def __init__(self, selected_folder,  max_width, max_height, quality):
        super().__init__()
        self.selected_folder = selected_folder
        self.max_width = max_width
        self.max_height = max_height
        self.quality = quality
        self.image_previews = []

    def run(self):
        output_folder = os.path.join(self.selected_folder, "output")
        os.makedirs(output_folder, exist_ok=True)

        for filename in os.listdir(self.selected_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                image_path = os.path.join(self.selected_folder, filename)
                self.image_previews.append(image_path)

        total_images = len(self.image_previews)
        for index, image_path in enumerate(self.image_previews):
            image = Image.open(image_path)
            width, height = image.size

            new_image = Image.new("RGBA", (self.max_width, self.max_height), (0, 0, 0, 0))

            aspect_ratio = width / height
            new_width = self.max_width
            new_height = int(new_width / aspect_ratio)
            if new_height > self.max_height:
                new_height = self.max_height
                new_width = int(new_height * aspect_ratio)
            resized_image = image.resize((new_width, new_height))

            # Center the resized image on the new canvas
            x_offset = (self.max_width - new_width) // 2
            y_offset = (self.max_height - new_height) // 2
            new_image.paste(resized_image, (x_offset, y_offset))

            image.close()
            output_file_path = os.path.join(output_folder, f"updated_{os.path.basename(image_path).split('.')[0]}.png")
            new_image.save(output_file_path, quality=self.quality)
            new_image.close()

            # Update progress bar
            progress = (index + 1) * 100 // total_images
            self.progress_changed.emit(progress)

        # Signal that processing is finished
        self.processing_finished.emit()

class ImageProcessorApp(QWidget):
    def __init__(self):
        super().__init__()

        self.selected_folder = ""
        self.image_previews = []
        self.max_width = 0  # Initialize to 0
        self.max_height = 0  # Initialize to 0
        self.quality = 100  # Default quality value
        self.init_ui()

    def init_ui(self):
        self.setMinimumSize(600, 400)  # Set the minimum window size

        layout = QVBoxLayout()

        select_button = QPushButton("Select Images Folder", self)
        select_button.clicked.connect(self.select_folder)

        process_button = QPushButton("Process Images", self)
        process_button.clicked.connect(self.process_images)

        buttons_layout = QVBoxLayout()
        buttons_layout.addWidget(select_button)
        buttons_layout.addWidget(process_button)

        # Add progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        buttons_layout.addWidget(self.progress_bar)

        self.preview_scroll_area = QScrollArea(self)
        self.preview_scroll_area.setWidgetResizable(True)
        self.preview_widget = QWidget(self.preview_scroll_area)
        self.preview_layout = QGridLayout(self.preview_widget)

        layout.addLayout(buttons_layout)
        layout.addWidget(self.preview_scroll_area)

        # Create a QLabel to show the loading animation
        self.loading_label = QLabel(self)
        self.loading_movie = QMovie("loading.gif")
        self.loading_label.setMovie(self.loading_movie)
        layout.addWidget(self.loading_label, alignment=Qt.AlignCenter)
        self.loading_label.hide()

        self.setLayout(layout)
        self.setWindowTitle("Image Processor")
        self.show()

    def resizeEvent(self, event):
        self.update_preview()

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(None, "Select a folder with images")
        if folder_path:
            self.selected_folder = folder_path
            self.update_preview()
            self.calculate_max_dimensions()

    def update_preview(self):
        if not self.selected_folder:
            return

        self.image_previews = []
        for filename in os.listdir(self.selected_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                image_path = os.path.join(self.selected_folder, filename)
                self.image_previews.append(image_path)

        self.clear_preview()

        if self.image_previews:
            row, col = 0, 0
            window_width = self.width()
            thumbnail_size = window_width // 5  # Adjust the number to change thumbnail size
            for i, image_path in enumerate(self.image_previews):
                pixmap = QPixmap(image_path)
                thumbnail = self.scale_pixmap(pixmap, thumbnail_size)
                label = QLabel(self)
                label.setPixmap(thumbnail)
                self.preview_layout.addWidget(label, row, col)
                col += 1
                if col > 3:
                    row += 1
                    col = 0

            self.preview_widget.setLayout(self.preview_layout)
            self.preview_scroll_area.setWidget(self.preview_widget)

    def scale_pixmap(self, pixmap, size):
            return pixmap.scaledToWidth(size, Qt.SmoothTransformation)

    def clear_preview(self):
        for i in reversed(range(self.preview_layout.count())):
            self.preview_layout.itemAt(i).widget().setParent(None)

    def calculate_max_dimensions(self):
        if not self.selected_folder:
            return

        self.max_width = 0
        self.max_height = 0
        for filename in os.listdir(self.selected_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                image_path = os.path.join(self.selected_folder, filename)
                image = Image.open(image_path)
                width, height = image.size
                self.max_width = max(self.max_width, width)
                self.max_height = max(self.max_height, height)
                image.close()

    def process_images(self):
        if not self.selected_folder:
            return

        # Disable buttons and show loading animation
        self.loading_label.show()
        self.loading_movie.start()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)

        # Disable buttons
        for button in self.findChildren(QPushButton):
            button.setDisabled(True)

        # Create a thread for image processing
        self.image_processor_thread = ImageProcessorThread(
            selected_folder=self.selected_folder,
            max_width=self.max_width,
            max_height=self.max_height,
            quality=self.quality
        )
        self.image_processor_thread.progress_changed.connect(self.update_progress)
        self.image_processor_thread.processing_finished.connect(self.finish_processing)

        # Start processing images in a separate thread
        self.image_processor_thread.start()

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)

    def finish_processing(self):
        # Hide loading animation and progress bar
        self.loading_movie.stop()
        self.loading_label.hide()
        self.progress_bar.setVisible(False)

        # Enable buttons
        for button in self.findChildren(QPushButton):
            button.setDisabled(False)

        # Clear state after processing is finished
        self.clear_preview()
        self.selected_folder = ""
        self.image_previews = []
        self.max_width = 0  # Initialize to 0
        self.max_height = 0

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageProcessorApp()
    sys.exit(app.exec_())
