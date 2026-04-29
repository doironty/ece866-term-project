# --- Imports ---
import os
import re
import requests
import time
import logging
import numpy as np
import geopandas as gpd
import planetary_computer
import pystac
import pystac_client
import stackstac
from datetime import datetime
from planetary_computer import sign
from PIL import Image
from io import BytesIO
from gis.geometry import load_geom, to_bbox
from util.logger import Logger
# noinspection PyUnusedImports
import rioxarray

# --- Private Functions ---
def _get_catalog(sign_inplace=False) -> pystac_client.Client:
    """
    Open and return the Microsoft Planetary Computer STAC catalog.

    sign_inplace : bool, optional
        If ``True``, sign retrieved objects in place. Default is ``False``.

    Returns
    -------
    pystac_client.Client
        STAC client connected to the Planetary Computer catalog.
    """
    kwargs = dict()
    if sign_inplace:
        kwargs["modifier"] = planetary_computer.sign_inplace

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        **kwargs
    )
    return catalog

def _get_collections(
        catalog : pystac_client.Client,
        match : str=None
) -> dict[str, pystac.Collection]:
    """
    Retrieve collections from a STAC catalog, optionally filtered by a substring match.

    Parameters
    ----------
    catalog : pystac_client.Client
        An open STAC client from which to fetch collections.
    match : str, optional
        Substring to filter collection IDs. Only collections whose ID contains
        this string are returned. If ``None``, all collections are returned.

    Returns
    -------
    dict of str to pystac.Collection
        Dictionary mapping collection ID to its corresponding STAC Collection object.
    """
    collection_search = catalog.get_collections()
    collections = dict()
    for collection in collection_search:
        if match is not None:
            if match not in collection.id:
                continue
        collections[collection.id] = collection
    return collections

def _get_signed_item(
        collection : str,
        item : pystac.Item,
        catalog : pystac_client.Client=None
) -> pystac.Item:
    """
    Resign a single STAC item from the Microsoft Planetary Computer catalog.

    Parameters
    ----------
    collection : str
        STAC collection ID (e.g. ``"modis-13A1-061"``).
    item : pystac.Item
        STAC item to resign.
    catalog : pystac_client.Client
        STAC catalog to fetch the item from. If a catalog is not provided, a
        new one will be created. Default is ``None``.

    Returns
    -------
    pystac.Item
        The requested STAC item, resigned for authenticated access.
    """
    if catalog is None:
        catalog = _get_catalog()
    item = catalog.get_collection(collection).get_item(item.id)
    item = planetary_computer.sign(item)
    return item

def _search_collections(
        collections : list[str],
        bbox : list[float],
        start_year : int,
        end_year : int,
        return_catalog: bool=False
) -> list[pystac.Item] | tuple[list[pystac.Item], pystac_client.Client]:
    """
    Search the Planetary Computer STAC catalog for items matching the given collections,
    bounding box, and date range.

    Parameters
    ----------
    collections : list of str
        STAC collection IDs to search (e.g. ``["modis-13A1-061"]``).
    bbox : list of float
        Bounding box as ``[minx, miny, maxx, maxy]`` in EPSG:4326.
    start_year : int
        Start year of the search range (inclusive).
    end_year : int
        End year of the search range (inclusive).
    return_catalog : bool, optional
        If ``True``, also return the catalog. Default is ``False``.

    Returns
    -------
    list of pystac.Item
        List of STAC items matching the search criteria.
    pystac_client.Client
        STAC client connected to the Planetary Computer catalog.
    """
    catalog = _get_catalog()
    datetime_ = f"{start_year}/{end_year}"
    search = catalog.search(
        collections=collections,
        bbox=bbox,
        datetime=datetime_,
    )
    item_collection = search.item_collection()

    items = []
    for item in item_collection:
        items.append(item)
    if return_catalog:
        return items, catalog
    return items

