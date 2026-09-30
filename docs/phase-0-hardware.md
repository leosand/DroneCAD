# Phase 0: hardware and local model

Probes, model selection and benchmark for the reference workstation.

## 1. Reference hardware

| Item | Value |
|---|---|
| GPU | NVIDIA RTX 4070 Ti SUPER, 16,376 MiB of VRAM |
| CPU and memory | Intel Xeon W-2123 (4 cores, 8 threads), 31.7 GB of RAM |
| Software | Windows, Docker 29.7 (WSL2 backend, Linux containers), Ollama 0.34, Python 3.12, Blender 5.2 |

FreeCAD was not installed at probe time, so the FreeCAD MCP server was first run in a container. It was later replaced by a native install (FreeCAD 1.1.3).

## 2. Corrections to the original brief

- The reference host is Windows, not Linux. Equivalent probes were run with PowerShell.
- The tag `devstral:22b` does not exist. `qwen3-coder-next` is 52 GB, not about 16 GB.
- The bridge repository is `gazebosim/ros_gz`, not `ros2/ros_gz`.

## 3. Model decision matrix

| Rank | Model | Verdict | Reason |
|---|---|---|---|
| 1 | `devstral:22b` | Unavailable | The tag does not exist |
| 1b | `devstral-small-2:24b` | Rejected | 15 GB, no KV-cache margin |
| 2 | `gpt-oss:20b` | Adopted | 14 GB, strong tool calling, documented on 16 GB cards |
| 3 | `qwen3-coder-next` | Rejected | 52 GB |
| 4 | `gemma4:12b` | Fallback | Use it if the strict 1.5 GiB VRAM margin must win |

## 4. Runtime incident: crash on the default server

Loading `gpt-oss:20b` on an Ollama server that uses flash attention, an 8-bit KV cache and the `cuda_v13` backend crashes at initialization (`0xc0000409`, `CUDA error: shared object initialization failed` in `MUL_MAT`). This is a known upstream issue (Ollama #17380 and #18522). Other models on the same machine run fine.

Isolated attempts on a temporary server:

| Try | Configuration | Result |
|---|---|---|
| 1 | Flash attention off only | No crash, but the 8-bit KV cache requires flash attention |
| 2 | f16 KV cache only | Same crash |
| 3 | Flash attention off, f16 KV, `cuda_v13` | Crash in `MUL_MAT` |
| 4 | `cuda_v12` only | Crash in `MUL_MAT` |
| 5 | `cuda_v12`, flash attention off, f16 KV | Loads, but 24% on CPU at context 32768 |
| 6 | Same plus context 8192 | 100% GPU, stable. Retained. |

The workaround is a dedicated Ollama server on `127.0.0.1:11499` started by `scripts/start-ollama-gptoss.ps1` (see ADR-0007 in [../ARCHITECTURE.md](../ARCHITECTURE.md)).

## 5. Benchmark

```bash
OLLAMA_HOST=http://127.0.0.1:11499 ollama run --verbose gpt-oss:20b "Explain in 5 points how to export a URDF from Blender."
```

| Metric | Result |
|---|---|
| Generation rate | 115.44 tokens per second (1,189 tokens), target 40 or more |
| Prompt rate | 222.96 tokens per second (84 tokens) |
| Model | `gpt-oss:20b`, MXFP4, 13 GiB loaded, effective context 8192 |

## 6. VRAM margin with the model loaded

- `ollama ps`: 100% GPU, context 8192.
- `nvidia-smi`: 14,601 MiB used, 1,463 MiB free. That is about 5% under a strict 1.5 GiB margin and above 1.5 GB in decimal units. The KV cache is preallocated, so the value is stable after generation.
- If the strict margin must win, switch to `gemma4:12b`.

## 7. Reproduce

```bash
ollama pull gpt-oss:20b                                   # about 13 GB, once
powershell -NoProfile -File scripts/start-ollama-gptoss.ps1   # dedicated server
OLLAMA_HOST=http://127.0.0.1:11499 ollama ps
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
```
