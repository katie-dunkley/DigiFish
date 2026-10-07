import bpy
import os
import mathutils
import math

#--------Add fish model--------
class MESH_OT_add_fish_model(bpy.types.Operator):
    """Create fish object with optional skin texture"""
    bl_idname = "mesh.add_fish_model"
    bl_label = "Add Fish Mesh Object"

    def execute(self, context):
        # --- Get paths ---
        scene = bpy.context.scene
        scene.cursor.location = (0, 0, 0)
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 0.01
        scene.unit_settings.length_unit = 'CENTIMETERS'
        print("Scene defaults applied")
        
        filepath = bpy.path.abspath(context.scene.fish_filepath)

        if not filepath or not os.path.exists(filepath):
            self.report({'ERROR'}, f"Invalid fish model filepath. {filepath}")
            return {'CANCELLED'}

        # --- Import model ---
        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            available_meshes = data_from.meshes
            if not available_meshes:
                self.report({'ERROR'}, f"No meshes found in file: {filepath}")
                return {'CANCELLED'}
            
            # Load the first mesh
            data_to.meshes = [available_meshes[0]]    
        mesh = data_to.meshes[0]
        fish_model = bpy.data.objects.new(f"{context.scene.fish_name}_{context.scene.fish_id}", mesh)
        bpy.context.collection.objects.link(fish_model)
        bpy.context.view_layer.objects.active = fish_model
        fish_model.select_set(True)
        self.fish_id = context.scene.fish_id

        # --- Apply initial scale ---
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # --- Set origin and move to world origin ---
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')
        fish_model.location = (0, 0, 0)

        # --- Scale to real-world length ---
        model_length_x = fish_model.dimensions[0]
        actual_length = context.scene.fishlength

        if actual_length:
            scale_factor = actual_length / model_length_x
            fish_model.scale = (scale_factor,) * 3
            fish_model.select_set(True)
            bpy.context.view_layer.objects.active = fish_model
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        else:
            self.report({'ERROR'}, "No fish length provided, model not scaled.")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        bpy.ops.mesh.fill_holes(sides=4)
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # --- Compute bounding box in world space ---
        bbox_world = [fish_model.matrix_world @ mathutils.Vector(corner) for corner in fish_model.bound_box]
        head_x = min(v.x for v in bbox_world)
        tail_x = max(v.x for v in bbox_world)

        context.scene.fish_head_x = head_x
        context.scene.fish_tail_x = tail_x
        context.scene.bbox_world_str = ";".join(f"{v.x:.3f},{v.y:.3f},{v.z:.3f}" for v in bbox_world)


        # --- Store info in scene ---
        context.scene.fish_model_name = fish_model.name
        context.scene.fish_id = self.fish_id

        # --- Set viewport shading to RENDERED if in 3D view ---
        if context.space_data and hasattr(context.space_data, "shading"):
            context.space_data.shading.type = 'RENDERED'

        self.report({'INFO'}, f"Imported fish model: {fish_model.name}")
        self.report({'INFO'}, f"Model scaled to {actual_length} cm (TL).")
        return {'FINISHED'}

