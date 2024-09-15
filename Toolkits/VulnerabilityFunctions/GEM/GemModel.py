import pandas as pd
import xml.etree.ElementTree as ET
import numpy as np
from scipy import interpolate
from scipy.stats import beta
import time
import sys
import argparse
from pathlib import PurePosixPath, PurePath, Path

parser = argparse.ArgumentParser(description = "Set up paths to receive inputs and output files to for vulnerability function data")
parser.add_argument('-W', "--working-folder", default='VulnerabilityLibrary', help = "input the name of the folder containing the source code and the oasis lmf model")
parser.add_argument('-d', "--num-damage-bins", default=100, type=int, help = "input number of damage bins")
parser.add_argument('-M', "--oasis-model-folder", default='global_earthquake_variants', help = "input name of folder containing the files and data to run oasis lmf model")
parser.add_argument('-count', "--country-specific", default='', nargs='+', help = "to analyse specific countries, input the name of which one to run the model on")
parser.add_argument('-cont', "--continent-specific", default='', nargs='+', help = "to analyse specific continents, input the name of which one to run the model on")
parser.add_argument('-imt', "--int-mes-types", default='PGA SA(0.3) SA(0.6) SA(1.0)', type=str, help="enter the unique intensity measurement types in the model data with a space in between each type as a string")
parser.add_argument('-F', "--data-folder", default="global_earthquake_data", help = "input name of folder containing the vulnerability functions")
parser.add_argument('-cov', "--coverage-type", default='structural', help = "input structural, contents or non_structural")

# default paths for input/output files
int_input_path = 'intensity_bins_input.csv'
int_dict_path = 'intensity_bin_dict.csv'
dam_bin_path = 'model_data/damage_bin_dict.csv'
vuln_dict_path = 'keys_data/vulnerability_dict.csv'
vulnerability_path = 'model_data/vulnerability.csv'
rel_height_path = 'keys_data/height_dict.csv'
rel_occup_path = 'keys_data/occupancy_dict.csv'
rel_constr_path = 'keys_data/construction_dict.csv'
rel_countr_path = 'keys_data/country_dict.csv'

# Notes on references for using tree and root method to analyse xml files
    # Intensity Measurement Type is root[0][i][0].attrib['imt']
    # Taxonomy is root[0][i].attrib['id']
        # Taxonomy [0]
        # Taxonomy [1]
        # Taxonomy [-1] 
    # Intensity is root[0][i][0].text
    # Mean Loss Ratio is root[0][i][1].text
    # Coefficient of Variation is root[0][i][2].text

def init_run(working_folder):
    model_path = PurePath(__file__)
    parent = model_path.parents
    for each in parent:
        if PurePosixPath(each).name == working_folder:
            path_stem = each
    return path_stem

def init_int_bins(path_stem):
    # create three lists for lower bound, upper bound and mid point point values of intensity bins
    int_bin_vals = []
    int_bins = []
    int_mp_vals = []
    with open(PurePath.joinpath(path_stem, int_input_path)) as bins_file:
        # Read in bins data from opened file
        for i, line in enumerate (bins_file):
            line = line.strip()
            if i:
                line = float(line)
                int_bin_vals.append(line)
                # condition to repeat first value
                if not (i-1):
                    int_bin_vals.append(line)
            else:
                continue

        # repeat last intensity value
        int_bin_vals.append(int_bin_vals[-1])
        for i in range (len(int_bin_vals)-1):
            int_bins.append((int_bin_vals[i], int_bin_vals[i+1]))
        int_bins = np.array(int_bins, dtype = float)
        for int_bin in int_bins:
            int_mp_val = (int_bin[0] + int_bin[1]) / 2
            int_mp_vals.append(round(int_mp_val, 16))

    # check for monotonicity
    if sorted(int_bin_vals) != int_bin_vals:
        print ('input intensity bins must be arranged in order of size...')
        sys.exit()
    return int_bins, int_mp_vals

def create_int_bins(int_bins, int_mp_vals, int_mes_types):
    # create function to find unique intensity measurement types
    index_num = 1
    for type in int_mes_types:
            for int_bin, int_mp_val in zip(int_bins, int_mp_vals):
                int_bin_dict = {'bin_index': index_num,
                                'intensity_measurement_type': type,
                                'bin_from': int_bin[0], 
                                'bin_to': int_bin[1], 
                                'interpolation': int_mp_val
                                }
                index_num += 1
                yield int_bin_dict

