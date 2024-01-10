import pandas as pd
import rasterio
import numpy as np

directory_path = r'data\\step1_input_data\\south_area\\'
input_excel_path = directory_path + r'MCA_criteria_template.xlsx'

df_input_excel = pd.read_excel(input_excel_path)

# Filter DataFrame for AOI, Include, and Exclude
# AOI dafa frame
df_AOI = df_input_excel[df_input_excel['AOI'] == 1]

# Filter rows where are AOI, include, exclude
scored_df = df_input_excel[(df_input_excel['AOI'] == 1) | (df_input_excel['include'] != 1) | (df_input_excel['exclude'] != 1)]

# Calculate the weight of layers
# Calculate the sum of layer_weight for filtered rows
total_layer_weight = scored_df['layer_weight'].sum()

# Add a new column 'layer_weight_calculation' with the calculated values
df_input_excel['layer_weight_rate'] = (df_input_excel['layer_weight'] / total_layer_weight).round(3)
print(df_input_excel)

# x, y resolution 과 extend 가 같은지 확인해서 안되면 에러메시지

with rasterio.open(directory_path + df_AOI.iloc[0]['file_name']) as AOI_dataset:
    AOI_raster_value = AOI_dataset.read(1).astype(float)

# filtering scored layers: layer_weight is not null
df_scored_layers = df_input_excel[df_input_excel['layer_weight'].notna()]

# filtering non-scored layers: layer_weight is null (AHOI, include, exclude)
df_nonscored_layers = df_input_excel[df_input_excel['layer_weight'].isna()]

# calculate layer weight
# Iterate over each row in the DataFrame
for index, row in df_scored_layers.iterrows():
    # Access values in each row
    file_path = directory_path + row['file_name']

    print(row['file_name'] + ' : ')
    with rasterio.open(file_path) as dataset:
        dataset_raster_value = dataset.read(1)
        print(dataset_raster_value * row['layer_weight_rate'])
        AOI_raster_value +=  dataset_raster_value * row['layer_weight_rate']

    print('result_MCA in progress:')
    print(AOI_raster_value)

# calculate AOI, Include, Exclude
# Iterate over each row in the DataFrame
for index, row in df_nonscored_layers.iterrows():
    # Access values in each row
    file_path = directory_path + row['file_name']
    include = row['include']
    exclude = row['exclude']
 
    print(row['file_name'] + ' : ')
    if include == 1:  # multiply
        with rasterio.open(file_path) as dataset:
            dataset_raster_value = dataset.read(1)
            print(dataset_raster_value)
            AOI_raster_value *= dataset_raster_value
            
    elif exclude == 1:  # 0,1 inverted multiply
        with rasterio.open(file_path) as dataset:
            inverted_dataset_raster_value = 1 - dataset.read(1)
            print(inverted_dataset_raster_value)
            AOI_raster_value *= inverted_dataset_raster_value

    print('result_MCA in progress:')
    print(AOI_raster_value)

print('result_MCA final:')
print(AOI_raster_value)

# smaller than 1 means NoData
no_data_value = 0
AOI_raster_value[AOI_raster_value < 1] = no_data_value

with rasterio.open(AOI_file_path) as AOI_dataset:
    profile = AOI_dataset.profile
    profile['nodata'] = no_data_value
    profile['compress'] = 'DEFLATE' # same as high compression(default) in QGIS compression option

with rasterio.open(directory_path + r'MCA_result.tif', 'w', **profile) as dst:
    dst.write(AOI_raster_value.astype(profile['dtype']), 1)