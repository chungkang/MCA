import os
import pandas as pd

def list_files(directory, extensions):
    file_dict = {}
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        for extension in extensions:
            if filename.endswith(extension):
                file_type = 'vector' if extension == '.shp' else 'raster'
                file_dict[file_path] = {
                    'file_name': filename,
                    'type(vector/raster)': file_type,
                    'source_resolution': None,
                    'target_resolution': None,
                    'source_CRS': None,
                    'target_CRS': None,
                    'AOI': None,
                    'exclusion': None,
                    'most_suitable': None,
                    'suitable': None,
                    'least_suitable': None,
                    'citation': None
                }
    return file_dict

directory_path = r'data\\step1_input_data\\'
extensions = ['.tif', '.shp']

files = list_files(directory_path, extensions)

df = pd.DataFrame(files)

# change row and colunm
df_transposed = df.transpose()

# add headers
df_transposed.columns = ['File Name', 'Type(vector/raster)', 'Source Resolution','Target Resolution', 'Source CRS', 'Target CRS', 'AOI' , 'Exclusion', 'Most Suitable', 'Suitable', 'Least Suitable', 'Citation']

# save excel
excel_path = r'data\\step1_input_data\\MCA_criteria_template.xlsx'
df_transposed.to_excel(excel_path, index=False)
