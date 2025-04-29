import rasterio
import numpy as np
import pandas as pd
import csv
from pathlib import PurePath,PurePosixPath, Path
import sys
from tqdm import tqdm
import argparse

parser = argparse.ArgumentParser(description='Extract model footprints from JBA raster `.tif` files.')
parser.add_argument('-r', '--rasterfile', required=True, help='Path to `.tif` raster file')
parser.add_argument('-w', '--workingfolder', help='Path to working folder')
parser.add_argument('-f', '--fooprintpath', default='model_data/footprint.csv',
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

args = vars(parser.parse_args())

raster_filepath = Path(args.get('rasterfile'))
working_folder = args.get('working_folder')
if working_folder is None:
    working_folder = raster_filepath.parent
else:
    working_folder = Path(working_folder)

oasis_footprint_filepath = working_folder / args.get('fooprintpath')
area_peril_dict_filepath = working_folder / args.get('areaperilpath')
print(f'Footprint path: {oasis_footprint_filepath}')
print(f'Area peril path: {oasis_footprint_filepath}')
int_input_path = args.get('intensity_input')
oasis_filepaths = [area_peril_dict_filepath, oasis_footprint_filepath]
oasis_fieldnames = [["area_peril_id","longitude","latitude"], ["event_id","area_peril_id","intensity_bin_id","probability"]]
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

            intensity *= intensity_scaling

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

    # Make directories
    for path in filepaths:
        path.parent.mkdir(parents=True, exist_ok=True)

    with open(filepaths[0], mode='w', newline='') as areaperil_dict, open(filepaths[1], mode='w', newline='') as footprint:

        writer1 = csv.DictWriter(areaperil_dict, fieldnames[0])
        writer2 = csv.DictWriter(footprint, fieldnames[1])

        writer1.writeheader()
        writer2.writeheader()

        for row in generator:
            writer1.writerow(row[0])
            writer2.writerow(row[1])

def main():
    print('Initialising bins..')
    int_bins, int_mp_vals = init_int_bins(max_int_val)
    int_bins_dict = create_int_bins(int_bins, int_mp_vals, int_mes_types)

    int_bins_df = pd.DataFrame(int_bins_dict)

    print('Creating footprint & area peril generator...')
    footprint_area_peril_gen = create_footprint_and_areaperil_dict(int_bins_df)

    print('Saving files...')
    create_files(oasis_filepaths, oasis_fieldnames, footprint_area_peril_gen)

main()
