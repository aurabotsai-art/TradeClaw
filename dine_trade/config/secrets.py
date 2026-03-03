"""Secrets resolution: try configured backend first, then env vars.

Phase 12.6 — Production options (set DINETRADE_SECRETS_BACKEND):
  - aws  → AWS Secrets Manager (recommended for AWS)
  - gcp  → GCP Secret Manager (recommended for GCP)
  - docker → Docker secrets (/run/secrets/<key>)
  - (unset) → use env vars only

NEVER commit .env to Git. In production, use a secrets backend and set
DINETRADE_SECRETS_BACKEND accordingly.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

# Cache for backends that return a single blob (e.g. AWS JSON secret)
_secrets_cache: Optional[dict[str, str]] = None


def _get_aws_secret(key: str) -> Optional[str]:
    """Fetch key from AWS Secrets Manager. Expects one secret JSON blob."""
    global _secrets_cache
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        return None
    secret_name = os.getenv("AWS_SECRET_NAME") or os.getenv("DINETRADE_AWS_SECRET_NAME") or "dinetrade/production"
    if _secrets_cache is None:
        try:
            client = boto3.client("secretsmanager")
            resp = client.get_secret_value(SecretId=secret_name)
            raw = resp.get("SecretString")
            if raw:
                _secrets_cache = json.loads(raw)
            else:
                _secrets_cache = {}
        except (ClientError, json.JSONDecodeError):
            _secrets_cache = {}
    return (_secrets_cache or {}).get(key)


def _get_gcp_secret(key: str) -> Optional[str]:
    """Fetch key from GCP Secret Manager. One secret per key or one JSON secret."""
    global _secrets_cache
    try:
        from google.cloud import secretmanager
    except ImportError:
        return None
    project = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        return None
    # Prefer single JSON secret id
    secret_id = os.getenv("GCP_SECRET_ID") or os.getenv("DINETRADE_GCP_SECRET_ID")
    if secret_id:
        if _secrets_cache is None:
            try:
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{project}/secrets/{secret_id}/versions/latest"
                resp = client.access_secret_version(request={"name": name})
                raw = resp.payload.data.decode("utf-8")
                _secrets_cache = json.loads(raw)
            except Exception:
                _secrets_cache = {}
        return (_secrets_cache or {}).get(key)
    # Else one secret per key: secret id = key lowercased with underscores
    try:
        client = secretmanager.SecretManagerServiceClient()
        sid = key.lower().replace(" ", "_")
        name = f"projects/{project}/secrets/{sid}/versions/latest"
        resp = client.access_secret_version(request={"name": name})
        return resp.payload.data.decode("utf-8").strip()
    except Exception:
        return None


def _get_docker_secret(key: str) -> Optional[str]:
    """Read Docker secret from /run/secrets/<key> (Swarm)."""
    base = os.getenv("DOCKER_SECRETS_PATH", "/run/secrets")
    path = Path(base) / key
    try:
        if path.exists():
            return path.read_text().strip()
    except Exception:
        pass
    return None


def get_secret(key: str) -> Optional[str]:
    """Return value from configured secrets backend, or None to fall back to env."""
    backend = (os.getenv("DINETRADE_SECRETS_BACKEND") or "").strip().lower()
    if backend == "aws":
        v = _get_aws_secret(key)
        if v is not None:
            return v
    if backend == "gcp":
        v = _get_gcp_secret(key)
        if v is not None:
            return v
    if backend == "docker":
        v = _get_docker_secret(key)
        if v is not None:
            return v
    return None