def _download_with_retry(
        catalog : pystac_client.Client,
        entry,
        gdf : gpd.GeoDataFrame,
        bounds : tuple[float, float, float, float],
        resolution : tuple[int | float, int | float],
        out_path : str,
        logger : logging.Logger,
        max_retries=5,
        backoff=5
):
    """
    Clip and write a raster to disk, retrying on transient read errors.

    Parameters
    ----------
    catalog : pystac_client.Client
        STAC client connected to the Planetary Computer catalog.
    entry : numpy.ndarray of dtype([('satellite', 'U5'),
    ('date', 'datetime64[D]'), ('tile', 'U6'), ('item', object)])
        Data entry containing item object associated metadata.
    gdf : geopandas.GeoDataFrame
        GeoDataFrame whose geometry is used to clip the raster.
    bounds : tuple[float, float, float, float]
        Output spatial bounding-box, as a tuple of (min_x, min_y, max_x, max_y).
        This defines the (west, south, east, north) rectangle the output array
        will cover. Values must be in the same coordinate reference system as
        epsg.
    resolution : tuple[int | float, int | float]
        Output resolution. Careful: this must be given in the output CRS's
        units! For example, with epsg=4326 (meaning lat-lon), the units are
        degrees of latitude/longitude, not meters. Giving resolution=20 in that
        case would mean each pixel is 20ºx20º (probably not what you wanted).
        You can also give a pair of (x_resolution, y_resolution).
    out_path : str
        Output file path for the written GeoTIFF.
    logger : logging.Logger
        Logger instance for warnings on retry attempts.
    max_retries : int, optional
        Maximum number of attempts before re-raising the exception. Default is 5.
    backoff : int, optional
        Base number of seconds to wait between retries. Wait time scales
        linearly as ``backoff * attempt``. Default is 5.
    """
    for attempt in range(1, max_retries + 1):
        try:
            item = entry["item"]
            item = _get_signed_item("modis-13A1-061", item, catalog=catalog)

            da = stackstac.stack(
                [item],
                epsg=4326,
                bounds=bounds,
                resolution=resolution,
            ).squeeze("time")
            logger.debug(f"Data shape: {da.shape}")
            clipped = da.rio.clip(gdf.geometry, crs=gdf.crs)
            clipped.rio.to_raster(out_path)
            return
        except RuntimeError as e:
            if "RasterioIOError" in str(e) and attempt < max_retries:
                wait = backoff * attempt
                logger.warning(
                    f"Transient read error on attempt {attempt}/{max_retries}. "
                    f"Retrying in {wait}s...\n{e}"
                )
                time.sleep(wait)
            else:
                logger.exception(f"Unhandled exception: {e}")

def _save_image(
        item : pystac.Item,
        out_file : str
):
    """
        Write an items rendered preview to a PNG file.

        Parameters
        ----------
        item : pystac.Item
            Item whose rendered preview is written to the output file.
        out_file : str
            Output file path for the written PNG.
        """
    url = item.assets["rendered_preview"].href
    url = sign(url)
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    image.save(out_file)

