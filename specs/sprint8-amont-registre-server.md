# Registre amont — commentaires et docstrings de `pyplet/server/_server.py`

Sprint #8, volet amont. Application de la règle éditoriale du projet
(`CLAUDE.md`, couche 0) au code **préexistant** de
`pyplet/server/_server.py` : un commentaire `#` qui porte une *raison*
devient un test ; un TODO devient une issue GitLab ; tout le reste
(séparateurs, code mort, paraphrase du code) disparaît. Les docstrings de
plus de 3 lignes migrent vers `docs/api/server.md` et sont ramenées à
3 lignes au plus dans le code.

## Périmètre et mesure

- SHA de base : `ed5401b` (`ed5401b2ea4116c47a9097e4cf25af0d6c3829fb`).
- Fichier traité : `pyplet/server/_server.py`. Aucun autre fichier de
  production n'est touché.
- Mesure (`tokenize` pour les commentaires, `ast` pour les docstrings,
  script jetable non versionné) :

| État | Commentaires | dont non-directives | Docstrings > 3 lignes |
| --- | --- | --- | --- |
| Avant (`ed5401b`) | 142 | 142 | 16 |
| Après | 3 | 3 (`# nosec`, voir plus bas) | 0 |

- Hors périmètre du comptage : la f-string `python_code` (lignes 672–990
  après passe) transporte le programme client PyScript/MicroPython comme
  donnée ; elle contient 51 lignes portant `#` qui sont des commentaires
  du programme *client*, pas de `_server.py`. `tokenize` ne les voit pas
  (jetons `STRING`) ; un `grep '#'` les compte. La mesure de référence est
  `tokenize` (spec, § Définitions, « Comptage »). La chaîne est inchangée
  à l'octet (identité d'AST, voir Vérifications).

- Définition retenue pour « directive d'outillage » (fixée par la
  commande) : texte après `#` et espaces commençant par `noqa`, `type:`,
  `pragma`, `ruff:`, `fmt:`, `pylint`, `mypy:`, `isort:`, `flake8:`,
  `coding`, `-*-`, `!`.
- Définition retenue pour « docstring longue » : nœud chaîne dont
  `end_lineno - lineno + 1 > 3`, lignes vides comprises.

## Répartition des 139 commentaires supprimés

| Catégorie | Nombre |
| --- | --- |
| `raison → test <nom du test>` | 70 |
| `raison → docs/api/server.md` | 18 |
| `TODO → issue (proposed: …)` | 1 |
| `séparateur` | 18 |
| `paraphrase` | 32 |
| `code mort` | 0 |

Les 70 lignes `raison → test` citent 20 identifiants de test distincts,
tous existants et passants. Pour rejouer la vérification, extraire la
colonne et la donner à `pytest` :

```
grep -o 'raison → test [^|]*' specs/sprint8-amont-registre-server.md \
  | sed 's/raison → test //;s/ *$//' | sort -u > /tmp/nodeids.txt
uv run --extra test pytest @/tmp/nodeids.txt -q   →  20 passed in 0.13s
```

Un bloc de commentaire multiligne donne une ligne de registre par ligne
de commentaire, toutes vers la même destination : le texte verbatim de
chaque ligne reste ainsi retrouvable par `grep`.

Sur les lignes `raison → docs/api/server.md`, la page de destination
porte la **raison rendue en français**, pas la chaîne anglaise d'origine
— le registre garde le verbatim, la documentation porte le fond. Un
relecteur y cherche donc le contenu de la raison, non le texte source.

## Commentaires supprimés

