from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QMessageBox
)

class FilterConfigWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Filter Configuration")
        self.setGeometry(200, 200, 400, 300)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Filter Controls
        layout.addWidget(QLabel("Filter:"))
        filter_layout = QHBoxLayout()

        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItems(["Bandpass", "Highpass", "Lowpass"])
        filter_layout.addWidget(self.filter_type_combo)

        self.min_freq_input = QLineEdit()
        self.min_freq_input.setPlaceholderText("Min Freq (Hz)")
        self.max_freq_input = QLineEdit()
        self.max_freq_input.setPlaceholderText("Max Freq (Hz)")
        self.offset_input = QLineEdit()
        self.offset_input.setPlaceholderText("Offset (s)")

        filter_layout.addWidget(self.min_freq_input)
        filter_layout.addWidget(self.max_freq_input)
        filter_layout.addWidget(self.offset_input)
        layout.addLayout(filter_layout)

        apply_filter_btn = QPushButton("Apply Filter")
        apply_filter_btn.clicked.connect(self.apply_filter)
        layout.addWidget(apply_filter_btn)

    def apply_filter(self):
        try:
            filter_type = self.filter_type_combo.currentText().lower()
            min_freq = (
                float(self.min_freq_input.text())
                if self.min_freq_input.text()
                else None
            )
            max_freq = (
                float(self.max_freq_input.text())
                if self.max_freq_input.text()
                else None
            )
            offset = float(self.offset_input.text()) if self.offset_input.text() else 0

            if filter_type == "bandpass" and (min_freq is None or max_freq is None):
                raise ValueError(
                    "Both minimum and maximum frequencies are required for bandpass filter"
                )
            elif filter_type == "highpass" and min_freq is None:
                raise ValueError("Minimum frequency is required for highpass filter")
            elif filter_type == "lowpass" and max_freq is None:
                raise ValueError("Maximum frequency is required for lowpass filter")

            if filter_type == "bandpass" and min_freq >= max_freq:
                raise ValueError(
                    "Minimum frequency must be less than maximum frequency for bandpass filter"
                )

            filter_params = {
                "type": filter_type,
                "min_freq": min_freq,
                "max_freq": max_freq,
                "offset": offset,
            }

            if self.parent:
                self.parent.apply_filter_from_config(filter_params)
                self.close()

            QMessageBox.information(
                self,
                "Success",
                f"{filter_type.capitalize()} filter parameters set successfully",
            )

        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to set filter parameters.\nError: {str(e)}"
            ) 