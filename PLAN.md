# Plan

## Birds eye

- Keep report reproducible: theory table + published refs + local GPU benchmarks.
- Use nbdev v3 only as static docs/README builder: notebooks/scripts in `nbs/`, config in `pyproject.toml`, no generated package.
- Use plain Python script for llama.cpp GGUF dtype/quant matrix.
- Keep large local deps/caches out of git.
- Keep each research project as its own numbered notebook under `nbs/`; `index.ipynb` is nbdev docs/README table of contents.

## Todo

- [x] Read handoff + current codebase state.
- [x] Build llama.cpp with CUDA from repo-local ignored deps.
- [x] Add llama.cpp benchmark harness.
- [x] Run Qwen3.5 GGUF quant matrix as disk/VRAM allows.
- [x] Append llama.cpp results to notebook.
- [x] Convert repo to nbdev v3 static docs.
- [x] Move benchmark harness back to plain script under `nbs/`.
- [x] Update CODE.md.
- [x] Add indoor 3D photo reconstruction research notebook.
- [x] Add indoor autonomous drone navigation/capture research notebook.
- [x] Move root research markdown notes into `nbs/` notebooks and sidebar.
- [x] Rename research notebooks to `01_`, `02_`, `03_` scheme and make `index.ipynb` a TOC.
- [ ] Optional: run Q5_K_M rows if more disk headroom is available.
