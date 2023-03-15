from functools import partial
import sys
import urllib.request


from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, Qt, QThread, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class Downloader(QObject):
    resultsChanged = pyqtSignal(bytes)

    @pyqtSlot(str)
    def download(self, url):
        img = urllib.request.urlopen(url).read()
        self.resultsChanged.emit(img)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("")

        self.thread = QThread(self)
        self.thread.start()

        self.downloader = Downloader()
        self.downloader.moveToThread(self.thread)
        self.downloader.resultsChanged.connect(self.on_resultsChanged)

        self.widgetIMG = QLabel(alignment=Qt.AlignHCenter)

        self.widgetList = QComboBox()
        self.widgetList.currentIndexChanged.connect(self.display)
        for text, url in zip(
            ("first image", "second image", "third image"),
            (
                "https://images.freeimages.com/images/previews/3c8/blumenwiese-1641773.jpg",
                "https://images.freeimages.com/images/previews/704/be-the-light-for-those-around-you-1641842.jpg",
                "https://images.freeimages.com/images/previews/ed7/tree-shadow-1641553.jpg",
            ),
        ):
            self.widgetList.addItem(text, url)

        widget = QWidget()
        lo2 = QVBoxLayout(widget)
        lo2.addWidget(self.widgetIMG)
        lo2.addWidget(self.widgetList)
        self.setCentralWidget(widget)

    @pyqtSlot(int)
    def display(self, ix):
        url = self.widgetList.itemData(ix)
        wrapper = partial(self.downloader.download, url)
        QTimer.singleShot(0, wrapper)

    @pyqtSlot(bytes)
    def on_resultsChanged(self, img):
        pixmap = QPixmap()
        pixmap.loadFromData(img)
        self.widgetIMG.setPixmap(pixmap.scaledToHeight(380))

    def closeEvent(self, event):
        self.thread.quit()
        self.thread.wait()
        super().closeEvent(event)


if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())