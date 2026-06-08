# 3D photo reconstruction / indoor navigation research notes

Goal: understand practical + SOTA (state-of-the-art) options for turning many indoor house photos/videos into a Google-Maps-like navigable environment: room-scale navigation, between-room transitions, photoreal visuals, optional metric geometry.

## Core distinction

"Photo stitching" is not one problem. Current systems usually combine several layers:

- **Pose layer**: camera locations/orientations from SfM (Structure from Motion; recover camera poses + sparse 3D points from overlapping photos), SLAM (Simultaneous Localization and Mapping; track device pose while building map), VIO (Visual-Inertial Odometry; estimate motion from camera + inertial sensor), ARKit/ARCore phone augmented-reality tracking, or LiDAR (Light Detection and Ranging; active depth sensing).
- **Visual layer**: panoramas, textured mesh, NeRF (Neural Radiance Field; neural scene representation for novel-view rendering), or 3DGS (3D Gaussian Splatting; explicit Gaussian blobs rendered by rasterization).
- **Geometry layer**: mesh/depth/floorplan/walls/doors/floors for collision, scale, measurement.
- **Navigation layer**: waypoint graph, room/portal graph, navmesh.
- **Semantic layer**: rooms, doors, furniture, walkable regions, labels.

Important: photoreal rendering alone does not solve navigation. 3DGS/NeRF can look good while geometry remains fuzzy/non-metric.

## Main approaches

### 1. Matterport / virtual-tour style

Representation: discrete 360° panoramas connected by clickable waypoints, often with floorplan/dollhouse mesh.

Commercial references / demos:

