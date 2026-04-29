from datetime import datetime, date, timedelta
import numpy as np

def generate_doy_array(start_date, end_date, step_days=1):
    """
    Generate an array of dates in YYYYDDD format, stepping every N days.

    Parameters
    ----------
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    step_days : int
        Number of days between each step (default: 1)

    Returns
    -------
    np.ndarray
        Array of strings in YYYYDDD format (e.g. '2012353')
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    dates = []
    current = start
    while current <= end:
        days_since_epoch = (current.date() - date(1970, 1, 1)).days
        dates.append(days_since_epoch)
        current += timedelta(days=step_days)

    return np.array(dates)

def to_datetime(doy_array):
    dates = []
    for doy in doy_array:
        dt = date(1970, 1, 1) + timedelta(days=int(doy))
        dates.append(dt)
    return np.array(dates)
