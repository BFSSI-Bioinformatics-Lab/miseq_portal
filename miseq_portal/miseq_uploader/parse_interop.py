from interop import py_interop_plot, py_interop_run_metrics, py_interop_run
from pathlib import Path
import pandas as pd


def get_qscore_dataframe(run_folder: Path) -> pd.DataFrame:
    """
    Returns a pandas DataFrame containing x (Q-score), y (Total in millions) values for the run
    """
    df_dict = {}
    x_vals = []
    y_vals = []

    run_metrics = py_interop_run_metrics.run_metrics()
    valid_to_load = py_interop_run.uchar_vector(py_interop_run.MetricCount, 0)
    valid_to_load[py_interop_run.Q] = 1
    run_metrics.read(str(run_folder), valid_to_load)
    bar_data = py_interop_plot.bar_plot_data()
    boundary = 30
    options = py_interop_plot.filter_options(run_metrics.run_info().flowcell().naming_method())
    py_interop_plot.plot_qscore_histogram(run_metrics, options, bar_data, boundary)

    for i in range(bar_data.size()):
        x = [bar_data.at(i).at(j).x() for j in range(bar_data.at(i).size())]
        y = [bar_data.at(i).at(j).y() for j in range(bar_data.at(i).size())]
        x_vals += x
        y_vals += y
    df_dict['x'] = x_vals
    df_dict['y'] = y_vals
    df = pd.DataFrame.from_dict(df_dict)
    return df


def get_qscore_json(run_folder: Path) -> str:
    df = get_qscore_dataframe(run_folder)
    return df.to_json()
