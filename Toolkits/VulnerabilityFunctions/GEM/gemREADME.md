# Model run on GEM data
## Overview
JrcModely.py runs oasis model on based on data from GEM.
Input/Output stored in `global_earthquake_variants` when running GemModel.py.
## Running in command line 
#### Usage: 
GemModel.py [-h] [-W WORKING_FOLDER] [-d NUM_DAMAGE_BINS] [-M OASIS_MODEL_FOLDER]
                   [-count COUNTRY_SPECIFIC [COUNTRY_SPECIFIC ...]]
                   [-cont CONTINENT_SPECIFIC [CONTINENT_SPECIFIC ...]] [-imt INT_MES_TYPES] [-F DATA_FOLDER]       
                   [-cov COVERAGE_TYPE]
Set up paths to receive inputs and output files to for vulnerability function data
options:
  -h, --help            show this help message and exit
  -W WORKING_FOLDER, --working-folder WORKING_FOLDER
                        input the name of the folder containing the source code and the oasis lmf model
  -d NUM_DAMAGE_BINS, --num-damage-bins NUM_DAMAGE_BINS
                        input number of damage bins
  -M OASIS_MODEL_FOLDER, --oasis-model-folder OASIS_MODEL_FOLDER
                        input name of folder containing the files and data to run oasis lmf model
  -count COUNTRY_SPECIFIC [COUNTRY_SPECIFIC ...], --country-specific COUNTRY_SPECIFIC [COUNTRY_SPECIFIC ...]       
                        to analyse specific countries, input the name of which one to run the model on
  -cont CONTINENT_SPECIFIC [CONTINENT_SPECIFIC ...], --continent-specific CONTINENT_SPECIFIC [CONTINENT_SPECIFIC ...]
                        to analyse specific continents, input the name of which one to run the model on
  -imt INT_MES_TYPES, --int-mes-types INT_MES_TYPES
                        enter the unique intensity measurement types in the model data with a space in between     
                        each type as a string
  -F DATA_FOLDER, --data-folder DATA_FOLDER
                        input name of folder containing the vulnerability functions
  -cov COVERAGE_TYPE, --coverage-type COVERAGE_TYPE
                        input structural, contents or non_structural

## Data Source (restrictions to be included)
The model data is source from Global Earhtquake Model (https://www.globalquakemodel.org/product/global-vulnerability-model).

The data for GemModel.py is stored in `VulnerabilityLibrary/global_flooding_variants/global_earthquake_data`

URL: https://github.com/gem/global_vulnerability_model/ 
#### Citation
Martins L., Silva V. (2023), Global Vulnerability Model of the GEM Foundation, GitHub. https://github.com/gem/global_vulnerability_model/ DOI: 10.5281/zenodo.8391742.
## How to process data 
Source code in `VulnerabilityLibrary/src/GemModel.py`

User needs to edit `VulnerabilityLibrary/intensity_bins_input.csv` to the appropriate bin sizes

Run code in terminal including extra dashes as shown by help guide using -h
#### Example running in windows environment:
PS C:\Users\...\Documents\VulnerabilityLibrary> src/GemModel.py.
#### Inputs
xml files in `VulnerabilityLibrary/global_earthquake_data`

intensity_bins_input.csv in `VulnerabilityLibrary/`

csv files in `VulnerabilityLibrary/global_earthquake_variants/keys_data`
#### Outputs
intensity_bin_dict in `VulnerabilityLibrary/`

vulnerability.csv, damage_bin_dict.csv in `global_earthquake_variants/model_data`

vulnerability_dict.csv in `VulnerabilityLibrary/global_earthquake_variants/keys_data`
#### Additional notes
GemModel.py can run on specific continents using -cont NAME or specific countries using -count NAME

Note: any single entry that requires a space in the name should be enclosed by apostrophes to indicate single string e.g. 'North America'
## Filepath compatibility
Pathlibs used so all filepaths are compatible with both Windows and Linux.
Relative file paths hard-coded at beginning of script. 

Computer outputs correct absolute file paths by using the folder (with default name VulnerabilityFile) as a reference. This folder name can be changed by editing `oasis_model_folder` argeparse argument


