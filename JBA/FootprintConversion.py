import rasterio
import numpy as np
import pandas as pd
import csv
from pathlib import PurePath,PurePosixPath
import sys
from tqdm import tqdm

working_folder = 'VulnerabilityLibrary'
raster_filepath = './jba_footprints/PH_TW_20240724_Typhoon_Gaemi_FLRF_U_RD_30m_4326.tif'
oasis_footprint_filepath = './global_flooding_variants/model_data/footprint-U.csv'
area_peril_dict_filepath = './global_flooding_variants/keys_data/areaperil_dict-U.csv'
oasis_filepaths = [area_peril_dict_filepath, oasis_footprint_filepath]
oasis_fieldnames = [["area_peril_id","longitude","latitude"], ["event_id","area_peril_id","intensity_bin_id","probability"]]
int_input_path = 'intensity_bins_input.csv'
int_dict_path = 'intensity_bin_dict-U.csv'

with rasterio.open(raster_filepath) as image:

    max_lat = image.bounds[3]
    min_lat = image.bounds[1]
    max_long = image.bounds[2]
    min_long = image.bounds[0]
    no_height_pixels = image.height
    no_width_pixels = image.width
    raster = image.read(1)

print('rasterio info')
print(f'  Filepath: {raster_filepath}')
print(f'  Latitude - min : {min_lat:.4f} max : {max_lat:.4f}')
print(f'  Longitude - min : {min_long:.4f} max : {max_long:.4f}')
print(f'  Height {no_height_pixels}px')
print(f'  Width {no_width_pixels}px')

def init_run(working_folder):
    model_path = PurePath(__file__)
    parent = model_path.parents
    for each in parent:
        if PurePosixPath(each).name == working_folder:
            path_stem = each
    return path_stem

def init_int_bins(path_stem, max_int_val):
    # create three lists for lower bound, upper bound and mid point point values of intensity bins
    int_bin_vals = []
    int_bins = []
    int_mp_vals = []
    with open(PurePath.joinpath(path_stem, int_input_path)) as bins_file:
        # Read in bins data from opened file
        for i, line in enumerate (bins_file):
            line = line.strip()
            if i and float(line) <= max_int_val:
                int_bin_vals.append(float(line))
            # condition to repeat first value
            if not (i-1) and float(line) <= max_int_val:
                int_bin_vals.append(float(line))
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

def create_footprint_and_areaperil_dict(int_bins):

    width_per_pixel = (max_long - min_long) / no_width_pixels
    height_per_pixel = (max_lat - min_lat) / no_height_pixels

    lat_incr = 0
    areaperil_id = 0

    for row in tqdm(raster, desc='footprint_area_peril_gen'):

        long_incr = 0
        latitude = round(max_lat - (height_per_pixel * (0.5 + lat_incr)), 6)

        for intensity in row:

            longitude = round(width_per_pixel * (0.5 + long_incr) + min_long, 6)
            long_incr += 1

            if intensity < -3e+38:
                continue

            if intensity > 6:
                intensity = 6

            areaperil_id += 1

            bin_from_differences = intensity - int_bins['bin_from']
            bin_to_differences = int_bins['bin_to'] - intensity
            differences_multiplied = bin_to_differences * bin_from_differences

            intensity_bin_id = int_bins['bin_index'][differences_multiplied.idxmax()] #Edge Case for when intensity value is equal to a bin edge value is currently being assigned the lower intensity bin_id
            footprint_row = { "event_id": 1, "area_peril_id": areaperil_id, "intensity_bin_id": intensity_bin_id, "probability": 1}
            areaperil_dict = { "area_peril_id": areaperil_id, "longitude": longitude, "latitude": latitude}
            yield (areaperil_dict, footprint_row)
        lat_incr += 1

def create_files(filepaths, fieldnames, generator):

    with open(filepaths[0], mode='w', newline='') as areaperil_dict, open(filepaths[1], mode='w', newline='') as footprint:

        writer1 = csv.DictWriter(areaperil_dict, fieldnames[0])
        writer2 = csv.DictWriter(footprint, fieldnames[1])

        writer1.writeheader()
        writer2.writeheader()

        for row in generator:
            writer1.writerow(row[0])
            writer2.writerow(row[1])

def main(working_folder = 'VulnerabilityLibrary', int_mes_types = ['flood_depth_metres'], max_int_val = 6):

    path_stem = init_run(working_folder)

    print('Initialising bins..')
    int_bins, int_mp_vals = init_int_bins(path_stem, max_int_val)
    int_bins_dict = create_int_bins(int_bins, int_mp_vals, int_mes_types)

    int_bins_df = pd.DataFrame(int_bins_dict)

    print('Creating footprint & area peril generator...')
    footprint_area_peril_gen = create_footprint_and_areaperil_dict(int_bins_df)

    print('Saving files...')
    create_files(oasis_filepaths, oasis_fieldnames, footprint_area_peril_gen)

main()
