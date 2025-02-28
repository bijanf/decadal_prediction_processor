import pytest
import xarray as xr
import numpy as np
import pandas as pd
from src.processor import process_files

def test_process_files(tmp_path):
    # Create dummy NetCDF files
    file1 = tmp_path / "tas_Amon_MPI-ESM-LR_dkfen42019_r7i2p1_201911-203912.nc"
    file2 = tmp_path / "tas_Amon_MPI-ESM-LR_dkfen42018_r7i2p1_201811-203812.nc"

    # Create dummy data
    ds1 = xr.Dataset(
        {"tas": (["time", "lat", "lon"], np.random.rand(24, 10, 10))},
        coords={"time": pd.date_range("2019-11-01", periods=24, freq="M")}
    )
    ds2 = xr.Dataset(
        {"tas": (["time", "lat", "lon"], np.random.rand(24, 10, 10))},
        coords={"time": pd.date_range("2018-11-01", periods=24, freq="M")}
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
    assert "lead_year" in output_ds.dims
    assert "tas" in output_ds.variables