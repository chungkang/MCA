"""
Created by Chungkang Choi
February 2024

Description: Calculate Range
"""

import os
import pandas as pd
from osgeo import gdal
import shutil  # library for copying files
import numpy as np
import re
import rasterio

# Function to process range strings
def process_range_str(range_str, raster_min_val, raster_max_val):
    if not range_str or pd.isna(range_str):
        return {}
    elif range_str:
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

# This function takes a range string as input and returns a dictionary containing the range type and actual values.
def parse_range(layer_name, row_data, raster_data):
    # extract minimum/maximum values from raster data
    raster_min = np.min(raster_data)
    raster_max = np.max(raster_data)

    # Initialize dictionaries
    exclusive_info = {}
    most_suitable_info = {}
    suitable_info = {}
    least_suitable_info = {}

    if 'land_cover' in layer_name:
        # Handle land cover separately
        most_suitable_info['values'] = list(map(int, row_data['most_suitable'].split(','))) if row_data['most_suitable'] else []
        suitable_info['values'] = list(map(int, row_data['suitable'].split(','))) if row_data['suitable'] else []
        least_suitable_info['values'] = list(map(int, row_data['least_suitable'].split(','))) if row_data['least_suitable'] else []
    else:
        # Apply processing to each range
        exclusive_info = process_range_str(row_data['exclusive_range'], raster_min, raster_max)
        most_suitable_info = process_range_str(row_data['most_suitable'], raster_min, raster_max)
        suitable_info = process_range_str(row_data['suitable'], raster_min, raster_max)
        least_suitable_info = process_range_str(row_data['least_suitable'], raster_min, raster_max)

    range_dictionary = {0: exclusive_info, 1: most_suitable_info, 2: suitable_info, 3: least_suitable_info}
    # print(range_dictionary)
    return range_dictionary


def reclassify_by_range(layer_name, raster, raster_data, raster_output_path, ranges, exclusive_yn):
    # create new raster to save reclassed data
    reclassified_data = np.zeros_like(raster_data)
    
    for score, value_range in ranges.items():
         # For cases where the score is 0 and the exclusivity is true
        if score == 0 and exclusive_yn == 'Y':
            # Processing exclusive_info
            min_val_raw = value_range.get('min', None)
            max_val_raw = value_range.get('max', None)

            min_val = int(min_val_raw) if min_val_raw is not None else None
            max_val = int(max_val_raw) if max_val_raw is not None else None

            if min_val is not None and max_val is not None:
                condition = (raster_data >= min_val) & (raster_data <= max_val)
                reclassified_data[condition] = 1
            break
        else:
            # land cover
            if 'land_cover' in layer_name and 'values' in value_range: 
                for val in value_range['values']:
                    condition = (raster_data == val)
                    reclassified_data[condition] = score
            # min-max ranges
            elif value_range != {}:
                min_val_raw = value_range.get('min', None)
                max_val_raw = value_range.get('max', None)
                
                min_val = int(min_val_raw) if min_val_raw is not None else None
                max_val = int(max_val_raw) if max_val_raw is not None else None
                
                if min_val is not None and max_val is not None:
                    condition = (raster_data >= min_val) & (raster_data <= max_val)
                    reclassified_data[condition] = score

    driver = gdal.GetDriverByName('GTiff')
    new_raster = driver.Create(raster_output_path, raster.RasterXSize, raster.RasterYSize, 1, gdal.GDT_Float32)
    new_band = new_raster.GetRasterBand(1)
    new_band.WriteArray(reclassified_data)
    new_raster.SetProjection(raster.GetProjection())
    new_raster.SetGeoTransform(raster.GetGeoTransform())
    new_band.FlushCache()
    raster = None
    new_raster = None


