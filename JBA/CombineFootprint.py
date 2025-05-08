import argparse
from pathlib import Path
import pandas as pd

import ipdb

parser = argparse.ArgumentParser(description='Combine multiple perils into single footprint')
parser.add_argument('-mp', '--model-paths', nargs='+', help='Paths to model directories.')
parser.add_argument('-p', '--perils', nargs='+', help='Peril ids for corresponding footprint files')
parser.add_argument('-f', '--footprint-path', default='model_data/footprint.csv', help='Footprint path from model path')
parser.add_argument('-a', '--areaperil-path', default='keys_data/areaperil_dict.csv', help='areaperil_dict path from model path')
parser.add_argument('-s', '--save-path', default='combined/', help='Path to save', type=Path)

args = vars(parser.parse_args())

model_paths = args['model_paths']
perils = args['perils']
footprint_subpath = args['footprint_path']
areaperil_subpath = args['areaperil_path']
save_path = args['save_path']

assert len(model_paths) == len(perils)
print('Combining models: ')
print(model_paths)
print('Associated perils: ')
print(perils)

footprint_paths = [Path(model_path) / footprint_subpath for model_path in model_paths]
areaperil_paths = [Path(model_path) / areaperil_subpath for model_path in model_paths]

areaperil_offset = 0

combined_footprint = []
combined_areaperil_dict = []

print('Offsetting area_peril_id..')
for footprint_path, areaperil_path, peril in zip(footprint_paths, areaperil_paths, perils):
    footprint_df = pd.read_csv(footprint_path)
    areaperil_df = pd.read_csv(areaperil_path)

    areaperil_df['area_peril_id'] += areaperil_offset
    areaperil_df['peril_id'] = peril

    footprint_df['area_peril_id'] += areaperil_offset

    combined_footprint.append(footprint_df)
    combined_areaperil_dict.append(areaperil_df)

    areaperil_offset = areaperil_df['area_peril_id'].max()

print('Concatenating..')
combined_footprint = pd.concat(combined_footprint)
combined_areaperil_dict = pd.concat(combined_areaperil_dict)

print('Saving...')
footprint_save_path = save_path / footprint_subpath
areaperil_save_path = save_path / areaperil_subpath
print('footprint save path: ', footprint_save_path)
print('areaperil save path: ', areaperil_save_path)

footprint_save_path.parent.mkdir(parents=True, exist_ok=True)
areaperil_save_path.parent.mkdir(parents=True, exist_ok=True)

combined_footprint.to_csv(footprint_save_path, index=False)
combined_areaperil_dict.to_csv(areaperil_save_path, index=False)