| Fichier | Ligne | Commentaire (verbatim) | Catégorie |
| --- | --- | --- | --- |
| `pyplet/server/_server.py` | 29 | # Configure logging | paraphrase |
| `pyplet/server/_server.py` | 37 | # Fixed virtual directory name for app files inside the browser-side | raison → test tests/package_test.py::TestPackageVfsKeys::test_absolute_apps_dir |
| `pyplet/server/_server.py` | 38 | # (Pyodide/MicroPython) virtual filesystem — see `ServerApplication.package` | raison → test tests/package_test.py::TestPackageVfsKeys::test_absolute_apps_dir |
| `pyplet/server/_server.py` | 39 | # and `ServerApplication.serve`. Kept separate from `config.apps` (the | raison → test tests/package_test.py::TestPackageVfsKeys::test_absolute_apps_dir |
| `pyplet/server/_server.py` | 40 | # *server's* on-disk apps directory, which may be relative, nested, or | raison → test tests/package_test.py::TestPackageVfsKeys::test_absolute_apps_dir |
| `pyplet/server/_server.py` | 41 | # absolute) so the client-side VFS layout and import path stay portable | raison → test tests/package_test.py::TestPackageVfsKeys::test_absolute_apps_dir |
| `pyplet/server/_server.py` | 42 | # regardless of how `config.apps` is configured. | raison → test tests/package_test.py::TestPackageVfsKeys::test_absolute_apps_dir |
| `pyplet/server/_server.py` | 45 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 46 | # Auth gate mixin | séparateur |
| `pyplet/server/_server.py` | 47 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 62 | # Sub-classes set this to True for WebSocket handlers where redirects | raison → test tests/server_auth_gate_test.py::test_server_websocket_is_flagged_ws_so_the_gate_answers_401 |
| `pyplet/server/_server.py` | 63 | # are not meaningful. | raison → test tests/server_auth_gate_test.py::test_server_websocket_is_flagged_ws_so_the_gate_answers_401 |
| `pyplet/server/_server.py` | 68 | # Return a sentinel so Tornado's @authenticated decorator works. | raison → test tests/server_auth_gate_test.py::test_get_current_user_returns_truthy_sentinel_when_auth_disabled |
| `pyplet/server/_server.py` | 111 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 112 | # Static file handler (no auth required) | séparateur |
| `pyplet/server/_server.py` | 113 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 151 | # StaticFileHandler.initialize requires a ``path``; the real | raison → test tests/app_static_traversal_test.py::AppStaticPerRequestRootTest::test_each_request_is_rooted_at_its_own_project |
| `pyplet/server/_server.py` | 152 | # per-request root is (re)computed in get() once ``project`` is known. | raison → test tests/app_static_traversal_test.py::AppStaticPerRequestRootTest::test_each_request_is_rooted_at_its_own_project |
| `pyplet/server/_server.py` | 159 | # Confine this request to the requested app's own static/ dir so a | raison → test tests/app_static_traversal_test.py::AppStaticPerRequestRootTest::test_each_request_is_rooted_at_its_own_project |
| `pyplet/server/_server.py` | 160 | # traversal in ``path`` cannot escape into the wider apps/ tree. | raison → test tests/app_static_traversal_test.py::AppStaticPerRequestRootTest::test_each_request_is_rooted_at_its_own_project |
| `pyplet/server/_server.py` | 167 | # Tornado dispatches every method as method(*path_args), so HEAD must | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_head_legit_static_file_is_served |
| `pyplet/server/_server.py` | 168 | # accept both capture groups too (project, tail). Delegate to the | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_head_legit_static_file_is_served |
| `pyplet/server/_server.py` | 169 | # body-less GET path (which sets the per-request ``self.root``), | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_head_traversal_to_sibling_server_source_blocked |
| `pyplet/server/_server.py` | 170 | # mirroring StaticFileHandler.head -> get(path, include_body=False). | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_head_legit_static_file_is_served |
| `pyplet/server/_server.py` | 176 | # Tornado's own containment check is LEXICAL: it compares | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_symlink_out_of_static_dir_blocked |
| `pyplet/server/_server.py` | 177 | # ``os.path.abspath`` prefixes and never resolves symlinks. So a | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_symlink_out_of_static_dir_blocked |
| `pyplet/server/_server.py` | 178 | # symlink planted inside an app's ``static/`` dir is served whatever it | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_symlink_out_of_static_dir_blocked |
| `pyplet/server/_server.py` | 179 | # points at, including files entirely outside the ``apps/`` tree — an | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_symlink_out_of_static_dir_blocked |
| `pyplet/server/_server.py` | 180 | # unauthenticated arbitrary-file read, strictly worse than the | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_symlink_out_of_static_dir_blocked |
| `pyplet/server/_server.py` | 181 | # traversal the per-request root above closes. Re-run the containment | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_symlink_out_of_static_dir_blocked |
| `pyplet/server/_server.py` | 182 | # test on the SYMLINK-RESOLVED paths. Symlinks that stay inside the | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_symlink_out_of_static_dir_blocked |
| `pyplet/server/_server.py` | 183 | # app's own ``static/`` dir keep working (they resolve inside root). | raison → test tests/app_static_traversal_test.py::AppStaticTraversalTest::test_symlink_inside_static_dir_still_served |
| `pyplet/server/_server.py` | 196 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 197 | # Application handlers | séparateur |
| `pyplet/server/_server.py` | 198 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 208 | # Encode the binary SVG data to a base64 string | paraphrase |
| `pyplet/server/_server.py` | 211 | # Format it as a Data URI for SVG | paraphrase |
| `pyplet/server/_server.py` | 215 | # Matches the opening <head ...> tag so the favicon can be inserted | paraphrase |
| `pyplet/server/_server.py` | 216 | # right after it. | paraphrase |
| `pyplet/server/_server.py` | 218 | # Matches any <link ...> tag so its `rel` attribute can be inspected. | paraphrase |
| `pyplet/server/_server.py` | 220 | # Matches a `rel` attribute, quoted or unquoted, inside a tag. | paraphrase |
| `pyplet/server/_server.py` | 245 | # 1. Check if we actually have a favicon loaded in settings | paraphrase |
| `pyplet/server/_server.py` | 251 | # 2. Normalize content to a plain `str`. Going through bytes | raison → test tests/server_test.py::TestWriteHtmlFaviconEnabled::test_markup_content_is_injected_as_real_markup |
| `pyplet/server/_server.py` | 252 | # matters here: htpy nodes/markupsafe.Markup render via `str()` | raison → test tests/server_test.py::TestWriteHtmlFaviconEnabled::test_markup_content_is_injected_as_real_markup |
| `pyplet/server/_server.py` | 253 | # into a `Markup` instance, and slicing/concatenating a plain str | raison → test tests/server_test.py::TestWriteHtmlFaviconEnabled::test_markup_content_is_injected_as_real_markup |
| `pyplet/server/_server.py` | 254 | # onto a `Markup` auto-*escapes* that plain str (e.g. our raw | raison → test tests/server_test.py::TestWriteHtmlFaviconEnabled::test_markup_content_is_injected_as_real_markup |
| `pyplet/server/_server.py` | 255 | # <link> tag below would come out as "&lt;link ...&gt;"). Encoding | raison → test tests/server_test.py::TestWriteHtmlFaviconEnabled::test_markup_content_is_injected_as_real_markup |
| `pyplet/server/_server.py` | 256 | # then decoding strips the Markup type, leaving a genuine str. | raison → test tests/server_test.py::TestWriteHtmlFaviconEnabled::test_markup_content_is_injected_as_real_markup |
| `pyplet/server/_server.py` | 263 | # 3. Inject the favicon right after <head>, unless one is | raison → test tests/server_test.py::TestWriteHtmlFaviconEnabled::test_leaves_existing_favicon_untouched |
| `pyplet/server/_server.py` | 264 | # already present anywhere in the document. | raison → test tests/server_test.py::TestWriteHtmlFaviconEnabled::test_leaves_existing_favicon_untouched |
| `pyplet/server/_server.py` | 496 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 497 | # Tornado application spec | séparateur |
| `pyplet/server/_server.py` | 498 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 516 | # App static resources (static files) | paraphrase |
| `pyplet/server/_server.py` | 518 | # Capture the app project and the file tail SEPARATELY so the | raison → test tests/app_static_traversal_test.py::test_app_static_route_captures_project_and_tail_separately |
| `pyplet/server/_server.py` | 519 | # handler can root itself at <apps>/<project>/static/ per request | raison → test tests/app_static_traversal_test.py::test_app_static_route_captures_project_and_tail_separately |
| `pyplet/server/_server.py` | 520 | # (see AppStaticFileHandler): a ".." in the tail then cannot escape | raison → test tests/app_static_traversal_test.py::test_app_static_route_captures_project_and_tail_separately |
| `pyplet/server/_server.py` | 521 | # the requested app's own static/ dir into the apps/ tree. | raison → test tests/app_static_traversal_test.py::test_app_static_route_captures_project_and_tail_separately |
| `pyplet/server/_server.py` | 526 | # App upload endpoint (for upload() and upload_area()) | paraphrase |
| `pyplet/server/_server.py` | 550 | # Signs session cookies.  Falls back to a per-process random value so the | raison → test tests/oauth_cookie_security_test.py::test_enforce_allows_when_not_production_without_secret |
| `pyplet/server/_server.py` | 551 | # server still works without PYPLET_COOKIE_SECRET | raison → test tests/oauth_cookie_security_test.py::test_enforce_allows_when_not_production_without_secret |
| `pyplet/server/_server.py` | 552 | # (sessions lost on restart). | raison → test tests/oauth_cookie_security_test.py::test_enforce_allows_when_not_production_without_secret |
| `pyplet/server/_server.py` | 554 | # Max WebSocket frame size. Tornado defaults to ~10 MB, which a base64'd | raison → test tests/server_settings_test.py::test_app_spec_sets_websocket_max_message_size |
| `pyplet/server/_server.py` | 555 | # document upload exceeds (killing the socket before app code runs). The | raison → test tests/server_settings_test.py::test_app_spec_sets_websocket_max_message_size |
| `pyplet/server/_server.py` | 556 | # default 40 MB carries a 25 MB upload (~33 MB frame) with headroom; raise | raison → test tests/server_settings_test.py::test_app_spec_sets_websocket_max_message_size |
| `pyplet/server/_server.py` | 557 | # PYPLET_WS_MAX_MESSAGE_MB in lockstep with any app's per-document cap. | raison → test tests/server_settings_test.py::test_app_spec_sets_websocket_max_message_size |
| `pyplet/server/_server.py` | 593 | # Must be an absolute path: Python's import machinery caches a | raison → test tests/app_discovery_test.py::TestAppDiscovery::test_reused_relative_apps_name_across_different_cwd |
| `pyplet/server/_server.py` | 594 | # per-directory finder in `sys.path_importer_cache` keyed by the | raison → test tests/app_discovery_test.py::TestAppDiscovery::test_reused_relative_apps_name_across_different_cwd |
| `pyplet/server/_server.py` | 595 | # literal path string, so a relative string reused under a | raison → test tests/app_discovery_test.py::TestAppDiscovery::test_reused_relative_apps_name_across_different_cwd |
| `pyplet/server/_server.py` | 596 | # different cwd (e.g. across server restarts, or two projects | raison → test tests/app_discovery_test.py::TestAppDiscovery::test_reused_relative_apps_name_across_different_cwd |
| `pyplet/server/_server.py` | 597 | # that both happen to be named "apps/<project>") would return a | raison → test tests/app_discovery_test.py::TestAppDiscovery::test_reused_relative_apps_name_across_different_cwd |
| `pyplet/server/_server.py` | 598 | # stale finder pointing at the wrong (or now-gone) directory. | raison → test tests/app_discovery_test.py::TestAppDiscovery::test_reused_relative_apps_name_across_different_cwd |
| `pyplet/server/_server.py` | 607 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 608 | # Fail-closed startup policy — production debug guard (Story 18.18, DEPLOY-8) | séparateur |
| `pyplet/server/_server.py` | 609 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 692 | # Load all server applications FIRST: importing each *_server.py | raison → test tests/server_routes_hook_test.py::AppDeclaredRouteTest::test_declared_route_reachable_and_catchall_last |
| `pyplet/server/_server.py` | 693 | # fires ServerApplication.**init_subclass**, which registers the | raison → test tests/server_routes_hook_test.py::AppDeclaredRouteTest::test_declared_route_reachable_and_catchall_last |
| `pyplet/server/_server.py` | 694 | # instance in server_applications. Anything derived from that | raison → test tests/server_routes_hook_test.py::AppDeclaredRouteTest::test_declared_route_reachable_and_catchall_last |
| `pyplet/server/_server.py` | 695 | # registry has to run once it is populated, so the modules are | raison → test tests/server_routes_hook_test.py::AppDeclaredRouteTest::test_declared_route_reachable_and_catchall_last |
| `pyplet/server/_server.py` | 696 | # loaded before the Tornado Application is built from _app_spec. | raison → test tests/server_routes_hook_test.py::AppDeclaredRouteTest::test_declared_route_reachable_and_catchall_last |
| `pyplet/server/_server.py` | 704 | # Fail-closed auth policy (Story 17.6, PB-1): on the production profile, | raison → test tests/oauth_cookie_security_test.py::test_enforce_raises_when_production_and_no_cookie_secret |
| `pyplet/server/_server.py` | 705 | # refuse to boot on a misdelivered auth config rather than serve | raison → test tests/oauth_cookie_security_test.py::test_enforce_raises_when_production_and_no_cookie_secret |
| `pyplet/server/_server.py` | 706 | # anonymously. Runs once the modules are loaded, so the policy sees | raison → test tests/oauth_cookie_security_test.py::test_enforce_raises_when_production_and_no_cookie_secret |
| `pyplet/server/_server.py` | 707 | # every discovered application. | raison → test tests/oauth_cookie_security_test.py::test_enforce_raises_when_production_and_no_cookie_secret |
| `pyplet/server/_server.py` | 710 | # Story 18.18 (DEPLOY-8): on the production profile, refuse to boot with | raison → test tests/prod_hardening_test.py::test_debug_policy_raises_when_production_and_debug_on |
| `pyplet/server/_server.py` | 711 | # Tornado debug on (autoreload + traceback pages must never ship to prod). | raison → test tests/prod_hardening_test.py::test_debug_policy_raises_when_production_and_debug_on |
| `pyplet/server/_server.py` | 714 | # Merge the routes each app declares into the handler table before the | raison → test tests/server_routes_hook_test.py::AppDeclaredRouteTest::test_declared_route_reachable_and_catchall_last |
| `pyplet/server/_server.py` | 715 | # Tornado Application is built from _app_spec. | raison → test tests/server_routes_hook_test.py::AppDeclaredRouteTest::test_declared_route_reachable_and_catchall_last |
| `pyplet/server/_server.py` | 720 | # Relative paths (e.g. the default "../images/...") are resolved | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 721 | # against the pyplet package directory, not the process CWD, so | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 722 | # the bundled favicon is found regardless of where the server | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 723 | # is launched from. | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 736 | # Inject it into the Tornado settings so the Handlers can find it | paraphrase |
| `pyplet/server/_server.py` | 740 | # Story 18.18 (DEPLOY-8): trust the edge's X-Forwarded-For / -Proto so the | raison → test tests/prod_hardening_test.py::test_astart_listens_with_xheaders |
| `pyplet/server/_server.py` | 741 | # app sees the real client IP + https scheme behind the reverse proxy. No | raison → test tests/prod_hardening_test.py::test_astart_listens_with_xheaders |
| `pyplet/server/_server.py` | 742 | # proxy in local dev ⇒ those headers are absent ⇒ behavior unchanged. | raison → test tests/prod_hardening_test.py::test_astart_listens_with_xheaders |
| `pyplet/server/_server.py` | 761 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 762 | # Base class for user applications | séparateur |
| `pyplet/server/_server.py` | 763 | # --------------------------------------------------------------------------- | séparateur |
| `pyplet/server/_server.py` | 780 | # Safely locate htpy and get its parent directory | paraphrase |
| `pyplet/server/_server.py` | 804 | # Inject htpy dynamically! | paraphrase |
| `pyplet/server/_server.py` | 809 | # Define the exact, absolute path to the project's static folder | paraphrase |
| `pyplet/server/_server.py` | 814 | # Skip **pycache** and similar hidden files | paraphrase |
| `pyplet/server/_server.py` | 822 | # Filter out cache and compiled bytecode | paraphrase |
| `pyplet/server/_server.py` | 829 | # Filter out project static folder | paraphrase |
| `pyplet/server/_server.py` | 835 | # Read as bytes and encode to base64 for JSON safety | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 836 | # 1. Open strictly in binary mode to prevent | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 837 | # UnicodeDecodeError on assets | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 841 | # 2. Process Python files through the transpiler | paraphrase |
| `pyplet/server/_server.py` | 844 | # Decode to string for AST manipulation | paraphrase |
| `pyplet/server/_server.py` | 847 | # Transpile ONCE to save CPU time | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 855 | # Write the transpiled content to | paraphrase |
| `pyplet/server/_server.py` | 856 | # "apps"/.transpiled/... | paraphrase |
| `pyplet/server/_server.py` | 870 | # Fallback if a .py file is somehow weirdly | paraphrase |
| `pyplet/server/_server.py` | 871 | # encoded/binary | paraphrase |
| `pyplet/server/_server.py` | 878 | # 3. Handle all other files (images, data, etc.) natively | paraphrase |
| `pyplet/server/_server.py` | 882 | # 4. Encode the final bytes to base64 for the JSON payload | paraphrase |
| `pyplet/server/_server.py` | 888 | # Convert to JSON and compress | paraphrase |
| `pyplet/server/_server.py` | 892 | # Set headers so the browser natively decompresses the payload | paraphrase |
| `pyplet/server/_server.py` | 900 | # Update the extension to .json | paraphrase |
| `pyplet/server/_server.py` | 901 | # COULD BE THE EXAMPLE RELATED BUG | TODO → issue (proposed: Bundle `package()` : élucider et lever le doute « COULD BE THE EXAMPLE RELATED BUG » sur la réécriture d'extension en `.json`) |
| `pyplet/server/_server.py` | 904 | # Inject PyScript core scripts | paraphrase |
| `pyplet/server/_server.py` | 922 | # The Python script to run on the client | paraphrase |
| `pyplet/server/_server.py` | 923 | # (works in both Pyodide and MicroPython) | paraphrase |
| `pyplet/server/_server.py` | 1252 | # Toggle between interpreters based on your class property | paraphrase |
| `pyplet/server/_server.py` | 1256 | # `micropip` itself isn't auto-loaded by Pyodide; it must be | raison → test tests/pyscript_config_test.py::TestPyScriptPackagesConfig::test_pyodide_packages_include_micropip |
| `pyplet/server/_server.py` | 1257 | # requested like any other package, or the runtime | raison → test tests/pyscript_config_test.py::TestPyScriptPackagesConfig::test_pyodide_packages_include_micropip |
| `pyplet/server/_server.py` | 1258 | # `import micropip` in `bootstrap_client` (used to install | raison → test tests/pyscript_config_test.py::TestPyScriptPackagesConfig::test_pyodide_packages_include_micropip |
| `pyplet/server/_server.py` | 1259 | # `self.client_libraries`) raises ModuleNotFoundError. | raison → test tests/pyscript_config_test.py::TestPyScriptPackagesConfig::test_pyodide_packages_include_micropip |
| `pyplet/server/_server.py` | 1267 | # Boot splash: a self-contained spinner shown inside #container from | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 1268 | # the very first HTML response, covering the blank window while | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 1269 | # PyScript/Pyodide and the transpiled app load. It carries no Tailwind | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 1270 | # classes (Tailwind loads later, client-side) and no external assets — | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 1271 | # only inline styles plus one <style> block for the rotation keyframes. | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 1272 | # Apps that replace #container's contents (rather than appending to | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 1273 | # them) drop it implicitly; bootstrap_client also removes | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 1274 | # #pyplet-boot-splash by id once the app module has loaded, so apps | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 1275 | # that append to #container don't leave it spinning. A fixed, | raison → docs/api/server.md |
| `pyplet/server/_server.py` | 1276 | # viewport-centered wrapper avoids any navbar-height assumption. | raison → docs/api/server.md |

