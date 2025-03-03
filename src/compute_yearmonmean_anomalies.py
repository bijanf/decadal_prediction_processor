import xarray as xr
import xesmf as xe  # Required for regridding
import numpy as np

def compute_anomalies_with_climatology(data_file: str, climatology_file: str, output_file: str):
    """
    Computes anomalies with respect to an external climatology file.
    
    1. Remaps the climatology to match the grid of the input dataset (if needed).
    2. Subtracts the climatology from the input dataset to compute anomalies.
    3. Saves anomalies as a NetCDF file.

    Args:
        data_file (str): Path to the input NetCDF file (output_file.nc).
        climatology_file (str): Path to the reference climatology file.
        output_file (str): Path to save the anomalies.
    """

    print(f"Loading dataset: {data_file}")
    ds = xr.open_dataset(data_file)

    print(f"Loading climatology file: {climatology_file}")
    clim_ds = xr.open_dataset(climatology_file)

    # Ensure 'tas' is ordered properly in the dataset
    if "tas" in ds:
        ds["tas"] = ds["tas"].transpose("initialization_year", "lead_time", "lat", "lon")

    # Check if regridding is needed (grid mismatch)
    if not np.array_equal(ds.lat, clim_ds.lat) or not np.array_equal(ds.lon, clim_ds.lon):
        print("⚠️ Grid mismatch detected. Regridding climatology to match dataset.")
        regridder = xe.Regridder(clim_ds, ds, method="bilinear")
        clim_ds = regridder(clim_ds)
        clim_ds.attrs['history'] += " | Regridded using xESMF bilinear interpolation"

    # Expand climatology dimensions to match the dataset
    clim_ds = clim_ds["tas"].expand_dims(["initialization_year", "lead_time"])

    # Compute anomalies
    anomalies = ds["tas"] - clim_ds

    # Save anomalies as a new NetCDF file
    anomalies_ds = anomalies.to_dataset(name="tas_anomaly")
    anomalies_ds.to_netcdf(output_file)

    print(f"✅ Anomalies saved to {output_file}")

