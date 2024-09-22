import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
from maya import OpenMayaUI as omui
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtGui import QColor
from PySide2.QtCore import QTimer, QPropertyAnimation, QEasingCurve
from shiboken2 import wrapInstance
from functools import wraps


def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)

def hex_value(hex_color, factor):
    color = QColor(hex_color)
    h, s, v, a = color.getHsvF()
    v = min(max(v * factor, 0), 1) 
    color.setHsvF(h, s, v, a)
    return color.name()

def undoable(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cmds.undoInfo(openChunk=True)
        try:
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True)
    return wrapper

def create_loc_object(object_name):
    object_data = {"shapes":[{"pos_vectors":[[0.0,1.0,0.0],[0.707107,0.707107,0.0],[1.0,0.0,0.0],[0.707107,-0.707107,0.0],[0.0,-1.0,0.0],[-0.707107,-0.707107,0.0],[-1.0,0.0,0.0],[-0.707107,0.707107,0.0],[0.0,1.0,0.0]],"degree":1,"knots":[],"form":0,"offset":[0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,1.0]},{"pos_vectors":[[0.0,0.0,1.0],[0.707107,-0.0,0.707107],[1.0,0.0,0.0],[0.707107,0.0,-0.707107],[0.0,0.0,-1.0],[-0.707107,0.0,-0.707107],[-1.0,0.0,0.0],[-0.707107,-0.0,0.707107],[0.0,0.0,1.0]],"degree":1,"knots":[],"form":0,"offset":[0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,1.0]},{"pos_vectors":[[0.0,0.0,1.0],[0.0,0.707107,0.707107],[-0.0,1.0,0.0],[-0.0,0.707107,-0.707107],[0.0,0.0,-1.0],[0.0,-0.707107,-0.707107],[0.0,-1.0,0.0],[0.0,-0.707107,0.707107],[0.0,0.0,1.0]],"degree":1,"knots":[],"form":0,"offset":[0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,1.0]},{"pos_vectors":[[-1.687391,0.0,0.0],[1.687391,0.0,0.0]],"degree":1,"knots":[],"form":2,"offset":[0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,1.0]},{"pos_vectors":[[0.0,0.0,1.687391],[0.0,0.0,-1.687391]],"degree":1,"knots":[],"form":2,"offset":[0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,1.0]},{"pos_vectors":[[0.0,-1.687391,0.0],[0.0,1.687391,0.0]],"degree":1,"knots":[],"form":2,"offset":[0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,0.433188,0.0,0.0,0.0,0.0,1.0]}]}
    created_curves = []
    shapes_data = object_data.get("shapes", [object_data])
    for i, shape_data in enumerate(shapes_data):
        required_keys = ["form", "pos_vectors", "knots", "degree"]
        for key in required_keys:
            if key not in shape_data:
                raise Exception(f"Cannot create curve with lacking curve data: missing {key}")

        points = shape_data["pos_vectors"]
        curve_name = f"{object_name}_curve_{i+1}"
        new_node = cmds.curve(p=points, k=shape_data["knots"], d=shape_data["degree"], name=curve_name)
        
        # Get the shape node and rename it
        curve_shapes = cmds.listRelatives(new_node, shapes=True, fullPath=True) or []
        if curve_shapes:
            curve_shape = curve_shapes[0]
            cmds.rename(curve_shape, f"{curve_name}Shape")

        if shape_data["form"] > 0:
            cmds.closeCurve(new_node, ch=False, rpo=True)
        if "offset" in shape_data:
            offset_matrix = shape_data["offset"]
            cmds.xform(new_node, matrix=offset_matrix, worldSpace=True)
        created_curves.append(new_node)

    for curve in created_curves:
        cmds.makeIdentity(curve, apply=True, translate=True, rotate=True, scale=True)

    curve_group = cmds.group(empty=True, name=object_name)
    cmds.select(clear=True)
    curve_shapes = []
    for curve in created_curves:
        shapes = cmds.listRelatives(curve, shapes=True, fullPath=True) or []
        curve_shapes.extend(shapes)

    if curve_shapes:
        cmds.select(curve_shapes, replace=True)
        cmds.select(curve_group, add=True)
        mel.eval('parent -r -s')

    for curve in created_curves:
        if not cmds.listRelatives(curve, children=True):
            cmds.delete(curve)
    
    cmds.xform(curve_group, centerPivots=True)
    cmds.select(curve_group, replace=True)
    mel.eval(f'rename `ls -sl` {object_name};')
    mel.eval('move -rpr 0 0 0;')
    mel.eval('FreezeTransformations;')
    mel.eval('makeIdentity -apply true -t 1 -r 1 -s 1 -n 0 -pn 1;')
    cmds.setAttr(f"{object_name}.overrideEnabled", 1)
    cmds.setAttr(f"{object_name}.overrideColor", 13)

#----------------------------------------------------------------------------------------------------------------
def create_curve(object_name, object_data):
        created_curves = []
        shapes_data = object_data.get("shapes", [object_data])
        for i, shape_data in enumerate(shapes_data):
            required_keys = ["form", "pos_vectors", "knots", "degree"]
            for key in required_keys:
                if key not in shape_data:
                    raise Exception(f"Cannot create curve with lacking curve data: missing {key}")

            points = shape_data["pos_vectors"]
            curve_name = f"{object_name}_curve_{i+1}"
            new_node = cmds.curve(p=points, k=shape_data["knots"], d=shape_data["degree"], name=curve_name)
            
            # Get the shape node and rename it
            curve_shapes = cmds.listRelatives(new_node, shapes=True, fullPath=True) or []
            if curve_shapes:
                curve_shape = curve_shapes[0]
                cmds.rename(curve_shape, f"{curve_name}Shape")

            if shape_data["form"] > 0:
                cmds.closeCurve(new_node, ch=False, rpo=True)
            if "offset" in shape_data:
                offset_matrix = shape_data["offset"]
                cmds.xform(new_node, matrix=offset_matrix, worldSpace=True)
            created_curves.append(new_node)

        for curve in created_curves:
            cmds.makeIdentity(curve, apply=True, translate=True, rotate=True, scale=True)

        curve_group = cmds.group(empty=True, name=object_name)
        cmds.select(clear=True)
        curve_shapes = []
        for curve in created_curves:
            shapes = cmds.listRelatives(curve, shapes=True, fullPath=True) or []
            curve_shapes.extend(shapes)

        if curve_shapes:
            cmds.select(curve_shapes, replace=True)
            cmds.select(curve_group, add=True)
            mel.eval('parent -r -s')

        for curve in created_curves:
            if not cmds.listRelatives(curve, children=True):
                cmds.delete(curve)
        
        cmds.xform(curve_group, centerPivots=True)
        cmds.select(curve_group, replace=True)
        mel.eval('rename `ls -sl` "{0}";'.format(object_name))
        mel.eval('move -rpr 0 0 0;')
        mel.eval('FreezeTransformations;')
        mel.eval('makeIdentity -apply true -t 1 -r 1 -s 1 -n 0 -pn 1;')

        object_name = cmds.ls(curve_group)[0]
        
        return object_name

