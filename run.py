from src.processor import process_files

if __name__ == "__main__":
    # Update these paths as needed
    input_dir = "/work/bm1159/XCES/xces-work/b380001/evaluation_system/CMOR4LINK/decadal/mpi/mpi-esm-lr"
    output_file = "/work/kd1418/codes/work/k202196/MYWORK/output_file.nc"
    process_files(input_dir, output_file)