import warnings
import numpy as np
import dask.array as da
from contextlib import nullcontext

# === Internal functions ===
def _as_dask_array(x):
    """
    Convert input to a Dask array if it is not already one.

    Parameters
    ----------
    x : array-like
        Input data to convert.

    Returns
    -------
    dask.array.Array
        Dask array representation of the input.
    """
    if isinstance(x, da.Array):
        return x
    return da.from_array(np.asarray(x), chunks="auto")

# === Public functions ===
def nansum(a, b, suppress_warnings=True):
    """
    Sum two arrays element-wise, treating NaNs as zeros.

    NaN values are replaced with zero before summation. The result is set back
    to NaN only where both ``a`` and ``b`` were NaN.

    Parameters
    ----------
    a : array-like
        First input array.
    b : array-like
        Second input array.
    suppress_warnings : bool, optional
        If ``True``, suppresses runtime warnings during computation. Default is ``True``.

    Returns
    -------
    dask.array.Array
        Element-wise sum of ``a`` and ``b``.
    """
    context_manager = warnings.catch_warnings() if suppress_warnings else nullcontext()
    with context_manager:
        if suppress_warnings:
            warnings.simplefilter("ignore")

        a = _as_dask_array(a)
        b = _as_dask_array(b)

        if a.size > 1 and b.size == 1:
            both_nan_mask = da.isnan(a)
        elif a.size == 1 and b.size > 1:
            both_nan_mask = da.isnan(b)
        else:
            both_nan_mask = da.isnan(a) & da.isnan(b)

        a_no_nans = da.nan_to_num(a)
        b_no_nans = da.nan_to_num(b)

        result = a_no_nans + b_no_nans
        result = da.where(both_nan_mask, np.nan, result)

    return result

def nansub(a, b, suppress_warnings=True):
    """
    Subtract two arrays element-wise, treating NaNs as zeros.

    NaN values are replaced with zero before subtraction. The result is set back
    to NaN only where both ``a`` and ``b`` were NaN.

    Parameters
    ----------
    a : array-like
        First input array (minuend).
    b : array-like
        Second input array (subtrahend).
    suppress_warnings : bool, optional
        If ``True``, suppresses runtime warnings during computation. Default is ``True``.

    Returns
    -------
    dask.array.Array
        Element-wise difference of ``a`` minus ``b``.
    """
    context_manager = warnings.catch_warnings() if suppress_warnings else nullcontext()
    with context_manager:
        if suppress_warnings:
            warnings.simplefilter("ignore")

        a = _as_dask_array(a)
        b = _as_dask_array(b)

        if a.size > 1 and b.size == 1:
            both_nan_mask = da.isnan(a)
        elif a.size == 1 and b.size > 1:
            both_nan_mask = da.isnan(b)
        else:
            both_nan_mask = da.isnan(a) & da.isnan(b)

        a_no_nans = da.nan_to_num(a)
        b_no_nans = da.nan_to_num(b)

        result = a_no_nans - b_no_nans
        result = da.where(both_nan_mask, np.nan, result)

    return result

def nanmul(a, b, suppress_warnings=True):
    """
    Multiply two arrays element-wise, treating NaNs as ones.

    NaN values are replaced with zero before multiplication (via ``nan_to_num``).
    The result is set back to NaN only where both ``a`` and ``b`` were NaN.

    Parameters
    ----------
    a : array-like
        First input array.
    b : array-like
        Second input array.
    suppress_warnings : bool, optional
        If ``True``, suppresses runtime warnings during computation. Default is ``True``.

    Returns
    -------
    dask.array.Array
        Element-wise product of ``a`` and ``b``.
    """
    context_manager = warnings.catch_warnings() if suppress_warnings else nullcontext()
    with context_manager:
        if suppress_warnings:
            warnings.simplefilter("ignore")

        a = _as_dask_array(a)
        b = _as_dask_array(b)

        if a.size > 1 and b.size == 1:
            both_nan_mask = da.isnan(a)
        elif a.size == 1 and b.size > 1:
            both_nan_mask = da.isnan(b)
        else:
            both_nan_mask = da.isnan(a) & da.isnan(b)

        a_no_nans = da.nan_to_num(a)
        b_no_nans = da.nan_to_num(b)

        result = a_no_nans * b_no_nans
        result = da.where(both_nan_mask, np.nan, result)

    return result