# --- External Functions ---
def download_modis_13a1_061(
        geom_file : str | gpd.GeoDataFrame,
        start_year : int,
        end_year : int,
        out_folder : str=None,
        use_cache : bool=True
):
    """
    Download MODIS 13A1 (NDVI/EVI) and paired 09A1 (surface reflectance preview)
    products from the Microsoft Planetary Computer for a given geometry and date range.

    For each MODIS 13A1 item found, a clipped GeoTIFF is saved. A matching 09A1
    rendered preview PNG is also saved when a corresponding item is available.

    Parameters
    ----------
    geom_file : str or gpd.GeoDataFrame
        Path to a vector file or an existing GeoDataFrame defining the area of interest.
    start_year : int
        Start year of the download range (inclusive).
    end_year : int
        End year of the download range (inclusive).
    out_folder : str, optional
        Root directory for output files. Defaults to the current working directory.
    use_cache : bool, optional
        If ``True``, skips downloading files that already exist on disk. Default is ``True``.

    Notes
    -----
    Output files are written to ``<out_folder>/modis-13A1-061/<item_id>.tif`` and
    ``<out_folder>/modis-13A1-061/<item_id>.png``.

    Both Terra (MOD) and Aqua (MYD) satellites are supported. The 09A1 preview
    is matched to each 13A1 item by satellite, date, and tile.
    """
    # Set up logger
    logger = Logger().get()

    # Set output folder
    if out_folder is None:
        out_folder = os.getcwd()

    # Load geometry
    gdf = load_geom(geom_file)
    bbox = to_bbox(gdf)

    # Search collection
    logger.info("Searching the modis-13A1-061 collection")
    items, catalog = _search_collections(["modis-13A1-061", "modis-09A1-061"], bbox, start_year, end_year, return_catalog=True)

    dtype = np.dtype([
        ("satellite", "U5"),
        ("date", "datetime64[D]"),
        ("tile", "U6"),
        ("item", object),
    ])
    items_13a1 = []
    items_09a1 = []
    for item in items:
        pattern = r"^M(OD|YD)(\w+)\.A(\d{4})(\d{3})\.(h\d{2}v\d{2})\."
        match = re.search(pattern, item.id)
        if match:
            satellite = "Terra" if match.group(1) == "OD" else "Aqua"
            product = match.group(2)
            date = datetime.strptime(match.group(3) + match.group(4), "%Y%j")
            tile = match.group(5)

            if product == "13A1":
                items_13a1.append(
                    np.array(
                        [
                            (satellite, np.datetime64(date, "D"), tile, item)
                        ],
                        dtype=dtype
                    )
                )
            elif product == "09A1":
                items_09a1.append(
                    np.array(
                        [
                            (satellite, np.datetime64(date, "D"), tile, item)
                        ],
                        dtype=dtype
                    )
                )
    items_13a1 = np.stack(items_13a1).flatten()
    items_09a1 = np.stack(items_09a1).flatten()
    logger.info(f"Found {len(items_13a1)} items")

    # Build reference stack just to get the common spatial extent
    ref_stack = stackstac.stack(
        items_13a1["item"].tolist(),
        epsg=4326,
    )
    ref_bounds = ref_stack.spec.bounds
    ref_resolution = ref_stack.spec.resolutions_xy

    for ii, entry in enumerate(items_13a1):
        logger.info(f"({ii + 1} of {items_13a1.size}) Downloading {entry['item'].id}")

        out_name = os.path.join(out_folder, "modis-13A1-061", f"{entry['item'].id}")
        os.makedirs(os.path.dirname(out_name), exist_ok=True)

        if use_cache and os.path.exists(f"{out_name}.tif"):
            logger.info(f"Skipping: Raster data already exists")
        else:
            try:
                _download_with_retry(catalog, entry, gdf, ref_bounds, ref_resolution, f"{out_name}.tif", logger)
            except Exception as e:
                logger.exception(f"Unhandled exception: {e}")

        if use_cache and os.path.exists(f"{out_name}.png"):
            logger.info(f"Skipping: Image data already exists")
        else:
            entry_09a1 = items_09a1[
                (items_09a1["satellite"] == entry["satellite"]) &
                (items_09a1["date"] == entry["date"]) &
                (items_09a1["tile"] == entry["tile"])
            ]
            if entry_09a1.size == 1:
                try:
                    item_09a1 = entry_09a1["item"][0]
                    item_09a1 = _get_signed_item("modis-09A1-061", item_09a1, catalog=catalog)

                    _save_image(item_09a1, f"{out_name}.png")
                except Exception as e:
                    logger.exception(f"Unhandled exception: {e}")
            else:
                logger.warning(f"{entry_09a1.size} 09A1 products found for this item")
