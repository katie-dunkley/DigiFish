# DigiFish: A flexible open-source tool for animating realistic virtual fish and reconstructing visual fields from tracking data

## Adding DigiFish to Blender
Download the latest DigiFish version [here](https://github.com/user-attachments/files/33150557/DigiFish_v1.0.0.zip). Blender add-ons must be installed as a `.zip` file via the `Preferences` menu. Select `Install from Disk`, choose the DigiFish `.zip` file, and DigiFish will be installed automatically. DigiFish currently works with [Blender 4.5](https://www.blender.org/download/releases/4-5/). 

<img width="1280" height="727" alt="AddDigiFish" src="https://github.com/user-attachments/assets/eb209a4f-cae8-4b24-bddc-2b8f9d9a09aa" />

## Setting up the scene in DigiFish

### 1) Clear the default Blender scene

![ClearScene](https://github.com/user-attachments/assets/e546187d-821f-44be-a4df-c522b56f9f55)

### 2) Adjust scene information

Enter information about the frame rate and resolution of the source video. DigiFish uses this information when setting up cameras and smoothing tracking data.

Users should also provide a pixel-to-cm conversion factor based on an object of known length visible in the source video. For example, for a 2704 × 1520 video recorded at 240 fps, if a 10 cm object measures 173.9 pixels:

`1 pixel = 10 / 173.9 = 0.0575 cm`

The corresponding pixel-to-cm conversion factor is therefore `0.0575`. DigiFish uses this value to convert x-y tracking coordinates supplied in pixels into real-world coordinates.

![AddInfo](https://github.com/user-attachments/assets/76414623-0040-44ab-8f59-a8f044bbd62d)

### 3) Import a scene

Scenes can be generated using a range of 3D modelling approaches, including photogrammetry and Neural Radiance Fields. Scenes should be prepared and edited in a separate `.blend` file before being imported into the DigiFish project.

![AddScene](https://github.com/user-attachments/assets/0f380ac0-c7f2-414f-9c6d-5595f05bac5e)

#### Adding a reference image

This optional step can help with positioning and scaling the reconstructed scene. A reference image, such as a frame from a lateral camera, can be used to align the scene with the tracking data. The image is automatically scaled according to the pixel-to-cm conversion factor supplied by the user.

![AddRefImage](https://github.com/user-attachments/assets/46ecee29-9d83-48c4-ba9c-ba6ed1722f5f)

### 4) Add lighting

Users can add an overhead light through the DigiFish panel. The resulting light-control panel can be used to adjust its brightness, colour, and location.

![AddLight](https://github.com/user-attachments/assets/113faf2b-7162-45e7-91ed-c9f0437d5cca)

## Adding fish

### 1) Set up the fish model

Prepare the fish model in a separate `.blend` file before importing it into DigiFish. Models can be imported into Blender in any compatible format (e.g. `.obj`) and generated using a range of approaches, including manual sculpting, Meshy AI, and SAM 3.

**Important:** DigiFish expects the model to have a specific starting orientation:

* the reconstructed scene lies on the x-y plane and is viewed from above;
* the fish model should lie on the z-x plane;
* the head should point to the left.

Apply all transforms before saving the `.blend` file so that the x, y, and z rotation values are reset to `0`.

<img width="892" height="461" alt="Screenshot 2026-03-02 at 16 31 27" src="https://github.com/user-attachments/assets/fc1225e4-20b4-4a38-9f87-cb232b205cbb" />

![SetupFish](https://github.com/user-attachments/assets/0edd212f-bdf3-4a17-9e37-c326570bf345)

### 2) Add a single fish model

The `.blend` file containing the fish model can then be added to the reconstruction using the DigiFish panel. Users specify the desired body length of the fish in cm, and DigiFish scales the model accordingly.

At this stage, users can also choose to add cameras at the fish's eyes. DigiFish estimates the location of the eyes from the model mesh, although their positions may sometimes require manual adjustment (see below).

![AddFish](https://github.com/user-attachments/assets/0bb75a82-8826-4298-9830-885f7c3ea654)

#### Adjust eye position

To ensure that the eye cameras are correctly positioned, users may need to manually move them on the fish model using `G` in Blender.

The x-y-z location of the left eye camera can then be entered under `Eye Cam Location` to ensure reproducibility and consistency across eyes and individuals. Locations should be entered as:

`1, x, y, z`

where `1` indicates a scale of 1. Users can alter this scale value to change the size of the eye objects; this does not change the resolution or properties of the eye cameras themselves.

![MoveEyes](https://github.com/user-attachments/assets/58aeb0a8-0ef8-4ba4-888b-17413b84a074)

![MoveEyes2](https://github.com/user-attachments/assets/039868d5-40b7-4147-879d-8985f03a1030)

### 3) Add bones

To map keypoint tracking data onto the fish model, users provide the names of their tracked body keypoints and the proportional positions of those keypoints along the model's body. Keypoint names must match those used in the tracking data.

Positions are specified along the body relative to its total length. The first keypoint is positioned at `0`, and the end of the body is `1.0`.

For example, four keypoints might be defined as:

`Head = 0`
`COM = 0.23`
`Caudal = 0.6`
`Tail = 0.8`

If an endpoint at `1.0` is not supplied, DigiFish adds one automatically.

Users can also add intermediate segments, which function similarly to vertebrae and control how smoothly the model bends between tracked keypoints. For example, five segments can be added between the COM (centre-of-mass) and Caudal keypoints and four between the Caudal and Tail keypoints (`COM: 5, Caudal: 4`).

Ideally, only one segment should be used between the first two keypoints because DigiFish assumes a straight-line vector between them.

<img width="300" height="224" alt="Screenshot 2025-12-03 at 12 12 33" src="https://github.com/user-attachments/assets/def5e3f6-5ada-428d-ab85-65f5818a92a9" />

![AddBones](https://github.com/user-attachments/assets/48399954-7e84-41d0-86ee-f6fbbd00f19f)

### 4) Animate fish

To animate a fish model, users supply x-y and, optionally, z tracking coordinates for each keypoint in a CSV file.

Column names must match the keypoint names specified during the `Add bones` stage and should be followed by `.x`, `.y`, or `.z`. For example:

`Head.x`, `Head.y`, `Head.z`

x-y coordinates can be supplied in pixels because DigiFish converts them using the pixel-to-cm conversion factor supplied by the user. z coordinates should be provided in cm. If z coordinates are not supplied, DigiFish assigns a default z position of 1 cm.

<img width="939" height="294" alt="Example csv" src="https://github.com/user-attachments/assets/6380a6fa-44cb-4f13-9f77-cc415ca04d80" />

[SLEAPTracks_Zebra1.csv](https://github.com/user-attachments/files/32949376/SLEAPTracks_Zebra1.csv)

If users also wish to animate pitch (head-up/head-down posture), the tracking file should contain a `pitch_deg` column containing pitch in degrees, with positive values indicating a head-up posture. Pitch can be calculated from 3D tracking data for the first and second keypoints using the example script below.

*Example code for calculating pitch from 3D tracking data:* [Code_pitch.py](https://github.com/user-attachments/files/32950388/Code_pitch.py)

Tracking CSV files are added to DigiFish using the `Animate fish` button. Users can specify separate smoothing values for three components of the reconstruction: posture, orientation, and movement through the scene.

Larger smoothing values generally remove more rapid changes in the tracking data, whereas smaller values retain more rapid variation. Users are encouraged to compare the resulting animation with the original tracked behaviour and adjust these values accordingly. The smoothing applied by DigiFish also accounts for the frame rate of the supplied tracking data.

Once `OK` is clicked, this step may take some time to complete. The eye-tracking section can be left blank if eye-tracking data are unavailable.

![AnimateFish](https://github.com/user-attachments/assets/63921830-421d-4f62-a511-c84cf7b65caa)

This process moves and deforms the fish model according to the supplied tracking data.

<img width="1512" height="859" alt="Screenshot 2026-10-02 at 11 22 36" src="https://github.com/user-attachments/assets/54ad2fbb-1583-4cd6-9869-4f708930ba94" />

#### Eye-tracking data

Eye-tracking data should be supplied as angles in degrees, with negative angles indicating that the eye is directed inward towards the snout and positive angles indicating that it is directed outward towards the tail.

These data should be supplied in a CSV file containing two separately named eye-angle columns and a `frame_idx` column. The names of the two eye-angle columns can be specified by the user in the DigiFish panel.

Users must also specify a smoothing value for the eye-tracking data. This can differ from the smoothing values used for body tracking and should be selected according to the temporal resolution and noise of the eye-tracking data.

<img width="282" height="305" alt="Screenshot 2026-10-02 at 11 33 51" src="https://github.com/user-attachments/assets/afee163c-8da6-4330-8b03-cea090b0e602" />

*Example code for calculating eye angles from tracking data:* [Code_eyeangle.py](https://github.com/user-attachments/files/32956414/Code_eyeangle.py)

### Add and animate multiple fish

Although multiple fish can be added independently using the steps above, DigiFish also allows users to provide a single CSV file containing the information required to add and animate multiple individuals.

The CSV should contain the following columns:

| Parameter              | Description                                                                                   |
| ---------------------- | --------------------------------------------------------------------------------------------- |
| `Name`                 | Name Blender will use for the fish model (e.g. `Zebra`).                                      |
| `ID`                   | Unique identification number for the individual fish.                                         |
| `ModelPath`            | File path to the `.blend` file containing the fish model.                                     |
| `Size`                 | Desired body length of the fish model, in cm.                                                 |
| `EyeCam`               | Whether eye cameras should be added to the fish model.                                        |
| `EyeFOV`               | Field of view of the eye camera(s), in degrees.                                               |
| `EyeCamLocation`       | Location of the eye camera(s) on the fish model.                                              |
| `Keypoints`            | Names of the tracked body keypoints used to reconstruct posture.                              |
| `KeypointPositions`    | Corresponding proportional positions of the keypoints on the fish model.                      |
| `Segments`             | Number of intermediate body segments associated with the keypoints.                           |
| `TrackData`            | File path to the tracking data used to reconstruct movement and posture.                      |
| `TrackDataFPS`         | Frame rate, in frames per second, of the tracking data.                                       |
| `EyeTrackData`         | File path to the eye-tracking data used to reconstruct eye movements.                         |
| `EyeTrackDataFPS`      | Frame rate, in frames per second, of the eye-tracking data.                                   |
| `EyeTrackColumns`      | Names of the columns containing the left and right eye-orientation values.                    |
| `EyeTrackSmoothWindow` | Smoothing value applied to the eye-tracking data before reconstruction.                       |
| `PixelConvert`         | Pixel-to-cm conversion factor used to convert x-y tracking coordinates into real-world units. |
| `VideoHeight`          | Height of the source video, in pixels.                                                        |
| `VideoWidth`           | Width of the source video, in pixels.                                                         |
| `PostureTrackSmooth`   | Smoothing value applied when reconstructing body posture.                                     |
| `OrientTrackSmooth`    | Smoothing value applied when reconstructing body orientation.                                 |
| `MoveTrackSmooth`      | Smoothing value applied when reconstructing movement through the scene.                       |

These parameters correspond to those described in the preceding steps. See the example CSV below for the required formatting.

*Example multi-fish CSV file:* [Example_multifish.csv](https://github.com/user-attachments/files/32956820/Example_multifish.csv)

### 5) Add a camera

In addition to eye cameras, cameras can be added to view the reconstructed scene from above or from the side. Users can specify the camera's distance from the scene and its field of view (FOV).

For side cameras, DigiFish places the camera on a circle around the scene. Users can then move and rotate the camera around this circle to obtain the desired viewpoint using `G` and `R`, respectively.

#### Add top camera

<img width="1280" height="727" alt="AddTopCamera" src="https://github.com/user-attachments/assets/96bcb4a2-1016-4651-9f40-b9af4ddecdc6" />

The camera can also be repositioned using the side panel:

<img width="1280" height="727" alt="MoveTopCamera" src="https://github.com/user-attachments/assets/76966540-3431-4bdf-94d4-6346ee4be276" />

#### Add side camera

<img width="1280" height="727" alt="AddSideCamera" src="https://github.com/user-attachments/assets/0e70e4c9-d918-4f52-8999-1a212fa633bb" />

### 6) Render videos

#### Render from a camera in the scene

DigiFish uses Blender's EEVEE rendering engine by default because it is computationally efficient. Before rendering, users should select the desired camera using the `Select camera` button.

The `Render video - camera` button renders the animation from the selected camera using the FOV specified when the camera was added. The output is saved as an `.mp4` file in the same folder as the current Blender project.

During rendering, a window displays each frame as it is generated. The output video's frame rate is determined by the frame rate specified in the `Add info` panel.

<img width="1280" height="727" alt="RenderCamera" src="https://github.com/user-attachments/assets/20c80429-c01d-47f7-be22-2b3e836b3f03" />

#### Render from point of view

To render point-of-view (POV) footage, DigiFish integrates with the [eeVR add-on](https://github.com/EternalTrail/eeVR), which enables fisheye rendering from virtual cameras positioned at the model's eyes.

This method produces a sequence of `.png` images, which can subsequently be converted into a video if required. Press `Escape` to cancel rendering.

<img width="1280" height="727" alt="RenderPOV" src="https://github.com/user-attachments/assets/0e6de3db-65da-4a11-9c49-2df9e2dd512b" />

*Example output image:*

<img width="2704" height="2704" alt="frame000000" src="https://github.com/user-attachments/assets/ab456970-6720-4c45-a232-4d15ce82325d" />
