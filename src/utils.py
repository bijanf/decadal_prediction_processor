import os
from typing import List


def validate_files(files: List[str]) -> None:
    """
    Validates that the input files exist and are NetCDF files.

    Args:
        files (List[str]): List of file paths.

    Raises:
        FileNotFoundError: If any file does not exist.
        ValueError: If any file is not a NetCDF file.
    """
    for file in files:
        if not file.endswith(".nc"):
            raise ValueError(f"File {file} is not a NetCDF file.")
        if not os.path.exists(file):
            raise FileNotFoundError(f"File {file} does not exist.")
