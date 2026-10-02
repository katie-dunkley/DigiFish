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

### 2) Add single fish model
.blend files containing model fish can then be added to the reconstruction project using the DigiFish panel. Users can specify the size of the fish in cms and DigiFish implements this when adding. There is an option at this stage to add cameras at the eys of the fish. DigiFish works out the location of the eyes based on the model mesh, but this may need adjusting at times (see below). 
![AddFish](https://github.com/user-attachments/assets/0bb75a82-8826-4298-9830-885f7c3ea654)

#### Adjust eye position
To ensure eye cameras are in the correct location, users may have to manually move them on the model fish (using "G" on the keyboard). The specific xyz location of the left eye camera can then be imported with the fish info ("Eye Cam Location") for reproducibility and consistency across eyes/individuals. Locations should be added as "1, x, y, z" (with 1 indicating a scale of 1). Users can change the size of the eyes through altering the scale value (although this does not change the eye camera size/resolution).  
![MoveEyes](https://github.com/user-attachments/assets/58aeb0a8-0ef8-4ba4-888b-17413b84a074)

![MoveEyes2](https://github.com/user-attachments/assets/039868d5-40b7-4147-879d-8985f03a1030)

### 3) Add bones
To map keypoint tracking data onto the model fish, users need to supply the name of keypoints and their proportional distance along the body (with the 1st point at 0). Keypoint names need to match the keypoints used in tracking. Here we will add four keypoints: Head, COM (centre-of-mass), Caudal, Tail, at the locations: 0.23, 0.6, 0.8. DigiFish will automatically add an end point at position 1.0 if it is not supplied the the user. Users can also add in segments which function like vertebrae, this helps increase or decrease the degree of bend on the fish. Here we will add 5 segments between the COM and Caudal, and 4 between the Caudal and Tail (COM: 5, Caudal:4). Ideally users should keep only one segment for the first two keypoints as DigiFish assumes a straighline vector between them. 

<img width="300" height="224" alt="Screenshot 2025-12-03 at 12 12 33" src="https://github.com/user-attachments/assets/def5e3f6-5ada-428d-ab85-65f5818a92a9" />

![AddBones](https://github.com/user-attachments/assets/48399954-7e84-41d0-86ee-f6fbbd00f19f)

### 4) Animate fish
To animate a model fish, users need to supply x-y (and optionally z) tracking data for each keypoint as a csv file. Column names must match the keypoint names used in the 'Add bones' stage and be followed by '.x', '.y' or '.z'. x-y data can be supplied in pixels (as it will be scaled by DigiFish using the supplied conversion) whilst z values should be provided in cms. If z is not supplied DigiFish assigns z as 1 cm as default.  

<img width="939" height="294" alt="Example csv" src="https://github.com/user-attachments/assets/6380a6fa-44cb-4f13-9f77-cc415ca04d80" />

[SLEAPTracks_Zebra1.csv](https://github.com/user-attachments/files/32949376/SLEAPTracks_Zebra1.csv)

If users wish to also animate pitch (head-up/down posture), the tracking file should also contain a 'pitch_deg' bearing column, with positive values indicating a head-up posture. This bearing value can be calculated using the following script and 3D tracking data of the first and second keypoints. 

_Example code for calculating pitch from 3D tracking data:_ [Code_pitch.py](https://github.com/user-attachments/files/32950388/Code_pitch.py)

CSV files are then added to DigiFish using the 'Animate fish' button on the DigiFish panel. Users supply smoothing values for the keypoints. DigiFish can work with different smoothing values for the different animation stages (posture, orient, move location), and users are encouraged to adjust these values until they are happy that the smoothness of the motion captures the real swimming behaviour of the fish being modelled. The smoothing function within DigiFish interacts with the frames per second of the tracking data, but broadly larger values remove more rapid changes in the data over time. Once 'OK' is clicked this step may take some time to implement. The eye tracking section can be left blank if these data are not available. 

<img width="1280" height="727" alt="AnimateFish" src="https://github.com/user-attachments/assets/63921830-421d-4f62-a511-c84cf7b65caa" />
This step moves the fish model to the correct location in the scene. 

<img width="1512" height="859" alt="Screenshot 2026-10-02 at 11 22 36" src="https://github.com/user-attachments/assets/54ad2fbb-1583-4cd6-9869-4f708930ba94" />

#### _Eye tracking data _
Eye tracking data must be imported as calculated angles with negative angles indicating that the eye faces inwards towards the snout, and positive angles outward towards the tail. These data should be supplied in a CSV file with two separately named columns and a 'frame_idx' column. These names can be supplied by the user in the DigiFish panel. A smoothing value will also need to be supplied for these data and can differ from those values supplied for the tracking (value will depend on the temporal resolution of the tracking data). 
<img width="282" height="305" alt="Screenshot 2026-10-02 at 11 33 51" src="https://github.com/user-attachments/assets/afee163c-8da6-4330-8b03-cea090b0e602" />

_Example code for calculating eye angles from tracking data:_ [Code_eyeangle.py](https://github.com/user-attachments/files/32956414/Code_eyeangle.py)