def init_damage_bins(incr):
    damage_bins = []

    # create list of values in the damage bins - first and last values repeated so bin creation is simpler
    dam_bin_vals = np.arange(0, 1 + incr, incr)
    dam_bin_vals = np.append (dam_bin_vals[0], dam_bin_vals)
    dam_bin_vals = np.append(dam_bin_vals, dam_bin_vals[-1])

    # create damage bins [a,b)
    for i in range (len(dam_bin_vals)-1):
        damage_bins.append((dam_bin_vals[i], dam_bin_vals[i+1]))
    damage_bins = np.array(damage_bins, dtype = float)

    # rounding decimal places results in division accuracy errors
    dam_bin_vals = [np.round(dam_bin, 12) for dam_bin in dam_bin_vals]
    damage_bins_list = [dam for dam in dam_bin_vals]
    # damage_bins_list returns list of damage bin values not including the repeated start and end values 
    return damage_bins, damage_bins_list[1:-1]

def directories(rootdir, coverage_type):
    location_dict = {}
    for file in Path(rootdir).glob('**/*.xml'):
        filepath = Path(file).absolute()
        cov_type_path = Path(file).name
        if PurePosixPath(cov_type_path).stem == f"vulnerability_{coverage_type}":
            location_continent = Path(file).parent.parent.name
            location_country = Path(file).parent.name
            location_dict [location_continent, location_country] = filepath
    return location_dict

def create_damage_bins(damage_bins):
    damage_bin_dict = {}
    index_num = 1
    for dam_bin in damage_bins:
        interp_val = (dam_bin[0] + dam_bin[1]) / 2
        interp_val = round(interp_val, 16)
        damage_bin_dict = {'bin_index': index_num,
                        'bin_from': "{:.6f}".format(dam_bin[0]),
                        'bin_to': "{:.6f}".format(dam_bin[1]), 
                        'interpolation': "{:.6f}".format(interp_val)
                        }
        index_num += 1
        yield damage_bin_dict

def create_vuln_dict(val_id, bin_index_list, damage_bins):
    for bin_index in bin_index_list:
        for k in range(len(damage_bins)):
            rec = {
                "vulnerability_id": val_id[0],
                "intensity_bin_id": bin_index,
                "damage_bin_id": "{:.0f}".format(k+1),
                }
            yield rec

def create_vuln_ids(location_dict, height_dict, occup_dict, constr_dict, countr_dict):
    vuln_ids = {}
    cur_vuln_id = 1    

    for country in location_dict:
        pathway = location_dict[country]
        tree = ET.parse(pathway)
        root = tree.getroot()
        for i in range (1, len(root[0])):
            taxonomy = root[0][i].attrib['id']
            tax = taxonomy.split('/')
            tax.append(tax[0] + '/' + tax[1])
            # example of tax: ['CR', 'LDUAL+CDL+DUM', 'H1', 'RES', 'CR/LDUAL+CDL+DUM']
            if (country, taxonomy) not in vuln_ids:
                vuln_ids[(country, taxonomy)] = cur_vuln_id
                cur_vuln_id += 1
                for (attribute2_3, peril_type, ranking) in constr_dict:
                    if attribute2_3 in tax:
                        attribute2_3_id = constr_dict[attribute2_3, peril_type, ranking]
                        peril_id = peril_type
                        rank = ranking
                for attribute6 in occup_dict:
                    if attribute6 in tax:
                        attribute6_id = occup_dict[attribute6]
                for attribute4 in height_dict:
                    if attribute4 in tax:
                        no_storeys = height_dict[attribute4]
                country_id = countr_dict[country]
                id_dict = {
                    "vulnerability_id": vuln_ids[(country, taxonomy)],
                    "peril_id": peril_id,
                    "country_id": country_id,
                    "taxonomy": taxonomy,
                    "node_id": i,
                    "attribute2_3_id": attribute2_3_id,
                    "ranking": rank,
                    "attribute4_id": no_storeys,
                    "attribute6_id": attribute6_id
                }
                yield id_dict

