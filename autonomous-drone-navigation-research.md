# Autonomous indoor drone navigation / capture research notes

Goal: design a house-scale drone system that can fly indoors, build a live 3D navigation map, remember where it has already captured imagery, decide where more imagery is needed, and save high-quality data for offline reconstruction.

Core take: **split live navigation from final reconstruction.** Live nav needs conservative geometry and reliable pose at 10-100Hz. Final HQ reconstruction can use large images/video/depth offline, tolerate minutes-hours of compute, and reprocess after loop closure.

## System boundary

Do not make Wi-Fi + desktop PC responsible for low-level flight safety.

Correct split:

- **Flight controller**: IMU (inertial measurement unit)-rate stabilization, motor mixing, arming, failsafes. Use [PX4](https://px4.io/) or [ArduPilot](https://ardupilot.org/).
- **Onboard companion computer**: VIO (Visual-Inertial Odometry; camera + IMU pose tracking), LIO (LiDAR-Inertial Odometry; laser scanner + IMU pose tracking), RGB-D (red-green-blue plus depth) odometry, local obstacle map, local planner, collision gate, watchdogs, setpoint streaming to flight controller.
- **Ground PC**: global map backend, loop closure, NBV (Next-Best-View; choose next camera pose that adds most useful information) / capture planning, operator UI, HQ data upload/storage, offline [3DGS](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) (3D Gaussian Splatting; photoreal radiance representation) / photogrammetry.

PC can choose goals. Drone must survive PC/link loss: hover, land, or backtrack using onboard state.

Reason: [PX4 Offboard Mode](https://docs.px4.io/main/en/flight_modes/offboard) requires continuous setpoint/heartbeat stream and exits/failsafes if it stops; docs call out `>2Hz` proof-of-life and offboard-loss failsafe. [ArduPilot external navigation](https://ardupilot.org/dev/docs/mavlink-nongps-position-estimation.html) accepts external odometry / guided commands, but position control depends on continuing valid estimator input. Household Wi-Fi has multipath, dead zones, and latency spikes.

## Nav data vs HQ data

### Nav data

Used during flight. Must be small, fast, conservative.

Typical inputs:

- IMU at high rate.
- Stereo/depth frames or LiDAR (Light Detection and Ranging; active laser depth sensing) scans at 10-60Hz.
- Low-res RGB for VIO/features and semantic hints.
- Barometer/rangefinder/optical flow if useful.

Typical outputs:

- Odometry: `T_world_body`, velocity, covariance/confidence.
- Local map: occupancy / TSDF / ESDF voxel grid.
- Collision state: free/occupied/unknown around drone.
- Frontier/candidate goals.
- Capture ledger updates: which poses/surfaces have usable evidence.

Good nav map representations:

- **Occupancy grid**: unknown/free/occupied voxels; good for exploration/frontiers.
- **TSDF** (Truncated Signed Distance Field; voxel grid storing signed distance near surfaces): fused surface geometry; good reconstruction source. [nvblox](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox) and [Voxblox](https://github.com/ethz-asl/voxblox) are common robotics references.
- **ESDF** (Euclidean Signed Distance Field; voxel grid storing distance to nearest obstacle): good for collision checking/planning. [NVIDIA nvblox docs](https://nvidia-isaac-ros.github.io/v/release-4.4/concepts/scene_reconstruction/nvblox/technical_details.html) explicitly use TSDF for reconstruction and ESDF for planning.
- **Pose graph**: keyframes + constraints + loop closures; fixes drift. Often optimized with graph libraries like [GTSAM](https://gtsam.org/).
- **Topological graph**: rooms/doors/waypoints/frontiers; cheap global planning.

### HQ data

Used for final output. Can be large and delayed.

Typical inputs:

- Full-res JPEG/RAW stills.
- 4K/8K video if needed.
- 360° panorama shots if hardware supports it.
- Raw depth/RGB-D bursts where useful.
- Exact camera intrinsics/extrinsics, exposure, focus, rolling-shutter metadata.

HQ data policy:

- Store onboard first; upload opportunistically. Do not block flight on upload.
- Every frame must have timestamp, camera pose estimate, calibration version, stream id, quality metrics.
- Keep raw source even if live map later changes. Offline pipeline can rerun poses via SfM (Structure from Motion; estimate camera poses + sparse geometry from overlapping images), SLAM (Simultaneous Localization and Mapping; estimate pose while building map), or loop closure.

## Capture ledger: what “already took pictures here” means

Position-only visited markers are insufficient. Need surface/view coverage.

Track at least:

```text
Keyframe:
  id, time, T_world_cam, camera_id, intrinsics_id
  image_uri/depth_uri, nav_or_hq
  blur, exposure, focus, feature_count, tracking_confidence

Surface voxel / surfel / mesh facet:
  state: unknown/free/occupied/surface
  room_id, semantic_label optional
  obs_count_depth, obs_count_rgb
  best_ground_sample_distance_or_px_per_meter
  best_incidence_angle
  view_direction_histogram
  image_ids_that_observe_it
  confidence / needs_revisit

Candidate view:
  pose, yaw/pitch, camera mode
  expected_new_unknown_voxels
  expected_hq_surface_area_gain
  expected_overlap_with_existing_images
  path_cost, clearance_min, battery_cost
  risk flags
```

Coverage tests:

- **Nav coverage**: free space observed by rays, obstacle voxels seen, unknown frontiers reduced.
- **Reconstruction coverage**: each surface seen by multiple sharp RGB images, enough overlap, enough parallax, sane viewing angle, enough pixel density.
- **Room coverage**: every room/doorway/portal has topological connectivity and capture nodes.

For photogrammetry/3DGS, “seen once” is weak. Prefer 2-4+ good views per surface, different baselines, with 60-80% overlap between neighboring images. Doorways need both sides. Outdoor mission planners like [UgCS Photogrammetry Area](https://manuals-ugcs.sphengineering.com/docs/photogrammetry-area) show useful overlap/GSD (Ground Sample Distance; real-world distance per image pixel) concepts, though indoor flight geometry is different.

## Planning: exploration vs reconstruction capture

Two separate objectives:

1. **Explore safely**: find free space, avoid obstacles, discover rooms.
2. **Capture well**: choose views that improve final reconstruction.

Classical pipeline:

1. Maintain occupancy/ESDF from depth/LiDAR.
2. Find frontiers: boundary between known free space and unknown space.
3. Sample candidate drone poses near frontiers / around under-covered surfaces.
4. Reject unsafe poses: low clearance, unknown collision corridor, bad localization confidence.
5. Score remaining poses:
   - information gain: unknown voxels visible;
   - reconstruction gain: under-covered surface area visible;
   - quality: distance, angle, expected blur, lighting;
   - cost: path length/time/battery/risk.
6. Execute short local trajectory.
7. Stop/hover for HQ capture when needed.

Good first version: frontier exploration + surface coverage heuristic. Do not start with learned NBV.

Research / state-of-the-art threads:

- **RRT (Rapidly-exploring Random Tree) / next-best-trajectory**: [ExplorationRRT](https://github.com/LTU-RAI/ExplorationRRT) expands RRT branches and scores information gain along full candidate trajectories, not only endpoint frontiers.
- **NBV exploration planner**: [NBV Exploration Planner](https://github.com/RaccoonlabDev/nbv_exploration_planner) uses RRT-like tree search from current pose, gain over unmapped voxels, and history graph for revisiting old promising areas.
- **ActiveSplat**: [ActiveSplat](https://li-yuetao.github.io/ActiveSplat/) does active reconstruction with Gaussian map + sparse topological map; useful concept, not turnkey drone product.
- **GenNBV / NextBestPath**: [GenNBV](https://github.com/zjwzcx/GenNBV) and [NextBestPath](https://github.com/shiyao-li/NextBestPath) are learned NBV/path policies for active 3D reconstruction. Good research direction after classical baseline exists.

## Drone/sensor stack options

### Minimal practical indoor stack

- Small quad with prop guards / ducted frame.
- PX4 or ArduPilot flight controller.
- Onboard companion: [Jetson Orin Nano / Orin NX](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/), Intel [NUC](https://www.intel.com/content/www/us/en/products/details/nuc.html), or [ModalAI VOXL 2](https://www.modalai.com/products/voxl-2)-class board.
- Stereo/depth + IMU camera, e.g. [Intel RealSense D435i](https://www.intelrealsense.com/depth-camera-d435i/) / [D455](https://www.intelrealsense.com/depth-camera-d455/) class or [Luxonis OAK-D](https://shop.luxonis.com/products/oak-d)-class.
- Optional downward rangefinder / optical flow for altitude hold.
- Optional small LiDAR if payload/budget allow.

RGB-only monocular is possible in papers, brittle in houses. Blank walls, motion blur, mirrors, glossy cabinets, repeated doors -> tracking loss. Depth/stereo/LiDAR buys safety.

### LiDAR-inertial route

LiDAR + IMU is robust for geometry and GPS-denied odometry. [FAST-LIO](https://github.com/hku-mars/FAST_LIO/tree/ROS2) / FAST-LIO2 are common LIO baselines and have drone usage. Downsides: payload, cost, power, sparse texture/color; still need RGB/HQ capture for final visuals.

Good when safety/navigation matters more than tiny drone size.

### Stereo/RGB-D route

Stereo/depth camera gives nav geometry and RGB in one package. [RTAB-Map](https://introlab.github.io/rtabmap/) (Real-Time Appearance-Based Mapping; RGB-D/stereo/LiDAR SLAM with loop closure), [Isaac ROS Visual SLAM](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_visual_slam), nvblox, and [ORB-SLAM3](https://github.com/UZ-SLAMLab/ORB_SLAM3) variants can fit.

Good first product route if payload allows.

### Tiny drone route

[Crazyflie](https://www.bitcraze.io/products/crazyflie-2-1/) / [Crazyswarm2](https://imrclab.github.io/crazyswarm2/) is safer indoors and has ROS 2 (Robot Operating System 2; robotics middleware) / Gazebo workflows, but payload and image quality are poor. Useful for autonomy algorithms, not final photo capture.

## Candidate software stacks

### PX4 + ROS 2 + Isaac ROS

Likely best NVIDIA path:

- PX4 flight controller.
- [`px4_ros_com`](https://github.com/PX4/px4_ros_com) / [MAVSDK](https://mavsdk.mavlink.io/) / [MAVROS](https://github.com/mavlink/mavros) bridge. MAVLink (Micro Air Vehicle Link; common autopilot message protocol) carries telemetry, external odometry, and setpoints.
- [Isaac ROS Visual SLAM](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_visual_slam): GPU-accelerated stereo VIO/SLAM, can be primary odometry for drones.
- [Isaac ROS nvblox](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox): TSDF/ESDF local map from depth, collision planning substrate.
- Custom frontier/NBV planner on onboard or PC.
- [ROS 2 bag](https://docs.ros.org/en/rolling/Tutorials/Advanced/Recording-A-Bag-From-Your-Own-Node-CPP.html) recording for nav/HQ metadata.

Good if using Jetson and stereo/depth camera.

### PX4/ArduPilot + RTAB-Map

Practical RGB-D baseline:

- RGB-D odometry + loop closure with [RTAB-Map ROS](https://github.com/introlab/rtabmap_ros/).
- Occupancy/point cloud/2D grids for navigation.
- Bridge odometry to flight controller external-vision input.
- Works in sim and real with ROS 2, but tuning and frame conversions matter.

### ArduPilot + external nav

ArduPilot accepts MAVLink `ODOMETRY` / `VISION_POSITION_ESTIMATE` at >=4Hz for non-GPS EKF (Extended Kalman Filter; sensor-fusion estimator) position estimation. [Guided Mode](https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html) supports local NED (North-East-Down coordinate frame) position/velocity/attitude commands. Good if ArduPilot ecosystem preferred.

### Aerostack2

[Aerostack2](https://aerostack2.github.io/) is a ROS 2 aerial robotics framework integrating control, localization/mapping, planning, missions, simulation/real drones. Useful glue if wanting less custom orchestration.

### Research planners

- [ExplorationRRT](https://github.com/LTU-RAI/ExplorationRRT): 3D UAV exploration, RRT branch info gain + NMPC (Nonlinear Model Predictive Control; optimize feasible dynamic trajectories), occupancy map input.
- [NBV Exploration Planner](https://github.com/RaccoonlabDev/nbv_exploration_planner): real-time MAV (Micro Aerial Vehicle; small drone) next-best-view planner using Voxblox TSDF/ESDF style maps.
- [ActiveSplat](https://li-yuetao.github.io/ActiveSplat/) / [GenNBV](https://github.com/zjwzcx/GenNBV) / [NextBestPath](https://github.com/shiyao-li/NextBestPath): active reconstruction research, likely inspiration not first dependency.

## PC offload architecture

### Onboard must run

- Flight controller stabilization and failsafes.
- Odometry source fused into controller: VIO/LIO/optical flow/range.
- Local collision map within ~3-5m.
- Emergency local planner/collision shield.
- Setpoint stream / heartbeat to flight controller.
- Health monitors: tracking confidence, map age, IMU vibration, battery, link quality.
- Local data recorder.

### PC can run

- Global map optimization and loop closure.
- Large TSDF/point cloud/mesh accumulation.
- NBV scoring over whole house.
- Operator UI + approve/deny capture goals.
- HQ image upload, indexing, previews.
- Offline [COLMAP](https://colmap.github.io/) / 3DGS / MVS (Multi-View Stereo; dense geometry from multiple posed images) training.

### Link protocol split

- **Control/telemetry**: tiny, reliable, low latency. MAVLink/UDP, ROS 2/DDS (Data Distribution Service; ROS 2 middleware layer) over LAN, or custom UDP. Must have heartbeat and sequence numbers.
- **Nav streaming**: pose, compressed depth/point cloud/keyframes. Prefer derived/map data over raw full-res if bandwidth tight.
- **HQ media**: large. Store onboard; upload after flight/while idle.

Do not stream raw HQ video to PC and require PC to compute collision avoidance unless link is engineered like a safety-critical tether. Home Wi-Fi is not enough. PX4's [WFB-ng guide](https://docs.px4.io/main/en/companion_computer/video_streaming_wfb_ng_wifi) is a useful low-latency video/telemetry link reference, but it still should not be sole safety layer.

## Flight/capture workflow

### Recommended two-pass model

1. **Recon pass**
   - Slow autonomous/assisted exploration.
   - Build conservative map + room/door graph.
   - Record nav frames and opportunistic HQ frames.
   - Stop before risky tight spaces.

2. **Capture pass**
   - Use map to plan stable capture poses.
   - Fly waypoint graph, stop-and-shoot HQ images/panos.
   - Revisit under-covered surfaces.
   - Operator can approve risky viewpoints.

Single-pass autonomous capture is possible later, but harder: exploration and photogrammetry needs fight each other. Exploration likes speed/coverage; HQ capture likes stable hover, good lighting/focus, repeated views.

### Capture pose rules

- Fly slow: ~0.2-0.5m/s indoors during mapping.
- Stop for HQ stills; avoid motion blur/rolling shutter.
- Maintain clearance margin larger than drone radius + localization error + airflow disturbance.
- Capture at multiple heights for occlusions if safe.
- Doorways from both sides.
- Loop closures: revisit previous hallway/room nodes.
- Avoid mirrors/glass/TVs where possible; mark as special surfaces.
- Keep lighting constant; no people/pets moving.

## Safety constraints specific to houses

- Prop guards mandatory. Ducted micro quad preferred for first indoor tests.
- Physical kill switch / RC (radio control; handheld manual transmitter) override mandatory.
- Max speed/accel/yaw rate caps.
- Geofence / room boundary / max altitude.
- No flight near people, pets, curtains, plants, loose cables.
- Treat unknown space as occupied for collision, except explicitly chosen exploration frontiers with conservative speed.
- Keep return/backtrack path alive. Better: always know last safe corridor.
- Battery reserve for return/land, not just mission completion.

Pushback: autonomous indoor drones are noisy, risky, and fragile around household clutter. Validate capture/coverage with handheld or ground robot first if final product permits. Drone only needed for viewpoints not reachable otherwise.

## Simulation first

Useful stacks:

- [PX4 SITL](https://docs.px4.io/main/en/simulation/) (Software-In-The-Loop; run flight stack on computer) + [Gazebo](https://gazebosim.org/) `x500_depth` / `x500_vision` for depth/VIO drone simulation.
- [Pegasus Simulator](https://pegasussimulator.github.io/PegasusSimulator/) on [Isaac Sim](https://developer.nvidia.com/isaac/sim) for multirotor + PX4/ArduPilot integration and richer sensors.
- [AirSim](https://microsoft.github.io/AirSim/) for legacy Unreal drone simulation; project is being archived, still useful for old research code.
- [Habitat-Sim](https://github.com/facebookresearch/habitat-sim) for very fast indoor embodied navigation experiments on [Matterport3D](https://niessner.github.io/Matterport/) / [HM3D](https://aihabitat.org/datasets/hm3d/) / [Replica](https://github.com/facebookresearch/Replica-Dataset), but not full drone physics.

Sim goals:

- Validate data model and coverage ledger.
- Test frontier/NBV planner.
- Tune link-loss and estimator-loss behavior.
- Generate expected bandwidth/CPU budgets.
- Fail system safely before real props spin.

## Staged build plan

### Stage 0 — non-flying data prototype

- Handheld RGB-D camera or phone LiDAR.
- Record nav frames + HQ frames + poses.
- Implement capture ledger and coverage visualization.
- Offline reconstruct from recorded data.

### Stage 1 — sim drone

- PX4 SITL + Gazebo/Isaac depth drone.
- ROS 2 map: RTAB-Map or nvblox.
- Frontier planner.
- Coverage ledger.
- Link-loss/failsafe tests.

### Stage 2 — safe real hover/waypoints

- Prop-guarded drone.
- External ground truth optional: [AprilTag](https://april.eecs.umich.edu/software/apriltag/) fiducials, [Vicon](https://www.vicon.com/) motion capture, [SteamVR Lighthouse](https://en.wikipedia.org/wiki/SteamVR#Lighthouse) tracking for early tests.
- VIO/depth odometry to flight controller.
- One-room known-waypoint capture.

### Stage 3 — autonomous one-room exploration

- Unknown room.
- Frontier exploration with strict speed/clearance.
- PC shows live map + proposed next goals.
- HQ images stop-and-shoot.

### Stage 4 — multi-room map + capture

- Doorway handling.
- Loop closure.
- Room graph.
- Revisit under-covered surfaces.
- Offline 3DGS/photogrammetry chunked by room.

### Stage 5 — active reconstruction

- Replace heuristics with better NBV/active mapping.
- Add surface quality prediction.
- Maybe online splat/mesh confidence on PC.

## Key open problems

- VIO drift/loss on blank walls, repetitive doors, glossy surfaces.
- Odometry frame resets confusing flight controller unless bridged carefully.
- ENU (East-North-Up), NED, and FRD (Front-Right-Down body frame) frame bugs causing flyaways.
- Wi-Fi loss exactly when behind walls/around corners.
- Motion blur and rolling shutter during aggressive motion.
- Door state changes between passes.
- Dynamic objects baked into map.
- Coverage metric mismatch: nav map says complete, final 3DGS still has holes.
- Battery too short for whole-house capture; need multi-session relocalization.
- Sound/safety/liability make consumer indoor flight hard.

## Early recommendation

Build this as **onboard-safe autonomy + PC-assisted active capture**, not PC-flown drone.

Initial target:

- PX4 + Jetson/VOXL-class companion.
- Stereo/RGB-D + IMU.
- Onboard VIO + local ESDF.
- PC global planner/coverage UI.
- Stop-and-shoot HQ stills saved onboard.
- Classical frontier + coverage heuristics before learned NBV/ActiveSplat.

Shortest useful milestone: one-room autonomous map + capture ledger that correctly says: “wall behind couch under-covered; need view from doorway-left at 1.2m height, yaw 35°.”

## End-to-end deep learning / learned navigation

There is real progress, but fielded systems are still mostly hybrid. Learned policies are replacing parts of nav, not whole safety stack.

Main threads:

- **Visual nav foundation models**: [GNM](https://openreview.net/forum?id=s20TrAOus5ew), [ViNT](https://arxiv.org/abs/2306.14846), [NoMaD](https://arxiv.org/abs/2310.07896). Camera history + goal image -> short-horizon waypoints/actions. Strong real-robot results; still use topological graphs/frontiers for long horizon.
- **Neural SLAM / learned exploration**: [Active Neural SLAM](https://arxiv.org/abs/2004.05155), [DD-PPO](https://arxiv.org/abs/1911.00357). Shows pure RL can work in sim with huge data, but modular learned mapper + planner is more sample-efficient and robust.
- **Drone agile flight**: [Learning high-speed flight in the wild](https://www.science.org/doi/10.1126/scirobotics.abg5810), [Swift drone racing](https://www.nature.com/articles/s41586-023-06419-4). DL shines in local control/racing/obstacle avoidance. Swift is hybrid: VIO + gate detector + Kalman filter + RL controller.
- **Vision-language navigation**: [VLFM](https://arxiv.org/abs/2312.03275), [Mobility VLA](https://arxiv.org/abs/2407.07775), [NaVILA](https://arxiv.org/html/2412.04453v1), [VLMnav](https://arxiv.org/abs/2411.05755). Useful for semantic goals (“inspect kitchen counter”), not safety-critical low-level flight.
- **Drone survey**: [Vision-Based Learning for Drones](https://arxiv.org/html/2312.05019v2) categorizes indirect, semi-direct, and end-to-end approaches.

Why not full E2E (end-to-end) yet: safety proofs weak, OOD (out-of-distribution) failures, sim-to-real gap, long-horizon memory/coverage, limited crash data, hard debugging. For this project: use learned models for semantic understanding, capture-quality prediction, frontier/NBV scoring, local affordances; keep VIO/LIO + ESDF + flight-controller failsafes classical.

## References

Autopilot/control:

- [PX4 Offboard Mode](https://docs.px4.io/main/en/flight_modes/offboard) — external setpoints, >2Hz proof-of-life, offboard-loss failsafe.
- [PX4 Visual Inertial Odometry](https://docs.px4.io/main/en/computer_vision/visual_inertial_odometry) — VIO into PX4 EKF, external vision tuning.
- [PX4 Path Planning Interface](https://px4.gitbook.io/px4-user-guide/drone_parts/companion_computer/computer_vision/path_planning_interface) — companion-side planning setpoint interface, heartbeat/fallback behavior.
- [PX4 WFB-ng WiFi video/telemetry link](https://docs.px4.io/main/en/companion_computer/video_streaming_wfb_ng_wifi) — low-latency Wi-Fi broadcast transport reference.
- [ArduPilot Non-GPS Position Estimation](https://ardupilot.org/dev/docs/mavlink-nongps-position-estimation.html) — external nav via MAVLink `ODOMETRY`, >=4Hz.
- [ArduPilot Guided Mode commands](https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html) — MAVLink local/global setpoint commands.

Mapping/SLAM:

- [Isaac ROS Visual SLAM](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_visual_slam) — GPU stereo VIO/SLAM; docs say usable as primary drone odometry source.
- [Isaac ROS nvblox technical details](https://nvidia-isaac-ros.github.io/v/release-4.4/concepts/scene_reconstruction/nvblox/technical_details.html) — TSDF/ESDF layers for reconstruction and planning.
- [RTAB-Map ROS](https://github.com/introlab/rtabmap_ros/) — ROS 2 RGB-D/stereo/3D LiDAR SLAM wrapper.
- [FAST-LIO ROS2](https://github.com/hku-mars/FAST_LIO/tree/ROS2) — LiDAR-inertial odometry baseline with UAV examples.
- [COLMAP](https://colmap.github.io/) — offline SfM/MVS baseline used by many 3DGS/photogrammetry pipelines.
- [ORB-SLAM3](https://github.com/UZ-SLAMLab/ORB_SLAM3) — visual / visual-inertial SLAM research baseline.

Autonomy/frameworks/planning:

- [Aerostack2](https://aerostack2.github.io/) — ROS 2 framework for aerial robot autonomy.
- [ExplorationRRT](https://github.com/LTU-RAI/ExplorationRRT) — tree-based next-best-trajectory method for 3D UAV exploration.
- [NBV Exploration Planner](https://github.com/RaccoonlabDev/nbv_exploration_planner) — real-time MAV next-best-view planner.
- [ActiveSplat](https://li-yuetao.github.io/ActiveSplat/) — active Gaussian-splatting reconstruction with online mapping/planning.
- [GenNBV](https://github.com/zjwzcx/GenNBV) — CVPR (Computer Vision and Pattern Recognition conference) 2024 generalizable NBV policy.
- [NextBestPath](https://github.com/shiyao-li/NextBestPath) — ICLR (International Conference on Learning Representations) 2025 next-best-path active mapping.

Simulation:

- [PX4 Gazebo Simulation](https://px4.gitbook.io/px4-user-guide/development/simulation/sim_gazebo_gz.md) — `x500_depth`, `x500_vision`, SITL.
- [Pegasus Simulator](https://pegasussimulator.github.io/PegasusSimulator/) — Isaac Sim multirotor simulator with PX4 integration.
- [AirSim](https://microsoft.github.io/AirSim/) — Unreal drone simulator, legacy/archived but still useful.
- [Habitat-Sim](https://github.com/facebookresearch/habitat-sim) — high-speed indoor embodied AI simulator over Matterport/HM3D/Replica scenes.

Photogrammetry capture:

- [UgCS Photogrammetry area](https://manuals-ugcs.sphengineering.com/docs/photogrammetry-area) — overlap/GSD/flight-grid concepts, useful though outdoor-oriented.

## Study list for autonomous navigation beginners

Best path: learn ground-robot navigation first. Same loop: localization → mapping → planning → control. Drone adds 3D motion, tighter safety, worse odometry, shorter time budgets.

### Watch first

1. [MathWorks Autonomous Navigation video series](https://www.mathworks.com/videos/series/autonomous-navigation.html) — best beginner overview. Covers localization, particle filters, SLAM/pose graphs, A* and RRT path planning.
2. [Cyrill Stachniss online mobile robotics / SLAM training](https://www.ipb.uni-bonn.de/online-training-robotics/) — excellent free SLAM lectures. More academic, worth it.
   - [Occupancy Grid Maps](https://www.youtube.com/watch?v=v-Rm9TUG9LA)
   - [EKF-SLAM](https://www.youtube.com/watch?v=X30sEgIws0g)
   - [Robot Mapping course page](https://www.ipb.uni-bonn.de/robot-mapping/)
3. [How Visual Inertial Odometry & SLAM Work](https://sparks.learning.asu.edu/videos/how-visual-inertial-odometry-slam-work) — good intuition for camera + IMU tracking.
4. [Path Planning with A* and RRT](https://www.mathworks.com/videos/autonomous-navigation-part-4-path-planning-with-a-and-rrt-1594987710455.html) — quick path-planning mental model.

### Read next

5. [PX4 Visual Inertial Odometry](https://docs.px4.io/main/en/computer_vision/visual_inertial_odometry) — practical drone-specific VIO into flight controller.
6. [PX4 Offboard Mode](https://docs.px4.io/main/en/flight_modes/offboard) — crucial: why Wi-Fi PC should not directly fly drone.
7. [ModalAI Flying with VIO](https://docs.modalai.com/flying-with-vio/) — concrete drone VIO setup.
8. [Visual Inertial Odometry Explained](https://www.thinkautonomous.ai/blog/visual-inertial-odometry/) — accessible VIO article.
9. [What is an Occupancy Grid Map?](https://automaticaddison.com/what-is-an-occupancy-grid-map/) — basic free/occupied/unknown map representation.
10. [Frontier-Based Exploration](https://awabot.com/en/autonomous-exploration-method-frontiers/) — core “where do we go next?” exploration idea.

### Hands-on software docs

11. [ROS 2 Nav2 Getting Started](https://docs.nav2.org/getting_started/index.html) — ground robot stack, but core map/costmap/planner/controller concepts transfer.
12. [ROS2 Nav2 Tutorial](https://roboticsbackend.com/ros2-nav2-tutorial/) — practical walkthrough.
13. [RTAB-Map ROS](https://github.com/introlab/rtabmap_ros/) — practical RGB-D/stereo SLAM stack.
14. [Isaac ROS Visual SLAM](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_visual_slam) — NVIDIA/Jetson path for stereo VIO.
15. [Isaac ROS nvblox RealSense tutorial](https://nvidia-isaac-ros.github.io/concepts/scene_reconstruction/nvblox/tutorials/tutorial_realsense.html) — depth → 3D reconstruction + collision map.

### Drone-specific examples

16. [GAAS: Using SLAM in GPS-denied drone environment](https://gaas.gitbook.io/guide/software-realization-build-your-own-autonomous-drone/build-your-own-autonomous-drone-part-3-using-slam-in-gps-denied-environment-for-position-estimation) — older, useful bridge between PX4, ROS, and SLAM.
17. [GPS-denied UAV with Visual SLAM](https://www.andrewbernas.com/docs/tutorials/robots/vslam) — modern-ish practical stack: Isaac ROS VSLAM + MAVROS + PX4.
18. [PX4 Developer Summit: Non-GPS Indoor Navigation](https://www.youtube.com/watch?v=VEXTClBmN4M) — drone-specific overview.

### Later / advanced

19. [ExplorationRRT](https://github.com/LTU-RAI/ExplorationRRT) — next-best-trajectory exploration for UAVs.
20. [ActiveSplat](https://li-yuetao.github.io/ActiveSplat/) — active reconstruction + Gaussian splatting.
21. [GenNBV](https://github.com/zjwzcx/GenNBV) — learned next-best-view; read after classical frontier/RRT makes sense.

Suggested order: MathWorks series → occupancy grids + frontier exploration → Stachniss SLAM lectures → PX4 VIO/Offboard docs → Nav2 or RTAB-Map hands-on → Isaac ROS/nvblox if using Jetson → ExplorationRRT/ActiveSplat later.
