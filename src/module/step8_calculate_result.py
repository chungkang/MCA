"""
Created by Chungkang Choi
February 2024

Description: Calculate Result
"""

import pandas as pd
import rasterio
import numpy as np
import copy

def process_result_calculation(input_path, output_path, input_excel_path):
    # create panda data frame for each purpose
    df_input_excel = pd.read_excel(input_excel_path)

    # Filter rows where are AOI, exclusion
    scored_df = df_input_excel[(df_input_excel['AOI'] != 1) | (df_input_excel['exclusion'] != 1)]

    # Calculate 'layer_weight_rate' column
    df_input_excel['layer_weight_rate'] = (df_input_excel['layer_weight'] / scored_df['layer_weight'].sum()).round(3)

    # file_name에 "AOI" 가 포함된 것으로 수정
    # AOI data frame
    df_AOI = df_input_excel[df_input_excel['AOI'] == 1]
    AOI_file_path = input_path + df_AOI.iloc[0]['file_name']

    # create base raster array for raster calculation, should be 0 value / using for raster cell calculation
    with rasterio.open(AOI_file_path) as AOI_dataset:
        array_calculation = np.array(copy.deepcopy(AOI_dataset.read(1).astype(float)))-1

    # filtering scored layers: layer_weight is not null
    df_scored_layers = df_input_excel[df_input_excel['layer_weight_rate'].notna()]
    
    # filtering non-scored layers: layer_weight is null (AOI, exclusion)
    df_nonscored_layers = df_input_excel[df_input_excel['layer_weight_rate'].isna()]

    # calculate layer weight
    for index, row in df_scored_layers.iterrows():
        file_path = input_path + row['file_name']
       
        try:
            with rasterio.open(file_path) as dataset:
                dataset_raster_value = dataset.read(1)
                # NoData 값을 확인하고 0으로 설정
                if dataset.nodata is not None:
                    dataset_raster_value[dataset_raster_value == dataset.nodata] = 0

                # 래스터 데이터 타입이 기대하는 타입인지 확인
                if not np.issubdtype(dataset_raster_value.dtype, np.number):
                    print(f"Error: Raster data type is not numeric at path {file_path}")
                    continue

                # 배열 연산 수행
                array_calculation += dataset_raster_value * row['layer_weight_rate']

        except rasterio.errors.RasterioIOError as e:
            print(f"Error reading raster file at path {file_path}: {e}")

    # calculate AOI, Exclusion
    for index, row in df_nonscored_layers.iterrows():
        # Access values in each row
        file_path = input_path + row['file_name']
        include_AOI = row['AOI']
        exclude = row['exclusion']

        if include_AOI == 1:  # multiply
            with rasterio.open(file_path) as dataset:
                dataset_raster_value = dataset.read(1)
                array_calculation *= dataset_raster_value

        elif exclude == 1:  # 0,1 inverted multiply
            with rasterio.open(file_path) as dataset:
                dataset_raster_value = dataset.read(1) # 래스터 데이터 읽기
                no_data_value = dataset.nodata # NoData 값 확인

                # NoData인 셀을 0으로 설정
                if no_data_value is not None:
                    dataset_raster_value[dataset_raster_value == no_data_value] = 0

                inverted_dataset_raster_value = 1 - dataset_raster_value
                array_calculation *= inverted_dataset_raster_value

    # smaller than 1 means NoData
    no_data_value = 0
    array_calculation[array_calculation < 1] = no_data_value

    with rasterio.open(AOI_file_path) as AOI_dataset:
        profile = AOI_dataset.profile
        profile.update(dtype=rasterio.float32, nodata=no_data_value, compress='DEFLATE')
    
    with rasterio.open(output_path + r'MCA_result.tif', 'w', **profile) as dst:
        dst.write(array_calculation.astype(profile['dtype']), 1)


def main():
    # set input file path
    input_path = r'data\\step7\\'
    output_path = r'data\\step8\\'
    setting_excel_path = r'data\\setting_excel\\'
    input_excel_path = setting_excel_path + r'step7_excel_template.xlsx'
    process_result_calculation(input_path, output_path, input_excel_path)

if __name__ == "__main__":
    main()