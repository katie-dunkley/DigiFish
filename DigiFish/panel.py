
import bpy


from . import SetupScene, AddFish, AddBones, Animate, Scene, MultiFish, eeVR

class VIEW3D_PT_my_custom_panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DigiFish"
    bl_label = "DigiFish Steps"

    def draw(self, context):
        layout = self.layout

        # --- Setup Section ---
        box_setup = layout.box()
        box_setup.label(text="Setup", icon='SCENE_DATA')
        box_setup.operator("obj.clear_scene", text="Clear scene", icon='TRASH')
        box_setup.operator("obj.add_info_dialog", text="Add info", icon='IMPORT')

        # --- Scene Setup ---
        box_scene = layout.box()
        box_scene.label(text="Scene", icon='SCENE_DATA')
        box_scene.operator("obj.importscene", text="Add scene model (.blend)", icon="APPEND_BLEND")
        box_scene.operator("obj.addref", text="Add scaled reference image", icon="APPEND_BLEND")
        box_scene.operator("obj.addlight", text="Add light source", icon="OUTLINER_DATA_LIGHT")
        box_scene.operator("obj.addwater", text="Add water", icon="MOD_OCEAN")
        
        
        # --- Add model ---
        box_scene = layout.box()
        box_scene.label(text="Add model", icon='BONE_DATA')
        box_scene.operator("obj.add_singlefish",text="Add single fish")

        
        # --- Animate! ---
        box_scene = layout.box()
        box_scene.label(text="Animate model", icon='ANIM_DATA')
        box_scene.operator("obj.add_bones", text="Add bones", icon='BONE_DATA')
        box_scene.operator("obj.animatefish", text="Animate fish", icon='ANIM_DATA')
        
         # --- MultiFish ---
        box_scene = layout.box()
        box_scene.label(text="Add multiple fish", icon='BONE_DATA')
        box_scene.operator("obj.add_multi", text="Add & Animate")

        # --- Scene Cameras ---
        box_scene = layout.box()
        box_scene.label(text="Render animation", icon='SEQUENCE')
        box_scene.operator("obj.addcamera", text="Add camera", icon="SCENE")
        box_scene.operator("obj.select_active_camera", text="Select camera", icon="SCENE")
        box_scene.operator("obj.rendervideo", text="Render video - camera", icon="SCENE")
        box_scene.operator("obj.rendervideoeye", text="Render video - eye view", icon="SCENE")




def register():
    bpy.utils.register_class(VIEW3D_PT_my_custom_panel)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_my_custom_panel)


