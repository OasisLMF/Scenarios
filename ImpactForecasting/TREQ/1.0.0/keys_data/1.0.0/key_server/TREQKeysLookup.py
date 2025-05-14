__all__ = [
    'TREQKeysLookup'
]

# Python standard library imports
import json
import os

# Python custom library imports
import pandas as pd
import numpy as np

# OasisLMF imports
from oasislmf.lookup.builtin import Lookup
from oasislmf.utils.coverages import COVERAGE_TYPES
from oasislmf.utils.status import OASIS_KEYS_STATUS
from oasislmf.utils.peril import PERILS
from oasislmf.utils.log import oasis_log
from oasislmf.utils.data import get_ids


class TREQKeysLookup(Lookup):
    """
    model keys lookup.
    """

    @oasis_log()
    def __init__(self, config, config_dir=None, user_data_dir=None, output_dir=None):
                 
        """
        Initialise the static data required for the lookup.
        """

        super(self.__class__, self).__init__(config, config_dir, user_data_dir, output_dir)

        # format path to key files
        def key_path(base_file_name, file_type='csv'):
            file_path = os.path.join(keys_data_directory, f'{self.MODEL_NAME}_{base_file_name}.{file_type}')
            return file_path

        self.MODEL_NAME = self.config.get('model').get('model_id')
        keys_data_directory = self.config.get('keys_data_path')
        self.LOCATION_HIERARCHY_FILE = key_path('Location_Hierarchy')
        self.PERIL_FILE = key_path('PerilID_Dict')
        self.LOCATION_FILES_DICT = key_path('AreaID_Dict', file_type='parquet')
        self.LOCATION_PERIL_FILES_DICT = key_path('AreaperilID_Dict', file_type='parquet')
        self.OED_TRANSFORMATION_FILE = key_path('required_columns_from_oed', file_type='json')
        self.COUNTRIES_FILE = key_path('Countries')
        self.VULNERABILITY_LOOKUP_FILE = key_path('Vulnerability_Dict', file_type='parquet')

        self.INPUT_COLUMNS = ['SITENUMBER','COUNTRYISO','LOCPERILSCOVERED','OCCUPANCYCLASS','OCCUPANCYSCHEME','BLDG','CONTENTS','TE']
        self.RELEVANT_COLUMNS = ['ACCNUMBER','LOCNUMBER','COUNTRYCODE','OCCUPANCYCODE',
                                 'POSTALCODE','LOWRESCRESTA','HIGHRESCRESTA',
                                 'GEOGSCHEME1','GEOGNAME1','GEOGSCHEME2','GEOGNAME2',
                                 'GEOGSCHEME3','GEOGNAME3','GEOGSCHEME4','GEOGNAME4','GEOGSCHEME5','GEOGNAME5',
                                 'BUILDINGTIV','CONTENTSTIV','BITIV',
                                 'PORTNUMBER','LOC_ID','LOCPERILSCOVERED']
        self.PERIL_ID = [ PERILS['earthquake']['id']]
    
    
    @oasis_log()
    # Insert required columns into OED data frame.
    def insert_required_columns(self, df_ptf):
        
        # Set class codes according to values in lookup json.
        def set_class_codes_simple(class_codes_keys, class_codes):
            return class_codes_keys.map(class_codes).fillna(class_codes['Otherwise'])
        
        # Extract lookup codes from json
        with open(self.OED_TRANSFORMATION_FILE, 'r') as f:
            lookup_codes = json.load(f)

        # Only consider the relavant columns
        df_ptf = df_ptf[[x for x in df_ptf.columns.values if x in self.RELEVANT_COLUMNS]]

        # Add required columns

        # General columns
        df_ptf['INDEX'] = df_ptf.index
        df_ptf['SITENUMBER'] = df_ptf['INDEX'] + 1
        df_ptf['COUNTRYCODE'] = df_ptf['COUNTRYCODE']#.str.lower()
        df_ptf['COUNTRYISO'] = pd.to_numeric(df_ptf['COUNTRYCODE'].map(lookup_codes['country_iso_codes']))
        df_ptf['BLDG'] = df_ptf['BUILDINGTIV'].apply(lambda x: 1 if x > 0 else 0)
        df_ptf['CONTENTS'] = df_ptf['CONTENTSTIV'].apply(lambda x: 1 if x > 0 else 0)
        df_ptf['TE'] = df_ptf['BITIV'].apply(lambda x: 1 if x > 0 else 0)
        df_ptf['OCCUPANCYSCHEME'] = 'IFE'
        
        # Occupancy & Construction
        df_ptf['OCCUPANCYCLASS']  = set_class_codes_simple(df_ptf['OCCUPANCYCODE'].astype(str), class_codes=lookup_codes['occupancy_class_codes'])

        geogs_cols = list([col for col in df_ptf.columns if 'GEOGSCHEME' in col])
        geogn_cols = [gc.replace('GEOGSCHEME', 'GEOGNAME') for gc in geogs_cols]

        # Come back to the GeogSchemes --> what OED fields should actually be used?
        GeogSchemes = ['IFSTA', 'IFDIS', 'CRL', 'CRH']
        Precisions = ['STATE', 'DISTRICT', 'CRESTAZONE', 'CRESTASUBZONE']

        df_ptf[geogs_cols] = df_ptf[geogs_cols].replace(GeogSchemes, Precisions)
        df_geo = df_ptf[geogs_cols + geogn_cols]

        for geogs_col in geogs_cols:
            i_scheme = geogs_cols.index(geogs_col)
            i_name = geogn_cols.index(geogs_col.replace('GEOGSCHEME', 'GEOGNAME'))

            a = df_geo.pivot(columns=geogs_cols[i_scheme], values=geogn_cols[i_name])
            df_ptf = pd.concat([df_ptf, a], axis=1)

        df_ptf = df_ptf.loc[:, df_ptf.columns.notnull()]
        df_ptf = df_ptf.groupby(level=0, axis=1).first()

        return df_ptf

    
    @oasis_log()
    # Process location rows - passed in as a pandas dataframe.
    def process_locations(self, df_ptf_orig):
        
        # Portfolio
        df_ptf = df_ptf_orig.copy()
        
        # Check for loc_id
        df_ptf.columns = df_ptf.columns.str.lower()
        if 'loc_id' not in df_ptf:
            df_ptf['loc_id'] = get_ids(df_ptf, ['portnumber', 'accnumber', 'locnumber'])
        df_ptf.columns = df_ptf.columns.str.upper()

        # Insert required columns and check for missing ones
        df_ptf = self.insert_required_columns(df_ptf)
        required_columns = self.INPUT_COLUMNS
        missing_fields = [x for x in required_columns if x not in df_ptf.columns.values]
        if missing_fields:
            raise Exception('Some required columns missing ' + str(missing_fields) + ', check your input file!')

        # Load country and location hiererchy files
        df_countries = pd.read_csv(self.COUNTRIES_FILE)
        df_location_fields = pd.read_csv(self.LOCATION_HIERARCHY_FILE)
        
        # Go through country-by-country
        for country in df_countries['CountryISO']:
            
            df_ptf_country = df_ptf.loc[df_ptf['COUNTRYISO'] == int(country)]
            df_location_fields_country = df_location_fields.loc[df_location_fields['CountryISO'] == int(country)]
            
            if len(df_ptf_country.index) > 0:
                # check if input data frame contains at least one supported location field
                location_hierarchy = pd.Series(df_location_fields_country.PrecisionName.values,index=df_location_fields_country.HierarchyOrder).to_dict()
                location_fields = list(location_hierarchy.values())
                
                # If gridcell is an option in Location Hierarchy, replace "gridcell" with "longitude" and "latitude"
                if 'GRIDCELL' in location_fields:
                    location_fields.remove('GRIDCELL')
                    location_fields.extend(['LONGITUDE','LATITUDE'])
                
                # Which resolutions are given in the portfolio?
                ptf_location_fields = [x for x in df_ptf_country.columns.values if x in location_fields]
                if not ptf_location_fields or ptf_location_fields==['LONGITUDE'] or ptf_location_fields==['LATITUDE']:
                    raise Exception('No location field available in input file. Add at least one (or both coordinates) of these ' + str(location_fields))
                
                # add required output fields with initial values to portfolio
                df_ptf_country['STATUS'] = OASIS_KEYS_STATUS['success']['id']
                df_ptf_country['MESSAGE'] = None
                
                # Peril(s) covered by the model and precedence (based on the order in if_utiles)
                df_perils = pd.DataFrame(data={'PERILSTRING':self.PERIL_ID, 'PRECEDENCE':range(1, len(self.PERIL_ID)+1)})
                
                # Peril(s) 
                df_perils_model = pd.read_csv(self.PERIL_FILE)
                
                # Assign perilID
                df_ptf_country = self.assign_perilID(df_ptf_country, df_perils, df_perils_model)
                
                # assign areaperil ID to portfolio
                df_finalloc = None

                for hierarchy in sorted(location_hierarchy):
                    
                    location_field = location_hierarchy[hierarchy].upper().replace(' ', '')
                    
                    if location_field in ptf_location_fields or 'GRIDCELL' in location_field and all(x in ptf_location_fields for x in ['LATITUDE', 'LONGITUDE']):

                        geocoded, not_geocoded = self.assign_areaID(df_ptf_country, location_field, int(country))
                        geocoded = self.assign_areaperilID(geocoded)
                        
                        if not not_geocoded.empty:

                            if df_finalloc is not None:
                                df_finalloc = pd.concat([df_finalloc,geocoded])
                            else:
                                df_finalloc = geocoded
                            fields = [f for f in not_geocoded.columns.values if f not in ['AREAPERIL_ID','NAME','REGION','MASTERTABLEID', 'GRIDCELL_ID', 'AREA_ID', 'MTID', 'TIER']]
                            df_ptf_country = not_geocoded.loc[:,fields]

                        else:

                            if df_finalloc is not None:
                                df_finalloc = pd.concat([df_finalloc,geocoded])
                            else:
                                df_finalloc = geocoded
                            break

                del df_ptf, df_ptf_country

                if not not_geocoded.empty:
                    df_finalloc = pd.concat([df_finalloc,not_geocoded])

                df_finalloc.loc[df_finalloc['AREAPERIL_ID'].isnull(),['STATUS','MESSAGE','AREAPERIL_ID']] = [OASIS_KEYS_STATUS['nomatch']['id'],'Failed to geocode',-9999]

                # unpivot bldg, contents and TE to separate rows and assign numerical coverage ID
                df_coverages = pd.DataFrame(data={'COVSTRING':['BLDG','CONTENTS','TE'], 'COVERAGE':[COVERAGE_TYPES['buildings']['id'],COVERAGE_TYPES['contents']['id'],COVERAGE_TYPES['bi']['id']]})
                df_withcov = self.assign_coverageID(df_finalloc, df_coverages)
                del df_finalloc, df_coverages

                # assign vulnerability ID
                df_withvuln = self.assign_vulnerabilityID(df_withcov)
                del df_withcov
        
                #return df_withvuln
                for item in self.format_output(df_withvuln):
                    yield item
    
    
    @oasis_log()
    def assign_perilID(self, df_in, df_perils, df_perils_model):
        
        # Add semicolons if necessary
        # Split into subperils at the semicolons
        # Drop the original peril column from portfolio
        df_in['LOCPERILSCOVERED'] = df_in['LOCPERILSCOVERED'].apply(lambda x: x +';'*(2-x.count(';')))
        df_in[['P1','P2','P3']] = df_in['LOCPERILSCOVERED'].str.split(';', expand=True)
        df_in.drop(columns =['LOCPERILSCOVERED'], inplace = True)
        
        # Melt P1, P2, and P3 into a single column (PERILSTRING) and strip whitespace
        fields = [x for x in list(df_in.columns.values) if x not in ['P1','P2','P3']]
        df_meltperil = pd.melt(df_in, id_vars=fields, value_vars=['P1','P2','P3'], var_name='TEMPPERIL', value_name='PERILSTRING')
        df_meltperil.PERILSTRING = df_meltperil.PERILSTRING.str.strip()
        
        df_out = pd.merge(df_meltperil, df_perils, how='left', on=['PERILSTRING'])
        df_out[['PRECEDENCE']] = df_out[['PRECEDENCE']].fillna(0)
        df_out['PRECEDENCE'] = df_out['PRECEDENCE'].astype(int)
        
        # Assign peril id
        df_perils_model.columns = df_perils_model.columns.str.upper()
        df_out = pd.merge(df_out, df_perils_model, how='left', left_on=['PERILSTRING'], right_on=['PERIL_CODE'])
        df_out[['PERIL_ID']] = df_out[['PERIL_ID']].fillna(0)
        df_out['PERIL_ID'] = df_out['PERIL_ID'].astype('int32')
     
        return df_out.loc[df_out['PRECEDENCE'] != 0,:]
    
    
    @oasis_log()
    def assign_areaID(self, df_in, location_field, country):

        df_in[location_field] = df_in[location_field].astype(str)
        df_in[location_field] = np.where(df_in[location_field].str.endswith('.0'), df_in[location_field].str.rstrip('.0'), df_in[location_field])
        df_in[location_field] = df_in[location_field].str.upper()

        aid_filter = [
            ('PrecisionName', '==', location_field),
            ('CountryISO', '==', country),
            ('UnitName', 'in', list(df_in[location_field].unique()))
        ]
        df_admin = pd.read_parquet(self.LOCATION_FILES_DICT, filters=aid_filter)
        df_admin.columns = df_admin.columns.str.upper()
        df_admin = df_admin.rename(columns={'UNITNAME': location_field})
        df_admin[location_field] = df_admin[location_field].astype(str)
        df_admin[location_field] = df_admin[location_field].str.upper()
        
        df_in.columns = df_in.columns.str.upper()
        df_admin.columns = df_admin.columns.str.upper()

        df_temp = pd.merge(df_in, df_admin, how='left', on=['COUNTRYISO', location_field])
        df_temp.drop(columns = 'UNITID', inplace = True)
        
        not_geocoded = df_temp[df_temp['AREA_ID'].isnull()]
        not_geocoded = not_geocoded[df_in.columns]

        geocoded = df_temp[np.isfinite(df_temp['AREA_ID'])]
        
        return geocoded, not_geocoded
    
    
    @oasis_log()
    def assign_areaperilID(self, df_in):
        df_in.columns = df_in.columns.str.upper()
        aid_filter = [
            ('area_id', 'in', df_in['AREA_ID'].unique())
        ]
        df_admin = pd.read_parquet(self.LOCATION_PERIL_FILES_DICT, filters=aid_filter)
        df_admin.columns = df_admin.columns.str.upper()
        geocoded = pd.merge(df_in, df_admin, on = ['AREA_ID', 'PERIL_ID'])
        return geocoded
    
    
    @oasis_log()
    def assign_coverageID(self, df_in, df_coverage):
        fields = [x for x in list(df_in.columns.values) if x not in ['BLDG','CONTENTS','TE']]
        df_meltcoverage = pd.melt(df_in, id_vars=fields, value_vars=['BLDG','CONTENTS','TE'], var_name='COVSTRING', value_name='TIV')
        df_out = pd.merge(df_meltcoverage, df_coverage, how='left', on=['COVSTRING'])
        return df_out


    @oasis_log()
    def assign_vulnerabilityID(self, df_in):
        merging_cols = ['OCCUPANCYSCHEME', 'OCCUPANCYCLASS', 'PRECEDENCE', 'COVERAGE', 'COUNTRYISO', 'REGION']
        df_vuln = pd.read_parquet(self.VULNERABILITY_LOOKUP_FILE)
        df_out = pd.merge(df_in, df_vuln, on=merging_cols, how='left')
        df_out.loc[df_out['VULNERABILITY_ID'].isnull() & df_out['MESSAGE'].isnull(), ['STATUS', 'MESSAGE']] = [OASIS_KEYS_STATUS['nomatch']['id'], 'Failed to assign vulnerability function']
        df_out.loc[df_out['VULNERABILITY_ID'].isnull(), ['VULNERABILITY_ID']] = -9999
        return df_out
    
    
    @oasis_log()
    def format_output(self, df_in):
        df_in = df_in.sort_values(by=['SITENUMBER','COVERAGE'])
        df_in = df_in.reset_index(drop=True)
        df_selected = df_in[['STATUS','PERIL_CODE','AREAPERIL_ID','COVERAGE','MESSAGE','SITENUMBER','VULNERABILITY_ID','LOC_ID']].copy()
        df_selected.loc[:,['AREAPERIL_ID','COVERAGE','SITENUMBER','VULNERABILITY_ID']] = df_selected.loc[:,['AREAPERIL_ID','COVERAGE','SITENUMBER','VULNERABILITY_ID']].astype(int)
        df_selected.columns = ['status','peril_id','area_peril_id','coverage','message','id','vulnerability_id','loc_id']
        df_selected['coverage_type'] = pd.Series(data=df_selected['coverage'].values, dtype=object)
        return df_selected.to_dict('index').values()
