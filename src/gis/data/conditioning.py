import numpy as np
import pandas as pd
import xarray as xr
from util.logger import Logger

def condition_data(data, grid_spacing_days=8):
    logger = Logger().get()

    data = mask_quality(data)

    evi  = data.sel(band="500m_16_days_EVI")
    ndvi = data.sel(band="500m_16_days_NDVI")

    # Collapse duplicate timestamps if present
    logger.info("Grouping data by time")
    evi  = evi.groupby("time").mean(skipna=True)
    ndvi = ndvi.groupby("time").mean(skipna=True)

    # Spatial average first — produces a 1D time series
    logger.info("Spatially averaging")
    evi  = evi.mean(dim=["x", "y"], skipna=True).squeeze()
    ndvi = ndvi.mean(dim=["x", "y"], skipna=True).squeeze()

    # Snap to uniform 8-day grid before interpolating
    logger.info("Snapping to uniform grid")
    evi  = snap_to_uniform_grid(evi, period_days=grid_spacing_days)
    ndvi = snap_to_uniform_grid(ndvi, period_days=grid_spacing_days)

    # Interpolate gaps on the uniform grid
    logger.info("Interpolating NaN values")
    evi  = evi.chunk(dict(time=-1)).interpolate_na(dim="time", method="pchip", use_coordinate=True)
    ndvi = ndvi.chunk(dict(time=-1)).interpolate_na(dim="time", method="pchip", use_coordinate=True)

    # NaNs on the end can't be interpolated so drop those
    evi = evi.dropna(dim="time", how="all")
    ndvi = ndvi.dropna(dim="time", how="all")

    return evi, ndvi

def mask_quality(da: xr.DataArray) -> xr.DataArray:
    """
    Mask pixels with clouds, shadows, or snow using the VI Quality band.
    Uses MODIS MOD13A1 VI Quality bit flags (16-bit unsigned integer).

    Bit 0-1: VI usefulness (00 = good, 01 = marginal, 10 = snow/ice, 11 = cloudy)
    Bit 2:   Shadow (1 = shadow)
    Bit 15:  Possible snow/ice (1 = snow/ice)

    Parameters
    ----------
    da : xr.DataArray
        Full data array with band dimension including "500m_16_days_VI_Quality"

    Returns
    -------
    xr.DataArray
        Data array with clouds, shadows, and snow masked to NaN
    """
    vi_quality = da.sel(band="500m_16_days_VI_Quality").astype(np.uint16)

    # Bits 0-1: MODLAND QA (10 = probably cloudy, 11 = not produced)
    modland_qa = vi_quality & 0b11
    modland_mask = modland_qa >= 0b10

    # Bits 2-5: VI Usefulness (4-bit field, shift right by 2 to isolate)
    vi_usefulness = (vi_quality >> 2) & 0b1111
    usefulness_mask = vi_usefulness >= 0b1100  # Lowest quality and below

    # Bit 10: Mixed clouds
    mixed_cloud_mask = (vi_quality & (1 << 10)) > 0

    # Bit 14: Possible snow/ice
    snow_mask = (vi_quality & (1 << 14)) > 0

    # Bit 15: Possible shadow
    shadow_mask = (vi_quality & (1 << 15)) > 0

    # Combine all bad-pixel masks
    bad_pixels = modland_mask | usefulness_mask | mixed_cloud_mask | snow_mask | shadow_mask

    # Expand mask across all bands for broadcasting
    bad_pixels = bad_pixels.expand_dims({"band": da.coords["band"].values}, axis=da.dims.index("band"))

    return da.where(~bad_pixels)

def snap_to_uniform_grid(da, period_days=8, tolerance_days=4):
    epoch = np.datetime64("1970-01-01", "D")
    time_days = da.time.values.astype(int)
    time_dt = epoch + time_days.astype("timedelta64[D]")
    da = da.assign_coords(time=time_dt)

    grid_start = pd.Timestamp(da.time.values[0])
    grid_end   = pd.Timestamp(da.time.values[-1])
    grid_dates = pd.date_range(start=grid_start, end=grid_end, freq=f"{period_days}D")

    da_snapped = da.reindex(time=grid_dates, method="nearest", tolerance=pd.Timedelta(f"{tolerance_days}D"))

    is_original = da_snapped.notnull()
    da_filled = da_snapped.interpolate_na(dim="time", method="pchip", use_coordinate=True)
    da_filled = da_filled.assign_coords(is_original=("time", is_original.values))

    time_dt = da_filled.time.values.astype("datetime64[D]")
    time_days = (time_dt - epoch).astype(int)
    da_filled = da_filled.assign_coords(time=time_days)

    return da_filled