def get_vuln_ids(vulns_df, countr_dict, location_dict):
    vuln_dict = {}
    # Reverse key and values in countr_dict 
    rev_countr_dict = {countr_dict[country]: country for country in countr_dict}
    # Map country to continent
    countr_to_cont = {country: continent for (continent, country) in location_dict}
    
    for index, row in vulns_df.iterrows():
        vuln_id = row['vulnerability_id']
        vuln_country_id = row['country_id']
        vuln_taxonomy = row['taxonomy']
        vuln_node_id = row['node_id']
        country = rev_countr_dict[str(vuln_country_id)]
        continent = countr_to_cont[country]
        vuln_dict[(continent, country, vuln_taxonomy, vuln_node_id)] = [vuln_id]

    return vuln_dict

def get_bin_index(int_bins, int_mp_vals, int_mes_types, intensity_measure):
    bin_index_list = []
    start_index = 1
    num_intensity_bins = len(int_bins)

    # Intensity bin indexes range: e.g. from 1-20 (PGA), 21-40 (SA 0.3), 41-60 (SA 0.6), 61-80 (SA 1.0) if 20 input hazard intensity bins
    for i, int_mes_type in enumerate(int_mes_types):
        if intensity_measure == int_mes_type:
            start_index += i * num_intensity_bins
    for int_mp_val in int_mp_vals:
        for i in range(len(int_bins)):
            # edge case: if hazard intensity value is below or equal to lower bound of smallest bin
            if (not(i) and int_mp_val <= int_bins[0][0]):
                bin_index = start_index
                break
            # edge case: if hazard intensity value is greater than or equal to upper bound of largest bin
            elif int_mp_val >= int_bins[-1][0]:
                bin_index = start_index + (len(int_bins) - 1)
                break
            elif int_bins[i][0] <= int_mp_val < int_bins[i][1]:
                bin_index = start_index + (i)
                break
        bin_index_list.append(bin_index)
    return bin_index_list

def compute_probs(int_vals, int_mp_vals, mean_LRs, std_devs, damage_bins_list):
    a=0
    b=1
    probs = {}

    # edge cases: bounds error is used when int_mp_vals (intensity bins) are above or below the range of intensity values 
    int_vs_mean = interpolate.interp1d(int_vals, mean_LRs, kind='linear', bounds_error=False, fill_value= (mean_LRs[0], mean_LRs[-1]))
    int_vs_std = interpolate.interp1d(int_vals, std_devs, kind='linear', bounds_error=False, fill_value= (std_devs[0], std_devs[-1]))
    # function created above can take in list of values to use for interpolation - seen below
    interp_mean = int_vs_mean (int_mp_vals)
    interp_std_dev = int_vs_std (int_mp_vals)

    for j, (mean_val, std_dev_val) in enumerate (zip(interp_mean, interp_std_dev)):
        # edge case if parametrisation cannot be made due to zero mean loss ratio and standard deviation of loss ratio
        if mean_val == 0 and std_dev_val == 0:
            cum_diff_vals = np.append(1, np.zeros(len(damage_bins_list)))
        # damage_bins_list[0] == 0 should always be true- hence following code simply checks if the current intensity bin index being run is hazard intensity zero
        elif j==0 and damage_bins_list[0] == 0:
            cum_diff_vals = np.append(1, np.zeros(len(damage_bins_list)))
        else:
            # Beta paramters for last few bins are very large, indicating dirac delta function shape - high intensity leads to high damage almost 100% of the time
            # Zero mean, and small std deviation => beta value 1000x order of magnitude of alpha => J shaped distribution
            alpha_val = (mean_val-a)/(b-a) * ((mean_val*(1-mean_val)/std_dev_val**2) - 1)
            beta_val = alpha_val * (1-mean_val) / mean_val
            # Beta function automatically runs has start and end interval from 0 to 1
            prob_vals = beta.cdf(damage_bins_list, alpha_val, beta_val)            
            # Generally, first damage bin has proabbility zero since it is a single value not a range- same for last damage bin that only represents single damage value
            # Exception for first damage bin since and hazard intensity bin representing zero intensity => no damage
            cum_diff_vals = list(np.diff(prob_vals, axis=0, prepend=0, append=prob_vals[-1]))

        for prob in cum_diff_vals:
            probs = {'probabilities': "{:.6f}".format(prob)
                }
            yield probs

def get_codes(header_name, path, extra_keys_in=None, id_suffix='_id'):
    mapping_dict = {}
    header = True
    if extra_keys_in == None:
        extra_keys = []
    else:
        extra_keys = extra_keys_in

    with open(path, "r") as file: 
        for line in file:
            data = line.strip().split(',')
            if header:    
                header_index = data.index(header_name)
                id_index = data.index(f'{header_name}{id_suffix}')
                extra_index = [data.index(extra_key) for extra_key in extra_keys]
                header = False
                continue
            if extra_keys:
                key = tuple([data[header_index]] + [data[index] for index in extra_index])
            else:
                key = data[header_index]
            mapping_dict[key] = data[id_index]
    return mapping_dict

