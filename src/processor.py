"""Processor module for handling NetCDF files and running Freva queries."""

import os
from typing import List

import freva
import numpy as np
import xarray as xr


def find_nc_files(
    experiment: str,
    project: str, time_frequency: str, variable: str, ensemble: str
) -> List[str]:
    """Finds NetCDF files using Freva's databrowser."""
    results = freva.databrowser(
        experiment=experiment,
        project=project,
        time_frequency=time_frequency,
        variable=variable,
        ensemble=ensemble,
    )
    return list(results)


def process_files(
    experiment: str,
    project: str,
    time_frequency: str,
    variable: str,
    ensemble: str,
    output_file: str,
) -> None:
    """
    Processes NetCDF files into a 5D
    dataset (initialization_year,
    lead_time, month, lat, lon).
    """
    files = find_nc_files(
        experiment, project, time_frequency, variable, ensemble)
    if not files:
        print("No NetCDF files found. Exiting.")
        return

    print(f"Found files: {files}")

    all_data = []

    for file in files:
        ds = xr.open_dataset(file, decode_times=False)

        # Extract initialization year
        filename = os.path.basename(file)
        try:
            init_year = int(filename.split("dkfen4")[1][:4])
        except ValueError:
            print(f"Error extracting year from filename: {filename}")
            continue

        # Determine lead time (assuming monthly time steps)
        # Compute lead time dynamically based on time variable length
        num_months = len(ds["time"])
        lead_times = np.arange(1, num_months // 12 + 2)
        lead_time_values = np.repeat(lead_times, 12)[
            :num_months
        ]  # Ensure matching size

        # Extract month index (1-12)
        months = np.tile(np.arange(1, 13), len(lead_times))[:num_months]
        ds = ds.assign_coords(
            {
                "initialization_year": ("time", [init_year] * num_months),
                "lead_time": ("time", lead_time_values),
                "month": ("time", months),
            }
        )

        all_data.append(ds)

    # Ensure sorted order
    all_data = sorted(
        all_data,
        key=lambda ds: ds["initialization_year"].values[0]
    )

    # Concatenate along time
    combined_ds = xr.concat(all_data, dim="time")

    # Set index correctly before unstacking
    combined_ds = combined_ds.set_index(
        time=["initialization_year", "lead_time", "month"]
    )
    # Unstack to create (initialization_year, lead_time, month, lat, lon)
    combined_ds = combined_ds.unstack("time")

    # Ensure variable dimensions are correctly ordered
    if "tas" in combined_ds:
        combined_ds["tas"] = combined_ds["tas"].transpose(
            "initialization_year", "lead_time", "month", "lat", "lon"
        )

    # Save dataset
    combined_ds.to_netcdf(output_file)
    print(f"Output saved to {output_file}")
