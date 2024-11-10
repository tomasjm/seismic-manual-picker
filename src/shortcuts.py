from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut

def setup_shortcuts(window):
    """Set up keyboard shortcuts for the main window"""
    
    shortcuts = [
        (QKeySequence(Qt.Key_Left), lambda: window.navigate_traces(-1)),
        (QKeySequence(Qt.Key_Up), lambda: window.navigate_traces(-1)),
        (QKeySequence(Qt.Key_Right), lambda: window.navigate_traces(1)),
        (QKeySequence(Qt.Key_Down), lambda: window.navigate_traces(1)),
        (QKeySequence(Qt.Key_F), window.toggle_filter),
        (QKeySequence(Qt.Key_Escape), window.handle_escape),
        (QKeySequence(Qt.Key_R), window.reload_plot),
        (QKeySequence(Qt.Key_T), window.toggle_review_tag),
        (QKeySequence(Qt.Key_Z), window.toggle_zoom_select_mode),
        (QKeySequence(Qt.Key_P), window.manually_mark_p),
        (QKeySequence(Qt.Key_Space), window.save_p_wave_time),
        (QKeySequence(Qt.Key_D), window.toggle_deleted_trace),
    ]
    
    return [QShortcut(key, window, activated=callback) for key, callback in shortcuts] 