def filter_vuln_dict(vulns_df, countr_dict, country_specific):
    rev_countr_dict = {countr_dict[country]: country for country in countr_dict}
    copy_vulns_df = vulns_df.copy()
    copy_vulns_df[['country_id','attribute2_3_id', 'ranking', 'attribute4_id', 'attribute6_id']] = copy_vulns_df[['country_id','attribute2_3_id', 'ranking', 'attribute4_id', 'attribute6_id']].astype(int)
    # indexes of rows preserved
    # dataframe country_code sorted last
    sorted_vulns_df = copy_vulns_df.sort_values(by=['country_id','attribute6_id','attribute4_id','attribute2_3_id','ranking'], inplace = False)
    header = True

    if country_specific == '':
        unique_df = sorted_vulns_df['country_id'].unique()
    else:
        country_specific_ids = [int(countr_dict[key]) for key in country_specific if key in countr_dict]
        unique_df = sorted_vulns_df[sorted_vulns_df['country_id'].isin(country_specific_ids)]['country_id'].unique()
        copy_vulns_df = copy_vulns_df[copy_vulns_df.loc[:,'country_id'].isin(country_specific_ids)]
    
    for country_id in unique_df:
        length = sorted_vulns_df['country_id'].value_counts()[country_id]
        header = True
        for num, cur_data in sorted_vulns_df[(sorted_vulns_df['country_id'] == country_id)].iterrows():
            if header:
                counter = 1
                print (f'filtering {rev_countr_dict[str(country_id)]}: ', counter, '/', length)
                prev_data = cur_data
                counter+=1
                header = False
                continue

            print (f'filtering {rev_countr_dict[str(country_id)]}: ', counter, '/', length)
            counter+=1
            if (prev_data['country_id'] == cur_data['country_id']) & (prev_data['attribute4_id'] == cur_data['attribute4_id']) & (prev_data['attribute6_id'] == cur_data['attribute6_id']) & (prev_data['attribute2_3_id'] == cur_data['attribute2_3_id']):
                copy_vulns_df.drop(index=num, inplace=True)
            elif cur_data['attribute2_3_id'] == 0:
                copy_vulns_df.drop(index=num, inplace=True)
            else:
                prev_data = cur_data

    copy_vulns_df.loc[:,'vulnerability_id'] = np.arange(1, len(copy_vulns_df) + 1)
    return copy_vulns_df

