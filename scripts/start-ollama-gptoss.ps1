# ============================================================
# start-ollama-gptoss.ps1: dedicated Ollama server for gpt-oss:20b
#
# Works around an upstream cuda_v13 / MXFP4 crash (Ollama issues #17380 and #18522,
# verified 2026-09-18). Any other Ollama server on the machine and its global
# settings stay untouched: this script only sets process-local variables.
#
# Usage : powershell -NoProfile -File scripts\start-ollama-gptoss.ps1
# Stop  : Get-NetTCPConnection -LocalPort 11499 -State Listen |
#           ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
# ============================================================
$ErrorActionPreference = 'Stop'

$env:OLLAMA_HOST            = '127.0.0.1:11499'  # dedicated DroneCAD port
$env:OLLAMA_LLM_LIBRARY     = 'cuda_v12'         # avoids the broken cuda_v13 MXFP4 kernel
$env:OLLAMA_FLASH_ATTENTION = '0'                # flash attention crashes gpt-oss here
$env:OLLAMA_KV_CACHE_TYPE   = 'f16'              # q8_0 requires flash attention
$env:OLLAMA_CONTEXT_LENGTH  = '8192'             # full GPU residency

Write-Host 'DroneCAD: dedicated Ollama server for gpt-oss:20b on http://127.0.0.1:11499'
Write-Host 'Press Ctrl+C to stop.'
& ollama serve
