# --- Standard Library ---
from collections import defaultdict
import datetime
from datetime import timedelta
import glob
import os
import re

# --- Third Party ---
from dotenv import load_dotenv
import numpy as np
from rasterio.enums import Resampling
import xarray as xr

# --- Internal ---
from util.logger import Logger

# --- Constants ---
_MODIS_13A1_061_BAND_NAMES = [
    "500m_16_days_EVI", "500m_16_days_NDVI",
    "500m_16_days_VI_Quality", "500m_16_days_MIR_reflectance",
    "500m_16_days_NIR_reflectance", "500m_16_days_red_reflectance",
    "500m_16_days_blue_reflectance", "500m_16_days_sun_zenith_angle",
    "500m_16_days_pixel_reliability", "500m_16_days_view_zenith_angle",
    "500m_16_days_relative_azimuth_angle", "500m_16_days_composite_day_of_the_year"
]

# --- Globals ---
_MODIS_13A1_CACHE = None

# --- Private Functions ---
def _select_coords(
        data : xr.DataArray,
        epsg=4326,
        x=None,
        y=None,
        buffer=None,
        buffer_pixels=None
) -> xr.DataArray:
    if epsg != data.rio.crs.to_epsg():
        da_doy = data.rio.reproject(f"EPSG:{epsg}")
        da_doy.rio.write_crs(f"EPSG:{epsg}", inplace=True)
    if x is not None and y is not None:
        x_values = data["x"].values
        y_values = data["y"].values
        if buffer is None:
            x_ind = np.array(np.argmin(np.abs(x_values - x)))
            y_ind = np.array(np.argmin(np.abs(y_values - y)))
            # data = data.isel(x=slice(x_ind, x_ind + 1), y=slice(y_ind, y_ind + 1))
        else:
            x_ind = np.argwhere((x_values > x - buffer) & (x_values < x + buffer)).flatten()
            y_ind = np.argwhere((y_values > y - buffer) & (y_values < y + buffer)).flatten()
        if buffer_pixels is not None:
            x_ind = np.arange(x_ind.min() - buffer_pixels, x_ind.max() + buffer_pixels + 1)
            y_ind = np.arange(y_ind.min() - buffer_pixels, y_ind.max() + buffer_pixels + 1)
        data = data.isel(x=slice(x_ind.min(), x_ind.max() + 1), y=slice(y_ind.min(), y_ind.max() + 1))
    return data

def _attach_modis_12q1_061(
        data : xr.DataArray,
        epsg=4326,
        x=None,
        y=None,
        buffer=None,
        buffer_pixels=None
) -> xr.DataArray:
    da_modis_12q1 = _load_modis_12q_061(sel=1)
    da_modis_12q1 = da_modis_12q1.sel(band="LC_Type1")
    da_modis_12q1 = da_modis_12q1.rio.reproject_match(data, resampling=Resampling.nearest)

    data = _select_coords(data, epsg=epsg, x=x, y=y, buffer=buffer, buffer_pixels=buffer_pixels)
    da_modis_12q1 = _select_coords(da_modis_12q1, epsg=epsg, x=x, y=y, buffer=buffer, buffer_pixels=buffer_pixels)

    mask = np.ones_like(data["time"].values, dtype=bool)
    for ii, time in enumerate(data["time"].values):
        dt = datetime.datetime(1970, 1, 1) + timedelta(days=int(time))
        year = dt.year
        if year not in da_modis_12q1["time"].values:
            mask[ii] = False
    data = data.isel(time=mask)

    data_arrays = []
    for time in data["time"].values:
        dt = datetime.datetime(1970, 1, 1) + timedelta(days=int(time))
        year = dt.year
        da = da_modis_12q1.sel(time=year)
        data_arrays.append(da)
    da = xr.concat(data_arrays, dim="time")
    da = da.expand_dims({"band": ["LC_Type1"]}).transpose("time", "band", "x", "y")
    da = da.assign_coords(time=data["time"].values, x=data["x"].values, y=data["y"].values)

    data = xr.concat([data, da], dim="band")

    return data

