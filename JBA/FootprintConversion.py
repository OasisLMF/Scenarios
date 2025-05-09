import rasterio
import numpy as np
import pandas as pd
import csv
from pathlib import PurePath,PurePosixPath, Path
import sys
from tqdm import tqdm
import argparse
import json

import ipdb

parser = argparse.ArgumentParser(description='Extract model footprints from JBA raster `.tif` files.')
parser.add_argument('-r', '--rasterfile', help='Path to `.tif` raster file')
parser.add_argument('-w', '--workingfolder', help='Path to working folder')
parser.add_argument('-f', '--footprintpath', default='model_data/footprint.csv',
                    help='Relative path to footprint file.')
parser.add_argument('-a', '--areaperilpath', default='keys_data/areaperil_dict.csv',
                    help='Relative path to area peril file.')
parser.add_argument('-i', '--intensity-input', default='./intensity_bins_input.csv',
                    help='Path to intensity bins input file')
parser.add_argument('-mi', '--max-intensity', default=600,
                    help='Max intensity bin value')
parser.add_argument('--intensity-unit', default='flood_depth_centimetres',
                    help='Units for intensity bins')
parser.add_argument('--scale', default=100, help='Scale the intensity. Useful for converting footprint units. Default to 100 (converting meters to centimeters).')
parser.add_argument('-c', '--config', help="Path to config file", type=Path)

args = vars(parser.parse_args())

config = args.pop('config')
if config is not None:
    with open(config, 'r') as f:
        config = json.load(f)

args.update(config)

raster_filepath = Path(args.get('rasterfile'))
working_folder = args.get('workingfolder')
if working_folder is None:
    working_folder = raster_filepath.parent
else:
    working_folder = Path(working_folder)

oasis_footprint_filepath = working_folder / args.get('footprintpath')
area_peril_dict_filepath = working_folder / args.get('areaperilpath')
int_input_path = args.get('intensity_input')
max_int_val = args.get('max_intensity')
int_mes_types = [args.get('intensity_unit')]
intensity_scaling = float(args.get('scale'))

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

def init_int_bins(max_int_val):
    # create three lists for lower bound, upper bound and mid point point values of intensity bins
    int_bin_vals = []
    int_bins = []
    int_mp_vals = []
    with open(int_input_path) as bins_file:
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

def init_bins(max_int_val):
    int_bin_vals = []
    with open(int_input_path) as bins_file:
        # Read in bins data from opened file
        for i, line in enumerate (bins_file):
            line = line.strip()
            if i and float(line) <= max_int_val:
                int_bin_vals.append(float(line))

    if sorted(int_bin_vals) != int_bin_vals:
        raise Exception('input intensity bins must be arranged in order of size...')

    return int_bin_vals


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

def generate_poisition_array(min_pos, max_pos, no_pixels):
    # Creates longitude and latitude grids based on max positions and the number of pixels.
    per_pixel = (max_pos - min_pos) / no_pixels
    return np.round(np.arange(min_pos + 0.5*per_pixel, max_pos, per_pixel), 6)


def main():
    int_bins = init_bins(max_int_val)
    footprint = raster


    # Filter low vals
    footprint = np.where(footprint < -3e28, 0, footprint)

    # Latitude and Longitude arrays
    print("Generating lat longs")
    latitude = generate_poisition_array(min_lat, max_lat, no_height_pixels)[::-1] # reverse
    longitude = generate_poisition_array(min_long, max_long, no_width_pixels)

    print("Filtering footprint")
    nonzero_ids = np.nonzero(footprint)
    footprint = footprint[nonzero_ids]
    footprint *= intensity_scaling

    print("Creating bins")
    # Make bins
    # Note right = False means bins[i-1] <= x < bins[i]
    # zero bin no longer required but +1 to all bins to include it
    # > max_int_val will have a bin index len(int_bins)
    footprint_bins = np.digitize(footprint, int_bins, right=False) + 1

    print("Saving...")
    area_peril_ids = range(1, len(footprint_bins) + 1)

    area_peril_df = pd.DataFrame(data={
        'area_peril_id': area_peril_ids,
        'latitude': latitude[nonzero_ids[0]],
        'longitude': longitude[nonzero_ids[1]],
    })

    area_peril_dict_filepath.parent.mkdir(parents=True, exist_ok=True)
    area_peril_df.to_csv(area_peril_dict_filepath, index=False)
    print(f"Saved area peril file: {area_peril_dict_filepath}")

    footprint_df = pd.DataFrame(data={
        'event_id': 1,
        'area_peril_id': area_peril_ids,
        'intensity_bin_id': footprint_bins,
        'probability': 1
    })

    oasis_footprint_filepath.parent.mkdir(parents=True, exist_ok=True)
    footprint_df.to_csv(oasis_footprint_filepath, index=False)
    print(f"Saved footprint file: {oasis_footprint_filepath}")

main()
