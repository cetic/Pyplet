---
title: Server
---

# Server

Pyplet’s server runtime is built on top of Tornado and lives in the `pyplet.server` package:

- `pyplet.server.web` wires the HTTP routes, static assets, WebSocket endpoints and application shell.
- `pyplet.server.config` exposes configuration values such as address, port, apps root and the Pyodide URL.

The `pyplet start` [CLI](../cli.md) command configures `pyplet.server.config` (via command-line flags and `PYPLET_*` environment variables) and then starts the Tornado application defined in `pyplet.server.web`.

At a high level:

- The [home page](../index.md) lists micro apps discovered under the configured `apps` root.
- Each app is served via a dedicated route that loads Pyodide, fetches the app bundle, and calls `pyplet.client.bootstrap`.
- WebSocket endpoints expose a minimal async API compatible with `pyplet.WebSocket`, allowing apps to implement `websocket_server_loop` coroutines for real-time communication.

Refer to the [CLI](../cli.md) and [Micro Apps](../micro-apps.md) pages for details on configuration and app structure.

## Notes d'implémentation du serveur

Cette section rassemble les raisons de conception et les contraintes du
module `pyplet.server._server` : elles vivaient dans des commentaires et
des docstrings longues du code, que la règle éditoriale du projet réserve
aux tests et à cette documentation. Chaque titre nomme le symbole
concerné ; le registre `specs/sprint8-amont-registre-server.md` fait le
lien ligne à ligne.

### `_APPS_VFS_ROOT` — racine du système de fichiers virtuel client

Nom de répertoire virtuel fixe (`apps`) pour les fichiers d'application à
l'intérieur du système de fichiers virtuel du navigateur
(Pyodide / MicroPython) ; voir `ServerApplication.package` et
`ServerApplication.serve`. Il est tenu séparé de `config.apps` (le
répertoire `apps` *du serveur*, sur disque, qui peut être relatif,
imbriqué ou absolu) afin que la disposition du VFS et le chemin d'import
côté client restent portables quelle que soit la configuration de
`config.apps`.

### `_AuthMixin` — portail d'authentification

Mixin de handler Tornado qui applique l'authentification au niveau de la
plate-forme. Quand l'authentification est désactivée (aucun fournisseur
OAuth configuré), chaque requête passe sans modification. Quand elle est
activée :

- requête non authentifiée vers une page HTML → redirection vers `/login` ;
- requête non authentifiée vers une autre ressource (zip, ws) → 401 ;
- requête authentifiée mais non autorisée → 403.

`_is_ws` : les sous-classes le passent à `True` pour les handlers
WebSocket, où une redirection n'a pas de sens — un client WebSocket ne
suit pas une 302, il doit recevoir un refus explicite.

`get_current_user` renvoie une sentinelle non vide
(`{"email": "", "name": "anonymous", "provider": None}`) quand
l'authentification est désactivée : le décorateur `@authenticated` de
Tornado ne teste que la véracité de `current_user`, et une valeur fausse
déclencherait une redirection vers `/login` alors qu'aucun portail n'est
actif.

### `_AuthMixin._require_auth`

Applique l'authentification puis l'ACL. Renvoie le dictionnaire
utilisateur en cas de succès, ou `None` si la requête a déjà été
terminée (redirection ou erreur déjà écrite) : l'appelant doit alors
retourner immédiatement sans rien écrire de plus.

### `StaticFileHandler.set_extra_headers`

Positionne l'en-tête `Cache-Control` à `no-cache` pour la ressource
demandée (argument `path`, le chemin de la ressource servie).

### `AppStaticFileHandler`

Sert les ressources statiques d'une application, confinées à
`<apps>/<projet>/static`.

