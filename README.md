# Decadal Prediction Processor
![CI](https://github.com/bijanf/decadal_prediction_processor/actions/workflows/ci.yml/badge.svg)
[![License](https://img.shields.io/badge/License-BSD-purple.svg)](LICENSE)

This project processes decadal prediction NetCDF files to extract monthly values with dimensions: `time`, `lead_year`, `initialization_year`, `lat`, and `lon`.

## **Features**
- Merges multiple NetCDF files.
- Adds `initialization_year` and `lead_year` dimensions.
- Saves the output to a new NetCDF file.

## **Requirements**
- Python 3.8+
- Libraries: `xarray`, `netCDF4`, `numpy`, `dask`

## **Installation**
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/decadal_prediction_processor.git
   cd decadal_prediction_processor
   ```

2. Install dependencies:
    ```bash
     mamba env create -f environment.yml
     conda activate decadal_prediction_processor
     
    ```

## Usage 

1. Place your NetCDF files in a directory.

2. Update the input_dir and output_file paths in run.py.

3. Run the script:

    ```bash 
        python -m pytest tests/
    ```
## Output

The output file will contain:

1. Dimensions: time, lead_year, initialization_year, lat, lon.
2. Variables: tas (near-surface air temperature).

## Tests
Run tests using:
```bash 
    pip install tox
    tox 
```
## run plot testing 
```python
python plot_time_series.py
```
![image](full_12_month_lead_time_blocks.png)

## License 

MIT License 
## TODOS: 
- finish the tests