## Commentaires conservés — écart assumé

Trois commentaires subsistent, tous `# nosec` :

| Fichier | Ligne (`ed5401b`) | Ligne (après) | Commentaire |
| --- | --- | --- | --- |
| `pyplet/server/_server.py` | 289 | 204 | `# nosec` |
| `pyplet/server/_server.py` | 1277 | 1009 | `# nosec` |
| `pyplet/server/_server.py` | 1294 | 1026 | `# nosec` |

`nosec` n'apparaît pas dans la liste des directives d'outillage fixée par
la commande, donc au sens strict ces trois commentaires devaient
disparaître. Ils sont **conservés** : c'est une directive d'outillage de
fait, lue par `bandit` (marqueur de suppression), et son retrait rend la
porte de sécurité rouge. Mesuré sur deux copies du fichier livré, hors
dépôt :

```
bandit -q with_nosec.py      → aucune constatation
bandit -q without_nosec.py   → Medium: 2  (High confidence: 2)
```

Les deux constatations sont les `markupsafe.Markup(...)` de l'injection
de favicon et du splash (B704). Décision à trancher par le propriétaire :
soit `nosec` rejoint la liste des directives, soit les suppressions
passent en configuration `bandit` (`pyproject.toml`, hors du périmètre de
cet agent).

