"""Garde d'authentification `_AuthMixin` — cf. docs/api/server.md."""

from types import SimpleNamespace

import pytest

from pyplet.server import oauth
from pyplet.server._server import _AuthMixin


class _Recorder:
    """Double de handler Tornado enregistrant la terminaison choisie."""

    def __init__(self):
        self.status = None
        self.written = []
        self.finished = False
        self.redirected = None
        self.request = SimpleNamespace(uri="/apps/demo/demo")

    def set_status(self, code):
        self.status = code

    def write(self, chunk):
        self.written.append(chunk)

    def finish(self, chunk=None):
        self.finished = True
        if chunk is not None:
            self.written.append(chunk)

    def redirect(self, url):
        self.redirected = url


class _WsGate(_AuthMixin, _Recorder):
    """Handler WebSocket : `_is_ws` vaut True."""

    _is_ws = True


class _PageGate(_AuthMixin, _Recorder):
    """Handler de page HTML : `_is_ws` garde sa valeur par défaut."""


@pytest.mark.unit
def test_get_current_user_returns_truthy_sentinel_when_auth_disabled(
    monkeypatch,
):
    """Auth désactivée ⇒ `get_current_user` renvoie une valeur vraie."""
    monkeypatch.setattr(oauth, "auth_enabled", lambda: False)

    user = _PageGate().get_current_user()

    assert user, (
        "get_current_user doit renvoyer une sentinelle VRAIE quand l'auth "
        "est désactivée : le décorateur @authenticated de Tornado redirige "
        "vers login_url dès que current_user est falsy, donc renvoyer None "
        "ou {} enfermerait dehors toute page non authentifiée"
    )


@pytest.mark.unit
def test_ws_gate_answers_401_and_never_redirects(monkeypatch):
    """`_is_ws` ⇒ terminaison en 401, jamais de redirection."""
    monkeypatch.setattr(oauth, "auth_enabled", lambda: True)
    monkeypatch.setattr(oauth, "get_session", lambda handler: None)
    gate = _WsGate()

    assert gate._require_auth() is None

    assert gate.status == 401, (
        f"un upgrade WebSocket non authentifié doit recevoir 401, pas "
        f"{gate.status!r} : une redirection 302 n'a aucun sens pour un "
        "client WebSocket, qui ne la suit pas et voit un échec de handshake"
    )
    assert gate.redirected is None, (
        f"le garde WebSocket a redirigé vers {gate.redirected!r} au lieu "
        "de répondre 401"
    )
    assert gate.finished, "la requête WebSocket refusée doit être terminée"


@pytest.mark.unit
def test_page_gate_redirects_to_login_and_never_sets_401(monkeypatch):
    """Hors `_is_ws` ⇒ redirection vers /login en conservant `next`."""
    monkeypatch.setattr(oauth, "auth_enabled", lambda: True)
    monkeypatch.setattr(oauth, "get_session", lambda handler: None)
    gate = _PageGate()

    assert gate._require_auth() is None

    assert gate.redirected == "/login?next=/apps/demo/demo", (
        f"une page HTML non authentifiée doit être redirigée vers /login "
        f"avec l'URI demandée en next, obtenu {gate.redirected!r}"
    )
    assert gate.status is None, (
        f"une page HTML ne doit pas être terminée par un code {gate.status!r} "
        "à la place de la redirection"
    )
