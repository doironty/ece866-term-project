# --- Imports ---
import geopandas as gpd

# --- External Functions ---
def load_geom(
        geom : str | gpd.GeoDataFrame,
        crs : str="EPSG:4326"
) -> gpd.GeoDataFrame:
    """
    Load geometry from a file path or geopandas.GeoDataFrame and reproject to a target CRS.

    Parameters
    ----------
    geom : str or geopandas.GeoDataFrame
        Path to a vector file (e.g. GeoJSON, Shapefile) or an existing GeoDataFrame.
    crs : str, optional
        Target coordinate reference system. Default is ``"EPSG:4326"``.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame reprojected to the specified CRS.
    """
    if isinstance(geom, gpd.GeoDataFrame):
        gdf = geom
    else:
        gdf = gpd.read_file(geom)
    gdf = gdf.to_crs(crs)
    return gdf

def to_bbox(
        gdf : gpd.GeoDataFrame
) -> list:
    """
    Extract the bounding box of a geopandas.GeoDataFrame as a flat list.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        GeoDataFrame from which to compute the bounding box.

    Returns
    -------
    list
        Bounding box as ``[minx, miny, maxx, maxy]``.
    """
    bbox = gdf.bounds.values.flatten().tolist()
    return bbox
