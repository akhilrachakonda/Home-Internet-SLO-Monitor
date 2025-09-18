import matplotlib
# Force non-interactive backend in headless containers
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

def save_time_series(ts_list, y_list, ylabel, outpath):
    Path(outpath).parent.mkdir(parents=True, exist_ok=True)
    plt.figure()
    plt.plot(ts_list, y_list)
    plt.xlabel("time")
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()