#--------Add eye cameras--------
class OBJECT_OT_add_cameras(bpy.types.Operator):
    """Add cameras at eye positions of the fish model"""

    bl_idname = "obj.add_eye_cameras"
    bl_label = "Add Cameras at Eyes"

    def execute(self, context):
        model_name = context.scene.fish_model_name
        number_fish = context.scene.fish_id

        fish_model = bpy.data.objects.get(model_name)
        if not fish_model or not fish_model.type == 'MESH':
            self.report({'ERROR'}, f"Fish model '{context.scene.fish_model_name}' not found or is not a mesh.")
            return {'CANCELLED'}

        # Get world-space vertex coordinates
        mesh = fish_model.data
        verts_world = [fish_model.matrix_world @ v.co for v in mesh.vertices]

        # Identify head region by thresholding along x-axis
        x_coords = [v.x for v in verts_world]
        x_min, x_max = min(x_coords), max(x_coords)
        head_threshold = x_min + 0.12 * (x_max - x_min)
        head_verts = [v for v in verts_world if v.x <= head_threshold]

        # Approximate eye center as lowest and highest Z in head region
        eye_loc = min(head_verts, key=lambda v: v.y)

        # Add left and right eye empties (mirrored across )
        left_eye_loc = (eye_loc.x, eye_loc.y, eye_loc.z)
        right_eye_loc = (eye_loc.x, -eye_loc.y, eye_loc.z)

        bpy.ops.object.empty_add(type='SPHERE', radius=0.07, location=left_eye_loc)
        left_eye = bpy.context.active_object
        left_eye.name = f"Lefteye_{context.scene.fish_model_name}"
        left_eye.rotation_euler[2] = -0.174533

        bpy.ops.object.empty_add(type='SPHERE', radius=0.07, location=right_eye_loc)
        right_eye = bpy.context.active_object
        right_eye.name = f"Righteye_{context.scene.fish_model_name}"
        right_eye.rotation_euler[2] = 0.174533

        # Optionally override eye location/scale
        if context.scene.eyecam_location:
            try:
                eye_values = [float(v.strip()) for v in context.scene.eyecam_location.split(',')]
                if len(eye_values) == 4:
                    scale,ex, ey, ez = eye_values
                    left_eye.location = (ex, ey, ez)
                    left_eye.scale = (scale, scale, scale)
                    right_eye.location = (ex, -ey, ez)
                    right_eye.scale = (scale, scale, scale)
            except ValueError:
                self.report({'WARNING'}, "Invalid eyecam_location format. Expected 4 comma-separated floats.")

        # Add and configure left eye camera
        bpy.ops.object.camera_add(location=(0, 0, 0))
        left_camera = bpy.context.active_object
        left_camera.name = f"LeftCamera_{context.scene.fish_model_name}"
        left_camera.parent = left_eye
        left_camera.location = (0, 0, 0)
        left_camera.rotation_euler = (1.5708, 0, 3.14159)
        left_camera.data.type = 'PERSP'
        left_camera.data.lens_unit = 'FOV'
        left_camera.data.angle = math.radians(context.scene.eyecamera_fov)
        left_camera.data.sensor_fit = 'HORIZONTAL'
       
        # Add and configure right eye camera
        bpy.ops.object.camera_add(location=(0, 0, 0))
        right_camera = bpy.context.active_object
        right_camera.name = f"RightCamera_{context.scene.fish_model_name}"
        right_camera.parent = right_eye
        right_camera.location = (0, 0, 0)
        right_camera.rotation_euler = (1.5708, 0, 0)
        right_camera.data.type = 'PERSP'
        right_camera.data.lens_unit = 'FOV'
        right_camera.data.angle = math.radians(context.scene.eyecamera_fov)
        right_camera.data.sensor_fit = 'HORIZONTAL'

        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.scene.render.resolution_x = int(context.scene.videowidth)
        bpy.context.scene.render.resolution_y = int(context.scene.videowidth)

        self.report({'INFO'}, "Eye cameras added.")
        return {'FINISHED'}