def _load_modis_12q_061(
        *,
        sel,
        epsg=4326,
        x=None,
        y=None,
        buffer=None,
        buffer_pixels=None
) -> xr.DataArray:
    logger = Logger().get()

    # List data files
    paths = glob.glob(os.path.join(os.getenv("DATA_ROOT"), f"modis-12Q{sel}-061", "*.tif"))

    # Regular expressions
    doy_pattern = re.compile(f"doy(\\d+)_")
    band_pattern = re.compile(f"MCD12Q{sel}\\.061_(.+?)_doy")

    # Group paths by DOY
    paths_by_doy = defaultdict(list)
    for path in paths:
        match = doy_pattern.search(path)
        if match:
            doy = match.group(1)
            paths_by_doy[doy].append(path)
    unique_doys = sorted(paths_by_doy.keys())

    # Generate time coordinates
    times = []
    for doy in unique_doys:
        times.append(int(doy[0:4]))

    # Main loading loop
    data_arrays_by_doy = []
    for doy in unique_doys:
        logger.info(f"Loading modis-12Q{sel}-061 for doy={doy}")

        matched_paths = sorted(paths_by_doy[doy])

        bands = []
        for path in matched_paths:
            match = band_pattern.search(path)
            if match:
                band = match.group(1)
                bands.append(band)

        data_arrays_by_band = []
        for path in matched_paths:
            da_band = xr.open_mfdataset(
                path
            ).to_array(dim="time")
            data_arrays_by_band.append(da_band)
        da_doy = xr.concat(data_arrays_by_band, dim="band")
        da_doy = da_doy.assign_coords(band=bands)

        # Reproject and sample
        da_doy = _select_coords(da_doy, epsg=epsg, x=x, y=y, buffer=buffer, buffer_pixels=buffer_pixels)

        data_arrays_by_doy.append(da_doy)

    # Prepare final data array
    da = xr.concat(data_arrays_by_doy, dim="time")
    da = da.assign_coords(time=times)
    da.name = f"modis-12Q{sel}"

    return da

def _load_modis_13a1_061(
        epsg=4326,
        x=None,
        y=None,
        buffer=None,
        buffer_pixels=None
) -> xr.DataArray:
    logger = Logger().get()

    global _MODIS_13A1_CACHE
    if _MODIS_13A1_CACHE is None:
        # List data files
        paths = glob.glob(os.path.join(os.getenv("DATA_ROOT"), "modis-13A1-061", "*.tif"))
        paths = sorted(paths)
        # paths = paths[::20]

        # Sort paths by acquistion date
        doy_pattern = re.compile(f"(MOD|MYD)13A1\\.A(\\d+)\\.")
        times = []
        for path in paths:
            match = doy_pattern.search(path)
            if match:
                doy = match.group(2)
                times.append(int(doy))

        times = np.asarray(times)
        paths = np.asarray(paths)
        sorted_inds = np.argsort(times)
        paths = paths[sorted_inds].tolist()

        # Main loading loop
        data_arrays = []
        times = []
        for ii, path in enumerate(paths):
            logger.info(f"({ii + 1} of {len(paths)}) {path}")
            try:
                da = xr.open_mfdataset(
                    path
                ).to_array(dim="time")
                data_arrays.append(da)

                match = doy_pattern.search(path)
                if match:
                    doy = match.group(2)
                    date = datetime.datetime.strptime(doy, "%Y%j").date()
                    days_since_epoch = (date - datetime.date(1970, 1, 1)).days
                    times.append(days_since_epoch)
            except Exception as e:
                logger.exception(e)

        # Prepare final data array
        logger.info("Concatenating data arrays")
        da = xr.concat(data_arrays, dim="time")
        da = da.assign_coords(time=times, band=_MODIS_13A1_061_BAND_NAMES)
        da.name = "modis-13A1-061"

        _MODIS_13A1_CACHE = da
    else:
        da = _MODIS_13A1_CACHE

    # Attach land cover data
    da = _attach_modis_12q1_061(da, epsg=epsg, x=x, y=y, buffer=buffer, buffer_pixels=buffer_pixels)

    return da

# --- External Functions ---
def load_collection(collection, epsg=4326, x=None, y=None, buffer=None, buffer_pixels=None) -> xr.DataArray:
    load_dotenv()
    match collection:
        case "modis-12Q1-061":
            return _load_modis_12q_061(sel=1, epsg=epsg, x=x, y=y, buffer=buffer, buffer_pixels=buffer_pixels)
        case "modis-12Q2-061":
            return _load_modis_12q_061(sel=2, epsg=epsg, x=x, y=y, buffer=buffer, buffer_pixels=buffer_pixels)
        case "modis-13A1-061":
            return _load_modis_13a1_061(epsg=epsg, x=x, y=y, buffer=buffer, buffer_pixels=buffer_pixels)
        case _:
            raise ValueError(f"Unknown collection: {collection}")
