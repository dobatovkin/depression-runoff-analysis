import arcpy
import depressionevaluation
archydrotoolbox_py='C:/Program Files (x86)/ArcGIS/Desktop10.8/ArcToolbox/Toolboxes/Arc Hydro Tools Python'
class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [RunoffAnalysis]


class RunoffAnalysis(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Runoff Analysis"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        in_dem = arcpy.Parameter(
            displayName="Input raster DEM",
            name="in_dem",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_runoff = arcpy.Parameter(
            displayName="Runoff amount in mm",
            name="densify_dist",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        in_runoff.value = 10

        out_depr = arcpy.Parameter(
            displayName="Output depressions",
            name="out_depr",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        out_da = arcpy.Parameter(
            displayName="Output drainage areas",
            name="out_da",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # out_dl = arcpy.Parameter(
        #     displayName="Output drainage lines",
        #     name="out_features",
        #     datatype="DEFeatureClass",
        #     parameterType="Required",
        #     direction="Output")

        params = [in_dem, in_runoff, out_depr, out_da]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        in_dem=parameters[0].valueAsText
        in_runoff=parameters[1].valueAsText
        out_depr=parameters[2].valueAsText
        out_da=parameters[3].valueAsText
        
        arcpy.AddMessage('Importing Arc Hydro Tools Python...')

        arcpy.ImportToolbox(archydrotoolbox_py)

        arcpy.AddMessage('Delination of closed depressions and their drainage areas...')

        arcpy.DepressionEvaluation_archydropy(in_dem, out_depr, out_da)

        arcpy.AddMessage('Adding runoff fields...')

        arcpy.AddField_management(out_depr, 'DrainVolume', 'DOUBLE')
        arcpy.AddField_management(out_depr, 'OverflowVolume', 'DOUBLE')
        arcpy.AddField_management(out_depr, 'IsFilled', 'SHORT')

        arcpy.AddMessage('Calculating DrainVolume field...')

        arcpy.CalculateField_management(out_depr,
            'DrainVolume', '!DrainArea! * {0}/1000'.format(in_runoff), 
            'PYTHON_9.3')

        arcpy.AddMessage('Calculating OverflowVolume field...')

        arcpy.CalculateField_management(out_depr,
            'OverflowVolume', 'overflow(!DrainVolume!,!FillVolume!)'.format(in_runoff), 
            'PYTHON_9.3',
            '''def overflow(drain, fill):
                if  drain-fill>0:
                    return drain-fill
                else:
                    return 0''')

        arcpy.AddMessage('Calculating IsFilled field...')

        arcpy.CalculateField_management(out_depr, 
            'IsFilled',
            'overflowblob(!OverflowVolume!)',
            'PYTHON_9.3',
            '''def overflowblob(over):
                if  over>0:
                    return 1
                else:
                    return 0''')

        return
