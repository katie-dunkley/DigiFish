import json

import sys, subprocess
import bpy

import sys, subprocess, importlib.util

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
from mathutils import Vector, Euler
from math import dist
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess
from skmisc.loess import loess

from scipy.interpolate import make_interp_spline
from scipy.interpolate import BSpline


track_data_store = {}
eyetrack_data_store={}
#-------Helper functions-------
def fish_name_items_armatures(self, context):
    # List all mesh objects that are influenced by an armature
    items = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        has_armature_modifier = any(mod.type == 'ARMATURE' for mod in obj.modifiers)
        is_parented_to_armature = obj.parent and obj.parent.type == 'ARMATURE'

        if has_armature_modifier or is_parented_to_armature:
            items.append((obj.name, obj.name, ""))
    return items

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

def ensure_z_columns(data, keypoints):
    if not data:
        return data  # Nothing to do for empty data

            # Collect all columns from the first row as reference
    existing_cols = set(data[0].keys())

    for kp in keypoints:
        z_col = f"{kp}.z"
        if z_col not in existing_cols:
            for row in data:
                row[z_col] = 0

    return data

def smooth_keypoint_xyz(data, keypoint_name, window=3, var_threshold=20, span=0.05, max_value=np.inf):
    def loess(x, y, span):
        return lowess(y, x, frac=span, return_sorted=False)

    def smooth_and_interpolate(col):
        # Extract values
        values = [float(row.get(col, np.nan)) if isinstance(row.get(col), (int, float)) else np.nan for row in data]

        # Compute rolling variance
        rolling_var = []
        for i in range(len(values)):
            start = max(0, i - window // 2)
            end = min(len(values), i + window // 2 + 1)
            window_vals = [v for v in values[start:end] if not np.isnan(v)]
            var = np.var(window_vals) if window_vals else np.nan
            rolling_var.append(var)

        # Filter high-variance points
        for i, var in enumerate(rolling_var):
            if not np.isnan(var) and var > var_threshold:
                values[i] = np.nan

        # Prepare for smoothing
        x_vals = [row['frame_idx'] for row in data]
        y_vals = values.copy()

        valid_idx = [i for i, v in enumerate(y_vals) if not np.isnan(v)]
        smoothed_vals = [np.nan] * len(data)

        if valid_idx:
            x_valid = np.array([x_vals[i] for i in valid_idx])
            y_valid = np.array([y_vals[i] for i in valid_idx])
            smoothed = loess(x_valid, y_valid, span=span)
            smoothed = np.minimum(smoothed, max_value)

            # Fill smoothed values
            for j, i in enumerate(valid_idx):
                smoothed_vals[i] = smoothed[j]

            # Interpolate over NaNs where possible
            smoothed_array = np.array(smoothed_vals)
            x_np = np.array(x_vals)

            mask = ~np.isnan(smoothed_array)
            if np.sum(mask) >= 2:  # Need at least 2 points to interpolate
                interp_vals = np.interp(
                    x_np, x_np[mask], smoothed_array[mask], left=np.nan, right=np.nan
                )
                smoothed_vals = interp_vals.tolist()

        # Store results
        for i, row in enumerate(data):
            row[f"{col}_smoothed"] = smoothed_vals[i]

    # Process x, y, z
    for axis in ['x', 'y', 'z']:
        col = f"{keypoint_name}.{axis}"
        if any(col in row for row in data):
            smooth_and_interpolate(col)

    return data

def extend_vector_back(a, b, d):
    """Extend backwards from point `a` in the direction a → b by distance d (XY only)."""
    if any(x is None for x in a + b):
        return [None, None]
    direction = [b[0] - a[0], b[1] - a[1]]  # Direction a → b
    length = math.hypot(*direction)
    if length == 0:
        return a  # No direction to extend
    unit_vector = [direction[0] / length, direction[1] / length]
    return [a[0] - d * unit_vector[0], a[1] - d * unit_vector[1]]

def extend_vector_forward(a, b, d):
    """Extend forwards from point `b` in the direction a → b by distance d (XY only)."""
    if any(x is None for x in a + b):
        return [None, None]
    direction = [b[0] - a[0], b[1] - a[1]]
    length = math.hypot(*direction)
    if length == 0:
        return a
    unit_vector = [direction[0] / length, direction[1] / length]
    return [b[0] + d * unit_vector[0], b[1] + d * unit_vector[1]]

def extend_keypoint_segments(data, keypoints, suffix="", d=50):
    """Apply extension to each pair of keypoints in the data."""
    for i in range(len(keypoints) - 1):
        k1, k2 = keypoints[i], keypoints[i + 1]
        suffix_str = f"_{suffix}" if suffix else ""
        x_col1, y_col1 = f"{k1}.x{suffix_str}", f"{k1}.y{suffix_str}"
        x_col2, y_col2 = f"{k2}.x{suffix_str}", f"{k2}.y{suffix_str}"
        new_x_col = f"{k1}{k2}_extended.x{suffix_str}"
        new_y_col = f"{k1}{k2}_extended.y{suffix_str}"

        for row in data:
            try:
                a = [float(row[x_col1]), float(row[y_col1])]
                b = [float(row[x_col2]), float(row[y_col2])]
            except (KeyError, ValueError, TypeError):
                a = b = [None, None]

            new_point = extend_vector_forward(a, b, d)
            row[new_x_col] = new_point[0]
            row[new_y_col] = new_point[1]

    return data

def smooth_angle_columns(df, angle_col1, angle_col2, window, var_threshold, span=0.05):
    def loess(x, y, span):
        return lowess(y, x, frac=span, return_sorted=False)

    def smooth_and_interpolate(col):
        values = pd.to_numeric(df[col], errors='coerce')

        # Compute rolling variance
        rolling_var = values.rolling(window=window, center=True, min_periods=1).var()

        # Filter high-variance points
        values[rolling_var > var_threshold] = np.nan

        x_vals = df["frame_idx"].values
        y_vals = values.values

        valid_mask = ~np.isnan(y_vals)
        smoothed_vals = np.full_like(y_vals, np.nan, dtype=np.float64)

        if np.sum(valid_mask) >= 2:
            x_valid = x_vals[valid_mask]
            y_valid = y_vals[valid_mask]
            smoothed = loess(x_valid, y_valid, span=span)

            # Assign smoothed values back
            smoothed_vals[valid_mask] = smoothed

            # Interpolate across NaNs
            interp_vals = np.interp(
                x_vals, x_vals[valid_mask], smoothed_vals[valid_mask], left=np.nan, right=np.nan
            )
            df[f"{col}_smoothed"] = interp_vals
        else:
            df[f"{col}_smoothed"] = np.nan

    for col in [angle_col1, angle_col2]:
        if col in df.columns:
            smooth_and_interpolate(col)

    return df

def angle_at_vertex_signed(a, b, c):
            # Create vectors BA and BC
            ba = [a[0] - b[0], a[1] - b[1]]
            bc = [c[0] - b[0], c[1] - b[1]]

            # Normalize vectors
            ba_len = math.hypot(ba[0], ba[1])
            bc_len = math.hypot(bc[0], bc[1])
            if ba_len == 0 or bc_len == 0:
                return None  # Avoid division by zero
            
            ba_norm = [ba[0] / ba_len, ba[1] / ba_len]
            bc_norm = [bc[0] / bc_len, bc[1] / bc_len]

            # Dot product for angle magnitude
            dot_prod = ba_norm[0] * bc_norm[0] + ba_norm[1] * bc_norm[1]
            # Clamp to avoid domain errors in acos
            cos_theta = max(min(dot_prod, 1), -1)
            angle_rad = math.acos(cos_theta)

            # 2D cross product to determine sign
            cross_prod = ba_norm[0] * bc_norm[1] - ba_norm[1] * bc_norm[0]

            signed_angle_deg = math.degrees(angle_rad) * math.copysign(1, cross_prod)
            return signed_angle_deg

def keypoint_to_keypoint_before(data, keypoints, suffix="", d=50):

            def find_column_with_terms(columns, terms):
                return [col for col in columns if all(term in col for term in terms)]

            n = len(keypoints)
            #self.report({'INFO'}, f"{n}")
            all_columns = data[0].keys()

            # This second extended vector is fixed: between keypoints[0] and keypoints[1]
            fixed_base = keypoints[0]
            fixed_tip = keypoints[1]
            
            fixed_x_matches = find_column_with_terms(all_columns, [fixed_base, fixed_tip, ".x"])
            fixed_y_matches = find_column_with_terms(all_columns, [fixed_base, fixed_tip, ".y"])

            if not fixed_x_matches or not fixed_y_matches:
                 raise ValueError(f"Extended columns not found for keypoint pair: {fixed_base}, {fixed_tip}")

            fixed_x = fixed_x_matches[0]
            fixed_y = fixed_y_matches[0]


            for i in range(n - 2):
                k1 = keypoints[i + 2]  # point before vertex
                k2 = keypoints[i + 1]  # vertex point
                k_base = keypoints[i]  # used for dynamic extended vector

                suff = f"_{suffix}" if suffix else ""
                

                x_col1 = f"{k1}.x{suff}"
                y_col1 = f"{k1}.y{suff}"
                x_col2 = f"{k2}.x{suff}"
                y_col2 = f"{k2}.y{suff}"

                # Dynamic extended vector for each triplet
                k3_dyn_x_matches = find_column_with_terms(all_columns, [k_base, k2, ".x"])
                k3_dyn_y_matches = find_column_with_terms(all_columns, [k_base, k2, ".y"])

                if not k3_dyn_x_matches or not k3_dyn_y_matches:
                    raise ValueError(f"Extended columns not found for keypoint: {k_base} and {k2}")

                k3_dyn_x = k3_dyn_x_matches[0]
                k3_dyn_y = k3_dyn_y_matches[0]

                angle_col_dynamic = f"Angle_{k1}_to_{k2}_to_{k_base}{k2}extended"
                angle_col_fixed = f"Angle_{k1}_to_{fixed_tip}_to_{fixed_base}{fixed_tip}extended"

                for row in data:
                    try:
                        prev = [float(row[x_col1]), float(row[y_col1])]
                        curr = [float(row[x_col2]), float(row[y_col2])]

                        # Dynamic extended point
                        dyn_next = [float(row[k3_dyn_x]), float(row[k3_dyn_y])]
                        angle_dynamic = angle_at_vertex_signed(dyn_next,prev, curr)

                        # Fixed extended point from keypoints[0] to keypoints[1]
                        fixed_next = [float(row[fixed_x]), float(row[fixed_y])]
                        x_col2=f"{keypoints[1]}.x{suff}"
                        y_col2=f"{keypoints[1]}.y{suff}"
                        anchor=[float(row[x_col2]), float(row[y_col2])]
                        x_col1 = f"{k1}.x{suff}"
                        y_col1 = f"{k1}.y{suff}"
                        point=[float(row[x_col1]), float(row[y_col1])]
                        angle_fixed = angle_at_vertex_signed(fixed_next, anchor, point)

                    except (KeyError, ValueError, TypeError):
                        angle_dynamic = None
                        angle_fixed = None

                    row[angle_col_dynamic] = angle_dynamic
                    row[angle_col_fixed] = angle_fixed

            return data

def auto_smooth_window(track_data, fps, desired_secs=0.1):
    """
    Automatically compute smoothing window and span for keypoints based on fps.
    The window is in frames corresponding to the desired smoothing time.
    If the dataset is too short, the window shrinks automatically.

    Args:
        track_data: list of dicts, each dict contains keypoint coords like 'Head.x'
        fps: frames per second of the video
        keypoints: list of keypoint names
        desired_secs: desired smoothing timescale in seconds (default 0.1s)

    Returns:
        window: int, window in frames
        span: float, fraction of dataset
    """

    total_rows = len(track_data)

    # Compute window in frames based on desired smoothing time
    window = int(desired_secs * fps)
    if window % 2 == 0:
        window += 1  # force odd window for symmetry

    # Automatically shrink if dataset is too short
    window = min(window, total_rows)
    span = window / total_rows  # fraction of dataset

    # Store results for each row
    #for row in track_data:
     #   row["best_window"] = window
      #  row["best_span"] = span

    return window, span

def smooth_every_time_list(data, columns, fps, span_secs=0.5):
    import numpy as np
    from statsmodels.nonparametric.smoothers_lowess import lowess
    import pandas as pd

    # Detect input type
    if isinstance(data, pd.DataFrame):
        df = data.copy()
        frame_idx = df["frame_idx"].astype(float).to_numpy()

        for col in columns:
            if col not in df.columns:
                print(f"Skipping invalid column: {col}")
                continue

            df[col] = pd.to_numeric(df[col], errors="coerce")
            y_vals = df[col].astype(float).to_numpy()

            valid_mask = ~np.isnan(y_vals)

            if np.sum(valid_mask) < 2:
                smoothed_full = np.full_like(
                    frame_idx,
                    np.nan,
                    dtype=float
                )

            else:
                x_valid = frame_idx[valid_mask]
                y_valid = y_vals[valid_mask]

                if span_secs <= 0:

                    smoothed_full = np.interp(
                        frame_idx,
                        x_valid,
                        y_valid,
                        left=np.nan,
                        right=np.nan
                    )

                
                else:

                    span_points = max(
                        3,
                        int(span_secs * fps)
                    )

                    frac = span_points / np.sum(valid_mask)

                    smoothed = lowess(
                        y_valid,
                        x_valid,
                        frac=frac,
                        return_sorted=False
                    )

                    smoothed_full = np.interp(
                        frame_idx,
                        x_valid,
                        smoothed,
                        left=np.nan,
                        right=np.nan
                    )

            df[f"{col}_smoothed"] = smoothed_full

        return df


    

    elif isinstance(data, list) and all(
        isinstance(row, dict) for row in data
    ):

        all_cols = data[0].keys() if data else []

        dict_data = {
            col: [
                row.get(col, np.nan)
                for row in data
            ]
            for col in all_cols
        }



    elif isinstance(data, dict):

        dict_data = data
        all_cols = dict_data.keys()

    else:

        raise ValueError(
            "data must be a pandas DataFrame, "
            "list of dicts, or dict of lists"
        )


    if "frame_idx" not in dict_data:
        raise KeyError(
            "data must contain 'frame_idx'"
        )


    frame_idx = np.asarray(
        dict_data["frame_idx"],
        dtype=float
    )


    for col in columns:

        if col not in dict_data:
            print(f"Skipping invalid column: {col}")
            continue

        y_vals = np.asarray(
            dict_data[col],
            dtype=float
        )

        valid_mask = ~np.isnan(y_vals)


        if np.sum(valid_mask) < 2:

            smoothed_full = np.full_like(
                frame_idx,
                np.nan,
                dtype=float
            )

        else:

            x_valid = frame_idx[valid_mask]
            y_valid = y_vals[valid_mask]



            if span_secs <= 0:

                smoothed_full = np.interp(
                    frame_idx,
                    x_valid,
                    y_valid,
                    left=np.nan,
                    right=np.nan
                )



            else:

                span_points = max(
                    3,
                    int(span_secs * fps)
                )

                frac = span_points / np.sum(valid_mask)

                smoothed = lowess(
                    y_valid,
                    x_valid,
                    frac=frac,
                    return_sorted=False
                )

                smoothed_full = np.interp(
                    frame_idx,
                    x_valid,
                    smoothed,
                    left=np.nan,
                    right=np.nan
                )



        if isinstance(data, list):

            for i, row in enumerate(data):

                row[f"{col}_smoothed"] = (
                    smoothed_full[i]
                )

        else:

            dict_data[f"{col}_smoothed"] = (
                smoothed_full
            )


    return data


#--------Read data--------
class READ_data(bpy.types.Operator):
    """Read track and eyetrack data"""
    bl_idname = "obj.readdata"
    bl_label = "Read in data"

    def execute(self, context):

        #------------Track data------------
        abs_path = bpy.path.abspath(context.scene.trackdata_folder)
        track_data = read_csv(abs_path)
        if track_data:
            self.report({'INFO'}, f"Loaded {len(track_data)} rows from {context.scene.trackdata_folder}") 
        else:
            self.report({'WARNING'}, "No data loaded from CSV.")
            return {'CANCELLED'}
        
        upsampled = upsample_frame_data_all_columns(track_data, original_fps=int(context.scene.csvfps), target_fps=int(context.scene.maxfps))      
        
        keypoints = [k.strip() for k in context.scene.keypoints.split(',') if k.strip()]
        upsampled_zdata=ensure_z_columns(upsampled, keypoints)
        global track_data_store
        track_data_store['upsampled_zdata'] = upsampled_zdata
        context.scene.track_data_store = json.dumps(upsampled_zdata)
        
        #------------Eye track data------------
        val = context.scene.eyetrackdata_folder
        if val and val.strip().lower() != "nan" and val.strip() != "":
            abs_path = bpy.path.abspath(val)
            if abs_path:
                eyetrack_data = read_csv(abs_path)
                if eyetrack_data and context.scene.eyetrack_colnames:
                    eyecols = [k.strip() for k in context.scene.eyetrack_colnames.split(',') if k.strip()]
                    eyecols.insert(0, 'frame_idx')
                    filtered_eyetrack_data = [{k: row[k] for k in eyecols if k in row} for row in eyetrack_data]
                    upsampled = upsample_frame_data_all_columns(filtered_eyetrack_data, original_fps=int(context.scene.eyecsvfps), target_fps=int(context.scene.maxfps))      
                    global eyetrack_data_store
                    eyetrack_data_store['eyetrack_data'] = upsampled
                    context.scene.eyetrack_data_store = json.dumps(upsampled)
                else:
                    self.report({'WARNING'}, "No valid eye columns specified.")

                self.report({'INFO'}, f"Loaded {len(eyetrack_data)} rows from {val}") 
        else:
            self.report({'WARNING'}, "Eye data CSV is empty or invalid. Proceeding without eye data.")


        return {'FINISHED'}


#--------Posture body--------
class POSE_OT_bodypose(bpy.types.Operator):
    """Keyframe body posture"""
    bl_idname = "obj.bodypose"
    bl_label = "Keyframe body posture"
    
    def execute(self, context):

        # ----------------
        # Get data
        # ----------------
        keypoints = [k.strip() for k in context.scene.keypoints.split(',') if k.strip()]
        #global track_data_store
        #track_data = track_data_store.get('upsampled_zdata', [])
        track_data=json.loads(context.scene.track_data_store)

        # Ensure values are numeric or NaN
        for row in track_data:
            for key, val in row.items():
                if key != 'frame_idx':
                    try:
                        row[key] = float(val)
                    except (TypeError, ValueError):
                        row[key] = np.nan


        columnssmooth = [
            col for col in track_data[0].keys()
            if any(kp in col for kp in keypoints) and col.endswith((".x", ".y", ".z"))
        ]

        track_data = smooth_every_time_list(track_data, columnssmooth, context.scene.maxfps, span_secs=context.scene.smoothtime_posture)

        # ----------------
        # Extend vectors & calc angles
        # ----------------
        model_name = context.scene.fish_model_name
        armature = bpy.data.objects.get(f"FishArmature_{context.scene.fish_model_name}")
        IK_armature = bpy.data.objects.get(f"IKArmature_{context.scene.fish_model_name}")

        if not armature or not IK_armature:
            self.report({'ERROR'}, "Missing one or both armatures")
            return {'CANCELLED'}
       
        track_data = extend_keypoint_segments(track_data, keypoints, suffix="smoothed", d=50)
        track_data = keypoint_to_keypoint_before(track_data, keypoints=keypoints, suffix="smoothed", d=50)

        # ----------------
        # Calculate position blender fish 
        # ----------------
        head_bone = armature.pose.bones.get(keypoints[0])
        if not head_bone:
            self.report({'ERROR'}, "First keypoint not found")
            return {'CANCELLED'}
        head_pos = armature.matrix_world @ head_bone.head
        distance_data = []
        for pose_bone in IK_armature.pose.bones:
            ik_head_pos = IK_armature.matrix_world @ pose_bone.head
            distance = (head_pos - ik_head_pos).length
            dataname=pose_bone.name
            dataname=dataname[3:]
            distance_data.append([head_bone.name, dataname, distance])
        
        blender_dist=distance_data[0][2]

        for row in track_data:
            if any(
                row.get(f"{kp}.x") is None or row.get(f"{kp}.y") is None
                for kp in keypoints
            ):
                continue  # Skip this row if any .x or .y is None
            
            # Proceed with processing this row
            n = len(keypoints)
            
            for i in range(n - 2):
                k1 = keypoints[0]  # point before vertex
                k2 = keypoints[1]  # vertex point
                kpoint=keypoints[i+2] 
                
                x_k1 = f"{k1}.x_smoothed"
                y_k1 = f"{k1}.y_smoothed"
                x_k2 = f"{k2}.x_smoothed"
                y_k2 = f"{k2}.y_smoothed"
                x_kpoint=f"{kpoint}.x_smoothed"
                y_kpoint=f"{kpoint}.y_smoothed"
                
                try:
                    point_k1 = [row[x_k1], row[y_k1]]
                    point_k2 = [row[x_k2], row[y_k2]]
                    point_kpoint = [row[x_kpoint], row[y_kpoint]]

                    k1_k2_dist = dist(point_k1, point_k2)
                    kpoint_k1_k2_angle=angle_at_vertex_signed(point_k2, point_k1, point_kpoint) #A_DBC
                    kpoint_k2_k1_angle=angle_at_vertex_signed(point_kpoint, point_k2, point_k1) #A_DCB
                    k1_kpoint_k2_angle=angle_at_vertex_signed(point_k1, point_kpoint, point_k2) #A_BDC
                    if round(abs(kpoint_k2_k1_angle) + abs(kpoint_k1_k2_angle) + abs(k1_kpoint_k2_angle), 0) != 180:
                        print(round(abs(kpoint_k2_k1_angle) + abs(kpoint_k1_k2_angle) + abs(k1_kpoint_k2_angle), 0))
                        break
                    
                    #Calculate "side lengths" based on anterior angles and known length
                    angle_A = math.radians(abs(kpoint_k1_k2_angle))
                    angle_B = math.radians(abs(kpoint_k2_k1_angle))
                    angle_C = math.radians(abs(k1_kpoint_k2_angle))
                    
                    # Use the Law of Sines
                    if math.sin(angle_C) == 0:
                        raise ValueError("Division by zero: angle_C leads to sin(angle_C) = 0")

                    k1_kpoint_length = (blender_dist * math.sin(angle_B)) / math.sin(angle_C)
                    k2_kpoint_length = (blender_dist * math.sin(angle_A)) / math.sin(angle_C)
                    
                    def find_column_with_terms(columns, terms):
                        return [col for col in columns if all(term in col for term in terms)]
            
                    position_angle=find_column_with_terms(row, [k1, k2,kpoint, "Angle"])
                    position_angle_val = row[position_angle[0]]
                    
                    ### Position point based on point B (COM), length and beta angle 
                    new_x_name=f"{kpoint}_blender.x"
                    new_y_name=f"{kpoint}_blender.y"
                    
                    angle=math.radians((position_angle_val))
                    blender_k1x=0-blender_dist
                    new_x=0+k1_kpoint_length*math.cos(angle)
                    new_y=0+k1_kpoint_length*math.sin(angle)
                    
                    #new_y=new_y*(-1)
        
                    #self.report({'INFO'}, f"{position_angle}, {position_angle_val}, {new_x}")
                    #new_extensionx, new_extensiony=extend_vector_forward(((blender_k1x, 0)),((0,0)),d=10)
                    #print(new_extensionx, new_extensiony)
                    new_angle=angle_at_vertex_signed(((10, 0)),((0,0)), ((new_x, new_y)) )             
                    
                    def sign(x):
                        return (x > 0) - (x < 0)
            
                    #if sign(new_angle) != sign(position_angle_val):
                     #   new_y = -new_y

                    new_angle=angle_at_vertex_signed(((10, 0)),((0,0)), ((new_x, new_y)) )
                    row[new_x_name] = new_x
                    row[new_y_name] = new_y
                    row[f"{new_x_name}_positionangle"]= new_angle  
                    row["snout_loc"] =blender_k1x
                    self.report({'INFO'}, f"{position_angle}, {position_angle_val}, {new_x}, {new_x_name}")    
                except (KeyError, ValueError, TypeError):
                    k1_k2_dist = None
                    kpoint_k2_k1_angle=None
                    kpoint_k1_k2_angle=None
                    k2_kpoint_k1_angle=None
        
        
        track_data = pd.DataFrame(track_data)
        keypoints_skipped = keypoints[2:]
        blender_x_cols = [f"{k}_blender" for k in keypoints_skipped]
        cols_to_smooth = [f"{col}.{axis}" for col in blender_x_cols for axis in ['x', 'y', 'z']]

        track_data = smooth_every_time_list(track_data, cols_to_smooth, context.scene.maxfps, span_secs=context.scene.smoothtime_posture)


        for idx, row in track_data.iterrows():
            if row[[f"{kp}.x" for kp in keypoints_skipped] + [f"{kp}.y" for kp in keypoints_skipped]].isnull().any():
                continue  # Skip this row if any .x or .y is NaN

            # Fit blender points to curve fish 
            keypoints_skipped = keypoints[2:]
            blender_x_cols = [f"{k}_blender.x_smoothed" for k in keypoints_skipped]

            x_values = [row[col] for col in blender_x_cols if col in row]
            x_values =[0-distance_data[0][2]]+[0]+x_values

            blender_y_cols = [f"{k}_blender.y_smoothed" for k in keypoints_skipped]
            y_values = [row[col] for col in blender_y_cols if col in row]
            y_values=[0]+[0]+y_values
            xy_sorted = sorted(zip(x_values, y_values), key=lambda pair: pair[0])
            x_sorted, y_sorted = zip(*xy_sorted)


            dx = np.diff(x_values)
            dy = np.diff(y_values)
            distances = np.sqrt(dx**2 + dy**2)
            t = np.insert(np.cumsum(distances), 0, 0) 
            spline_x = make_interp_spline(t, x_values, k=3)
            spline_y = make_interp_spline(t, y_values, k=3)

            t_new = np.linspace(0, t[-1], 200)
            x_smooth = spline_x(t_new)
            y_smooth = spline_y(t_new)

            # ---- Step 4: compute tangent at last point ----
            # derivative splines
            spline_x_der = spline_x.derivative()
            spline_y_der = spline_y.derivative()

            dx_dt = spline_x_der(t[-1])
            dy_dt = spline_y_der(t[-1])

            # normalize direction vector
            direction = np.array([dx_dt, dy_dt])
            direction /= np.linalg.norm(direction)

            # extension length = last segment length
            extend_length = distances[-1]

            # ---- Step 5: extend past last point ----
            n_extend = 50
            steps = np.linspace(0, extend_length, n_extend)
            x_extend = x_smooth[-1] + steps * direction[0]
            y_extend = y_smooth[-1] + steps * direction[1]


            x_extended = np.concatenate([x_smooth, x_extend[1:]])  # skip duplicate last point
            y_extended = np.concatenate([y_smooth, y_extend[1:]])

            cumulative_distances = [0]  # Start with zero distance at the first point
            for k in range(1, len(x_extended)):
                dx = x_extended[k] - x_extended[k-1]
                dy = y_extended[k] - y_extended[k-1]
                dist2 = math.sqrt(dx**2 + dy**2)
                cumulative_distances.append(cumulative_distances[-1] + dist2)   
            
            target_dist = abs(blender_dist)

            # 1. Find the index closest to the target distance
            cumulative_distances = np.array(cumulative_distances)
            closest_index = np.argmin(np.abs(cumulative_distances - target_dist))
            max_index = np.argmax(cumulative_distances)
            start_index = closest_index + 1
            row["curvelength"]=max(cumulative_distances)
            max_distance = max(cumulative_distances)
            if start_index < 400:
                start_distance = cumulative_distances[start_index]
                length = max_distance - start_distance
                    
                actual_length = context.scene.fishlength - target_dist
                scaling_factor = actual_length / length
                row["scaling_factor"]=scaling_factor
                anchor_x = x_extended[start_index]
                anchor_y = y_extended[start_index]
                x_sub = np.array(x_extended[start_index:])
                y_sub = np.array(y_extended[start_index:])
                centered_x = x_sub - anchor_x
                centered_y = y_sub - anchor_y
                rescaled_x = centered_x * scaling_factor
                rescaled_y = centered_y * scaling_factor
                final_x = rescaled_x + anchor_x
                final_y = rescaled_y + anchor_y

                cumulative_distances = [0]  # Start with zero distance at the first point
                for k in range(1, len(final_x)):
                    dx = final_x[k] - final_x[k-1]
                    dy = final_y[k] - final_y[k-1]
                    dist2 = math.sqrt(dx**2 + dy**2)
                    cumulative_distances.append(cumulative_distances[-1] + dist2) 
                row["curvelength2"]=max(cumulative_distances)
                
                closest_points = []
                points = len(distance_data)
                for i in range(points-1):
                    target_dist = distance_data[i+1][2]-distance_data[0][2]
                    closest_index = min(range(len(cumulative_distances)), key=lambda i: abs(cumulative_distances[i] - target_dist))
                        # Get the corresponding (x, y) point on the spline
                    closest_x = final_x[closest_index]
                    closest_y = float(final_y[closest_index])
                    point_id=distance_data[i+1][1]
                    new_x_name=f"{point_id}_blender_adjusted.x"
                    new_y_name=f"{point_id}_blender_adjusted.y"
                    row[new_x_name]=closest_x
                    row[new_y_name]=closest_y 

                    track_data.at[idx, "scaling_factor"] = scaling_factor
                    track_data.at[idx, "curvelength2"] = max(cumulative_distances)

                    track_data.at[idx, new_x_name] = closest_x
                    track_data.at[idx, new_y_name] = closest_y
           

        # ----------------
        # Smooth new points
        # ----------------
        track_data = pd.DataFrame(track_data)

        keypoints_skipped = [point[1] for point in distance_data[1:]]
        blender_x_cols = [f"{k}_blender_adjusted" for k in keypoints_skipped]
        cols_to_smooth = [f"{col}.{axis}" for col in blender_x_cols for axis in ['x', 'y', 'z']]

        track_data = smooth_every_time_list(track_data, cols_to_smooth, context.scene.maxfps, span_secs=context.scene.smoothtime_posture)
        track_data = pd.DataFrame(track_data)

        for point in keypoints_skipped:
            x_name = f"{point}_blender_adjusted.x_smoothed"
            y_name = f"{point}_blender_adjusted.y_smoothed"

            # Default to NaN in case no match is found
            distance_val = float('nan')

            # Find the distance associated with the current keypoint
            matched_rows = [row2 for row2 in distance_data if row2[1] == point]
            if matched_rows:
                distance_val = matched_rows[0][2]

            # Calculate point_location relative to start
            if distance_data:
                point_location = -distance_data[0][2] + distance_val
            else:
                point_location = float('nan')

            new_col = f"{point}_x_move"

            # Update or add the new column
            if x_name in track_data.columns:
                track_data[new_col] = track_data[x_name] - point_location
            else:
                track_data[new_col] = float('nan')


        # ----------------
        # Pose fish
        # ----------------
        for point in keypoints_skipped:
            x_name=f"{point}_x_move"
            y_name=f"{point}_blender_adjusted.y_smoothed"
            bpy.context.view_layer.objects.active = IK_armature
            bpy.ops.object.mode_set(mode='POSE')
        
            for index, row in track_data.iterrows():
                frame = row["frame_idx"]
                if frame is None:
                    continue
                
                pose_bone = IK_armature.pose.bones.get(f"IK_{point}")
                pose_bone.bone.select = True
                IK_armature.data.bones.active = IK_armature.data.bones[f"IK_{point}"]
                    
                if not pose_bone:
                    continue

                x = row[x_name]
                
                if math.isnan(x):
                    continue
                
                x = 0 if x > 0 else x
                
                y = row[y_name]
                matched_rows = [row2 for row2 in distance_data if row2[1] == point]

                bpy.context.scene.frame_set(int(frame))
                pose_bone.location = (-y,x, 0)
                bpy.ops.anim.keyframe_insert_by_name(type="LocRotScale")
                #self.report({'INFO'}, f"{pose_bone},{x}, {pose_bone.location}" )
            bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.context.scene.frame_start = int(track_data["frame_idx"].min())
        bpy.context.scene.frame_end = int(track_data["frame_idx"].max())
        # Set interpolation to linear in Dope Sheet
        for area in bpy.context.screen.areas:
            if area.type == 'DOPESHEET_EDITOR':
                with bpy.context.temp_override(area=area):
                    bpy.ops.action.interpolation_type(type='LINEAR')
                break   

        
        track_data = pd.DataFrame(track_data)
        

        return {'FINISHED'}
    
#--------Keyframe eye track data--------
class POSE_OT_eyepose(bpy.types.Operator):
    """Keyframe body posture"""
    bl_idname = "obj.eyepose"
    bl_label = "Keyframe body posture"
    
    def execute(self, context):
        # ----------------
        # Get data
        # ----------------
        #global eyetrack_data_store
        #eyetrack_data = eyetrack_data_store.get('eyetrack_data', [])
        eyetrack_data=json.loads(context.scene.eyetrack_data_store)
        eyecols = [k.strip() for k in context.scene.eyetrack_colnames.split(',') if k.strip()]

        eyetrack_data = pd.DataFrame(eyetrack_data)
        cols_to_smooth = [f"{k}" for k in eyecols]
        

        eyetrack_data = smooth_every_time_list(eyetrack_data, cols_to_smooth, context.scene.maxfps, span_secs=context.scene.eyesmoothtime)



        #else:
         #   self.report({'WARNING'}, "Eyetrack columns not found in data.")

        # ----------------
        # Get eye direction controls
        # ----------------    
        bpy.ops.object.mode_set(mode='OBJECT')
        lefteye_empty=bpy.data.objects.get(f"Lefteye_{context.scene.fish_model_name}")
        righteye_empty=bpy.data.objects.get(f"Righteye_{context.scene.fish_model_name}")
        
        if not lefteye_empty or not righteye_empty:
            self.report({'ERROR'}, f"Lefteye_{context.scene.fish_model_name} or Righteye_{context.scene.fish_model_name} not found")
            return {'CANCELLED'}

        for _, row in eyetrack_data.iterrows():
            frame = int(row["frame_idx"])
            if frame is None:
                continue

            leftangle = row[f"{eyecols[0]}_smoothed"]
            rightangle = row[f"{eyecols[1]}_smoothed"]

            if leftangle is None or rightangle is None:
                continue

            context.scene.frame_set(frame)
            lefteye_empty.rotation_euler.z = math.radians(leftangle)
            lefteye_empty.keyframe_insert(data_path="rotation_euler", frame=frame)

            righteye_empty.rotation_euler.z = math.radians(-rightangle)
            righteye_empty.keyframe_insert(data_path="rotation_euler", frame=frame)

        # Set interpolation to linear in the Dope Sheet
        for area in bpy.context.screen.areas:
            if area.type == 'DOPESHEET_EDITOR':
                with bpy.context.temp_override(area=area):
                    bpy.ops.action.interpolation_type(type='LINEAR')
                break
        self.report({'INFO'}, "Finished")
        

        return {'FINISHED'}

#--------Keyframe orientation track data--------

class ORIENT_OT_bodypose(bpy.types.Operator):
    """Keyframe body posture"""
    bl_idname = "obj.bodyorient"
    bl_label = "Keyframe body posture"

    def execute(self, context):

        # ----------------
        # Get data
        # ----------------
        keypoints = [k.strip() for k in context.scene.keypoints.split(',') if k.strip()]
        #global track_data_store
        #track_data = track_data_store.get('upsampled_zdata', [])
        track_data=json.loads(context.scene.track_data_store)

        # Ensure values are numeric or NaN
        for row in track_data:
            for key, val in row.items():
                if key != 'frame_idx':
                    try:
                        row[key] = float(val)
                    except (TypeError, ValueError):
                        row[key] = np.nan

        track_data=pd.DataFrame(track_data)
        keypoints_first_two = keypoints[:2]
        columnssmooth = [
            col for col in track_data.columns
            if any(kp in col for kp in keypoints_first_two) and col.endswith((".x", ".y", ".z"))
        ]
        track_data = smooth_every_time_list(track_data, columnssmooth, context.scene.maxfps, span_secs=context.scene.smoothtime_orient)

        def bearing(dx, dy):
            angle = np.arctan2(dx, dy) * 180 / np.pi  # dx and dy are intentionally flipped
            return (angle + 360) % 360

        
        def vertical_bearing(dx, dz):
            # Angle above/below horizontal plane
            angle = np.arctan2(dz, dx) * 180 / np.pi  # dz over horizontal distance
            return angle  # Can be negative for below horizontal, positive for above

        com_3d = np.array([track_data[f"{keypoints_first_two[1]}.x_smoothed"], track_data[f"{keypoints_first_two[1]}.y_smoothed"], track_data[f"{keypoints_first_two[1]}.z_smoothed"]])
        head_3d = np.array([track_data[f"{keypoints_first_two[0]}.x_smoothed"], track_data[f"{keypoints_first_two[0]}.y_smoothed"], track_data[f"{keypoints_first_two[0]}.z_smoothed"]])

        track_data = track_data.sort_values(
            ['frame_idx']
        ).reset_index(drop=True)

        track_data["x_diff"] = (
    track_data[f"{keypoints_first_two[1]}.x_smoothed"]
    - track_data[f"{keypoints_first_two[0]}.x_smoothed"]
        )

        track_data["y_diff"] = (
            track_data[f"{keypoints_first_two[1]}.y_smoothed"]
            - track_data[f"{keypoints_first_two[0]}.y_smoothed"]
        )

        track_data["z_diff"] = (
            track_data[f"{keypoints_first_two[1]}.z_smoothed"]
            - track_data[f"{keypoints_first_two[0]}.z_smoothed"]
        )


        track_data['xy_bearing'] = bearing(track_data["x_diff"], track_data["y_diff"])
        track_data = track_data.sort_values(['frame_idx'])

        
        x_diff_cm = track_data["x_diff"] * context.scene.pixelconvert
        y_diff_cm = track_data["y_diff"] * context.scene.pixelconvert


        horizontal_dist = np.sqrt(
        x_diff_cm**2+
        y_diff_cm**2
    )

        # Vertical bearing
        track_data['z_bearing'] = np.degrees(
    np.arctan2(track_data["z_diff"], horizontal_dist)
)

        track_data["z_bearing"] = track_data["pitch_deg"] if "pitch_deg" in track_data.columns else 0
        track_data = smooth_every_time_list(track_data, ['z_bearing'], context.scene.maxfps, span_secs=context.scene.smoothtime_orient)



        track_data["x_diff_cm"] = track_data["x_diff"] * context.scene.pixelconvert
        track_data["y_diff_cm"] = track_data["y_diff"] * context.scene.pixelconvert

        track_data["horizontal_dist"] = np.sqrt(
            track_data["x_diff_cm"]**2 +
            track_data["y_diff_cm"]**2
        )

        track_data["z_diff_debug"] = track_data["z_diff"]

        track_data["z_bearing_debug"] = np.degrees(
            np.arctan2(
                track_data["z_diff_debug"],
                track_data["horizontal_dist"]
            )
        )



        def bearing_diff(angle1, angle2):
            delta = angle2 - angle1
            return ((delta + 180) % 360) - 180

        def compute_bearing_change(group):
            group = group.copy()
            group['xy_bearing_change'] = bearing_diff(group['xy_bearing'], group['xy_bearing'].shift(-1))
            group['z_bearing_change'] = bearing_diff(group['z_bearing_smoothed'], group['z_bearing_smoothed'].shift(-1))
            return group

        track_data = compute_bearing_change(track_data)
        

        track_data = smooth_every_time_list(track_data, ['xy_bearing_change'], context.scene.maxfps, span_secs=context.scene.smoothtime_orient)
        track_data = smooth_every_time_list(track_data, ['z_bearing_change'], context.scene.maxfps, span_secs=context.scene.smoothtime_orient)

        track_data = track_data.sort_values(['frame_idx']).copy()
        start = track_data['xy_bearing'].iloc[0]  # or whichever initial bearing you want
        track_data['xy_winding_angle'] = start + track_data['xy_bearing_change_smoothed'].cumsum()

        start_z = track_data['z_bearing'].iloc[0]
        track_data['z_winding_angle'] = start_z + track_data['z_bearing_change_smoothed'].cumsum()


        ###Rotate direction control
        bpy.ops.object.mode_set(mode='OBJECT')


        # Get the directional empty object
        direction_empty = bpy.data.objects.get(f"DirectionControl_{context.scene.fish_model_name}")
        if not direction_empty:
            self.report({'ERROR'}, f"DirectionControl_{context.scene.fish_model_name} not found")
            return {'CANCELLED'}

        # Insert keyframes for body orientation
        for index, row in track_data.iterrows():
                frame = int(row["frame_idx"])
                if frame is None:
                    continue
                
                angle = row['xy_winding_angle']
                angle2=row['z_winding_angle']
                if frame is None or angle is None:
                    continue

                context.scene.frame_set(frame)
                direction_empty.rotation_euler.z = math.radians(-(angle-90))
                direction_empty.rotation_euler.y = math.radians(angle2)
                direction_empty.keyframe_insert(data_path="rotation_euler", frame=frame)

        # Set interpolation to linear in the Dope Sheet
        for area in bpy.context.screen.areas:
            if area.type == 'DOPESHEET_EDITOR':
                with bpy.context.temp_override(area=area):
                    bpy.ops.action.interpolation_type(type='LINEAR')
                break
        self.report({'INFO'}, "Finished")


       

        
        return {'FINISHED'}



#--------Keyframe body location track data--------

class LOCATE_OT_bodypose(bpy.types.Operator):
    """Keyframe body location"""
    bl_idname = "obj.bodylocate"
    bl_label = "Keyframe body location"

    def execute(self, context):

        # ----------------
        # Get data
        # ----------------
        keypoints = [k.strip() for k in context.scene.keypoints.split(',') if k.strip()]
        #global track_data_store
        #track_data = track_data_store.get('upsampled_zdata', [])
        track_data=json.loads(context.scene.track_data_store)

        # Ensure values are numeric or NaN
        for row in track_data:
            for key, val in row.items():
                if key != 'frame_idx':
                    try:
                        row[key] = float(val)
                    except (TypeError, ValueError):
                        row[key] = np.nan

        track_data=pd.DataFrame(track_data)
        keypoints_com = keypoints[1]

        columnssmooth = [
            col for col in track_data.columns
            if any(kp in col for kp in keypoints_com) and col.endswith((".x", ".y", ".z"))
        ]
        track_data = smooth_every_time_list(track_data, columnssmooth, context.scene.maxfps, span_secs=context.scene.smoothtime_move)
        #track_data.to_csv("C:/Users/mert4358/Desktop/DigiFishDemo_lab/track_data_check_locate.csv")
        
        x_col = f"{keypoints_com}.x_smoothed"
        y_col = f"{keypoints_com}.y_smoothed"
        z_col = f"{keypoints_com}.z_smoothed"

        track_data["x_blender"] = track_data[x_col] * context.scene.pixelconvert
        track_data["y_blender"] = track_data[y_col] * context.scene.pixelconvert
        track_data["z_blender"] = track_data[z_col]

        direction_empty = bpy.data.objects.get(f"DirectionControl_{context.scene.fish_model_name}")

        for index, row in track_data.iterrows():
            frame = int(row["frame_idx"])
            if frame is None:
                continue
                
            x = row["x_blender"] if not pd.isna(row["x_blender"]) else 1.0
            y = row["y_blender"] if not pd.isna(row["y_blender"]) else 1.0
            z = row["z_blender"] if not pd.isna(row["z_blender"]) else 1.0

            context.scene.frame_set(frame)
            direction_empty.location = (x, y, z)
            direction_empty.keyframe_insert(data_path="location", frame=frame)
        

        return {'FINISHED'}









#--------Main class--------
class Animate_Fish(bpy.types.Operator):
    """Keyframe body posture"""
    bl_idname = "obj.animatefish"
    bl_label = "Keyframe body posture"
    
    fish_name: bpy.props.EnumProperty(
        name="Fish Model",
        description="Select a fish model",
        items=fish_name_items_armatures
    )
    
    trackdata_folder: bpy.props.StringProperty(
        name="Track Data File",
        description="Path to csv file with tracking data",
        subtype='FILE_PATH'
    )
    
    csvfps:bpy.props.FloatProperty(
        name="Tracking fps", description="Frames per second of track data", default=240
    )
    
    smoothtime_posture:bpy.props.FloatProperty(
        name="Posture smoothing window", description="Posture: Smoothing window (s) for track data", default=0.5
    )

    smoothtime_orient:bpy.props.FloatProperty(
        name="Orient smoothing window", description="Orient: Smoothing window (s) for track data", default=0.5
    )

    smoothtime_move:bpy.props.FloatProperty(
        name="Move smoothing window", description="Move: Smoothing window (s) for track data", default=0.5
    )


    eyetrackdata_folder: bpy.props.StringProperty(
            name="Eye Track Data File",
            description="Path to csv with eye tracking data",
            subtype='FILE_PATH'
        )    
    
    eyetrack_colnames:bpy.props.StringProperty(
        name="Eye tracking columns",
        description="Column names for left and right eye",
        default=""
    )
    
    eyecsvfps:bpy.props.FloatProperty(
        name="Eye tracking fps", description="Frames per second of eye track data", default=240
    )

    eyesmoothtime:bpy.props.FloatProperty(
        name="Eye tracking smoothing window", description="Smoothing window (s) for eye track data", default=0.5
    )

    def invoke(self, context, event):
        # Trigger the popup that lets user enter fish_id
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        context.scene.fish_model_name = self.fish_name
        context.scene.trackdata_folder=self.trackdata_folder
        context.scene.csvfps=self.csvfps
        context.scene.eyetrackdata_folder=self.eyetrackdata_folder
        context.scene.eyetrack_colnames=self.eyetrack_colnames
        context.scene.eyecsvfps=self.eyecsvfps
        context.scene.smoothtime_posture=self.smoothtime_posture
        context.scene.smoothtime_orient=self.smoothtime_orient
        context.scene.smoothtime_move=self.smoothtime_move
        
        context.scene.eyesmoothtime=self.eyesmoothtime

        bpy.ops.obj.readdata('EXEC_DEFAULT')
        if track_data_store is not None: 
            self.report({'INFO'}, f"Loaded track data from {context.scene.trackdata_folder}")
        
        if context.scene.eyetrackdata_folder and context.scene.eyetrack_colnames: 
            self.report({'INFO'}, f"Loaded track data from {context.scene.eyetrackdata_folder}")
        else: 
            self.report({'INFO'}, f"No eye track data loaded")

        bpy.ops.obj.bodypose('EXEC_DEFAULT')

        if context.scene.eyetrackdata_folder and context.scene.eyetrack_colnames:
            bpy.ops.obj.eyepose('EXEC_DEFAULT')

        bpy.ops.obj.bodyorient('EXEC_DEFAULT')
        bpy.ops.obj.bodylocate('EXEC_DEFAULT')


        return {'FINISHED'}
    
#--------------Register--------------
def register():
    bpy.utils.register_class(Animate_Fish)
    bpy.utils.register_class(READ_data)
    bpy.utils.register_class(POSE_OT_bodypose)
    bpy.utils.register_class(POSE_OT_eyepose)
    bpy.utils.register_class(ORIENT_OT_bodypose)
    bpy.utils.register_class(LOCATE_OT_bodypose)

    bpy.types.Scene.fish_model_name= bpy.props.StringProperty(name="Named Fish Model")
    bpy.types.Scene.trackdata_folder = bpy.props.StringProperty(name="Track data folder", default="")
    bpy.types.Scene.eyetrackdata_folder = bpy.props.StringProperty(name="Eye track data file", default="")
    bpy.types.Scene.eyetrack_colnames= bpy.props.StringProperty(name="Eye cam column names")
    bpy.types.Scene.csvfps = bpy.props.FloatProperty(name="Track data frames per second", default=240)
    bpy.types.Scene.eyecsvfps = bpy.props.FloatProperty(name="Eye track data frames per second", default=30)
    bpy.types.Scene.track_data_store = bpy.props.StringProperty(name="Track Data Store")
    bpy.types.Scene.eyetrack_data_store= bpy.props.StringProperty(name="Eye Track Data Store")
    bpy.types.Scene.eyesmoothtime = bpy.props.FloatProperty(name="Eye tracking smoothing window", default=0.5)
    bpy.types.Scene.smoothtime_posture = bpy.props.FloatProperty(name="Posture:Tracking smoothing window", default=0.5)
    bpy.types.Scene.smoothtime_orient = bpy.props.FloatProperty(name="Orient:Tracking smoothing window", default=0.5)
    bpy.types.Scene.smoothtime_move = bpy.props.FloatProperty(name="Move:Tracking smoothing window", default=0.5)
    
    
    

def unregister():
    bpy.utils.unregister_class(Animate_Fish)
    bpy.utils.unregister_class(READ_data)
    bpy.utils.unregister_class(POSE_OT_bodypose)
    bpy.utils.unregister_class(POSE_OT_eyepose)
    bpy.utils.unregister_class(ORIENT_OT_bodypose)

    
    del bpy.types.Scene.fish_model_name
    del bpy.types.Scene.trackdata_folder
    del bpy.types.Scene.eyetrackdata_folder
    del bpy.types.Scene.eyetrack_colnames
    del bpy.types.Scene.csvfps
    del bpy.types.Scene.eyecsvfps 
    del bpy.types.Scene.track_data_store
    del bpy.types.Scene.eyetrack_data_store 
    del bpy.types.Scene.smoothtime_posture
    del bpy.types.Scene.smoothtime_orient
    del bpy.types.Scene.smoothtime_move
    del bpy.types.Scene.eyesmoothtime
