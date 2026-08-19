# Plan

## Birds eye

- Run a 3-week drone research sprint that can support the next contract milestone without overclaiming.
- Shape client expectations toward feasible future milestones.
- Research three streams:
  - Local navigation: onboard SLAM / lidar / sensor fusion / emergency obstacle avoidance; hardest and most hardware-dependent, so keep conclusions conditional.
  - Autonomous navigation and exploration: PC-side planner consuming drone SLAM/state and deciding where to go next.
  - Photogrammetry: PC-side reconstruction of 3D environments from photos/video, possibly with sensor input.
- Prioritise hands-on progress in autonomous navigation and photogrammetry; local navigation may be solved or constrained by hardware providers.
- Use Isaac Sim/Pegasus to build hands-on drone skills and milestone evidence together. Emphasis shifted to local navigation/SLAM and sim↔real flight-hardware comms; photo-coverage/exploration-policy work demoted to an optional photogrammetry stream. Defer Isaac Lab/RL and manipulator Jacobian/IK work.
- Follow the block plan in `ISAAC_LESSONS.md` (B0–B5, build→measure→artifact): B0 flight/frames/controller (done), B1 native RGB/depth/lidar/IMU capture contract (in progress), B2 local mapping/SLAM with odometry-drift-vs-ground-truth and external-SLAM integration (spine), B3 PX4 SITL/MAVLink and HITL stretch, B4 optional coverage metric + policy comparison, B5 videos + report. Keep the honesty spine: label estimated-vs-ground-truth, freeze metrics before comparison, one negative control per claim. Center live work on Omniverse-kernel notebooks with explicit print/pprint and manual timeline control; promote stable scored artifacts to standalone scripts.

## Todo

- [x] Static SvelteKit quaternion lesson under `quaternion-lab/`: explicit learner model/outcomes and teaching plan; seven-part known-to-new sequence; restrained diagrams; prediction, manipulation, worked examples, recaps, scenario assessment, API checklist, and tested quaternion math. No backend runtime.

- [x] Week 1: GLEAM-first autonomous navigation pass.
  - [x] Cache/clone GLEAM locally under ignored deps.
  - [x] Install GLEAM-compatible Python/CUDA/Isaac Gym env.
  - [x] Build and import GLEAM CUDA extension `bfs_cuda_2D`.
  - [x] Smoke-test imports: Isaac Gym, Torch CUDA, Open3D, OpenCV, GLEAM.
  - [x] Get gated GLEAM-Bench eval data (`data_gleam/eval_128`).
  - [x] Get released GLEAM checkpoint.
  - [x] Run GLEAM evaluation with small `--num_envs` first.
  - [x] Run medium and full GLEAM evals; parse metrics.
  - [x] Capture GLEAM screenshots/logs for report.
  - [x] Write GLEAM ecosystem/state report: runtime assumptions, sensors, sim limits, 2D-vs-3D nav, dataset requirements.
  - [x] Explore NVIDIA Isaac ecosystem only as needed to understand/debug GLEAM: Isaac Gym first; Isaac Sim/Lab later.
  - [x] Pause Next Best Path, Habitat/Habitat-Sim, and extra paper/codebase search until GLEAM is running end-to-end.
