import bpy
import mathutils

#-------Add bones class-------

class POSE_OT_posefish(bpy.types.Operator):
    """Add armature, Bezier curve, and control points to pose a fish"""
    bl_idname = "obj.posefish"
    bl_label = "Add ability to pose fish"

    def execute(self, context):
        keypoints = [k.strip() for k in context.scene.keypoints.split(',') if k.strip()]
        if not keypoints:
            self.report({'WARNING'}, "No keypoints provided.")
            return {'CANCELLED'}
        
        model_name = context.scene.fish_model_name
        fish_model = bpy.data.objects.get(model_name)
        if not fish_model:
            self.report({'WARNING'}, f"Fish model '{model_name}' not found.")
            return {'CANCELLED'}

        number_fish=context.scene.fish_id
        # Create and configure armature
        bpy.ops.object.armature_add(enter_editmode=True, align='WORLD', location=(0, 0, 0))
        armature = bpy.context.object
        armature.name = f"FishArmature_{context.scene.fish_model_name}"
        bones = armature.data.edit_bones
        bones.remove(bones[0])

        raw_str = context.scene.bbox_world_str
        bbox_world = [mathutils.Vector(map(float, s.split(','))) for s in raw_str.split(';')]
        head_point = min(bbox_world, key=lambda v: v.x)
        fish_head_x = head_point.x
        tail_point_x = max(bbox_world, key=lambda v: v.x).x
        model_length = abs(fish_head_x - tail_point_x)

        x_min = min(v.x for v in bbox_world)
        threshold = 1e-3
        head_y_values = [v.y for v in bbox_world if abs(v.x - x_min) < threshold]
        head_y = sum(head_y_values) / len(head_y_values)

        keypoint_locations = [float(k.strip()) for k in context.scene.keypoint_locations.split(',')]
        
        if 1.0 in keypoint_locations:
            keypoints= keypoints[:-1]
        
        if 1.0 not in keypoint_locations:
            keypoint_locations.append(1.0)
        
        if 0.0 in keypoint_locations:
            keypoint_locations.remove(0.0)
            
        self.report({'WARNING'}, f"{keypoint_locations}.")   
        def parse_split_map(split_str):
            split_dict = {}
            for item in split_str.split(','):
                try:
                    key, val = item.split(':')
                    split_dict[key.strip()] = int(val.strip())
                except ValueError:
                    print(f"Invalid entry: {item}")
            return split_dict

        split_map = parse_split_map(context.scene.split_map)

        previous_bone = None
        for i, name in enumerate(keypoints):
            start_x = head_point.x if i == 0 else head_point.x + model_length * keypoint_locations[i - 1]
            end_x = head_point.x + model_length * keypoint_locations[i] if i < len(keypoints) - 1 else context.scene.fish_tail_x
            n_splits = split_map.get(name, 1)
            segment_length = (end_x - start_x) / n_splits

            for s in range(n_splits):
                seg_name = f"{name}_{s+1}" if n_splits > 1 else name
                bone = bones.new(seg_name)
                bone.head = (start_x + s * segment_length, head_y, 0)
                bone.tail = (start_x + (s + 1) * segment_length, head_y, 0)
                if previous_bone:
                    bone.parent = previous_bone
                    bone.use_connect = True
                previous_bone = bone
        
        bpy.ops.object.mode_set(mode='OBJECT')
        fish_model.select_set(True)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')

        # Parent eyes to head bone if they exist
        bone_matrix_world = armature.matrix_world @ armature.pose.bones[0].matrix
        for side in ["Lefteye", "Righteye"]:
            eye_name = f"{side}_{context.scene.fish_model_name}"
            if eye_name in bpy.data.objects:
                eye = bpy.data.objects[eye_name]
                original_matrix = eye.matrix_world.copy()
                eye.parent = armature
                eye.parent_type = 'BONE'
                eye.parent_bone = keypoints[0]
                eye.matrix_parent_inverse = bone_matrix_world.inverted()
                eye.matrix_world = original_matrix
                self.report({'INFO'}, f"{eye_name}, {keypoints[0]}")

        
        # Bezier curve
        bpy.ops.curve.primitive_bezier_curve_add()
        curve_obj = bpy.context.active_object
        curve_obj.name = f"BodyCurve_{context.scene.fish_model_name}"
        curve = curve_obj.data
        curve.dimensions = '3D'
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.curve.select_all(action='SELECT')
        bpy.ops.curve.delete(type='VERT')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        
        armature = bpy.data.objects.get(f"FishArmature_{context.scene.fish_model_name}")
        pose_bone_names = [pb.name for pb in armature.pose.bones]
        points = []
        for i, kp in enumerate(keypoints):
            if kp in split_map:
                 points.append(armature.matrix_world @ armature.pose.bones[f"{kp}_1"].head)
            else:
                points.append(armature.matrix_world @ armature.pose.bones[kp].head)
        points.append(armature.matrix_world @ armature.pose.bones[keypoints[-1]].tail)
            
        spline = curve.splines.new('BEZIER')
        spline.bezier_points.add(len(points) - 1)
        for i, pt in enumerate(points):
            bp = spline.bezier_points[i]
            bp.co = pt
            if i == 0 or i == len(spline.bezier_points) - 1:
                bp.handle_left_type = bp.handle_right_type = 'VECTOR'
            else:
                bp.handle_left_type = bp.handle_right_type = 'AUTO'

        coords = [f"({p.co.x:.2f}, {p.co.y:.2f}, {p.co.z:.2f})" for p in spline.bezier_points]
        self.report({'INFO'}, f"Curve points: {' | '.join(coords)}")

        bpy.ops.object.mode_set(mode='OBJECT')

        fish_model.select_set(True)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')

        # Spline IK setup
        for bone in armature.pose.bones:
            bone.bone.select = False

        last_bone_name = list(armature.pose.bones.keys())[-1]
        last_bone = armature.pose.bones[last_bone_name]
        last_bone.bone.select = True

        bezier_curve = bpy.data.objects.get(curve_obj.name)
        ik_constraint = last_bone.constraints.new(type='SPLINE_IK')
        ik_constraint.target = bezier_curve
        ik_constraint.chain_count = len(armature.pose.bones)
        ik_constraint.y_scale_mode = 'BONE_ORIGINAL'
        bpy.ops.object.mode_set(mode='OBJECT')
        
        
        # Add IK controller bones
        bpy.ops.object.armature_add()
        IK_armature = bpy.context.object
        IK_armature.name = f"IKArmature_{context.scene.fish_model_name}"
        bpy.ops.object.mode_set(mode='EDIT')
        bones = IK_armature.data.edit_bones
        bones.remove(bones[0])
        ik_keypoints=[k.strip() for k in context.scene.keypoints.split(',') if k.strip()]
        
        keypoint_locations = [float(k.strip()) for k in context.scene.keypoint_locations.split(',')]
        if 1.0 not in keypoint_locations:
            ik_keypoints.append("End")

        for i, kp in enumerate(ik_keypoints):
            if i == 0:
                continue
            loc = spline.bezier_points[i].co
            bone = bones.new(f"IK_{kp}")
            bone.head = loc
            bone.tail = (loc[0]+1, loc[1], loc[2])

        bpy.ops.object.mode_set(mode='OBJECT')
        IK_armature.show_in_front = True
        
        # Hook curve points to IK bones
        for i, kp in enumerate(ik_keypoints):
            if(i == 0):
                continue
            bone_name = f"IK_{kp}"  # Bone name
            position = i
            bpy.ops.object.select_all(action='DESELECT')
            IK_armature.select_set(True) 
            bpy.context.view_layer.objects.active = IK_armature  # Make it active
            bpy.ops.object.mode_set(mode='POSE')
            pose_bone = IK_armature.pose.bones.get(bone_name)      
            IK_armature.data.bones.active = IK_armature.data.bones.get(bone_name)
            bpy.ops.object.mode_set(mode='OBJECT')
            bezier_curve.select_set(True)
            bpy.context.view_layer.objects.active = bezier_curve 
            bpy.ops.object.mode_set(mode='EDIT') 
            bpy.ops.curve.select_all(action='DESELECT')
            bezier_curve.data.splines[0].bezier_points[position].select_control_point = True
            bpy.ops.object.hook_add_selob(use_bone=True)
            bpy.ops.object.hook_reset()
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

        # Create a small control shape
        bpy.ops.mesh.primitive_circle_add(radius=1, location=(0, 0, 3))
        custom_shape = bpy.context.object
        custom_shape.rotation_euler[0] = 1.5708
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        bpy.ops.object.modifier_add(type='SKIN')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.transform.skin_resize(value=(0.05, 0.05, 0.05))
        bpy.ops.object.mode_set(mode='OBJECT')
        custom_shape.modifiers["Skin"].use_smooth_shade = True
        custom_shape.name = f"Circle_{context.scene.fish_model_name}"
        custom_shape.hide_viewport = True
        custom_shape.hide_render = True
        
        for pose_bone in IK_armature.pose.bones:
            pose_bone.custom_shape = custom_shape
            
        bpy.ops.object.select_all(action='DESELECT')
        direction_empty = bpy.data.objects.new(f"DirectionControl_{context.scene.fish_model_name}", None)
        bpy.context.collection.objects.link(direction_empty)
        direction_empty.empty_display_type = 'SPHERE'
        com_bone = armature.pose.bones.get(keypoints[0])
        com_pos = armature.matrix_world @ com_bone.tail
        direction_empty.location = com_pos
        diameter = abs((armature.matrix_world @ com_bone.head - com_pos).x)
        direction_empty.scale = (diameter, diameter/2, diameter/2)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Recenter cursor
        bpy.context.scene.cursor.location = com_pos
        self.report({'INFO'}, f"Curve points: {com_bone}")

        # Apply origin and constraints
        for obj_name in [f"context.scene.fish_model_name", IK_armature.name, armature.name]:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=False)
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                constraint = obj.constraints.new(type='COPY_ROTATION')
                constraint.target = direction_empty
                constraint = obj.constraints.new(type='COPY_LOCATION')
                constraint.target = direction_empty

        
        bezier_curve.parent = direction_empty
        bezier_curve.matrix_parent_inverse = direction_empty.matrix_world.inverted()
        bpy.ops.object.select_all(action='DESELECT')
        direction_empty.location=(0,0,0)
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
    
        for eye in [left_eye, right_eye] if 'left_eye' in locals() and 'right_eye' in locals() else []:
                eye.rotation_euler[2] = 0

        return {'FINISHED'}

