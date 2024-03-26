# Multi Criteria Analysis
The workflow is based on [QGIS Tutorials and Tips - Multi Criteria Overlay Analysis (QGIS3)](https://www.qgistutorials.com/en/docs/3/multi_criteria_overlay.html)

The wrokflow of MCA with QGIS is also described on [SuntraceWiki](https://wiki.suntrace.de/wiki/Analysis_%E2%80%93_MCA_for_site_selection) as well 



# Prerequisites
- Install Git
- Install Python
- Install Anaconda
- Install IDE(Integrated Development Environment) such as Visual Studio Code



# How to Excute the code
- Download or clone the repository
- Execute the command on Command Line or Powershell.
`conda env create -f environment.yml`
- Activate Virtual Environment for dependencies
`conda activate gis`
- Excute code



# Code Execution
Please follow the description below for each step of the procedure.

The code for steps 3 through 8 is executed based on the Excel files of the previous steps, namely step2_excel_template through step7_excel_template. For each step, check the files to be used and adjust the input parameters as needed by adding or removing them.


## Step 1. Prepare Data

1. Create an Area of Interest (AOI) as a polygon in shapefile (.shp) format using QGIS.

2. Open the 'step1_prepare_data_GEE' file with the [Sample Code](https://colab.research.google.com/drive/1uMmtVNNbjE_4-qoH3WjihAMtjb1P1fSv?usp=sharing) on Google Colab.
   - This sample code is based on a tutorial by the YouTuber ['GeoDev'](https://www.youtube.com/watch?v=7fC7YqhoOPE). Please refer to the video for guidance on using the 'geemap' library.
   - In case the Colab link is lost, please check the backup code in [Jupyter Notebook format (.ipynb)](src/module/step1_prepare_data_GEE.ipynb).

3. Upload the shapefile of the AOI to the 'content' directory.

   ![image](https://github.com/chungkang/MCA/assets/36185863/85ebcb9d-310b-4d69-a04b-571b9afe025f)

4. Execute the code to download each data in use. The downloaded data will be displayed under the 'content' directory.

5. Download the data to the 'data\step1' directory of the project.



## Step 2. Create Excel Template

1. Execute 'step2_create_excel_template.py' with an IDE (such as Visual Studio Code).
   - This will create 'step2_excel_template.xlsx' in the 'data\setting_excel' directory.

2. Fill in the 'target_CRS', 'target_resolution(m)', and 'AOI' fields in 'step2_excel_template.xlsx' as desired.
   - 'target_CRS' should be in the 'EPSG:XXXX' format.
   - 'target_resolution' should be an integer number with the meter unit.
   - 'AOI' should have a value of '1' (multiple AOIs can be specified, but the first one will be considered the base AOI).

   ![image](https://github.com/chungkang/MCA/assets/36185863/3788222f-52df-4a4f-b678-7351039a3cba)



## Step 3. Convert CRS

1. Execute 'step3_convert_CRS.py' using an IDE (such as Visual Studio Code).
   - This script utilizes 'step2_excel_template.xlsx' from the 'data\setting_excel' directory as input for setting values.
     'file_name', 'source_CRS', and 'target_CRS' will be utilized for this step.
   - Input data is sourced from 'data\step1', where files in tif, shp, and geojson formats are read.
   - The outputs are stored in the 'data\step3' directory, with tif files retaining their original tif format, while shp or geojson files are converted to shp format using the specified target_CRS. Additionally, a suffix "_CRS" is appended to the filenames.
   - This process generates 'step3_excel_template.xlsx' in the 'data\setting_excel' directory.
   - This process creates the result files in the 'data\step3' directory.

2. Since the 'target_resolution' input from Step 2 is utilized, there is no need to input it again if it was already provided in Step 2.



## Step 4. Rasterize Vector + Equalize Resolution

1. Execute 'step4_rasterize_vector_equalize_resolution.py' using an IDE (such as Visual Studio Code).
   - This script utilizes 'step3_excel_template.xlsx' from the 'data\setting_excel' directory as input for setting values.
     'file_name', 'source_resolution', and 'target_resolution' will be utilized for this step.
   - Input data is sourced from 'data\step3', where files in tif and shp formats are read.
   - The outputs are stored in the 'data\step4' directory. Files in shp format are rasterized based on the 'target_resolution' and saved in tif format with the suffix '_rasterized'. Raster files in tif format have their resolution transformed based on the 'target_resolution' and saved as tif files with the suffix '_equalized'. Additionally, if 'source_resolution' and 'target_resolution' are the same, the filenames will remain unchanged from the previous ones.
   - This process generates 'step4_excel_template.xlsx' in the 'data\setting_excel' directory.
   - This process creates the result files in the 'data\step4' directory.

2. Fill in the 'AOI', 'exclusion', and 'proximity' fields in 'step4_excel_template.xlsx' as desired.
   - 'AOI' should have a value of '1' (multiple AOIs can be specified, but the first one will be considered the base AOI).
   - 'exclusion' should have a value of '1'. 'exclusion' indicates areas that should be excluded.
   - 'proximity' should have a value of '1'. 'proximity' indicates cases where vector files (in geojson or shp format) are converted to raster and range calculation is required (e.g., roads, electrical grid...).

   ![image](https://github.com/chungkang/MCA/assets/36185863/9599f785-009f-4129-ba68-2b3ed906f501)



## Step 5. Calculate Proximity

1. Execute 'step5_calculate_proximity.py' using an IDE (such as Visual Studio Code).
   - This script utilizes 'step4_excel_template.xlsx' from the 'data\setting_excel' directory as input for setting values.
     'file_name' and 'proximity' will be utilized for this step.
   - Input data is sourced from 'data\step4', where files in tif format are read.
   - The outputs are stored in the 'data\step5' directory. Data with 'proximity' field filled with '1' will have proximity calculated and saved as tif files with the suffix '_proximity'. Additionally, if 'proximity' does not contain '1', the filenames will remain unchanged from the previous ones.
   - This process generates 'step5_excel_template.xlsx' in the 'data\setting_excel' directory.
   - This process creates the result files in the 'data\step5' directory.

2. Since the 'AOI', 'exclusion', and 'proximity' inputs from Step 4 are utilized, there is no need to input them again if they were already provided in Step 4.



## Step 6. Clip Extend

1. Execute 'step6_clip_extend.py' using an IDE (such as Visual Studio Code).
   - This script utilizes 'step5_excel_template.xlsx' from the 'data\setting_excel' directory as input for setting values.
      'file_name' and 'AOI' will be utilized for this step.
   - Input data is sourced from 'data\step5', where files in tif format are read.
   - All raster (tif) files are clipped (cropped) based on the extent of the 'AOI' layer, with the '_clip' suffix appended, and saved in the 'data\step6' directory.
   - This process generates 'step6_excel_template.xlsx' in the 'data\setting_excel' directory.
   - This process creates the result files in the 'data\step6' directory.


2. Fill in the following fields in 'step6_excel_template.xlsx' as desired:
   - Since the data units for each layer are different, it's important to use the appropriate units for each respective layer.
   - 'most_suitable', 'suitable', 'least_suitable', and 'exclusive_range' should contain integer numbers in the format of 'minimum\~maximum'. If only one side of the range is specified (e.g., '\~5000' indicates only the maximum value, '2100\~' indicates only the minimum value), the maximum value from the specified minimum or the minimum value from the specified maximum of the raster (tif) data will be applied. The range should be indicated with '~'.
   - 'AOI' should be set to '1' (multiple AOIs can be specified, but the first one will be considered the base AOI).
   - For layers, ensure that either 'AOI'/'exclusion' is set to '1' (there should be no case where AOI is true and exclusion is true), or 'layer_weight' is set to '1'. It is assumed that 'AOI'/'exclusion' and 'layer_weight' do not coexist.
   - If the 'file_name' field contains the word 'land_cover', it will be treated separately. It can contain a single integer or comma-separated integers, with each number corresponding to the suitability ('most_suitable', 'suitable', 'least_suitable') based on the classification of each data. In the example below, the classification is based on the [Sample Code](https://colab.research.google.com/drive/1uMmtVNNbjE_4-qoH3WjihAMtjb1P1fSv?usp=sharing) from the Google Colab mentioned in Step 1. The referenced data is [ESRI 10m Annual Land Use Land Cover (2017-2022)](https://gee-community-catalog.org/projects/S2TSLULC/?h=land+use).
   - For 'layer_weight', specify how much weight each suitability layer carries. In the example below, all layers are considered with equal weight.
   - To distinguish between projects conducted on water (FPV - floating photovoltaics) and on land (PV - photovoltaics), the 'AOI' field in the GLOBathy layer is used. If 'AOI' is set to '1', it indicates a FPV project conducted on water. If 'AOI' is not present, it indicates a PV project conducted on land.
   ![image](https://github.com/chungkang/MCA/assets/36185863/28eb6e00-aa1d-4bf5-b61a-0064f86786c6)



## Step 7. Calculate Range

1. Execute 'step7_calculate_range.py' using an IDE (such as Visual Studio Code).
   - This script utilizes 'step6_excel_template.xlsx' from the 'data\setting_excel' directory as input for setting values.
      'file_name', 'AOI', 'exclusion', 'most_suitable', 'suitable', 'least_suitable', 'exclusive_range', and 'layer_weight' will be utilized for this step.
   - Input data is sourced from 'data\step6', where files in tif format are read.
   - Operations are performed on the ranges of suitability (most_suitable, suitable, least_suitable) for layers containing 'layer_weight' values of '1', as well as on 'exclusive_range'. Suffixes '_scored', '_exclusion', and '_FPV'/'_PV' are appended to distinguish their respective purposes.
     - '_score' indicates data where suitability scores are assigned as follows: most_suitable is assigned a score of 1, suitable is assigned a score of 2, and least_suitable is assigned a score of 3. This data is used for calculating final scores in Step 8.
     - '_exclusion' signifies files with the same suffix as existing exclusion files, performing the same function of area exclusion. It represents the range of values specified in 'exclusive_range' saved into new files.
     - '_FPV'/'_PV' are used to distinguish between projects conducted on water (FPV - floating photovoltaics) and on land (PV - photovoltaics). '_FPV' treats GLOBathy waterbodies as AOIs, while '_PV' treats areas other than GLOBathy waterbodies as AOIs (the filename must contain the word 'GLOBathy').
   - This process generates 'step7_excel_template.xlsx' in the 'data\setting_excel' directory.
   - This process creates the result files in the 'data\step7' directory.

2. Since the 'AOI', 'exclusion', and 'layer_weight' inputs from Step 6 are utilized, there is no need to input them again if they were already provided in Step 6.


## Step 8. Calculate Result

1. Execute 'step8_calculate_result.py' using an IDE (such as Visual Studio Code).
   - This script utilizes 'step7_excel_template.xlsx' from the 'data\setting_excel' directory as input for setting values.
      'file_name', 'AOI', 'exclusion', and 'layer_weight' will be utilized for this step.
   - Input data is sourced from 'data\step7', where files in tif format are read.
   - Scores are calculated by summing the scores assigned to each layer (most_suitable-1, suitable-2, least_suitable-3) in areas within the 'AOI' but outside the 'exclusion' range, considering the weight of each layer. The sum is divided by the sum of all 'layer_weight' fields, and then multiplied by the proportion of each layer's 'layer_weight', rounded to three decimal places.
   - This process creates the result files in the 'data\step8' directory.
   - The resulting layers are raster (tif) files with values ranging from 1 to 3, where values closer to 1 are considered more suitable.

![flowchart](flowchart.png)

![setting_values](setting_values.png)

* figures can be editted with [draw.io](draw.io)




## Data Source

### Data Source Used in Google Colab's Sample Code
| Data               | Name of the source                                | Data Type | Link                                                |
|--------------------|---------------------------------------------------|-----------|-----------------------------------------------------|
| DEM                | GLO-30 DEM                                        | Raster    | [Link](https://gee-community-catalog.org/projects/glo30/?h=dem)             |
| Inland Bathymetry  | GLOBathy                                          | Raster    | [Link](https://gee-community-catalog.org/projects/globathy/?h=globathy)      |
| Solar Radiation-GHI| Global Solar Atlas                                | Raster    | [Link](https://gee-community-catalog.org/projects/gsa/?h=global+solar)       |
| Wind Speed         | Global Wind Atlas                                 | Raster    | [Link](https://gee-community-catalog.org/projects/gwa/?h=global+wind+atlas)  |
| Land Cover         | ESRI 10m Annual Land Use Land Cover (2017-2022)   | Raster    | [Link](https://gee-community-catalog.org/projects/S2TSLULC/?h=land+use)     |
| Roads              | GRIP                                              | Vector    | [Link](https://gee-community-catalog.org/projects/grip/?h=roads)             |
| Electrical Grid    | Global Power                                      | Vector    | [Link](https://gee-community-catalog.org/projects/global_power/?h=power)    |

* GLOBathy data provides approximate information and may contain missing waterbodies.


### Data Manually Merged and Downloaded Directly, Utilizing QGIS
| Data               | Name of the source                                | Data Type | Link                                                |
|--------------------|---------------------------------------------------|-----------|-----------------------------------------------------|
|Protected Area	   |Protected Planet                                   |Vector     |[Link](https://www.protectedplanet.net/en)           |


### Additional Development
   - Highlighting Excel Input Fields - to make it easy to understand the information required for each step of input. 
   - In cases where Slope criteria are required for site selection, add logic to calculate Slope using DEM data.
   - Functionality to filter by Waterbody size as a condition.
