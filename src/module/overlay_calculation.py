import pandas as pd
import rasterio

directory_path = r'data\\step1_input_data\\entire_area\\'
excel_path = directory_path + r'MCA_criteria_template.xlsx'

df = pd.read_excel(excel_path)

# AOI dafa frame
AOI_df = df[df['AOI'] == 1]
# Use the first row as the base raster for calculation
AOI_file_path = directory_path + AOI_df.iloc[0]['file_name']

# Filter rows where are AOI, include, exclude
scored_df = df[(df['AOI'] == 1) |(df['include'] != 1) | (df['exclude'] != 1)]

# Calculate the sum of layer_weight for filtered rows
total_layer_weight = scored_df['layer_weight'].sum()

# Add a new column 'layer_weight_calculation' with the calculated values
df['layer_weight_rate'] = (df['layer_weight'] / total_layer_weight).round(3)
print(df)

# x, y resolution 과 extend 가 같은지 확인해서 안되면 에러메시지

with rasterio.open(AOI_file_path) as AOI_dataset:
    AOI_raster = AOI_dataset.read(1).astype(float)

# Iterate over each row in the DataFrame
for index, row in df.iterrows():
    # Access values in each row
    file_path = directory_path + row['file_name']
    AOI = row['AOI']
    include = row['include']
    exclude = row['exclude']

    print(row['file_name'] + ' : ')

    # Check conditions and update result raster
    if (AOI == 1) | (include == 1):  # multiply
        with rasterio.open(file_path) as dataset:
            dataset_raster = dataset.read(1)
            print(dataset_raster)
            AOI_raster *= dataset_raster
            
    elif exclude == 1:  # 0,1 inverted multiply
        with rasterio.open(file_path) as dataset:
            inverted_dataset_raster = 1 - dataset.read(1)
            print(inverted_dataset_raster)
            AOI_raster *= inverted_dataset_raster

    else:  # calculate weight rate
        with rasterio.open(file_path) as dataset:
            dataset_raster = dataset.read(1)
            print(dataset_raster * row['layer_weight_rate'])
            AOI_raster +=  dataset_raster * row['layer_weight_rate']

    print('result_MCA in progress:')
    print(AOI_raster)


print('result_MCA final:')
print(AOI_raster)

# smaller than 1 means NoData / value shouldn't be 
no_data_value = -1
AOI_raster[AOI_raster < 1] = no_data_value

with rasterio.open(AOI_file_path) as AOI_dataset:
    profile = AOI_dataset.profile
    profile['nodata'] = no_data_value
    profile['compress'] = 'DEFLATE' # same as high compression(default) in QGIS compression option

with rasterio.open(directory_path + r'MCA_result.tif', 'w', **profile) as dst:
    dst.write(AOI_raster.astype(profile['dtype']), 1)