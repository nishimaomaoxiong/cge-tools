
# coding: utf-8

# # Data preparation for CECP CoP21 website
# File locations:

# Cell:

from os.path import join

GDX_DIR = join('..', '..', '..', 'crem', 'gdx')
OUT_DIR = join('..', '..', '..', 'cecp-cop21-data')
GDX_DIR


# ## 1. Run C-REM
# Run the next cell will run the model eight times, which takes a *very long time*. The commands are provided for illustration.
# 
# Currently, separate commits of C-REM must be used to run the base and 'less-GDP' cases.
# 
# See [issue #35](https://github.com/mit-jp/crem/issues/35).

# Cell:

get_ipython().run_cell_magic('bash', '', '# C-REM runs\ncrem gdx/result_urban_exo -- --case=default\ncrem gdx/result_cint_n_3 -- --case=cint_n --cint_n_rate=3\ncrem gdx/result_cint_n_4 -- --case=cint_n --cint_n_rate=4\ncrem gdx/result_cint_n_5 -- --case=cint_n --cint_n_rate=5\n# Low-growth cases\ncrem gdx/result_urban_exo_lessGDP -- --case=default\ncrem gdx/result_cint_n_3_lessGDP -- --case=cint_n --cint_n_rate=3\ncrem gdx/result_cint_n_4_lessGDP -- --case=cint_n --cint_n_rate=4\ncrem gdx/result_cint_n_5_lessGDP -- --case=cint_n --cint_n_rate=5')


# ## 2. Preprocess the GDX files
# Some of the quantities used below are stored in the GAMS parameters `report(*,*,*)` and `egyreport2(*,*,*,*)`, which pyGDX cannot handle. The cell below runs the simple GAMS script `pre.gms` to produce a new file named `*foo*_extra.gdx` with the pyGDX-friendly variables `ptcarb_t(t)`, `pe_t(e,r,t)` and `cons_t(r,t)`.

# Cell:

get_ipython().run_cell_magic('win-bash', '', 'gams pre.gms --file=gdx/result_urban_exo\ngams pre.gms --file=gdx/result_cint_n_3\ngams pre.gms --file=gdx/result_cint_n_4\ngams pre.gms --file=gdx/result_cint_n_5\ngams pre.gms --file=gdx/result_urban_exo_lessGDP\ngams pre.gms --file=gdx/result_cint_n_3_lessGDP\ngams pre.gms --file=gdx/result_cint_n_4_lessGDP\ngams pre.gms --file=gdx/result_cint_n_5_lessGDP')


# ## 3. Read the GDX files

# Cell:

# Load all the GDX files
import csv
from collections import OrderedDict
from os import makedirs as mkdir
from os.path import join

import gdx
from numpy import nan
from openpyxl import load_workbook
import pandas as pd
import xray

FILES = [
    ('bau', 'result_urban_exo.gdx'),
    ('3', 'result_cint_n_3.gdx'),
    ('4', 'result_cint_n_4.gdx'),
    ('5', 'result_cint_n_5.gdx'),
    ('bau_lo', 'result_urban_exo_lessGDP.gdx'),
    ('3_lo', 'result_cint_n_3_lessGDP.gdx'),
    ('4_lo', 'result_cint_n_4_lessGDP.gdx'),
    ('5_lo', 'result_cint_n_5_lessGDP.gdx'),
    ]

raw = OrderedDict()
extra = dict()
for case, fn in FILES:
    raw[case] = gdx.File(join(GDX_DIR, fn))
    extra[case] = gdx.File(join(GDX_DIR, fn.replace('.gdx', '_extra.gdx')))

CREM = raw['bau']
cases = pd.Index(raw.keys(), name='case')
time = pd.Index(filter(lambda t: int(t) <= 2030, CREM.set('t')))


# Cell:

# List all the parameters available in each file
#CREM.parameters()

# Temporary container for read-in data
arrays = {}

def label(variable, desc, unit_long, unit_short):
    """Add some descriptive attributes to an xray.DataArray."""
    arrays[variable].attrs.update({'desc': desc, 'unit_long': unit_long,
                                   'unit_short': unit_short})


# Cell:

# GDP
temp = [raw[case].extract('gdp_ref') for case in cases]
arrays['GDP'] = xray.concat(temp, dim=cases).sel(rs=CREM.set('r'))                     .rename({'rs': 'r'})
label('GDP', 'Gross domestic product',
      'billions of U.S. dollars, constant at 2007', '10⁹ USD')