circle_18_shape = {"shapes": [{"pos_vectors":[[1.0,0.0,0.0],[0.939693,0.34202,0.0],[0.766044,0.642788,0.0],[0.5,0.866025,0.0],[0.173648,0.984808,0.0],[-0.173648,0.984808,0.0],[-0.5,0.866025,0.0],[-0.766044,0.642788,0.0],[-0.939693,0.34202,0.0],[-1.0,0.0,0.0],[-0.939693,-0.34202,0.0],[-0.766044,-0.642788,0.0],[-0.5,-0.866025,0.0],[-0.173648,-0.984808,0.0],[0.173648,-0.984808,0.0],[0.5,-0.866025,0.0],[0.766044,-0.642788,0.0],[0.939693,-0.34202,0.0],[1.0,0.0,0.0]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0,17.0,18.0],"form":0,"offset":[1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.195995,1.0]}]}
square_shape  = {"shapes": [{"pos_vectors":[[1.0,1.0,0.0],[-1.0,1.0,0.0],[-1.0,-1.0,0.0],[1.0,-1.0,0.0],[1.0,1.0,0.0]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0],"form":0,"offset":[1.0,0.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,-1.0,0.0,0.0,0.0,0.0,0.0,1.0]}]}
cube_shape = {"shapes": [{"pos_vectors":[[-5.150279,5.150279,5.150279],[-5.150279,5.150279,-5.150279],[5.150279,5.150279,-5.150279],[5.150279,5.150279,5.150279],[-5.150279,5.150279,5.150279],[-5.150279,-5.150279,5.150279],[-5.150279,-5.150279,-5.150279],[-5.150279,5.150279,-5.150279],[-5.150279,5.150279,5.150279],[-5.150279,-5.150279,5.150279],[5.150279,-5.150279,5.150279],[5.150279,5.150279,5.150279],[5.150279,5.150279,-5.150279],[5.150279,-5.150279,-5.150279],[5.150279,-5.150279,5.150279],[5.150279,-5.150279,-5.150279],[-5.150279,-5.150279,-5.150279]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0],"form":0,"offset":[0.205628,0.0,0.0,0.0,0.0,0.205628,0.0,0.0,0.0,0.0,0.205628,0.0,0.0,0.0,0.0,1.0]}]}
triangle_shape = {"shapes": [{"pos_vectors":[[0.0,0.369752,-0.369752],[0.0,-0.369752,-0.369752],[0.0,0.0,0.369752],[0.0,0.369752,-0.369752]],"degree":1,"knots":[0.0,1.0,2.0,3.0],"form":0,"offset":[2.874707,0.0,0.0,0.0,0.0,2.874707,0.0,0.0,0.0,0.0,2.874707,0.0,0.0,0.0,0.0,1.0]}]}
pyramid_shape = {"shapes": [{"pos_vectors":[[-0.738213,-0.0,-0.738213],[0.738213,-0.0,-0.738213],[0.738213,-0.0,0.738213],[-0.738213,-0.0,0.738213],[-0.738213,-0.0,-0.738213],[-0.0,1.539523,-0.0],[0.738213,-0.0,-0.738213],[0.738213,-0.0,0.738213],[-0.0,1.539523,-0.0],[-0.738213,-0.0,0.738213],[-0.738213,-0.0,-0.738213],[-0.0,1.539523,-0.0],[0.738213,-0.0,-0.738213]],"degree":1,"knots":[0.0,4.0,8.0,12.0,16.0,24.485,32.97,36.97,45.455,53.941,57.941,66.426,74.911],"form":0,"offset":[1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]}]}
arrow_shape = {"shapes": [{"pos_vectors":[[-0.418175,-1.25,0.0],[-0.418175,-0.25,0.0],[-1.0,-0.25,0.0],[0.0,1.25,0.0],[1.0,-0.25,0.0],[0.418175,-0.25,0.0],[0.418175,-1.25,0.0],[-0.418175,-1.25,0.0]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0],"form":0,"offset":[1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]}]}
cycle_shape = {"shapes": [{"pos_vectors":[[1.821412,-0.0,3.228411],[2.575865,-0.0,2.649498],[3.154778,-0.0,1.895045],[3.518698,-0.0,1.016465],[3.642823,-0.0,0.073633],[3.518698,-0.0,-0.8692],[3.154777,-0.0,-1.74778],[2.575865,-0.0,-2.502233],[1.821411,-0.0,-3.081145],[1.421608,-0.0,-2.462164],[0.717669,-0.0,-4.559907],[0.720485,-0.0,-4.567671],[2.786863,-0.0,-4.843799],[2.45964,-0.0,-4.18659],[3.478457,-0.0,-3.404825],[4.260222,-0.0,-2.386008],[4.75166,-0.0,-1.199571],[4.919281,-0.0,0.073632],[4.751661,-0.0,1.346836],[4.260222,-0.0,2.533273],[3.478457,-0.0,3.55209],[2.459641,-0.0,4.333856],[2.459641,-0.0,4.333856],[2.459641,-0.0,4.333856],[2.459641,-0.0,4.333856]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0,17.0,18.0,19.0,20.0,21.0,22.0,23.0,24.0],"form":2,"offset":[0.329236,0.0,0.0,0.0,0.0,0.329236,0.0,0.0,0.0,0.0,0.329236,0.0,0.0,0.0,0.0,1.0]},
                          {"pos_vectors":[[-1.821412,-0.0,3.228411],[-1.540693,-0.0,2.763896],[-0.698641,-0.0,4.568377],[-0.702549,-0.0,4.57625],[-2.736469,-0.0,4.843799],[-2.459641,-0.0,4.333856],[-3.478457,-0.0,3.55209],[-4.260222,-0.0,2.533273],[-4.751661,-0.0,1.346836],[-4.919281,-0.0,0.073632],[-4.75166,-0.0,-1.199571],[-4.260222,-0.0,-2.386008],[-3.478457,-0.0,-3.404825],[-2.45964,-0.0,-4.18659],[-1.821411,-0.0,-3.081145],[-2.575865,-0.0,-2.502233],[-3.154777,-0.0,-1.74778],[-3.518698,-0.0,-0.8692],[-3.642823,-0.0,0.073633],[-3.518698,-0.0,1.016465],[-3.154778,-0.0,1.895045],[-2.575865,-0.0,2.649498],[-2.575865,-0.0,2.649498],[-2.575865,-0.0,2.649498],[-2.575865,-0.0,2.649498]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0,17.0,18.0,19.0,20.0,21.0,22.0,23.0,24.0],"form":2,"offset":[0.329236,0.0,0.0,0.0,0.0,0.329236,0.0,0.0,0.0,0.0,0.329236,0.0,0.0,0.0,0.0,1.0]}]}

