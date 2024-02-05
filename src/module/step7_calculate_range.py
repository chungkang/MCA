"""
Created by Chungkang Choi
January 2024

Description: Calculate Range
"""

import os
import pandas as pd
from osgeo import gdal
import shutil  # library for copying files
import numpy as np


# 이 함수는 범위 문자열을 입력으로 받고 범위 유형과 실제 값을 딕셔너리로 반환합니다.
def parse_range(range_str):
    # 범위 유형을 결정합니다.
    if ',' in range_str:
        # 구체적인 값들의 리스트 (type 1)
        values = list(map(int, range_str.split(',')))
        return {'type': 1, 'values': values}
    elif '-' in range_str:
        # 최소-최대 범위 (type 2 or 3)
        min_val, max_val = range_str.split('-')
        min_val = int(min_val) if min_val else None
        max_val = int(max_val) if max_val else None
        return {'type': 2 if max_val is None else 3, 'min': min_val, 'max': max_val}
    else:
        # 단일 값 (type 1)
        return {'type': 1, 'values': [int(range_str)]}



def reclassify_by_range(raster_path, ranges):
    raster = gdal.Open(raster_path)
    band = raster.GetRasterBand(1)
    raster_data = band.ReadAsArray()
    
    # 새로운 래스터 데이터를 저장할 배열을 생성합니다.
    reclassified_data = np.zeros_like(raster_data)
    
    # 각 범위에 따라 점수를 할당합니다.
    for score, value_range in ranges.items():
        print('assign score')
        # 구현 필요

    # 새로운 래스터 파일을 저장합니다.
    driver = gdal.GetDriverByName('GTiff')

    new_raster = driver.Create(os.path.splitext(row['raster_path'])[0] + '_scored.tif', raster.RasterXSize, raster.RasterYSize, 1, band.DataType)
    new_band = new_raster.GetRasterBand(1)
    
    # 새로운 데이터를 밴드에 씁니다.
    new_band.WriteArray(reclassified_data)
    
    # 좌표계와 지리적 변환을 복사합니다.
    new_raster.SetProjection(raster.GetProjection())
    new_raster.SetGeoTransform(raster.GetGeoTransform())
    
    # 파일을 닫습니다.
    new_band.FlushCache()
    raster = None
    new_raster = None


input_path = r'data\\step6\\'
output_path = r'data\\step7\\'
setting_excel_path = r'data\\setting_excel\\'
input_excel_path = setting_excel_path + r'step6_excel_template.xlsx'
output_excel_path = setting_excel_path + r'step7_excel_template.xlsx'

# Read the input Excel file
df_input_excel = pd.read_excel(input_excel_path)

# Initialize a list to keep track of processed files for the Excel output
processed_files = []

tif_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith('.tif')]

# Process '.tif' files for range calculation
for idx, row in tif_df.iterrows():
    input_file_path = input_path + row['file_name']

    if row['AOI'] == 1:
        output_file_name = row['file_name']
        output_file_path = output_path + output_file_name
        shutil.copy(input_file_path, output_file_path)

    # calculate layers with range values
    elif pd.notnull(row['most_suitable']):
        # 범위 문자열을 파싱하여 범위 유형과 값을 추출합니다.
        most_suitable_info = parse_range(row['most_suitable'])
        suitable_info = parse_range(row['suitable'])
        least_suitable_info = parse_range(row['least_suitable'])

        # 각 점수에 해당하는 범위 정보를 사전에 저장합니다.
        range_dict = {
            1: most_suitable_info,
            2: suitable_info,
            3: least_suitable_info
        }

        # reclassify_by_range 함수를 호출하여 래스터 데이터를 재분류합니다.
        reclassify_by_range(input_file_path, range_dict)
        
        if pd.notnull(row['exclusive_range']):
        # Create new file with "_exclusion" to Exclusive_range + add 1 to exclusion column
            print('exclusion')

    # Add file info to excel
    processed_files.append({
        'file_name': output_file_name,
        'source_resolution(m)': row['source_resolution(m)'],
        'target_resolution(m)': row['target_resolution(m)'],
        'source_CRS': row['source_CRS'],
        'target_CRS': row['target_CRS'],
        'AOI': row['AOI'],
        'exclusion': row['exclusion'],
        'most_suitable': row['most_suitable'],
        'suitable': row['suitable'],
        'least_suitable': row['least_suitable'],
        'exclusive_range': row['exclusive_range'],
        'layer_weight': row['layer_weight']
    })

# Create a DataFrame from the processed_files list
df_processed = pd.DataFrame(processed_files)

# Save the DataFrame to an Excel file
df_processed.to_excel(output_excel_path, index=False)
