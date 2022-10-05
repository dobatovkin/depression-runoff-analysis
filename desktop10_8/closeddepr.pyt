import arcpy
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
        self.label = "Runoff Analysis"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        in_dem = arcpy.Parameter(
            displayName="Input raster DEM",
            name="in_dem",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        in_runoff = arcpy.Parameter(
            displayName="Runoff amount in mm",
            name="in_runoff",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        in_runoff.value = 10

        in_dl_area = arcpy.Parameter(
            displayName="Area to define a stream in amount of DEM cells",
            name="in_dl_area",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        in_dl_area.value = 1000

        out_depr = arcpy.Parameter(
            displayName="Output depressions",
            name="out_depr",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        out_da = arcpy.Parameter(
            displayName="Output depression drainage areas",
            name="out_da",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        out_dl = arcpy.Parameter(
            displayName="Output drainage lines (streams)",
            name="out_dl",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        params = [in_dem, in_runoff, in_dl_area, out_depr, out_da, out_dl]
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
        
        # !Base block

        # Parameters definition
        in_dem=parameters[0].valueAsText
        in_runoff=float(parameters[1].valueAsText)
        in_dl_area=parameters[2].valueAsText
        out_depr=parameters[3].valueAsText
        out_da=parameters[4].valueAsText
        out_dl=parameters[5].valueAsText
        
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

        arcpy.AddMessage('Calculating flow direction raster...')

        flowdir = 'in_memory/flowdir'
        arcpy.FlowDirection_archydropy(in_dem, flowdir)

        arcpy.AddMessage('Calculating flow accumulation raster...')

        flowacc = 'in_memory/flowacc'
        arcpy.FlowAccumulation_archydropy(in_dem, flowacc)

        arcpy.AddMessage('Calculating drainage lines...')

        dl_raster='in_memory/dl_raster'
        dllnk_raster='in_memory/dllnk_raster'
        arcpy.StreamDefinition_archydropy(flowacc, in_dl_area, dl_raster)
        arcpy.StreamSegmentation_archydropy(dl_raster, flowdir, dllnk_raster)
        arcpy.DrainageLineProcessing_archydropy(dllnk_raster, flowdir, out_dl) 

        # !Connectivity block

        arcpy.AddMessage('Calculating filled DEM')
        
        fill_dem='in_memory/fill_DEM'
        arcpy.FillSinks_archydropy (in_dem, fill_dem)  

        arcpy.AddMessage('Calculating flow direction raster for filled DEM...')

        fill_flowdir = 'in_memory/fill_flowdir'
        arcpy.FlowDirection_archydropy(fill_dem, fill_flowdir)

        arcpy.AddMessage('Calculating flow accumulation raster for filled DEM...')

        fill_flowacc = 'in_memory/fill_flowacc'
        arcpy.FlowAccumulation_archydropy(fill_dem, fill_flowacc)    

        # arcpy.AddMessage('Adding connection fields...')

        # arcpy.AddField_management(out_depr, 'NextDownID', 'LONG')
        # arcpy.AddField_management(out_depr, 'UpstreamVolume', 'DOUBLE')
        
        # arcpy.AddMessage('Calculating UpstreamVolume field...')

        arcpy.AddMessage('SUCCESS')

        return
