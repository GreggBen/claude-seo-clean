# claude-seo-clean — 24 skills SEO/AEO pour Claude Code, version assainie

Une boîte à outils SEO/AEO pour [Claude Code](https://claude.com/claude-code) : audit de site,
schema.org, AEO (citabilité par les IA — AI Overviews, ChatGPT, Perplexity), Core Web Vitals,
contenu E-E-A-T, SEO local, et données de recherche via les **APIs Google accessibles avec ton compte**.

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

**Ce qui reste = les intégrations sans fournisseur payant imposé**, sur les APIs Google (Search Console,
PageSpeed, CrUX, GA4) et des sources libres (Common Crawl, Moz free), selon les quotas et conditions
propres à chaque service. L'audit sécurité n'a trouvé
**aucune télémétrie, aucune exfiltration** : rien ne « rapporte » à personne.

> ⚠️ **Note d'honnêteté** : « gratuit » ne débloque pas la donnée *premium* (SERP live, volumes de
> mots-clés, index backlinks concurrents). Celle-ci est réellement payante chez des tiers — ce fork
> ne la cracke pas, il **retire juste le tunnel** qui te poussait à la payer. La donnée qui compte
> via Search Console dépend des données de **ton** site et de ton accès.

---

## Démarche (installation et connexion à ton compte Google)

```bash
git clone https://github.com/GreggBen/claude-seo-clean.git
cd claude-seo-clean
bash install.sh          # copie les skills/agents dans ~/.claude, prépare le venv Python
```

Les commandes de scripts dans les skills et agents passent par
`~/.claude/skills/seo/run-script <nom-du-script.py> [arguments...]` : ce lanceur
retrouve les scripts et le Python du venv installé depuis n'importe quel
répertoire courant. Vérification après installation :

```bash
~/.claude/skills/seo/run-script portability_check.py --json
```

Depuis le clone avant installation, utiliser `./skills/seo/run-script`.
L'installation des dépendances reste dans `~/.claude/skills/seo/.venv` ; aucun
paquet Python n'est installé globalement.

Puis, dans Claude Code :

```
/seo audit https://ton-site.com
```

**Connexion Google (par utilisateur)** : les skills qui utilisent Search Console / PageSpeed /
CrUX / GA4 (`seo-google`) s'authentifient avec **ton propre compte Google** via OAuth. Ton token
reste **sur ta machine** dans un fichier JSON non chiffré ; le script applique les permissions
`0600` lorsque le système de fichiers les prend en charge (`skills/seo/scripts/google_auth.py`,
`_save_oauth_token`). Ces permissions limitent l'accès local, sans chiffrer le contenu.
Aucune clé partagée ; les requêtes utilisent directement les API Google configurées.
La 1ʳᵉ utilisation te guide pour créer un projet Google Cloud et activer les APIs concernées ;
vérifie leurs quotas et conditions avant usage.

Les skills **prompt-only** (`seo-schema`, `seo-geo`, `seo-content`) marchent **sans aucune config**.

---

## Les 24 skills

**Audit & technique**
- `seo` — orchestrateur : route vers les spécialistes, détecte le type de site.
- `seo-fix` — corrèle 3 vues d'une page (HTML brut, DOM rendu, code source) et corrige à la source ; la seule skill qui lit la codebase et y écrit, avec re-mesure obligatoire.
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

**Données de recherche (APIs Google)**
- `seo-google` — Search Console, PageSpeed, CrUX (25 semaines), GA4 organique.

**Backlinks (sources gratuites)**
- `seo-backlinks` — profil de liens via Moz free, Bing Webmaster, Common Crawl.

**Local & Maps**
- `seo-local` — Google Business Profile, NAP, citations, avis, schema local.
- `seo-maps` — présence cartographique publique, NAP cross-plateforme, commerces voisins (Overpass/Geoapify).

**E-commerce & autres**
- `seo-ecommerce` — audit des pages produit et du balisage Product/Offer.
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

## Rendre les informations du commerce local consultables

Ces skills aident à auditer la découvrabilité et les signaux de citation observables.
[**ActionsBricks**](https://actionsbricks.com) expose une représentation vérifiable
et consultable des commerces locaux (fiches vérifiées, surfaces lisibles par les agents).
La publication ne garantit ni la consultation, ni l'indexation, ni la citation par une IA.

---

## Crédit & licence

Fork de [`AgriciDaniel/claude-seo`](https://github.com/AgriciDaniel/claude-seo) — merci à l'auteur
original pour un excellent travail. Licence **MIT** (voir `LICENSE`). Mes modifications sont
listées dans `NOTICE.md`. Contributions bienvenues.