#--------Main class--------
class OBJECT_OT_addsinglefish(bpy.types.Operator):
    """Add single fish model"""

    bl_idname = "obj.add_singlefish"
    bl_label = "Add single fish"

    fish_filepath: bpy.props.StringProperty(
        name="Fish Model Path",
        description="Path to the base .obj fish model",
        subtype='FILE_PATH'
    )

    fish_name: bpy.props.StringProperty(
        name="Fish Name",
        description="Custom name for the fish model",
        default="Fish")
        
    fish_id: bpy.props.StringProperty(
        name="Fish ID",
        description="Custom identifier for the fish model",
        default="001"
    )
    
    fishlength: bpy.props.FloatProperty(
        name="Fish TL (cm)",
        description="Fish TL (cm) used for rescaling",
        default=3.0
    )
    
    
    addeyecam: bpy.props.EnumProperty(
        name="Eye cams?", description="Add cameras at eyes",
        items=[('YES', "Yes", ""), ('NO', "No", "")],
        default='YES'
    )
    
    eyecamera_fov: bpy.props.IntProperty(
        name="Eye FOV",
        description="FOV of eye camera in degrees",
        default=120,
        min=1
    )
    
    eyecam_location: bpy.props.StringProperty(
        name="Eye Cam Location",
        description="x,y,z coords of eye camera location",
        default=""
    )
 

    def invoke(self, context, event):
        # Trigger the popup that lets user enter fish_id
        return context.window_manager.invoke_props_dialog(self)


    def execute(self, context):
        context.scene.fish_id = self.fish_id
        context.scene.fishlength = self.fishlength
        context.scene.fish_name = self.fish_name
        context.scene.fish_filepath = self.fish_filepath
        context.scene.eyecam_location = self.eyecam_location
        context.scene.eyecamera_fov = self.eyecamera_fov

        bpy.ops.mesh.add_fish_model('EXEC_DEFAULT')
        if self.addeyecam=="YES":
            bpy.ops.obj.add_eye_cameras('EXEC_DEFAULT')
            
        
        fish_model_name = f"{self.fish_name}_{self.fish_id}"
        fish_model = bpy.data.objects.get(fish_model_name)
        if not fish_model:
            self.report({'ERROR'}, f"Fish model '{fish_model_name}' not found.")
            return {'CANCELLED'}

        # Create or get fish-specific collection
        collection_name = f"{self.fish_name}_{self.fish_id}"
        fish_coll = bpy.data.collections.get(collection_name)
        if not fish_coll:
            fish_coll = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(fish_coll)

        # Link fish model to its collection
        if fish_model.name not in fish_coll.objects:
            fish_coll.objects.link(fish_model)
            
        for coll in fish_model.users_collection:
                    if coll != fish_coll:
                        coll.objects.unlink(fish_model)

        # Optionally manage camera objects
        if self.addeyecam == "YES":
            camera_object = bpy.data.objects.get(f"Lefteye_{fish_model_name}")
            if camera_object:
                if camera_object.name not in fish_coll.objects:
                    fish_coll.objects.link(camera_object)

                # Unlink from any other collections
                for coll in camera_object.users_collection:
                    if coll != fish_coll:
                        coll.objects.unlink(camera_object)
            
            camera_object = bpy.data.objects.get(f"Righteye_{fish_model_name}")
            if camera_object:
                if camera_object.name not in fish_coll.objects:
                    fish_coll.objects.link(camera_object)

                # Unlink from any other collections
                for coll in camera_object.users_collection:
                    if coll != fish_coll:
                        coll.objects.unlink(camera_object)
        
            camera_object = bpy.data.objects.get(f"LeftCamera_{fish_model_name}")
            if camera_object:
                if camera_object.name not in fish_coll.objects:
                    fish_coll.objects.link(camera_object)

                # Unlink from any other collections
                for coll in camera_object.users_collection:
                    if coll != fish_coll:
                        coll.objects.unlink(camera_object)
        
            camera_object = bpy.data.objects.get(f"RightCamera_{fish_model_name}")
            if camera_object:
                if camera_object.name not in fish_coll.objects:
                    fish_coll.objects.link(camera_object)

                # Unlink from any other collections
                for coll in camera_object.users_collection:
                    if coll != fish_coll:
                        coll.objects.unlink(camera_object)
        
        return {'FINISHED'}
    
#--------------Register--------------
def register():

    bpy.utils.register_class(OBJECT_OT_addsinglefish)
    bpy.utils.register_class(MESH_OT_add_fish_model)
    bpy.utils.register_class(OBJECT_OT_add_cameras)

    bpy.types.Scene.fish_filepath = bpy.props.StringProperty(name="Fish Object Path")
    bpy.types.Scene.fishlength = bpy.props.FloatProperty(name="Fish length", default=3.0)
    bpy.types.Scene.fish_name= bpy.props.StringProperty(name="Named Fish Model")
    bpy.types.Scene.fish_id = bpy.props.StringProperty(name="Fish ID")    
    bpy.types.Scene.eyecam_location = bpy.props.StringProperty(name="Update eye camera location and scale",default="")
    bpy.types.Scene.eyecamera_fov = bpy.props.FloatProperty(name="Eye camera FOV", default=120)
    bpy.types.Scene.fish_head_x = bpy.props.FloatProperty(name="Fish head location x")
    bpy.types.Scene.fish_tail_x = bpy.props.FloatProperty(name="Fish tail location x")
    bpy.types.Scene.bbox_world_str = bpy.props.StringProperty(name="bbox_world")
    bpy.types.Scene.fish_model_name= bpy.props.StringProperty(name="Named Fish Model")

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_addsinglefish)
    bpy.utils.unregister_class(MESH_OT_add_fish_model)
    bpy.utils.unregister_class(OBJECT_OT_add_cameras)

    del bpy.types.Scene.fish_filepath 
    del bpy.types.Scene.fishlength 
    del bpy.types.Scene.fish_name
    del bpy.types.Scene.fish_id
    del bpy.types.Scene.eyecamera_fov 
    del bpy.types.Scene.eyecam_location
    del bpy.types.Scene.fish_head_x 
    del bpy.types.Scene.fish_tail_x
    del bpy.types.Scene.bbox_world_str
    del bpy.types.Scene.fish_model_name






