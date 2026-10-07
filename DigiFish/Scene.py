import bpy
import os

# --------- Add blender scene ---------
class OBJECT_OT_importscene(bpy.types.Operator):
    """Import a scene from a .blend file"""
    bl_idname = "obj.importscene"
    bl_label = "Import .blend Collection"

    filepath: bpy.props.StringProperty(
        name="Blend File Path",
        subtype='FILE_PATH',
    )
    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        default="Scene",
        description="Name of the collection to append"
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Select .blend file and collection to append")
        layout.prop(self, "filepath")
        layout.prop(self, "collection_name")

    def execute(self, context):
        scene = bpy.context.scene
        scene.cursor.location = (0, 0, 0)
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 0.01
        scene.unit_settings.length_unit = 'CENTIMETERS'
        print("Scene defaults applied")
        filepath = bpy.path.abspath(self.filepath)
        collection_name = self.collection_name

        # Path inside the .blend file to the collection datablock
        collection_path = f"Collection/{collection_name}"

        # Append collection
        try:
            bpy.ops.wm.append(
                filepath=collection_path,
                directory=os.path.join(filepath, "Collection"),
                filename=collection_name,
                link=False,
                autoselect=True,
                active_collection=True,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Failed to append collection '{collection_name}': {e}")
            return {'CANCELLED'}
        
        
        context.scene.sceneimport=self.filepath
            
        self.report({'INFO'}, f"Appended collection '{collection_name}' from {filepath}")
        return {'FINISHED'}

# --------- Add reference scene image ---------

class OBJECT_OT_addrefimage(bpy.types.Operator):
    """Add scene reference image"""
    bl_idname = "obj.addref"
    bl_label = "Add reference image"

    image: bpy.props.StringProperty(
        name="Image path",
        subtype='FILE_PATH'
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="⚠️ Ensure image size is same dimensions as video")
        layout.prop(self, "image")

    def execute(self, context):
        # Load image and add empty image object
        full_path = bpy.path.abspath(self.image)  
        bpy.ops.object.empty_image_add(filepath=full_path)
        ref_obj = context.active_object
        ref_obj.name = "SceneReferenceImage"

        # Scale based on scene properties
        video_w = context.scene.videowidth * context.scene.pixelconvert
        video_h = context.scene.videoheight * context.scene.pixelconvert
        
        image = ref_obj.data

        ref_obj.scale = (video_w, video_w, 1)
        ref_obj.empty_display_size = 1

        # Position the image so the bottom-left corner is at the origin
        ref_obj.location = (video_w / 2, video_h / 2, 0)
        #ref_obj.rotation_euler[0] = 1.5708  # Rotate to lie flat in XY plane

        # Move object to "Scene" collection
        master_collection = bpy.context.scene.collection
        scene_collection = bpy.data.collections.get("Scene")
        if scene_collection is None:
            scene_collection = bpy.data.collections.new("Scene")
            master_collection.children.link(scene_collection)
        elif scene_collection.name not in [c.name for c in master_collection.children]:
            master_collection.children.link(scene_collection)
            
        for coll in list(ref_obj.users_collection):
            coll.objects.unlink(ref_obj)

        # THEN link it to "Scene" collection
        scene_collection.objects.link(ref_obj)

        
        self.report({'INFO'}, "Scene image added.")
        return {'FINISHED'}




# --------- Add light to scene ---------
class OBJECT_OT_addlight(bpy.types.Operator):
    """Add light source"""
    bl_idname = "obj.addlight"
    bl_label = "Add light source"
    def execute(self, context):
        video_w = context.scene.videowidth * context.scene.pixelconvert
        video_h = context.scene.videoheight * context.scene.pixelconvert
        bpy.ops.object.light_add(type='AREA', radius=video_w, align='WORLD', location=(video_w/2, video_h/2, 80), scale=(1, 1, 1))
        light = context.active_object
        light.name = "Interactive_Light"
        
        bpy.context.space_data.shading.type = 'RENDERED'

        self.report({'INFO'}, f"Light added to scene")
        return {'FINISHED'}
    
class LightBrightnessPanel(bpy.types.Panel):
    """Panel for adjusting light brightness"""
    bl_label = "Light Settings"
    bl_idname = "VIEW3D_PT_light_brightness"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'DigiFish Light Control'

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'LIGHT' and obj.name.startswith("Interactive_")

    def draw(self, context):
        layout = self.layout
        obj = context.object
        light = obj.data

        layout.label(text="Brightness & Color:")
        layout.prop(light, "energy", slider=True)
        layout.prop(light, "color")

        layout.separator()
        layout.label(text="Light Position & Size:")
        layout.prop(obj, "location", index=2, text="Distance Away")  # Only Z
        layout.prop(light, "size_y", text="Size")
        
        layout.separator()
        layout.label(text="Shadow Settings:")
        layout.prop(light, "use_shadow", text="Cast Shadows")

# --------- Add water to scene ---------

direction_items = [
    ('+X', '+X', 'Flow along positive X axis'),
    ('-X', '-X', 'Flow along negative X axis'),
    ('+Y', '+Y', 'Flow along positive Y axis'),
    ('-Y', '-Y', 'Flow along negative Y axis'),
    ('+Z', '+Z', 'Flow along positive Z axis'),
    ('-Z', '-Z', 'Flow along negative Z axis'),
]


def update_water_flow(self, context):
    obj = self
    mat = obj.active_material or (obj.data.materials[0] if obj.data.materials else None)
    if not mat or not mat.use_nodes:
        return

    mapping_node = mat.node_tree.nodes.get("Mapping")
    if not mapping_node:
        return

    # X component of Mapping Node location input vector
    data_path = f'nodes["{mapping_node.name}"].inputs[1].default_value'

    # Clamp user speed 0-100
    user_speed = max(0, min(obj.water_flow_speed, 100))

    # Frames per second
    fps = context.scene.render.fps if context else 30

    # Duration of one full cycle at max speed (seconds)
    cycle_duration_sec = 3.0

    # Calculate speed per frame for driver (how much X moves per frame)
    speed_per_frame = (1.0 / (cycle_duration_sec * fps)) * (user_speed / 100)

    axis_map = {'+X': 0, '-X': 0, '+Y': 1, '-Y': 1, '+Z': 2, '-Z': 2}
    direction_sign = {'+X': 1, '-X': -1, '+Y': 1, '-Y': -1, '+Z': 1, '-Z': -1}

    direction = obj.water_flow_direction
    dir_index = axis_map.get(direction, 0)
    sign = direction_sign.get(direction, 1)

    # Ensure animation data and driver exist
    anim_data = mat.node_tree.animation_data_create()

    # Remove drivers on other axes if they exist
    for i in range(3):
        if i != dir_index:
            data_path_other = f'nodes["{mapping_node.name}"].inputs[1].default_value'
            for drv in anim_data.drivers:
                if drv.data_path == data_path_other and drv.array_index == i:
                    anim_data.drivers.remove(drv)

    # Create or reuse driver on correct axis
    fcurve = None
    for driver in anim_data.drivers:
        if driver.data_path == data_path and driver.array_index == dir_index:
            fcurve = driver
            break
    if not fcurve:
        fcurve = anim_data.drivers.new(data_path=data_path, index=dir_index)

    driver = fcurve.driver
    driver.type = 'SCRIPTED'
    driver.expression = "(frame * speed) % 1.0"

    # Create or update driver variable
    if len(driver.variables) == 0:
        var = driver.variables.new()
    else:
        var = driver.variables[0]

    var.name = "speed"
    var.type = 'SINGLE_PROP'
    target = var.targets[0]
    target.id_type = 'OBJECT'
    target.id = obj
    target.data_path = '["water_flow_speed_driver"]'

    obj["water_flow_speed_driver"] = sign * speed_per_frame
    obj.water_flow_speed = user_speed

class OBJECT_OT_addwater(bpy.types.Operator):
    bl_idname = "obj.addwater"
    bl_label = "Add Water Volume"

    depth: bpy.props.IntProperty(name="Water depth (cm)", default=10)
    flow_speed: bpy.props.FloatProperty(
        name="Flow Speed",
        default=10,
        min=0,
        max=100,
        description="Speed of water flow animation"
    )

    water_flow_direction: bpy.props.EnumProperty(
            name="Water Flow Direction",
            description="Direction of water flow for mapping animation",
            items=direction_items,
            default='+X',
        )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        obj = context.object
        layout.prop(self, "depth")
        layout.prop(self, "water_flow_direction")
        layout.prop(self, "flow_speed")

    def execute(self, context):
        video_w = context.scene.get("videowidth", 1920) * context.scene.get("pixelconvert", 1)
        video_h = context.scene.get("videoheight", 1080) * context.scene.get("pixelconvert", 1)
        w_sf = video_w / self.depth
        h_sf = video_h / self.depth

        bpy.ops.mesh.primitive_cube_add(
            size=self.depth + 2,
            location=(video_w / 2, video_h / 2, (self.depth / 2) - 2),
            scale=(w_sf, w_sf, 1)
        )
        cube = context.active_object
        cube.name = "Water"

        mat = bpy.data.materials.new(name="WaterVolumeMaterial")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear existing nodes
        for node in nodes:
            nodes.remove(node)

        # Create nodes
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        volume_node = nodes.new(type='ShaderNodeVolumePrincipled')
        multiply_node = nodes.new(type="ShaderNodeMath")
        multiply_node.operation = "MULTIPLY"
        multiply_node.name = "Multiply"
        colourramp = nodes.new(type="ShaderNodeValToRGB")
        colourramp.name = "WaterColorRamp"
        noise_node = nodes.new(type="ShaderNodeTexNoise")
        mapping_node = nodes.new(type="ShaderNodeMapping")
        mapping_node.name="Mapping"
        texture_node = nodes.new(type="ShaderNodeTexCoord")

        # Position nodes
        output_node.location = (400, 0)
        volume_node.location = (0, 0)
        multiply_node.location = (-200, 0)
        colourramp.location = (-400, 0)
        noise_node.location = (-600, 0)
        mapping_node.location = (-800, 0)
        texture_node.location = (-1000, 0)

        # Setup node inputs
        volume_node.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        volume_node.inputs["Anisotropy"].default_value = 0.6

        multiply_node.inputs[1].default_value = 1  # density factor

        # Setup ColorRamp
        ramp = colourramp.color_ramp
        while len(ramp.elements) > 2:
            ramp.elements.remove(ramp.elements[-1])

        
        noise_node.name = "WaterNoise"
        noise_node.inputs["Detail"].default_value = 40
        noise_node.inputs["Roughness"].default_value = 0.8


        # Set values of remaining elements
        ramp.elements[0].position = 0.0
        ramp.elements[0].color = (0.0, 0.0, 0.0, 1)

        ramp.elements[1].position = 0.15
        ramp.elements[1].color = (0.1, 0.4, 0.6, 1)
        e3 = ramp.elements.new(0.85)
        e3.color = (0.02, 0.1, 0.2, 1)
        ramp.elements[0].position = 0.4  # Move black closer to white
        ramp.elements[1].position = 0.9
        ramp.elements[0].color = (0, 0, 0, 1)   # Keep black
        ramp.elements[1].color = (0.2, 0.5, 0.6, 1)  # Lower intensity

        ramp.interpolation = 'EASE'

        # Links
        links.new(colourramp.outputs["Color"], multiply_node.inputs[0])
        links.new(multiply_node.outputs["Value"], volume_node.inputs["Density"])
        links.new(volume_node.outputs["Volume"], output_node.inputs["Volume"])
        links.new(noise_node.outputs["Fac"], colourramp.inputs["Fac"])
        links.new(mapping_node.outputs["Vector"], noise_node.inputs["Vector"])
        links.new(texture_node.outputs["Object"], mapping_node.inputs["Vector"])

        # Assign material
        cube.data.materials.append(mat)

        # Assign property and call update to setup driver

        cube.water_flow_direction = self.water_flow_direction 
        cube.water_flow_speed = max(0, min(self.flow_speed, 100))
        update_water_flow(cube, context)

        return {'FINISHED'}


class WaterPanel(bpy.types.Panel):
    bl_label = "Water Turbidity"
    bl_idname = "VIEW3D_PT_water_turbidity"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'DigiFish Water Control'

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.name.startswith("Water")

    def draw(self, context):
        layout = self.layout
        obj = context.object

        mat = obj.active_material or (obj.data.materials[0] if obj.data.materials else None)
        if not mat or not mat.use_nodes:
            layout.label(text="No volume material found.")
            return

        nodes = mat.node_tree.nodes
        volume_node = nodes.get("Principled Volume")
        colorramp = nodes.get("WaterColorRamp")
        multiply_node = nodes.get('Multiply')

        if volume_node:
            layout.prop(multiply_node.inputs[1], "default_value", text="Density")
            layout.prop(volume_node.inputs["Anisotropy"], "default_value", text="Anisotropy")
            layout.prop(volume_node.inputs["Color"], "default_value", text="Water Color")
        else:
            layout.label(text="No Principled Volume node found.")

        noise_node = nodes.get("WaterNoise")
        if noise_node:
            layout.label(text="Noise Texture Settings:")
            layout.prop(noise_node.inputs["Detail"], "default_value", text="Detail")
            layout.prop(noise_node.inputs["Roughness"], "default_value", text="Roughness")

        if colorramp:
            layout.label(text="Turbidity Contrast:")
            layout.template_color_ramp(colorramp, "color_ramp", expand=True)
        else:
            layout.label(text="No ColorRamp node found.")

        layout.separator()
        layout.label(text="Flow Animation Speed:")
        layout.prop(obj, "water_flow_speed")

#--------------Register--------------
def register():
    bpy.utils.register_class(WaterPanel)
    bpy.utils.register_class(OBJECT_OT_addwater)
    bpy.utils.register_class(OBJECT_OT_addlight)
    bpy.utils.register_class(LightBrightnessPanel)
    bpy.utils.register_class(OBJECT_OT_importscene)
    bpy.utils.register_class(OBJECT_OT_addrefimage)

    bpy.types.Object.water_flow_speed = bpy.props.FloatProperty(
        name="Water Flow Speed",
        description="Speed of water flow (0-100)",
        default=10,
        min=0,
        max=100,
        update=update_water_flow
    )

    bpy.types.Object.water_flow_direction = bpy.props.EnumProperty(
        name="Water Flow Direction",
        description="Direction of water flow for mapping animation",
        items=direction_items,
        default='+X',
        update=update_water_flow
    )

def unregister():
    bpy.utils.unregister_class(WaterPanel)
    bpy.utils.unregister_class(OBJECT_OT_addwater)
    del bpy.types.Object.water_flow_speed
    bpy.utils.unregister_class(OBJECT_OT_addlight)
    bpy.utils.unregister_class(LightBrightnessPanel)
    bpy.utils.unregister_class(OBJECT_OT_importscene)
    del bpy.types.Object.water_flow_direction
    bpy.utils.unregister_class(OBJECT_OT_addrefimage)