# Prompt Kimi Code — Stack de prototypage humanoïde agentique (Blender + FreeCAD + ROS 2 + MCP)

> Brief fondateur du projet DroneCAD — archivé tel quel (2026-09-18). Réutilisable via `--context-file` ou copie directe dans Kimi Code.

Usage : copier ce fichier tel quel dans Kimi Code (ou l'injecter via --context-file).
Cible matérielle : GPU NVIDIA RTX 4070 16 Go VRAM (Ti Super), 32 Go RAM système minimum, docker disponible.
Sévérité : chaque étape bloquante doit être exécutée, vérifiée et rapportée — pas de « TODO » silencieux.

0. Rôle
Tu es un ingénieur senior full-stack + robotique (ROS 2, simulation, IA agentique), bilingue EN/FR-CA.
Commentaires de code bilingues // EN : English purpose / FR : but en français.
TypeScript strict applicable à toute couche d'orchestration éventuelle ; Python 3.12 pour les scripts agentiques.
Tu respectes : sécurité d'abord (conteneurs non-root, localhost par défaut, aucun secret codé en dur), GitHub Actions pour CI, et tu cites les dépôts GitHub de référence (owner/repo) pour chaque brique que tu installes, avec verdict adopt/fork/inspiration.

1. Phase 0 — Détection matérielle & sélection du modèle local (OBLIGATOIRE AVANT TOUT)
Avant toute installation :

Exécute nvidia-smi --query-gpu=name,memory.total --format=csv et free -h, puis rapporte les valeurs réelles.

Vérifie que Ollama est installé (ollama --version) ; sinon installe-le (script officiel Linux ou équivalent plateforme détectée ; sous Windows/PowerShell, utilise l'installeur officiel).

Sélection du modèle — critères explicites
Choisis le meilleur modèle agentique de codage qui tient entièrement résident en VRAM avec marge KV-cache sur 16 Go. Applique cette grille de décision (valide au 2026-09) :

Priorité    Modèle    Tag Ollama    VRAM estimée    Justification
1 (défaut agentique)    Devstral 2    devstral:22b    ~14,1 Go (Q4)    Meilleur coder agentique ≤24 Go : éditions multi-fichiers, tool calling, boucles de debug ; ~52 % SWE-bench Verified
2 (si Devstral indisponible/lent)    gpt-oss 20B    gpt-oss:20b    ~14 Go    Le seul à passer 8/8 tâches agentiques testées sur carte 16 Go, 178-190 tok/s, excellent tool calling
3 (efficacité MoE)    Qwen3-Coder-Next    qwen3-coder-next    ~16 Go (3B actifs / 80B MoE)    Qualité ≈ 30B+ avec latence de petit modèle ; serré, réduire le contexte si besoin
4 (repli sécuritaire)    Gemma 4 12B    gemma4:12b    ~7,6 Go    Large marge de contexte, quasi-parité 26B
Télécharge le modèle retenu : ollama pull <tag> puis benchmark rapide et rapport :

bash
ollama run <tag> --verbose "Explique en 5 points comment exporter un URDF depuis Blender avec Phobos."
Mesure tok/s ; cible ≥ 40 tok/s. Si < 25 tok/s, rétrograde au repli immédiat inférieur et justifie dans le rapport.

Vérifie la marge : nvidia-smi doit montrer ≥ 1,5 Go de VRAM libre avec le modèle chargé (marge KV-cache + contexte long). Sinon, baisse num_ctx à 8192 dans le Modelfile ou rétrograde de niveau.

Consigne dans REPORT.md : modèle final, quantification, tok/s mesurés, VRAM résiduelle, et pourquoi les alternatives ont été rejetées.

2. Phase 1 — Isolation & orchestration (Docker Compose)
Crée docker-compose.yml à la racine du workspace ~/humanoid-agentic-stack/. Exigences :

Tous les services en non-root (user:, UID/GUID mappés), read_only: quand possible, pas de privileged: true sauf justification documentée.

Réseau interne agentnet ; aucun port MCP exposé à l'extérieur de 127.0.0.1.

Services :

ros2-jazzy : image ros:jazzy + Gazebo Harmonic + ros_gz + ros2_control + MoveIt 2 (Dockerfile multi-étapes, couche de build séparée).

ros2-mcp : serveur MCP wise-vision/ros2_mcp (audit d'abord : licence, activité récente, tests) ; alternative kakimochi/ros2-mcp-server pour le contrôle /cmd_vel uniquement si le premier échoue.

freecad-mcp : ghcr.io/spkane/freecad-robust-mcp (image Docker officielle du dépôt spkane) ; workbench bridge FreeCAD installé côté hôte si GUI disponible.

mcp-rosbags : binabik-ai/mcp-rosbags pour l'analyse agentique des sacs ROS en langage naturel.

Blender reste sur l'hôte (GUI + accès GPU pour les rendus) : installe blender-mcp (uvx blender-mcp servant de pont ; addon addon.py activé dans Blender 5.1+) et le serveur MCP officiel Blender Lab si disponible. Ajoute l'addon Phobos (DFKI, rock-simulation/phobos) pour l'export URDF/SDF/SMURF.

3. Phase 2 — Chaîne de conception humanoïde
Crée les packages ROS 2 suivants (colcon workspace ~/humanoid-agentic-stack/ws/src/) :

humanoid_description :

URDF/Xacro minimal mais complet d'un humanoïde bipède 24-32 DoF : torso, tête (caméra RGB-D + IMU dans TF), bras 6 DoF ×2, jambes 6 DoF ×2, capteurs (contact FT aux pieds via Gazebo).

Masses, inerties valides, limites articulaires, transmissions ros2_control_compliant.

Export de validation : script bpy + Phobos qui régénère l'URDF depuis un .blend maître, versionné dans Git (fichier binaire + script d'export textuel reproductible).

humanoid_gazebo : mondes Gazebo Harmonic (sol plat + obstacles), fichiers launch, pont ros_gz_bridge (topics : /clock, /joint_states, /camera, /imu).

humanoid_control : contrôleurs ros2_control (position + effort), fichier YAML, script de squat test (consignes articulaires sinusoïdales → vérification de stabilité).

Tests : pytest de validation URDF (check_urdf, inerties > 0, pas de liens orphelins) + test d'intégration headless Gazebo (le robot reste debout 10 s simulés).

4. Phase 3 — Boucle agentique MCP
Génère .mcp.json (compatibles Claude Code / Cursor / Kimi Code) enregistrant : blender, freecad, ros2, rosbags, memory (shodh-memory pour mémoire cognitive locale). Ports localhost uniquement.

Écris agent_loop.py (Python 3.12, type hints stricts) démontrant la boucle :

Concevoir : instruction LLM → FreeCAD-MCP crée une pièce paramétrique (bracket moteur) → export STEP.

Modéliser : Blender-MCP + Phobos assemble l'enveloppe et ré-exporte URDF.

Simuler : ros2_mcp publie des consignes sur le contrôleur ; Gazebo avance la simulation.

Analyser : mcp-rosbags ingère le sac enregistré et produit un diagnostic (chute ? dépassement de couple articulaire ?).

Itérer : si un critère échoue, l'agent propose une modification paramétrique et recommence (max 3 itérations, garde-fou explicite).

Garde-fous agentiques obligatoires : allowlist d'outils MCP par phase, timeout par appel, journal JSON structuré avec correlation ID par itération.

5. Phase 4 — CI/CD & qualité
ci.yml GitHub Actions : lint (ruff, clang-tidy si C++), build colcon dans conteneur ros:jazzy, tests URDF + intégration Gazebo headless (xvfb), scan de dépendances (Trivy) sur les images.

Image finale multi-étapes, tag sémantique v0.1.0, scan sans vulnérabilité haute/critique avant merge.

README.md bilingue EN/FR-CA : architecture (diagramme Mermaid), installation one-liner, arborescence, table des dépôts de référence audités.

ARCHITECTURE.md : ADR (Architecture Decision Records) expliquant le choix du modèle Ollama, de Gazebo vs MuJoCo (recommander d'ajouter mujoco en phase future pour RL locomotion), et les limites actuelles.

6. Phase 5 — Livrables & auto-vérification
Before final answer, exécute cette checklist et colle le résultat dans REPORT.md :

Modèle local chargé, résident GPU, tok/s rapportés, alternative documentée

docker compose config valide ; tous conteneurs non-root démarrés

mcp.json chargé : chaque serveur MCP répond à un appel tools/list réel

Robot humanoïde se tient debout ≥ 10 s dans Gazebo (log joint_states joint)

Boucle agentique complète exécutée 1 fois de bout en bout (artefacts : STEP, BLEND, URDF, ROS bag, diagnostic)

CI verte sur la branche feature/initial-stack

Aucun secret, aucun port exposé publiquement, docker scout/trivy propre

Table des dépôts GitHub audités avec verdict adopt/fork/inspiration

Si une case échoue : corrige, réexécute, puis seulement présente le résultat. Ne jamais livrer un stack « à moitié fonctionnel » sans le dire explicitement.

7. Contraintes transverses
Dates au ISO YYYY-MM-DD ; espaces insécables en FR au besoin ; « courriel », « téléversement ».

Aucune dépendance obsolète (< 12 mois de maintenance requis, sauf justification ADR).

Performance cible : démarrage de la pile complète < 90 s sur la machine cible ; simulation 1/1 temps réel Gazebo sur le RTX 4070 avec IMU/caméra activés.

Sécurité : TLS inutile en localhost mais CSP/principes de moindre privilège ; pas d'eval, pas d'innerHTML non assaini dans toute UI éventuelle.
