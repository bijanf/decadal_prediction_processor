import numpy as np
import pandas as pd
import pytest
import xarray as xr

from src.processor import process_files  # Ensure correct import


@pytest.mark.parametrize(
    "experiment, project, time_frequency, variable, ensemble",
    [("dkfen4197*", "comingdecade", "mon", "tas", "r26i2p1")],
)
def test_process_files(
    tmp_path, experiment, project, time_frequency, variable, ensemble
):
    """
    Test the `process_files` function by creating temporary NetCDF files with
    synthetic data, running the function, and verifying output.
    """

    # Define temporary file paths
    file1 = tmp_path / "tas_Amon_MPI-ESM-LR_dkfen42019_r7i2p1_201911-203912.nc"
    file2 = tmp_path / "tas_Amon_MPI-ESM-LR_dkfen42018_r7i2p1_201811-203812.nc"
    output_file = tmp_path / "output.nc"

    # Create synthetic time variables (ensure no overlapping)
    time1 = pd.date_range("2019-11-01", periods=24, freq="M")
    time2 = pd.date_range("2021-11-01", periods=24, freq="M")

    # Create dummy datasets with random values and coordinates
    ds1 = xr.Dataset(
        {"tas": (["time", "lat", "lon"], np.random.rand(24, 10, 10))},
        coords={
            "time": time1,
            "lat": np.linspace(-90, 90, 10),
            "lon": np.linspace(0, 360, 10),
        },
    )
    ds2 = xr.Dataset(
        {"tas": (["time", "lat", "lon"], np.random.rand(24, 10, 10))},
        coords={
            "time": time2,
            "lat": np.linspace(-90, 90, 10),
            "lon": np.linspace(0, 360, 10),
        },
    )

    # Save datasets as NetCDF files
    ds1.to_netcdf(file1)
    ds2.to_netcdf(file2)

    # Run the `process_files` function
    process_files(
        experiment,
        project, time_frequency, variable, ensemble, str(output_file)
    )

    # Open and verify output dataset
    output_ds = xr.open_dataset(output_file)

    # ✅ Assertions to check output integrity
    assert (
        "initialization_year" in output_ds.dims
    ), "Missing 'initialization_year' dimension"
    assert (
        "lead_time" in output_ds.coords or "lead_year" in output_ds.coords
    ), "Missing 'lead_time' or 'lead_year' coordinate"
    assert "tas" in output_ds.variables, "Missing 'tas' variable"

    # Check dataset size
    assert output_ds["time"].size > 0, "Time dimension is empty"
    assert output_ds["lat"].size == 10, "Latitude dimension is incorrect"
    assert output_ds["lon"].size == 10, "Longitude dimension is incorrect"

    # Ensure lead years are correctly computed
    assert (output_ds["lead_year"].values >= 1).all(), "years should be +"

    print("✅ Test passed successfully!")
