# Codebase state

nbdev v3 static docs/report project estimating memory-bandwidth-bound LLM decode TPS and comparing to published/local llama.cpp measurements. Config lives in `pyproject.toml`; report notebooks/scripts live in `nbs/`; README is generated from `nbs/index.ipynb`. nbdev is used as static site/README builder, not as library generator.

## Files

- `nbs/index.ipynb`: README/docs landing notebook with a table of contents linking to numbered research notebooks.
- `nbs/01_edge_llm_tps.ipynb`: Edge LLM TPS research notebook. Markdown-first report estimating decode TPS on Qualcomm Dragonwing IQ-9075, NVIDIA Jetson Orin platforms, NVIDIA GeForce RTX 3080 Laptop GPU (16GB), and NVIDIA GeForce RTX 5060. Includes assumptions, LaTeX bandwidth/TPS formulas, generated bandwidth/TPS tables, published LLM results, a hidden manual benchmark cell, and a render cell that reads the single result file next to the notebook: `nbs/llama_cpp_tps_results.jsonl`. Fresh benchmark runs are not executed during README/docs render.
- `nbs/02_3d_photo_reconstruction.ipynb`: Markdown-only research notebook for indoor photo/video reconstruction into Google-Maps-like navigable house environments. Covers Matterport-style pano graphs, photogrammetry/SLAM meshes, 3D Gaussian Splatting, hybrid product architecture, capture constraints, hard problems, datasets, inline acronym/concept definitions, and recommended staged approach. Includes open-source/research/commercial reference links.
- `nbs/03_autonomous_drone_navigation.ipynb`: Markdown-only research notebook for indoor autonomous drone mapping/capture. Covers onboard-vs-PC autonomy split, nav vs HQ data streams, coverage/capture ledger data model, frontier/NBV planning, candidate drone/software stacks, safety constraints, simulation options, staged build plan, end-to-end/learned navigation research, references, and beginner study list.
- `nbs/04_ref_matrials.ipynb`: Markdown reference notebook for Matterport-like panorama navigation. Links Matterport demo, Marzipano/Pannellum baselines, notes missing smooth/live transitions, and starts pose-capture notes including ARKit/ARCore Wikipedia links.
- `README.md`: nbdev-generated GitHub-renderable report from `nbs/index.ipynb`.
- `nbs/bench_llama_cpp.py`: Plain llama.cpp GGUF benchmark script, intentionally not an nbdev notebook/export. Downloads selected GGUF files through `huggingface_hub`, resets the cwd-local result JSONL for fresh benchmark runs, runs `llama-bench -o jsonl`, tags prompt-eval rows as `prefill` and gen rows as `decode`, samples `nvidia-smi` peak VRAM, writes enriched JSONL rows. Uses repo root only for caches/CUDA/llama.cpp build paths; result file defaults to cwd-local `llama_cpp_tps_results.jsonl`.
- `pyproject.toml`: PEP 621 project metadata plus `[tool.nbdev]` config (`branch = "master"`, `nbs_path = "nbs"`, `doc_path = "_docs"`). No package/library export entry points; `[tool.setuptools] packages = []` keeps editable install metadata-only for docs deps.
- `nbs/nbdev.yml`, `nbs/_quarto.yml`, `nbs/sidebar.yml`, `nbs/styles.css`: nbdev/Quarto docs config. Sidebar lists landing page plus numbered research notebooks. GitHub Actions deploy docs to Pages.
- `.github/workflows/test.yaml`: Static-doc CI: install docs deps, run `nbdev-test`, `nbdev-clean`, `nbdev-readme`, then require clean git diff.
- `.github/workflows/deploy.yaml`: nbdev3 Quarto/GitHub Pages workflow.
- `build_llama_cpp.sh`: Reproducible repo-local llama.cpp CUDA build. Clones `ggml-org/llama.cpp` into ignored `.deps/`, uses CUDA compiler/libs from `.venv/lib/python3.12/site-packages/nvidia/cu13`, creates missing CUDA `.so` symlinks, and passes `CCCL_DISABLE_CTK_COMPATIBILITY_CHECK` because venv nvcc/runtime minor versions differ.
- `nbs/llama_cpp_tps_results.jsonl`: Tracked raw/enriched llama.cpp rows for Qwen3.5 2B/4B/9B GGUF matrix on local RTX 3080 Laptop GPU. Notebook reads this file directly; hidden benchmark cell/script replaces it at the start of fresh benchmark runs.
- `bench_env.sh`: Local benchmark env exports. Keeps HF/XDG/CUDA caches inside repo because `$HOME` is mostly read-only; exports llama.cpp/CUDA runtime paths.
- `.gitignore`: Ignores local uv venv, HF/XDG/CUDA caches, `.deps/`, nbdev build dirs, package build outputs, bytecode, notebook checkpoints, and logs.
- `LICENSE`: Apache-2.0.
- `PLAN.md`: Current high-level plan/todo state.
- `AGENTS.md`: Local agent/project instructions.

## Commands

- `nbdev-test`: execute notebooks.
- `nbdev-clean`: clean notebook metadata.
- `nbdev-readme`: update `README.md` from `nbs/index.ipynb`.
- `nbdev-docs`: build Quarto docs into ignored `_docs/`.
- `python nbs/bench_llama_cpp.py --profile smoke --list-matrix`: quick benchmark script smoke check.
- `(cd nbs && python bench_llama_cpp.py --profile matrix --prompt-tokens 512 --gen-tokens 256 --repetitions 3)`: replace `nbs/llama_cpp_tps_results.jsonl` with full local benchmark matrix after `./build_llama_cpp.sh`.

## Current model

The report uses peak memory bandwidth as decode bottleneck:

$\mathrm{TPS}=\mathrm{BW}_{GB/s}/(P_B\cdot B_{param})$

Default edge estimate uses INT4 weights (`0.5 bytes/param`); INT8 and FP16 (`2 bytes/param`) also shown. Jetson AGX Orin 64GB is primary Jetson comparison point; Orin NX/Nano bandwidths included as notes. Discrete GPU rows include NVIDIA GeForce RTX 3080 Laptop GPU (256-bit GDDR6 at 14Gbps effective = 448.0 GB/s), NVIDIA GeForce RTX 5060 (128-bit GDDR7 at 28Gbps effective = 448.0 GB/s, $299 MSRP / $349.99 listing), NVIDIA GeForce RTX 4090 (384-bit GDDR6X at 21Gbps effective = 1008.0 GB/s), and NVIDIA A100 80GB PCIe (5120-bit HBM2e at 3.2Gbps/pin effective = 2048.0 GB/s).

Local RTX 3080 Laptop GPU llama.cpp matrix, `llama-bench` prompt eval 512 / gen eval 256 / repeats 3, all layers GPU, f16 KV, flash-attn auto. Decode tok/s currently rendered in README/notebook from `nbs/llama_cpp_tps_results.jsonl`:

- Qwen3.5-2B GGUF: BF16 90.05, Q8_0 142.21, Q6_K 145.87, Q4_K_M 176.04.
- Qwen3.5-4B GGUF: BF16 41.99, Q8_0 66.11, Q6_K 48.23, Q4_K_M 44.30.
- Qwen3.5-9B GGUF: Q8_0 20.16, Q6_K 10.52, Q4_K_M 13.27. BF16 skipped because 17.92GB GGUF exceeds local 16GB VRAM before KV/overhead.

Local HF cache keeps only used GGUF repos: `unsloth/Qwen3.5-2B-GGUF`, `unsloth/Qwen3.5-4B-GGUF`, `unsloth/Qwen3.5-9B-GGUF`.