arrays['GDP_aagr'] = ((arrays['GDP'][:,:,1:].values / arrays['GDP'][:,:,:-1])
                      ** (1 / CREM.extract('lp')) - 1) * 100
label('GDP_aagr', 'Gross domestic product, average annual growth rate',
      'percent', '%')

arrays['GDP_delta'] = (arrays['GDP'] / arrays['GDP'].sel(case='bau') - 1) * 100
label('GDP_delta', 'Change in gross domestic product relative to BAU',
      'percent', '%')


# Cell:

# CO2 emissions
temp = []
for case in cases:
    temp.append(raw[case].extract('sectem').sum('g') +
        raw[case].extract('houem'))
arrays['CO2_emi'] = xray.concat(temp, dim=cases)
label('CO2_emi', 'Annual CO₂ emissions',
      'millions of tonnes of CO₂', 'Mt')


# Cell:

# Air pollutant emissions
temp = []
for case in cases:
    temp.append(raw[case].extract('urban').sum('*'))
temp = xray.concat(temp, dim=cases).sel(rs=CREM.set('r')).rename({'rs': 'r'})
for u in temp['urb']:
    if u in ['PM10', 'PM25']:
        continue
    var_name = '{}_emi'.format(u.values)
    arrays[var_name] = temp.sel(urb=u).drop('urb')
    u_fancy = str(u.values).translate({'2': '₂', '3': '₃'})
    label(var_name, 'Annual {} emissions'.format(u_fancy),
          'millions of tonnes of ' + str(u_fancy), 'Mt')


# Cell:

# CO₂ price
temp = []
for case in cases:
    temp.append(extra[case].extract('ptcarb_t'))
arrays['CO2_price'] = xray.concat(temp, dim=cases)
label('CO2_price', 'Price of CO₂ emissions permit',
      '2007 US dollars per tonne CO₂', '2007 USD/t')


# Cell:

# Consumption
temp = []
for case in cases:
    temp.append(extra[case].extract('cons_t'))
arrays['cons'] = xray.concat(temp, dim=cases)
label('cons', 'Household consumption',
      'billions of U.S. dollars, constant at 2007', '10⁹ USD')


# Cell:

# Primary energy
temp = []
for case in cases:
    temp.append(extra[case].extract('pe_t'))
temp = xray.concat(temp, dim=cases)
temp = temp.where(temp < 1e300).fillna(0)
e_name = {
    'COL': 'Coal',
    'GAS': 'Natural gas',
    'OIL': 'Crude oil',
    'NUC': 'Nuclear',
    'WND': 'Wind',
    'SOL': 'Solar',
    'HYD': 'Hydroelectricity',
    }
for ener in temp['e']:
    var_name = '{}_energy'.format(ener.values)
    # Convert non-fossil electrical energy to the raw quantity of coal needed
    # to generate such amount of electricity:
    arrays[var_name] = temp.sel(e=ener).drop('e') * (1. if ener in
                                                     ['COL', 'GAS', 'OIL'] else
                                                     0.356 / 0.12)
    label(var_name, 'Primary energy from {}'.format(e_name[str(ener.values)]),
          'millions of tonnes of coal equivalent', 'Mtce')

# Sums and shares 
arrays['energy_fossil'] = temp.sel(e=['COL', 'GAS', 'OIL']).sum('e')
label('energy_fossil', 'Primary energy from fossil fuels',
      'millions of tonnes of coal equivalent', 'Mtce')

arrays['energy_nonfossil'] = (temp.sel(e=['NUC', 'WND', 'SOL', 'HYD']).sum('e')
                              * 0.356 / 0.12)
label('energy_nonfossil', 'Primary energy from non-fossil sources',
      'millions of tonnes of coal equivalent', 'Mtce')

arrays['energy_total'] = arrays['energy_fossil'] + arrays['energy_nonfossil']
label('energy_total', 'Primary energy, total',
      'millions of tonnes of coal equivalent', 'Mtce')

arrays['penergy_nonfossil_share'] = (arrays['energy_nonfossil'] /
    arrays['energy_total']) * 100
label('penergy_nonfossil_share',
      'Share of non-fossil sources in final energy',
      'percent', '%')


# Cell:

# Reported share of NHW
temp1 = []
temp2 = []
for case in cases:
    temp1.append(extra[case].extract('nhw_share'))
    temp2.append(extra[case].extract('nhw_share_CN')) 
