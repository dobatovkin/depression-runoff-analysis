import arcpy
archydrotoolbox_py='C:/Program Files (x86)/ArcGIS/Desktop10.8/ArcToolbox/Toolboxes/Arc Hydro Tools Python'
class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [RunoffAnalysis, ConnectivityAnalysis]


class RunoffAnalysis(object):
    def __init__(self):
        self.label = "1) Runoff Analysis"
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

        out_hyd_edge = arcpy.Parameter(
            displayName="Output hydro edge lines",
            name="out_hyd_edge",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        params = [in_dem, in_runoff, out_depr, out_da, out_dr_dl, out_hyd_jun, out_hyd_edge]
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
        out_hyd_edge=parameters[6].valueAsText

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

        # !Connectivity prep block


        arcpy.AddMessage('Calculating Sink Structures...')
        sink_poly = '{0}\\sink_poly'.format(arcpy.env.scratchGDB)
        sink_poly_grid = '{0}\\sink_poly_grid'.format(arcpy.env.scratchWorkspace)
        sink_pnt = '{0}\\sink_pnt'.format(arcpy.env.scratchGDB)
        sink_pnt_grid = '{0}\\sink_pnt_grid'.format(arcpy.env.scratchWorkspace)
        
        arcpy.CreateSinkStructures_archydropy(in_dem, out_depr, sink_poly, sink_poly_grid, sink_pnt, sink_pnt_grid) 

        arcpy.AddMessage('Calculating flow direction raster...')

        flowdir = '{0}\\flowdir'.format(arcpy.env.scratchWorkspace)
        arcpy.FlowDirection_archydropy(in_dem, flowdir)

        flowdir_adj='{0}\\flowdir_adj'.format(arcpy.env.scratchWorkspace)
        arcpy.AdjustFlowDirectioninSinks_archydropy(flowdir, sink_pnt_grid, sink_poly_grid, flowdir_adj) 

        arcpy.AddMessage('Calculating flow accumulation raster...')

        flowacc = '{0}\\flowacc'.format(arcpy.env.scratchWorkspace)
        arcpy.FlowAccumulation_archydropy(flowdir_adj, flowacc)

        sink_DA_grid='{0}\\sink_DA_grid'.format(arcpy.env.scratchWorkspace)
        sink_DA='{0}\\sink_DA'.format(arcpy.env.scratchGDB)
        arcpy.CatchmentGridDelineation_archydropy(flowdir_adj, sink_pnt_grid, sink_DA_grid)
        arcpy.CatchmentPolygonProcessing_archydropy(sink_DA_grid, sink_DA)

        dr_pnt='{0}\\dr_pnt'.format(arcpy.env.scratchGDB)
        arcpy.DrainagePointProcessing_archydropy(flowacc, sink_DA_grid, sink_DA, dr_pnt) 

        dr_boundary='{0}\\dr_boundary'.format(arcpy.env.scratchGDB)
        dr_conn='{0}\\dr_conn'.format(arcpy.env.scratchGDB)
        arcpy.DrainageBoundaryDefinition_archydropy(sink_DA, in_dem, dr_boundary, dr_conn)

        # hyd_edge='{0}\\hyd_edge'.format(arcpy.env.scratchGDB)
        arcpy.DrainageConnectivityCharacterization_archydropy(in_dem, flowdir_adj, sink_DA, dr_boundary, dr_pnt, dr_conn, out_hyd_edge, out_hyd_jun, out_dr_dl)

        return

class ConnectivityAnalysis(object):
    def __init__(self):
        self.label = "2) Connectivity Analysis"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        in_runoff = arcpy.Parameter(
            displayName="Runoff amount in mm",
            name="in_runoff",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        in_runoff.value = 10

        in_depr = arcpy.Parameter(
            displayName="Input depressions",
            name="in_depr",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        in_da = arcpy.Parameter(
            displayName="Input depressions' drainage areas",
            name="in_da",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        in_hyd_jun = arcpy.Parameter(
            displayName="Input hydro junction points",
            name="in_hyd_jun",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        params = [in_runoff, in_depr, in_da, in_hyd_jun]
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

        arcpy.SelectLayerByAttribute_management(out_hyd_jun, 'NEW_SELECTION', 'NextDownID = -1')
        arcpy.management.DeleteFeatures(out_hyd_jun)

        arcpy.AddMessage('Adding connection fields...')

        arcpy.AddField_management(out_depr, 'HydJunID', 'LONG')
        arcpy.AddField_management(out_depr, 'NextDownID', 'LONG')
        arcpy.AddField_management(out_depr, 'UpstreamVolume', 'DOUBLE')
        arcpy.AddField_management(out_hyd_jun, 'IsActive', 'SHORT')
        
        # !Connectivity loop block
        with arcpy.da.UpdateCursor(out_depr, ['OID@', 'HydJunID', 'NextDownID']) as cursor:
            for row in cursor:
                arcpy.SelectLayerByAttribute_management(out_da, 'NEW_SELECTION', 'OID@ = {0}'.format(row[0]))
                arcpy.SelectLayerByLocation_management(out_hyd_jun, 'INTERSECT', out_da)
                arcpy.CalculateField_management(out_hyd_jun, 'IsActive', '1', 'PYTHON_9.3')

                elev_row=[]
                for lower_row in arcpy.da.SearchCursor(out_hyd_jun, ['Elev'], where_clause='IsActive = 1'):
                    elev_row.append(float(lower_row[0]))

                arcpy.AddMessage('Processing depr', str(row[0]))
                arcpy.AddMessage(str(elev_row))

                min_elev=min(elev_row)
                arcpy.SelectLayerByAttribute_management(out_hyd_jun, 'SUBSET_SELECTION', 
                    where_clause='Elev = {0}'.format(min_elev))

                arcpy.CalculateField_management(out_hyd_jun, 'IsActive', '2', 'PYTHON_9.3')

                with arcpy.da.UpdateCursor(out_hyd_jun, ['HydroID', 'IsActive'], where_clause='IsActive = 2') as upper_cursor:
                    for upper_row in upper_cursor:
                        row[1]=upper_row[0]
                        upper_row[1] = 3
                        upper_cursor.updateRow(upper_row)

                arcpy.SelectLayerByAttribute_management(out_hyd_jun, 'NEW_SELECTION', 'IsActive = 1')
                arcpy.CalculateField_management(out_hyd_jun, 'IsActive', '0', 'PYTHON_9.3')

                arcpy.SelectLayerByAttribute_management(out_hyd_jun, 'CLEAR_SELECTION')
                arcpy.SelectLayerByAttribute_management(out_da, 'CLEAR_SELECTION')

                cursor.updateRow(row)

    

        arcpy.AddMessage('Calculating UpstreamVolume field...')

        # ! Cleaning up block

        # arcpy.Delete_management(arcpy.env.scratchGDB)
        # arcpy.Delete_management(arcpy.env.scratchFolder)
        # arcpy.Delete_management(arcpy.env.scratchWorkspace)
        
        arcpy.AddMessage('SUCCESS')

        return