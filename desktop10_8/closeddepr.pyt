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
        # ? Next tool seems broken for .pyt use -- it cannot output to scratch workspace 
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
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        in_da = arcpy.Parameter(
            displayName="Input depressions' drainage areas",
            name="in_da",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        in_hyd_jun = arcpy.Parameter(
            displayName="Input hydro junction points",
            name="in_hyd_jun",
            datatype="GPFeatureLayer",
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
        
        # in_runoff, in_depr, in_da, in_hyd_jun

        in_runoff = int(parameters[0].valueAsText)
        in_depr = parameters[1].valueAsText
        in_da = parameters[2].valueAsText
        in_hyd_jun = parameters[3].valueAsText

        depr='depr'
        dra='dra'
        hyd_jun='hyd_jun'
        arcpy.MakeFeatureLayer_management(in_depr, depr)
        arcpy.MakeFeatureLayer_management(in_da, dra)
        arcpy.MakeFeatureLayer_management(in_hyd_jun, hyd_jun)
        arcpy.AddMessage('Removing unnecessary hydro junction points...')

        arcpy.SelectLayerByAttribute_management(hyd_jun, 'NEW_SELECTION', 'NextDownID = -1')
        arcpy.management.DeleteFeatures(hyd_jun)

        arcpy.AddMessage('Adding connection fields...')

        arcpy.AddField_management(depr, 'HydJunID', 'LONG')
        arcpy.AddField_management(depr, 'NextDrownID', 'LONG')
        arcpy.AddField_management(depr, 'NextDownID', 'LONG')
        
        arcpy.AddField_management(depr, 'UpstreamVolume', 'DOUBLE')
        arcpy.AddField_management(hyd_jun, 'IsActive', 'SHORT')
        arcpy.AddField_management(hyd_jun, 'Elevin', 'LONG')
        arcpy.CalculateField_management(hyd_jun, 'Elevin', '!Elev!*100000', 'PYTHON_9.3')

        # ! Connectivity loop block

        # todo: It can be a good idea to add progressor, considering amount of loops

        with arcpy.da.UpdateCursor(depr, ['DrainID', 'HydJunID', 'NextDrownID']) as cursor:
            for row in cursor:
                arcpy.SelectLayerByAttribute_management(dra, 'NEW_SELECTION', 'HydroID = {0}'.format(row[0]))
                arcpy.SelectLayerByLocation_management(hyd_jun, 'INTERSECT', dra)
                arcpy.CalculateField_management(hyd_jun, 'IsActive', '1', 'PYTHON_9.3')

                # todo: Speed up making an FL - exctract fewer fields 

                curr_hyd_jun = "curr_hyd_jun"
                arcpy.MakeFeatureLayer_management(hyd_jun, curr_hyd_jun, where_clause='IsActive = 1')
                
                elevList = [r[0] for r in arcpy.da.SearchCursor (curr_hyd_jun, ['Elevin'])]    # <-- proud of this 
                arcpy.AddMessage(elevList)
                arcpy.SelectLayerByAttribute_management(curr_hyd_jun, 'NEW_SELECTION', 'Elevin = {0}'.format(min(elevList)))
                
                count = int(str(arcpy.management.GetCount(curr_hyd_jun)))
                if count == 1:
                    for upper_row in arcpy.da.SearchCursor(curr_hyd_jun, ['HydroID']):
                        row[1] = upper_row[0]
                else: arcpy.AddMessage("Error "+str(count))

                arcpy.SelectLayerByLocation_management(dra, 'INTERSECT', curr_hyd_jun, selection_type='NEW_SELECTION')
                arcpy.SelectLayerByAttribute_management(dra, 'REMOVE_FROM_SELECTION', 'HydroID = {0}'.format(row[0]))

                if int(str(arcpy.management.GetCount(dra))) == 1:
                    for upper_row in arcpy.da.SearchCursor(dra, ['HydroID']):
                        row[2] = upper_row[0]
                else:
                    row[2] = -1
                    row[1] = -1

                arcpy.Delete_management(curr_hyd_jun)

                arcpy.SelectLayerByAttribute_management(hyd_jun, 'NEW_SELECTION', 'IsActive = 1')
                arcpy.CalculateField_management(hyd_jun, 'IsActive', '0', 'PYTHON_9.3')

                arcpy.SelectLayerByAttribute_management(hyd_jun, 'CLEAR_SELECTION')
                arcpy.SelectLayerByAttribute_management(dra, 'CLEAR_SELECTION')                

                cursor.updateRow(row)


        arcpy.DeleteField_management(hyd_jun, 'Elevin')

        # ! Order definition block
        
        arcpy.AddField_management(dra, 'DeprID', 'LONG')
        arcpy.AddField_management(depr, 'DeprOrder', 'SHORT')
        arcpy.JoinField_management(dra, 'HydroID', depr, 'DrainID', 'HydroID')
        arcpy.CalculateField_management(dra, 'DeprID', '!HydroID_1!', 'PYTHON_9.3')
        arcpy.DeleteField_management(dra, 'HydroID_1')
        
        
        arcpy.JoinField_management(depr, 'NextDrownID', dra, 'HydroID', 'DeprID')
        arcpy.CalculateField_management(depr, 'NextDownID', '!DeprID!', 'PYTHON_9.3')
        arcpy.DeleteField_management(depr, 'DeprID')
        arcpy.SelectLayerByAttribute_management(depr, 'NEW_SELECTION', 'NextDrownID = -1')
        arcpy.CalculateField_management(depr, 'NextDownID', '-1', 'PYTHON_9.3')
        arcpy.CalculateField_management(depr, 'DeprOrder', '1', 'PYTHON_9.3')
        arcpy.SelectLayerByAttribute_management(depr, 'CLEAR_SELECTION')
      
        i = 1
        i_list = []
        while True:
            i_list.append(i)
            arcpy.AddMessage('Processing {0} order...'.format(i))
            hydro_values = [row[0] for row in arcpy.da.SearchCursor(depr, "HydroID", where_clause='DeprOrder = {0}'.format(i))]
            i += 1
            if len(hydro_values) == 0:
                break
            arcpy.SelectLayerByAttribute_management(depr, 'NEW_SELECTION', 'NextDownID in '+str(tuple(hydro_values)))
            arcpy.CalculateField_management(depr, 'DeprOrder', str(i), 'PYTHON_9.3')
            
            arcpy.SelectLayerByAttribute_management(depr, 'NEW_SELECTION', 'DeprOrder IS NULL')
            if int(str(arcpy.management.GetCount(depr))) == 0:
                break
            arcpy.SelectLayerByAttribute_management(depr, 'CLEAR_SELECTION')

        arcpy.AddMessage('Calculating UpstreamVolume field...')

        # for n in range(i-1, 0, -1):
        #     for row in arcpy.da.UpdateCursor(depr, ['UpstreamVolume', 'OverflowVolume', 'DrainVolume',], where_clause='Order = {0}'.format(n))
        #     row[0] = sum([r[0] for r in arcpy.da.SearchCursor (depr, ['OverflowVolume'], where_clause='Order = {0}'.format(n+1))])
               
        
        # ! Cleaning up block

        arcpy.Delete_management(arcpy.env.scratchGDB)
        arcpy.Delete_management(arcpy.env.scratchFolder)
        # arcpy.Delete_management(arcpy.env.scratchWorkspace)
        
        arcpy.AddMessage('SUCCESS')

        return