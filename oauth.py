import time
import sqlite3
import secrets
from typing import Optional, List

from mcp.server.auth.provider import (
    OAuthAuthorizationServerProvider,
    AuthorizationParams,
    AuthorizationCode,
    AccessToken,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

import config

_CODE_TTL = 300
_ACCESS_TTL = 3600
_REFRESH_TTL = 30 * 24 * 3600
_SCOPES = ["news"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS oauth_clients (
  client_id TEXT PRIMARY KEY,
  data      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS oauth_codes (
  code       TEXT PRIMARY KEY,
  client_id  TEXT NOT NULL,
  data       TEXT NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS oauth_access (
  token      TEXT PRIMARY KEY,
  client_id  TEXT NOT NULL,
  scopes     TEXT NOT NULL,
  subject    TEXT,
  expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS oauth_refresh (
  token      TEXT PRIMARY KEY,
  client_id  TEXT NOT NULL,
  scopes     TEXT NOT NULL,
  subject    TEXT,
  expires_at INTEGER NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_oauth() -> None:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(_SCHEMA)


class NewsOAuthProvider(OAuthAuthorizationServerProvider):
    async def get_client(self, client_id: str) -> Optional[OAuthClientInformationFull]:
        with _connect() as conn:
            row = conn.execute(
                "SELECT data FROM oauth_clients WHERE client_id = ?", (client_id,)
            ).fetchone()
        if not row:
            return None
        return OAuthClientInformationFull.model_validate_json(row["data"])

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        with _connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO oauth_clients (client_id, data) VALUES (?, ?)",
                (client_info.client_id, client_info.model_dump_json()),
            )

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        code = secrets.token_urlsafe(32)
        auth_code = AuthorizationCode(
            code=code,
            scopes=params.scopes or _SCOPES,
            expires_at=time.time() + _CODE_TTL,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource,
            subject="owner",
        )
        with _connect() as conn:
            conn.execute(
                "INSERT INTO oauth_codes (code, client_id, data, expires_at) VALUES (?, ?, ?, ?)",
                (code, client.client_id, auth_code.model_dump_json(), int(auth_code.expires_at)),
            )
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> Optional[AuthorizationCode]:
        with _connect() as conn:
            row = conn.execute(
                "SELECT data, expires_at FROM oauth_codes WHERE code = ? AND client_id = ?",
                (authorization_code, client.client_id),
            ).fetchone()
        if not row or row["expires_at"] < time.time():
            return None
        return AuthorizationCode.model_validate_json(row["data"])

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        with _connect() as conn:
            conn.execute("DELETE FROM oauth_codes WHERE code = ?", (authorization_code.code,))
        return self._issue(client.client_id, authorization_code.scopes, authorization_code.subject)

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> Optional[RefreshToken]:
        with _connect() as conn:
            row = conn.execute(
                "SELECT scopes, expires_at FROM oauth_refresh WHERE token = ? AND client_id = ?",
                (refresh_token, client.client_id),
            ).fetchone()
        if not row or row["expires_at"] < time.time():
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=client.client_id,
            scopes=row["scopes"].split(),
            expires_at=row["expires_at"],
        )

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: List[str]
    ) -> OAuthToken:
        with _connect() as conn:
            conn.execute("DELETE FROM oauth_refresh WHERE token = ?", (refresh_token.token,))
        return self._issue(client.client_id, scopes or refresh_token.scopes, "owner")

    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        if config.TOKEN and secrets.compare_digest(token, config.TOKEN):
            return AccessToken(token=token, client_id="owner-static", scopes=_SCOPES,
                               expires_at=None, subject="owner")
        with _connect() as conn:
            row = conn.execute(
                "SELECT client_id, scopes, subject, expires_at FROM oauth_access WHERE token = ?",
                (token,),
            ).fetchone()
        if not row or row["expires_at"] < time.time():
            return None
        return AccessToken(token=token, client_id=row["client_id"], scopes=row["scopes"].split(),
                           expires_at=row["expires_at"], subject=row["subject"])

    async def revoke_token(self, token) -> None:
        with _connect() as conn:
            conn.execute("DELETE FROM oauth_access WHERE token = ?", (token.token,))
            conn.execute("DELETE FROM oauth_refresh WHERE token = ?", (token.token,))

    def _issue(self, client_id: str, scopes: List[str], subject: Optional[str]) -> OAuthToken:
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        now = int(time.time())
        scope_str = " ".join(scopes)
        with _connect() as conn:
            conn.execute(
                "INSERT INTO oauth_access (token, client_id, scopes, subject, expires_at) VALUES (?, ?, ?, ?, ?)",
                (access, client_id, scope_str, subject, now + _ACCESS_TTL),
            )
            conn.execute(
                "INSERT INTO oauth_refresh (token, client_id, scopes, subject, expires_at) VALUES (?, ?, ?, ?, ?)",
                (refresh, client_id, scope_str, subject, now + _REFRESH_TTL),
            )
        return OAuthToken(access_token=access, token_type="Bearer", expires_in=_ACCESS_TTL,
                          refresh_token=refresh, scope=scope_str)
