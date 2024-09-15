# Model run on JRC data
## Overview
JrcModely.py runs oasis model on based on data from JRC.
Input/Output stored in `global_flooding_variants` when running JrcModel.py
## Running in command line 
#### Usage: 
JrcModel.py [-h] [-W WORKING_FOLDER] [-d NUM_DAMAGE_BINS] [-M OASIS_MODEL_FOLDER]
                   [-count COUNTRY_SPECIFIC [COUNTRY_SPECIFIC ...]]
                   [-cont CONTINENT_SPECIFIC [CONTINENT_SPECIFIC ...]] [-imt INT_MES_TYPES] [-F DATA_PATH]
                   [-e JRC_INPUT_PATH]
##### Set up paths to receive inputs and output files to for vulnerability function data
##### Options:
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
                        to run the model on specific continents, input names from one of the following: Africa,    
                        Asia, Centr&south America, Europe, North America or Global` 
  -imt INT_MES_TYPES, --int-mes-types INT_MES_TYPES
                        enter the unique intensity measurement types in the model data 
  -F DATA_PATH, --data-path DATA_PATH
                        input name of file containing the vulnerability functions
  -e JRC_INPUT_PATH, --jrc-input-path JRC_INPUT_PATH
                        input name of file containing the exposure file for the JRC data containing headers:       
                        'country_code' and 'oed_occupancy_code'
                        
## Data Source (restrictions to be included)
Stored in `global_flooding_data` from JRC Publications Repository- Global flood depth-damage functions (https://publications.jrc.ec.europa.eu/repository/handle/JRC105688).
#### Citation
Huizinga, J., De Moel, H. and Szewczyk, W., Global flood depth-damage functions: Methodology and the database with guidelines, EUR 28552 EN, Publications Office of the European Union, Luxembourg, 2017, ISBN 978-92-79-67781-6, doi:10.2760/16510, JRC105688.
## How to process data 
Source code in `VulnerabilityLibrary/src/`

User edits `VulnerabilityLibrary/intensity_bins_input.csv` to the appropriate bin sizes

Run code in terminal including extra dashes as shown by help guide.
#### Example running in windows environment:
PS C:\Users\...\Documents\VulnerabilityLibrary> src/JrcModel.py.
#### Inputs
intensity_bins_input.csv in `VulnerabilityLibrary/`

csv files in `VulnerabilityLibrary/global_flooding_variants/keys_data`
#### Outputs
intensity_bin_dict in `VulnerabilityLibrary/`

vulnerability.csv, damage_bin_dict.csv in `global_flooding_variants/model_data`

vulnerability_dict.csv in `VulnerabilityLibrary/global_flooding_variants/keys_data`
#### Additional notes
JrcModel.py can run on specific continents using -cont ‘North America’ in command line.

Note: any single entry that requires a space in the name should be enclosed by apostrophes to indicate single string.
## Filepath compatibility
Pathlibs used so all filepaths are compatible with both Windows and Linux.
Relative file paths hard-coded at beginning of script. 

Computer outputs correct absolute file paths by using the folder (with default name VulnerabilityFile) as a reference. This folder name can be changed by editing `oasis_model_folder` argeparse argument


