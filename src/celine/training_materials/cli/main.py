from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess

import httpx
import typer

from celine.sdk.auth import OidcClientCredentialsProvider

app = typer.Typer(name="celine-training-materials", no_args_is_help=True)


async def _get_token_from_client_credentials(
    auth_url: str,
    client_id: str,
    client_secret: str,
    scope: str | None = None,
    verify_ssl: bool = True,
) -> str:
    provider = OidcClientCredentialsProvider(
        base_url=auth_url,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        verify_ssl=verify_ssl,
    )
    access_token = await provider.get_token()
    return access_token.access_token


def _resolve_token(
    token: str | None,
    auth_url: str,
    client_id: str | None,
    client_secret: str | None,
    scope: str | None,
    verify_ssl: bool,
) -> str:
    if token:
        return token
    if client_id and client_secret:
        return asyncio.run(
            _get_token_from_client_credentials(
                auth_url=auth_url,
                client_id=client_id,
                client_secret=client_secret,
                scope=scope,
                verify_ssl=verify_ssl,
            )
        )
    raise typer.BadParameter(
        "Authentication required. Provide --token or --client-id + --client-secret."
    )


@app.command("sync-ai-assistant")
def sync_ai_assistant(
    api: str = typer.Option(
        "http://localhost:8012",
        "--api",
        help="AI assistant API base URL",
        envvar="TRAINING_MATERIALS_API_URL",
    ),
    commit: str = typer.Option(
        "",
        "--commit",
        help="Commit SHA to sync. Defaults to current HEAD.",
        envvar="TRAINING_MATERIALS_COMMIT",
    ),
    token: str | None = typer.Option(
        None,
        "--token",
        help="Pre-obtained JWT access token",
        envvar="TRAINING_MATERIALS_TOKEN",
    ),
    client_id: str | None = typer.Option(
        None,
        "--client-id",
        help="OAuth2 client ID",
        envvar="TRAINING_MATERIALS_CLIENT_ID",
    ),
    client_secret: str | None = typer.Option(
        None,
        "--client-secret",
        help="OAuth2 client secret",
        envvar="TRAINING_MATERIALS_CLIENT_SECRET",
    ),
    auth_url: str = typer.Option(
        "http://localhost:8080/realms/celine",
        "--auth-url",
        help="OIDC/Keycloak realm URL",
        envvar="TRAINING_MATERIALS_AUTH_URL",
    ),
    scope: str | None = typer.Option(
        None,
        "--scope",
        help="OAuth2 scope",
        envvar="TRAINING_MATERIALS_SCOPE",
    ),
    timeout: float = typer.Option(60.0, "--timeout", help="HTTP timeout in seconds"),
    verify_ssl: bool = typer.Option(
        True, "--verify-ssl/--no-verify-ssl", help="Verify TLS certificates"
    ),
):
    commit_sha = commit or _current_head()
    access_token = _resolve_token(
        token=token,
        auth_url=auth_url,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        verify_ssl=verify_ssl,
    )
    url = f"{api.rstrip('/')}/admin/training-materials/sync"
    payload = {"target_ref": commit_sha}

    with httpx.Client(timeout=timeout, verify=verify_ssl) as client:
        response = client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if response.status_code >= 400:
        raise typer.BadParameter(
            f"POST {url} failed [{response.status_code}]: {response.text}"
        )

    data = response.json()
    typer.echo(f"Synced commit: {data['git']['current_commit']}")
    typer.echo(f"Indexed: {data['ingest']['indexed']}")
    typer.echo(f"Skipped: {data['ingest']['skipped']}")


def _current_head() -> str:
    git_dir = Path.cwd()
    result = subprocess.run(
        ["git", "-C", str(git_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    commit_sha = result.stdout.strip()
    if not commit_sha:
        raise typer.BadParameter("Unable to resolve current HEAD commit")
    return commit_sha


if __name__ == "__main__":
    app()
