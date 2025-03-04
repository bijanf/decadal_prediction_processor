from src.processor import process_files
from src.plot_time_series import plot_global_mean_tas
from src.processor import shift_initialization_time
if __name__ == "__main__":
    output_file = "/work/kd1418/codes/work/k202196/MYWORK/tas_Amon_MPI-ESM-LR_dkfen41979-2021_r26i2p1.nc"
    process_files(
        experiment="dkfen4*",
        project="comingdecade",
        time_frequency="mon",
        variable="tas",
        ensemble="r26i2p1",
        climatology_file="/work/bk1318/k202208/diff-pred/data/mpi-esm/tas_Amon_MPI-ESM-historical_ensmean_185001-200512_climatology.nc",
        output_file="/work/kd1418/codes/work/k202196/MYWORK/tas_Amon_MPI-ESM-LR_dkfen41979-2021_r26i2p1_f.nc", 
        output_dir="./", 
        cleanup=False 
    )
    shift_initialization_time("/work/kd1418/codes/work/k202196/MYWORK/tas_Amon_MPI-ESM-LR_dkfen41979-2021_r26i2p1_f.nc",
                          output_file)

    plot_global_mean_tas(
        output_file,
        num_lead_years=2,
        output_plot=f"first_2_lead_years_with_mean.png",
    )
    plot_global_mean_tas(
        output_file,
        num_lead_years=11,
        output_plot=f"first_11_lead_years_with_mean.png",
    )

   
    

