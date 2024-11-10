from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QListWidget, QToolBar, QAction, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import pyqtgraph as pg
from pyqtgraph import LabelItem

def setup_ui(window):
    # Central widget
    central_widget = QWidget()
    window.setCentralWidget(central_widget)

    # Install event filter for key press events
    window.installEventFilter(window)

    # Main layout
    main_layout = QVBoxLayout()
    central_widget.setLayout(main_layout)

    # Setup toolbar
    setup_toolbar(window, main_layout)

    # PyQtGraph PlotWidget
    window.spectrogram_widget = pg.PlotWidget()
    main_layout.addWidget(window.spectrogram_widget)  # type: ignore
    window.plot_widget = pg.PlotWidget()
    main_layout.addWidget(window.plot_widget)  # type: ignore

    # Set up zoom selection variables
    window.zoom_select_mode = False
    window.zoom_start = None
    window.zoom_rect = None

    # Layouts for controls below the plot
    controls_layout = QHBoxLayout()
    main_layout.addLayout(controls_layout)

    # Sidebar for controls
    sidebar = QVBoxLayout()
    list_container = QVBoxLayout()
    controls_layout.addLayout(sidebar, 1)
    controls_layout.addLayout(list_container, 2)

    # Set up the plots
    setup_plots(window)

    # Setup controls
    setup_controls(window, sidebar, list_container)

def setup_toolbar(window, main_layout):
    window.toolbar = QToolBar("Navigation Toolbar")
    window.addToolBar(window.toolbar)

    # Add reset view action
    reset_view_action = QAction(QIcon.fromTheme("view-refresh"), "Reset View [R]", window)
    reset_view_action.triggered.connect(window.reset_view)
    window.toolbar.addAction(reset_view_action)

    reload_plot_action = QAction(QIcon.fromTheme("view-refresh"), "Reload plot [L]", window)
    reload_plot_action.triggered.connect(window.reload_plot)
    window.toolbar.addAction(reload_plot_action)

    # Add zoom selection action
    window.zoom_select_action = QAction(QIcon.fromTheme("zoom-select"), "Zoom Select [Z]", window)
    window.zoom_select_action.triggered.connect(window.toggle_zoom_select_mode)
    window.zoom_select_action.setCheckable(True)
    window.toolbar.addAction(window.zoom_select_action)

    # Add button to manually mark P
    window.mark_manual_p = QAction("Add P mark [P]", window)
    window.mark_manual_p.triggered.connect(window.manually_mark_p)
    window.toolbar.addAction(window.mark_manual_p)

    window.delete_p = QAction("Delete selected P [X]", window)
    window.delete_p.triggered.connect(window.delete_selected_p_marker)
    window.toolbar.addAction(window.delete_p)

    # Add button to toggle review tag
    toggle_review_tag = QAction("Toggle tag for review [T]", window)
    toggle_review_tag.triggered.connect(window.toggle_review_tag)
    window.toolbar.addAction(toggle_review_tag)

    # Add button to toggle review tag
    remove_trace_button = QAction("Remove trace [D]", window)
    remove_trace_button.triggered.connect(window.toggle_deleted_trace)
    window.toolbar.addAction(remove_trace_button)

    # Add button to save current state
    save_p_wave_button = QAction("Save trace P wave [SPACE]", window)
    save_p_wave_button.triggered.connect(window.save_p_wave_time)
    window.toolbar.addAction(save_p_wave_button)


def setup_plots(window):
    # Configure main plot widget
    window.plot_widget.setBackground("w")
    window.plot_item = window.plot_widget.getPlotItem()  # Get plot item for main plot
    window.plot_item.setLabel("bottom", "Time (s)")
    window.plot_item.setLabel("left", "Amplitude")
    window.plot_item.showGrid(x=True, y=True)
    window.plot_item.getAxis("bottom").setPen(pg.mkPen(color=(0, 0, 0), width=1))
    window.plot_item.getAxis("left").setPen(pg.mkPen(color=(0, 0, 0), width=1))
    window.plot_item.getAxis("bottom").setTextPen(pg.mkPen(color=(0, 0, 0)))
    window.plot_item.getAxis("left").setTextPen(pg.mkPen(color=(0, 0, 0)))

    # Configure spectrogram widget
    window.spectrogram_item = window.spectrogram_widget.getPlotItem()
    window.spectrogram_item.setLabel("bottom", "Time (s)")
    window.spectrogram_item.setLabel("left", "Frequency (Hz)")  # Changed to frequency for spectrogram
    window.spectrogram_item.showGrid(x=True, y=True)

    # Initialize zoom state
    window.zoom_mode = False
    window.zoom_start = None
    window.plot_widget.setMouseEnabled(x=False, y=False)
    window.plot_widget.setMenuEnabled(False)
    window.spectrogram_widget.setMouseEnabled(x=False, y=False)
    window.spectrogram_widget.setMenuEnabled(False)

    # Set up PyQtGraph global config
    pg.setConfigOptions(antialias=True)

def setup_controls(window, sidebar, list_container):
    # Load Data Button
    load_btn = QPushButton("Load Seismic Data")
    load_btn.clicked.connect(window.save_ref_data)
    list_container.addWidget(load_btn)

    # List of loaded traces
    window.traces_label = QLabel("Loaded Traces:")
    list_container.addWidget(window.traces_label)
    window.trace_list = QListWidget()
    window.trace_list.itemClicked.connect(window.plot_selected_trace)
    list_container.addWidget(window.trace_list)

    # # P Wave Marker Controls
    # sidebar.addWidget(QLabel("P Wave Marker:"))
    # p_wave_layout = QHBoxLayout()
    # window.p_wave_label = QLabel("Use 'P' key or toolbar button to mark P wave")
    # p_wave_layout.addWidget(window.p_wave_label)
    # sidebar.addLayout(p_wave_layout)

    # Filter Configuration Button
    open_filter_config_btn = QPushButton("Open Filter Configuration")
    open_filter_config_btn.clicked.connect(window.open_filter_config)
    sidebar.addWidget(open_filter_config_btn)

    # STA/LTA Trigger Controls
    open_trigger_config_btn = QPushButton("Open Trigger Configuration")
    open_trigger_config_btn.clicked.connect(window.open_trigger_config)
    sidebar.addWidget(open_trigger_config_btn)

    # Filter options
    sidebar.addWidget(QLabel("Filter Options:"))
    window.filter_tagged = QCheckBox("Filter tagged for review events")
    window.filter_with_p = QCheckBox("Filter P marked events")
    window.filter_tagged.setTristate(True)
    window.filter_with_p.setTristate(True)
    sidebar.addWidget(window.filter_tagged)
    sidebar.addWidget(window.filter_with_p)

    # Connect filter checkboxes
    window.filter_tagged.stateChanged.connect(window.apply_filters)
    window.filter_with_p.stateChanged.connect(window.apply_filters)

    # Spacer
    sidebar.addStretch() 