def main(working_folder, num_damage_bins, coverage_type, oasis_model_folder, data_folder, country_specific, continent_specific, int_mes_types):    
    incr = 1/num_damage_bins
    int_mes_types = int_mes_types.split()
    
    if continent_specific and country_specific:
        print ("Cannot input both specific countries and continents")
        sys.exit()
    
    # produces string that is the name of the folder in which all the model's data and code is contained - default is 'VulnerabilityLibrary'
    path_stem = init_run(working_folder)

    # hazard intensity bins created and a dictionary is outputted 
    int_bins, int_mp_vals = init_int_bins(path_stem)
    
    int_bins_dict = create_int_bins(int_bins, int_mp_vals, int_mes_types)

    int_bins_df = pd.DataFrame(int_bins_dict)
    int_bin_dict_path = PurePath.joinpath(path_stem, int_dict_path)
    int_bins_df.to_csv(int_bin_dict_path, index=False)
    
    # damage bin list does not have repeated start or end
    damage_bins, damage_bins_list = init_damage_bins(incr)
    dam_bins_dict = create_damage_bins(damage_bins)

    damage_bins_df = pd.DataFrame(dam_bins_dict)
    damage_bins_path = PurePath.joinpath(path_stem, oasis_model_folder, dam_bin_path)
    damage_bins_df.to_csv(damage_bins_path, index=False)

    rootdir = PurePath.joinpath(path_stem, data_folder)
    # dictionary of all locations in earthquake model data folder as key and the value is the relative file path
    locations_dict = directories(rootdir, coverage_type)
    # removes continent key in the location_dict dictionary
    location_dict = {country: locations_dict[(continent, country)] for (continent, country) in locations_dict}
    
    # check that continent/country specified is within data - also prevents entering a country name using the continent arge parse command and vice versa
    # location[0] and location[1] refer to continent and country respectively
    for count in continent_specific:
        if continent_specific and (count not in [location[0] for (location, filepath) in locations_dict.items()]):
            print ("Must specify continent within model data")
            sys.exit()

    for count in country_specific:
        if count and (count not in [location[1] for (location, filepath) in locations_dict.items()]):
            print ("Must specify country within model data")
            sys.exit()

    # creates dictionary to pair attrbiutes with attribute ids
    height_path = PurePath.joinpath(path_stem, oasis_model_folder, rel_height_path)
    occup_path = PurePath.joinpath(path_stem, oasis_model_folder, rel_occup_path)
    constr_path = PurePath.joinpath(path_stem, oasis_model_folder, rel_constr_path)
    countr_path = PurePath.joinpath(path_stem, oasis_model_folder, rel_countr_path)

    height_dict = get_codes('attribute4', height_path)
    occup_dict = get_codes('attribute6', occup_path)
    constr_dict = get_codes('attribute2_3', constr_path, extra_keys_in = ['peril_id', 'ranking'])
    countr_dict = get_codes('country', countr_path)

    vulnerability_dict_path = PurePath.joinpath(path_stem, oasis_model_folder, vuln_dict_path)
    # output vulnerability id dictionary - each type of building within each country given unique id 
    vuln_ids = create_vuln_ids(location_dict, height_dict, occup_dict, constr_dict, countr_dict)
    vulns_df = pd.DataFrame(vuln_ids)
    t_zero = time.time()
    vulns_df = filter_vuln_dict(vulns_df, countr_dict, country_specific)
    t_filter = time.time() - t_zero
    vuln_dict = get_vuln_ids(vulns_df, countr_dict, locations_dict)
    vulns_df.to_csv(vulnerability_dict_path, index=False)
    # node_id column is only useful for backend purposes
    t_one = time.time()
    with open (PurePath.joinpath(path_stem, oasis_model_folder, vulnerability_path), 'wb') as dict_file:
        header = True
        current_location = ('','')
        prev_country = 0
        for (continent, country, taxonomy, node_id) in vuln_dict:
            if country != prev_country:
                counter = 1
            # not () and not () functions as NAND logic gate
            if (not(country_specific) and not(continent_specific)) or continent in continent_specific or country in country_specific:
                if country != current_location:
                    current_location = country
                    pathway = location_dict[country]
                    tree = ET.parse(pathway)
                    root = tree.getroot()
                # node id easier to understand than using complicated logic to track progress
                print ('running', continent, country, ': ', counter, '/', sum(1 for key in vuln_dict if key[1] == country))
                counter += 1
                prev_country = country
                intensity_measure = root[0][int(node_id)][0].attrib['imt']
                int_vals = list(map(float,root[0][int(node_id)][0].text.split()))
                mean_LRs = list(map(float,root[0][int(node_id)][1].text.split()))
                coeff_vars = list(map(float,root[0][int(node_id)][2].text.split()))
                std_devs = [mean_LR*coeff_var for mean_LR, coeff_var in zip(mean_LRs, coeff_vars)]
                
                # return list of bin index values for each intensity value used to calulcate a probability
                bin_index_list = get_bin_index(int_bins, int_mp_vals, int_mes_types, intensity_measure)
                # vulnerability id can be found with either taxonomy or node id 
                vuln_id = vuln_dict[(continent, country, taxonomy, node_id)]
                # create vulnerability file with vulnerability ids, correct intensity bin indexes and damage bin indexes
                vuln_data = create_vuln_dict (vuln_id, bin_index_list, damage_bins)
                vuln_temp_df = pd.DataFrame(vuln_data)
                
                # function compute_probs() computes probabilities using beta distribution
                probs_data = compute_probs(int_vals, int_mp_vals, mean_LRs, std_devs, damage_bins_list)
                probs_df = pd.DataFrame(probs_data)

                vuln_df = pd.concat([vuln_temp_df, probs_df], axis = 1)        
                vuln_df.to_csv(dict_file, index=False, header=header)       
                header = False
    print (f'vulnerability dictionary filter took {t_filter} seconds')
    print (f'toolkit took {time.time() - t_one} seconds')
kwargs = vars(parser.parse_args())
main(**kwargs)