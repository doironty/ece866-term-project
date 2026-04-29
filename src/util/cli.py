import os
import sys
import re
import pathlib
import logging
import subprocess
import webbrowser
from argparse import ArgumentParser, ArgumentTypeError
from gis.data.mpc import download_modis_13a1_061
from util.logger import Logger

# --- Constants ---
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# --- External Functions ---
def doc_entry():
    """
    Build the Sphinx HTML documentation and open it in the default web browser.

    Runs ``make html`` in the project's ``sphinx/`` directory. If the build
    succeeds, the generated ``index.html`` is opened in a new browser tab.
    If the build fails, the non-zero return code and stderr output are printed
    to the console.

    Notes
    -----
    Registered as a ``[project.scripts]`` entry point in ``pyproject.toml``
    under the name ``doc``.

    Assumes the Sphinx source is located at ``<project_root>/sphinx/`` and
    the built HTML output is at ``<project_root>/doc/sphinx/html/``.
    """
    parser = ArgumentParser(
        description="A tool for generating the project documentation.",
    )
    args = parser.parse_args(sys.argv[1:])

    sphinx_root = os.path.join(_PROJECT_ROOT, "sphinx")
    src_root = os.path.join(_PROJECT_ROOT, "src")

    cmd_line = ["sphinx-apidoc", "-f", "--no-toc", "-o", os.path.join(sphinx_root, "source"), os.path.join(src_root)]
    process = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    for line in process.stdout:
        print(line, end='')
    process.wait()
    if process.returncode != 0:
        print(f"Command failed with return code {process.returncode}.")
        for line in process.stderr:
            print(line, end='')
        return

    for rst in pathlib.Path(sphinx_root).glob("**/*.rst"):
        content = rst.read_text()
        content = re.sub(r"Submodules\n-+\n\n", "", content)
        content = re.sub(r"Module contents\n-+\n\n", "", content)
        rst.write_text(content)

    cmd_line = ["make", "-C", sphinx_root, "html"]
    process = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    for line in process.stdout:
        print(line, end='')
    process.wait()
    if process.returncode != 0:
        print(f"Command failed with return code {process.returncode}.")
        for line in process.stderr:
            print(line, end='')
        return

    file_path = os.path.join(sphinx_root, "build", "html", "index.html")
    if os.path.exists(file_path):
        webbrowser.open_new_tab(f'file://{file_path}')

def fetch_entry():
    """
    CLI entry point for downloading remote sensing data products.

    Parses command-line arguments and dispatches to the appropriate download
    function based on the specified product. A timestamped log file is written
    to the output folder.

    Raises
    ------
    ArgumentTypeError
        If required arguments are missing or cannot be parsed.
    ValueError
        If the specified product is not recognized.

    Notes
    -----
    Registered as a ``[project.scripts]`` entry point in ``pyproject.toml``
    under the name ``fetch``.

    Currently supported products:

    - ``modis-13a1-061`` — MODIS Terra/Aqua Vegetation Indices (500m, 8-day)

    Examples
    --------
    .. code-block:: bash

        fetch -p modis-13a1-061 -g region.geojson -ys 2020 -ye 2023 -o ./data --use-cache
    """
    # Set up arguments
    parser = ArgumentParser(
        description="A tool for downloading data sets for the ECE 866 term project.",
    )
    parser.add_argument(
        "-p", "--product",
        type=str, required=True, action="store", default=None,
        choices=["modis-13a1-061"],
        help="[required] data product to download"
    )
    parser.add_argument(
        "-g", "--geom-file",
        type=str, required=True, action="store", default=None,
        help="[required] full path to geometry file"
    )
    parser.add_argument(
        "-ys", "--start-year",
        type=int, required=True, action="store", default=None,
        help="[required] first year to start searching for data"
    )
    parser.add_argument(
        "-ye", "--end-year",
        type=int, required=True, action="store", default=None,
        help="[required] last year to start searching for data"
    )
    parser.add_argument(
        "-o", "--out-folder",
        type=str, required=False, action="store", default=os.getcwd(),
        help="[optional] folder for storing data"
    )
    parser.add_argument(
        "--use-cache",
        required=False, action="store_true",
        help="[optional] flag indicating whether to use cached data"
    )
    parser.add_argument(
        "--debug",
        required=False, action="store_true",
        help="[optional] flag indicating whether to print debug messages"
    )

    # Parse arguments
    try:
        args = parser.parse_args(sys.argv[1:])
    except SystemExit as e:
        if e.code != 0:
            parser.print_help()
            raise ArgumentTypeError(f"Error parsing arguments: {e}")
        sys.exit(e.code)

    # Unpack arguments
    product = args.product
    geom_file = args.geom_file
    start_year = args.start_year
    end_year = args.end_year
    out_folder = args.out_folder
    use_cache = args.use_cache
    debug = args.debug

    # Set up logger
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    Logger().init(log_dir=out_folder, log_level=log_level)
    logger = Logger().get()

    # Download data
    logger.info(f"Command Line: {" ".join(sys.argv)}")
    if product == "modis-13a1-061":
        download_modis_13a1_061(geom_file, start_year, end_year, out_folder, use_cache=use_cache)
    else:
        raise ValueError(f"Unknown product: {product}")
