import sys
from PyQt5.QtWidgets import QApplication
from src.main import SeismicPlotter
def main():
    app = QApplication(sys.argv)
    window = SeismicPlotter()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()