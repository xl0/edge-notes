# Codebase state

Small research notebook project estimating memory-bandwidth-bound LLM decode TPS and comparing to published/local llama.cpp measurements.

## Files

- `report.ipynb`: Markdown-first report estimating decode TPS on Qualcomm Dragonwing IQ-9075, NVIDIA Jetson Orin platforms, NVIDIA GeForce RTX 3080 Laptop GPU (16GB), and NVIDIA GeForce RTX 5060. Includes assumptions, LaTeX bandwidth/TPS formulas, generated bandwidth/TPS tables, published LLM results, and a llama.cpp code cell that runs the GGUF matrix, averages appended runs, and renders a row-separated tok/s table.
- `build_llama_cpp.sh`: Reproducible repo-local llama.cpp CUDA build. Clones `ggml-org/llama.cpp` into ignored `.deps/`, uses CUDA compiler/libs from `.venv/lib/python3.12/site-packages/nvidia/cu13`, creates missing CUDA `.so` symlinks, and passes `CCCL_DISABLE_CTK_COMPATIBILITY_CHECK` because venv nvcc/runtime minor versions differ.
- `bench_llama_cpp.py`: Standalone llama.cpp GGUF benchmark harness. Downloads selected GGUF files through `huggingface_hub` into repo-local HF cache, runs `llama-bench -o jsonl`, tags prompt-eval rows as `prefill` and gen rows as `decode`, samples `nvidia-smi` peak VRAM, and appends enriched JSONL rows.
- `llama_cpp_tps_results.jsonl`: Generated raw/enriched llama.cpp rows for Qwen3.5 2B/4B/9B GGUF matrix on local RTX 3080 Laptop GPU. The notebook/benchmark appends rows here when run.
- `bench_env.sh`: Local benchmark env exports. Keeps HF/XDG/CUDA caches inside repo because `$HOME` is mostly read-only; exports llama.cpp/CUDA runtime paths.
- `.gitignore`: Ignores local uv venv, HF/XDG/CUDA caches, `.deps/`, bytecode, notebook checkpoints, and benchmark logs.
- `PLAN.md`: Current high-level plan/todo state.
- `AGENTS.md`: Local agent/project instructions.
- `test.md`, `test.py`: Scratch/unrelated leftovers.

## Current model

The report uses peak memory bandwidth as decode bottleneck:

$\mathrm{TPS}=\mathrm{BW}_{GB/s}/(P_B\cdot B_{param})$

Default edge estimate uses INT4 weights (`0.5 bytes/param`); INT8 and FP16 (`2 bytes/param`) also shown. Jetson AGX Orin 64GB is primary Jetson comparison point; Orin NX/Nano bandwidths included as notes. NVIDIA GeForce RTX 3080 Laptop GPU row uses 256-bit GDDR6 at 14Gbps effective = 448.0 GB/s. NVIDIA GeForce RTX 5060 row uses 128-bit GDDR7 at 28Gbps effective = 448.0 GB/s, with $299 MSRP / $349.99 current listing price noted.

Local RTX 3080 Laptop GPU llama.cpp matrix, `llama-bench` prompt eval 512 / gen eval 256 / repeats 3, all layers GPU, f16 KV, flash-attn auto. Decode tok/s:

- Qwen3.5-2B GGUF: BF16 91.16, Q8_0 145.81, Q6_K 153.02, Q4_K_M 182.76.
- Qwen3.5-4B GGUF: BF16 43.00, Q8_0 70.67, Q6_K 74.01, Q4_K_M 93.20.
- Qwen3.5-9B GGUF: Q8_0 41.89, Q6_K 44.02, Q4_K_M 58.91. BF16 skipped because 17.92GB GGUF exceeds local 16GB VRAM before KV/overhead.

Local HF cache now keeps only used GGUF repos: `unsloth/Qwen3.5-2B-GGUF`, `unsloth/Qwen3.5-4B-GGUF`, `unsloth/Qwen3.5-9B-GGUF`.