## Docstrings longues migrées

Les 16 docstrings de plus de 3 lignes sont reprises **en français** dans
`docs/api/server.md` (page existante de l'arbre Sphinx, section
« Notes d'implémentation du serveur »), et ramenées à 3 lignes au plus
dans le code. La reprise n'est pas une copie : la documentation du projet
est en français, le fond de chaque docstring y est rendu, pas son texte
anglais d'origine.

| Fichier | Lignes | Symbole | Lignes source | Destination |
| --- | --- | --- | --- | --- |
| `pyplet/server/_server.py` | 51–60 | `_AuthMixin` | 10 | `docs/api/server.md` § `_AuthMixin` — portail d'authentification |
| `pyplet/server/_server.py` | 75–78 | `_AuthMixin._require_auth` | 4 | `docs/api/server.md` § `_AuthMixin._require_auth` |
| `pyplet/server/_server.py` | 122–126 | `StaticFileHandler.set_extra_headers` | 5 | `docs/api/server.md` § `StaticFileHandler.set_extra_headers` |
| `pyplet/server/_server.py` | 131–148 | `AppStaticFileHandler` | 18 | `docs/api/server.md` § `AppStaticFileHandler` |
| `pyplet/server/_server.py` | 239–242 | `BaseHandler` | 4 | `docs/api/server.md` § `BaseHandler` — injection du favicon |
| `pyplet/server/_server.py` | 300–305 | `PackageHandler.get` | 6 | `docs/api/server.md` § `PackageHandler.get` |
| `pyplet/server/_server.py` | 316–319 | `LoginHandler` | 4 | `docs/api/server.md` § `LoginHandler` |
| `pyplet/server/_server.py` | 349–358 | `HealthzHandler` | 10 | `docs/api/server.md` § `HealthzHandler` |
| `pyplet/server/_server.py` | 398–401 | `MagicLinkVerifyHandler` | 4 | `docs/api/server.md` § `MagicLinkVerifyHandler` |
| `pyplet/server/_server.py` | 421–442 | `ServerWebSocket.check_origin` | 22 | `docs/api/server.md` § `ServerWebSocket.check_origin` |
| `pyplet/server/_server.py` | 454–464 | `ServerWebSocket.get_compression_options` | 11 | `docs/api/server.md` § `ServerWebSocket.get_compression_options` |
| `pyplet/server/_server.py` | 563–570 | `_ensure_namespace_package` | 8 | `docs/api/server.md` § `_ensure_namespace_package` |
| `pyplet/server/_server.py` | 613–618 | `DebugConfigError` | 6 | `docs/api/server.md` § `DebugConfigError` et `enforce_startup_debug_policy` |
| `pyplet/server/_server.py` | 622–640 | `enforce_startup_debug_policy` | 19 | `docs/api/server.md` § `DebugConfigError` et `enforce_startup_debug_policy` |
| `pyplet/server/_server.py` | 651–670 | `_merge_app_declared_routes` | 20 | `docs/api/server.md` § `_merge_app_declared_routes` |
| `pyplet/server/_server.py` | 1308–1336 | `ServerApplication.routes` | 29 | `docs/api/server.md` § `ServerApplication.routes()` |

## Issue GitLab proposée

Un seul TODO dans le fichier. L'agent ne crée pas d'issue :
l'orchestrateur la crée sur GitLab `seglab/pyplet` (projet 1724).

### Issue 1

- **Titre** : Bundle `package()` : élucider et lever le doute
  « COULD BE THE EXAMPLE RELATED BUG » sur la réécriture d'extension en
  `.json`
- **Corps** :

  > `pyplet/server/_server.py`, `ServerApplication.package()`, portait
  > jusqu'au sprint #8 un commentaire nu, ligne 901 à `ed5401b` :
  > `# COULD BE THE EXAMPLE RELATED BUG`, placé juste après la
  > réécriture de l'extension du fichier de paquet en `.json`
  > (`# Update the extension to .json`).
  >
  > Le commentaire ne dit ni quel bug, ni quel exemple. Il a été retiré
  > du code par la passe éditoriale et enregistré ici pour ne pas perdre
  > le soupçon.
  >
  > À faire : reproduire le défaut soupçonné sur les exemples
  > (`seglab/apps/pyplet_examples`), déterminer si la réécriture
  > d'extension en `.json` en est la cause, puis soit corriger et
  > verrouiller par un test, soit clore l'issue en constatant que le
  > soupçon n'a plus d'objet.
  >
  > Origine : sprint #8, registre
  > `specs/sprint8-amont-registre-server.md`.

## Vérifications

Toutes commandes lancées depuis la racine de l'arbre de travail.

- **Comptes après passe** : `comments = 3`, `non-directive = 3`,
  `long docstrings = 0`.
- **Aucun changement de code** : l'AST du fichier livré, docstrings
  neutralisées, est identique à celui de `ed5401b`
  (`ast.dump` comparé — `True`). Le diff ne contient donc que des lignes
  `#`, des lignes de docstring et des lignes vides.
- **Tests cités** : les 20 identifiants de test de la colonne
  « Catégorie » passent (`20 passed`).
- **Suite complète** : `make test` — voir le rapport de fin de lot.
- **Lint** : `make lint`.
