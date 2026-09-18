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
| Ollama | 0.34.0 | ✅ installé (modèles existants : `qwen2.5vl`, `gemma4:e4b-64k`, `batiai/gemma4-12b:q4`, `qwen2.5-coder:7b`, `nomic-embed-text`…) |
| Docker | 29.7.2 (Compose v5.5.0, OSType=linux) | ✅ WSL2 : Ubuntu (stopped), docker-desktop (running) |
| Python / uv | 3.12.10 / 0.12.9 | ✅ |
| gh / git | 2.96.0 (compte `leosand`) / 2.55.0 | ✅ |
| Blender | 5.2 (hôte) | ✅ |
| FreeCAD | absent de l'hôte | ⚠️ — le serveur MCP FreeCAD passera par l'image Docker (voir ADR-0006) |

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
| 4 | `gemma4:12b` | 🔁 repli conservé | si le banc passe sous 25 tok/s (et `batiai/gemma4-12b:q4` déjà présent) |

**Décision : `gpt-oss:20b`** — enregistrée dans `ARCHITECTURE.md` (ADR-0002).

## 5. Banc local (`ollama run --verbose`, cible brief ≥ 40 tok/s)

Commande exacte :

```bash
ollama run gpt-oss:20b --verbose "Explique en 5 points comment exporter un URDF depuis Blender avec Phobos."
```

<!-- BENCH -->

## 6. Marge VRAM avec modèle chargé (critère brief ≥ 1,5 Go libre)

<!-- VRAM -->

## 7. Reproductibilité

```bash
ollama pull gpt-oss:20b                    # ~13 Go (13 000 000 000 octets ≈ 14 GB décimaux)
ollama run gpt-oss:20b --verbose "..."     # banc ; si < 25 tok/s → repli gemma4:12b
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader   # marge ; si < 1,5 Go → num_ctx 8192 ou repli
```
