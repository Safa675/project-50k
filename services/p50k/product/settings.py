"""Validated runtime configuration; credentials are read only by runtime consumers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit
import os
import re

from pydantic import SecretStr


def _boolean(value: str, name: str) -> bool:
    if value.lower() not in {"true", "false", "1", "0"}:
        raise ValueError(f"{name} must be a boolean")
    return value.lower() in {"true", "1"}


@dataclass(frozen=True)
class Settings:
    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "p50k"
    db_user: str = "p50k_app"
    db_password_file: Path = Path("/run/secrets/db_app_password")
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "api")
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:3070", "http://localhost:3070",
        "http://127.0.0.1:3071", "http://localhost:3071",
    )
    test_endpoints: bool = False
    ai_mode: str = "off"
    analysis_date: str = "live"
    db_connect_timeout: int = 5
    auth_pepper_file: Path = Path("/run/secrets/auth_pepper")
    cookie_secure: bool = False
    trusted_proxy_hosts: tuple[str, ...] = ("web",)
    # Single-user local mode: when set, every request acts as this existing user and login is not required.
    local_open_email: str = ""

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        settings = cls(
            db_host=env.get("P50K_DB_HOST", "db"),
            db_port=int(env.get("P50K_DB_PORT", "5432")),
            db_name=env.get("P50K_DB_NAME", "p50k"),
            db_user=env.get("P50K_DB_USER", "p50k_app"),
            db_password_file=Path(env.get("P50K_DB_PASSWORD_FILE", "/run/secrets/db_app_password")),
            allowed_hosts=tuple(item.strip() for item in env.get("P50K_ALLOWED_HOSTS", "127.0.0.1,localhost,api").split(",")),
            allowed_origins=tuple(item.strip() for item in env.get(
                "P50K_ALLOWED_ORIGINS",
                "http://127.0.0.1:3070,http://localhost:3070,http://127.0.0.1:3071,http://localhost:3071",
            ).split(",")),
            test_endpoints=_boolean(env.get("P50K_TEST_ENDPOINTS", "false"), "P50K_TEST_ENDPOINTS"),
            ai_mode=env.get("P50K_AI_MODE", "off"),
            analysis_date=env.get("P50K_ANALYSIS_DATE", "live"),
            db_connect_timeout=int(env.get("P50K_DB_CONNECT_TIMEOUT", "5")),
            auth_pepper_file=Path(env.get("P50K_AUTH_PEPPER_FILE", "/run/secrets/auth_pepper")),
            cookie_secure=_boolean(env.get("P50K_COOKIE_SECURE", "false"), "P50K_COOKIE_SECURE"),
            trusted_proxy_hosts=tuple(env.get("P50K_TRUSTED_PROXY_HOSTS", "web").split(",")),
            local_open_email=env.get("P50K_LOCAL_OPEN_EMAIL", "").strip().lower(),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not 1 <= self.db_port <= 65535 or not 1 <= self.db_connect_timeout <= 30:
            raise ValueError("Invalid database port or timeout")
        for value in (self.db_host, self.db_name, self.db_user):
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
                raise ValueError("Invalid database connection identifier")
        if not self.allowed_hosts or any(host not in {"localhost", "127.0.0.1", "api"} for host in self.allowed_hosts):
            raise ValueError("Only explicit local API hosts are permitted")
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
                raise ValueError("Origins must be explicit loopback HTTP origins")
            if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment or parsed.port is None:
                raise ValueError("Origins must contain only scheme, loopback host and port")
        if self.local_open_email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.local_open_email):
            raise ValueError("Local open mode needs the email of an existing user")
        if self.test_endpoints and self.db_name != "p50k_dev":
            raise ValueError("Proxy test endpoints require the isolated p50k_dev database")
        if self.ai_mode not in {"off", "mock", "live"}:
            raise ValueError("Invalid AI mode")
        if self.ai_mode == "mock" and self.db_name != "p50k_dev":
            raise ValueError("Mock AI requires the separate development database")
        if self.analysis_date!='live':
            from datetime import date
            if date.fromisoformat(self.analysis_date).isoformat()!=self.analysis_date:
                raise ValueError('Invalid analysis date')

    def database_password(self) -> SecretStr:
        value = self.db_password_file.read_text(encoding="utf-8").strip()
        if len(value) < 24:
            raise ValueError("Database credential file is absent or invalid")
        return SecretStr(value)

    def auth_pepper(self) -> SecretStr:
        value = self.auth_pepper_file.read_text(encoding="utf-8").strip()
        if len(value) < 32:
            raise ValueError("Authentication pepper is absent or invalid")
        return SecretStr(value)

    def connect_kwargs(self) -> dict[str, object]:
        return {
            "host": self.db_host, "port": self.db_port, "dbname": self.db_name,
            "user": self.db_user, "password": self.database_password().get_secret_value(),
            "connect_timeout": self.db_connect_timeout,
        }
