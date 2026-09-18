# Phase 0 — Détection matérielle & sélection du modèle local

> Exécuté le **2026-09-18** (America/Toronto, UTC-4) sur la machine cible.
> EN: raw probe evidence and model-decision trail for the founding brief's Phase 0. / FR-CA : preuves brutes et justification du choix du modèle.

## 1. Sondes brutes (réelles)

```bash
$ nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
NVIDIA GeForce RTX 4070 Ti SUPER, 16376 MiB, 610.88
```

Équivalent Windows de `free -h` (PowerShell `Get-CimInstance Win32_OperatingSystem`) — voir ADR-0001 :

```
Intel(R) Xeon(R) W-2123 CPU @ 3.60GHz -- 31,7 GB total / 15,1 GB free
C: 252 Go libres · E: 373 Go libres
```

Outils détectés :

| Outil | Version | État |
|---|---|---|
| Ollama | 0.34.0 | ✅ installé (serveur principal `127.0.0.1:11480` ; `FA=1`, `KV=q8_0`, ctx 32768) |
| Docker | 29.7.2 (Compose v5.5.0, OSType=linux) | ✅ WSL2 : Ubuntu (stopped), docker-desktop (running) |
| Python / uv | 3.12.10 / 0.12.9 | ✅ |
| gh / git | 2.96.0 (compte `leosand`) / 2.55.0 | ✅ |
| Blender | 5.2 (hôte) | ✅ |
| FreeCAD | **1.1.3** (hôte, `%LOCALAPPDATA%\Programs\FreeCAD 1.1`, GUI ouverte) | ✅ — pont MCP hôte via le workbench `robust-mcp` (`spkane/freecad-addon-robust-mcp-server`), XML-RPC `127.0.0.1:9875` ; image Docker en repli (ADR-0006). *Correction : la première sonde ne couvrait que `Program Files` — installation user-local ratée.* |

## 2. Audit des dépôts de référence (2026-09-18)

Méthode : vérification en ligne réelle (GitHub API + pages, PyPI, Docker Hub, registre Ollama), pas de mémoire.
Tableau complet et verdicts : `README.md` § *Reference repositories audited*.

Constats qui corrigent le brief :

| Ligne du brief | Réalité vérifiée | Impact |
|---|---|---|
| `ros2/ros_gz` | **404** — le dépôt canonique est `gazebosim/ros_gz` | Correction de source |
| `spkane/freecad-robust-mcp` (repo) | **404** — l'image `ghcr.io/spkane/freecad-robust-mcp` existe ; le dépôt canonique est `spkane/freecad-addon-robust-mcp-server` | Le nom du dépôt du brief était erroné, l'image est valide |
| « serveur MCP officiel Blender Lab si disponible » | **Disponible** : `projects.blender.org/lab/blender_mcp`, GPL-3.0-or-later, v1.0.3 (2026-09-11), **exige Blender ≥ 5.1** (hôte : 5.2 ✅) ; CLI serveur côté client non documentée publiquement | Cible Phase 3 ; `mcp-for-blender` (uvx) enregistré en attendant (ADR-0004) |
| Phobos (DFKI) pour l'export URDF | `dfki-ric/phobos` — testé Blender 3.3 LTS ; **cassage ouvert sur Blender 4.2**, aucun fork maintenu ≥ 4 | Export URDF par script `bpy` (ADR-0004) |

## 3. Disponibilité réelle des tags Ollama (ollama.com/library, 2026-09-18)

| Modèle | Tag | Existe | Taille | Note |
|---|---|---|---|---|
| devstral | `22b` | ❌ | — | le brief cite un tag inexistant ; seuls des 24b existent |
| devstral | `24b` (≈ `latest`) | ✅ | 14 Go | gén. 1, ~1 an, Q4_K_M |
| devstral-small-2 | `24b` | ✅ | 15 Go | 384K ctx, tools — **marge KV insuffisante sur 16 Go** |
| devstral-2 | `123b` | ✅ | 75 Go | hors matériel |
| gpt-oss | `20b` | ✅ | **14 Go** | MXFP4, 128K ctx, tools/thinking |
| qwen3-coder | `30b-a3b` | ✅ | 19 Go | **ne tient pas entièrement résident** |
| qwen3-coder-next | `latest` | ✅ | **52 Go** | le brief estimait ~16 Go — erroné, non résident |
| gemma4 | `12b` | ✅ | 7,6 Go | repli (niveau 4 du brief) |
| gemma4 | `e4b` / `26b` | ✅ | 9,6 / 19 Go | 26b hors VRAM |
| qwen3 | `14b` | ✅ | 9,3 Go | repli intermédiaire |

## 4. Grille appliquée → décision

