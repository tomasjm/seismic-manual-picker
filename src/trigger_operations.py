from obspy.signal.trigger import classic_sta_lta, trigger_onset

def calculate_triggers(trace, sta, lta, threshold):
    """
    Calculate STA/LTA triggers for a single trace.
    
    Args:
        trace: ObsPy Trace object
        sta: Short-term average window (in seconds)
        lta: Long-term average window (in seconds)
        threshold: Trigger threshold value
        
    Returns:
        tuple: (trigger_times, first_trigger_time)
    """
    cft = classic_sta_lta(
        trace.data,
        int(sta * trace.stats.sampling_rate),
        int(lta * trace.stats.sampling_rate),
    )
    on_off = trigger_onset(cft, threshold, threshold)
    
    if len(on_off) > 0:
        first_trigger = on_off[0][0] / trace.stats.sampling_rate
        return on_off, first_trigger
    
    return on_off, None

def calculate_stream_triggers(stream, sta, lta, threshold):
    """
    Calculate triggers for all traces in a stream.
    
    Args:
        stream: ObsPy Stream object
        sta: Short-term average window (in seconds)
        lta: Long-term average window (in seconds)
        threshold: Trigger threshold value
        
    Returns:
        tuple: (triggers_dict, earliest_trigger_time)
    """
    triggers = {}
    first_trigger_time = None
    
    for tr in stream:
        on_off, trigger_time = calculate_triggers(tr, sta, lta, threshold)
        
        if len(on_off) > 0:
            triggers[tr.id] = on_off
            if first_trigger_time is None or trigger_time < first_trigger_time:
                first_trigger_time = trigger_time
                
    return triggers, first_trigger_time 