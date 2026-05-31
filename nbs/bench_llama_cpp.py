#!/usr/bin/env python
"""Local llama.cpp GGUF TPS benchmark.

Uses llama-bench JSONL rows:
- n_prompt > 0 => prompt eval / prefill proxy
- n_gen > 0 => decode TPS

Fresh benchmark runs replace the result JSONL before writing rows.
"""
import argparse, json, os, shutil, subprocess, sys, threading, time
from pathlib import Path

MATRIX = {
    "2B": ("unsloth/Qwen3.5-2B-GGUF", ["BF16", "Q8_0", "Q6_K", "Q4_K_M"]),
    "4B": ("unsloth/Qwen3.5-4B-GGUF", ["BF16", "Q8_0", "Q6_K", "Q4_K_M"]),
    "9B": ("unsloth/Qwen3.5-9B-GGUF", ["Q8_0", "Q6_K", "Q4_K_M"]),
}
DEFAULT_BENCH = Path(".deps/llama.cpp/build/bin/llama-bench")
DEFAULT_JSONL = Path("llama_cpp_tps_results.jsonl")

def repo_root(start=None):
    start = Path(start or Path.cwd()).resolve()
    for p in (start, *start.parents):
        if (p/"pyproject.toml").exists(): return p
    return Path.cwd().resolve()

def in_root(path, root):
    path = Path(path)
    return path if path.is_absolute() else root/path

def in_cwd(path):
    path = Path(path)
    return path if path.is_absolute() else Path.cwd()/path

def parse_args(argv=None):
    if argv is None and Path(sys.argv[0]).name == "ipykernel_launcher.py": argv = []
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile", choices=["smoke", "matrix"], default="smoke")
    p.add_argument("--list-matrix", action="store_true")
    p.add_argument("--sizes", help="comma list, e.g. 2B,4B,9B")
    p.add_argument("--quants", help="comma list, e.g. Q4_K_M,Q6_K,Q8_0,BF16")
    p.add_argument("--prompt-tokens", type=int, default=512)
    p.add_argument("--gen-tokens", type=int, default=256)
    p.add_argument("--repetitions", type=int, default=3)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--n-gpu-layers", type=int, default=-1)
    p.add_argument("--flash-attn", choices=["on", "off", "auto"], default="auto")
    p.add_argument("--llama-bench", type=Path, default=DEFAULT_BENCH)
    p.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    p.add_argument("--download-only", action="store_true")
    p.add_argument("--local-files-only", action="store_true")
    p.add_argument("--no-warmup", action="store_true")
    p.add_argument("--no-vram-sample", action="store_true")
    p.add_argument("--vram-interval", type=float, default=0.05)
    return p.parse_args(argv)

def csv_arg(s): return [x.strip() for x in s.split(",") if x.strip()] if s else None

def cases(args):
    sizes = csv_arg(args.sizes) or (["2B"] if args.profile == "smoke" else list(MATRIX))
    qfilter = set(csv_arg(args.quants) or (["Q4_K_M"] if args.profile == "smoke" else []))
    for size in sizes:
        repo, qs = MATRIX[size]
        for q in qs:
            if qfilter and q not in qfilter: continue
            yield size, repo, q, f"Qwen3.5-{size}-{q}.gguf"

def set_local_env(env, root):
    env.setdefault("HF_HOME", str(root/".hf")); env.setdefault("HF_HUB_CACHE", str(root/".hf/hub")); env.setdefault("HF_XET_CACHE", str(root/".hf/xet"))
    env.setdefault("XDG_CACHE_HOME", str(root/".cache")); env.setdefault("XDG_CONFIG_HOME", str(root/".config")); env.setdefault("HF_HUB_DISABLE_XET", "1")
    cuda = root/".venv/lib/python3.12/site-packages/nvidia/cu13"
    if cuda.exists():
        env.setdefault("CUDA_HOME", str(cuda))
        env["PATH"] = f"{cuda/'bin'}:{env.get('PATH','')}"
        env["LD_LIBRARY_PATH"] = f"{cuda/'lib'}:{root/'.deps/llama.cpp/build/bin'}:{env.get('LD_LIBRARY_PATH','')}"
    return env

