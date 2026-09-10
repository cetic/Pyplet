<!-- markdownlint-disable MD029 -->

# Sprint #8 — travail amont (conformité de la chaîne et du code)

Contrat spec-first. Propriétaire : Arthur. Rédigé le 2026-09-10, HEAD
`ed5401b` ; révisé le même jour après critique adverse (agent `fable-high`,
3 constats sur-cible intégrés + 2 au-delà du plafond). Sprint #7 clos
(décision Arthur) ; jalon Sprint #8 inchangé (2026-09-28 → 2026-10-09), ce
travail le précède.

## But

Le code existant de `pyplet/` obéit aux mêmes règles que le code ajouté par
un agent, et une seule chaîne d'outils le vérifie, localement comme en CI.

## Décisions d'Arthur (2026-09-10, réglées)

| Réf | Décision |
| --- | --- |
| A1 | Pas de changement de date du jalon Sprint #8 ; travail amont |
| A2 | Ordre : #60 → #56 → revue du pré-existant → reste de #52 |
| B1 | Règles de complexité ruff = `C90` + `PLR0911/0912/0915` ; **PLR0913 exclu** (les constructeurs de composants publics ont des options nommées, pas de la complexité) ; aucun `noqa`, aucune exemption par fichier |
| B2 | Le critère « `per-file-ignores` vide dans `.flake8` » est remplacé : flake8 disparaît avec #60 |
| B3 | Périmètre de la revue du pré-existant = **tout `pyplet/` sauf `tests/`**, y compris le scaffold `pyplet/apps/` |
| C1 | #52 : constater que les hooks Claude sont déjà actifs à la racine ; reste = `make doctor`, drift check, CI, CLAUDE.md |
| C2 | La CI GitLab rejoue `make lint` ; le workflow GitHub reste en pas |
| D1 | **Les deux fonctions du code client sans aucun test** (`_setup_vfs_bindings`, `bootstrap_client`, couverture mesurée 0 %) **sortent du lot 2** : issue dédiée, tests d'abord, découpage ensuite |

## Définitions (fixées pour rendre les critères reproductibles)

- **Directive d'outillage** : commentaire dont le texte, après `#` et
  espaces, commence par l'un de : `noqa`, `type:`, `pragma`, `ruff:`,
  `fmt:`, `pylint`, `mypy:`, `isort:`, `flake8:`, `coding`, `-*-`, `!`.
  Tout autre commentaire compte.
- **Docstring longue** : empan source `end_lineno − lineno + 1 > 3` du
  nœud chaîne (module, classe, fonction), lignes vides comprises.
- **Comptage** : tokenize + ast sur `pyplet/**/*.py`, `.transpiled` exclu.
- **Registre des suppressions** : fichier `specs/sprint8-amont-registre.md`,
  une ligne par commentaire supprimé : fichier, ligne d'origine, texte,
  catégorie ∈ {raison → test `<nom>` | raison → `docs/<page>` | TODO →
  issue `#N` | séparateur | code mort | paraphrase | repère tutoriel
  conservé}.

## État mesuré (2026-09-10, confirmé par le critique)

- `make lint` vert, `make test` = 305 passed.
- Complexité (`C901, PLR0911/12/13/15`) : 21 findings, **6 fichiers**
  (`client/__init__.py`, `_transpiler.py`, `cli.py`, `oauth.py`,
  `templates.py`, `shared/dom/_dom.py`), 0 dans `tests/` ; sans PLR0913 :
  **13 findings** ; sans PLR0913 ni les deux fonctions D1 : **9 findings**.
- Pré-existant hors `tests/`, selon les définitions ci-dessus : **628
  commentaires** et **54 docstrings longues**, 11 fichiers. Top 3 :
  `_transpiler.py` (180 / 5), `_server.py` (142 / 16), `oauth.py` (75 / 17).
  Parmi les 628 : 56 séparateurs, 84 lignes de code mort commenté
  (`_transpiler.py` l. 208-330, classe `UnionTypeFixer`), 8 repères
  pédagogiques dans `pyplet/apps/tutorial/tutorial_client.py`.
- Couverture de `pyplet/client/__init__.py` : 12 % ; les corps de
  `_setup_vfs_bindings` (l. 139-448) et `bootstrap_client` (l. 453-538) ne
  sont exécutés par aucun test.
- Outils déclarés sans effet ou en doublon : black, isort, flake8,
  setup-cfg-fmt. La CI (`.gitlab-ci.yml` l. 130) exécute `prek run
  --all-files` avec ruff `0.15.11 --fix` ; `make lint` exécute ruff `0.16.6
  --no-fix` sur `pyplet tests`.
- Hooks Claude : `.claude/hooks` et `.claude/settings.json` pointent déjà sur
  `../apps/QualiSpectra/.claude/` ; `.claude/` est gitignoré ; trois refus
  du garde mesurés ce jour.

## Critères d'acceptation

Chaque critère se vérifie sur `gitlab/main` après fusion, par un critique
distinct de l'auteur, avec les définitions ci-dessus.

### Lot 1 — #60, une seule autorité de qualité

1. black, isort, flake8 et setup-cfg-fmt n'apparaissent plus dans aucun
   fichier de **configuration** (`pyproject.toml` sections `[tool.*]`,
   `.pre-commit-config.yaml`, `.flake8`, workflows) ; `.flake8` n'existe
   plus. Une mention dans un texte explicatif (ex. rationale de `src`)
   ne compte pas.
