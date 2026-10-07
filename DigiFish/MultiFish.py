import bpy
import csv

import sys, subprocess

import sys, subprocess, importlib.util
import json

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

import pandas as pd





#-------Helper functions-------
def auto_convert(value):
    try:
        return float(value) if '.' in value else int(value)
    except ValueError:
        return value

def read_csv(file_path):
    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)
        return [{k: auto_convert(v) for k, v in row.items()} for row in reader]   

def upsample_frame_data_all_columns(data, original_fps, target_fps):
            
    multiplier = target_fps // original_fps
    data = sorted(data, key=lambda r: r['frame_idx'])

    all_columns = set()
    for row in data:
        all_columns.update(row.keys())
    all_columns.discard('frame_idx')  # Handle frame_idx separately

    upsampled = []
    for i, row in enumerate(data):
        base_frame = row['frame_idx'] * multiplier
        new_row = row.copy()
        new_row['frame_idx'] = base_frame
        upsampled.append(new_row)

               
        if i < len(data) - 1:
            next_frame = data[i + 1]['frame_idx'] * multiplier
            for f in range(base_frame + 1, next_frame):
                filler = {'frame_idx': f}
                for col in all_columns:
                    filler[col] = None
                upsampled.append(filler)

    return upsampled
     
# --------- Add multiple fish  ---------
import math
def set_scene_prop_safe(scene, scene_attr, row, colname, default=None, cast=str):
    """
    Sets scene.<scene_attr> from row[colname] if available and not NaN, else default.
    """
    val = row.get(colname)
    if val is not None and not (isinstance(val, float) and math.isnan(val)):
        setattr(scene, scene_attr, cast(val))
    else:
        setattr(scene, scene_attr, default)



