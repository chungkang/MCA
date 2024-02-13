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
import re


# 이 함수는 범위 문자열을 입력으로 받고 범위 유형과 실제 값을 딕셔너리로 반환합니다.
def parse_range(layer_name, row_data, raster_data):
    # extract minimum/maximum values from raster data
    raster_min_val = np.min(raster_data)
    raster_max_val = np.max(raster_data)

    # Initialize dictionaries
    most_suitable_info = {}
    suitable_info = {}
    least_suitable_info = {}

    if 'land_cover' in layer_name:
        # Handle land cover separately
        most_suitable_info['values'] = list(map(int, row_data['most_suitable'].split(','))) if row_data['most_suitable'] else []
        suitable_info['values'] = list(map(int, row_data['suitable'].split(','))) if row_data['suitable'] else []
        least_suitable_info['values'] = list(map(int, row_data['least_suitable'].split(','))) if row_data['least_suitable'] else []
    else:
        # Function to process range strings
        def process_range_str(range_str):
            if range_str:
                # Find all numbers in the string
                numbers = re.findall(r'-?\d+', range_str)
                numbers = [int(num) for num in numbers]
                if "~" in range_str:
                    if range_str.startswith("~"):
                        return {'min': raster_min_val, 'max': numbers[0]}
                    elif range_str.endswith("~"):
                        return {'min': numbers[0], 'max': raster_max_val}
                    else:
                        return {'min': numbers[0], 'max': numbers[1]}
                else:
                    return {'values': numbers}
            else:
                return {}

        # Apply processing to each range
        most_suitable_info = process_range_str(row_data['most_suitable'])
        suitable_info = process_range_str(row_data['suitable'])
        least_suitable_info = process_range_str(row_data['least_suitable'])

    return {1: most_suitable_info, 2: suitable_info, 3: least_suitable_info}


def reclassify_by_range(layer_name, raster, raster_data, raster_output_path, ranges):
    # create new raster to save reclassed data
    reclassified_data = np.zeros_like(raster_data)
    
    for score, value_range in ranges.items():
        # land cover
        if 'land_cover' in layer_name: 
            for val in value_range['values']:
                condition = (raster_data == val)
                reclassified_data[condition] = score
        # min-max ranges
        else:
            # None 값 처리를 위한 조건 추가
            min_val = int(value_range.get('min', None))
            if min_val is None:
                min_val = np.min(raster_data)  # 최소값 설정
            max_val = int(value_range.get('max', None))
            if max_val is None:
                max_val = np.max(raster_data)  # 최대값 설정

            condition = (raster_data >= min_val) & (raster_data <= max_val)
            reclassified_data[condition] = score

    # 새로운 래스터 파일을 저장하는 나머지 부분은 변경 없음
    driver = gdal.GetDriverByName('GTiff')
    new_raster = driver.Create(raster_output_path, raster.RasterXSize, raster.RasterYSize, 1, band.DataType)
    new_band = new_raster.GetRasterBand(1)
    new_band.WriteArray(reclassified_data)
    new_raster.SetProjection(raster.GetProjection())
    new_raster.SetGeoTransform(raster.GetGeoTransform())
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

    if row['AOI'] == 1 or row['exclusion'] == 1:
        output_file_name = row['file_name']
        output_file_path = output_path + output_file_name
        shutil.copy(input_file_path, output_file_path)
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

    # calculate layers with range values
    else:
        if pd.notnull(row['most_suitable']):
            base_file_name = os.path.splitext(row['file_name'])[0]
            output_file_name = base_file_name + '_scored.tif'
            output_file_path = output_path + output_file_name

            raster = gdal.Open(input_file_path)
            band = raster.GetRasterBand(1)
            raster_data = band.ReadAsArray()

            # Updated to pass raster_data directly
            range_dict = parse_range(base_file_name, row, raster_data)

            # reclassify_by_range updated to remove the unnecessary 'raster' parameter
            reclassify_by_range(base_file_name, raster, raster_data, output_file_path, range_dict)

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

        # Create new file with "_exclusion" to Exclusive_range + add 1 to exclusion column
        if pd.notnull(row['exclusive_range']):
            print('exclusion')



# Create a DataFrame from the processed_files list
df_processed = pd.DataFrame(processed_files)

# Save the DataFrame to an Excel file
df_processed.to_excel(output_excel_path, index=False)