La route capture le *projet* et la *queue* du chemin en deux groupes
distincts (`/apps/<projet>/static/<queue>`) et le handler s'enracine, à
chaque requête, dans le seul répertoire `static/` de cette application.
`validate_absolute_path` de Tornado ne garantit qu'une chose : une
requête ne peut pas sortir de `self.root`. Enraciner le handler sur tout
l'arbre `apps/` (ancien comportement) laissait un `..` dans la queue
sortir de `static/` pour atteindre le code serveur d'une application
voisine (`*_server.py`) ou le fichier d'ACL (`auth_rules.json`) tout en
restant sous `apps/` — une traversée de chemin non authentifiée.
L'enracinement par application la referme : un `..` (brut ou
percent-encodé, Tornado décodant l'URL avant l'appariement) ne peut plus
résoudre vers quoi que ce soit hors du `static/` de l'application
demandée (les tentatives reçoivent 403/404). Une application sans
répertoire `static/` répond simplement 404 au lieu de faire tomber le
serveur.

`initialize` doit fournir un `path` à `StaticFileHandler.initialize` ;
la vraie racine, propre à la requête, est (re)calculée dans `get()`
une fois le `project` connu.

`head()` : Tornado distribue chaque méthode sous la forme
`method(*path_args)`, donc `head` doit accepter les deux groupes de
capture (`project`, `tail`) et déléguer au chemin `get` sans corps, à
l'image de `StaticFileHandler.head -> get(path, include_body=False)`.

### `AppStaticFileHandler.validate_absolute_path`

Le test de confinement de Tornado est purement **lexical** : il compare
des préfixes `os.path.abspath` et ne résout jamais les liens
symboliques. Un lien symbolique planté dans le `static/` d'une
application est donc servi quoi qu'il désigne, y compris des fichiers
entièrement hors de l'arbre `apps/` — une lecture de fichier arbitraire
non authentifiée, strictement pire que la traversée que la racine par
requête referme. Le test de confinement est donc rejoué sur les chemins
**résolus** ; les liens symboliques qui restent dans le `static/` de
l'application continuent de fonctionner (ils résolvent sous la racine).

### `BaseHandler` — injection du favicon

Handler de base qui fournit une méthode d'injection d'un favicon SVG
Base64 en ligne dans des chaînes HTML brutes.

`write_html` normalise d'abord le contenu en `str` simple. Le passage
par les octets est nécessaire : un nœud htpy ou un `markupsafe.Markup`
se rend via `str()` en instance de `Markup`, et concaténer une `str`
simple à une `Markup` *échappe* cette `str` (la balise `<link>` brute
sortirait en `&lt;link ...&gt;`). Encoder puis décoder retire le type
`Markup` et laisse une véritable `str`.

L'injection a lieu juste après `<head>`, sauf si un favicon est déjà
présent n'importe où dans le document : `_HEAD_OPEN_RE` apparie la
balise ouvrante `<head ...>`, `_LINK_TAG_RE` toute balise `<link ...>`
et `_REL_ATTR_RE` un attribut `rel`, avec ou sans guillemets.

### `PackageHandler.get`

Sert la ressource de paquet pour le projet et l'application demandés
(arguments `project_name` et `app_name`).

### `LoginHandler`

`GET /login` — affiche la page de connexion (boutons des fournisseurs),
ou redirige vers `/` si l'utilisateur est déjà authentifié.

### `HealthzHandler`

`GET /healthz` — sonde de vivacité du processus, non authentifiée.

Délibérément un handler ordinaire (et **non** `_AuthMixin`) : une sonde
de vivacité doit répondre à un répartiteur de charge, à systemd ou à
Kubernetes sans session, même quand l'authentification est activée.
Elle ne renseigne que « le processus est debout » — aucune vérification
de base de données, de fournisseur ni de boucle d'événements (la
disponibilité applicative profonde relève de la route `/readyz` de
l'application). Elle vit dans le `_app_spec` statique du cœur, donc elle
répond pour toute application pyplet, même quand un module applicatif a
échoué à l'import (`astart` avale les erreurs d'import des applications).

### `MagicLinkVerifyHandler`

`GET /auth/verify?token=<token>` — valide le jeton et connecte
l'utilisateur.

### `ServerWebSocket.check_origin`

Autorise les montées en WebSocket de même origine **ou** l'origine
déployée `PYPLET_URL` (Story 18.18, SECURI-4).