| Priorité (brief) | Candidat réel | Verdict | Motif |
|---|---|---|---|
| 1 | `devstral:22b` | ❌ | n'existe pas au registre |
| 1′ | `devstral-small-2:24b` | ❌ | 15 Go → viole le critère « entièrement résident + marge KV ≥ 1,5 Go » |
| **2** | **`gpt-oss:20b`** | ✅ **retenu** | 14 Go, profil agentique/tool-calling documenté sur cartes 16 Go ; déclenché par l'indisponibilité du niveau 1 |
| 3 | `qwen3-coder-next` | ❌ | 52 Go réels ≠ ~16 Go estimés |
| 4 | `gemma4:12b` | 🔁 repli conservé | si le banc échoue ou si le seuil strict de 1,5 Gio de marge doit primer (`batiai/gemma4-12b:q4` aussi présent) |

**Décision : `gpt-oss:20b`** — enregistrée dans `ARCHITECTURE.md` (ADR-0002).

## 5. Incident de runtime (documenté) — crash gpt-oss sur le serveur principal

Premier essai sur le serveur Ollama principal (`127.0.0.1:11480` ; `FA=1`, `KV=q8_0`, ctx 32768) :
le backend `llama-server` **crashe à l'initialisation** :

```text
exit status 0xc0000409 (stack buffer overrun) … CUDA error: shared object initialization failed
ggml_cuda_compute_forward: MUL_MAT failed  (build llama-server-cuda_v13)
```

- Vérifié : **bug amont connu et non corrigé** (ollama #17380, #18522 — Windows/Ada + MXFP4 + `cuda_v13`).
- `gemma4:e4b-64k` et `qwen2.5-coder:7b` fonctionnent sur la même machine → défaut **spécifique à gpt-oss**.

**Essais isolés** (serveur temporaire sur `:11499`, sans toucher au serveur principal) :

| Essai | Config | Résultat |
|---|---|---|
| 1 | `FA=0` seul | plus de crash CUDA, mais `quantized V cache requires flash_attn` (KV q8_0 incompatible) |
| 2 | `KV=f16` seul (FA=1) | **crash identique** → c'est bien FA+cuda_v13 qui casse sur gpt-oss |
| 3 | `FA=0` + `KV=f16` (cuda_v13) | crash `MUL_MAT` (cuda_v13) |
| 4 | `cuda_v12` seul | crash `MUL_MAT` |
| 5 | **`cuda_v12` + `FA=0` + `KV=f16`** | ✅ **charge** (mais 24 % CPU à ctx 32768 : 18 Go requis > 16 Go) |
| 6 | **+ ctx 8192** (`OLLAMA_CONTEXT_LENGTH=8192`) | ✅ **100 % GPU, stable** — config retenue |

**Contournement validé (ADR-0007)** — serveur Ollama **dédié** sur `127.0.0.1:11499`, lancé par `scripts/start-ollama-gptoss.ps1` ; le serveur principal `:11480` et ses réglages globaux restent intacts.

## 5bis. Banc local (`ollama run --verbose`, cible brief ≥ 40 tok/s)

Commande exacte (serveur dédié) :

```bash
OLLAMA_HOST=http://127.0.0.1:11499 ollama run --verbose gpt-oss:20b "Explique en 5 points comment exporter un URDF depuis Blender avec Phobos."
```

**Résultat (artefact brut : `artifacts/phase-0-bench.txt`) :**

```text
total duration:       10.69 s
prompt eval count:    84 token(s)   → prompt eval rate: 222.96 tok/s
eval count:           1 189 token(s) → eval rate: **115.44 tok/s**
```

- Cible du brief (**≥ 40 tok/s**) : **ATTEINTE** (115,44) — le seuil de rétrogradation (< 25 tok/s) est hors de question.
- Modèle : `gpt-oss:20b`, quantification **MXFP4** (14 Go décimaux / 13 Gio), 128 K ctx natif ; contexte effectif **8 192** (règle de repli du brief).

## 6. Marge VRAM avec modèle chargé (critère brief ≥ 1,5 Go libre)

```text
nvidia-smi (modèle chargé, stable après génération) : 14 601 Mio utilisés / 1 463 Mio libres
ollama ps          : gpt-oss:20b — 13 GB — 100% GPU — CONTEXT 8192 — keep-alive 30 min
```

- **Résidence : 100 % GPU** ✅ (aucun offload CPU, vérifié via `ollama ps`).
- Marge libre : **1 463 Mio (~1,43 Gio)** — à ~5 % sous le seuil strict de 1,5 **Gio** du brief (au-dessus de 1,5 **Go décimaux** = 1 430 Mio). La KV est **préallouée à 8 192** (pas de croissance dynamique pendant l'usage) et la valeur est stable après génération.
- Alternative si le seuil strict doit primer : repli niveau 4 `gemma4:12b` (7,6 Go, marge très large, qualité agentique inférieure) — décision utilisateur.

## 7. Reproductibilité

```bash
# 1. Modèle (13 Go, une fois)
ollama pull gpt-oss:20b

# 2. Serveur dédié (contournement documenté — ADR-0007)
powershell -NoProfile -File scripts/start-ollama-gptoss.ps1

# 3. Banc + marge
OLLAMA_HOST=http://127.0.0.1:11499 ollama run --verbose gpt-oss:20b "Explique en 5 points comment exporter un URDF depuis Blender avec Phobos."
OLLAMA_HOST=http://127.0.0.1:11499 ollama ps
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
```