2. Même verdict local / CI, **prouvé sur arbre rouge** : un fichier de
   sonde portant une violation ruff non autofixable (ex. `B006`) fait
   échouer `make lint`, `make precommit` **et** le pipeline GitLab ; retiré,
   les trois passent. Les deux chaînes utilisent la même version de ruff
   et les mêmes options.

### Lot 2 — #56, complexité (hors D1)

3. `[tool.ruff.lint] select` contient `C90`, `PLR0911`, `PLR0912`,
   `PLR0915` et pas `PLR0913` ; `make lint` vert.
4. Aucun `noqa` ni exemption par fichier ajouté ; aucune signature publique
   modifiée (`upload`, `upload_area`, `slider`, `base_template`).
5. Suite de tests verte, nombre de tests ≥ 305 ; chaque fonction découpée
   hors code client est exécutée par au moins un test (couverture de la
   fonction > 0 avant et après).
6. Issue GitLab créée pour D1 (deux fonctions client, tests d'abord), au
   jalon Sprint #8, avec la couverture mesurée (6 des 13 findings sont dans
   ces fonctions : sans les découper, le critère 3 ne peut pas passer sans
   exemption). Elle est **exécutée dans ce run**, dans une fusion à elle,
   dans cet ordre : tests exécutant les deux corps (couverture > 0 mesurée
   sous pytest), puis découpage, puis critère 3 vérifié globalement.

### Lot 3 — revue du pré-existant (B3), livré en 4 fusions

Découpage : `_transpiler.py` ; `_server.py` ; `oauth.py` ; le reste. Chaque
fusion satisfait 7 à 10 sur sa tranche.

7. Sur `pyplet/` hors `tests/` : 0 commentaire hors directive d'outillage
   **sauf** les repères du tutoriel (voir 10) ; 0 docstring longue. Le
   comptage des Définitions rend 0 / 0 hors tutoriel.
8. Registre complet : chaque commentaire supprimé a une ligne et une
   catégorie. Le critique tire **20 lignes au hasard parmi les catégories
   raison/TODO** et retrouve la destination de chacune (le test existe et
   passe, la page `docs/` porte le texte, l'issue est ouverte).
9. Comportement inchangé : suite verte ; `pyplet init tutorial` puis
   `pyplet start` servent le tutoriel ; upload et download y fonctionnent
   dans le navigateur (preuve : capture ou sortie de console consignée dans
   la MR).
10. Le tutoriel garde ses repères : ses 8 commentaires pédagogiques sont
    soit conservés tels quels (catégorie « repère tutoriel conservé »),
    soit migrés vers `docs/` avec un lien depuis le fichier ; aucun n'est
    simplement effacé. Ses docstrings longues migrent vers `docs/`, ne
    sont pas supprimées.

### Lot 4 — reste de #52

11. `make doctor` et `make env` existent (`env` n'existait pas : il est
    créé, il pose les liens `.claude/*` et `core.hooksPath`). Sur un clone
    frais **sans** `apps/QualiSpectra`, `doctor` échoue en nommant chaque
    lien manquant ; après `make env` sur la machine d'Arthur, il passe et
    son drift check couvre hooks git **et** hooks Claude.
12. `.gitlab-ci.yml` rejoue `make lint` ; `.github/workflows/test.yml`
    reste son miroir (même commande).
13. `CLAUDE.md` § *Development constraints* dit couches 0–1 **live sur un
    poste où `make doctor` passe** ; plus aucune mention « deferred ».
14. Les issues #52, #56, #60 portent une note d'état exacte (chiffres
    mesurés, décisions ci-dessus) ; #56 et #60 fermées ; #52 fermée si le
    critère 11 passe ; l'issue D1 ouverte.

## Hors périmètre

- `tests/` : ni revue des commentaires, ni découpage.
- PLR0913 et toute modification de signature publique.
- Découpage de `_setup_vfs_bindings` et `bootstrap_client` (D1, issue
  dédiée).
- #58 (bloqué), #59, #61 à #66 : non touchés, sauf issues créées au titre
  du critère 8.
- Dates et contenu du jalon Sprint #8.

## Protocole d'exécution (décision Arthur 2026-09-10)

- Agents `opus-max`, parallélisés au maximum ; chaque agent écrivant est
  isolé dans son worktree dès son premier appel.
- Une revue adverse `opus-max` par lot, distincte de l'auteur, obligation
  de prouver par exécution ; l'orchestrateur rejoue lui-même toute commande
  citée avant d'agir.
- Ordre imposé par les fichiers partagés : lot 1 (pyproject, prek, CI)
  seul, fusionné avant tout ; puis en parallèle lot 2, lot 3-`_server.py`,
  lot 4 ; puis lot 3-`_transpiler.py`, `oauth.py`, reste (après fusion du
  lot 2, qui touche les mêmes fichiers).
- **Aucune interruption** tant que les 14 critères ne passent pas, sauf
  blocage réel (accès, décision hors spec, trois échecs sur un même
  critère).

## Points nécessitant une décision d'Arthur pendant le run

Aucun prévu. Un texte du tutoriel qui perd son sens en migrant vers `docs/`
sera remonté comme option, pas tranché seul.
