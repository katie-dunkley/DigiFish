import bpy

import sys, subprocess

import sys, subprocess, importlib.util
from math import radians

def installModule(packageName):
    try:
        __import__(packageName)
        print(f"'{packageName}' is already installed.")
    except ImportError:
        print(f"Installing '{packageName}'...")
        python_exe = sys.executable

        # ensure pip exists
        if importlib.util.find_spec("pip") is None:
            subprocess.check_call([python_exe, "-m", "ensurepip", "--upgrade"])

        # upgrade pip
        subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])

        # install the package
        subprocess.check_call([python_exe, "-m", "pip", "install", "--user", packageName])
installModule("pandas")
installModule("scipy")
installModule("statsmodels")
installModule("scikit-misc")





import csv
import pandas as pd
import math
import os


#------------Add camera------------
class OBJECT_OT_addcamera(bpy.types.Operator):
    """Add cameras with custom settings"""
    bl_idname = "obj.addcamera"
    bl_label = "Add Cameras"

    location: bpy.props.EnumProperty(
        name="Camera View",
        description="Location of camera",
        items=[
            ('TOP', "Top View", ""),
            ('SIDE', "Side View", "")
        ],
        default='TOP'
    )

    fov: bpy.props.FloatProperty(
        name="Lens FOV (mm)",
        default=90.0,
        min=1.0,
        max=250.0
    )
    
    distance: bpy.props.FloatProperty(
        name="Distance from base (cm)",
        default=80.0
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        scene = context.scene

        # Convert scene dimensions from pixels to meters
        width_scaled = scene.videowidth * scene.pixelconvert
        height_scaled = scene.videoheight * scene.pixelconvert

        # Deselect everything
        bpy.ops.object.select_all(action='DESELECT')

        # Add the camera
        bpy.ops.object.camera_add()
        camera_object = context.active_object
        camera_object.name = f"{self.location.capitalize()}Camera"
        camera_object.data.lens_unit = 'FOV'
        camera_object.data.angle = math.radians(self.fov)

        # Default location and rotation
        if self.location == "TOP":
            camera_object.location = (width_scaled / 2,  height_scaled / 2, self.distance)
            camera_object.rotation_euler = (0, 0, 0)

        elif self.location == "SIDE":
            # Create empty directly
            control_name = f"CameraControl_{camera_object.name}"
            sidecam_empty = bpy.data.objects.new(control_name, None)
            sidecam_empty.empty_display_type = 'CIRCLE'
            sidecam_empty.empty_display_size = 40
            sidecam_empty.location = (width_scaled / 2, height_scaled / 2,self.distance)
            sidecam_empty.rotation_euler=(1.5708,0,0)
            sidecam_empty.lock_rotation[0] = True
            sidecam_empty.lock_rotation[1] = True

            # Offset camera relative to empty, then parent
            camera_object.location = (sidecam_empty.empty_display_size, 0, 0)  # Offset relative to empty
            camera_object.scale=(0.5, 0.5,0.5)
            camera_object.parent = sidecam_empty

            # Track the empty
            track = camera_object.constraints.new(type='TRACK_TO')
            track.target = sidecam_empty
            track.track_axis = 'TRACK_NEGATIVE_Z'
            track.up_axis = 'UP_Y'

        # Create or get the "Cameras" collection
        cam_coll = bpy.data.collections.get("Cameras")
        if not cam_coll:
            cam_coll = bpy.data.collections.new("Cameras")
            context.scene.collection.children.link(cam_coll)

        # Link objects to Cameras collection
        if camera_object.name not in cam_coll.objects:
            cam_coll.objects.link(camera_object)
        if self.location == "SIDE" and sidecam_empty.name not in cam_coll.objects:
            cam_coll.objects.link(sidecam_empty)

        # Unlink from current collection if not Cameras
        for coll in camera_object.users_collection:
            if coll != cam_coll:
                coll.objects.unlink(camera_object)
        if self.location == "SIDE":
            for coll in sidecam_empty.users_collection:
                if coll != cam_coll:
                    coll.objects.unlink(sidecam_empty)

        self.report({'INFO'}, f"Added {self.location} camera")
        return {'FINISHED'}


#----------Select active cameras---------

def get_camera_items(self, context):
    """Dynamically list all cameras in the scene"""
    cameras = [(cam.name, cam.name, "") for cam in bpy.data.objects if cam.type == 'CAMERA']
    if not cameras:
        cameras = [("NONE", "No cameras found", "")]
    return cameras


class OBJECT_OT_select_active_camera(bpy.types.Operator):
    """Select a camera to set as active"""
    bl_idname = "obj.select_active_camera"
    bl_label = "Select Active Camera"

    camera_name: bpy.props.EnumProperty(
        name="Cameras",
        description="Choose a camera to make active",
        items=get_camera_items
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "camera_name")

    def execute(self, context):
        camera_obj = bpy.data.objects.get(self.camera_name)
        if camera_obj and camera_obj.type == 'CAMERA':
            context.scene.camera = camera_obj
            self.report({'INFO'}, f"Active camera set to: {camera_obj.name}")
            name = camera_obj.name.lower()
            if "left" in name or "right" in name:
                scene = context.scene
                scene.render.resolution_x = int(context.scene.videowidth)
                scene.render.resolution_y = int(context.scene.videowidth)
            else:
                scene = context.scene
                scene.render.resolution_x = int(context.scene.videowidth)
                scene.render.resolution_y = int(context.scene.videoheight)

            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Selected object is not a valid camera.")
            return {'CANCELLED'}

#----------Render video

class OBJECT_OT_rendervideo(bpy.types.Operator):
    """Render video"""
    bl_idname = "obj.rendervideo"
    bl_label = "Render Video"

    output_path: bpy.props.StringProperty(
        name="Output Folder",
        description="Folder to save video (leave blank to use .blend folder)",
        default="//",
        subtype='DIR_PATH'
    )

    video_name: bpy.props.StringProperty(
        name="Video Name",
        description="Filename for the rendered video (no extension needed)",
        default="rendered_video"
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "output_path")
        layout.prop(self, "video_name")

    def execute(self, context):
        # Find keyframe range
        min_frame = float('inf')
        max_frame = float('-inf')

        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action:
                for fcurve in obj.animation_data.action.fcurves:
                    for keyframe in fcurve.keyframe_points:
                        frame = keyframe.co.x
                        min_frame = min(min_frame, frame)
                        max_frame = max(max_frame, frame)

        if min_frame == float('inf'):
            self.report({'ERROR'}, "No keyframes found.")
            return {'CANCELLED'}

        # Configure scene settings
        scene = context.scene
        scene.frame_start = int(min_frame)
        scene.frame_end = int(max_frame)
        scene.render.fps = int(scene.maxfps)
        #scene.render.resolution_x = int(scene.videowidth)
        #scene.render.resolution_y = int(scene.videoheight)
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'

        # Determine output file path

        base_dir = bpy.path.abspath(self.output_path) if self.output_path.strip() else bpy.path.abspath("//")
        video_filename = self.video_name.strip() or "rendered_video"
        if not video_filename.lower().endswith(".mp4"):
            video_filename += ".mp4"
        scene.render.filepath = os.path.join(base_dir, video_filename)
        
        
        bpy.ops.render.render('INVOKE_DEFAULT', animation=True)

        self.report({'INFO'}, f"Rendered to: {scene.render.filepath}")
        return {'FINISHED'}


class OBJECT_OT_rendervideoeye(bpy.types.Operator):
    """Render video eye"""
    bl_idname = "obj.rendervideoeye"
    bl_label = "Render Video - eye pov"

    
    renderModeEnum: bpy.props.EnumProperty(
        items=[
            ("EQUI", "Equirectangular", "Renders in equirectangular projection"),
            ("DOME", "Full Dome", "Renders in full dome projection"),
        ],
        default="EQUI",
        name="Mode",
    )

    domeMethodEnum: bpy.props.EnumProperty(
        items=[
            ("0", "Equidistant (VTA)", "Renders in equidistant dome projection"),
            ("1", "Hemispherical (VTH)", "Renders in hemispherical dome projection"),
            ("2", "Equisolid", "Renders in equisolid dome projection"),
            ("3", "Stereographic", "Renders in Stereographic dome projection"),
        ],
        default="0",
        name="Method",
    )

    fovModeEnum: bpy.props.EnumProperty(
        items=[
            ("180", "180°", "VR 180"),
            ("360", "360°", "VR 360 (over 180°, not support stereo)"),
            ("ANY", "Custom FOV", "over 180°, not support stereo"),
        ],
        default="180",
        name="VR Format",
    )

    HFOV360: bpy.props.FloatProperty(
        name="Horizontal FOV",
        subtype='ANGLE',
        precision=0,
        step=100,
        default=radians(360),
        min=radians(1),
        max=radians(360),
        description="Horizontal Field of view in degrees",
    )

    HFOV180: bpy.props.FloatProperty(
        name="Horizontal FOV",
        subtype='ANGLE',
        unit='ROTATION',
        precision=0,
        step=100,
        default=radians(180),
        min=radians(1),
        max=radians(180),
        description="Horizontal Field of view in degrees",
    )

    VFOV: bpy.props.FloatProperty(
        name="Vertical FOV",
        subtype='ANGLE',
        unit='ROTATION',
        precision=0,
        step=100,
        default=radians(180),
        min=radians(1),
        max=radians(180),
        description="Vertical Field of view in degrees",
    )

    frontFOV: bpy.props.FloatProperty(
        name="Front View FOV",
        subtype='ANGLE',
        unit='ROTATION',
        precision=0,
        step=100,
        default=radians(90),
        min=radians(90),
        max=radians(160),
        description="Front View's Field of view in degrees",
    )

    stitchMargin: bpy.props.FloatProperty(
        name="Stitch Margin",
        subtype='ANGLE',
        unit='ROTATION',
        precision=0,
        step=100,
        default=radians(5),
        min=radians(0),
        max=radians(15),
        description="Margin for Seam Blending in degrees",
    )

    frontViewResolution: bpy.props.FloatProperty(
        name="Front View Resolution",
        subtype='PERCENTAGE',
        precision=0,
        step=100,
        default=90,
        min=1,
        max=100,
        description="Overscan/Reduction Rate for Front View Rendering",
    )

    sideViewResolution: bpy.props.FloatProperty(
        name="Side View Resolution",
        subtype='PERCENTAGE',
        precision=0,
        step=100,
        default=90,
        min=1,
        max=100,
        description="Overscan/Reduction Rate for Side View Rendering",
    )

    topViewResolution: bpy.props.FloatProperty(
        name="Top View Resolution",
        subtype='PERCENTAGE',
        precision=0,
        step=100,
        default=90,
        min=1,
        max=100,
        description="Overscan/Reduction Rate for Top View Rendering",
    )

    bottomViewResolution: bpy.props.FloatProperty(
        name="Bottom View Resolution",
        subtype='PERCENTAGE',
        precision=0,
        step=100,
        default=90,
        min=1,
        max=100,
        description="Overscan/Reduction Rate for Bottom View Rendering",
    )

    rearViewResolution: bpy.props.FloatProperty(
        name="Rear View Resolution",
        subtype='PERCENTAGE',
        precision=0,
        step=100,
        default=90,
        min=1,
        max=100,
        description="Overscan/Reduction Rate for Rear View Rendering",
    )

    appliesParallaxForSideAndBack: bpy.props.BoolProperty(
        description="If it is on, it allows for noticeable seams or blending artifacts in side and rear views to introduce collect parallax"\
         " at over HFOV 180 rendering. default is false.",
        default=False,
        name="Apply Parallax for side and rear view",
    )

    isTopRightEye: bpy.props.BoolProperty(
        description="If it is on, right eye image will be placed as top image. default is false.",
        default=False,
        name="Top is RightEye",
    )

    trueTopBottom: bpy.props.BoolProperty(
        name="TrueTopBottom",
        default=False
    )

    cancel: bpy.props.BoolProperty(
        name="Cancel",
        default=True
    )


    def invoke(self, context, event):
        # Opens the properties dialog popup
        return context.window_manager.invoke_props_dialog(self, width=420)


    def draw(self, context):
        layout = self.layout

        layout.label(text="Render Mode:")
        layout.prop(self, "renderModeEnum", text="")

        if self.renderModeEnum == "DOME":
            layout.prop(self, "domeMethodEnum")

        layout.separator()
        layout.label(text="Field of View:")
        layout.prop(self, "fovModeEnum", text="")

        col = layout.column(align=True)
        if self.fovModeEnum == "180":
            col.prop(self, "HFOV180")
        elif self.fovModeEnum == "360":
            col.prop(self, "HFOV360")
        else:
            col.prop(self, "HFOV360", text="HFOV (custom)")
        col.prop(self, "VFOV")

        layout.separator()
        layout.prop(self, "frontFOV")
        layout.prop(self, "stitchMargin")

        layout.separator()
        layout.label(text="View Resolutions:")
        col = layout.column(align=True)
        col.prop(self, "frontViewResolution")
        col.prop(self, "sideViewResolution")
        col.prop(self, "topViewResolution")
        col.prop(self, "bottomViewResolution")
        col.prop(self, "rearViewResolution")

        layout.separator()
        layout.prop(self, "appliesParallaxForSideAndBack")
        layout.prop(self, "isTopRightEye")
        layout.prop(self, "trueTopBottom")

    def execute(self, context):
        ee = context.scene.eeVR
        # Enum properties
        ee.renderModeEnum = self.renderModeEnum
        ee.domeMethodEnum = self.domeMethodEnum
        ee.fovModeEnum = self.fovModeEnum

        # Float properties
        ee.HFOV360 = self.HFOV360
        ee.HFOV180 = self.HFOV180
        ee.VFOV = self.VFOV
        ee.frontFOV = self.frontFOV
        ee.stitchMargin = self.stitchMargin

        ee.frontViewResolution = self.frontViewResolution
        ee.sideViewResolution = self.sideViewResolution
        ee.topViewResolution = self.topViewResolution
        ee.bottomViewResolution = self.bottomViewResolution
        ee.rearViewResolution = self.rearViewResolution

        # Boolean properties
        ee.appliesParallaxForSideAndBack = self.appliesParallaxForSideAndBack
        ee.isTopRightEye = self.isTopRightEye
        ee.trueTopBottom = self.trueTopBottom
        ee.cancel = self.cancel

        bpy.context.scene.render.image_settings.file_format = 'PNG'
        # Start eeVR animation render
        bpy.ops.eevr.render_animation('EXEC_DEFAULT')


        self.report({'INFO'}, "Render started with selected eeVR settings")
        return {'FINISHED'}



#--------------Register--------------
def register():
    bpy.utils.register_class(OBJECT_OT_addcamera)
    bpy.utils.register_class(OBJECT_OT_select_active_camera)
    bpy.utils.register_class(OBJECT_OT_rendervideo)
    bpy.utils.register_class(OBJECT_OT_rendervideoeye)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_addcamera)
    bpy.utils.unregister_class(OBJECT_OT_select_active_camera)
    bpy.utils.unregister_class(OBJECT_OT_rendervideo)
    bpy.utils.unregister_class(OBJECT_OT_rendervideoeye)

