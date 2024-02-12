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
def parse_range(range_str, raster_data):
    range_str = str(range_str).strip()

    # 최소값과 최대값을 래스터 데이터에서 추출
    raster_min_val = np.min(raster_data)
    raster_max_val = np.max(raster_data)

    if '-' in range_str:
        parts = range_str.split('-')
        # 최소값만 있는 경우 (예: "-5")
        if range_str.startswith('-'):
            min_val = None  # 최소값을 래스터의 최소값으로 설정
            max_val = int(parts[1]) if parts[1] else raster_max_val
        # 최대값만 있는 경우 (예: "5-")
        elif range_str.endswith('-'):
            min_val = int(parts[0]) if parts[0] else raster_min_val
            max_val = None  # 최대값을 래스터의 최대값으로 설정
        # 최소-최대 범위
        else:
            min_val = int(parts[0]) if parts[0] else raster_min_val
            max_val = int(parts[1]) if parts[1] else raster_max_val

        # 범위 유형 결정
        if min_val is None:
            return {'type': 1, 'min': raster_min_val, 'max': max_val}
        elif max_val is None:
            return {'type': 3, 'min': min_val, 'max': raster_max_val}
        else:
            return {'type': 3, 'min': min_val, 'max': max_val}
    elif ',' in range_str:
        values = list(map(int, range_str.split(',')))
        return {'type': 2, 'values': values}
    elif range_str.isdigit():
        return {'type': 2, 'values': [int(range_str)]}



def reclassify_by_range(raster, raster_data, raster_output_path, ranges):
    # 새로운 래스터 데이터를 저장할 배열을 생성합니다.
    reclassified_data = np.zeros_like(raster_data)
    
    for score, value_range in ranges.items():
        if value_range['type'] == 1:  # 최소-최대 범위
            # None 값 처리를 위한 조건 추가
            min_val = value_range.get('min', None)
            if min_val is None:
                min_val = np.min(raster_data)  # 최소값 설정
            max_val = value_range.get('max', None)
            if max_val is None:
                max_val = np.max(raster_data)  # 최대값 설정

            condition = (raster_data >= min_val) & (raster_data <= max_val)
            reclassified_data[condition] = score
        elif value_range['type'] == 2:  # 특정 값들의 리스트
            for val in value_range['values']:
                condition = (raster_data == val)
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
            base_file_name = os.path.splitext(row['file_name'])[0]  # .tif 확장자 제거
            output_file_name = base_file_name + '_scored.tif'  # 최종 파일 이름 설정
            output_file_path = output_path + output_file_name  # 출력 파일 경로 설정

            raster = gdal.Open(input_file_path)
            band = raster.GetRasterBand(1)
            raster_data = band.ReadAsArray()

            # 범위 문자열을 파싱하여 범위 유형과 값을 추출합니다.
            most_suitable_info = parse_range(row['most_suitable'], raster_data)
            suitable_info = parse_range(row['suitable'], raster_data)
            least_suitable_info = parse_range(row['least_suitable'], raster_data)

            # 각 점수에 해당하는 범위 정보를 사전에 저장합니다.
            range_dict = {
                1: most_suitable_info,
                2: suitable_info,
                3: least_suitable_info
            }

            # reclassify_by_range 함수를 호출하여 래스터 데이터를 재분류합니다.
            reclassify_by_range(raster, raster_data, output_file_path, range_dict)
            
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
