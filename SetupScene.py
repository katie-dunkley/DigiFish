import bpy

#--------Clear scene--------
class OBJECT_OT_clear_scene(bpy.types.Operator):
    """Remove all objects etc from the scene"""
    bl_idname = "obj.clear_scene"
    bl_label = "Clear Scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Ensure we're in Object mode (needed for deleting)
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Unhide all objects (both viewport and render)
        for obj in bpy.data.objects:
            obj.hide_set(False)           # Viewport visibility
            obj.hide_viewport = False     # For older versions
            obj.hide_render = False

        # Delete all objects in the scene
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

        # Safely purge unused data blocks
        def purge(data_collection):
            for block in list(data_collection): 
                if block.users == 0:
                    data_collection.remove(block)

        purge(bpy.data.meshes)
        purge(bpy.data.lights)
        purge(bpy.data.cameras)
        purge(bpy.data.armatures)
        purge(bpy.data.materials)
        purge(bpy.data.images)
        
        self.report({'INFO'}, "Scene cleared successfully.")
        return {'FINISHED'}

#--------Add general details--------
class INPUT_OT_add_user_info(bpy.types.Operator):
    """Add panel that asks for user info"""
    bl_idname = "obj.add_info_dialog"
    bl_label = "Add Fish Info"
    bl_description = "Enter general info about the filming and pixel conversion."


    # -------------------- VIDEO PROPERTIES --------------------
    videowidth: bpy.props.IntProperty(
        name="Video width (px)", description="Width of video", default=2704
    )
    videoheight: bpy.props.IntProperty(
        name="Video height (px)", description="Height of video", default=1520
    )
    pixelconvert: bpy.props.FloatProperty(
        name="Pixel to cm ratio", description="Pixel conversion", default=0.0500, precision=4
    )
    
    maxfps:bpy.props.FloatProperty(
        name="Max fps", description="Frames per second", default=240
    )

    # -------------------- UI HANDLERS --------------------
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        # Grouped for logical readability
        box_vid = layout.box()
        box_vid.label(text="Video Settings")
        box_vid.prop(self, "videowidth")
        box_vid.prop(self, "videoheight")
        box_vid.prop(self, "pixelconvert")
        box_vid.prop(self, "maxfps")

    def execute(self, context):
        # Store to scene for persistent access
        props = {
            "videowidth": self.videowidth,
            "videoheight": self.videoheight,
            "pixelconvert": self.pixelconvert
        }

        for key, value in props.items():
            setattr(context.scene, key, value)

        self.report({'INFO'}, "Fish info added to scene")
        return {'FINISHED'}

#--------------Register--------------
def register():
    bpy.utils.register_class(OBJECT_OT_clear_scene)
    bpy.utils.register_class(INPUT_OT_add_user_info)

    bpy.types.Scene.videowidth = bpy.props.FloatProperty(name="Video width", default=2704)
    bpy.types.Scene.videoheight = bpy.props.FloatProperty(name="Video height", default=1520)
    bpy.types.Scene.pixelconvert = bpy.props.FloatProperty(name="Pixel convert", default=0.05)
    bpy.types.Scene.sceneimport = bpy.props.StringProperty(name="Scene import filepath", default="")
    bpy.types.Scene.maxfps = bpy.props.FloatProperty(name="Max frames per second", default=240)
    
def unregister():
    bpy.utils.unregister_class(OBJECT_OT_clear_scene)
    bpy.utils.unregister_class(INPUT_OT_add_user_info)

    del bpy.types.Scene.videowidth 
    del bpy.types.Scene.videoheight
    del bpy.types.Scene.pixelconvert 
    del bpy.types.Scene.sceneimport
    del bpy.types.Scene.maxfps
    