arrays['energy_nonfossil_share'] = 100 * xray.concat(temp1, dim=cases)
label('energy_nonfossil_share',
      'Share of non-fossil sources in final energy',
      'percent', '%')
nhw_share = 100 * xray.concat(temp2, dim=cases)


# Cell:

# Population
temp = []
for case in cases:
    temp.append(raw[case].extract('pop2007').sel(g='c') *
                raw[case].extract('pop') * 1e-2)
arrays['pop'] = xray.concat(temp, dim=cases).drop('g').sel(rs=CREM.set('r'))                     .rename({'rs': 'r'})
label('pop', 'Population', 'millions', '10⁶')


# Cell:

# Share of coal in provincial GDP
temp = []
for case in cases:
    temp.append(raw['bau'].extract('sect_prod'))
sect_prod = xray.concat(temp, dim=cases).sel(rs=CREM.set('r'), g='COL')                 .drop('g').rename({'rs': 'r'})
arrays['COL_share'] = (sect_prod / arrays['GDP']) * 100
label('COL_share', 'Share of coal production in provincial GDP',
      'percent', '%')


# ### 3.1. PM2.5 concentrations & population-weighted exposure
# **Note:** these are contained in a separate XLSX file, pm.xslx.

# Cell:

# Open the workbook and worksheet
wb = load_workbook(join(GDX_DIR,'pm.xlsx'), read_only=True)

cols = {
    None: None,
    2010: ('bau', '2010'),
    '2030_BAU': ('bau', '2030'),
    '2030_cint3': ('3', '2030'),
    '2030_cint4': ('4', '2030'),
    '2030_cint5': ('5', '2030'),
    '2030_BAU_lessGDP': ('bau_lo', '2030'),
    '2030_cint3_lessGDP': ('3_lo', '2030'),
    '2030_cint4_lessGDP': ('4_lo', '2030'),
    '2030_cint5_lessGDP': ('5_lo', '2030'),
    }
pm_extra = {}
for ws in wb:
    # Read the table in to a list of lists
    temp = []
    for r, row in enumerate(ws.rows):
        if r == 0:
            temp.append([cols[cell.value] for cell in row])
        else:
            temp.append([cell.value for cell in row])

    # Convert to a pandas.DataFrame
    df = pd.DataFrame(temp).set_index(0).dropna(axis=(0, 1), how='all')
    df.columns = pd.MultiIndex.from_tuples(df.iloc[0,:], names=['case', 't'])
    df.drop(None, inplace=True)
    df.index.name = 'r'
    df.dropna(axis=(0, 1), how='all', inplace=True)
    df = df.stack(['case', 't']).swaplevel('case', 'r')

    # Convert to an xray.DataArray
    da = xray.DataArray.from_series(df)
    # Fill in 2010 values across cases
    da.loc[:,:,'2010'] = da.loc['bau',:,'2010']

    if ws.title == 'prv_actual_average':
        arrays['PM25_conc'] = da
        label('PM25_conc', 'Province-wide average PM2.5',
              'micrograms per cubic metre', 'μg/m³')
    elif ws.title == 'prv_pop_average':
        arrays['PM25_exposure'] = da
        label('PM25_exposure', 'Population-weighted exposure to PM2.5',
              'micrograms per cubic metre', 'μg/m³')
    else:
        pm_extra[ws.title] = da


# Cell:

df = pd.DataFrame([
    ['bau', '2010', 66.37],
    ['bau', '2030', 84.78],
    ['3'  , '2030', 78.64],
    ['4'  , '2030', 71.23],
    ['5'  , '2030', 60.87]],
    columns=['case', 't', 'value']).set_index(['case', 't'])
da = xray.DataArray.from_series(df['value'])
# Fill in 2010 values across cases
da.loc[:,'2010'] = da.loc['bau','2010']
PM25_exposed_frac = da

# Placeholder value at regional level
arrays['PM25_exposed_frac'] = xray.DataArray([nan] * len(time), coords=[time],
                                             dims='t')
label('PM25_exposed_frac', 'Population exposed to PM2.5 concentrations greater'
      ' than 35 μg/m³', 'percent', '%')
PM25_exposed_frac


# ### 3.2. Finish preprocessing

# Cell:

# Combine all variables into a single xray.Dataset and truncate time
data = xray.Dataset(arrays).sel(t=time)

