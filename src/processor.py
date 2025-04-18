import os
import subprocess
from typing import List

import cftime
import freva
import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm


def shift_initialization_time(nc_file: str, output_file: str) -> None:
    """
    Shifts the initialization time from January (01) to November (11)
    in a NetCDF file.
    """
    print(f"🔄 Shifting initialization time in {nc_file}")

    ds = xr.open_dataset(nc_file)

    if "initialization" in ds.coords:
        # Convert initialization years to full dates (YYYY-01-01)
        init_years = ds["initialization"].values
        init_dates = pd.to_datetime([f"{year}-01-01" for year in init_years])

        # Shift by -2 months (from January to November of previous year)
        shifted_dates = init_dates - pd.DateOffset(months=2)

        # Convert back to CFTime objects for NetCDF compatibility
        shifted_dates_cftime = [
            cftime.DatetimeProlepticGregorian(date.year, date.month, date.day)
            for date in shifted_dates
        ]

        # Assign the shifted values
        ds = ds.assign_coords(
            initialization=("initialization", shifted_dates_cftime)
        )

        # Save the modified dataset
        ds.to_netcdf(output_file)
        print(f"✅ Shifted initialization times saved to {output_file}")

    else:
        print("⚠️ No 'initialization' coordinate found in the dataset!")

    ds.close()


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
    print(
        f"📌 Adjusting climatology {climatology_file}",
        f"   to match {reference_file}")

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

    os.remove(remapped_grid_file)

    print(f"✅ Adjusted climatology saved as {output_file}")


