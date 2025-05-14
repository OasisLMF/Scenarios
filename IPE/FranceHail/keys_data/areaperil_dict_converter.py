from shapely.geometry import Polygon
import geopandas as gpd
import pandas as pd
from pathlib import Path
import ipdb
from math import isnan
from tqdm import tqdm

file_path = Path(__file__).parent.parent / 'source_data/areaperil_dict.parquet'
print('Reading areaperil_dict file: ', file_path)

df = pd.read_parquet(file_path)
polygon_point_order = range(1, 703)

def proccess_row(row):
    filtered_row = [(row[f"lon{i}"], row[f"lat{i}"]) for i in polygon_point_order if not isnan(row[f"lon{i}"])]
    return Polygon(filtered_row)

print('Creating geometry...')
gdf_peril_area = gpd.GeoDataFrame(df)
tqdm.pandas(desc='applying geometry')
gdf_peril_area["geometry"] = gdf_peril_area.progress_apply(
    lambda row: proccess_row(row), axis=1)

# remove unused coordinate
print('Removing unused coordinates...')
gdf_peril_area.drop(columns=sum(([f"lon{i}", f"lat{i}"] for i in polygon_point_order), []), inplace=True)

# store to parquet format
print('Storing parquet...')
gdf_peril_area.to_parquet(Path(__file__).parent / "areaperil_dict.parquet")