Le `check_origin` par défaut de Tornado n'accepte qu'une requête dont
l'hôte d'`Origin` égale l'en-tête `Host` — ce que le point d'entrée peut
casser en réécrivant `Host`. Une origine dont l'hôte correspond à
l'origine déployée configurée (`config.url` / `PYPLET_URL`) est donc
également acceptée, la comparaison portant sur l'hôte seul afin que le
schéma et le port du point d'entrée n'importent pas. Quand `PYPLET_URL`
n'est pas défini (développement local), le résultat de même origine de
Tornado est repris tel quel, donc `localhost` se connecte toujours.

Réserve (documentée) : Tornado n'invoque `check_origin` que lorsqu'un
en-tête `Origin` est présent ; une montée sans `Origin` (client non
navigateur) n'est donc pas bloquée ici — le véritable verrou contre
l'accès anonyme reste `_AuthMixin._require_auth` dans `open`.

Argument : `origin`, la valeur de l'en-tête `Origin` de la requête.
Retour : `True` pour accepter la montée cross-origine, `False` pour la
rejeter (Tornado répond alors 403 à la poignée de main).

### `ServerWebSocket.get_compression_options`

Active la compression `permessage-deflate` du WebSocket.

Renvoyer un dictionnaire (éventuellement vide) fait entrer la connexion
dans l'extension deflate par message de Tornado : le client propose
l'extension et ce handler l'accepte pendant la poignée de main. Le
`compression_level` 6 est le compromis vitesse/taux par défaut de zlib —
adapté aux trames JSON/texte bavardes de l'application, sans coût
processeur excessif par message.

Retour : un dictionnaire d'options de compression activant
`permessage-deflate`.

### `_app_spec` — réglages Tornado

`cookie_secret` signe les cookies de session. Le repli sur une valeur
aléatoire par processus permet au serveur de fonctionner sans
`PYPLET_COOKIE_SECRET` (au prix des sessions perdues à chaque
redémarrage).

`websocket_max_message_size` fixe la taille maximale de trame
WebSocket. Tornado plafonne par défaut à ~10 Mo, ce qu'un document
téléversé encodé en base64 dépasse — tuant la socket avant que le code
applicatif ne s'exécute. Le défaut de 40 Mo porte un téléversement de
25 Mo (~33 Mo de trame) avec de la marge ; `PYPLET_WS_MAX_MESSAGE_MB`
doit être relevé de concert avec le plafond par document d'une
application.

### `_ensure_namespace_package`

Obtient ou crée un paquet d'espace de noms enregistré dans
`sys.modules`. `search_path`, quand il est fourni, devient le `__path__`
du paquet, ce qui laisse la machinerie d'import de Python localiser à la
demande les vrais sous-modules sous ce répertoire — c'est ce qui fait
fonctionner les imports intra-projet ordinaires (par exemple
`from . import other_server`) pour les modules chargés par
`_load_server_module`.

Ce chemin doit être **absolu** : la machinerie d'import de Python met en
cache un chercheur par répertoire dans `sys.path_importer_cache`, indexé
par la chaîne littérale du chemin ; une chaîne relative réutilisée sous
un répertoire courant différent (redémarrages du serveur, ou deux
projets nommés tous deux `apps/<projet>`) renverrait un chercheur
périmé, pointant vers le mauvais répertoire ou vers un répertoire
disparu.

### `DebugConfigError` et `enforce_startup_debug_policy`

Politique de démarrage « fail-closed » — garde-fou du mode debug en
production (Story 18.18, DEPLOY-8).

`DebugConfigError` est levée au démarrage quand le profil de production
tourne avec le mode debug actif. Refuser de démarrer est intentionnel :
le mode debug de Tornado active le rechargement automatique et les pages
de trace complètes, qui ne doivent jamais être exposées sur le profil de
production (`PYPLET_REQUIRE_AUTH=1`). L'exception reflète
`oauth.AuthConfigError`.