class OBJECT_OT_addmulti(bpy.types.Operator):
    """Add multiple fish model"""

    bl_idname = "obj.add_multi"
    bl_label = "Add multiple fish to scene from csv info sheet"

    multi_filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to csv containing fish info",
        subtype='FILE_PATH'
    )

    def invoke(self, context, event):
        # Trigger the popup that lets user enter info
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):

        abs_path = bpy.path.abspath(self.multi_filepath)
        fish_data = pd.read_csv(
        abs_path,
        keep_default_na=True,    # Recognize standard NaN values
        na_values=["", " ", "   "]  # Treat empty or space-only cells as NaN
    )

        if fish_data.empty:
            self.report({'WARNING'}, "No data loaded from CSV.")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Loaded {len(fish_data)} rows from {self.multi_filepath}")

        # Columns to check - if missing data break 
        cols_to_check = [
            "Name", "ID", "ModelPath", "Size", "EyeCam", "EyeFOV",
            "Keypoints", "KeypointPositions", "Segments", "TrackData", "TrackDataFPS"
        ]
        fish_data[cols_to_check] = fish_data[cols_to_check].replace(r'^\s*$', pd.NA, regex=True)
        mask_specific = fish_data[cols_to_check].isna().any(axis=1)
        failing_specific = fish_data[mask_specific]
        if not failing_specific.empty:
            self.report({'WARNING'}, f"{len(failing_specific)} rows have no data in the specified columns: {failing_specific} ")
            return {'CANCELLED'}
        self.report({'INFO'}, "CSV data loaded successfully.")

        #-------------Add info to scene------------- 
        for idx, row in fish_data.iterrows():

            prop_map = [
            ("fish_name", "Name", str, ""),
            ("fish_id", "ID", str, ""),
            ("fishlength", "Size", float, 0.0),
            ("fish_filepath", "ModelPath", str, ""),
            ("keypoints", "Keypoints", str, ""),
            ("keypoint_locations", "KeypointPositions", str, ""),
            ("split_map", "Segments", str, ""),
            ("trackdata_folder", "TrackData", str, ""),
            ("eyetrackdata_folder", "EyeTrackData", str, ""),
            ("eyetrack_colnames", "EyeTrackColumns", str, ""),
            ("csvfps", "TrackDataFPS", float, 0.0),
            ("eyecsvfps", "EyeTrackDataFPS", float, 0.0),
            ("eyesmoothtime", "EyeTrackSmoothWindow", float, 0.0),
            ("pixelconvert", "PixelConvert", float, 0.0),
            ("smoothtime_posture", "PostureTrackSmooth", float, 0.0),
            ("smoothtime_orient", "OrientTrackSmooth", float, 0.0),
            ("smoothtime_move", "MoveTrackSmooth", float, 0.0),
            
        ]

            for scene_attr, colname, cast, default in prop_map:
                set_scene_prop_safe(context.scene, scene_attr, row, colname, default=default, cast=cast)
                        
        # -------------Add fish ------------- 
            bpy.ops.mesh.add_fish_model('EXEC_DEFAULT')

            eyecam=str(row["EyeCam"])
            context.scene.eyecam_location=str(row["EyeCamLocation"]) 
            context.scene.eyecamera_fov=float(row["EyeFOV"])

            if eyecam=="Yes":
                bpy.ops.obj.add_eye_cameras('EXEC_DEFAULT')

            fish_model_name = f"{context.scene.fish_name}_{context.scene.fish_id}"
            context.scene.fish_model_name=fish_model_name
            fish_model = bpy.data.objects.get(fish_model_name)
            if not fish_model:
                self.report({'ERROR'}, f"Fish model '{fish_model_name}' not found.")
                return {'CANCELLED'}
            collection_name = f"{context.scene.fish_name}_{context.scene.fish_id}"
            fish_coll = bpy.data.collections.get(collection_name)
            if not fish_coll:
                fish_coll = bpy.data.collections.new(collection_name)
                bpy.context.scene.collection.children.link(fish_coll)
            if fish_model.name not in fish_coll.objects:
                fish_coll.objects.link(fish_model)    
            for coll in fish_model.users_collection:
                        if coll != fish_coll:
                            coll.objects.unlink(fish_model)

            if eyecam=="Yes":
                camera_object = bpy.data.objects.get(f"Lefteye_{fish_model_name}")
                if camera_object:
                    if camera_object.name not in fish_coll.objects:
                        fish_coll.objects.link(camera_object)
                    for coll in camera_object.users_collection:
                        if coll != fish_coll:
                            coll.objects.unlink(camera_object)
                
                camera_object = bpy.data.objects.get(f"Righteye_{fish_model_name}")
                if camera_object:
                    if camera_object.name not in fish_coll.objects:
                        fish_coll.objects.link(camera_object)
                    for coll in camera_object.users_collection:
                        if coll != fish_coll:
                            coll.objects.unlink(camera_object)
            
                camera_object = bpy.data.objects.get(f"LeftCamera_{fish_model_name}")
                if camera_object:
                    if camera_object.name not in fish_coll.objects:
                        fish_coll.objects.link(camera_object)
                    for coll in camera_object.users_collection:
                        if coll != fish_coll:
                            coll.objects.unlink(camera_object)
            
                camera_object = bpy.data.objects.get(f"RightCamera_{fish_model_name}")
                if camera_object:
                    if camera_object.name not in fish_coll.objects:
                        fish_coll.objects.link(camera_object)
                    for coll in camera_object.users_collection:
                        if coll != fish_coll:
                            coll.objects.unlink(camera_object)
            
            # -------------Add bones ------------- 
            fish_obj = bpy.data.objects.get(fish_model_name)
            bpy.ops.object.select_all(action='DESELECT')
            fish_obj.select_set(True)
            context.view_layer.objects.active = fish_obj
            bpy.ops.obj.posefish('EXEC_DEFAULT')
            
            collection_name = f"{context.scene.fish_model_name}"
            fish_coll = bpy.data.collections.get(collection_name)
            if not fish_coll:
                fish_coll = bpy.data.collections.new(collection_name)
                bpy.context.scene.collection.children.link(fish_coll)

            new_object = bpy.data.objects.get(f"DirectionControl_{context.scene.fish_model_name }")
            if new_object:
                if new_object.name not in fish_coll.objects:
                    fish_coll.objects.link(new_object)
                    # Unlink from any other collections
                for coll in new_object.users_collection:
                    if coll != fish_coll:
                        coll.objects.unlink(new_object)
            
            new_object = bpy.data.objects.get(f"BodyCurve_{context.scene.fish_model_name }")
            if new_object:
                if new_object.name not in fish_coll.objects:
                    fish_coll.objects.link(new_object)
                    # Unlink from any other collections
                for coll in new_object.users_collection:
                    if coll != fish_coll:
                        coll.objects.unlink(new_object)
            
            new_object = bpy.data.objects.get(f"FishArmature_{context.scene.fish_model_name }")
            if new_object:
                if new_object.name not in fish_coll.objects:
                    fish_coll.objects.link(new_object)
                    # Unlink from any other collections
                for coll in new_object.users_collection:
                    if coll != fish_coll:
                        coll.objects.unlink(new_object)
            
            new_object = bpy.data.objects.get(f"IKArmature_{context.scene.fish_model_name }")
            if new_object:
                if new_object.name not in fish_coll.objects:
                    fish_coll.objects.link(new_object)
                    # Unlink from any other collections
                for coll in new_object.users_collection:
                    if coll != fish_coll:
                        coll.objects.unlink(new_object)
            
            new_object = bpy.data.objects.get(f"Circle_{context.scene.fish_model_name }")
            if new_object:
                if new_object.name not in fish_coll.objects:
                    fish_coll.objects.link(new_object)
                    # Unlink from any other collections
                for coll in new_object.users_collection:
                    if coll != fish_coll:
                        coll.objects.unlink(new_object)

            # -------------Read in tracking data  -------------  
            #track_data_store = {}
            #eyetrack_data_store={}
            bpy.ops.obj.readdata('EXEC_DEFAULT')
            track_data = json.loads(context.scene.track_data_store)
            if context.scene.eyetrack_data_store:
                eyetrack_data=json.loads(context.scene.eyetrack_data_store)
            else:
                self.report({'WARNING'}, "Eye data CSV is empty or invalid. Proceeding without eye data.")
            
            bpy.ops.obj.bodypose('EXEC_DEFAULT')

            if context.scene.eyetrackdata_folder and context.scene.eyetrack_colnames:
                bpy.ops.obj.eyepose('EXEC_DEFAULT')


            bpy.ops.obj.bodyorient('EXEC_DEFAULT')
            bpy.ops.obj.bodylocate('EXEC_DEFAULT')




        return {'FINISHED'}
    

