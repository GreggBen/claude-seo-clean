#!/usr/bin/env bash
# claude-seo-clean — installateur simple et transparent.
# Copie les skills + agents dans ~/.claude, prépare un venv Python isolé.
# NE câble AUCUN hook (aucun comportement d'arrière-plan). N'installe AUCUNE extension payante.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DST="${HOME}/.claude/skills"
AGENTS_DST="${HOME}/.claude/agents"

echo "== claude-seo-clean : installation =="

command -v python3 >/dev/null 2>&1 || { echo "✗ Python 3 requis."; exit 1; }
command -v git     >/dev/null 2>&1 || { echo "✗ Git requis."; exit 1; }

mkdir -p "${SKILLS_DST}" "${AGENTS_DST}"

echo "→ Skills..."
cp -R "${SRC_DIR}/skills/"seo* "${SKILLS_DST}/"
chmod 755 "${SKILLS_DST}/seo/run-script"

echo "→ Agents..."
cp "${SRC_DIR}/agents/"seo-*.md "${AGENTS_DST}/"

echo "→ Venv Python (skills à scripts : seo-audit, seo-technical, seo-drift, seo-google)..."
VENV="${SKILLS_DST}/seo/.venv"
if ! python3 -m venv "${VENV}"; then
  echo "✗ venv indisponible. Installe python3-venv puis relance l'installation." >&2
  exit 1
fi
if ! "${VENV}/bin/pip" install --quiet -r "${SRC_DIR}/requirements.txt"; then
  echo "✗ Installation des dépendances incomplète. Relance : ${VENV}/bin/pip install -r ${SRC_DIR}/requirements.txt" >&2
  exit 1
fi
echo "  ✓ dépendances installées (${VENV})"

echo ""
echo "✓ Installé. 24 skills + 16 agents dans ~/.claude/ (aucun hook câblé, aucune extension payante)."
echo "  Redémarre Claude Code, puis :  /seo audit https://ton-site.com"
echo "  Scripts depuis tout répertoire :  ${SKILLS_DST}/seo/run-script portability_check.py --json"
echo "  Désinstaller :  rm -rf ~/.claude/skills/seo* ~/.claude/agents/seo-*.md"