def subtract_climatology(
    input_file: str, climatology_file: str, output_file: str, variable: str
) -> xr.Dataset:
    """
    Subtracts the monthly climatology from the input dataset.
    - Replaces 'time' with 'lead_time' (1 to 122).
    - Adjusts the time axis to start from November (YYYY-11-01).
    - Returns the anomalies as an xarray Dataset.
    """
    print(f"📉 Subtracting monthly climatology for {input_file}")

    ds = xr.open_dataset(input_file, decode_times=False)
    clim = xr.open_dataset(climatology_file)

    if "time" not in clim.dims or len(clim.time) != 12:
        raise ValueError(
            "❌ Climatology file must contain exactly 12 monthly means.")

    time_var = ds["time"]
    time_units = time_var.attrs["units"]

    if "months since" in time_units:
        print(f"🕒 Manually fixing 'months since' format in {input_file}")

        base_time_str = time_units.split("since")[-1].strip()
        base_date = pd.to_datetime(base_time_str)

        # Adjust the base date to start from November (YYYY-11-01)
        base_date = base_date.replace(month=11, day=1)

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
    
    # Add progress bar for climatology subtraction
    print("\n🔄 Subtracting climatology for each timestep:")
    for i, month in enumerate(tqdm(ds_months, desc="Processing timesteps", unit="step")):
        clim_month = clim[variable].isel(
            time=month - 1  # Climatology file is assumed to have months 1-12
        )
        anomalies[i] = ds[variable].isel(time=i).values - clim_month.values

    ds_anomalies = ds.copy()
    ds_anomalies[variable].values = anomalies

    # Replace 'time' with 'lead_time' (1 to 122)
    ds_anomalies = ds_anomalies.assign_coords(
        lead_time=("time", np.arange(1, len(ds_anomalies.time) + 1))
    ).drop_vars("time")

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
    print(f"📊 Input dataset dimensions: {ds.dims}")
    print(f"📊 Input dataset shape: {ds[variable].shape}")

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

    initializations = np.arange(n_initializations)
    lead_times = np.arange(n_lead_times)

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
        result = subprocess.run(
            ["cdo", "showyear", file],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        years = list(map(int, result.stdout.strip().split()))
        return years
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running `cdo showyear` on {file}: {e.stderr}")
        raise


def find_nc_files_manual(directory: str, pattern: str = "*.nc") -> List[str]:
    """Finds NetCDF files in a directory manually.
    
    Args:
        directory: Path to the directory containing NetCDF files
        pattern: File pattern to match (default: "*.nc")
        
    Returns:
        List of file paths
    """
    print(f"🔍 Searching for NetCDF files in directory: {directory}")
    
    import glob
    import os
    
    # Ensure the path ends with a separator
    directory = os.path.join(directory, "")
    
    # Find all matching files
    search_pattern = os.path.join(directory, pattern)
    results = glob.glob(search_pattern)
    
    if not results:
        print("⚠️ Warning: No files found in the given directory.")
    else:
        print(f"✅ Found {len(results)} files.")
    
    return sorted(results)


def process_files(
    output_file: str,
    output_dir: str,
    cleanup: bool = False,
    # Freva search parameters (optional)
    experiment: str = None,
    project: str = None,
    time_frequency: str = None,
    variable: str = None,
    ensemble: str = None,
    # Manual directory search parameters (optional)
    input_directory: str = None,
    file_pattern: str = "*.nc",
    # Climatology parameters (optional)
    climatology_file: str = None,
    subtract_clim: bool = True,
) -> None:
    """
    Processes NetCDF files into a 4D dataset (initialization, lead_time, lat, lon).
    Files can be found either using Freva databrowser or by specifying a directory.
    Climatology subtraction is optional.

    Args:
        output_file: Path to save the final processed file
        output_dir: Directory to store intermediate files
        cleanup: Whether to remove intermediate files
        experiment: (Freva) Experiment name
        project: (Freva) Project name
        time_frequency: (Freva) Time frequency
        variable: (Freva) Variable name
        ensemble: (Freva) Ensemble member
        input_directory: Directory containing NetCDF files (for manual search)
        file_pattern: Pattern to match files when using manual search
        climatology_file: Path to climatology file (required if subtract_clim=True)
        subtract_clim: Whether to subtract climatology (default: True)
    """
    # Find input files
    if input_directory is not None:
        files = find_nc_files_manual(input_directory, file_pattern)
    elif all([experiment, project, time_frequency, variable, ensemble]):
        files = find_nc_files(
            experiment,
            project,
            time_frequency,
            variable,
            ensemble)
    else:
        raise ValueError(
            "Either input_directory or all Freva parameters must be provided"
        )

    if not files:
        print("❌ No NetCDF files found. Exiting.")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Process climatology if needed
    if subtract_clim:
        if not climatology_file:
            raise ValueError(
                "climatology_file must be provided when subtract_clim=True"
            )
        adjusted_climatology = os.path.join(output_dir, "adjusted_climatology.nc")
        adjust_climatology(climatology_file, files[0], adjusted_climatology)

    anomaly_files = []
    years = []
    
    # Add progress bar for file processing
    print("\n🔄 Processing files:")
    for file in tqdm(files, desc="Processing files", unit="file"):
        if subtract_clim:
            anomaly_file = os.path.join(
                output_dir, 
                os.path.basename(file).replace(".nc", "_anomaly.nc")
            )
            ds_anomalies = subtract_climatology(
                file, adjusted_climatology, anomaly_file, variable
            )
        else:
            # If not subtracting climatology, just open the file directly
            ds_anomalies = xr.open_dataset(file)

        anomaly_files.append(ds_anomalies)
        file_years = extract_years_from_file(file)
        years.append(file_years[0])

    print(f"\n📊 Extracted years: {years}")

    unique_time_steps = {len(ds.time) for ds in anomaly_files}
    print(f"📊 Unique time step counts in anomaly files: {unique_time_steps}")

    if len(unique_time_steps) > 1:
        print("❌ Warning: Not all files have the same number of time steps!")
        for i, ds in enumerate(anomaly_files):
            print(f"File {i}: {len(ds.time)} time steps")

    combined_ds = xr.concat(anomaly_files, dim="initialization")

    combined_ds = combined_ds.assign_coords(
        initialization=("initialization", years))

    print(
        f"📊 Updated initialization values:"
        f" {combined_ds.initialization.values}")

    combined_ds.initialization.attrs["units"] = "year"

    print(f"📊 Combined dataset dimensions: {combined_ds.dims}")
    print(f"📊 Combined dataset shape: {combined_ds[variable].shape}")

    n_initializations = len(files)
    n_lead_times = len(
        anomaly_files[0].time
    )

    ds_4d = reorganize_to_4d(
        combined_ds,
        variable,
        n_initializations,
        n_lead_times)

    ds_4d = ds_4d.assign_coords(initialization=("initialization", years))

    ds_4d.initialization.attrs["units"] = "year"

    ds_4d = ds_4d.set_coords("initialization")

    print(f"📊 Final initialization values: {ds_4d.initialization.values}")
    print(
        "📊 Final initialization units",
        f" : {ds_4d.initialization.attrs.get('units', 'N/A')}"
    )

    ds_4d.to_netcdf(output_file)
    print(f"✅ Processed data saved to {output_file}")

    if cleanup:
        print("🧹 Cleaning up intermediate files...")
        for file in anomaly_files:
            os.remove(file)
        if subtract_clim:
            os.remove(adjusted_climatology)
        print("✅ Intermediate files removed.")
