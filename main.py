import sys
import os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QToolBar,
    QComboBox,
    QShortcut,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QIcon
from PyQt5.QtWidgets import QAction
import pyqtgraph as pg
from pyqtgraph import LabelItem
from obspy import read
from obspy.signal.trigger import classic_sta_lta, trigger_onset
import numpy as np
import pandas as pd


class SeismicPlotter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seismic Trace Plotter")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon(os.path.join("resources", "icons", "app_icon.png")))

        self.traces = {}  # List to store seismic traces
        self.p_wave_time = None  # P Wave marker time
        self.filtered_traces = {}  # List to store filtered traces
        self.triggers = {}  # List to store trigger times
        self.filter = False
        self.trigger = False
        self.filter_params = None  # Store filter parameters
        self.marker_line = None  # PyQtGraph line for P Wave marker
        self.dragging = False  # Flag to indicate if marker is being dragged
        self.data_file = None  # Will be set when loading data
        print(self.group_sac_files("test_folder"))

        self.initUI()
        self.setupShortcuts()
        self.load_data_from_csv()

        # Set up PyQtGraph
        pg.setConfigOptions(antialias=True)
        self.plot_widget.setBackground("w")
        self.plot_widget.getAxis("bottom").setPen(pg.mkPen(color=(0, 0, 0), width=1))
        self.plot_widget.getAxis("left").setPen(pg.mkPen(color=(0, 0, 0), width=1))
        self.plot_widget.getAxis("bottom").setTextPen(pg.mkPen(color=(0, 0, 0)))
        self.plot_widget.getAxis("left").setTextPen(pg.mkPen(color=(0, 0, 0)))

    def load_data_from_csv(self):
        if self.data_file and os.path.exists(self.data_file):
            self.data_df = pd.read_csv(self.data_file, index_col="trace_path")
        else:
            self.data_df = pd.DataFrame(
                columns=["trace_path", "p_wave_frame", "needs_review"]
            )
            self.data_df.set_index("trace_path", inplace=True)

    def save_data_to_csv(self):
        if self.data_file:
            self.data_df.to_csv(self.data_file)
            print("saving csv")
            print(self.data_df)
        else:
            print("Error: data_file path not set")

    def setupShortcuts(self):
        QShortcut(
            QKeySequence(Qt.Key_Left), self, activated=lambda: self.navigate_traces(-1)
        )
        QShortcut(
            QKeySequence(Qt.Key_Up), self, activated=lambda: self.navigate_traces(-1)
        )
        QShortcut(
            QKeySequence(Qt.Key_Right), self, activated=lambda: self.navigate_traces(1)
        )
        QShortcut(
            QKeySequence(Qt.Key_Down), self, activated=lambda: self.navigate_traces(1)
        )
        QShortcut(QKeySequence(Qt.Key_F), self, activated=self.toggle_filter)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.handle_escape)
        QShortcut(QKeySequence(Qt.Key_R), self, activated=self.reload_plot)
        QShortcut(QKeySequence(Qt.Key_T), self, activated=self.toggle_review_tag)

    def handle_escape(self):
        # Clear focus from any widget
        focused_widget = QApplication.focusWidget()
        if focused_widget:
            focused_widget.clearFocus()

        # Deselect all toolbar actions
        for action in self.toolbar.actions():
            if action.isCheckable():
                action.setChecked(False)

        # Disable zoom select mode if active
        if self.zoom_select_mode:
            self.toggle_zoom_select_mode()

    def initUI(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Install event filter for key press events
        self.installEventFilter(self)

        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Toolbar for navigation (zoom, pan, etc.)
        self.toolbar = QToolBar("Navigation Toolbar")
        self.addToolBar(self.toolbar)

        # Add reset view action
        reset_view_action = QAction(QIcon.fromTheme("view-refresh"), "Reset View", self)
        reset_view_action.triggered.connect(self.reset_view)
        self.toolbar.addAction(reset_view_action)

        # Add zoom selection action
        zoom_select_action = QAction(
            QIcon.fromTheme("zoom-select"), "Zoom Select", self
        )
        zoom_select_action.triggered.connect(self.toggle_zoom_select_mode)
        zoom_select_action.setCheckable(True)
        self.toolbar.addAction(zoom_select_action)

        # PyQtGraph PlotWidget
        self.plot_widget = pg.PlotWidget()
        main_layout.addWidget(self.plot_widget)

        # Set up zoom selection variables
        self.zoom_select_mode = False
        self.zoom_start = None
        self.zoom_rect = None

        # Layouts for controls below the plot
        controls_layout = QHBoxLayout()
        main_layout.addLayout(controls_layout)

        # Sidebar for controls
        sidebar = QVBoxLayout()
        controls_layout.addLayout(sidebar, 2)

        # Set up the plot
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.setLabel("bottom", "Time (s)")
        self.plot_item.setLabel("left", "Amplitude")
        self.plot_item.showGrid(x=True, y=True)

        # Initialize zoom state
        self.zoom_mode = False
        self.zoom_start = None
        self.plot_widget.setMouseEnabled(x=False, y=False)  # Disable horizontal drag
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.scene().sigMouseClicked.connect(self.on_mouse_click)

        # Load Data Button
        load_btn = QPushButton("Load Seismic Data")
        load_btn.clicked.connect(self.save_ref_data)
        sidebar.addWidget(load_btn)

        # List of loaded traces
        sidebar.addWidget(QLabel("Loaded Traces:"))
        self.trace_list = QListWidget()
        self.trace_list.itemClicked.connect(self.plot_selected_trace)
        sidebar.addWidget(self.trace_list)

        # P Wave Marker Controls
        sidebar.addWidget(QLabel("P Wave Marker:"))
        p_wave_layout = QHBoxLayout()
        self.p_wave_input = QLineEdit()
        self.p_wave_input.setPlaceholderText("Enter P Wave Time (s)")
        self.p_wave_input.returnPressed.connect(self.update_p_wave_marker)
        p_wave_layout.addWidget(self.p_wave_input)
        set_p_wave_btn = QPushButton("Set")
        set_p_wave_btn.clicked.connect(self.update_p_wave_marker)
        p_wave_layout.addWidget(set_p_wave_btn)
        sidebar.addLayout(p_wave_layout)

        # Filter Controls
        sidebar.addWidget(QLabel("Filter:"))
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
        sidebar.addLayout(filter_layout)

        apply_filter_btn = QPushButton("Apply Filter")
        apply_filter_btn.clicked.connect(self.apply_filter)
        sidebar.addWidget(apply_filter_btn)

        # STA/LTA Trigger Controls
        sidebar.addWidget(QLabel("STA/LTA Trigger:"))
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
        sidebar.addLayout(trigger_layout)
        apply_trigger_btn = QPushButton("Set Trigger Parameters")
        apply_trigger_btn.clicked.connect(self.apply_sta_lta_trigger)
        sidebar.addWidget(apply_trigger_btn)

        # Export Plot Button
        export_btn = QPushButton("Export Plot as Image")
        export_btn.clicked.connect(self.export_plot)
        sidebar.addWidget(export_btn)

        # Tag for Review Button
        self.tag_review_btn = QPushButton("Tag for Review")
        self.tag_review_btn.clicked.connect(self.tag_for_review)
        sidebar.addWidget(self.tag_review_btn)

        # Spacer
        sidebar.addStretch()

        # Set up the plot
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.setLabel("bottom", "Time (s)")
        self.plot_item.setLabel("left", "Amplitude")
        self.plot_item.showGrid(x=True, y=True)

    def save_ref_data(self):
        options = QFileDialog.Options()
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing Seismic Data Files",
            options=options,
        )
        if folder:
            self.data_file = os.path.join(folder, "data.csv")
            self.load_data_from_csv()  # Reload data with new file path
            self.file_groups = self.group_sac_files(folder)
            for group_key, files in self.file_groups.items():
                try:
                    item = QListWidgetItem(group_key)
                    self.trace_list.addItem(item)
                    if group_key not in self.data_df.index:
                        self.data_df.loc[group_key] = [
                            None,
                            False,
                        ]  # p_wave_frame, needs_review
                except Exception as e:
                    QMessageBox.critical(
                        self, "Error", f"Failed to load {group_key}.\nError: {str(e)}"
                    )

            self.save_data_to_csv()

            # Select and plot the first item
            if self.trace_list.count() > 0:
                first_item = self.trace_list.item(0)
                self.trace_list.setCurrentItem(first_item)
                self.plot_selected_trace(first_item)

    def load_data(self, group_key):
        files = self.file_groups[group_key]
        try:
            st = read(files[0])  # Read the first file
            print(f"Loaded first file: {files[0]}")
            print(f"Number of traces: {len(st)}")
            print(f"First trace data length: {len(st[0].data)}")
            for file in files[1:]:
                st += read(file)  # Add other components
                print(f"Added file: {file}")
            self.traces[group_key] = st
            print(f"Total number of traces for {group_key}: {len(st)}")
            print(f"Trace IDs: {[tr.id for tr in st]}")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to load {group_key}.\nError: {str(e)}"
            )

    # agrupa los tres sacs que encuentra *_Z.sac *_E *_N y los guarda con una key equivalente a event_id/station_id segun la estructura de carpeta/dato que usamos
    def group_sac_files(self, folder):
        file_groups = {}
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith((".sac", ".SAC")):
                    path_parts = os.path.relpath(root, folder).split(os.path.sep)
                    if len(path_parts) >= 2:
                        event = path_parts[0]
                        station = path_parts[-1]
                        group_key = f"{event}/{station}"
                        if group_key not in file_groups:
                            file_groups[group_key] = []
                        file_groups[group_key].append(os.path.join(root, file))
        return file_groups

    def plot_traces(self, selected_group_key=None):
        self.plot_item.clear()

        if selected_group_key is None:
            raise Exception("Selected group key trace cannot be none")

        # Calculate trigger if necessary
        if self.trigger:
            self.calculate_trigger_for_selected()

        if self.filter and selected_group_key in self.filtered_traces:
            st = self.filtered_traces[selected_group_key]
        else:
            st = self.traces[selected_group_key]

        tr = st.select(channel="*Z")[0]

        times = np.linspace(0, tr.stats.endtime - tr.stats.starttime, num=len(tr.data))

        # Plot the trace data with increased width
        self.plot_item.plot(
            x=times, y=tr.data, pen=pg.mkPen(color=(0, 0, 0), width=1), name=tr.id
        )

        # Plot P wave marker
        if self.p_wave_time is not None:
            self.marker_line = pg.InfiniteLine(
                pos=self.p_wave_time,
                angle=90,
                pen=pg.mkPen(color=(255, 0, 0), width=2.5),
                movable=True,
            )
            self.plot_item.addItem(self.marker_line)
            self.marker_line.sigPositionChanged.connect(self.update_p_wave_marker)

        # Indicate if the trace is tagged for review
        if (
            selected_group_key in self.data_df.index
            and self.data_df.loc[selected_group_key, "needs_review"]
        ):
            label = LabelItem(
                text="Tagged for Review", color=(255, 0, 0), justify="left"
            )
            self.plot_item.addItem(label)
            label.setParentItem(self.plot_item.getViewBox())
            label.anchor(itemPos=(0, 0), parentPos=(0.45, 0.065))

        self.plot_item.setTitle(
            "Filtered Seismic Traces (Z Channel)"
            if self.filter
            else "Seismic Traces (Z Channel)"
        )

        # Set labels and ranges
        self.plot_item.setLabel("left", "Amplitude")
        self.plot_item.setLabel("bottom", "Time (s)")
        self.plot_item.enableAutoRange()

    def plot_selected_trace(self, item_or_index=None):
        if isinstance(item_or_index, QListWidgetItem):
            item = item_or_index
        elif isinstance(item_or_index, int):
            item = self.trace_list.item(item_or_index)
        else:
            item = self.trace_list.currentItem()

        if item is None:
            return  # No item selected

        group_key = item.text()
        self.trace_list.setCurrentItem(item)

        # Check if the trace is already loaded
        index = self.trace_list.row(item)
        if index >= len(self.traces):
            # Load the data if it hasn't been loaded yet
            self.load_data(group_key)

        if 0 <= index < len(self.traces):
            # Apply filter if parameters are set
            if self.filter and self.filter_params:
                self.apply_filter_to_selected()

            # Calculate trigger and update P wave marker
            if self.trigger:
                self.calculate_trigger_for_selected()

            # Load P-wave arrival time from CSV
            if group_key in self.data_df.index and pd.notnull(
                self.data_df.loc[group_key, "p_wave_frame"]
            ):
                p_wave_frame = self.data_df.loc[group_key, "p_wave_frame"]
                st = self.traces[group_key]
                tr = st.select(channel="*Z")[0]
                wave_offset = 0
                if self.filter:
                    wave_offset = int(self.filter_params["offset"])
                self.p_wave_time = p_wave_frame / tr.stats.sampling_rate - wave_offset
                self.p_wave_input.setText(f"{self.p_wave_time:.2f}")

            # Update the tag for review button
            is_tagged = self.data_df.loc[group_key, "needs_review"]
            self.update_tag_review_button(is_tagged)

            selected_trace = group_key
            self.plot_traces(selected_group_key=selected_trace)

    def update_p_wave_marker(self, line=None):
        try:
            if line:
                time = line.value()
            else:
                time = float(self.p_wave_input.text())

            if self.plot_item:
                if self.marker_line:
                    self.marker_line.setValue(time)
                else:
                    self.marker_line = pg.InfiniteLine(
                        pos=time, angle=90, pen="r", movable=True
                    )
                    self.plot_item.addItem(self.marker_line)
                    self.marker_line.sigPositionChanged.connect(
                        self.update_p_wave_marker
                    )

                self.p_wave_time = time
                self.p_wave_input.setText(f"{time:.2f}")
                self.save_p_wave_time_to_csv()

        except ValueError:
            QMessageBox.warning(
                self,
                "Input Error",
                "Please enter a valid numerical value for P Wave time.",
            )

    def save_p_wave_time_to_csv(self):
        current_item = self.trace_list.currentItem()
        if current_item:
            print("updating csv")
            group_key = current_item.text()
            st = self.traces[group_key]
            tr = st.select(channel="*Z")[0]
            p_wave_frame = int(self.p_wave_time * tr.stats.sampling_rate)
            wave_offset = 0
            if self.filter:
                wave_offset = int(self.filter_params["offset"] * tr.stats.sampling_rate)
            self.data_df.loc[group_key, "p_wave_frame"] = p_wave_frame + wave_offset
            self.save_data_to_csv()

    def on_click(self, event):
        print("clicking")
        if event.inaxes != self.ax:
            return
        if self.marker_line:
            print("clicking marker")
            contains, _ = self.marker_line.contains(event)
            if contains:
                self.dragging = True

    def on_drag(self, event):
        if not self.dragging or not self.marker_line:
            return
        if event.inaxes != self.ax:
            return
        new_time = event.xdata
        # Update marker position with constraints
        if new_time < self.ax.get_xlim()[0]:
            new_time = self.ax.get_xlim()[0]
        elif new_time > self.ax.get_xlim()[1]:
            new_time = self.ax.get_xlim()[1]
        self.marker_line.set_xdata([new_time, new_time])
        self.p_wave_time = new_time
        self.p_wave_input.setText(f"{new_time:.2f}")
        self.canvas.draw()

    def on_release(self, event):
        self.dragging = False
        self.save_p_wave_time_to_csv()

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

            # Store filter parameters
            self.filter_params = {
                "type": filter_type,
                "min_freq": min_freq,
                "max_freq": max_freq,
                "offset": offset,
            }
            self.filter = True
            self.reload_plot()

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

    def apply_filter_to_selected(self):
        if not self.filter or not self.filter_params:
            return

        current_item = self.trace_list.currentItem()
        if not current_item:
            return

        group_key = current_item.text()
        st = self.traces[group_key]

        try:
            filtered_st = st.copy()
            filter_type = self.filter_params["type"]

            if filter_type == "bandpass":
                filtered_st.filter(
                    "bandpass",
                    freqmin=self.filter_params["min_freq"],
                    freqmax=self.filter_params["max_freq"],
                )
            elif filter_type == "highpass":
                filtered_st.filter(
                    "highpass",
                    freq=self.filter_params["min_freq"],
                )
            elif filter_type == "lowpass":
                filtered_st.filter(
                    "lowpass",
                    freq=self.filter_params["max_freq"],
                )

            # Apply offset
            for tr in filtered_st:
                start_time = tr.stats.starttime + self.filter_params["offset"]
                tr.trim(starttime=start_time)

            self.filtered_traces[group_key] = filtered_st

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to apply filter.\nError: {str(e)}"
            )

    def apply_sta_lta_trigger(self):
        try:
            self.sta = float(self.sta_input.text())
            self.lta = float(self.lta_input.text())
            self.threshold = float(self.threshold_input.text())

            if self.sta >= self.lta:
                raise ValueError("STA must be less than LTA")

            self.trigger = True
            QMessageBox.information(
                self, "Success", "STA/LTA trigger parameters set successfully"
            )

            # Replot after changing trigger settings
            self.reload_plot()
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to set STA/LTA trigger parameters.\nError: {str(e)}",
            )

    def calculate_trigger_for_selected(self, reload=False):
        if not self.trigger:
            print("Trigger is not enabled")
            return

        current_item = self.trace_list.currentItem()
        if not current_item:
            print("No item selected")
            return

        group_key = current_item.text()

        current_saved_p_wave = self.data_df.loc[group_key, "p_wave_frame"]
        if current_saved_p_wave and not reload:
            return

        st = (
            self.filtered_traces.get(group_key)
            if self.filter
            else self.traces.get(group_key)
        )

        if not st:
            print(f"No data found for {group_key}")
            return

        print(f"Processing group: {group_key}")
        print(f"STA: {self.sta}, LTA: {self.lta}, Threshold: {self.threshold}")

        self.triggers[group_key] = {}
        first_trigger_time = None
        for tr in st:
            print(f"Processing trace: {tr.id}")
            print(f"Trace stats: {tr.stats}")
            print(f"Data length: {len(tr.data)}")

            if len(tr.data) == 0:
                print("Trace data is empty, skipping")
                continue

            cft = classic_sta_lta(
                tr.data,
                int(self.sta * tr.stats.sampling_rate),
                int(self.lta * tr.stats.sampling_rate),
            )
            on_off = trigger_onset(cft, self.threshold, self.threshold)
            print(f"Trigger points found: {len(on_off)}")

            if len(on_off) > 0:
                print(f"Trigger saved for {tr.id}")
                self.triggers[group_key][tr.id] = on_off
                trigger_time = on_off[0][0] / tr.stats.sampling_rate
                if first_trigger_time is None or trigger_time < first_trigger_time:
                    first_trigger_time = trigger_time
            else:
                print(f"No triggers found for {tr.id}")

        if first_trigger_time is not None:
            self.p_wave_time = first_trigger_time
            self.p_wave_input.setText(f"{self.p_wave_time:.2f}")
            print(f"P wave time updated to {self.p_wave_time:.2f}")
            self.save_p_wave_time_to_csv()

        elif not any(self.triggers[group_key]):
            print("No triggers found for any trace in this group")

    def apply_trigger_to_selected(self):
        current_item = self.trace_list.currentItem()
        if current_item:
            group_key = current_item.text()
            self.apply_sta_lta_trigger(group_key)

    def export_plot(self):
        options = QFileDialog.Options()
        file, _ = QFileDialog.getSaveFileName(
            self,
            "Save Plot As Image",
            "",
            "PNG Image (*.png);;All Files (*)",
            options=options,
        )
        if file:
            try:
                exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
                exporter.export(file)
                QMessageBox.information(
                    self, "Success", f"Plot saved successfully at {file}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save plot.\nError: {str(e)}"
                )

    def toggle_filter(self):
        print("trying to toggle filter")
        self.filter = not self.filter
        current_item = self.trace_list.currentItem()
        if current_item:
            self.plot_selected_trace(current_item)
        QMessageBox.information(
            self, "Filter Toggle", f"Filter is now {'on' if self.filter else 'off'}"
        )

    def navigate_traces(self, direction):
        current_index = self.trace_list.currentRow()
        new_index = current_index + direction
        if 0 <= new_index < self.trace_list.count():
            self.plot_selected_trace(new_index)

    def reload_plot(self):
        current_item = self.trace_list.currentItem()
        if current_item:
            self.plot_selected_trace(current_item)
        QMessageBox.information(self, "Reload", "Plot reloaded successfully")

    def toggle_review_tag(self):
        current_item = self.trace_list.currentItem()
        if current_item:
            group_key = current_item.text()
            current_status = self.data_df.loc[group_key, "needs_review"]
            new_status = not current_status
            self.data_df.loc[group_key, "needs_review"] = new_status
            self.save_data_to_csv()
            self.update_tag_review_button(new_status)
            status_text = "tagged for review" if new_status else "untagged from review"
            QMessageBox.information(
                self,
                "Review Status Changed",
                f"Trace {group_key} has been {status_text}.",
            )
            self.reload_plot()
        else:
            QMessageBox.warning(
                self, "No Selection", "Please select a trace to toggle review status."
            )

    def tag_for_review(self):
        self.toggle_review_tag()

    def update_tag_review_button(self, is_tagged):
        button_text = "Untag from Review" if is_tagged else "Tag for Review"
        self.tag_review_btn.setText(button_text)

    def zoom_in(self):
        self.plot_widget.getViewBox().scaleBy((0.5, 0.5))

    def zoom_out(self):
        self.plot_widget.getViewBox().scaleBy((2, 2))

    def reset_view(self):
        self.plot_widget.getViewBox().autoRange()

    def toggle_zoom_select_mode(self):
        self.zoom_select_mode = not self.zoom_select_mode
        if self.zoom_select_mode:
            self.plot_widget.setCursor(Qt.CrossCursor)
            self.plot_widget.scene().sigMouseClicked.disconnect(self.on_mouse_click)
            self.plot_widget.scene().sigMouseClicked.connect(self.on_zoom_select_click)
            self.plot_widget.scene().sigMouseMoved.connect(self.on_zoom_select_move)
        else:
            self.plot_widget.setCursor(Qt.ArrowCursor)
            self.plot_widget.scene().sigMouseClicked.disconnect(
                self.on_zoom_select_click
            )
            self.plot_widget.scene().sigMouseMoved.disconnect(self.on_zoom_select_move)
            self.plot_widget.scene().sigMouseClicked.connect(self.on_mouse_click)
            if self.zoom_rect:
                self.plot_item.removeItem(self.zoom_rect)
                self.zoom_rect = None

    def on_zoom_select_click(self, event):
        if event.button() == Qt.LeftButton:
            pos = self.plot_item.vb.mapSceneToView(event.scenePos())
            if self.zoom_start is None:
                self.zoom_start = pos.x()
                self.zoom_rect = pg.LinearRegionItem([pos.x(), pos.x()], movable=False)
                self.plot_item.addItem(self.zoom_rect)
            else:
                self.apply_zoom(self.zoom_start, pos.x())
                self.zoom_start = None
                self.plot_item.removeItem(self.zoom_rect)
                self.zoom_rect = None

    def on_zoom_select_move(self, event):
        if self.zoom_start is not None and self.zoom_rect is not None:
            pos = self.plot_item.vb.mapSceneToView(event)
            self.zoom_rect.setRegion([self.zoom_start, pos.x()])

    def on_mouse_click(self, event):
        # This method is now empty as we're not using it for zoom functionality
        pass

    def apply_zoom(self, start, end):
        left, right = min(start, end), max(start, end)
        self.plot_item.setXRange(left, right, padding=0)


def main():
    app = QApplication(sys.argv)
    window = SeismicPlotter()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
