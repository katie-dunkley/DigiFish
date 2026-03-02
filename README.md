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
![AddLight](https://github.com/user-attachments/assets/113faf2b-7162-45e7-91ed-c9f0437d5cca)

## Adding fish
### 1) Setup fish model
In a seperate .blend file ensure fish model is facing the correct direction. Because the scene is on an xy axis and is viewed from above, the fish model should be on the zx plane with it's head pointing to the left. Make sure to apply all transforms before saving .blend file (i.e. ensure all xyz rotation values are reset to 0). Model fish can be imported into blender in any compatabile format (e.g. .obj file), and can be generated via multiple methods including sculpting, MeshyAI and Sam3. 
<img width="892" height="461" alt="Screenshot 2026-03-02 at 16 31 27" src="https://github.com/user-attachments/assets/fc1225e4-20b4-4a38-9f87-cb232b205cbb" />
![SetupFish](https://github.com/user-attachments/assets/0edd212f-bdf3-4a17-9e37-c326570bf345)

### 2) Add model fish
.blend files containing model fish can then be added to the reconstruction project using the DigiFish panel. Users can specify the size of the fish in cms and DigiFish implements this when adding. There is an option at this stage to add cameras at the eys of the fish. DigiFish works out the location of the eyes based on the model mesh, but this may need adjusting at times (see below). 
![AddFish](https://github.com/user-attachments/assets/0bb75a82-8826-4298-9830-885f7c3ea654)

### Adjust eye position
To ensure eye cameras are in the correct location, users may have to manually move them on the model fish (using "G" on the keyboard). The specific xyz location of the left eye camera can then be imported with the fish info ("Eye Cam Location") for reproducability and consistency across eyes/individuals. Locations should be added as "1, x, y, z" (with 1 indicating a scale of 1). Users can change the size of the eyes through altering the scale value (although this does not change the eye camera size/resolution).  
![MoveEyes](https://github.com/user-attachments/assets/58aeb0a8-0ef8-4ba4-888b-17413b84a074)

![MoveEyes2](https://github.com/user-attachments/assets/039868d5-40b7-4147-879d-8985f03a1030)





