# ============================================================
# start-ollama-gptoss.ps1 — Serveur Ollama dédié DroneCAD (gpt-oss:20b)
# EN: dedicated Ollama server for gpt-oss:20b — works around the upstream
#     cuda_v13/MXFP4 crash (ollama issues #17380 / #18522, verified 2026-09-18).
# FR : serveur Ollama dédié pour gpt-oss:20b — contourne le crash amont
#     cuda_v13/MXFP4 (tickets ollama #17380 / #18522, vérifié le 2026-09-18).
#
# Le serveur principal du poste (127.0.0.1:11480) et ses réglages globaux
# restent INTACTS — ce script n'exporte que des variables locales au processus.
# The machine's main server (127.0.0.1:11480) and its global settings stay
# UNTOUCHED — this script only sets process-local variables.
#
# Usage   : powershell -NoProfile -File scripts\start-ollama-gptoss.ps1
# Arrêt   : Get-NetTCPConnection -LocalPort 11499 -State Listen |
#             ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
# ============================================================
$ErrorActionPreference = 'Stop'

$env:OLLAMA_HOST           = '127.0.0.1:11499'  # port dédié DroneCAD / dedicated DroneCAD port
$env:OLLAMA_LLM_LIBRARY    = 'cuda_v12'         # évite le noyau MXFP4 cassé de cuda_v13 / avoids broken cuda_v13 MXFP4 kernel
$env:OLLAMA_FLASH_ATTENTION = '0'               # FA fait crasher gpt-oss ici / FA crashes gpt-oss here
$env:OLLAMA_KV_CACHE_TYPE  = 'f16'              # q8_0 exige FA / q8_0 requires FA
$env:OLLAMA_CONTEXT_LENGTH = '8192'             # résidence GPU complète / full GPU residency

Write-Host 'DroneCAD — serveur Ollama dédié gpt-oss:20b sur http://127.0.0.1:11499'
Write-Host 'Serveur principal :11480 non modifié. Ctrl+C pour arrêter.'
& ollama serve
