from src.processor import process_files
from src.compute_yearmonmean_anomalies import compute_yearmonmean_anomalies

if __name__ == "__main__":
    output_file = "/work/kd1418/codes/work/k202196/MYWORK/output_file.nc"
    process_files(
        experiment="dkfen4197*",
        project="comingdecade",
        time_frequency="mon",
        variable="tas",
        ensemble="r26i2p1",
        output_file="/work/kd1418/codes/work/k202196/MYWORK/output_file.nc"
    )
   
    compute_anomalies_with_climatology(
        data_file="/work/kd1418/codes/work/k202196/MYWORK/output_file.nc",
        climatology_file="/work/bk1318/k202208/diff-pred/data/mpi-esm/tas_Amon_MPI-ESM-historical_ensmean_185001-200512_climatology.nc",
        output_file="/work/kd1418/codes/work/k202196/MYWORK/output_file_anomalies.nc"
    )       



