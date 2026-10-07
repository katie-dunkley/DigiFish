bl_info = {
    "name": "DigiFish",
    "author": "Katie Dunkley",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "category": "Animation"
}



import sys, subprocess, importlib, site

def ensure_module(packageName):
    """Install and import a module into Blender's Python."""
    try:
        return __import__(packageName)
    except ImportError:
        print(f"Installing '{packageName}'...")
        python_exe = sys.executable

        # ensure pip exists
        if importlib.util.find_spec("pip") is None:
            subprocess.check_call([python_exe, "-m", "ensurepip", "--upgrade"])

        # upgrade pip
        subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([python_exe, "-m", "pip", "install", "--user", packageName])

        # add user site-packages to sys.path
        if site.USER_SITE not in sys.path:
            sys.path.append(site.USER_SITE)

        return __import__(packageName)


def safe_ensure_module(packageName):
    try:
        return ensure_module(packageName)
    except Exception as e:
        print(f"Failed to install/import {packageName}: {e}")
        return None

safe_ensure_module("pandas")
safe_ensure_module("scipy")
safe_ensure_module("statsmodels")
safe_ensure_module("scikit-misc")



import bpy


from . import panel
from . import AddFish
from . import Animate
from . import AddBones
from . import SetupScene
from . import Scene
from . import MultiFish
from . import Render
from . import eeVR



def setup_scene_defaults():
    scene = bpy.context.scene
    scene.cursor.location = (0, 0, 0)
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.01
    scene.unit_settings.length_unit = 'CENTIMETERS'
    print("Scene defaults applied")
    return None  # stop timer

def register():
    bpy.app.timers.register(setup_scene_defaults)
    panel.register()
    SetupScene.register()
    AddFish.register()
    AddBones.register()
    Animate.register()
    Scene.register()
    MultiFish.register()
    Render.register()
    eeVR.register()
    


def unregister():
    panel.unregister()
    SetupScene.unregister()
    AddFish.unregister()
    AddBones.unregister()
    Animate.unregister()
    Scene.unregister()
    MultiFish.unregister()
    Render.unregister()
    eeVR.unregister()
    