#----------------------------------------------------------------------------------------------------------------
class DoubleClickButton(QtWidgets.QPushButton):
    singleClicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(DoubleClickButton, self).__init__(*args, **kwargs)
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.performSingleClick)
        self.click_count = 0

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.click_count += 1
            if not self.timer.isActive():
                self.timer.start(300)
        super(DoubleClickButton, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.click_count == 2:
                self.timer.stop()
                self.click_count = 0
                self.doubleClicked.emit()
        super(DoubleClickButton, self).mouseReleaseEvent(event)

    def performSingleClick(self):
        if self.click_count == 1:
            self.singleClicked.emit()
        self.click_count = 0

class CustomButton(DoubleClickButton):
    def __init__(self, text='', icon=None, color='#4d4d4d', tooltip='', flat=False, size=None, width=None, height=None, parent=None, radius = 3):
        super().__init__(parent)
        self.setFlat(flat)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        if flat:
            self.setStyleSheet(f"background-color: transparent;")
        else:
            self.setStyleSheet(f'''QPushButton{{background-color: {color};border-radius: {radius}px;}}
                                    QPushButton:hover {{background-color: {hex_value(color, 1.2)} ;}}
                                    QPushButton:pressed  {{background-color: {hex_value(color, 0.8)} ;}}
                                    QToolTip {{background-color: {color};color: white; border:0px;}}''')
        
        icon_size = size if size else 24
        
        if icon:
            self.setIcon(QtGui.QIcon(icon))
            self.setIconSize(QtCore.QSize(icon_size, icon_size))
        
        if text:
            self.setText(text)
            if height is None:
                self.setFixedHeight(24)
            if width is None:
                if icon:
                    # If both icon and text are present, add some padding
                    self.setMinimumWidth(self.calculate_button_width(text, padding=30))
                    self.setStyleSheet(self.styleSheet() + " QPushButton {{ text-align: right; padding-right: 10px; }}")
                else:
                    self.setMinimumWidth(self.calculate_button_width(text))
        elif icon and (width is None or height is None):
            # If only icon is present and width or height is not specified
            self.setFixedSize(icon_size, icon_size)
        
        # Set custom width and height if provided
        if width is not None:
            self.setFixedWidth(width)
        if height is not None:
            self.setFixedHeight(height)
        
        if icon and text:
            # Set icon to the left of the text
            self.setLayoutDirection(QtCore.Qt.LeftToRight)
        
        self.setToolTip(f"<html><body><p style='color:white; white-space:nowrap; '>{tooltip}</p></body></html>")

    def calculate_button_width(self, text, padding=20):
        font_metrics = QtGui.QFontMetrics(QtWidgets.QApplication.font())
        text_width = font_metrics.horizontalAdvance(text)
        return text_width + padding
    
class CustomFrame(QtWidgets.QFrame):
    def __init__(self, 
                    height=None, 
                    style="QFrame { border: 0px solid gray; border-radius: 3px; background-color: #1f1f1f; }", 
                    layout_type='horizontal', 
                    margin = 4,
                    parent=None):
        super().__init__(parent)
        
        self.setStyleSheet(style)
        if height is not None:
            self.setFixedHeight(height) 
        
        if layout_type.lower() == 'horizontal':
            self.layout = QtWidgets.QHBoxLayout(self)
        elif layout_type.lower() == 'vertical':
            self.layout = QtWidgets.QVBoxLayout(self)
        else:
            raise ValueError("Invalid layout_type. Use 'horizontal' or 'vertical'.")
        
        self.layout.setAlignment(QtCore.Qt.AlignLeft)
        self.layout.setSpacing(margin + 4)

        if layout_type == 'horizontal':
            self.layout.setContentsMargins(margin, margin, margin, margin)
        
        if layout_type == 'vertical':
            self.layout.setContentsMargins(margin, margin, margin, margin)   

class ToggleButton(QtWidgets.QPushButton):
    toggled_with_id = QtCore.Signal(bool, int)  # Custom signal
    #toggled= QtCore.Signal(bool)  # Custom signal

    def __init__(self, text, button_id, bg_color = '#5285A6',tooltip = '', border_radius = 10, parent=None):
        super(ToggleButton, self).__init__(text, parent)
        self.button_id = button_id
        self.setCheckable(True)
        self.setFixedSize(20, 20)
        self.toggled.connect(self.on_toggle)
        self.setText(text)
        #bg_color = 808080 87CEFA
        self.setStyleSheet(f'''
            QPushButton {{background-color: rgba(40, 40, 40, .3);border: none; color: rgba(250, 250, 250, .6); padding: 2px;text-align: center; border-radius: {border_radius};}}
            QPushButton:hover {{background-color: rgba(20, 20, 20, .3);}}
            QPushButton:checked {{background-color: {bg_color};}}
            QToolTip {{background-color: {bg_color};color: white; border:0px;}}''')
        self.setToolTip(f"<html><body><p>{tooltip}</p></body></html>")
        

    def on_toggle(self, checked):
        self.toggled_with_id.emit(checked, self.button_id)

class FloatingTools(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(FloatingTools, self).__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setWindowTitle("Floating Tools")
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setStyleSheet('QWidget {background-color: rgba(0, 0, 0, 0);}')
        #self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout_col = QtWidgets.QHBoxLayout()
        self.mainLayout.addLayout(self.mainLayout_col)
        self.mainLayout_col.setAlignment(QtCore.Qt.AlignRight)

        frameColSpacer = QtWidgets.QHBoxLayout()

        self.frame_col = QtWidgets.QVBoxLayout()
        self.frame_col.setAlignment(QtCore.Qt.AlignCenter)

        frameColSpacer.addStretch()
        frameColSpacer.addLayout(self.frame_col)
        self.mainLayout_col.addLayout(frameColSpacer)

        self.is_minimized = False
        self.setup_ui()  

        # Set initial opacity
        self.setWindowOpacity(1)
        
        # Create timer and animation
        self.fade_timer = QTimer(self)
        self.fade_timer.setSingleShot(True)
        self.fade_timer.timeout.connect(self.start_fade_animation)
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(1000)  # 500 ms for fade effect
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Set up right-click menu for the frame
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_frame_context_menu)
        self.fade_away_enabled = False

    #---------------------------------------------------------------------------------------------------------------
    def setup_ui(self):
        frameWidth = 280

        def frameStyleSheet(frame):
            frame.setStyleSheet(f'''QFrame {{ border: 0px solid gray; border-radius: 5px; background-color: rgba(40, 40, 40, .6); }}''')

        def mrs(col):
            reset_move_button = CustomButton(text='Move', icon=':delete.png', color='#262626', size=16, tooltip="Resets the moved object values to Origin.")
            reset_rotate_button = CustomButton(text='Rotate', icon=':delete.png', color='#262626', size=16, tooltip="Resets the rotated object values to Origin.")
            reset_scale_button = CustomButton(text='Scale', icon=':delete.png', color='#262626', size=16, tooltip="Resets the scaled object values to Origin.")
            reset_all_button = CustomButton(text='Reset All', color='#CF2222', tooltip="Resets all the object transform to Origin.")
            reset_move_button.singleClicked.connect(self.reset_move)
            reset_rotate_button.singleClicked.connect(self.reset_rotate)
            reset_scale_button.singleClicked.connect(self.reset_scale)
            reset_all_button.singleClicked.connect(self.reset_all)
            col.addWidget(reset_move_button)
            col.addWidget(reset_rotate_button)
            col.addWidget(reset_scale_button)
            col.addWidget(reset_all_button)

        #==========================================================================================================================================
        fs = 7
        self.menu_frame_1 = QtWidgets.QFrame()
        self.menu_frame_1.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.menu_frame_1.setFixedWidth(frameWidth)
        frameStyleSheet(self.menu_frame_1)
        menu_frame_layout_1 = QtWidgets.QVBoxLayout(self.menu_frame_1)
        menu_frame_layout_1.setContentsMargins(fs, fs, fs, fs)
        menu_frame_layout_1.setSpacing(7)
        self.frame_col.addWidget(self.menu_frame_1)

        frame1_col1 = QtWidgets.QHBoxLayout()
        frame1_col1.setSpacing(7)
        frame1_col2 = QtWidgets.QHBoxLayout()
        frame1_col2.setSpacing(7)
        frame1_col3_frame = QtWidgets.QFrame()
        frame1_col3_frame.setStyleSheet(f'''QFrame {{ border: 0px solid gray; border-radius: 5px; background-color: rgba(30, 30, 30, .75); }}''')
        frame1_col3 = QtWidgets.QHBoxLayout(frame1_col3_frame)
        frame1_col3.setContentsMargins(7, 7, 7, 7)
        #frame1_col3.setSpacing(4)

        mrs(frame1_col1)

        store_pos_button = CustomButton(text='Store Pos', color='#16AAA6', tooltip="Store Position: Stores the position of selected Vertices, Edges or Faces. Double Click to make locator visible")
        move_to_pos_button = CustomButton(text='Move to Pos', color='#D58C09', tooltip="Move to Position: Move selected object(s) to the stored position.")
        parent_constraint_button = CustomButton(icon=':parentConstraint.png', color='transparent', tooltip="Constraint active object to selected object.")
        centerPivot_button = CustomButton(icon=':CenterPivot.png', color='transparent', tooltip="Resets the selected object(s) pivot to the center.")
        deleteHistory_button = CustomButton(icon=':DeleteHistory.png', color='transparent', tooltip="Delete construction history on selected object(s).")
        freezeTransform_button = CustomButton(icon=':FreezeTransform.png', color='transparent', tooltip="Changes curent transform values to base transform values.")
        object_to_world_button = CustomButton(icon=':absolute.png', color='#4d4d4d', size=22, tooltip="Object to world Origin: Moves object to world origin.")
        active_to_selected_button = CustomButton(icon=':absolute.png', color='#C41B16', size=22, tooltip="Snap to Active Object: Moves selected object(s) to Active Objects Position.")
        pivot_to_world_button = CustomButton(icon=':absolute.png', color='#049E9F', size=22, tooltip="Pivot to Stored Position: Moves the object(s) Stored Position.")
        pivot_to_selected_button = CustomButton(icon=':absolute.png', color='#6C9809', size=22, tooltip="Selected Pivot to Active Pivot: Moves the pivot of selected object(s) to the pivot of active objects(s).")
        adj_grp_tt = '<b>Create Adjustment Group:</b> <br> Single Click: Create offset group for selected objects. <br> Double Click: Select the control object and the joint object to create the adjustment group.'
        self.adjustment_grp_button = CustomButton(text='GRP', color='#133266', tooltip=adj_grp_tt)
        self.adjustment_grp_button.setFixedWidth(35)

        store_pos_button.singleClicked.connect(self.store_component_position)
        store_pos_button.doubleClicked.connect(self.store_component_position_vis)
        move_to_pos_button.singleClicked.connect(self.move_objects_to_stored_position)
        parent_constraint_button.singleClicked.connect(self.parent_constraint)
        parent_constraint_button.doubleClicked.connect(self.parent_constraint_options)
        centerPivot_button.singleClicked.connect(self.center_pivot)
        deleteHistory_button.singleClicked.connect(self.delete_history)
        freezeTransform_button.singleClicked.connect(self.freeze_transformation)
        object_to_world_button.singleClicked.connect(self.object_to_world_origin)
        active_to_selected_button.singleClicked.connect(self.object_to_active_position)
        pivot_to_world_button.singleClicked.connect(self.pivot_to_world_origin)
        pivot_to_selected_button.singleClicked.connect(self.selected_pivot_to_active_pivot)
        self.adjustment_grp_button.singleClicked.connect(self.create_adjustment_group)
        self.adjustment_grp_button.doubleClicked.connect(self.create_adjustment_group_move)

        frame1_col2.addWidget(store_pos_button)
        frame1_col2.addWidget(move_to_pos_button)
        frame1_col2.addWidget(parent_constraint_button)
        frame1_col2.addWidget(self.adjustment_grp_button)
        frame1_col3.addWidget(centerPivot_button)
        frame1_col3.addWidget(deleteHistory_button)
        frame1_col3.addWidget(freezeTransform_button)
        frame1_col3.addWidget(object_to_world_button)
        frame1_col3.addWidget(active_to_selected_button)
        frame1_col3.addWidget(pivot_to_world_button)
        frame1_col3.addWidget(pivot_to_selected_button)

        menu_frame_layout_1.addLayout(frame1_col1)
        menu_frame_layout_1.addLayout(frame1_col2)
        menu_frame_layout_1.addWidget(frame1_col3_frame)

        self.frame1_label = QtWidgets.QLabel('Modeling Tools')
        self.frame1_label.setStyleSheet(f'''QLabel {{ color:rgba(160, 160, 160, .5) }}''')
        
        frame1_base_col = QtWidgets.QHBoxLayout()
        self.moreTools1 = ToggleButton("More", 11, tooltip='Show More Tools', border_radius=3, bg_color='rgba(40, 40, 40, .3)')
        self.moreTools1.setFixedSize(50, 20)
        self.moreTools1.setChecked(False)
        self.moreTools1.toggled.connect(self.update_frame_visibility)
        frame1_base_col.addWidget(self.frame1_label)
        frame1_base_col.addStretch()
        frame1_base_col.addWidget(self.moreTools1)
        self.frame_col.addLayout(frame1_base_col)

        #==========================================================================================================================================
        self.match_frame = QtWidgets.QFrame()
        self.match_frame.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.match_frame.setFixedWidth(frameWidth)
        frameStyleSheet(self.match_frame)
        match_frame_layout = QtWidgets.QVBoxLayout(self.match_frame)
        match_frame_layout.setContentsMargins(7,7,7,7)
        
        self.frame_col.addWidget(self.match_frame)

        match_frameCol_1 = QtWidgets.QHBoxLayout()
        match_frameCol_1.setSpacing(7)

        def matchTransform(col):
            match_move_button = CustomButton(text='Move', icon=':ghostingObjectTypeLocator.png', color='#262626', size=16, tooltip="Match Transforms.")
            match_rotate_button = CustomButton(text='Rotate', icon=':ghostingObjectTypeLocator.png', color='#262626', size=16, tooltip="Match Rotation.")
            match_scale_button = CustomButton(text='Scale', icon=':ghostingObjectTypeLocator.png', color='#262626', size=16, tooltip="Match Scaling.")
            match_all_button = CustomButton(text='Match All', color='#CF2222', tooltip="Match All Transforms.")
            match_move_button.singleClicked.connect(self.match_move)
            match_rotate_button.singleClicked.connect(self.match_rotate)
            match_scale_button.singleClicked.connect(self.match_scale)
            match_all_button.singleClicked.connect(self.match_all)
            col.addWidget(match_move_button)
            col.addWidget(match_rotate_button)
            col.addWidget(match_scale_button)
            col.addWidget(match_all_button)

        matchTransform(match_frameCol_1)
        match_frame_layout.addLayout(match_frameCol_1)
        

        #==========================================================================================================================================
        cm = 3
        self.orientFrame = CustomFrame(style=f'''QFrame {{ border: 0px solid gray; border-radius: 5px; background-color: rgba(40, 40, 40, .5); }}''', height=None, margin=2)
        frameStyleSheet(self.orientFrame)
        self.orientFrame.setFixedWidth(frameWidth)
        self.orientFrame_layout = QtWidgets.QHBoxLayout(self.orientFrame)
        self.orientFrame_layout.setContentsMargins(cm, cm, cm, cm)
        self.orientFrame_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.orientFrame.layout.addLayout(self.orientFrame_layout)
        self.frame_col.addWidget(self.orientFrame)

        self.increment_label = QtWidgets.QLabel("Set Increment:")
        self.increment_input = QtWidgets.QLineEdit("90")
        self.increment_input.setValidator(QtGui.QDoubleValidator())
        increment_input_col = '#333333'
        self.increment_input.setStyleSheet(f'''QLineEdit{{background-color: {increment_input_col}; color: white;}} QComboBox:hover {{background-color: {hex_value(increment_input_col, .8)};}} QToolTip {{background-color: {increment_input_col}; color: white; border:0px;}} ''')
        self.increment_input.setFixedHeight(30)
        self.increment_input.setToolTip(f"Type Rotation Increment Factor")

        XFrame = CustomFrame(style="QFrame { border: 0px solid gray; border-radius: 5px; background-color: #262626; }", margin=5)
        XFrame.layout.setSpacing(6)
        YFrame = CustomFrame(style="QFrame { border: 0px solid gray; border-radius: 5px; background-color: #262626; }", margin=5)
        YFrame.layout.setSpacing(6)
        ZFrame = CustomFrame(style="QFrame { border: 0px solid gray; border-radius: 5px; background-color: #262626; }", margin=5)
        ZFrame.layout.setSpacing(6)

        bs = 20
        self.r_pos_X_button = CustomButton(text='+', color='#4d4d4d', height=bs, width=bs, tooltip="Rotate in +X Orientation by factor .")
        self.r_neg_X_button = CustomButton(text='-', color='#4d4d4d', height=bs, width=bs, tooltip="Rotate in -X Orientation by factor .")
        self.r_pos_Y_button = CustomButton(text='+', color='#4d4d4d', height=bs, width=bs, tooltip="Rotate in +Y Orientation by factor .")
        self.r_neg_Y_button = CustomButton(text='-', color='#4d4d4d', height=bs, width=bs, tooltip="Rotate in -Y Orientation by factor .")
        self.r_pos_Z_button = CustomButton(text='+', color='#4d4d4d', height=bs, width=bs, tooltip="Rotate in +Z Orientation by factor .")
        self.r_neg_Z_button = CustomButton(text='-', color='#4d4d4d', height=bs, width=bs, tooltip="Rotate in -Z Orientation by factor .")

        XFrame.layout.addWidget(QtWidgets.QLabel("X"))
        XFrame.layout.addWidget(self.r_pos_X_button)
        XFrame.layout.addWidget(self.r_neg_X_button)
        YFrame.layout.addWidget(QtWidgets.QLabel("Y"))
        YFrame.layout.addWidget(self.r_pos_Y_button)
        YFrame.layout.addWidget(self.r_neg_Y_button)
        ZFrame.layout.addWidget(QtWidgets.QLabel("Z"))
        ZFrame.layout.addWidget(self.r_pos_Z_button)
        ZFrame.layout.addWidget(self.r_neg_Z_button)

        self.r_pos_X_button.clicked.connect(lambda: self.rotate_object(1, 0, 0))
        self.r_neg_X_button.clicked.connect(lambda: self.rotate_object(-1, 0, 0))
        self.r_pos_Y_button.clicked.connect(lambda: self.rotate_object(0, 1, 0))
        self.r_neg_Y_button.clicked.connect(lambda: self.rotate_object(0, -1, 0))
        self.r_pos_Z_button.clicked.connect(lambda: self.rotate_object(0, 0, 1))
        self.r_neg_Z_button.clicked.connect(lambda: self.rotate_object(0, 0, -1))

        self.orientFrame_layout.addWidget(self.increment_input)
        self.orientFrame_layout.addWidget(XFrame)
        self.orientFrame_layout.addWidget(YFrame)
        self.orientFrame_layout.addWidget(ZFrame)
        #==========================================================================================================================================
        self.shapeFrame = QtWidgets.QFrame()
        self.shapeFrame.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.shapeFrame.setFixedWidth(frameWidth)
        
        frameStyleSheet(self.shapeFrame)
        shapeFrame_layout = QtWidgets.QVBoxLayout(self.shapeFrame)
        shapeFrame_layout.setAlignment(QtCore.Qt.AlignLeft)
        shapeFrame_layout.setContentsMargins(7,7,7,7)
        self.frame_col.addWidget(self.shapeFrame)

        shapeFrameCol_1 = QtWidgets.QHBoxLayout()
        shapeFrameCol_1.setSpacing(7)

        def shapeFrame(col):
            circle_shape_button = CustomButton(text='⬤', width = None, color='#202C39', tooltip="Circle Shape")
            square_shape_button = CustomButton(text='◻', width = None, color='#283845', tooltip="SquareShape")
            box_shape_button = CustomButton(text='🎲', width = None, color='#596762', tooltip="Cube Shape")
            triangle_shape_button = CustomButton(text='▲', width = None, color='#544E61', tooltip="Triangle Shape")
            pyramid_shape_button = CustomButton(text='🗼', width = None, color='#867558', tooltip="Pyramid Shape")
            arrow_shape_button = CustomButton(text='⬆', width = None, color='#205d8b', tooltip="Arrow Shape")
            cycle_shape_button = CustomButton(text='↻', width = None, color='#783F8E', tooltip="Cycle Shape")

            circle_shape_button.singleClicked.connect(self.circle_sc)
            square_shape_button.singleClicked.connect(self.square_sc)
            box_shape_button.singleClicked.connect(self.cube_sc)
            triangle_shape_button.singleClicked.connect(self.triangle_sc)
            pyramid_shape_button.singleClicked.connect(self.pyramid_sc)
            arrow_shape_button.singleClicked.connect(self.arrow_sc)
            cycle_shape_button.singleClicked.connect(self.cycle_sc)

            col.addWidget(circle_shape_button)
            col.addWidget(square_shape_button)
            col.addWidget(box_shape_button)
            col.addWidget(triangle_shape_button)
            col.addWidget(pyramid_shape_button)
            col.addWidget(arrow_shape_button)
            col.addWidget(cycle_shape_button)

        shapeFrame(shapeFrameCol_1)
        shapeFrame_layout.addLayout(shapeFrameCol_1)
        #==========================================================================================================================================
        self.menu_frame_2 = QtWidgets.QFrame()
        self.menu_frame_2.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.menu_frame_2.setFixedWidth(frameWidth)
        frameStyleSheet(self.menu_frame_2)
        menu_frame_layout_2 = QtWidgets.QVBoxLayout(self.menu_frame_2)
        menu_frame_layout_2.setContentsMargins(fs, fs, fs, fs)
        menu_frame_layout_2.setSpacing(7)
        self.frame_col.addWidget(self.menu_frame_2)
        frame2_col1 = QtWidgets.QHBoxLayout()
        frame2_col1.setSpacing(7)
        frame2_col2 = QtWidgets.QHBoxLayout()
        frame2_col2.setSpacing(7)
        frame2_col3 = QtWidgets.QHBoxLayout()
        frame2_col3.setSpacing(7)
        frame2_col4 = QtWidgets.QHBoxLayout()
        frame2_col4.setSpacing(7)
        frame2_col2_frame = QtWidgets.QFrame()
        frame2_col2_frame.setStyleSheet(f'''QFrame {{ border: 0px solid gray; border-radius: 5px; background-color: rgba(30, 30, 30, .75); }}''')
        frame2_col2_col = QtWidgets.QVBoxLayout(frame2_col2_frame)
        
        
        frame2_col2_col.setContentsMargins(7, 7, 7, 7)
        frame2_col2_col.setSpacing(7)
        
        mrs(frame2_col1)

        buttons = [
            CustomButton(text='Key', color='#d62e22', tooltip="Sets key frame."),
            CustomButton(text='Key', color='#3fb07f', tooltip="Sets breakdown frame."),
            CustomButton(text='Mute all', color='#8c805a', tooltip="Mutes all the animation of selected objects."),
            CustomButton(text='Unmute all', color='#696969', tooltip="Unmutes all the animation of selected objects."),
            CustomButton(text='Copy', color='#293F64', tooltip="Copy selected key(s)."),
            CustomButton(text='Paste', color='#1699CA', tooltip="Paste copied key(s)."),
            CustomButton(text='Paste Inverse', color='#9416CA', tooltip="Paste Inverted copied keys(s)."),
            CustomButton(text='<', color='#7B945D', width=22, tooltip="Remove Inbetween at current time."),
            CustomButton(text='>', color='#7B945D', width=22, tooltip="Add Inbetween at current time."),
            CustomButton(text='Delete Key', color='#A00000', size=16, tooltip="Deletes keys from the given start frame to the current frame."),
        ]

        for button in buttons[:4]:
            frame2_col2.addWidget(button)
        for button in buttons[4:7]:
            frame2_col3.addWidget(button)
        for button in buttons[7:]:
            frame2_col4.addWidget(button)

        buttons[0].singleClicked.connect(self.set_key)
        buttons[1].singleClicked.connect(self.set_breakdown)
        buttons[2].singleClicked.connect(self.mute_all)
        buttons[3].singleClicked.connect(self.unMute_all)
        buttons[4].singleClicked.connect(self.copy_keys)
        buttons[5].singleClicked.connect(self.paste_keys)
        buttons[6].singleClicked.connect(self.paste_inverse)
        buttons[7].singleClicked.connect(self.remove_inbetweens)
        buttons[8].singleClicked.connect(self.add_inbetweens)
        buttons[9].singleClicked.connect(self.delete_keys)

        menu_frame_layout_2.addLayout(frame2_col1)
        frame2_col2_col.addLayout(frame2_col2)
        frame2_col2_col.addLayout(frame2_col3)
        frame2_col2_col.addLayout(frame2_col4)
        menu_frame_layout_2.addWidget(frame2_col2_frame)

        self.frame2_label = QtWidgets.QLabel('Timeline Tools')
        self.frame2_label.setStyleSheet(f'''QLabel {{ color:rgba(160, 160, 160, .5) }}''')
        self.frame_col.addWidget(self.frame2_label)        
        #==========================================================================================================================================
        mf3Spacer = QtWidgets.QHBoxLayout()
        self.menu_frame_3 = QtWidgets.QFrame()
        self.menu_frame_3.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.menu_frame_3.setFixedWidth(250)
        frameStyleSheet(self.menu_frame_3)

        menu_frame_layout_3 = QtWidgets.QVBoxLayout(self.menu_frame_3)
        menu_frame_layout_3.setContentsMargins(5,5,5,5)

        mf3Spacer.addStretch()
        mf3Spacer.addWidget(self.menu_frame_3)
        self.frame_col.addLayout(mf3Spacer)

        frame3_col1 = QtWidgets.QHBoxLayout()
        frame3_col1.setSpacing(7)
        frame3_col2 = QtWidgets.QHBoxLayout()
        frame3_col2.setSpacing(7)
        frame3_col3 = QtWidgets.QHBoxLayout()
        frame3_col3.setSpacing(7)
        frame3_col4 = QtWidgets.QHBoxLayout()
        frame3_col4.setSpacing(7)
        frame3_col2_frame = QtWidgets.QFrame()
        frame3_col2_frame.setStyleSheet(f'''QFrame {{ border: 0px solid gray; border-radius: 5px; background-color: rgba(30, 30, 30, .6); }}''')
        frame3_col2_col = QtWidgets.QVBoxLayout(frame3_col2_frame)
        fs = 7
        frame3_col2_col.setSpacing(fs)
        frame3_col2_col.setContentsMargins(fs,fs,fs,fs)

        #mrs(frame3_col1)

        buttons = [
            CustomButton(text='Key', color='#d62e22', tooltip="Sets key frame."),
            CustomButton(text='Key', color='#0E8E9A', tooltip="Insert Key Inserts a key on the visible curves in the graph editor."),
            CustomButton(text='Copy', color='#293F64', tooltip="Copy Keys:This copies the selected key(s)."),
            CustomButton(text='Paste', color='#1699CA', tooltip="Paste Keys:This pastes the copied key(s)."),
            CustomButton(text='Paste Selected', color='#5DA380', tooltip="Pastes the selected keys to the current frame in the graph editor."),
            CustomButton(text='Invert', color='#965D94', tooltip="Inverts the selected keys in the graph editor."),
            CustomButton(text='Zero Out', color='#AF8E4F', tooltip="Sets the selected keys to zero in the graph editor."),
            CustomButton(text='Delete Key', color='#A00000', size=16, tooltip="Deletes selected keys."),
        ]

        for button in buttons[:4]:
            frame3_col2.addWidget(button)
        for button in buttons[4:6]:
            frame3_col3.addWidget(button)
        for button in buttons[6:]:
            frame3_col4.addWidget(button)

        buttons[0].singleClicked.connect(self.set_graph_key)
        buttons[1].singleClicked.connect(self.insert_key)
        buttons[2].singleClicked.connect(self.copy_graph_key)
        buttons[3].singleClicked.connect(self.paste_graph_key)
        buttons[4].singleClicked.connect(self.copy_and_paste_selected_keys)
        buttons[5].singleClicked.connect(self.invert_keys)
        buttons[6].singleClicked.connect(self.zero_out)
        buttons[7].singleClicked.connect(self.delete_keys_graphEditor)

        menu_frame_layout_3.addLayout(frame3_col1)
        frame3_col2_col.addLayout(frame3_col2)
        frame3_col2_col.addLayout(frame3_col3)
        frame3_col2_col.addLayout(frame3_col4)
        menu_frame_layout_3.addWidget(frame3_col2_frame)

        self.frame3_label = QtWidgets.QLabel('Graph Editor Tools')
        self.frame3_label.setStyleSheet(f'''QLabel {{ color:rgba(160, 160, 160, .5) }}''')
        self.frame_col.addWidget(self.frame3_label)

        #==========================================================================================================================================
        self.toggle_col = QtWidgets.QVBoxLayout()
        self.toggle_col.setAlignment(QtCore.Qt.AlignTop)
        self.toggle_col.setSpacing(4)
        self.mainLayout_col.addLayout(self.toggle_col)

        self.toggle_col.addSpacing(5)
        self.toggle_minimize_button = CustomButton(icon=":eye.png", size=20, color='rgba(50, 50, 50,.5)', tooltip="Maximize/Minimize", radius=10)
        self.toggle_minimize_button.clicked.connect(self.toggle_minimize)
        self.toggle_col.addWidget(self.toggle_minimize_button)

        self.toggle_col.addSpacing(10)
        self.toggle_button_1 = ToggleButton("1", 1, tooltip='Modeling Tools')
        self.toggle_button_1.setChecked(True)
        self.toggle_button_2 = ToggleButton("2", 2, tooltip='Time Line Tools')
        self.toggle_button_3 = ToggleButton("3", 3, tooltip='Graph Editor Tools')

        self.toggle_button_1.toggled_with_id.connect(self.update_toggle)
        self.toggle_button_2.toggled_with_id.connect(self.update_toggle)
        self.toggle_button_3.toggled_with_id.connect(self.update_toggle)

        self.toggle_col.addWidget(self.toggle_button_1)
        self.toggle_col.addWidget(self.toggle_button_2)
        self.toggle_col.addWidget(self.toggle_button_3)
        #==========================================================================================================================================
        minimized_col = QtWidgets.QHBoxLayout()

        self.minimized_frame = QtWidgets.QFrame()
        self.minimized_frame.setFixedWidth(100)
        self.minimized_frame.setStyleSheet('QFrame { border: 0px solid gray; border-radius: 5px; background-color: rgba(20, 20, 20, .4); }')
        minimized_layout = QtWidgets.QHBoxLayout(self.minimized_frame)
        self.minimized_label = QtWidgets.QLabel("Floating tools")
        self.minimized_label.setStyleSheet('QLabel { color: rgba(222, 222, 222, .5); background-color: transparent;font-weight: bold;}')
        minimized_layout.addWidget(self.minimized_label)
        #minimized_layout.addWidget(self.toggle_minimize_button)
        
        minimized_col.addStretch()
        minimized_col.addWidget(self.minimized_frame)
        self.frame_col.addLayout(minimized_col)
        self.minimized_frame.hide()


        self.frame_col.addStretch()
        self.update_frame_visibility()

        # Install event filter
        self.installEventFilter(self)
    
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    
    def toggle_minimize(self):
        self.is_minimized = not self.is_minimized
        self.update_frame_visibility()

    def update_frame_visibility(self):
        if self.is_minimized:
            self.menu_frame_1.hide()
            self.match_frame.hide()
            self.orientFrame.hide()
            self.shapeFrame.hide()
            self.menu_frame_2.hide()
            self.menu_frame_3.hide()
            self.toggle_button_1.hide()
            self.toggle_button_2.hide()
            self.toggle_button_3.hide()
            self.minimized_frame.show()

            self.moreTools1.hide()
            self.frame1_label.hide()
            self.frame2_label.hide()
            self.frame3_label.hide()
        else:
            self.menu_frame_1.setVisible(self.toggle_button_1.isChecked())
            self.moreTools1.setText("More" if self.moreTools1.isChecked() == False else "Less")
            self.moreTools1.setToolTip("Show More Tools" if self.moreTools1.isChecked() == False else "Show Less Tools")
            #self.adjustment_grp_button.setVisible(self.toggle_button_1.isChecked() and self.moreTools1.isChecked())
            self.match_frame.setVisible(self.toggle_button_1.isChecked() and self.moreTools1.isChecked())
            self.orientFrame.setVisible(self.toggle_button_1.isChecked() and self.moreTools1.isChecked())
            self.shapeFrame.setVisible(self.toggle_button_1.isChecked() and self.moreTools1.isChecked())
            
            #self.moreTools1.show()
            self.frame1_label.setVisible(self.toggle_button_1.isChecked())
            self.moreTools1.setVisible(self.toggle_button_1.isChecked())

            self.menu_frame_2.setVisible(self.toggle_button_2.isChecked())
            self.frame2_label.setVisible(self.toggle_button_2.isChecked())

            self.menu_frame_3.setVisible(self.toggle_button_3.isChecked())
            self.frame3_label.setVisible(self.toggle_button_3.isChecked())

            self.toggle_button_1.show()
            self.toggle_button_2.show()
            self.toggle_button_3.show()
            self.minimized_frame.hide()
        #maya_main_window().activateWindow()
    
    def update_toggle(self, checked, button_id):
        if checked:
            self.toggle_button_1.setChecked(button_id == 1)
            self.toggle_button_2.setChecked(button_id == 2)
            self.toggle_button_3.setChecked(button_id == 3)
            self.update_frame_visibility()
    
    def show_frame_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        # Remove background and shadow
        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        menu.setStyleSheet('''
            QMenu {
                background-color: rgba(51, 51, 51, 0);
                border-radius: 3px;
                padding: 5px;
            }
            QMenu::item {
                background-color: #222222;
                padding: 6px;
                border: 2px solid #00749a;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #111111;
            }
        ''')
        toggle_fade_action = menu.addAction("Toggle Fade Away")
        toggle_fade_action.setCheckable(True)
        toggle_fade_action.setChecked(self.fade_away_enabled)
        
        action = menu.exec_(self.mapToGlobal(pos))
        if action == toggle_fade_action:
            self.toggle_fade_away()

    def toggle_fade_away(self):
        self.fade_away_enabled = not self.fade_away_enabled
        if not self.fade_away_enabled:
            self.fade_timer.stop()
            self.fade_animation.stop()
            self.setWindowOpacity(1.0)
 
    #---------------------------------------------------------------------------------------------------------------
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.WindowActivate:
            # Prevent the widget from taking focus
            maya_main_window().activateWindow()
            return True
        return super(FloatingTools, self).eventFilter(obj, event)
    
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def enterEvent(self, event):
        if self.fade_away_enabled:
            self.fade_timer.stop()
            self.fade_animation.stop()
            self.fade_animation.setDuration(100)  # 100ms for fade in
            self.fade_animation.setStartValue(self.windowOpacity())
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.start()
        super(FloatingTools, self).enterEvent(event)

    def leaveEvent(self, event):
        if self.fade_away_enabled:
            self.fade_timer.start(1000)  # 1000ms delay before fade out
        super(FloatingTools, self).leaveEvent(event)

    def start_fade_animation(self):
        if self.fade_away_enabled:
            self.fade_animation.setDuration(1000)  # 1000ms for fade out
            self.fade_animation.setStartValue(self.windowOpacity())
            self.fade_animation.setEndValue(0.2)
            self.fade_animation.start()
    #---------------------------------------------------------------------------------------------------------------
    def circle_sc(self):
        #create_curve('circle',circle_18_shape)
        cmds.circle(c=(0, 0, 0), nr=(0, 1, 0), sw=360, r=1, d=3, ut=0, tol=0.0001, s=8, ch=1)[0]
    def square_sc(self):
        create_curve('square',square_shape)
    def cube_sc(self):
        create_curve('box',cube_shape)
    def triangle_sc(self):
        create_curve('triangle',triangle_shape)
    def pyramid_sc(self):
        create_curve('pyramid',pyramid_shape)
    def arrow_sc(self):
        create_curve('arrow',arrow_shape)
    def cycle_sc(self):
        create_curve('cycle',cycle_shape)
    #----------------------------------------------------------------------------------------------------------------
    def rotate_object(self, x, y, z):
        increment = float(self.increment_input.text())
        selected_objects = cmds.ls(selection=True)
        if not selected_objects:
            cmds.warning("No objects selected.")
            return

        for obj in selected_objects:
            cmds.rotate(x * increment, y * increment, z * increment, obj, relative=True, objectSpace=True)

    def center_pivot(self):
        mel.eval('''CenterPivot;''')
        
    def delete_history(self):
        mel.eval('''DeleteHistory;''')
    
    def freeze_transformation(self):
        mel.eval('''
                    FreezeTransformations;
                    makeIdentity -apply true -t 1 -r 1 -s 1 -n 0 -pn 1;
                 ''')
    
    def object_to_world_origin(self):
        mel.eval('''
                    string $obj[] = `ls -sl`;
                    move -rpr 0 0 0 $obj;
                 ''')
    
    def pivot_to_world_origin(self):
        selected_objects = cmds.ls(selection=True, long=True)
        if not cmds.objExists('storedPositionLocator'):
            create_loc_object('storedPositionLocator')
            #cmds.spaceLocator(name='storedPositionLocator')
            cmds.setAttr('storedPositionLocator.visibility', 0)

        source_pivot = cmds.xform('storedPositionLocator', q=True, ws=True, rp=True)

        for obj in selected_objects:
            cmds.xform(obj, ws=True, piv=source_pivot)
        cmds.select(selected_objects)
        #cmds.xform(ws=True, piv=(0, 0, 0))
        #mel.eval('''xform -ws -piv 0 0 0;''')
    
    def selected_pivot_to_active_pivot(self):
        # Get the selected objects
        selected_objects = cmds.ls(selection=True)

        # Check if there are at least two objects selected
        if len(selected_objects) > 1:
            # Get the last selected object (active object)
            active_object = selected_objects[-1]
            
            # Get the pivot position of the active object
            pivot_position = cmds.xform(active_object, query=True, worldSpace=True, rotatePivot=True)
            
            # Loop through the other selected objects and set their pivots to the active object's pivot
            for obj in selected_objects[:-1]:
                cmds.xform(obj, worldSpace=True, pivots=pivot_position)
            cmds.select(selected_objects[:-1], replace=True)
        else:
            cmds.warning("Please select at least two objects.")

    @undoable
    def object_to_active_position(self):
        selected_objects = cmds.ls(selection=True, long=True)

        if len(selected_objects) > 1:
            active_object = selected_objects[-1]
            
            # Get the position of the active object
            active_position = cmds.xform(active_object, query=True, worldSpace=True, rotatePivot=True)
            
            # Loop through the other selected objects and set their positions to the active object's position
            for obj in selected_objects[:-1]:
                if obj != active_object:
                    # Get the current world space rotate pivot of the object
                    current_position = cmds.xform(obj, query=True, worldSpace=True, rotatePivot=True)
                    
                    # Calculate the difference between the stored position and current position
                    offset = [active_position[i] - current_position[i] for i in range(3)]
                    
                    # Move the object by the calculated offset
                    cmds.move(offset[0], offset[1], offset[2], obj, relative=True, worldSpace=True)

            cmds.select(selected_objects[:-1], replace=True)
        else:
            cmds.warning("Please select at least two objects.")
 
    @undoable
    def store_component_position(self):
        # Get the active selection
        selection = om.MGlobal.getActiveSelectionList()
        
        if selection.isEmpty():
            if cmds.objExists('storedPositionLocator'):
                cmds.move(0, 0, 0, 'storedPositionLocator', absolute=True, worldSpace=True)
                cmds.setAttr('storedPositionLocator.visibility', 0)
                return
            else:
                cmds.warning("Nothing selected. Please select an object or components.")
                return

        # Get the manipulator position
        manipulator_pos = None
        if cmds.currentCtx() == 'moveSuperContext':
            manipulator_pos = cmds.manipMoveContext('Move', q=True, position=True)
        elif cmds.currentCtx() == 'RotateSuperContext':
            manipulator_pos = cmds.manipRotateContext('Rotate', q=True, position=True)
        elif cmds.currentCtx() == 'scaleSuperContext':
            manipulator_pos = cmds.manipScaleContext('Scale', q=True, position=True)

        if not manipulator_pos:
            cmds.warning("Unable to get manipulator position. Ensure you're in move tool mode.")
            return

        # Store the position in a custom attribute on the scene
        if not cmds.objExists('storedPositionLocator'):
            create_loc_object('storedPositionLocator')
            #cmds.spaceLocator(name='storedPositionLocator')
            cmds.setAttr('storedPositionLocator.visibility', 0)

        cmds.xform('storedPositionLocator', translation=manipulator_pos, worldSpace=True)
        cmds.setAttr('storedPositionLocator.visibility', 0)
        print("Manipulator position stored:", manipulator_pos)

    @undoable
    def store_component_position_vis(self):
        # Get the active selection
        selection = om.MGlobal.getActiveSelectionList()
        
        if selection.isEmpty():
            if cmds.objExists('storedPositionLocator'):
                cmds.move(0, 0, 0, 'storedPositionLocator', absolute=True, worldSpace=True)
                cmds.setAttr('storedPositionLocator.visibility', 1)
                return
            else:
                cmds.warning("Nothing selected. Please select an object or components.")
                return

        # Get the manipulator position
        
        manipulator_pos = None
        if cmds.currentCtx() == 'moveSuperContext':
            manipulator_pos = cmds.manipMoveContext('Move', q=True, position=True)
        elif cmds.currentCtx() == 'RotateSuperContext':
            manipulator_pos = cmds.manipRotateContext('Rotate', q=True, position=True)
        elif cmds.currentCtx() == 'scaleSuperContext':
            manipulator_pos = cmds.manipScaleContext('Scale', q=True, position=True)

        if not manipulator_pos:
            cmds.warning("Unable to get manipulator position. Ensure you're in move tool mode.")
            return

        # Store the position in a custom attribute on the scene
        if not cmds.objExists('storedPositionLocator'):
            create_loc_object('storedPositionLocator')
            #cmds.spaceLocator(name='storedPositionLocator')
            cmds.setAttr('storedPositionLocator.visibility', 0)

        cmds.xform('storedPositionLocator', translation=manipulator_pos, worldSpace=True)
        cmds.setAttr('storedPositionLocator.visibility', 1)
        print("Manipulator position stored:", manipulator_pos)
    
    @undoable
    def store_component_position_avg(self):
        selection = cmds.ls(selection=True, flatten=True)

        if not selection:
            cmds.warning("Nothing selected. Please select vertices, edges, faces, or objects.")
            return

        positions = []

        for item in selection:
            if '.vtx[' in item:
                # Vertex
                pos = cmds.xform(item, query=True, translation=True, worldSpace=True)
                positions.append(pos)
            elif '.e[' in item:
                # Edge
                edge_vertices = cmds.polyListComponentConversion(item, fromEdge=True, toVertex=True)
                edge_vertices = cmds.ls(edge_vertices, flatten=True)
                for vtx in edge_vertices:
                    pos = cmds.xform(vtx, query=True, translation=True, worldSpace=True)
                    positions.append(pos)
            elif '.f[' in item:
                # Face
                face_vertices = cmds.polyListComponentConversion(item, fromFace=True, toVertex=True)
                face_vertices = cmds.ls(face_vertices, flatten=True)
                for vtx in face_vertices:
                    pos = cmds.xform(vtx, query=True, translation=True, worldSpace=True)
                    positions.append(pos)
            else:
                # Assume it's an object
                if cmds.objExists(item):
                    pos = cmds.xform(item, query=True, translation=True, worldSpace=True)
                    positions.append(pos)
                else:
                    cmds.warning(f"Unsupported item type or object doesn't exist: {item}")

        if not positions:
            cmds.warning("No valid components or objects found. Please select vertices, edges, faces, or objects.")
            return

        avg_position = [sum(coord)/len(coord) for coord in zip(*positions)]

        # Store the position in a custom attribute on the scene
        if not cmds.objExists('storedPositionLocator'):
            cmds.spaceLocator(name='storedPositionLocator')
            cmds.setAttr('storedPositionLocator.visibility', 0)

        cmds.xform('storedPositionLocator', translation=avg_position, worldSpace=True)

        print("Component or object position stored:", avg_position)
    
    @undoable
    def move_objects_to_stored_position(self):
        selected_objects = cmds.ls(selection=True, long=True)
        
        # Check if the stored position locator exists
        if not cmds.objExists('storedPositionLocator'):
            create_loc_object('storedPositionLocator')
            cmds.setAttr('storedPositionLocator.visibility', 0)

        # Get the stored position
        stored_position = cmds.xform('storedPositionLocator', query=True, translation=True, worldSpace=True)

        # Check if there are any objects selected
        if not selected_objects:
            cmds.warning("Please select at least one object to move.")
            return

        # Loop through the selected objects and move them to the stored position
        for obj in selected_objects:
            # Get the current world space rotate pivot of the object
            current_position = cmds.xform(obj, query=True, worldSpace=True, rotatePivot=True)
            
            # Calculate the difference between the stored position and current position
            offset = [stored_position[i] - current_position[i] for i in range(3)]
            
            # Move the object by the calculated offset
            cmds.move(offset[0], offset[1], offset[2], obj, relative=True, worldSpace=True)
        
        cmds.select(selected_objects)
        print(f"Moved {len(selected_objects)} object(s) to stored position: {stored_position}")
    
    def match_move(self):
        mel.eval('''MatchTranslation;''')
    
    def match_rotate(self):
        mel.eval('''MatchRotation;''')
    
    def match_scale(self):
        mel.eval('''MatchScaling;''')
    
    def match_all(self):
        mel.eval('''MatchTransform;''')

    @undoable
    def reset_move(self):
        cmds.undoInfo(openChunk=True)
        try:
            # Get the list of selected objects
            sel_objs = cmds.ls(sl=True)

            # Loop through each selected object
            for obj in sel_objs:
                # Get the current translate values
                tx = cmds.getAttr(f"{obj}.tx")
                ty = cmds.getAttr(f"{obj}.ty")
                tz = cmds.getAttr(f"{obj}.tz")

                # Check if the attributes are locked
                tx_locked = cmds.getAttr(f"{obj}.tx", lock=True)
                ty_locked = cmds.getAttr(f"{obj}.ty", lock=True)
                tz_locked = cmds.getAttr(f"{obj}.tz", lock=True)

                # Reset the translate values if the attribute is not locked
                if not tx_locked:
                    cmds.setAttr(f"{obj}.tx", 0)

                if not ty_locked:
                    cmds.setAttr(f"{obj}.ty", 0)

                if not tz_locked:
                    cmds.setAttr(f"{obj}.tz", 0)
        finally:
            cmds.undoInfo(closeChunk=True) 
    
    @undoable
    def reset_rotate(self):
        cmds.undoInfo(openChunk=True)
        try:
            # Get the list of selected objects
            sel_objs = cmds.ls(sl=True)

            # Loop through each selected object
            for obj in sel_objs:
                # Get the current rotate values
                rx = cmds.getAttr(f"{obj}.rx")
                ry = cmds.getAttr(f"{obj}.ry")
                rz = cmds.getAttr(f"{obj}.rz")

                # Check if the rotate attributes are locked
                rx_locked = cmds.getAttr(f"{obj}.rx", lock=True)
                ry_locked = cmds.getAttr(f"{obj}.ry", lock=True)
                rz_locked = cmds.getAttr(f"{obj}.rz", lock=True)

                # Reset the rotate values if the attribute is not locked
                if not rx_locked:
                    cmds.setAttr(f"{obj}.rx", 0)
                if not ry_locked:
                    cmds.setAttr(f"{obj}.ry", 0)
                if not rz_locked:
                    cmds.setAttr(f"{obj}.rz", 0)
        finally:
            cmds.undoInfo(closeChunk=True)

    @undoable   
    def reset_scale(self):
        cmds.undoInfo(openChunk=True)
        try:
            # Get the list of selected objects
            sel_objs = cmds.ls(sl=True)

            # Loop through each selected object
            for obj in sel_objs:
                # Get the current scale values
                sx = cmds.getAttr(f"{obj}.sx")
                sy = cmds.getAttr(f"{obj}.sy")
                sz = cmds.getAttr(f"{obj}.sz")

                # Check if the scale attributes are locked
                sx_locked = cmds.getAttr(f"{obj}.sx", lock=True)
                sy_locked = cmds.getAttr(f"{obj}.sy", lock=True)
                sz_locked = cmds.getAttr(f"{obj}.sz", lock=True)

                # Reset the scale values if the attribute is not locked
                if not sx_locked:
                    cmds.setAttr(f"{obj}.sx", 1)
                if not sy_locked:
                    cmds.setAttr(f"{obj}.sy", 1)
                if not sz_locked:
                    cmds.setAttr(f"{obj}.sz", 1)
        finally:
            cmds.undoInfo(closeChunk=True) 

    @undoable
    def reset_all(self):
        cmds.undoInfo(openChunk=True)
        try:
            # Get the list of selected objects
            sel_objs = cmds.ls(sl=True)

            # Loop through each selected object
            for obj in sel_objs:
                # Get the current translate, rotate, and scale values
                tx = cmds.getAttr(f"{obj}.tx")
                ty = cmds.getAttr(f"{obj}.ty")
                tz = cmds.getAttr(f"{obj}.tz")
                rx = cmds.getAttr(f"{obj}.rx")
                ry = cmds.getAttr(f"{obj}.ry")
                rz = cmds.getAttr(f"{obj}.rz")
                sx = cmds.getAttr(f"{obj}.sx")
                sy = cmds.getAttr(f"{obj}.sy")
                sz = cmds.getAttr(f"{obj}.sz")

                # Check if the attributes are locked
                tx_locked = cmds.getAttr(f"{obj}.tx", lock=True)
                ty_locked = cmds.getAttr(f"{obj}.ty", lock=True)
                tz_locked = cmds.getAttr(f"{obj}.tz", lock=True)
                rx_locked = cmds.getAttr(f"{obj}.rx", lock=True)
                ry_locked = cmds.getAttr(f"{obj}.ry", lock=True)
                rz_locked = cmds.getAttr(f"{obj}.rz", lock=True)
                sx_locked = cmds.getAttr(f"{obj}.sx", lock=True)
                sy_locked = cmds.getAttr(f"{obj}.sy", lock=True)
                sz_locked = cmds.getAttr(f"{obj}.sz", lock=True)

                # Reset the translate values if the attribute is not locked
                if not tx_locked:
                    cmds.setAttr(f"{obj}.tx", 0)
                if not ty_locked:
                    cmds.setAttr(f"{obj}.ty", 0)
                if not tz_locked:
                    cmds.setAttr(f"{obj}.tz", 0)

                # Reset the rotate values if the attribute is not locked
                if not rx_locked:
                    cmds.setAttr(f"{obj}.rx", 0)
                if not ry_locked:
                    cmds.setAttr(f"{obj}.ry", 0)
                if not rz_locked:
                    cmds.setAttr(f"{obj}.rz", 0)

                # Reset the scale values if the attribute is not locked
                if not sx_locked:
                    cmds.setAttr(f"{obj}.sx", 1)
                if not sy_locked:
                    cmds.setAttr(f"{obj}.sy", 1)
                if not sz_locked:
                    cmds.setAttr(f"{obj}.sz", 1)
        finally:
            cmds.undoInfo(closeChunk=True) 
    #---------------------------------------------------------------------------------------------------------------
    def parent_constraint(self):
        mel.eval("ParentConstraint ;")

    def parent_constraint_options(self):
        mel.eval("ParentConstraintOptions ;")
    @undoable
    def create_adjustment_group(self):
        # Get the selected objects
        selection = cmds.ls(selection=True, long=True)
        
        # Check if there is at least one object selected
        if not selection:
            cmds.error("No objects selected. Please select at least one object.")
            return

        for ctrl_obj in selection:
            # Get the short name of the control object for naming the group
            ctrl_short_name = cmds.ls(ctrl_obj, shortNames=True)[0]
            grp1_name = f"{ctrl_short_name}_offset"
            #grp2_name = f"{ctrl_short_name}_xform"
            #grp3_name = f"{ctrl_short_name}_topGrp"
            
            # Get the current parent of the control object
            current_parent = cmds.listRelatives(ctrl_obj, parent=True, fullPath=True)
            
            # Create a group for ctrl_obj
            ctrl_grp1 = cmds.group(empty=True, name=grp1_name)
            #ctrl_grp2 = cmds.group(empty=True, name=grp2_name)
            #ctrl_grp3 = cmds.group(empty=True, name=grp3_name)
            
            # Match the transform of the new group to the control object
            cmds.matchTransform(ctrl_grp1, ctrl_obj)
            #cmds.matchTransform(ctrl_grp2, ctrl_obj)
            #cmds.matchTransform(ctrl_grp3, ctrl_obj)
            
            # If the control object had a parent, parent the new group to it
            if current_parent:
                cmds.parent(ctrl_grp1, current_parent[0])
                
            # Parent the control object to the new group
            cmds.parent(ctrl_obj, ctrl_grp1)
            #cmds.parent(ctrl_grp1, ctrl_grp2)
            #cmds.parent(ctrl_grp2, ctrl_grp3)
            
    @undoable
    def create_adjustment_group_move(self):
        # Get the selected objects
        selection = cmds.ls(selection=True, long=True)
        
        if len(selection) < 2:
            cmds.warning("Please select at least two objects: the control object and then the joint object.")
            return
        
        ctrl_obj = selection[0]
        jnt_obj = selection[-1]
        
        if not cmds.objExists(ctrl_obj) or not cmds.objExists(jnt_obj):
            cmds.warning("One or both of the selected objects do not exist.")
            return
        cmds.matchTransform(ctrl_obj, jnt_obj, rotation=True)
        cmds.makeIdentity(ctrl_obj, apply=True, rotate=True)

        # Get the short name of the control object for naming the group
        ctrl_short_name = cmds.ls(ctrl_obj, shortNames=True)[0]
        grp1_name = f"{ctrl_short_name}_offset"
        #grp2_name = f"{ctrl_short_name}_xform"
        #grp3_name = f"{ctrl_short_name}_topGrp"
        
        # Get the current parent of the control object
        current_parent = cmds.listRelatives(ctrl_obj, parent=True, fullPath=True)
        
        # Create a group for ctrl_obj
        ctrl_grp1 = cmds.group(empty=True, name=grp1_name)
        #ctrl_grp2 = cmds.group(empty=True, name=grp2_name)
        #ctrl_grp3 = cmds.group(empty=True, name=grp3_name)
        
        # Match the transform of the new group to the control object
        cmds.matchTransform(ctrl_grp1, ctrl_obj)
        #cmds.matchTransform(ctrl_grp2, ctrl_obj)
        #cmds.matchTransform(ctrl_grp3, ctrl_obj)
        
        # Parent the control object to the new group
        cmds.parent(ctrl_obj, ctrl_grp1)
        #cmds.parent(ctrl_grp1, ctrl_grp2)
        #cmds.parent(ctrl_grp2, ctrl_grp3)
        
        # If the control object had a parent, parent the new group to it
        if current_parent:
            cmds.parent(ctrl_grp1, current_parent[0])

        # Match the group's transform to the control object
        cmds.matchTransform(ctrl_grp1, jnt_obj)

    #---------------------------------------------------------------------------------------------------------------
    def set_key(self):
        mel.eval("setKeyframe -breakdown 0 -preserveCurveShape 1 -hierarchy none -controlPoints 0 -shape 0;")
    
    def set_breakdown(self):
        mel.eval("setKeyframe -breakdown 1 -preserveCurveShape 1 -hierarchy none -controlPoints 0 -shape 0;")
    
    @undoable
    def mute_all(self):
        # Get the selected objects
        selected_objects = cmds.ls(selection=True)

        # Check if any objects are selected
        if not selected_objects:
            cmds.warning("No object selected!")
        else:
            # Mute the channel box controls for each selected object
            for obj in selected_objects:
                for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
                    cmds.mute(f"{obj}.{attr}")

            print("Transform attributes muted for selected objects.")
    
    @undoable
    def unMute_all(self):
        # Get the selected objects
        selected_objects = cmds.ls(selection=True)

        # Check if any objects are selected
        if not selected_objects:
            cmds.warning("No object selected!")
        else:
            # Unmute the channel box controls for each selected object
            for obj in selected_objects:
                for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
                    cmds.mute(f"{obj}.{attr}", disable=True, force=True)

            print("Transform attributes unmuted for selected objects.")

    def insert_key(self):
        mel.eval("InsertKey;")
    
    def copy_keys(self):
        mel.eval("timeSliderCopyKey;")
    
    def paste_keys(self):
        mel.eval("timeSliderPasteKey false;")
    
    @undoable
    def paste_inverse(self):
        mel.eval("timeSliderPasteKey false;")
        try:
            # Get the list of selected objects
            sel_objs = cmds.ls(sl=True)

            # Loop through each selected object
            for obj in sel_objs:
                # Get the current translate, rotate, and scale values
                tx = cmds.getAttr(f"{obj}.tx")
                ty = cmds.getAttr(f"{obj}.ty")
                tz = cmds.getAttr(f"{obj}.tz")
                rx = cmds.getAttr(f"{obj}.rx")
                ry = cmds.getAttr(f"{obj}.ry")
                rz = cmds.getAttr(f"{obj}.rz")
                sx = cmds.getAttr(f"{obj}.sx")
                sy = cmds.getAttr(f"{obj}.sy")
                sz = cmds.getAttr(f"{obj}.sz")

                # Check if the attributes are locked
                tx_locked = cmds.getAttr(f"{obj}.tx", lock=True)
                ty_locked = cmds.getAttr(f"{obj}.ty", lock=True)
                tz_locked = cmds.getAttr(f"{obj}.tz", lock=True)
                rx_locked = cmds.getAttr(f"{obj}.rx", lock=True)
                ry_locked = cmds.getAttr(f"{obj}.ry", lock=True)
                rz_locked = cmds.getAttr(f"{obj}.rz", lock=True)
                sx_locked = cmds.getAttr(f"{obj}.sx", lock=True)
                sy_locked = cmds.getAttr(f"{obj}.sy", lock=True)
                sz_locked = cmds.getAttr(f"{obj}.sz", lock=True)

                # Reset the translate values if the attribute is not locked
                if not tx_locked:
                    cmds.setAttr(f"{obj}.tx", tx * -1)

                '''if not ty_locked:
                    cmds.setAttr(f"{obj}.ty", ty * -1)
                if not tz_locked:
                    cmds.setAttr(f"{obj}.tz", tz * -1)'''

                # Reset the rotate values if the attribute is not locked
                if not rx_locked:
                    cmds.setAttr(f"{obj}.rx", rx)
                if not ry_locked:
                    cmds.setAttr(f"{obj}.ry", ry * -1)
                if not rz_locked:
                    cmds.setAttr(f"{obj}.rz", rz * -1)
                
                '''# Reset the scale values if the attribute is not locked
                if not sx_locked:
                    cmds.setAttr(f"{obj}.sx", 1)
                if not sy_locked:
                    cmds.setAttr(f"{obj}.sy", 1)
                if not sz_locked:
                    cmds.setAttr(f"{obj}.sz", 1)'''
        finally:
            cmds.undoInfo(closeChunk=True) 
    
    def add_inbetweens(self):
        mel.eval("timeSliderEditKeys addInbetween;")

    def remove_inbetweens(self):
        mel.eval("timeSliderEditKeys removeInbetween;")

    def delete_keys(self):
        mel.eval('''timeSliderClearKey;''')
#----------------------------------------------------------------------------------------------------------------
    def set_graph_key(self):
        mel.eval("setKeyframe -breakdown 0 -preserveCurveShape 1 -hierarchy none -controlPoints 0 -shape 0;")

    def insert_key(self):
        mel.eval("InsertKey;")
    
    def copy_graph_key(self):
        mel.eval("copyKey ;")
    
    def paste_graph_key(self):
        current_time = cmds.currentTime(query=True)
        cmds.pasteKey(time=(current_time, current_time), option="merge")
    
    @undoable 
    def copy_and_paste_selected_keys(self):
        # Get the selected keys
        selected_keys = cmds.keyframe(q=True, sl=True)
        
        # Check if any keys are selected
        if not selected_keys:
            cmds.error("No keys selected. Please select keys in the graph editor.")
            return
        
        # Copy selected keys
        cmds.copyKey()
        print("Selected keys copied successfully.")
        
        # Paste keys at the current time without deleting existing keyframes
        current_time = cmds.currentTime(query=True)
        cmds.pasteKey(time=(current_time, current_time), option="merge")
        print("Keys pasted at the current time.")

    @undoable
    def invert_keys(self):
        mel.eval('scaleKey -scaleSpecifiedKeys 1 -autoSnap 0 -timeScale 1 -timePivot 0 -floatScale 1 -floatPivot 0 -valueScale -1 -valuePivot 0 ;')

    @undoable        
    def zero_out(self):
        # Get the selected keyframes
        selected_keys = cmds.keyframe(query=True, selected=True)

        if selected_keys:
            # Get the selected animation curves
            anim_curves = cmds.keyframe(query=True, selected=True, name=True)
            
            if anim_curves:
                # Get all selected keyframe times
                key_times = cmds.keyframe(query=True, selected=True, timeChange=True)
                
                for curve in anim_curves:
                    for time in key_times:
                        # Set the value of each selected keyframe to zero
                        cmds.keyframe(curve, edit=True, time=(time,), valueChange=0)
                
                print(f"Set {len(key_times)} keyframe(s) to zero across {len(anim_curves)} animation curve(s).")
            else:
                print("No animation curve selected.")
        else:
            print("No keyframe selected. Please select keyframe(s) in the Graph Editor.")

    def delete_keys_graphEditor(self):
        mel.eval("cutKey -animation keys -clear;")

    #----------------------------------------------------------------------------------------------------------------
    
def show_floating_tool():
    try:
        if hasattr(maya_main_window(), '_floating_tool_widget'):
            maya_main_window()._floating_tool_widget.close()
            maya_main_window()._floating_tool_widget.deleteLater()
    except:
        pass

    floating_tool_widget = FloatingTools(parent=maya_main_window())
    floating_tool_widget.setObjectName("floatingTool")
    floating_tool_widget.move(1280, 700)
    floating_tool_widget.show()
    maya_main_window()._floating_tool_widget = floating_tool_widget

show_floating_tool()
