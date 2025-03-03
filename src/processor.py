import pandas as pd
import os
import subprocess
from typing import List

import cftime
import freva
import numpy as np
import xarray as xr


def find_nc_files(
    experiment: str,
    project: str, time_frequency: str, variable: str, ensemble: str
) -> List[str]:
    """Finds NetCDF files using Freva's databrowser."""
    print("🔍 Searching for NetCDF files with parameters:")
    print(
        f"   Experiment: {experiment}, Project: {project}",
        f"   Time Frequency: {time_frequency}",
        f"   Variable: {variable}, Ensemble: {ensemble}"
    )

    results = list(
        freva.databrowser(
            experiment=experiment,
            project=project,
            time_frequency=time_frequency,
            variable=variable,
            ensemble=ensemble,
        )
    )  # Convert generator to list

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
    print(
        f"📌 Adjusting climatology {climatology_file}",
        f"   to match {reference_file}")

    # Step 1: Remap to the same grid
    remapped_grid_file = output_file.replace(".nc", "_grid.nc")
    subprocess.run(
        ["cdo", "remapbil," +
            reference_file, climatology_file, remapped_grid_file],
        check=True,
    )

    subprocess.run(["cdo",
                    "ymonmean",
                    remapped_grid_file,
                    output_file],
                   check=True)

    # Cleanup intermediate files
    os.remove(remapped_grid_file)

    print(f"✅ Adjusted climatology saved as {output_file}")


def subtract_climatology(
    input_file: str, climatology_file: str, output_file: str, variable: str
) -> xr.Dataset:
    """
    Subtracts the monthly climatology from the input dataset.
    - Replaces 'time' with 'lead_time' (1 to 122).
    - Returns the anomalies as an xarray Dataset.
    """
    print(f"📉 Subtracting monthly climatology for {input_file}")

    # Load input dataset without decoding times
    ds = xr.open_dataset(input_file, decode_times=False)
    clim = xr.open_dataset(climatology_file)

    # Ensure climatology has exactly 12 time steps (one per month)
    if "time" not in clim.dims or len(clim.time) != 12:
        raise ValueError(
            "❌ Climatology file must contain exactly 12 monthly means.")

    # 🔥 **Manually decode time axis** 🔥
    time_var = ds["time"]
    time_units = time_var.attrs["units"]

    if "months since" in time_units:
        print(f"🕒 Manually fixing 'months since' format in {input_file}")

        # Extract base date
        base_time_str = time_units.split("since")[-1].strip()
        # Use Pandas for flexible parsing
        base_date = pd.to_datetime(base_time_str)

        # Compute new datetime values
        time_values = [
            base_date + pd.DateOffset(months=int(t)) for t in time_var.values
        ]

        # Convert to cftime datetime objects
        time_values_cftime = [
            cftime.DatetimeProlepticGregorian(t.year, t.month, t.day)
            for t in time_values
        ]

        # Assign fixed time axis to dataset
        ds = ds.assign_coords(time=("time", time_values_cftime))

    # ✅ Now `.dt` will work!
    ds_months = ds["time"].dt.month

    # Create an empty array to store the anomalies
    anomalies = np.zeros_like(ds[variable].values)

    # Loop over each time step in the input dataset
    for i, month in enumerate(ds_months):
        # Find the corresponding climatology month
        clim_month = clim[variable].isel(
            time=month - 1
        )  # Climatology time is 0-indexed (Jan=0, Feb=1, etc.)

        # Subtract the climatology month from the current time step
        anomalies[i] = ds[variable].isel(time=i).values - clim_month.values

    # Create a new dataset for the anomalies
    ds_anomalies = ds.copy()
    ds_anomalies[variable].values = anomalies

    # 🔥 Convert absolute time to 'lead_time' (1 to 122)
    ds_anomalies = ds_anomalies.assign_coords(
        lead_time=("time", np.arange(1, len(ds_anomalies.time) + 1))
    ).drop_vars("time")

    # Close datasets
    ds.close()
    clim.close()

    return ds_anomalies


def reorganize_to_4d(
    ds: xr.Dataset, variable: str, n_initializations: int, n_lead_times: int
) -> xr.Dataset:
    """
    Reorganizes a 3D dataset (time, lat, lon) into a 4D dataset
     (initialization, lead_time, lat, lon).
    - `n_initializations` is the number of files (initializations).
    - `n_lead_times` is the length of the time dimension in each file.
    """
    # Debug: Print the dimensions of the input dataset
    print(f"📊 Input dataset dimensions: {ds.dims}")
    print(f"📊 Input dataset shape: {ds[variable].shape}")

    # Reshape the data into 4D
    try:
        data_4d = ds[variable].values.reshape(
            n_initializations, n_lead_times, ds.lat.size, ds.lon.size
        )
    except ValueError as e:
        print(f"❌ Reshaping failed: {e}")
        print(
            f"❌ Expected shape: ({n_initializations}",
            f" {n_lead_times}, {ds.lat.size}, {ds.lon.size})"
        )
        print(f"❌ Actual size: {ds[variable].values.size}")
        raise

    # Create new coordinates
    initializations = np.arange(n_initializations)
    lead_times = np.arange(n_lead_times)

    # Create the 4D dataset
    ds_4d = xr.Dataset(
        {variable: (("initialization", "lead_time", "lat", "lon"), data_4d)},
        coords={
            "initialization": initializations,
            "lead_time": lead_times,
            "lat": ds.lat,
            "lon": ds.lon,
        },
    )

    return ds_4d


