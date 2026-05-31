#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
mkdir -p .deps
[ -d .deps/llama.cpp/.git ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp .deps/llama.cpp
PY="${PYTHON:-$ROOT/.venv/bin/python}"
CUDA_HOME="${CUDA_HOME:-$($PY - <<'PY'
import site
from pathlib import Path
for p in site.getsitepackages():
    d=Path(p)/'nvidia/cu13'
    if (d/'bin/nvcc').exists(): print(d); break
else: raise SystemExit('no venv nvidia/cu13 nvcc found')
PY
)}"
ln -sfn lib "$CUDA_HOME/lib64"
for x in libcudart libcublas libcublasLt; do
    f=$(find "$CUDA_HOME/lib" -maxdepth 1 -name "$x.so.*" | head -1)
    [ -n "$f" ] && ln -sfn "$(basename "$f")" "$CUDA_HOME/lib/$x.so"
done
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib:${LD_LIBRARY_PATH:-}"
cmake -S .deps/llama.cpp -B .deps/llama.cpp/build \
    -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=86 \
    -DCMAKE_CUDA_COMPILER="$CUDA_HOME/bin/nvcc" -DCUDAToolkit_ROOT="$CUDA_HOME" \
    -DCMAKE_CUDA_FLAGS="-DCCCL_DISABLE_CTK_COMPATIBILITY_CHECK" \
    -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON
cmake --build .deps/llama.cpp/build --config Release -j "$(nproc)" --target llama-bench llama-cli