data['scenarios'] = xray.DataArray([
    'BAU: Business-as-usual',
    'Policy: Reduce carbon-intensity of GDP by 3%/year from BAU',
    'Policy: Reduce carbon-intensity of GDP by 4%/year from BAU',
    'Policy: Reduce carbon-intensity of GDP by 5%/year from BAU',
    'LO: BAU with 1% lower annual GDP growth',
    'Policy: Reduce carbon-intensity of GDP by 3%/year from LO',
    'Policy: Reduce carbon-intensity of GDP by 4%/year from LO',
    'Policy: Reduce carbon-intensity of GDP by 5%/year from LO',
    ], coords={'case': cases}, dims='case')

#for var in [data.PM25_exposure, data.PM25_conc]:
#    # interpolate PM data for missing years
#    var.loc[:,:,'2007'] = var.loc[:,:,'2010']
#    increment = (var.loc[:,:,'2030'] - var.loc[:,:,'2010']) / 4
#    var.loc[:,:,'2015'] = var.loc[:,:,'2010'] + increment
#    var.loc[:,:,'2020'] = var.loc[:,:,'2010'] + 2 * increment
#    var.loc[:,:,'2025'] = var.loc[:,:,'2010'] + 3 * increment

# Construct data for low-ammonia cases
# N.B. the NH₃ cases do not appear on the final website, so these lines simply
#      copy data from the other cases.
base_cases = [str(name.values) for name in data['case']]
nh3_cases = [name + '_nh3' for name in base_cases]
d = xray.Dataset(coords={'case': nh3_cases})
data.merge(d, join='outer', inplace=True)
# fill in PM data for missing cases
for nh3_case, base_case in zip(nh3_cases, base_cases):
    data.PM25_conc.loc[nh3_case,:,:] = data.PM25_conc.loc[base_case,:,:]


# Compute national totals and averages
national = data.sum('r')
national['penergy_nonfossil_share'] = (national['energy_nonfossil'] /
                                       national['energy_total']) * 100
national['energy_nonfossil_share'] = nhw_share
national['PM25_exposed_frac'] = PM25_exposed_frac
# Unweighted average across provincial averages
national['PM25_exposure'] = pm_extra['region_pop_average']                             .sel(r='Whole China').drop('r')
national['PM25_conc'] = pm_extra['region_actual_average'].sel(r='Whole China')                                                         .drop('r')
    
for var in [national.PM25_exposure, national.PM25_conc]:
    # interpolate PM data for missing years
    var.loc[:,'2007'] = var.loc[:,'2010']
    increment = (var.loc[:,'2030'] - var.loc[:,'2010']) / 4
    var.loc[:,'2015'] = var.loc[:,'2010'] + increment
    var.loc[:,'2020'] = var.loc[:,'2010'] + 2 * increment
    var.loc[:,'2025'] = var.loc[:,'2010'] + 3 * increment


# ## 4. Output data

# Cell:

# Output a file with scenario information
data['scenarios'].to_dataframe().to_csv(join(OUT_DIR, 'scenarios.csv'),
                                        header=['description'],
                                        quoting=csv.QUOTE_ALL)

# Output a file with variable information
var_info = pd.DataFrame(index=[d for d in data.data_vars if d != 'scenarios'],
                        columns=['desc', 'unit_long', 'unit_short'],
                        dtype=str)

print('Missing dimension info:')
none_missing = True
for name, _ in var_info.iterrows():
    try:
        row = [data[name].attrs[k] for k in var_info.columns]
    except KeyError:
        print('  ', name)
        none_missing = False
        continue
    var_info.loc[name,:] = row
if none_missing:
    print('  (None)')
var_info.to_csv(join(OUT_DIR, 'variables.csv'), index_label='Variable',
                quoting=csv.QUOTE_ALL)

# Create directories
for r in CREM.set('r'):
    mkdir(join(OUT_DIR, r), exist_ok=True)
mkdir(join(OUT_DIR, 'national'), exist_ok=True)

# Serialize to CSV
for c in map(lambda x: x.values, data.case):
    # Provincial data
    for r in CREM.set('r'):
        data.sel(case=c, r=r).drop(['case', 'r', 'scenarios']).to_dataframe()             .to_csv(join(OUT_DIR, r, '{}.csv'.format(c)))
            
    # Todo: sort column names before dump data to csv
    
    # National data
    national.sel(case=c).drop(['case', 'scenarios']).to_dataframe()             .to_csv(join(OUT_DIR, 'national', '{}.csv'.format(c)))