def nandiv(a, b, suppress_warnings=True):
    """
    Divide two arrays element-wise, treating NaNs as ones.

    NaN values are replaced with zero before division (via ``nan_to_num``).
    The result is set back to NaN only where both ``a`` and ``b`` were NaN.

    Parameters
    ----------
    a : array-like
        Numerator array.
    b : array-like
        Denominator array.
    suppress_warnings : bool, optional
        If ``True``, suppresses runtime warnings during computation (e.g. divide
        by zero). Default is ``True``.

    Returns
    -------
    dask.array.Array
        Element-wise quotient of ``a`` divided by ``b``.
    """
    context_manager = warnings.catch_warnings() if suppress_warnings else nullcontext()
    with context_manager:
        if suppress_warnings:
            warnings.simplefilter("ignore")

        a = _as_dask_array(a)
        b = _as_dask_array(b)

        if a.size > 1 and b.size == 1:
            both_nan_mask = da.isnan(a)
        elif a.size == 1 and b.size > 1:
            both_nan_mask = da.isnan(b)
        else:
            both_nan_mask = da.isnan(a) & da.isnan(b)

        a_no_nans = da.nan_to_num(a)
        b_no_nans = da.nan_to_num(b)

        result = a_no_nans / b_no_nans
        result = da.where(both_nan_mask, np.nan, result)

    return result

def mad(data, axis=None):
    """
    Compute the Median Absolute Deviation (MAD) along a given axis.

    Parameters
    ----------
    data : array-like or da.Array
        Input data.
    axis : int, optional
        Axis along which to compute the MAD. If ``None``, the MAD is computed
        over the entire array.

    Returns
    -------
    numpy.ndarray or dask.array.Array
        MAD values along the specified axis, matching the type of ``data``.
    """
    if isinstance(data, da.Array):
        median = da.nanmedian(data, axis=axis)
        median = median.reshape((median.shape[0],) + (1,) * (data.ndim - 1))
        x = da.nanmedian(da.abs(data - median), axis=axis)
    else:
        median = np.nanmedian(data, axis=axis)
        median = median.reshape((median.shape[0],) + (1,) * (data.ndim - 1))
        x = np.nanmedian(np.abs(data - median), axis=axis)
    return x

def remove_outliers(data, axis=None, k=3, return_inds=False):
    """
    Remove outliers from an array using the Median Absolute Deviation (MAD) method.

    Values more than ``k`` MADs from the median are replaced with NaN.

    Parameters
    ----------
    data : array-like or dask.array.Array
        Input data from which to remove outliers.
    axis : int, optional
        Axis along which to compute the median and MAD. If ``None``, computed
        over the entire array.
    k : float, optional
        Number of MADs beyond the median to use as the outlier threshold. Default is ``3``.
    return_inds : bool, optional
        If ``True``, also returns a boolean mask where ``True`` indicates an outlier.
        Default is ``False``.

    Returns
    -------
    data : numpy.ndarray or dask.array.Array
        Array with outliers replaced by NaN, matching the type of the input.
    mask : numpy.ndarray or dask.array.Array
        Boolean outlier mask. Only returned if ``return_inds=True``.
    """
    if isinstance(data, da.Array):
        data = data.astype(float)
        median = da.nanmedian(data, axis=axis)
        median = median.reshape((median.shape[0],) + (1,) * (data.ndim - 1))
        x = mad(data, axis=axis)
        x = x.reshape((x.shape[0],) + (1,) * (data.ndim - 1))
        mask = da.abs(data - median) > k * x
        data = da.where(mask, np.nan, data)
    else:
        data = data.astype(float)
        median = np.nanmedian(data, axis=axis)
        median = median.reshape((median.shape[0],) + (1,) * (data.ndim - 1))
        x = mad(data, axis=axis)
        x = x.reshape((x.shape[0],) + (1,) * (data.ndim - 1))
        mask = np.abs(data - median) > k * x
        data[mask] = np.nan
    if return_inds:
        return data, mask
    else:
        return data

def mink(data, k):
    """
    Return the ``k`` smallest values in an array and their indices, in ascending order.

    Parameters
    ----------
    data : array-like
        1-D input array to search.
    k : int
        Number of smallest values to return. If ``k <= 0``, empty arrays are
        returned. If ``k >= len(data)``, all elements are returned sorted.

    Returns
    -------
    values : numpy.ndarray
        The ``k`` smallest values in ascending order.
    indices : numpy.ndarray of int
        Indices into ``data`` corresponding to the ``k`` smallest values.
    """
    if k <= 0:
        return np.array([]), np.array([], dtype=int)

    if k >= len(data):
        indices = np.argsort(data)
        return data[indices], indices

    partitioned_inds = np.argpartition(data, k)[:k]
    sorted_inds = partitioned_inds[np.argsort(data[partitioned_inds])]
    return data[sorted_inds], sorted_inds
