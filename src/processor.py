import os
import subprocess
from typing import List

import cftime
import freva
import numpy as np
import pandas as pd
import xarray as xr


def find_nc_files(
    experiment: str,
    project: str,
    time_frequency: str,
    variable: str,
    ensemble: str
) -> List[str]:
    """Finds NetCDF files using Freva's databrowser."""
    print("🔍 Searching for NetCDF files with parameters:")
    print(
        f"Experiment: {experiment}, Project: {project}, "
        f"Time Frequency: {time_frequency}, Variable: {variable}, "
        f"Ensemble: {ensemble}"
    )

    results = list(
        freva.databrowser(
            experiment=experiment,
            project=project,
            time_frequency=time_frequency,
            variable=variable,
            ensemble=ensemble,
        )
    )

    if not results:
        print("⚠️ Warning: No files found with the given parameters.")
    else:
        print(f"✅ Found {len(results)} files.")

    return results


def adjust_climatology(
    climatology_file: str, reference_file: str, output_file: str
) -> None:
    """
    Adjusts the climatology file to match the reference file in grid,
    levels, and time axis.
    """
    print(f"📌 Adjusting climatology {climatology_file} to {reference_file}")

    remapped_grid_file = output_file.replace(".nc", "_grid.nc")
    subprocess.run(
        ["cdo", "remapbil," + reference_file, climatology_file,
            remapped_grid_file],
        check=True,
    )
    subprocess.run(
        ["cdo", "ymonmean", remapped_grid_file, output_file],
        check=True,
    )
    os.remove(remapped_grid_file)
    print(f"✅ Adjusted climatology saved as {output_file}")


def subtract_climatology(
    input_file: str, climatology_file: str, output_file: str, variable: str
) -> xr.Dataset:
    """Subtracts the monthly climatology from the input dataset."""
    print(f"📉 Subtracting monthly climatology for {input_file}")

    ds = xr.open_dataset(input_file, decode_times=False)
    clim = xr.open_dataset(climatology_file)

    if "time" not in clim.dims or len(clim.time) != 12:
        raise ValueError("❌ Climatology file must contain 12 mon means.")

    time_var = ds["time"]
    time_units = time_var.attrs["units"]

    if "months since" in time_units:
        base_time_str = time_units.split("since")[-1].strip()
        base_date = pd.to_datetime(base_time_str)
        time_values = [
            base_date + pd.DateOffset(months=int(t)) for t in time_var.values
        ]
        time_values_cftime = [
            cftime.DatetimeProlepticGregorian(t.year, t.month, t.day)
            for t in time_values
        ]
        ds = ds.assign_coords(time=("time", time_values_cftime))

    ds_months = ds["time"].dt.month
    anomalies = np.zeros_like(ds[variable].values)

    for i, month in enumerate(ds_months):
        clim_month = clim[variable].isel(time=month - 1)
        anomalies[i] = ds[variable].isel(time=i).values - clim_month.values

    ds_anomalies = ds.copy()
    ds_anomalies[variable].values = anomalies
    ds_anomalies = ds_anomalies.assign_coords(
        lead_time=("time", np.arange(1, len(ds_anomalies.time) + 1))
    ).drop_vars("time")

    ds.close()
    clim.close()

    return ds_anomalies


def extract_years_from_file(file: str) -> List[int]:
    """Extracts the years from a NetCDF file using `cdo showyear`."""
    try:
        result = subprocess.run(
            ["cdo", "showyear", file],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return list(map(int, result.stdout.strip().split()))
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running `cdo showyear` on {file}: {e.stderr}")
        raise


def process_files(
    experiment: str,
    project: str,
    time_frequency: str,
    variable: str,
    ensemble: str,
    output_file: str,
    climatology_file: str,
    output_dir: str,
    cleanup: bool = False,
) -> None:
    """Processes NetCDF files into a 4D dataset."""
    files = find_nc_files(
        experiment,
        project, time_frequency, variable, ensemble
        )
    if not files:
        print("❌ No NetCDF files found. Exiting.")
        return

    os.makedirs(output_dir, exist_ok=True)
    adjusted_climatology = os.path.join(output_dir, "adjusted_climatology.nc")
    adjust_climatology(climatology_file, files[0], adjusted_climatology)

    anomaly_files, years = [], []
    for file in files:
        anomaly_file = os.path.join(
            output_dir, os.path.basename(file).replace(".nc", "_anomaly.nc")
        )
        ds_anomalies = subtract_climatology(
            file, adjusted_climatology, anomaly_file, variable
        )
        anomaly_files.append(ds_anomalies)
        years.append(extract_years_from_file(file)[0])

    combined_ds = xr.concat(anomaly_files, dim="initialization")
    combined_ds = combined_ds.assign_coords(
        initialization=("initialization", years)
        )
    combined_ds.initialization.attrs["units"] = "year"

    ds_4d = combined_ds.expand_dims(dim={"initialization": len(files)})
    ds_4d = ds_4d.assign_coords(initialization=("initialization", years))
    ds_4d.initialization.attrs["units"] = "year"
    ds_4d.to_netcdf(output_file)
    print(f"✅ Processed data saved to {output_file}")

    if cleanup:
        for file in anomaly_files:
            os.remove(file)
        os.remove(adjusted_climatology)
        print("✅ Intermediate files removed.")
