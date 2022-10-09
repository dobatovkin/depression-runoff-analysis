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

        out_dr_dl = arcpy.Parameter(
            displayName="Output depression drainage lines",
            name="out_dr_dl",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        out_hyd_jun = arcpy.Parameter(
            displayName="Output hydro junction points",
            name="out_hyd_jun",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        params = [in_dem, in_runoff, out_depr, out_da, out_dr_dl, out_hyd_jun]
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
        out_depr=parameters[2].valueAsText
        out_da=parameters[3].valueAsText
        out_dr_dl=parameters[4].valueAsText
        out_hyd_jun=parameters[5].valueAsText

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

        # !Connectivity block


        arcpy.AddMessage('Calculating Sink Structures...')
        sink_poly='in_memory/sink_poly'
        sink_poly_grid='in_memory/sink_poly_grid'
        sink_pnt='in_memory/sink_pnt'
        sink_pnt_grid='in_memory/sink_pnt_grid'
        arcpy.CreateSinkStructures_archydropy(in_dem, out_depr, sink_poly, sink_poly_grid, sink_pnt, sink_pnt_grid) 

        arcpy.AddMessage('Calculating flow direction raster...')

        flowdir = 'in_memory/flowdir'
        arcpy.FlowDirection_archydropy(in_dem, flowdir)

        flowdir_adj='in_memory/flowdir_adj'
        arcpy.AdjustFlowDirectioninSinks_archydropy(flowdir, sink_pnt_grid, sink_poly_grid, flowdir_adj) 

        arcpy.AddMessage('Calculating flow accumulation raster...')

        flowacc = 'in_memory/flowacc'
        arcpy.FlowAccumulation_archydropy(flowdir_adj, flowacc)

        sink_DA_grid='in_memory/sink_DA_grid'
        sink_DA='in_memory/sink_DA'
        arcpy.CatchmentGridDelineation_archydropy(flowdir_adj, sink_pnt_grid, sink_DA_grid)
        arcpy.CatchmentPolyProcessing_archydropy(sink_DA_grid, sink_DA)

        dr_pnt='in_memory/dr_pnt'
        arcpy.DrainagePointProcessing_archydropy(flowacc, sink_DA_grid, sink_DA, dr_pnt) 

        dr_boundary='in_memory/dr_boundary'
        dr_conn='in_memory/dr_conn'
        arcpy.DrainageBoundaryDefinition_archydropy(sink_DA, in_dem, dr_boundary, dr_conn)

        hyd_edge='in_memory'
        arcpy.DrainageConnectivityCharacterization_archydropy(in_dem, flowdir_adj, sink_DA, dr_boundary, dr_pnt, dr_conn, hyd_edge, out_hyd_jun, out_dr_dl)

        arcpy.SelectLayerByAttribute_management(out_hyd_jun, 'NEW_SELECTION', 'NextDownID = -1')
        arcpy.management.DeleteFeatures(out_hyd_jun)

        arcpy.AddMessage('Adding connection fields...')

        arcpy.AddField_management(out_depr, 'HydJunID', 'LONG')
        arcpy.AddField_management(out_depr, 'NextDownID', 'LONG')
        arcpy.AddField_management(out_depr, 'UpstreamVolume', 'DOUBLE')
        
        for row in arcpy.da.UpdateCursor(out_depr, ['OID@', 'HydJunID', 'HydJunID']):
            arcpy.SelectLayerByAttribute_management(out_da, 'NEW_SELECTION', 'OID@ = {0}'.format(row[0]))
            arcpy.SelectLayerByLocation_management(out_hyd_jun, 'INTERSECT', out_da)
            arcpy.SelectLayerByAttribute_management(out_hyd_jun, SUBSET_SELECTION,)


        arcpy.AddMessage('Calculating UpstreamVolume field...')

        arcpy.AddMessage('SUCCESS')

        return
