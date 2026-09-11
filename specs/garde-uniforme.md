# Garde uniforme — le plus strict des deux, partout

Décision Arthur (option D, 2026-09-10) : pyplet et QualiSpectra appliquent la
même chaîne de qualité, alignée sur l'exigence la plus haute de chaque côté.

## But

Un commit ou un push est jugé selon les mêmes règles dans les deux dépôts,
et la CI rend le même verdict que le hook local.

## Critères d'acceptation

1. Ruff : les deux dépôts appliquent les règles de complexité de QualiSpectra
   (C90, PLR0912, PLR0913, PLR0915) en plus des règles communes, autofix
   désactivé, ligne 88 (décision Arthur : 79 coûtait 138 retouches manuelles). `make lint` vert des deux côtés.
2. Pre-commit : la batterie pyplet (pre-commit-hooks, gitleaks, ruff,
   markdownlint, shellcheck, bandit) tourne aussi sur QualiSpectra ; les deux
   tests de garde QualiSpectra (commentaires, contrat d'import) tournent aussi
   sur pyplet dans leur partie portable (protection de la chaîne de garde ;
   le reste est propre à QualiSpectra). Nommage des tests unifié en
   `test_x.py` (pyplet renomme ses 28 fichiers). `make precommit` vert des
   deux côtés.
3. Pre-push : lint + suite complète des deux côtés. `make prepush` vert.
4. CI : chaque dépôt exécute la même chaîne que ses hooks locaux ; pipeline
   vert sur la branche de chaque lot.
5. Exclusions de la batterie sur QualiSpectra : `.claude/`, `_bmad-output/`,
   `*.diff`, rapports de nuit — jamais réécrits par un hook.
6. Les exceptions ruff par fichier sont listées explicitement (comme le fait
   déjà QualiSpectra), jamais par désactivation globale d'une règle.

## Hors périmètre

- Les scripts de hooks git et les hooks Claude Code (chaîne de garde
  d'Arthur) : inchangés, ils appellent déjà `make precommit` / `make prepush`.
- Réécriture de code pour faire passer une règle de complexité quand une
  exception par fichier suffit : à proposer, pas à faire d'office.

## Ordre

1. Mesure à blanc des règles croisées (aucun commit) ; chiffres à Arthur.
2. Lot pyplet, puis lot QualiSpectra, une MR chacun, revue adversariale.