def process_range_calculation(input_path, output_path, input_excel_path, output_excel_path):
    # Read the input Excel file
    df_input_excel = pd.read_excel(input_excel_path)

    # Initialize a list to keep track of processed files for the Excel output
    processed_files = []

    # Process '.tif' files for range calculation
    for idx, row in df_input_excel.iterrows():
        input_file_path = input_path + row['file_name']

        # AOI/exclusion
        if 'AOI' in row['file_name'] or 'exclusion' in row['file_name']:
            output_file_name = row['file_name']
            output_file_path = output_path + output_file_name
            
            # no processing, just copying
            shutil.copy(input_file_path, output_file_path)

            # Add file info to excel
            processed_files.append({
                'file_name': output_file_name,
                'AOI': row['AOI'],
                'exclusion': row['exclusion'],
                'most_suitable': row['most_suitable'],
                'suitable': row['suitable'],
                'least_suitable': row['least_suitable'],
                'exclusive_range': row['exclusive_range'],
                'layer_weight': row['layer_weight']
            })

            # Creating a base frame using the AOI file
            if 'AOI' in row['file_name']:
                # create base raster array for raster calculation, should be 0 value
                with rasterio.open(input_file_path) as AOI_dataset:
                    array_calculation = np.zeros_like(AOI_dataset.read(1).astype(float))

        # none AOI/exclusion
        else:
            # calculate range of suitability
            if pd.notnull(row['most_suitable']):
                base_file_name = os.path.splitext(row['file_name'])[0]
                output_file_name = base_file_name + '_scored.tif'
                output_file_path = output_path + output_file_name

                suitability_raster = gdal.Open(input_file_path)
                band = suitability_raster.GetRasterBand(1)
                raster_data = band.ReadAsArray()

                # Updated to pass raster_data directly
                range_dict = parse_range(base_file_name, row, raster_data)

                # reclassify_by_range updated to remove the unnecessary 'raster' parameter
                reclassify_by_range(base_file_name, suitability_raster, raster_data, output_file_path, range_dict, 'N')

                # Add file info to excel
                processed_files.append({
                    'file_name': output_file_name,
                    'AOI': None,
                    'exclusion': None,
                    'most_suitable': row['most_suitable'],
                    'suitable': row['suitable'],
                    'least_suitable': row['least_suitable'],
                    'exclusive_range': None,
                    'layer_weight': row['layer_weight']
                })

            # calculate exclusive range -> Create new file with "_exclusion" to Exclusive_range + add 1 to exclusion column
            if pd.notnull(row['exclusive_range']):
                base_file_name = os.path.splitext(row['file_name'])[0]
                output_file_name = base_file_name + '_exclusion.tif'
                output_file_path = output_path + output_file_name

                raster = gdal.Open(input_file_path)
                band = raster.GetRasterBand(1)
                raster_data = band.ReadAsArray()

                # Updated to pass raster_data directly
                range_dict = parse_range(base_file_name, row, raster_data)

                # reclassify_by_range updated to remove the unnecessary 'raster' parameter
                reclassify_by_range(base_file_name, raster, raster_data, output_file_path, range_dict, 'Y')

                # Add file info to excel
                processed_files.append({
                    'file_name': output_file_name,
                    'AOI': None,
                    'exclusion': 1,
                    'most_suitable': None,
                    'suitable': None,
                    'least_suitable': None,
                    'exclusive_range': row['exclusive_range'],
                    'layer_weight': None
                })
            

            # add AOI filter for Floating Photovoltaic(FPV)/Ground-mounted Solar Photovoltaic(PV)
            if 'GLOBathy' in row['file_name']:
                # FPV
                if row['AOI'] == 1:
                    # Open GLOBathy file
                    with rasterio.open(input_path + row['file_name']) as globathy_dataset:
                        # read GLOBathy data
                        globathy_data = globathy_dataset.read(1).astype(float)
                        
                        # Assigning 1 to all cells that are not 'no data'
                        # Here, for example, we assume 'no data' values to be 0.
                        # Actual 'no data' values should be determined based on the metadata of the raster data.
                        mask = globathy_data != 0  # Creating a mask for all non-zero values
                        array_calculation[mask] = 1  # Assigning 1 to masked locations

                        base_file_name = os.path.splitext(row['file_name'])[0]
                        output_file_name = base_file_name + '_FPV.tif'
                        output_file_path = output_path + output_file_name

                        # Logic for saving the converted raster data to a file
                        new_dataset = rasterio.open(
                            output_file_path, 'w',
                            driver='GTiff',
                            height=array_calculation.shape[0],
                            width=array_calculation.shape[1],
                            count=1,
                            dtype=array_calculation.dtype,
                            crs=AOI_dataset.crs,
                            transform=AOI_dataset.transform,
                        )
                        new_dataset.write(array_calculation, 1)
                        new_dataset.close()

                        # Adding processed file information from GLOBathy to the processed_files list
                        processed_files.append({
                            'file_name': output_file_name,
                            'AOI': 1,
                            'exclusion': None,
                            'most_suitable': None,
                            'suitable': None,
                            'least_suitable': None,
                            'exclusive_range': None,
                            'layer_weight': None
                        })
                # PV
                else:
                    # read PV file
                    with rasterio.open(input_path + row['file_name']) as pv_dataset:
                        # read PV data
                        pv_data = pv_dataset.read(1).astype(float)
                        
                        # Assigning 1 to all cells with 'no data' or a value of 0
                        # Here, we also assume 'no data' values to be 0.
                        # Actual 'no data' values should be determined based on the metadata of the raster data.
                        mask = (pv_data == 0)  # Creating a mask for cells with a value of 0
                        array_calculation[mask] = 1  # Assigning 1 to masked locations

                        base_file_name = os.path.splitext(row['file_name'])[0]
                        output_file_name = base_file_name + '_PV.tif'
                        output_file_path = output_path + output_file_name

                        # Logic for saving the converted raster data to a file
                        new_dataset = rasterio.open(
                            output_file_path, 'w',
                            driver='GTiff',
                            height=array_calculation.shape[0],
                            width=array_calculation.shape[1],
                            count=1,
                            dtype=array_calculation.dtype,
                            crs=AOI_dataset.crs,
                            transform=AOI_dataset.transform,
                        )
                        new_dataset.write(array_calculation, 1)
                        new_dataset.close()

                        # Adding processed file information from GLOBathy to the processed_files list
                        processed_files.append({
                            'file_name': output_file_name,
                            'AOI': 1,
                            'exclusion': None,
                            'most_suitable': None,
                            'suitable': None,
                            'least_suitable': None,
                            'exclusive_range': None,
                            'layer_weight': None
                        })

    # Create a DataFrame from the processed_files list
    df_processed = pd.DataFrame(processed_files)

    # Save the DataFrame to an Excel file
    df_processed.to_excel(output_excel_path, index=False)

def main():
    input_path = r'data\\step6\\'
    output_path = r'data\\step7\\'
    setting_excel_path = r'data\\setting_excel\\'
    input_excel_path = setting_excel_path + r'step6_excel_template.xlsx'
    output_excel_path = setting_excel_path + r'step7_excel_template.xlsx'
    process_range_calculation(input_path, output_path, input_excel_path, output_excel_path)

if __name__ == "__main__":
    main()