#--------------Register--------------
def register():
    bpy.utils.register_class(OBJECT_OT_addmulti)
    bpy.types.Scene.fish_filepath = bpy.props.StringProperty(name="Fish Object Path")
    bpy.types.Scene.fishlength = bpy.props.FloatProperty(name="Fish length", default=3.0)
    bpy.types.Scene.fish_name= bpy.props.StringProperty(name="Named Fish Model")
    bpy.types.Scene.fish_id = bpy.props.StringProperty(name="Fish ID")    
    bpy.types.Scene.eyecam_location = bpy.props.StringProperty(name="Update eye camera location and scale",default="")
    bpy.types.Scene.eyecamera_fov = bpy.props.FloatProperty(name="Eye camera FOV", default=120)
    bpy.types.Scene.keypoints = bpy.props.StringProperty(name="Keypoints")
    bpy.types.Scene.keypoint_locations = bpy.props.StringProperty(name="Keypoint locations")
    bpy.types.Scene.split_map = bpy.props.StringProperty(name="Keypoint segments")
    bpy.types.Scene.fish_model_name= bpy.props.StringProperty(name="Named Fish Model")
    bpy.types.Scene.trackdata_folder = bpy.props.StringProperty(name="Track data folder", default="")
    bpy.types.Scene.eyetrackdata_folder = bpy.props.StringProperty(name="Eye track data file", default="")
    bpy.types.Scene.eyetrack_colnames= bpy.props.StringProperty(name="Eye cam column names")
    bpy.types.Scene.csvfps = bpy.props.FloatProperty(name="Track data frames per second", default=240)
    bpy.types.Scene.eyecsvfps = bpy.props.FloatProperty(name="Eye track data frames per second", default=30)
    bpy.types.Scene.track_data_store = bpy.props.StringProperty(name="Track Data Store")

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_addmulti)
    del bpy.types.Scene.fish_filepath 
    del bpy.types.Scene.fishlength
    del bpy.types.Scene.fish_name
    del bpy.types.Scene.fish_id 
    del bpy.types.Scene.eyecam_location 
    del bpy.types.Scene.eyecamera_fov 
    del bpy.types.Scene.keypoints 
    del bpy.types.Scene.keypoint_locations
    del bpy.types.Scene.split_map
    del bpy.types.Scene.fish_model_name
    del bpy.types.Scene.trackdata_folder 
    del bpy.types.Scene.eyetrackdata_folder 
    del bpy.types.Scene.eyetrack_colnames
    del bpy.types.Scene.csvfps 
    del bpy.types.Scene.eyecsvfps
    del bpy.types.Scene.track_data_store 