`enforce_startup_debug_policy` lève `DebugConfigError` sur le profil de
production (`PYPLET_REQUIRE_AUTH=1`) quand `PYPLET_DEBUG=1` (le défaut
de `config.py`), parce que le mode debug expose la source et les piles
d'appel et se réexécute à chaque modification de fichier. Hors profil de
production (`PYPLET_REQUIRE_AUTH` absent ou `0`), la fonction ne fait
rien : debug et rechargement automatique restent disponibles pour la
boucle de développement locale.

Le verrou est `config.require_auth` — et **non** `oauth.auth_enabled()`
— en miroir délibéré du verrou de production de
`oauth.enforce_startup_auth_policy`. Verrouiller sur `auth_enabled()`
casserait la boucle de développement authentifiée (un identifiant client
de fournisseur défini + debug + rechargement automatique), qui est un
usage quotidien et non de la production.

Effets de bord : lecture de `config`. Lève `DebugConfigError` pour
avorter le démarrage sur une brèche du profil de production.

### `_merge_app_declared_routes`

Insère les `routes()` déclarées par les applications dans
`_app_spec["handlers"]`.

Chaque application enregistrée est interrogée pour ses `routes()` et le
résultat est inséré **avant** la redirection attrape-tout `r"/.*"`, qui
est la **dernière** entrée de `_app_spec["handlers"]` (voir la
définition au niveau du module) : une route listée après elle serait
masquée en redirection et jamais atteinte. L'insertion est une
affectation de tranche `[-1:-1]`, donc l'attrape-tout reste dernier.

Appelée depuis `astart()` une fois les modules applicatifs chargés (c'est
ce qui peuple `server_applications`) et **avant** la construction de
l'`Application` Tornado depuis `_app_spec` — une fusion postérieure à
l'existence de l'`Application` n'aurait aucun effet sur le serveur en
cours d'exécution.

Une `routes()` en échec est journalisée puis ignorée, afin qu'une
application cassée ne fasse pas tomber les autres.

