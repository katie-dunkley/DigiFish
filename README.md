# DigiFish: A flexible open-source tool for animating realistic virtual fish and reconstructing visual fields from tracking data

## Adding DigiFish to Blender


## Setting up the scene in DigiFish
### 1) Clear default Blender scene
![ClearScene](https://github.com/user-attachments/assets/e546187d-821f-44be-a4df-c522b56f9f55)

### 2) Adjust scene info 
Add info to scene about frames per second and resoultion of video data (links to tracking video) - this is used for setting up cameras and for adjusting smoothing of tracked points. Also add in 1 pixel to cm ratio based on known length in lateral camera view (e.g. 2704 x 1520 video @ 240 fps, 10 cm object = 173.9 pixels ∴ 1 pixel = 0.0575 cm). This ratio is used for converting xy tracking data into real world coordinates. 
![AddInfo](https://github.com/user-attachments/assets/76414623-0040-44ab-8f59-a8f044bbd62d)

### 3) Importing scene 
