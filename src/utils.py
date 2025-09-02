from PyQt5.QtWidgets import QMessageBox
from obspy import read
import pandas as pd
import os

def group_sac_files(folder):
    """Groups SAC files by event/station."""
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

def load_trace_data(files, group_key):
    """Loads seismic trace data from files."""
    try:
        st = read(files[0])  # Read the first file
        print(f"Loaded first file: {files[0]}")
        print(f"Number of traces: {len(st)}")
        print(f"First trace data length: {len(st[0].data)}")
        for file in files[1:]:
            st += read(file)  # Add other components
            print(f"Added file: {file}")
        print(f"Total number of traces for {group_key}: {len(st)}")
        print(f"Trace IDs: {[tr.id for tr in st]}")
        return st
    except Exception as e:
        QMessageBox.critical(
            None, "Error", f"Failed to load {group_key}.\nError: {str(e)}"
        )
        return None

def calculate_wave_frame(p_wave_time, sampling_rate, filter_params=None):
    """Calculates wave frame from time considering filter offset."""
    wave_offset = 0
    if filter_params:
        wave_offset = int(filter_params["offset"] * sampling_rate)
    return int(p_wave_time * sampling_rate) + wave_offset 