- [Matterport](https://matterport.com/) — commercial baseline; strong example of pano graph + dollhouse UX (user experience). Demo: [Matterport sample tour](https://my.matterport.com/show/?m=jm5WwEA3HUN&log=0&help=0&nt=0&play=1&qs=0&brand=1&dh=1&tour=1&gt=1&hr=1&mls=0&mt=1&tagNav=1&pin=1&portal=1&f=1&fp=1&nozoom=0&search=1&wh=1&kb=1&lp=0&title=0&tourcta=1&vr=1).

  <iframe width="853" height="480" src="https://my.matterport.com/show/?m=jm5WwEA3HUN&log=0&help=0&nt=0&play=1&qs=0&brand=1&dh=1&tour=1&gt=1&hr=1&mls=0&mt=1&tagNav=1&pin=1&portal=1&f=1&fp=1&nozoom=0&search=1&wh=1&kb=1&lp=0&title=0&tourcta=1&vr=1" frameborder="0" allowfullscreen allow="xr-spatial-tracking; fullscreen; autoplay"></iframe>

- [Polycam](https://poly.cam/) — mobile-first consumer capture app; LiDAR/photo modes.
- [Zillow 3D Home](https://www.zillow.com/3d-home/) — simple real-estate pano-tour UX reference.

Open-source viewers / tour builders. 360 panorama tours are mature. Limitation: usually click-to-jump between pano nodes, not Matterport-like spatial/free-walk interpolation.

- [Marzipano](https://www.marzipano.net/) / [GitHub](https://github.com/google/marzipano) — strongest open-source baseline for multi-resolution web pano tours.
- [Pannellum](https://pannellum.org/) / [GitHub](https://github.com/mpetroff/pannellum) — lightweight MIT-licensed web panorama viewer with scene hotspots/tour configs.
- [Photo Sphere Viewer](https://photo-sphere-viewer.js.org/) / [GitHub](https://github.com/mistic100/Photo-Sphere-Viewer) — Three.js-based 360° viewer; good plugin ecosystem.
- [360 panorama tour viewer/editor](https://github.com/un0btanium/360-panorama-tour-viewer-and-editor) — Marzipano-based open-source editor/viewer; useful if editor UX matters.


Pros:

- Most robust product path.
- Browser-friendly.
- Navigation UX solved: node-to-node movement.
- Good for real estate / documentation.
- Avoids many free-view reconstruction artifacts.

Cons:

- Not true continuous free-walk 3D.
- Parallax wrong between panorama nodes.
- Usually needs capture discipline or dedicated hardware.

Use when reliability matters more than full 6DoF (six degrees of freedom; position `x,y,z` + orientation `roll,pitch,yaw`) movement.

### 2. Photogrammetry / SLAM mesh

Photogrammetry is mostly **solving a giant jigsaw puzzle of where cameras were**.

Each photo is a 2D projection of same 3D world. If same chair corner appears in 5 photos, system can ask: "where could these 5 cameras have been so this one 3D point lands at exactly these 5 pixel positions?" Do that for thousands/millions of points -> recover camera poses and a sparse 3D skeleton of room.

- same physical point seen from multiple views gives a ray from each camera;
- correct 3D point lies where rays intersect / nearly intersect;
- correct camera poses are ones that make all those intersections consistent;
- bundle adjustment nudges every camera + point until projected points land back on observed pixels.

Once cameras are known, dense geometry becomes easier: for each pixel, search along its camera ray for depth that makes nearby photos agree. Repeat over many images -> depth maps / dense point cloud. Fuse those depths -> mesh. Then paste original photos back onto mesh as texture.

SLAM is same family but online: while walking, estimate current camera motion and map at same time. VIO adds an IMU (inertial measurement unit; accelerometer/gyroscope motion cues). RGB-D (red-green-blue plus depth; color image plus depth image) and LiDAR add direct depth. Those extra sensors are extremely useful indoors because they give scale and stop drift.

Key mental split:

- **SfM/SLAM** answers: where was each camera?
- **MVS (Multi-View Stereo) / depth fusion** answers: where are surfaces?
- **texturing** answers: what color should surfaces have?
- **navmesh/waypoints** answer: where may user walk?

That last part is not output by photogrammetry. A pretty mesh can still have noisy floors, fused chair legs, holes, fake mirror geometry. Product needs separate cleanup/semantics for walkable areas, doors, rooms.

Indoor gotcha: algorithms want parallax + texture. Houses give blank walls, repeated doors, mirrors, glass, narrow corridors. More photos helps only if they add new viewpoints and stable features. RGB-D/VIO often helps more than bigger models.

Commercial tools worth knowing:

- [RealityCapture](https://www.capturingreality.com/) — strong commercial photogrammetry.
- [Agisoft Metashape](https://www.agisoft.com/) — commercial photogrammetry.
- [iPhone/iPad LiDAR + ARKit](https://developer.apple.com/augmented-reality/arkit/) — practical mobile RGB-D/VIO capture source.
- [ARCore](https://developers.google.com/ar) — Android AR/VIO stack.

Open-source tools:

- [COLMAP](https://colmap.github.io/) / [GitHub](https://github.com/colmap/colmap) — **offline** SfM/MVS baseline; common input to NeRF/3DGS pipelines. Can process ordered video frames, but not intended as live tracker.
- [OpenMVG](https://github.com/openMVG/openMVG) — **offline** multi-view geometry/SfM framework.
- [OpenMVS](https://github.com/cdcseacave/openMVS) — **offline** dense reconstruction from SfM outputs; often paired with OpenMVG.
- [Meshroom / AliceVision](https://github.com/alicevision/Meshroom) — **offline** node-based photogrammetry pipeline.
- [OpenDroneMap](https://github.com/OpenDroneMap/ODM) — **offline** photogrammetry stack; outdoor/drone-oriented but useful pipeline reference.
- [ORB-SLAM3](https://github.com/UZ-SLAMLab/ORB_SLAM3) — **real-time/online tracking** visual/visual-inertial SLAM research baseline using ORB (Oriented FAST and Rotated BRIEF; efficient local image features). Map quality is tracking-grade, not polished product mesh.
- [RTAB-Map](https://github.com/introlab/rtabmap) — **real-time/online** RTAB-Map (Real-Time Appearance-Based Mapping; graph-based SLAM); practical RGB-D, stereo, LiDAR robotics baseline. Can also optimize/export maps offline after capture.
- [Kimera](https://github.com/MIT-SPARK/Kimera) — **real-time/online research stack** for metric-semantic SLAM. Heavier integration burden; closer to robotics than turnkey photogrammetry.

Rule of thumb: **SfM/MVS/photogrammetry tools are offline and produce better final assets; SLAM/VIO tools are online and produce live poses/maps, often needing post-processing for nice meshes.**


Pros:

- Produces explicit geometry.
- Useful for measurements, floorplan, collision, room layout.
- Can feed game-engine/web navigation.

Cons:

- Indoor scenes are hard: blank walls, repetition, mirrors, glass, glossy surfaces, narrow corridors.
- Photoreal quality often worse than source photos/3DGS.
- Mesh cleanup can be required.

Use when metric structure and navigability matter.

### 3. Neural rendering: NeRF and 3D Gaussian Splatting

Current visual SOTA for practical use is **3DGS (3D Gaussian Splatting)** more than vanilla NeRF.

Pipeline: photos/video -> camera poses from SfM/SLAM -> optimize radiance representation -> real-time novel-view rendering.

Core papers / project pages:

- [3D Gaussian Splatting for Real-Time Radiance Field Rendering](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) — original 3DGS paper/project.
- [3DGS official code](https://github.com/graphdeco-inria/gaussian-splatting) — reference implementation.
- [Nerfstudio](https://github.com/nerfstudio-project/nerfstudio) — open toolkit for NeRF/3DGS workflows.
- [Nerfstudio Splatfacto docs](https://docs.nerf.studio/nerfology/methods/splat.html) — practical 3DGS model in Nerfstudio.
- [gsplat](https://github.com/nerfstudio-project/gsplat) — CUDA (NVIDIA GPU programming/runtime stack) rasterization library used by Nerfstudio; good base for custom 3DGS training/rendering.
- [instant-ngp](https://github.com/NVlabs/instant-ngp) — older but important real-time NeRF/hash-grid baseline.

Open-source 3DGS implementations / pipelines:

- [OpenSplat](https://github.com/pierotofy/opensplat) — C++ 3DGS pipeline; takes COLMAP/OpenSfM/OpenMVG/Nerfstudio-style inputs.
- [gaussian-splatting-lightning](https://github.com/yzslab/gaussian-splatting-lightning) — PyTorch Lightning research framework.
- [Gaussian Splatting Toolkit](https://github.com/Gaussian-Splatting-Toolkit/Gaussian-Splatting-Toolkit) — toolkit for training/evaluation variants.
- [Gaussian splatting pipeline](https://github.com/VincentChoi33/gaussian-splatting-pipeline) — end-to-end video/photos -> COLMAP/LightGlue -> compressed splats; useful pipeline reference.
- [InstantSplat](https://github.com/NVlabs/InstantSplat) — sparse-view/generalizable splatting research code.
- [FreeSplat](https://github.com/wangys16/freesplat) — feed-forward/generalizable 3DGS research thread.

Web viewers / deployment:

- [SuperSplat](https://github.com/playcanvas/super-splat) — PlayCanvas open-source 3DGS editor.
- [SuperSplat Viewer](https://github.com/playcanvas/supersplat-viewer) — self-hostable web viewer for splats.
- [SuperSplat docs](https://developer.playcanvas.com/user-manual/gaussian-splatting/editing/supersplat/) — useful practical docs.
- [Kevin Kwok WebGL splat viewer](https://antimatter15.com/splat/) / [GitHub](https://github.com/antimatter15/splat) — minimal browser splat viewer reference.

Pros:

- Very photorealistic.
- 3DGS renders fast, often real-time.
- Better practical latency than classic NeRF.
- Handles view-dependent appearance better than textured mesh.

Cons:

- Needs good poses or joint pose optimization.
- Geometry can be fuzzy / non-physical.
- Navigation/collision not directly available.
- Large houses need chunking/streaming.
- Browser/mobile renderer less mature than pano tours.
- Mirrors/glass/lighting changes remain hard.

Use for visuals, not as sole navigation substrate.

### Relation between photogrammetry and neural rendering

Photogrammetry/SLAM and neural rendering are not competing replacements. Usually they are **two stages in same pipeline**.

Photogrammetry/SLAM first answers: **where were cameras?** Neural rendering then asks: **given those cameras and images, what scene representation best reproduces the photos from new viewpoints?**

Typical 3DGS/NeRF pipeline:

1. Capture photos/video.
2. Run SfM/SLAM to estimate camera poses.
3. Initialize sparse geometry from SfM point cloud or RGB-D depth.
4. Optimize neural/gaussian scene so rendered views match source photos.
5. Render novel views from new camera positions.

So COLMAP often appears inside neural-rendering workflows. Nerfstudio, original 3DGS code, OpenSplat, etc. commonly take COLMAP outputs: camera intrinsics, camera extrinsics, sparse points.

Key difference is output:

- **Photogrammetry output**: mesh/point cloud/depth. Explicit geometry. Good for measurement, collision, floorplans, navmesh. Looks okay, often not photoreal.
- **Neural-rendering output**: radiance field / gaussian splats. Optimized for making images. Looks great. Geometry may be approximate, fuzzy, or non-physical.

Mental model:

> Photogrammetry is surveying. Neural rendering is cinematography.

Surveying gives map/structure. Cinematography gives convincing views. For indoor navigation product, likely need both: photogrammetry/SLAM for pose + coarse walkable geometry; 3DGS/NeRF for visual layer.

Important nuance: some newer systems blur boundary. Gaussian SLAM, pose-free 3DGS, RGB-D 3DGS, SDF+Gaussian hybrids jointly optimize pose, geometry, and appearance. But product-wise same split remains useful: **metric/navigation layer** vs **photoreal rendering layer**.

## SOTA indoor / reconstruction research to track

Indoor-specific 3DGS/SfM/SLAM is active. Useful papers/projects:

- [OmniIndoor3D](https://ucwxb.github.io/OmniIndoor3D/) / [arXiv](https://arxiv.org/abs/2505.20610) / [GitHub](https://github.com/ucwxb/OmniIndoor3D) — indoor 3DGS with appearance + geometry + panoptic reconstruction from consumer RGB-D.
- [IndoorGS](https://openaccess.thecvf.com/content/CVPR2025/papers/Ruan_IndoorGS_Geometric_Cues_Guided_Gaussian_Splatting_for_Indoor_Scene_Reconstruction_CVPR_2025_paper.pdf) — geometric cues guided 3DGS for indoor scenes; tackles low texture/repetition.
- [NopeRoomGS](https://openreview.net/forum?id=SoPSI570Ap) — pose-free indoor 3DGS optimization; useful if capture poses are unreliable.
- [ActiveSplat](https://li-yuetao.github.io/ActiveSplat/) / [arXiv](https://arxiv.org/abs/2410.21955) — active indoor reconstruction using Gaussian splatting + planning.
- [FreeSplat++](https://arxiv.org/pdf/2503.22986) — efficient/generalizable indoor whole-scene 3DGS.
- [On-the-fly reconstruction for large-scale NVS (Novel View Synthesis; render views from camera poses not present in source photos) from unposed images](https://repo-sam.inria.fr/nerphys/on-the-fly-nvs/) — unposed image reconstruction + 3DGS direction.

Gaussian SLAM / RGB-D reconstruction:

- [MonoGS](https://github.com/muskie82/MonoGS) — monocular/stereo/RGB-D Gaussian Splatting SLAM; CVPR (Computer Vision and Pattern Recognition conference) 2024 highlight.
- [Splat-SLAM](https://github.com/google-research/Splat-SLAM) — RGB-only SLAM with 3D Gaussian representation and globally optimized dense geometry/rendering.
- [GauS-SLAM](https://github.com/gaus-slam/gaus-slam) — dense RGB-D SLAM with Gaussian surfels.
- [GS-ICP-SLAM](https://github.com/Lab-of-AI-and-Robotics/GS-ICP-SLAM) — RGB-D Gaussian Splatting SLAM with ICP (Iterative Closest Point; point-cloud/depth-frame alignment) style tracking.
- [GPS-SLAM](https://github.com/MisEty/GPS-SLAM) — Gaussian + SDF (signed distance field; volumetric geometry storing distance to nearest surface) hybrid SLAM; interesting because SDF helps geometry while Gaussians help appearance.
- [VTGaussian-SLAM](https://github.com/pengchongH/VTGaussian-SLAM) — RGB-D SLAM for large indoor scenes with view-tied Gaussians.
- [4DGS-SLAM](https://github.com/yanyan-li/4DGS-SLAM) — dynamic-scene Gaussian SLAM.
- [SEGS-SLAM](https://github.com/leaner-forever/SEGS-SLAM) — structure-enhanced 3DGS SLAM using ORB-SLAM3.
- [DenseSplat](https://github.com/DrLi-Ming/DenseSplat) — sparse-keyframe densification with 3DGS/NeRF priors.

## Datasets / benchmarks

Useful for testing indoor reconstruction assumptions before collecting houses:

- [ScanNet](http://www.scan-net.org/) — RGB-D indoor scans with semantic labels.
- [ScanNet++](https://kaldir.vc.in.tum.de/scannetpp/) — higher-fidelity RGB-D / DSLR (digital single-lens reflex camera) indoor dataset.
- [Matterport3D](https://niessner.github.io/Matterport/) — large-scale indoor RGB-D panoramas/mesh dataset; common for navigation/semantic tasks.
- [Replica](https://github.com/facebookresearch/Replica-Dataset) — high-quality synthetic/realistic indoor scenes.
- [TUM RGB-D](https://cvg.cit.tum.de/data/datasets/rgbd-dataset) — classic TUM (Technical University of Munich) RGB-D SLAM benchmark.
- [7-Scenes](https://www.microsoft.com/en-us/research/project/rgb-d-dataset-7-scenes/) — RGB-D relocalization benchmark.
- [Habitat](https://github.com/facebookresearch/habitat-sim) — simulator for embodied navigation; useful if converting scans to navigable environments.

## Likely best architecture for house-scale product

Hybrid:

1. Capture RGB-D/video when possible, normal photos otherwise.
2. Estimate camera poses with SLAM/SfM/VIO; use depth/LiDAR to stabilize scale and low-texture areas.
3. Build coarse geometry: floor, walls, openings, maybe room mesh.
4. Build room/portal/waypoint graph or navmesh.
5. Train/render 3DGS chunks per room/area for photoreal visuals.
6. Use panorama/waypoint anchors as robust UX fallback.

Short version:

> 3DGS for visuals + coarse mesh/depth/floorplan for navigation + pano/waypoint graph for reliable UX.

## Product tiers

### Tier A: practical baseline

Matterport-like node graph:

- 360 panorama / photos every 1-2m.
- Auto or manual graph edges.
- Optional floorplan/dollhouse.
- Browser viewer.

Best first product. Low technical risk.

### Tier B: photoreal controlled navigation

- Capture video/photos.
- Reconstruct poses.
- Train 3DGS per room/region.
- Navigate via waypoints; allow short interpolated motion.
- Keep graph constraints to avoid bad viewpoints.

Good compromise: modern visual quality without full free-flight burden.

### Tier C: free-walk indoor digital twin

- RGB-D SLAM with loop closure.
- Pose graph optimization.
- Depth fusion/coarse mesh.
- 3DGS visual layer with chunk streaming.
- Navmesh/collision.
- Room/door semantic graph.

Closest to "Google Maps inside house". Much harder.

## Capture constraints

Good capture matters more than model choice.

Need:

- 60-80% overlap.
- Slow continuous video or dense photo path.
- Loop closures: revisit prior areas.
- Doorways captured from both sides.
- Multiple viewpoints/heights for occlusions.
- Consistent lighting/exposure.
- No moving people/pets.
- Enough texture; add temporary visual markers if needed for research.

Avoid or special-case:

- Mirrors.
- Glass.
- TV screens.
- Glossy counters/floors.
- Repetitive blank walls/corridors.
- Open/closed door state changes during capture.

## Hard problems

- Pose drift across rooms/floors.
- Textureless walls and ceilings.
- Repeated features in corridors.
- Reflective/transparent surfaces.
- Thin geometry: chair legs, railings, doorframes.
- Occlusions behind/under furniture.
- Lighting baked into reconstruction.
- Cross-room alignment through narrow portals.
- Deriving walkable space from visual representation.
- Web/mobile streaming of large 3DGS scenes.

## Research threads / keywords

- Structure-from-Motion (SfM), COLMAP.
- VIO (Visual-Inertial Odometry), ARKit/ARCore.
- RGB-D SLAM, LiDAR SLAM, loop closure.
- 3DGS (3D Gaussian Splatting), large-scene 3DGS, chunked/streamed splats.
- Pose-free / pose-refinement 3DGS.
- Neural Radiance Fields (NeRF), instant-ngp, Zip-NeRF variants.
- Room segmentation, Manhattan-world indoor reconstruction.
- Floorplan extraction from RGB-D / point clouds.
- Navigation mesh generation from reconstructed geometry.
- Matterport-style panorama graph UX.

## Early recommendation

Do not start with unconstrained free-flight 3D reconstruction.

Start with a waypoint/panorama graph baseline, then add 3DGS as visual interpolation/immersion layer. In parallel, maintain a coarse metric geometry layer from depth/SLAM for floors/walls/doors/navigation.
