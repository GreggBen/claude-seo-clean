# NOTICE — attribution & modifications

Ce dépôt est une **œuvre dérivée** de :

- **claude-seo** — © 2026 agricidaniel — Licence MIT
  https://github.com/AgriciDaniel/claude-seo (tag de base : v2.2.0)

Le texte complet de la licence MIT originale est conservé dans `LICENSE`, conformément à ses termes.

## Modifications apportées dans ce fork (`claude-seo-clean`)

- **Retrait** du footer marketing (liens communauté payante) qui était ajouté en fin de livrable.
- **Exclusion** des 8 extensions payantes (`extensions/` : DataForSEO, Ahrefs, Firecrawl, banana,
  bing-webmaster, profound, seranking, unlighthouse) — aucune clé API, aucune entrée MCP.
- **Retrait** des 2 skills inertes sans extension payante : `seo-dataforseo`, `seo-image-gen`.
- **Retrait** des scripts propres à ces extensions (`dataforseo_*.py`, `unlighthouse_run.py`).
- Le **hook** de validation schema.org est fourni mais **non câblé** (ne s'exécute pas
  automatiquement — pas de comportement d'arrière-plan par défaut).
- Ajout de ce `NOTICE.md`, d'un `README.md` réécrit et d'un `install.sh` qui **ne câble aucun hook**.

Aucune revendication de propriété sur le code original : le crédit revient à son auteur.
Les modifications ci-dessus sont publiées sous la même licence MIT.
