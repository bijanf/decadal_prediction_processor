import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


def plot_global_mean_tas(
    nc_file: str,
    num_lead_years: int,
    output_plot: str
 ) -> None:
    """
    Plots the monthly global mean surface air temperature (tas)
    for each initialization
    and overlays a mean line for months with more than two data points.

    Parameters:
        nc_file (str): Path to the NetCDF file.
        num_lead_years (int): Number of lead years to plot.
        output_plot (str): Path to save the output plot.

    Returns:
        None
    """
    ds = xr.open_dataset(nc_file)
    fldmean_tas = ds["tas"].mean(dim=["lat", "lon"])

    yearly_data = {}
    monthly_values = {}

    for init_year in ds["initialization"]:
        lead_times = fldmean_tas.sel(initialization=init_year)[
            "lead_time"
        ].values
        block_range = range(0, min(len(lead_times), num_lead_years * 12), 12)

        for block_start in block_range:
            year = int(init_year.values) + block_start // 12
            block = lead_times[block_start:block_start + 12]
            tas_block = fldmean_tas.sel(
                initialization=init_year, lead_time=block
            ).values

            if len(tas_block) < 12:
                continue

            yearly_data.setdefault(year, []).append(tas_block)

            for month_idx, temp_value in enumerate(tas_block):
                actual_time = year + month_idx / 12
                monthly_values.setdefault(actual_time, []).append(temp_value)

    plt.figure(figsize=(14, 7))

    for year, tas_blocks in yearly_data.items():
        for tas_block in tas_blocks:
            plt.plot(
                [year + (month - 1) / 12 for month in range(1, 13)],
                tas_block,
                "k-",
                alpha=0.5,
            )

    mean_x_vals = []
    mean_y_vals = []

    for time_point, values in sorted(monthly_values.items()):
        if len(values) > 2:
            mean_x_vals.append(time_point)
            mean_y_vals.append(np.mean(values))

    plt.plot(
        mean_x_vals, mean_y_vals, "r-", linewidth=2, label="Mean (if N > 2)"
    )
    plt.xlabel("Year")
    plt.ylabel("Field Mean of tas (K)")
    plt.title(f"Monthly Field Mean of tas (First {num_lead_years} Lead Years)")
    plt.legend()

    plt.savefig(output_plot, bbox_inches="tight", pad_inches=0, dpi=300)
    print(f"Plot saved to {output_plot}")
