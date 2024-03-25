
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


# Multi Criteria Analysis
The workflow is based on [QGIS Tutorials and Tips - Multi Criteria Overlay Analysis (QGIS3)](https://www.qgistutorials.com/en/docs/3/multi_criteria_overlay.html)

The wrokflow of MCA with QGIS is also described on [SuntraceWiki](https://wiki.suntrace.de/wiki/Analysis_%E2%80%93_MCA_for_site_selection) as well 



# Code Execution
Please follow the description below for each step of the procedure.



## Step 1: Prepare Data

1. Create an Area of Interest (AOI) as a polygon in shapefile (.shp) format using QGIS.

2. Open the 'step1_prepare_data_GEE' file with the [Sample Code](https://colab.research.google.com/drive/1uMmtVNNbjE_4-qoH3WjihAMtjb1P1fSv?usp=sharing) on Google Colab.
   - This sample code is based on a tutorial by the YouTuber ['GeoDev'](https://www.youtube.com/watch?v=7fC7YqhoOPE). Please refer to the video for guidance on using the 'geemap' library.
   - In case the Colab link is lost, please check the backup code in [Jupyter Notebook format (.ipynb)](src/module/step1_prepare_data_GEE.ipynb).

3. Upload the shapefile of the AOI to the 'content' directory.

   ![image](https://github.com/chungkang/MCA/assets/36185863/85ebcb9d-310b-4d69-a04b-571b9afe025f)

4. Execute the code to download each data in use. The downloaded data will be displayed under the 'content' directory.

5. Download the data to the 'data\step1' directory.
 



![flowchart](flowchart.png)

![setting_values](setting_values.png)

* figures can be editted with [draw.io](draw.io)
