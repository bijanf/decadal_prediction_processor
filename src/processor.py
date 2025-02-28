import xarray as xr
import numpy as np
import os
import glob
from typing import List

def find_nc_files(input_dir: str) -> List[str]:
    """
    Recursively finds all .nc files in the input directory and its subdirectories.

    Args:
        input_dir (str): Directory containing input NetCDF files.

    Returns:
        List[str]: List of paths to .nc files.
    """
    nc_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".nc"):
                nc_files.append(os.path.join(root, file))
    return nc_files

def process_files(input_dir: str, output_file: str) -> None:
    """
    Processes decadal prediction files and saves the output with additional dimensions.

    Args:
        input_dir (str): Directory containing input NetCDF files.
        output_file (str): Path to save the output NetCDF file.
    """
    # Find all .nc files recursively
    files = find_nc_files(input_dir)

    # Open all files as a single dataset
    ds = xr.open_mfdataset(files, combine="by_coords")

    # Extract initialization year from the filenames
    initialization_years = [int(os.path.basename(f).split("dkfen4")[1][:4]) for f in files]

    # Add initialization_year as a new dimension
    ds["initialization_year"] = xr.DataArray(initialization_years, dims="initialization_year")

    # Calculate lead_year based on time and initialization_year
    ds["lead_year"] = (ds["time"].dt.year - ds["initialization_year"]) + 1

    # Select the required variables and dimensions
    output_ds = ds[["tas"]].assign_coords({
        "lead_year": ds["lead_year"],
        "initialization_year": ds["initialization_year"]
    })

    # Save the output to a new NetCDF file
    output_ds.to_netcdf(output_file)
    print(f"Output saved to {output_file}")