def download(repo, file, local_only=False):
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(repo, file, local_files_only=local_only))

def gpu_used_mib():
    if not shutil.which("nvidia-smi"): return None
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True, timeout=2)
        return int(out.splitlines()[0].strip())
    except (subprocess.SubprocessError, ValueError, IndexError): return None

def run(cmd, env, sample_vram=True, interval=0.05):
    base = peak = gpu_used_mib() if sample_vram else None; stop = False
    def sampler():
        nonlocal peak
        while not stop:
            m = gpu_used_mib()
            if m is not None: peak = m if peak is None else max(peak, m)
            time.sleep(interval)
    th = threading.Thread(target=sampler, daemon=True) if sample_vram else None
    if th: th.start()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    out, err = p.communicate(); stop = True
    if th: th.join(timeout=1)
    if p.returncode:
        raise RuntimeError(f"llama-bench failed ({p.returncode})\ncmd: {' '.join(map(str, cmd))}\nstdout:\n{out[-4000:]}\nstderr:\n{err[-4000:]}")
    return out, err, base, peak

def bench(args, env, size, repo, quant, file, path):
    cmd = [str(args.llama_bench), "-m", str(path), "-p", str(args.prompt_tokens), "-n", str(args.gen_tokens), "-r", str(args.repetitions),
           "-t", str(args.threads), "-ngl", str(args.n_gpu_layers), "-fa", args.flash_attn, "-o", "jsonl"]
    if args.no_warmup: cmd.append("--no-warmup")
    out, err, base, peak = run(cmd, env, not args.no_vram_sample, args.vram_interval)
    rows = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
    if not rows: raise RuntimeError(f"no JSON rows from llama-bench\nstdout:\n{out[-2000:]}\nstderr:\n{err[-2000:]}")
    for r in rows:
        phase = "prefill" if r.get("n_prompt", 0) else "decode" if r.get("n_gen", 0) else "unknown"
        r.update(type="llama_cpp", phase=phase, size=size, repo=repo, file=file, quant=quant, command=cmd,
                 baseline_vram_mib=base, peak_vram_mib=peak, delta_peak_vram_mib=(peak-base if peak is not None and base is not None else None),
                 ms_per_token=(1000/r["avg_ts"] if r.get("avg_ts") else None))
    return rows

def print_case(row):
    vram = f", peak {row['peak_vram_mib']} MiB" if row.get("peak_vram_mib") is not None else ""
    print(f"{row['size']:>2} {row['quant']:>6} {row['phase']:<7} {row['avg_ts']:8.2f} tok/s {row['ms_per_token']:7.3f} ms/tok{vram}", flush=True)

def main(argv=None):
    root = repo_root(Path(__file__).resolve().parent if "__file__" in globals() else None)
    args = parse_args(argv)
    args.llama_bench = in_root(args.llama_bench, root)
    args.jsonl = in_cwd(args.jsonl)
    env = set_local_env(os.environ.copy(), root); os.environ.update(env)
    cs = list(cases(args))
    if args.list_matrix:
        for c in cs: print(" ".join(c))
        return
    if not args.download_only and not args.llama_bench.exists(): raise SystemExit(f"missing {args.llama_bench}; run {root/'build_llama_cpp.sh'}")
    args.jsonl.parent.mkdir(parents=True, exist_ok=True)
    if not args.download_only: args.jsonl.unlink(missing_ok=True)
    for size, repo, quant, file in cs:
        path = download(repo, file, args.local_files_only); print(f"model {size} {quant}: {path}", flush=True)
        if args.download_only: continue
        rows = bench(args, env, size, repo, quant, file, path)
        with args.jsonl.open("a") as f:
            for r in rows: f.write(json.dumps(r) + "\n")
        for r in rows: print_case(r)

if __name__ == "__main__": main()
