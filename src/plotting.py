
from matplotlib import mlab
import numpy as np
import pyqtgraph as pg

def plot_spectrogram( tr):
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
                        (0.0, (0, 0, 0, 255))]})
                        # (0.0, (69, 4, 87, 255))]})
    img.setImage(Sxx.T)
    img.setRect(times[0],freqs[0],times[-1]-times[0],freqs[-1]-freqs[0])
    return img
