import glob
import os
from typing import List

import numpy as np
import pandas as pd
import xarray as xr

from src.processor import process_files  # Correct import


def test_process_files(tmp_path):
    # Create dummy NetCDF files
    file1 = tmp_path / "tas_Amon_MPI-ESM-LR_dkfen42019_r7i2p1_201911-203912.nc"
    file2 = tmp_path / "tas_Amon_MPI-ESM-LR_dkfen42018_r7i2p1_201811-203812.nc"

    # Create dummy data with non-overlapping time coordinates
    time1 = pd.date_range("2019-11-01", periods=24, freq="ME")  # 2019-11 to 2021-10
    time2 = pd.date_range("2021-11-01", periods=24, freq="ME")  # 2021-11 to 2023-10

    ds1 = xr.Dataset(
        {"tas": (["time", "lat", "lon"], np.random.rand(24, 10, 10))},
        coords={"time": time1},
    )
    ds2 = xr.Dataset(
        {"tas": (["time", "lat", "lon"], np.random.rand(24, 10, 10))},
        coords={"time": time2},
    )

    # Save dummy data to files
    ds1.to_netcdf(file1)
    ds2.to_netcdf(file2)

    # Process files
    output_file = tmp_path / "output.nc"
    process_files(str(tmp_path), str(output_file))

    # Verify output
    output_ds = xr.open_dataset(output_file)
    assert "initialization_year" in output_ds.dims
    assert "lead_year" in output_ds.coords  # Check if lead_year is a coordinate
    assert "tas" in output_ds.variables
