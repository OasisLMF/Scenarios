<img src="https://oasislmf.org/packages/oasis_theme_package/themes/oasis_theme/assets/src/oasis-lmf-colour.png" alt="Oasis LMF logo" width="250"/>

# Hurricane Michael, Oct 2018

A single-event Oasis model of the wind footprint of Hurricane Michael (October 11-12 2018), provided by Applied Research Associates (ARA). Michael made landfall near Mexico Beach, Florida as a Category 4 hurricane before weakening to a tropical storm.

## Contents

| Path | |
|---|---|
| `source_data/2018-Michael_windgrid_ver36.csv` | ARA's wind grid for the event: gust (`Vg_mph`) and sustained (`Vsus_mph`) wind speeds by latitude and longitude |
| `model_data/` | Oasis model files (footprint, vulnerability, damage bins, events, occurrence) |
| `keys_data/` | Lookup: each location is matched to the nearest wind grid point by latitude and longitude, for tropical cyclone wind (`WTC`) |
| `meta-data/model_settings.json` | Model name and description |
| `analysis_settings.json` | Example analysis settings |
| `tests/` | Example exposure (OED location files) |

## Running

With the [Oasis MDK](https://github.com/OasisLMF/OasisLMF) installed, from this folder:

```
oasislmf model run --config oasislmf.json
```

See the [top-level README](../../README.md) for the terms of use and disclaimer.
