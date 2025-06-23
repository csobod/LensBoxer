# LensBoxer.py - Creates boxing references for a selected closed curve
# Copyright (C) 2025 by Chad Sobodash
# This code is licensed under MIT license (see LICENSE.txt for details)

import adsk.core, adsk.fusion, adsk.cam, traceback

# Global list to keep handlers in scope
handlers = []

# Command details
CMD_ID = 'LensBoxerHotkeyCmd'
CMD_NAME = 'LensBoxer'
CMD_DESC = 'Creates boxing references for a selected closed curve.'
PANEL_ID = 'SketchCreatePanel' 

# This class contains the flawless logic from your script.
class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        ui = None
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            design = app.activeProduct

            if not design: return
            if not (design.activeEditObject and isinstance(design.activeEditObject, adsk.fusion.Sketch)):
                ui.messageBox('A sketch must be active. Please enter "Edit Sketch" mode.')
                return

            sketch = design.activeEditObject
            
            if ui.activeSelections.count != 1:
                ui.messageBox('Please select the eyewire, represented \nby a single closed sketch curve.')
                return
            eyewireCurve = ui.activeSelections.item(0).entity
            if not isinstance(eyewireCurve, adsk.fusion.SketchCurve) or not eyewireCurve.geometry.isClosed:
                ui.messageBox('The selected item must be a single closed sketch curve.\nTry to ensure all points are connected.')
                return

            bbox = eyewireCurve.boundingBox
            minPt, maxPt = bbox.minPoint, bbox.maxPoint
            centerPt = adsk.core.Point3D.create((minPt.x + maxPt.x) / 2, (minPt.y + maxPt.y) / 2, minPt.z)
            
            lines = sketch.sketchCurves.sketchLines
            dims = sketch.sketchDimensions
            
            p1 = adsk.core.Point3D.create(minPt.x, minPt.y, minPt.z)
            p2 = adsk.core.Point3D.create(maxPt.x, minPt.y, minPt.z)
            p3 = adsk.core.Point3D.create(maxPt.x, maxPt.y, minPt.z)
            p4 = adsk.core.Point3D.create(minPt.x, maxPt.y, minPt.z)
            
            bottom_line, right_line, top_line, left_line = lines.addByTwoPoints(p1, p2), lines.addByTwoPoints(p2, p3), lines.addByTwoPoints(p3, p4), lines.addByTwoPoints(p4, p1)
            for line in [bottom_line, right_line, top_line, left_line]: line.isConstruction = True

            width_dim_pt = adsk.core.Point3D.create(centerPt.x, maxPt.y + 0.5, minPt.z) 
            dims.addDistanceDimension(top_line.startSketchPoint, top_line.endSketchPoint, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, width_dim_pt)
            height_dim_pt = adsk.core.Point3D.create(maxPt.x + 0.5, centerPt.y, minPt.z)
            dims.addDistanceDimension(right_line.startSketchPoint, right_line.endSketchPoint, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, height_dim_pt)

            h_midline, v_midline = lines.addByTwoPoints(adsk.core.Point3D.create(minPt.x, centerPt.y, minPt.z), adsk.core.Point3D.create(maxPt.x, centerPt.y, minPt.z)), lines.addByTwoPoints(adsk.core.Point3D.create(centerPt.x, minPt.y, minPt.z), adsk.core.Point3D.create(centerPt.x, maxPt.y, minPt.z))
            h_midline.isConstruction, v_midline.isConstruction = True, True
            
            evaluator = eyewireCurve.geometry.evaluator
            (retVal, start_param, end_param) = evaluator.getParameterExtents()
            (retVal, curve_points) = evaluator.getPointsAtParameters([start_param + (i/200.0) * (end_param - start_param) for i in range(201)])

            furthest_point, max_dist = None, 0
            for pt in curve_points:
                dist = centerPt.distanceTo(pt)
                if dist > max_dist: max_dist, furthest_point = dist, pt
            
            if furthest_point:
                vec_to_center = furthest_point.vectorTo(centerPt)
                opposite_point = centerPt.copy()
                opposite_point.translateBy(vec_to_center)
                
                ed_line = lines.addByTwoPoints(opposite_point, furthest_point)
                ed_line.isConstruction = True
                dims.addDistanceDimension(ed_line.startSketchPoint, ed_line.endSketchPoint, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, centerPt)
        except:
            if ui: ui.messageBox('Script failed:\n{}'.format(traceback.format_exc()))

class CommandCreatedEventHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            cmd = args.command
            onExecute = CommandExecuteHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)
        except:
            app = adsk.core.Application.get()
            ui = app.userInterface
            if ui: ui.messageBox('Failed to create command:\n{}'.format(traceback.format_exc()))

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        cmdDef = ui.commandDefinitions.itemById(CMD_ID)
        if not cmdDef:
            # The resource folder is just the folder name, relative to the manifest.
            resource_folder = 'resources'
            cmdDef = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_DESC, resource_folder)
        
        onCommandCreated = CommandCreatedEventHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)
        
        sketchPanel = ui.allToolbarPanels.itemById(PANEL_ID)
        if sketchPanel:
            cntrl = sketchPanel.controls.itemById(CMD_ID)
            if not cntrl:
                sketchPanel.controls.addCommand(cmdDef)
        
    except:
        if ui: ui.messageBox('Failed to run add-in:\n{}'.format(traceback.format_exc()))

def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        sketchPanel = ui.allToolbarPanels.itemById(PANEL_ID)
        if sketchPanel:
            cntrl = sketchPanel.controls.itemById(CMD_ID)
            if cntrl:
                cntrl.deleteMe()
        
        cmdDef = ui.commandDefinitions.itemById(CMD_ID)
        if cmdDef:
            cmdDef.deleteMe()
            
    except:
        if ui: ui.messageBox('Failed to stop add-in:\n{}'.format(traceback.format_exc()))
