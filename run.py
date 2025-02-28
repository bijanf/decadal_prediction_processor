from src.processor import process_files

if __name__ == "__main__":
    # Update these paths as needed
    output_file = "/work/kd1418/codes/work/k202196/MYWORK/output_file.nc"
    process_files(
        experiment="dkfen4197*",
        project="comingdecade",
        time_frequency="mon",
        variable="tas",
        ensemble="r26i2p1",
        output_file=output_file,
    )