- [ ] Week 2: Modify most promising approach.
  - [x] Install and headless-smoke-test Isaac Sim 6.0.1 in a dedicated conda env.
  - [ ] Finish only the Isaac Sim fundamentals needed for drones: frames/transforms, rigid-body physics, runtime state/control, simulation stepping, sensors, and debugging.
    - [x] Reverse-engineer the Isaac Sim VS Code execution bridge; retain both protocol sides and document framing, execution semantics, version changes, and security limits.
  - [ ] Cover robot kinematics only at a surface level; skip manipulator Jacobian/IK/reaching exercises for now.
  - [x] Evaluate Pegasus Simulator compatibility with Isaac Sim 6.0.1 and choose a reproducible install/version path.
    - [x] Install current Pegasus main (`bef3c57`) editably and capture its first Isaac 6.0.1 failure: removed `omni.isaac.dynamic_control` imported by `vehicle.py`.
    - [x] Select and install supported Isaac Sim 5.1.0 + Pegasus `v5.1.0` in the existing environment/path.
    - [x] Resolve Isaac 5.1 baseline RTX startup crash by downgrading driver 595.58.03 to 580.159.03; headless app, Dynamic Control, Pegasus import, and shutdown pass.
    - [x] Run empty-backend/sensor Iris for 500 steps, reset, and repeat; finite physical parameters/state and exact reset pose pass automatically.
  - [x] Run a working Pegasus Python-controller flight before low-level decomposition; trace state, force/torque allocation, rotor model, and motion.
    - [x] Run baseline upstream nonlinear-controller hover then 1 m east target with no PX4/sensors; automatic tracking/rotor gate passes.
  - [x] Verify state frames and simulation timing with independent physical fixtures, not conversion round trips alone.
  - [x] Stress the existing controller with one deliberate model mismatch/disturbance; defer custom altitude/attitude controller construction unless needed.
  - [x] B1: native RGB/depth/lidar/IMU capture contract. Camera static+moving mount + projection + stale-pose (`b1_1`/`b1_2`), lidar contract (`b1_3`), IMU fixture + Pegasus IMU bias audit (`b1_4`, three confirmed unreported bugs — don't file upstream, use our own corrected IMU model in B2).
    - [ ] Fixture defects surfaced while expanding the lesson theory, all diagnosed in-notebook: `b1_1` reprojection gate compares a point prediction against a 0.5 m cube's clipped silhouette centroid (swap for a small sphere); `b1_4` static gate sampled at t=1.3 s during the climb, so `‖f‖`=9.115 not g (sample later in the settle window); `b1_2`'s stored capture spans a stage rebuild (`image_age_s` negative — clear `captures` on rebuild); `b0_3` `physical_mass_kg` sets only the body link, true flying mass ≈2.12 kg by thrust/weight.
    - [ ] `b2_1`/`b1_3` plane gates score against wall *centre* planes while beams hit the near face 0.05 m closer — a constant bias that puts `b2_1`'s p95 (0.0632) over its 0.05 gate. Offset `PLANES` by half thickness.
  - [ ] B2 (spine): local mapping/SLAM. Back-projection done (`b2_1`, hand-rolled vs Isaac unproject cross-check + plane gate + injected-pose control; pending in-Kit run). Remaining: occupancy/voxel map from world points (`b2_2`, free/occupied/unknown), sensor-estimated odometry with drift vs Isaac ground truth (ATE/RPE) using our corrected Gauss-Markov IMU model, integrate one external SLAM stack (RTAB-Map / ORB-SLAM3 / lidar-odometry), loop-closure concept + one registration example.
  - [ ] VOXL software-in-the-loop on x86 (`voxl/NATIVE_BUILD.md`). Native builds are done:
        MPA transport, `voxl-hitl-vio-server` (Isaac→`qvio` verified), `voxl-mapper`,
        `voxl-vision-hub` (stubbed `libmodal-cv`), logger/replay, tag detector, streamer,
        mpa-tools. Remaining: writable `/etc/modalai`, then drive 14560 from Pegasus and
        attach a planner to `voxl-mapper`'s `plan_msgs` control pipe. Real qVIO and the
        camera pipeline stay out of the loop (closed `mvVISLAM`, Qualcomm-only codec).
  - [ ] B3 (exploratory): sim↔real flight hardware. Re-enable Pegasus PX4 backend, fly hover/waypoint through PX4 SITL over MAVLink, log state age per interface hop, compare native-vs-PX4 honestly; HITL with a real flight controller as stretch.
  - [ ] B4 (optional, photogrammetry only): simulate RGB/360 capture, define + freeze a reconstruction-aware coverage metric (visibility/range/incidence/footprint/overlap), compare frontier baseline vs coverage-aware policy under equal budgets + held-out seeds. Sensor-substitution (RGB vs lidar vs depth+IMU) and 3D-nav probing live here.
  - [ ] B5: produce representative videos + concise technical report; fold into `nbs/` alongside the GLEAM report.
  - [ ] Make it run on cloud GPUs (4× A6000) if the laptop is insufficient.
  - [ ] Defer Isaac Lab/RL unless a later learned-policy experiment creates a concrete need.
- [ ] Week 3: Decide based on week 1-2 results.
  - [ ] Decide whether to demo photogrammetry.
  - [ ] Decide whether to spend remaining time on photogrammetry, local navigation, or report integration.
  - [ ] Integrate technical reports into overall milestone report.
