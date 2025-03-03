import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Load the NetCDF file with decode_times=False
file_path = "/work/kd1418/codes/work/k202196/MYWORK/output_file.nc"
ds = xr.open_dataset(file_path, decode_times=False)

# Compute the global mean (fldmean) for each initialization_year
fldmean_tas = ds["tas"].mean(dim=["lat", "lon"])

# Create a dictionary to store data for each year
yearly_data = {}

# Iterate over each initialization_year and extract the relevant lead_time blocks
for i, init_year in enumerate(ds["initialization_year"]):
    # Get the lead_time values for this initialization_year
    lead_times = fldmean_tas.sel(initialization_year=init_year)["lead_time"].values
    
    # Iterate over each 12-month block and assign it to the corresponding year
    for block_start in range(0, len(lead_times), 12):
        # Calculate the year for this block
        year = init_year.values + block_start // 12
        
        # Extract the 12-month block
        block = lead_times[block_start:block_start + 12]
        tas_block = fldmean_tas.sel(initialization_year=init_year, lead_time=block).values
        
        # If the year is not in the dictionary, initialize it with an empty list
        if year not in yearly_data:
            yearly_data[year] = []
        
        # Append the tas values for this block to the corresponding year
        yearly_data[year].append(tas_block)

# Prepare data for plotting
years = sorted(yearly_data.keys())
months = np.arange(1, 13)  # Months from 1 to 12

# Plot the monthly values for each year
plt.figure(figsize=(14, 7))

for year in years:
    # Extract the 12-month blocks for this year
    tas_blocks = yearly_data[year]
    
    # Plot each 12-month block as a separate line
    for i, tas_block in enumerate(tas_blocks):
        plt.plot(
            [year + (month - 1) / 12 for month in months],
            tas_block,
            marker="o",
            label=f"{year} (Block {i + 1})"
        )

# Add labels and title
plt.xlabel("Year")
plt.ylabel("Field Mean of tas (K)")
plt.title("12-Month Lead Time Blocks Across Initialization Years")

# Add a legend
plt.legend()

# Save the plot without extra whitespace
output_plot_path = "12_month_lead_time_blocks.png"
plt.savefig(output_plot_path, bbox_inches="tight", pad_inches=0, dpi=300)

print(f"Plot saved to {output_plot_path}")
output_plot_path = "12_month_lead_time_blocks.png"
plt.savefig(output_plot_path, bbox_inches="tight", pad_inches=0, dpi=300)

print(f"Plot saved to {output_plot_path}")