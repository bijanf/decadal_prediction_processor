import os

import pytest

from src.utils import validate_files


def test_validate_files(tmp_path):
    # Create a dummy file
    file = tmp_path / "test.nc"
    file.touch()

    # Test valid file
    validate_files([str(file)])

    # Test invalid file
    with pytest.raises(FileNotFoundError):
        validate_files([str(tmp_path / "nonexistent.nc")])

    with pytest.raises(ValueError):
        validate_files([str(tmp_path / "test.txt")])
