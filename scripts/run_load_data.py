"""Script for loading and conditioning data."""
# --- Imports ---
import json
import os
import numpy as np
from scipy.io import savemat
import xarray as xr
from util.logger import Logger
from gis.data.io import load_collection
from gis.data.conditioning import condition_data

# --- Constants ---
STUDY_SITES = "/Users/tdoiron/Library/CloudStorage/OneDrive-Personal/Sandbox/msu/ece866/term-project/data/study_sites.json"

def load_data(site_id, site):
    # --- Load Data ---
    da = load_cache(site_id)
    if da is None:
        lat = site["coordinate"][0]
        lon = site["coordinate"][1]

        da = load_collection("modis-13A1-061", x=lon, y=lat, buffer_pixels=1)

        logger.info(f"Saving data")
        save_cache(site_id, da)
    return da

def save_cache(site_id, data, overwrite=False):
    data = data.compute()

    npz_file = f"site{site_id}_raw.npz"
    if not os.path.exists(npz_file) or overwrite:
        np.savez_compressed(
            npz_file,
            data=data.values,
            dims=np.array(data.dims),
            **{f"coord_{k}": v.values for k, v in data.coords.items()}
        )

    mat_file = f"site{site_id}_raw.mat"
    if not os.path.exists(mat_file) or overwrite:
        data_dict = dict()
        data_dict["data"] = data.values
        data_dict["dims"] = data.dims
        data_dict["coords"] = {k: v.values for k, v in data.coords.items()}
        savemat(mat_file, data_dict)

def load_cache(site_id):
    npz_file = f"site{site_id}_raw.npz"
    if os.path.exists(npz_file):
        loaded = np.load(npz_file, allow_pickle=True)
        data = xr.DataArray(
            loaded["data"],
            dims=list(loaded["dims"]),
            coords={k[6:]: loaded[k] for k in loaded if k.startswith("coord_")}
        )
        return data
    else:
        return None

def load_modis_13a1(sites):
    for ii, site in enumerate(sites):
        site_id = ii + 1
        logger.info(f"Loading 'modis-13A1-061' collection for site {site_id}")

        # --- Load Data ---
        da = load_data(site_id, site)

        # --- Condition Data ---
        grid_spacing = 8
        evi, ndvi = condition_data(da, grid_spacing_days=grid_spacing)

        evi = evi.compute()
        evi_time = evi.time.values
        evi_data = evi.data[:]
        savemat(
            f"site{site_id}_evi.mat",
            {
                "t": evi_time,
                "x": evi_data,
                "Ts": grid_spacing,
                "L": len(evi)
            }
        )

        ndvi = ndvi.compute()
        ndvi_time = ndvi.time.values
        ndvi_data = ndvi.data[:]
        savemat(
            f"site{site_id}_ndvi.mat",
            {
                "t": ndvi_time,
                "x": ndvi_data,
                "Ts": grid_spacing,
                "L": len(ndvi)
            }
        )

def load_modis_12q2(sites):
    for ii, site in enumerate(sites):
        site_id = ii + 1
        logger.info(f"Loading 'modis-12Q2-061' collection for site {site_id}")

        # --- Load Data ---
        lat = site["coordinate"][0]
        lon = site["coordinate"][1]
        da = load_collection("modis-12Q2-061", x=lon, y=lat, buffer_pixels=1)

        num_cycles = da.sel(band="NumCycles").mean(dim=["x", "y"]).round(0).compute()
        greenup = da.sel(band="Greenup_0").mean(dim=["x", "y"]).round(0).compute()
        greenup_mid = da.sel(band="MidGreenup_0").mean(dim=["x", "y"]).round(0).compute()
        maturity = da.sel(band="Maturity_0").mean(dim=["x", "y"]).round(0).compute()
        peak = da.sel(band="Peak_0").mean(dim=["x", "y"]).round(0).compute()
        senescensce = da.sel(band="Senescence_0").mean(dim=["x", "y"]).round(0).compute()
        greendown_mid = da.sel(band="MidGreendown_0").mean(dim=["x", "y"]).round(0).compute()
        dormancy = da.sel(band="Dormancy_0").mean(dim=["x", "y"]).round(0).compute()

        savemat(
            f"site{site_id}_modis_12q2.mat",
            {
                "num_cycles": num_cycles,
                "greenup": greenup,
                "greenup_mid": greenup_mid,
                "maturity": maturity,
                "peak": peak,
                "senescence": senescensce,
                "greendown_mid": greendown_mid,
                "dormancy": dormancy
            }
        )

if __name__ == "__main__":
    Logger().init(write_file=False)
    logger = Logger().get()

    with open(STUDY_SITES, "r") as f:
        json_data = json.load(f)
    study_sites = json_data["sites"]
    
    load_modis_13a1(study_sites)
    load_modis_12q2(study_sites)
