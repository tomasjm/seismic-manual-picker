import os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QListWidgetItem,
)
from src.filter_window import FilterConfigWindow
from src.trigger_window import TriggerConfigWindow
from src.shortcuts import setup_shortcuts
from src.ui_setup import setup_ui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import  QIcon
import pyqtgraph as pg
from pyqtgraph import LabelItem
from obspy import read
from obspy.signal.trigger import classic_sta_lta, trigger_onset
import numpy as np
import pandas as pd
from matplotlib import mlab


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
        self.active_plot = None  # Track which plot is being zoomed

        setup_ui(self)
        setup_shortcuts(self)
        self.load_data_from_csv()


    def load_data_from_csv(self):
        if self.data_file and os.path.exists(self.data_file):
            self.data_df = pd.read_csv(self.data_file, index_col="trace_path")
            if "deleted" not in self.data_df.columns:
                self.data_df['deleted'] = False
        else:
            self.data_df = pd.DataFrame(
                columns=["trace_path", "p_wave_frame", "needs_review", "deleted"]
            )
            self.data_df.set_index("trace_path", inplace=True)

    def save_data_to_csv(self):
        if self.data_file:
            self.data_df.to_csv(self.data_file)
            print("saving csv")
            print(self.data_df)
        else:
            print("Error: data_file path not set")


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
                            False
                        ]  # p_wave_frame, needs_review
                except Exception as e:
                    QMessageBox.critical(
                        self, "Error", f"Failed to load {group_key}.\nError: {str(e)}"
                    )

            self.save_data_to_csv()

            # Apply filters and update the trace list
            self.apply_filters()

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

        self.clear_plot()

        if selected_group_key is None:
            raise Exception("Selected group key trace cannot be none")

        if self.filter and selected_group_key in self.filtered_traces:
            st = self.filtered_traces[selected_group_key]
        else:
            st = self.traces[selected_group_key]

        tr = st.select(channel="*Z")[0]

        Sxx, freqs, times = mlab.specgram(tr.data - tr.data.mean(), Fs=tr.stats.sampling_rate, NFFT=128,pad_to=8*128, noverlap=int(128 * 0.9))
        Sxx = np.sqrt(Sxx[1:, :])
        freqs = freqs[1:]
        img = pg.ImageItem()
        hist = pg.HistogramLUTItem()
        hist.setImageItem(img)
        hist.setLevels(np.min(Sxx), np.max(Sxx))
        hist.gradient.restoreState(
                {'mode': 'rgb',
                    'ticks': [(0.5, (33, 145, 140, 255)),
                            (1.0, (250, 230, 0, 255)),
                            (0.0, (69, 4, 87, 255))]})
        self.spectrogram_item.addItem(img)
        img.setImage(Sxx.T)
        img.setRect(times[0],freqs[0],times[-1]-times[0],freqs[-1]-freqs[0])
        times = np.linspace(0, tr.stats.endtime - tr.stats.starttime, num=len(tr.data))

        # Plot the trace data with increased width
        self.plot_item.plot(
            x=times, y=tr.data, pen=pg.mkPen(color=(0, 0, 0), width=1), name=tr.id
        )

        self.spectrogram_item.getViewBox().setXLink(self.plot_item)

        # Plot P wave marker
        if self.p_wave_time is not None:
            self.setup_p_markers()

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

    def setup_p_markers(self, pos= None):
        p = self.p_wave_time
        if pos is not None:
            p = pos


        self.spec_marker_line = pg.InfiniteLine(
            pos=p,
            angle=90,
            pen=pg.mkPen(color=(255, 0, 0), width=2.5),
            movable=True,
        )
        self.spectrogram_item.addItem(self.spec_marker_line)
        self.spec_marker_line.sigPositionChanged.connect(self.update_p_wave_marker)

        self.marker_line = pg.InfiniteLine(
            pos=p,
            angle=90,
            pen=pg.mkPen(color=(255, 0, 0), width=2.5),
            movable=True,
        )
        self.plot_item.addItem(self.marker_line)
        self.marker_line.sigPositionChanged.connect(self.update_p_wave_marker)

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

        # Check if the trace is already loaded
        index = self.trace_list.row(item)
        print(f"Selected {group_key}")
        if group_key not in self.traces:
            self.load_data(group_key)
        print(self.traces[group_key])
        # Apply filter if parameters are set
        self.clear_p_marker()
        if self.filter and self.filter_params:
            self.apply_filter_to_selected()

        # Calculate trigger and update P wave marker
        if self.trigger:
            self.calculate_trigger_for_selected()

        # Load P-wave arrival time from CSV
        if group_key in self.data_df.index and pd.notna(
            self.data_df.loc[group_key, "p_wave_frame"]
        ):
            p_wave_frame = self.data_df.loc[group_key, "p_wave_frame"]
            st = self.traces[group_key]
            tr = st.select(channel="*Z")[0]
            wave_offset = 0
            if self.filter:
                wave_offset = int(self.filter_params["offset"])
            self.p_wave_time = p_wave_frame / tr.stats.sampling_rate - wave_offset
            self.p_wave_label.setText(f"P Wave Time: {self.p_wave_time:.2f} s")

        selected_trace = group_key
        self.plot_traces(selected_group_key=selected_trace)

    def update_p_wave_marker(self, line):
        print(line)
        time = line.value()
        if self.plot_item:
            self.p_wave_time = time
            self.p_wave_label.setText(f"P Wave Time: {time:.2f} s")
            self.spec_marker_line.setValue(time)
            self.marker_line.setValue(time)

    def manually_mark_p(self):
        if self.plot_item:
            self.p_wave_time = 5 
            self.setup_p_markers()
            self.p_wave_label.setText(f"P Wave Time: {self.p_wave_time:.2f} s")

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
            QMessageBox.information(self, "Success", f"P-wave time for {group_key} saved successfully.")

    def save_p_wave_time(self):
        if self.p_wave_time is not None:
            self.save_p_wave_time_to_csv()
            self.navigate_to_next_trace()
            self.apply_filters()
        else:
            QMessageBox.warning(self, "Warning", "No P-wave time to save. Please mark a P-wave first.")

    def navigate_to_next_trace(self):
        current_index = self.trace_list.currentRow()
        next_index = current_index + 1
        if next_index < self.trace_list.count():
            next_item = self.trace_list.item(next_index)
            self.trace_list.setCurrentItem(next_item)
            self.clear_p_marker()
            self.plot_selected_trace(next_item)
        else:
            QMessageBox.information(self, "End of List", "You've reached the end of the trace list.")
            self.clear_plot()

    def apply_filter(self, filter_params):
        self.filter_params = filter_params
        self.filter = True
        self.reload_plot()

        QMessageBox.information(
            self,
            "Success",
            f"{filter_params['type'].capitalize()} filter parameters set successfully",
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

    def apply_sta_lta_trigger(self, trigger_params):
        self.sta = trigger_params["sta"]
        self.lta = trigger_params["lta"]
        self.threshold = trigger_params["threshold"]
        self.trigger = True
        self.reload_plot()

    def open_trigger_config(self):
        self.trigger_config_window = TriggerConfigWindow(self)
        self.trigger_config_window.show()

    def calculate_trigger_for_selected(self, reload=False):
        if not self.trigger:
            print("Trigger is not enabled")
            return

        current_item = self.trace_list.currentItem()
        if not current_item:
            print("No item selected")
            return

        group_key = current_item.text()


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
            self.p_wave_label.setText(f"P Wave Time: {self.p_wave_time:.2f} s")
            print(f"P wave time updated to {self.p_wave_time:.2f}")

        elif not any(self.triggers[group_key]):
            print("No triggers found for any trace in this group")

    def apply_trigger_to_selected(self):
        current_item = self.trace_list.currentItem()
        if current_item:
            group_key = current_item.text()
            self.apply_sta_lta_trigger(group_key)

    def toggle_filter(self):
        print("trying to toggle filter")
        self.filter = not self.filter
        current_item = self.trace_list.currentItem()
        if current_item:
            self.plot_selected_trace(current_item)
        QMessageBox.information(
            self, "Filter Toggle", f"Filter is now {'on' if self.filter else 'off'}"
        )

    def clear_p_marker(self):
        self.marker_line = None
        self.spec_marker_line = None
        self.p_wave_time = None
        self.p_wave_label.setText("Use 'P' key or toolbar button to mark P wave")

    def clear_plot(self):
        self.plot_item.clear()
        self.spectrogram_item.clear()

    def navigate_traces(self, direction):
        current_index = self.trace_list.currentRow()
        new_index = current_index + direction
        if 0 <= new_index < self.trace_list.count():
            item = self.trace_list.item(new_index)
            self.trace_list.setCurrentItem(item)
            self.plot_selected_trace(item)

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
            status_text = "tagged for review" if new_status else "untagged from review"
            QMessageBox.information(
                self,
                "Review Status Changed",
                f"Trace {group_key} has been {status_text}.",
            )
            self.apply_filters()
        else:
            QMessageBox.warning(
                self, "No Selection", "Please select a trace to toggle review status."
            )

    def toggle_deleted_trace(self):
        current_item = self.trace_list.currentItem()

        if current_item:
            ret = QMessageBox.question(self,'', f"Are you sure to mark as removed trace: {current_item.text()}?", QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                return
            group_key = current_item.text()
            self.data_df.loc[group_key, "deleted"] = True 
            self.save_data_to_csv()
            self.navigate_to_next_trace()
        else:
            QMessageBox.warning(
                self, "No Selection", "Please select a trace to toggle review status."
            )


    def tag_for_review(self):
        self.toggle_review_tag()

    def apply_filters(self):
        self.clear_p_marker()
        
        # Store the currently selected item
        current_item = self.trace_list.currentItem()
        current_group_key = current_item.text() if current_item else None
        
        self.trace_list.clear()
        total_traces = len(self.file_groups)
        for group_key in self.file_groups.keys():
            show_item = True
            
            tagged_state = self.filter_tagged.checkState()
            p_wave_state = self.filter_with_p.checkState()
            
            if tagged_state == Qt.Checked:
                show_item = show_item and self.data_df.loc[group_key, "needs_review"]
            elif tagged_state == Qt.PartiallyChecked:
                show_item = show_item and not self.data_df.loc[group_key, "needs_review"]
            
            if p_wave_state == Qt.Checked:
                show_item = show_item and pd.notnull(self.data_df.loc[group_key, "p_wave_frame"])
            elif p_wave_state == Qt.PartiallyChecked:
                show_item = show_item and pd.isnull(self.data_df.loc[group_key, "p_wave_frame"])

            deleted = self.data_df.loc[group_key, "deleted"]
            show_item = show_item and (pd.isna(deleted) or not deleted) 

            if show_item:
                self.trace_list.addItem(QListWidgetItem(group_key))

        # Try to select the previously selected item, or select the first item if not found
        if self.trace_list.count() > 0:
            if current_group_key:
                items = self.trace_list.findItems(current_group_key, Qt.MatchExactly)
                if items:
                    self.trace_list.setCurrentItem(items[0])
                    self.plot_selected_trace(items[0])
                else:
                    first_item = self.trace_list.item(0)
                    self.trace_list.setCurrentItem(first_item)
                    self.plot_selected_trace(first_item)
            else:
                first_item = self.trace_list.item(0)
                self.trace_list.setCurrentItem(first_item)
                self.plot_selected_trace(first_item)
        else:
            self.clear_plot()
                
        # Update the traces label with the count
        visible_traces = self.trace_list.count()
        self.traces_label.setText(f"Loaded Traces: {visible_traces}/{total_traces}")


    def reset_view(self):
        self.spectrogram_wdiget.getViewBox().autoRange()
        self.plot_widget.getViewBox().autoRange()

    def toggle_zoom_select_mode(self):
        self.zoom_select_mode = not self.zoom_select_mode
        self.zoom_select_action.setChecked(self.zoom_select_mode)
        if self.zoom_select_mode:
            self.plot_on_zoom_click = lambda ev: self.on_zoom_select_click(ev, "plot")
            self.spec_on_zoom_click= lambda ev: self.on_zoom_select_click(ev, "spectrogram")
            self.plot_widget.setCursor(Qt.CrossCursor)
            self.plot_widget.scene().sigMouseClicked.connect(self.plot_on_zoom_click)
            self.plot_widget.scene().sigMouseMoved.connect(self.on_zoom_select_move)

            self.spectrogram_widget.setCursor(Qt.CrossCursor)
            self.spectrogram_widget.scene().sigMouseClicked.connect(self.spec_on_zoom_click)
            self.spectrogram_widget.scene().sigMouseMoved.connect(self.on_zoom_select_move)
        else:
            self.plot_widget.setCursor(Qt.ArrowCursor)
            self.plot_widget.scene().sigMouseClicked.disconnect(self.plot_on_zoom_click)
            self.plot_widget.scene().sigMouseMoved.disconnect(self.on_zoom_select_move)

            self.spectrogram_widget.setCursor(Qt.ArrowCursor)
            self.spectrogram_widget.scene().sigMouseClicked.disconnect(self.spec_on_zoom_click)
            self.spectrogram_widget.scene().sigMouseMoved.disconnect(self.on_zoom_select_move)
            if self.zoom_rect:
                self.plot_item.removeItem(self.zoom_rect)
                self.zoom_rect = None

    def on_zoom_select_click(self, event, source):
        if source == "plot":
            self.active_zoom_plot = self.plot_item
        if source == "spectrogram":
            self.active_zoom_plot = self.spectrogram_item
        if event.button() == Qt.LeftButton:
            pos = self.active_zoom_plot.vb.mapSceneToView(event.scenePos())
            if self.zoom_start is None:
                self.zoom_start = pos.x()
                self.zoom_rect = pg.LinearRegionItem([pos.x(), pos.x()], movable=False)
                self.active_zoom_plot.addItem(self.zoom_rect)
            else:
                self.apply_zoom(self.zoom_start, pos.x())
                self.zoom_start = None
                self.active_zoom_plot.removeItem(self.zoom_rect)
                self.zoom_rect = None

    def on_zoom_select_move(self, event):
        if self.zoom_start is not None and self.zoom_rect is not None:
            pos = self.active_zoom_plot.vb.mapSceneToView(event)
            self.zoom_rect.setRegion([self.zoom_start, pos.x()])

    def apply_zoom(self, start, end):
        left, right = min(start, end), max(start, end)
        self.spectrogram_item.setXRange(left, right, padding=0)
        self.plot_item.setXRange(left, right, padding=0)


    def open_filter_config(self):
        self.filter_config_window = FilterConfigWindow(self)
        self.filter_config_window.show()

    def apply_filter_from_config(self, filter_params):
        self.filter_params = filter_params
        self.filter = True
        self.apply_filter_to_selected()
        self.reload_plot()