def extract_years_from_file(file: str) -> List[int]:
    """
    Extracts the years from a NetCDF file using `cdo showyear`.
    """
    try:
        # Run `cdo showyear` and capture the output
        result = subprocess.run(
            ["cdo", "showyear", file],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # Parse the output into a list of integers
        years = list(map(int, result.stdout.strip().split()))
        return years
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
    """
    Processes NetCDF files into a 4D dataset
    (initialization, lead_time, lat, lon),
    ensuring climatology is correctly adjusted before subtraction.
    """
    files = find_nc_files(
        experiment,
        project,
        time_frequency,
        variable,
        ensemble)
    if not files:
        print("❌ No NetCDF files found. Exiting.")
        return

    os.makedirs(output_dir, exist_ok=True)

    adjusted_climatology = os.path.join(output_dir, "adjusted_climatology.nc")
    adjust_climatology(climatology_file, files[0], adjusted_climatology)

    anomaly_files = []
    years = []  # List to store the extracted years
    for file in files:
        anomaly_file = os.path.join(
            output_dir, os.path.basename(file).replace(".nc", "_anomaly.nc")
        )
        ds_anomalies = subtract_climatology(
            file, adjusted_climatology, anomaly_file, variable
        )

        # Debug: Print number of time steps in each file
        print(f"📊 {file} has {len(ds_anomalies.time)} time steps")

        anomaly_files.append(ds_anomalies)

        # Extract the years from the file using `cdo showyear`
        file_years = extract_years_from_file(file)
        # Use the first year as the initialization year
        years.append(file_years[0])

    # Debug: Print the extracted years
    print(f"📊 Extracted years: {years}")

    # Check if all files have the same number of time steps
    unique_time_steps = {len(ds.time) for ds in anomaly_files}
    print(f"📊 Unique time step counts in anomaly files: {unique_time_steps}")

    if len(unique_time_steps) > 1:
        print("❌ Warning: Not all files have the same number of time steps!")
        for i, ds in enumerate(anomaly_files):
            print(f"File {i}: {len(ds.time)} time steps")

    # Combine all anomaly datasets into a single dataset along a new
    # initialization dimension
    combined_ds = xr.concat(anomaly_files, dim="initialization")

    # Replace the default initialization values (0 to 9) with the actual years
    # (1970 to 1979)
    combined_ds = combined_ds.assign_coords(
        initialization=("initialization", years))

    # Debug: Print the updated initialization values after assignment
    print(
        f"📊 Updated initialization values:"
        f" {combined_ds.initialization.values}")

    # Assign units to the initialization coordinate
    combined_ds.initialization.attrs["units"] = "year"

    # Debug: Print the dimensions of the combined dataset
    print(f"📊 Combined dataset dimensions: {combined_ds.dims}")
    print(f"📊 Combined dataset shape: {combined_ds[variable].shape}")

    # Get the number of initializations and lead times
    # Number of files = number of initializations
    n_initializations = len(files)
    n_lead_times = len(
        anomaly_files[0].time
    )  # Number of lead times (time steps per file)

    # Reorganize into 4D structure
    ds_4d = reorganize_to_4d(
        combined_ds,
        variable,
        n_initializations,
        n_lead_times)

    # Ensure the initialization dimension is set to the years (1970 to 1979)
    ds_4d = ds_4d.assign_coords(initialization=("initialization", years))

    # Assign units to the initialization coordinate in the final dataset
    ds_4d.initialization.attrs["units"] = "year"

    # Ensure `initialization` is a coordinate variable
    ds_4d = ds_4d.set_coords("initialization")

    # Debug: Print the final initialization values and units
    print(f"📊 Final initialization values: {ds_4d.initialization.values}")
    print(
        "📊 Final initialization units",
        f" : {ds_4d.initialization.attrs.get('units', 'N/A')}"
    )

    # Save the result
    ds_4d.to_netcdf(output_file)
    print(f"✅ Processed data saved to {output_file}")

    if cleanup:
        print("🧹 Cleaning up intermediate files...")
        for file in anomaly_files:
            os.remove(file)
        os.remove(adjusted_climatology)
        print("✅ Intermediate files removed.")
