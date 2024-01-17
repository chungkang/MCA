import os
import pandas as pd
import rasterio

def list_files(directory, extensions):
    file_dict = {}
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        for extension in extensions:
            if filename.endswith(extension):
                file_type = 'etc'
                if extension == '.tif':
                    file_type = 'raster'
                elif extension == '.shp':
                    file_type = 'vector'

                if file_type == 'raster':
                    # Open a TIFF file
                    with rasterio.open(file_path) as dataset:
                        # Access resolution, CRS
                        resolution = dataset.res[0]
                        crs = dataset.crs
                    file_dict[file_path] = {
                        'file_name': filename,
                        'source_resolution(m)': resolution,
                        'target_resolution(m)': resolution,
                        'source_CRS': crs,
                        'target_CRS': crs,
                        'AOI': None,
                        'include': None,
                        'exclude': None,
                        'layer_weight': None,
                        'most_suitable': None,
                        'suitable': None,
                        'least_suitable': None,
                        'exclusive_range': None
                    }
    return file_dict

directory_path = r'data\\step7\\entire_area\\'
extensions = ['.tif', '.shp']
 
files = list_files(directory_path, extensions)
# print(files)
df = pd.DataFrame(files)

# change row and colunm
df_transposed = df.transpose()

# add headers
df_transposed.columns = [
                            'file_name',
                            'source_resolution(m)',
                            'target_resolution(m)',
                            'source_CRS',
                            'target_CRS',
                            'AOI',
                            'include',
                            'exclude',
                            'layer_weight',
                            'most_suitable',
                            'suitable',
                            'least_suitable',
                            'exclusive_range'
                        ]

# save excel
excel_path = directory_path + r'range_criteria_template.xlsx'
df_transposed.to_excel(excel_path, index=False)