Retour : les tuples de handlers effectivement insérés (liste vide s'il
n'y en a aucun).

### `astart()` — ordre de démarrage

L'ordre des étapes de `astart()` est une contrainte, pas une commodité :

1. **Charger d'abord toutes les applications serveur** : importer chaque
   `*_server.py` déclenche `ServerApplication.__init_subclass__`, qui
   enregistre l'instance dans `server_applications`. Tout ce qui dérive
   de ce registre doit tourner une fois celui-ci peuplé, donc les
   modules sont chargés avant que l'`Application` Tornado ne soit
   construite depuis `_app_spec`.
2. **Politique d'authentification « fail-closed »** (Story 17.6, PB-1) :
   sur le profil de production, refuser de démarrer sur une
   configuration d'authentification mal livrée plutôt que de servir
   anonymement. Elle tourne une fois les modules chargés, afin que la
   politique voie toutes les applications découvertes.
3. **Garde-fou du mode debug** (Story 18.18, DEPLOY-8) : sur le profil de
   production, refuser de démarrer avec le debug Tornado actif
   (rechargement automatique et pages de trace ne doivent jamais partir
   en production).
4. **Fusionner les routes déclarées** par chaque application dans la
   table de handlers, avant que l'`Application` Tornado ne soit
   construite depuis `_app_spec`.

Favicon : les chemins relatifs (par exemple le défaut
`../images/...`) sont résolus par rapport au répertoire du paquet
`pyplet`, et non par rapport au répertoire courant du processus, de
sorte que le favicon fourni est trouvé quel que soit l'endroit d'où le
serveur est lancé. L'URI de données obtenu est injecté dans les réglages
Tornado, où les handlers le retrouvent.

`app.listen(..., xheaders=True)` (Story 18.18, DEPLOY-8) fait confiance
aux en-têtes `X-Forwarded-For` / `X-Forwarded-Proto` du point d'entrée,
afin que l'application voie l'IP cliente réelle et le schéma https
derrière le proxy inverse. Sans proxy en développement local, ces
en-têtes sont absents et le comportement est inchangé.

### `ServerApplication.package()` — fabrication du bundle

`package()` parcourt les fichiers de l'application, ceux d'`htpy` et de
`markupsafe`, et en construit une carte de fichiers compressée. Les
contraintes de cette boucle :

- Les fichiers sont ouverts **strictement en mode binaire** puis encodés
  en base64 : lire un asset en mode texte lèverait
  `UnicodeDecodeError` sur tout fichier non UTF-8 (images, données
  binaires) et ferait échouer la fabrication du bundle entier.
- Le répertoire `static/` du projet est exclu du bundle : il est servi
  par `AppStaticFileHandler` sur `/apps/<projet>/static/...`, l'embarquer
  dans le VFS le dupliquerait.
- `__pycache__` et le bytecode compilé sont filtrés, comme les fichiers
  cachés.
- Chaque fichier `.py` est transpilé **une seule fois** ; le résultat
  sert à la fois à la charge utile JSON et au fichier écrit sous
  `.transpiled/`. Transpiler deux fois doublerait le coût processeur de
  chaque requête de paquet.
- Un fichier `.py` qui n'est pas de l'UTF-8 valide ne fait pas échouer la
  fabrication : l'`UnicodeDecodeError` est journalisée en avertissement
  et les octets bruts sont embarqués tels quels.
- La charge utile est sérialisée en JSON puis compressée avec gzip, et
  les en-têtes `Content-Type: application/json` et
  `Content-Encoding: gzip` sont posés pour que le navigateur la
  décompresse nativement.

### `ServerApplication.serve()` — configuration PyScript et splash

`micropip` n'est pas chargé automatiquement par Pyodide : il doit être
demandé comme n'importe quel paquet, sans quoi l'`import micropip` du
`bootstrap_client` (utilisé pour installer `self.client_libraries`) lève
`ModuleNotFoundError`.

Splash de démarrage : un indicateur d'attente autonome, affiché dans
`#container` dès la première réponse HTML, qui couvre la fenêtre blanche
pendant le chargement de PyScript/Pyodide et de l'application
transpilée. Il ne porte aucune classe Tailwind (Tailwind est chargé plus
tard, côté client) et aucun asset externe — uniquement des styles en
ligne et un bloc `<style>` pour les images-clés de la rotation. Les
applications qui remplacent le contenu de `#container` (au lieu d'y
ajouter) le suppriment implicitement ; `bootstrap_client` retire par
ailleurs `#pyplet-boot-splash` **par identifiant** une fois le module
applicatif chargé, afin que les applications qui ajoutent à `#container`
ne le laissent pas tourner indéfiniment. Une enveloppe fixe, centrée sur
la fenêtre, évite toute hypothèse sur la hauteur d'une barre de
navigation.

### `ServerApplication.routes()`

Renvoie les handlers Tornado supplémentaires apportés par
l'application.

Chaque tuple est `(url_regex, RequestHandlerClass, init_kwargs)` — la
forme même que Tornado accepte dans l'argument `handlers` de
`tornado.web.Application`. Pyplet les fusionne dans la liste globale de
handlers au moment de `astart()`, insérés **avant** la redirection
attrape-tout `r"/.*"` pour que les routes soient atteignables. Le défaut
renvoie une liste vide ; les applications qui ont besoin de routes HTTP
personnalisées (par exemple un point d'entrée
`/apps/<projet>/<app>/assets/...` servant des ressources) la
redéfinissent.

Arguments des handlers Tornado : un handler qui a besoin d'un état
propre à l'application (chemins, caches, etc.) doit recevoir ces valeurs
via une méthode `initialize(...)` de Tornado, passées comme troisième
élément du tuple.

Notes :

- Pyplet invoque `routes()` **une seule fois** par application, au
  démarrage du serveur, après l'enregistrement de l'instance par
  `__init_subclass__`. La liste renvoyée n'est pas relue aux requêtes
  suivantes.
- Les handlers ajoutés via `routes()` ne passent **pas** par
  `_AuthMixin` par défaut : une route à authentification obligatoire
  doit explicitement hériter de `_AuthMixin` depuis ce module.
