# Codebase state

nbdev v3 static docs/report project estimating memory-bandwidth-bound LLM decode TPS and comparing to published/local llama.cpp measurements. Config lives in `pyproject.toml`; report notebooks/scripts live in `nbs/`; README is generated from `nbs/index.ipynb`. nbdev is used as static site/README builder, not as library generator.

## Files

- `nbs/index.ipynb`: Main report/README source. Markdown-first report estimating decode TPS on Qualcomm Dragonwing IQ-9075, NVIDIA Jetson Orin platforms, NVIDIA GeForce RTX 3080 Laptop GPU (16GB), and NVIDIA GeForce RTX 5060. Includes assumptions, LaTeX bandwidth/TPS formulas, generated bandwidth/TPS tables, published LLM results, and a cwd-stable render cell that averages the newest `llama_cpp_tps_results.jsonl` found in cwd, `nbs/`, or repo root. Fresh benchmark runs are invoked separately via script, not during README/docs render.
- `README.md`: nbdev-generated GitHub-renderable report from `nbs/index.ipynb`.
- `nbs/bench_llama_cpp.py`: Plain llama.cpp GGUF benchmark script, intentionally not an nbdev notebook/export. Downloads selected GGUF files through `huggingface_hub`, resets the cwd-relative result JSONL for fresh benchmark runs, runs `llama-bench -o jsonl`, tags prompt-eval rows as `prefill` and gen rows as `decode`, samples `nvidia-smi` peak VRAM, writes enriched JSONL rows. Detects repo root from `pyproject.toml` for repo-local caches/build paths, but writes results relative to cwd unless `--jsonl` is absolute.
- `pyproject.toml`: PEP 621 project metadata plus `[tool.nbdev]` config (`branch = "master"`, `nbs_path = "nbs"`, `doc_path = "_docs"`). No package/library export entry points; `[tool.setuptools] packages = []` keeps editable install metadata-only for docs deps.
- `nbs/nbdev.yml`, `nbs/_quarto.yml`, `nbs/sidebar.yml`, `nbs/styles.css`: nbdev/Quarto docs config. GitHub Actions deploy docs to Pages.
- `.github/workflows/test.yaml`: Static-doc CI: install docs deps, run `nbdev-test`, `nbdev-clean`, `nbdev-readme`, then require clean git diff.
- `.github/workflows/deploy.yaml`: nbdev3 Quarto/GitHub Pages workflow.
- `build_llama_cpp.sh`: Reproducible repo-local llama.cpp CUDA build. Clones `ggml-org/llama.cpp` into ignored `.deps/`, uses CUDA compiler/libs from `.venv/lib/python3.12/site-packages/nvidia/cu13`, creates missing CUDA `.so` symlinks, and passes `CCCL_DISABLE_CTK_COMPATIBILITY_CHECK` because venv nvcc/runtime minor versions differ.
- `llama_cpp_tps_results.jsonl`: Tracked raw/enriched llama.cpp rows for Qwen3.5 2B/4B/9B GGUF matrix on local RTX 3080 Laptop GPU. Notebook can read this repo-root copy; benchmark script replaces its cwd-relative `--jsonl` target at the start of fresh benchmark runs.
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
- `python nbs/bench_llama_cpp.py --profile matrix --prompt-tokens 512 --gen-tokens 256 --repetitions 3`: replace results with full local benchmark matrix after `./build_llama_cpp.sh`.

## Current model

The report uses peak memory bandwidth as decode bottleneck:

$\mathrm{TPS}=\mathrm{BW}_{GB/s}/(P_B\cdot B_{param})$

Default edge estimate uses INT4 weights (`0.5 bytes/param`); INT8 and FP16 (`2 bytes/param`) also shown. Jetson AGX Orin 64GB is primary Jetson comparison point; Orin NX/Nano bandwidths included as notes. NVIDIA GeForce RTX 3080 Laptop GPU row uses 256-bit GDDR6 at 14Gbps effective = 448.0 GB/s. NVIDIA GeForce RTX 5060 row uses 128-bit GDDR7 at 28Gbps effective = 448.0 GB/s, with $299 MSRP / $349.99 current listing price noted.

Local RTX 3080 Laptop GPU llama.cpp matrix, `llama-bench` prompt eval 512 / gen eval 256 / repeats 3, all layers GPU, f16 KV, flash-attn auto. Decode tok/s currently rendered in README/notebook from `llama_cpp_tps_results.jsonl`:

- Qwen3.5-2B GGUF: BF16 90.54, Q8_0 144.82, Q6_K 152.77, Q4_K_M 182.38.
- Qwen3.5-4B GGUF: BF16 42.87, Q8_0 70.12, Q6_K 71.26, Q4_K_M 89.81.
- Qwen3.5-9B GGUF: Q8_0 40.33, Q6_K 39.62, Q4_K_M 49.21. BF16 skipped because 17.92GB GGUF exceeds local 16GB VRAM before KV/overhead.

Local HF cache keeps only used GGUF repos: `unsloth/Qwen3.5-2B-GGUF`, `unsloth/Qwen3.5-4B-GGUF`, `unsloth/Qwen3.5-9B-GGUF`.
