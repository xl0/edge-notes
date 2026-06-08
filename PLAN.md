# Plan

## Birds eye

- Keep report reproducible: theory table + published refs + local GPU benchmarks.
- Use nbdev v3 only as static docs/README builder: notebooks/scripts in `nbs/`, config in `pyproject.toml`, no generated package.
- Use plain Python script for llama.cpp GGUF dtype/quant matrix.
- Keep large local deps/caches out of git.
- Maintain `3D-photo-research.md` as living research notes for indoor photo/video reconstruction and navigation exploration.
- Maintain `autonomous-drone-navigation-research.md` as living research notes for indoor autonomous drone mapping/capture exploration.

## Todo

- [x] Read handoff + current codebase state.
- [x] Build llama.cpp with CUDA from repo-local ignored deps.
- [x] Add llama.cpp benchmark harness.
- [x] Run Qwen3.5 GGUF quant matrix as disk/VRAM allows.
- [x] Append llama.cpp results to notebook.
- [x] Convert repo to nbdev v3 static docs.
- [x] Move benchmark harness back to plain script under `nbs/`.
- [x] Update CODE.md.
- [x] Add indoor 3D photo reconstruction research notes.
- [x] Add indoor autonomous drone navigation/capture research notes.
- [ ] Optional: run Q5_K_M rows if more disk headroom is available.
