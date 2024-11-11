from PyQt5.QtWidgets import QMessageBox
from obspy import read
import pandas as pd
import os
import re

def group_sac_files(folder):
    """Groups SAC files by event/station."""
    file_groups = {}
    print(f"loading folder {folder}")
    for root, dirs, files in os.walk(os.path.join(folder)):
        for file in files:
            if file.endswith((".sac", ".SAC", ".mseed", ".MSEED")):
                print(f"found file {file}")
                group_key = file.split(".")[0]
                if group_key not in file_groups:
                    file_groups[group_key] = []
                file_groups[group_key].append(os.path.join(root, file))
    sorted_data = dict(sorted(file_groups.items(), key=lambda x: int(re.search(r'\d+', x[0]).group())))
    return sorted_data 

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
