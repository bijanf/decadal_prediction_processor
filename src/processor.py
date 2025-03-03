import os
from typing import List
import xarray as xr
import numpy as np
import cftime
import freva
def find_nc_files(
    experiment: str,
    project: str,
    time_frequency: str,
    variable: str,
    ensemble: str
) -> List[str]:
    """Finds NetCDF files using Freva's databrowser."""
    print("Searching for NetCDF files with parameters:")
    print(f"Experiment: {experiment}, Project: {project}, Time Frequency: {time_frequency}, Variable: {variable}, Ensemble: {ensemble}")
    
    results = list(freva.databrowser(
        experiment=experiment,
        project=project,
        time_frequency=time_frequency,
        variable=variable,
        ensemble=ensemble,
    ))  # Convert generator to list
    
    if not results:
        print("Warning: No files found with the given parameters.")
    else:
        print(f"Found {len(results)} files.")
    
    return results

def process_files(
    experiment: str,
    project: str,
    time_frequency: str,
    variable: str,
    ensemble: str,
    output_file: str,
) -> None:
    """
    Processes NetCDF files into a 5D dataset (initialization_year, lead_time, month, lat, lon).
    Groups by initialization_year and lead_time.
    """
    files = find_nc_files(
        experiment, project, time_frequency, variable, ensemble)
    
    if not files:
        print("No NetCDF files found. Exiting.")
        return

    print(f"Found files: {files}")

    all_data = []
    init_years = []

    for file in files:
        if not os.path.exists(file):
            print(f"Warning: File {file} does not exist. Skipping.")
            continue

        # Open the dataset
        ds = xr.open_dataset(file, decode_times=False)

        # Extract time variable and its units
        time_var = ds['time']
        time_units = time_var.attrs['units']

        # Handle 'months since' time units
        if "months since" in time_units:
            print(f"Detected 'months since' format in file {file}. Converting to 'days since'.")
            base_time_str = time_units.split("since")[-1].strip().split(" ")[0]  # Extract YYYY-MM-DD
            base_date = cftime.datetime.strptime(base_time_str, "%Y-%m-%d")

            # Convert months to days (approximate each month as 30 days)
            time_days = time_var.values * 30
            new_time_units = f"days since {base_date.year}-{base_date.month:02d}-{base_date.day:02d}"
            init_dates = cftime.num2date(time_days, new_time_units, calendar="proleptic_gregorian")
        else:
            # Handle other time formats
            init_dates = cftime.num2date(time_var.values, time_units, calendar="proleptic_gregorian")

        # Get initialization year (first year in the time dimension)
        init_year = init_dates[0].year
        init_years.append(init_year)

        # Compute lead_time (1-based index for lead time)
        lead_times = np.arange(1, len(init_dates) + 1)

        # Add initialization_year and lead_time as coordinates
        ds = ds.assign_coords(
            {
                "initialization_year": ("time", np.full(len(time_var), init_year), {"units": "year"}),
                "lead_time": ("time", lead_times, {"units": "months since initialization"}),
            }
        )

        # Append the dataset to the list
        all_data.append(ds)

    # Concatenate all datasets along the time dimension
    combined_ds = xr.concat(all_data, dim="time")

    # Group by initialization_year and lead_time
    combined_ds = combined_ds.set_index(time=["initialization_year", "lead_time"])
    combined_ds = combined_ds.unstack("time")

    # Ensure variable dimensions are correctly ordered
    if variable in combined_ds:
        combined_ds[variable] = combined_ds[variable].transpose(
            "initialization_year", "lead_time", "lat", "lon"
        )

    print("Final Initialization Years:", init_years)

    # Save the combined dataset to a NetCDF file
    combined_ds.to_netcdf(output_file)
    print(f"Output saved to {output_file}")