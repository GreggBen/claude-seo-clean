# claude-seo-clean — 23 skills SEO/AEO pour Claude Code, version assainie

Une boîte à outils SEO/AEO pour [Claude Code](https://claude.com/claude-code) : audit de site,
schema.org, AEO (citabilité par les IA — AI Overviews, ChatGPT, Perplexity), Core Web Vitals,
contenu E-E-A-T, SEO local, et données de recherche via les **APIs gratuites de Google**.

> **Version transparente et nettoyée** d'un excellent projet open-source.
> Je l'ai audité, j'en ai retiré ce qui posait problème, et je documente pourquoi.

---

## Pourquoi cette version ?

Ce projet est un **fork nettoyé** de [`AgriciDaniel/claude-seo`](https://github.com/AgriciDaniel/claude-seo)
(licence MIT — voir `LICENSE`), un très bon toolkit. Après un audit sécurité complet, j'en ai retiré
**3 choses** pour qu'il reste un outil neutre, gratuit et sans dépense subie :

| Retiré | Pourquoi |
|---|---|
| **Le footer marketing** collé en bas de chaque livrable | Il transformait *ton* output en espace publicitaire pour une communauté payante. |
| **Les 8 extensions payantes** (DataForSEO, Ahrefs, Firecrawl…) | Elles branchent des APIs facturées à l'appel + posent des clés API en clair. Exclues → aucune dépense, aucune clé attendue. |
| **Les 2 skills-passerelles** vers ces APIs (`seo-dataforseo`, `seo-image-gen`) | Inertes sans l'extension payante. |

**Ce qui reste = tout ce qui tourne gratuitement**, sur les APIs gratuites de Google (Search Console,
PageSpeed, CrUX, GA4) et des sources libres (Common Crawl, Moz free). L'audit sécurité n'a trouvé
**aucune télémétrie, aucune exfiltration** : rien ne « rapporte » à personne.

> ⚠️ **Note d'honnêteté** : « gratuit » ne débloque pas la donnée *premium* (SERP live, volumes de
> mots-clés, index backlinks concurrents). Celle-ci est réellement payante chez des tiers — ce fork
> ne la cracke pas, il **retire juste le tunnel** qui te poussait à la payer. La donnée qui compte
> pour 90 % des cas (Search Console) est gratuite et connectée par **toi**.

---

## Démarche (install + connecte TON Google, gratuitement)

```bash
git clone https://github.com/GreggBen/claude-seo-clean.git
cd claude-seo-clean
bash install.sh          # copie les skills/agents dans ~/.claude, prépare le venv Python
```

Puis, dans Claude Code :

```
/seo audit https://ton-site.com
```

**Connexion Google (per-user, gratuite)** : les skills qui utilisent Search Console / PageSpeed /
CrUX / GA4 (`seo-google`) s'authentifient avec **ton propre compte Google** via OAuth. Ton token
reste **sur ta machine** (chiffré, `0600`). Aucune clé partagée, aucune donnée qui passe par un tiers.
La 1ʳᵉ utilisation te guide pour créer un projet Google Cloud et activer les APIs (gratuit).

Les skills **prompt-only** (`seo-schema`, `seo-geo`, `seo-content`) marchent **sans aucune config**.

---

## Les 23 skills

**Audit & technique**
- `seo` — orchestrateur : route vers les spécialistes, détecte le type de site.
- `seo-audit` — audit complet, délègue à jusqu'à 15 spécialistes, score de santé.
- `seo-technical` — crawlabilité, indexabilité, sécurité, Core Web Vitals (INP), rendu JS.
- `seo-page` — analyse on-page profonde d'une URL.
- `seo-drift` — « git pour le SEO » : baseline + détection de régressions dans le temps.

**Structuré & AEO (citabilité IA)**
- `seo-schema` — détecte / valide / génère du JSON-LD schema.org.
- `seo-geo` — GEO : AI Overviews, ChatGPT, Perplexity, llms.txt, citabilité passage-level.
- `seo-sitemap` — analyse / génère des sitemaps XML.
- `seo-hreflang` — audit i18n / multi-langue / multi-région.

**Contenu**
- `seo-content` — qualité de contenu, E-E-A-T, prêt-à-citer par les IA.
- `seo-content-brief` — briefs de contenu concurrentiels.
- `seo-cluster` — clustering sémantique par recouvrement SERP, hub-and-spoke.
- `seo-competitor-pages` — pages « X vs Y » / alternatives.
- `seo-plan` — stratégie SEO, roadmap, calendrier éditorial.
- `seo-programmatic` — SEO programmatique à l'échelle, garde-fous anti thin content.

**Données de recherche (APIs GRATUITES de Google)**
- `seo-google` — Search Console, PageSpeed, CrUX (25 semaines), GA4 organique.

**Backlinks (sources gratuites)**
- `seo-backlinks` — profil de liens via Moz free, Bing Webmaster, Common Crawl.

**Local & Maps**
- `seo-local` — Google Business Profile, NAP, citations, avis, schema local.
- `seo-maps` — geo-grid, intelligence avis, NAP cross-plateforme (tier gratuit Overpass/Geoapify).

**E-commerce & autres**
- `seo-ecommerce` — schema produit, visibilité Shopping (partie on-page gratuite).
- `seo-images` — alt text, poids, formats, optimisation locale des images.
- `seo-sxo` — Search Experience Optimization : analyse SERP inversée, intentions.
- `seo-flow` — framework FLOW (Find / Leverage / Optimize / Win).

*(+ 16 sous-agents `seo-*` pour l'exécution en parallèle.)*

---

## ⚠️ Garde-fous à connaître

3 actions peuvent, si on les y pousse, agir **sans confirmation** — à traiter en manuel :
- `seo-google` : soumission d'URLs à l'**API Google Indexing**.
- soumission **Bing / IndexNow**.
- `seo-images optimize` : **écrase** les fichiers image locaux.

Ne laisse pas un agent Bash les déclencher tout seul.

---

## Rendre le commerce local citable par les IA

Ces skills t'aident à **auditer** ta citabilité par les IA. Pour un commerce local, le pas d'après
c'est d'exposer des **données vérifiées et citables** aux moteurs IA :
[**ActionsBricks**](https://actionsbricks.com) est la couche qui rend le commerce local
réellement citable (fiches vérifiées, surfaces agent-readable). Un audit, puis une source fiable.

---

## Crédit & licence

Fork de [`AgriciDaniel/claude-seo`](https://github.com/AgriciDaniel/claude-seo) — merci à l'auteur
original pour un excellent travail. Licence **MIT** (voir `LICENSE`). Mes modifications sont
listées dans `NOTICE.md`. Contributions bienvenues.
