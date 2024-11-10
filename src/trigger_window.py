from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox
)

class TriggerConfigWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Trigger Configuration")
        self.setGeometry(200, 200, 400, 300)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # STA/LTA Trigger Controls
        layout.addWidget(QLabel("STA/LTA Trigger:"))
        trigger_layout = QHBoxLayout()

        self.sta_input = QLineEdit()
        self.sta_input.setPlaceholderText("STA (s)")
        self.lta_input = QLineEdit()
        self.lta_input.setPlaceholderText("LTA (s)")
        self.threshold_input = QLineEdit()
        self.threshold_input.setPlaceholderText("Threshold")

        trigger_layout.addWidget(self.sta_input)
        trigger_layout.addWidget(self.lta_input)
        trigger_layout.addWidget(self.threshold_input)
        layout.addLayout(trigger_layout)

        apply_trigger_btn = QPushButton("Apply Trigger")
        apply_trigger_btn.clicked.connect(self.apply_trigger)
        layout.addWidget(apply_trigger_btn)

    def apply_trigger(self):
        try:
            sta = float(self.sta_input.text())
            lta = float(self.lta_input.text())
            threshold = float(self.threshold_input.text())

            if sta >= lta:
                raise ValueError("STA must be less than LTA")

            trigger_params = {
                "sta": sta,
                "lta": lta,
                "threshold": threshold,
            }

            if self.parent:
                self.parent.apply_sta_lta_trigger(trigger_params)
                self.close()

            QMessageBox.information(
                self, "Success", "STA/LTA trigger parameters set successfully"
            )

        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to set STA/LTA trigger parameters.\nError: {str(e)}",
            ) 