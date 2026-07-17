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

echo "→ Agents..."
cp "${SRC_DIR}/agents/"seo-*.md "${AGENTS_DST}/"

echo "→ Venv Python (skills à scripts : seo-audit, seo-technical, seo-drift, seo-google)..."
VENV="${SKILLS_DST}/seo/.venv"
if python3 -m venv "${VENV}" 2>/dev/null; then
  "${VENV}/bin/pip" install --quiet -r "${SRC_DIR}/requirements.txt" \
    && echo "  ✓ dépendances installées (${VENV})" \
    || echo "  ⚠ pip a échoué — relance : ${VENV}/bin/pip install -r ${SRC_DIR}/requirements.txt"
else
  echo "  ⚠ venv indisponible — installe manuellement : pip install --user -r ${SRC_DIR}/requirements.txt"
fi

echo ""
echo "✓ Installé. 23 skills + 16 agents dans ~/.claude/ (aucun hook câblé, aucune extension payante)."
echo "  Redémarre Claude Code, puis :  /seo audit https://ton-site.com"
echo "  Désinstaller :  rm -rf ~/.claude/skills/seo* ~/.claude/agents/seo-*.md"
