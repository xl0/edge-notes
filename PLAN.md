# Plan

## Birds eye

- Keep report reproducible: theory table + published refs + local GPU benchmarks.
- Use llama.cpp for GGUF dtype/quant matrix.
- Keep large local deps/caches out of git.

## Todo

- [x] Read handoff + current codebase state.
- [x] Build llama.cpp with CUDA from repo-local ignored deps.
- [x] Add llama.cpp benchmark harness.
- [x] Run Qwen3.5 GGUF quant matrix as disk/VRAM allows.
- [x] Append llama.cpp results to notebook.
- [x] Update CODE.md.
- [ ] Optional: run Q5_K_M rows if more disk headroom is available.
