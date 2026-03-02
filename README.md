# DigiFish: A flexible open-source tool for animating realistic virtual fish and reconstructing visual fields from tracking data

## Adding DigiFish to Blender


## Setting up the scene in DigiFish
### 1) Clear default Blender scene
![ClearScene](https://github.com/user-attachments/assets/e546187d-821f-44be-a4df-c522b56f9f55)

### 2) Adjust scene info 
Add info to scene about frames per second and resoultion of video data (links to tracking video) - this is used for setting up cameras and for adjusting smoothing of tracked points. Also add in 1 pixel to cm ratio based on known length in lateral camera view (e.g. 2704 x 1520 video @ 240 fps, 10 cm object = 173.9 pixels ∴ 1 pixel = 0.0575 cm). This ratio is used for converting xy tracking data into real world coordinates. 
![AddInfo](https://github.com/user-attachments/assets/76414623-0040-44ab-8f59-a8f044bbd62d)

### 3) Importing scene 
Scenes can be generated through a range of 3D modelling approaches including photogrammetry and Neural Radiance Fields. Scenes should be edited in a seperate .blend file before being imported into the DigiFish .blend file. 
![AddScene](https://github.com/user-attachments/assets/0f380ac0-c7f2-414f-9c6d-5595f05bac5e)

#### Adding reference image 
Optional step to help with scaling. Including a reference image (i.e. a screenshot of a lateral camera) is useful to help position and scale the scene so that the tracking data aligns correctly with the scene. The image should automatically scale to the correct size using the pixel to cm ratio supplied by the user.
![AddRefImage](https://github.com/user-attachments/assets/46ecee29-9d83-48c4-ba9c-ba6ed1722f5f)

### 4) Adding light 
Users can add an overhead light to the scene through the DigiFish panel, and through the light control panel that pops up, adjust the brightness, colour and location. 
![AddInfo](https://github.com/user-attachments/assets/e32f9150-7d4b-4851-a9a4-5307dce3d05a)