def fish_name_items(self, context):
    # List all mesh objects with names like "FishName_ID" or custom criteria
    return [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'MESH']

#--------Main class--------
class OBJECT_OT_addbones(bpy.types.Operator):
    """Add single fish model"""

    bl_idname = "obj.add_bones"
    bl_label = "Add bones to fish"
    
    fish_name: bpy.props.EnumProperty(
        name="Fish Model",
        description="Select a fish model",
        items=fish_name_items
    )
    
    keypoints: bpy.props.StringProperty(
        name="Keypoints",
        description="Comma-separated tracking keypoints",
        default=""
    )

    keypoint_locations: bpy.props.StringProperty(
        name="Keypoint Pos.",
        description="Comma-separated positions (0–1, include 1)",
        default=""
    )

    split_map: bpy.props.StringProperty(
        name="Segments",
        description="Key:Value pairs (e.g., COM:3,Caudal:4)",
        default=""
    )

    
    def invoke(self, context, event):
        # Trigger the popup that lets user enter fish_id
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        context.scene.fish_model_name = ""
        context.scene.keypoints=""
        context.scene.keypoint_locations=""
        context.scene.split_map=""

        context.scene.fish_model_name = self.fish_name
        context.scene.keypoints=self.keypoints
        context.scene.keypoint_locations=self.keypoint_locations
        context.scene.split_map=self.split_map
        
        fish_obj = bpy.data.objects.get(context.scene.fish_model_name)
        bpy.ops.object.select_all(action='DESELECT')
        fish_obj.select_set(True)
        context.view_layer.objects.active = fish_obj
        bpy.ops.obj.posefish('EXEC_DEFAULT')
        

        # Create or get fish-specific collection
        collection_name = f"{context.scene.fish_model_name}"
        fish_coll = bpy.data.collections.get(collection_name)
        if not fish_coll:
            fish_coll = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(fish_coll)

        new_object = bpy.data.objects.get(f"DirectionControl_{context.scene.fish_model_name}")
        if new_object:
            if new_object.name not in fish_coll.objects:
                fish_coll.objects.link(new_object)
                # Unlink from any other collections
            for coll in new_object.users_collection:
                if coll != fish_coll:
                    coll.objects.unlink(new_object)
        
        new_object = bpy.data.objects.get(f"BodyCurve_{context.scene.fish_model_name}")
        if new_object:
            if new_object.name not in fish_coll.objects:
                fish_coll.objects.link(new_object)
                # Unlink from any other collections
            for coll in new_object.users_collection:
                if coll != fish_coll:
                    coll.objects.unlink(new_object)
        
        new_object = bpy.data.objects.get(f"FishArmature_{context.scene.fish_model_name}")
        if new_object:
            if new_object.name not in fish_coll.objects:
                fish_coll.objects.link(new_object)
                # Unlink from any other collections
            for coll in new_object.users_collection:
                if coll != fish_coll:
                    coll.objects.unlink(new_object)
        
        new_object = bpy.data.objects.get(f"IKArmature_{context.scene.fish_model_name}")
        if new_object:
            if new_object.name not in fish_coll.objects:
                fish_coll.objects.link(new_object)
                # Unlink from any other collections
            for coll in new_object.users_collection:
                if coll != fish_coll:
                    coll.objects.unlink(new_object)
        
        
        new_object = bpy.data.objects.get(f"Circle_{context.scene.fish_model_name}")
        if new_object:
            if new_object.name not in fish_coll.objects:
                fish_coll.objects.link(new_object)
                # Unlink from any other collections
            for coll in new_object.users_collection:
                if coll != fish_coll:
                    coll.objects.unlink(new_object)
        
        return {'FINISHED'}

#--------------Register--------------
def register():

    bpy.utils.register_class(POSE_OT_posefish)
    bpy.utils.register_class(OBJECT_OT_addbones)

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
    bpy.types.Scene.keypoints = bpy.props.StringProperty(name="Keypoints")
    bpy.types.Scene.keypoint_locations = bpy.props.StringProperty(name="Keypoint locations")
    bpy.types.Scene.split_map = bpy.props.StringProperty(name="Keypoint segments")
   
def unregister():
    bpy.utils.unregister_class(POSE_OT_posefish)
    bpy.utils.unregister_class(OBJECT_OT_addbones)

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

    del bpy.types.Scene.keypoints 
    del bpy.types.Scene.keypoint_locations 
    del bpy.types.Scene.split_map 




   
