"""Download- en installatielogica: haalt een integratie van een Gitea-repo.

Gebruikt enkel de Python-standaardbibliotheek (urllib + zipfile), zodat het
zonder curl/unzip werkt in elke HA-installatie (Container, OS, ...).
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import tempfile
import urllib.request
import zipfile

_LOGGER = logging.getLogger(__name__)


class InstallError(Exception):
    """Fout tijdens downloaden/installeren."""


def _request(url: str, token: str | None) -> urllib.request.Request:
    req = urllib.request.Request(
        url, headers={"User-Agent": "HomeAssistant-GiteaInstaller"}
    )
    if token:
        req.add_header("Authorization", f"token {token}")
    return req


def _archive_url(base_url: str, owner: str, repo: str, branch: str) -> str:
    return (
        f"{base_url.rstrip('/')}/api/v1/repos/{owner}/{repo}/archive/{branch}.zip"
    )


def _download_zip(
    base_url: str, owner: str, repo: str, branch: str, token: str | None
) -> bytes:
    url = _archive_url(base_url, owner, repo, branch)
    try:
        with urllib.request.urlopen(_request(url, token), timeout=30) as resp:
            return resp.read()
    except Exception as err:  # noqa: BLE001 - uiteenlopende netwerkfouten
        raise InstallError(f"Downloaden mislukt van {url}: {err}") from err


def _find_manifest(zfile: zipfile.ZipFile) -> str | None:
    for name in zfile.namelist():
        if name.split("/")[-1] == "manifest.json":
            return name
    return None


def _analyse_zip(
    zfile: zipfile.ZipFile,
) -> tuple[str | None, str | None]:
    """Detecteer de repolayout.

    "standard" -> repo-root bevat custom_components/<domain>/manifest.json
    "root"     -> de repo-root IS de integratie (HACS content_in_root)
    """
    names = zfile.namelist()
    for name in names:
        parts = name.split("/")
        if (
            len(parts) >= 4
            and parts[1] == "custom_components"
            and parts[-1] == "manifest.json"
        ):
            return "standard", parts[2]
    for name in names:
        parts = name.split("/")
        if len(parts) == 2 and parts[-1] == "manifest.json":
            return "root", None
    return None, None


def _read_json_zip(zfile: zipfile.ZipFile, path: str) -> dict:
    with zfile.open(path) as fh:
        return json.loads(fh.read().decode("utf-8"))


def fetch_remote_manifest(
    base_url: str,
    owner: str,
    repo: str,
    branch: str,
    token: str | None,
) -> dict | None:
    """Haal manifest.json op van de remote repo (zonder te installeren)."""
    data = _download_zip(base_url, owner, repo, branch, token)
    with zipfile.ZipFile(io.BytesIO(data)) as zfile:
        manifest_path = _find_manifest(zfile)
        if manifest_path is None:
            return None
        return _read_json_zip(zfile, manifest_path)


def install_from_gitea(
    base_url: str,
    owner: str,
    repo: str,
    branch: str,
    token: str | None,
    config_dir: str,
) -> tuple[str, dict]:
    """Download de repo en installeer de integratie.

    Geeft (domain, manifest) terug. Bestaande installaties worden eerst naar
    <domain>.bak verplaatst.
    """
    data = _download_zip(base_url, owner, repo, branch, token)
    with zipfile.ZipFile(io.BytesIO(data)) as zfile:
        layout, _domain = _analyse_zip(zfile)
        if layout is None:
            raise InstallError("Geen geldige integratie gevonden in het ZIP-bestand.")
        manifest_path = _find_manifest(zfile)
        if manifest_path is None:
            raise InstallError("Geen manifest.json gevonden in het ZIP-bestand.")
        manifest = _read_json_zip(zfile, manifest_path)
        domain = manifest.get("domain")
        if not domain:
            raise InstallError("manifest.json bevat geen 'domain'.")

        tmp = tempfile.mkdtemp(prefix="gitea_installer_")
        try:
            zfile.extractall(tmp)
            top = os.path.join(tmp, os.listdir(tmp)[0])
            if layout == "standard":
                src = os.path.join(top, "custom_components", domain)
            else:
                src = top
            if not os.path.isfile(os.path.join(src, "manifest.json")):
                raise InstallError(f"manifest.json ontbreekt in {src}")

            dest_parent = os.path.join(config_dir, "custom_components")
            os.makedirs(dest_parent, exist_ok=True)
            dest = os.path.join(dest_parent, domain)
            backup = None
            if os.path.exists(dest):
                backup = f"{dest}.bak"
                shutil.rmtree(backup, ignore_errors=True)
                shutil.move(dest, backup)
            shutil.copytree(src, dest)
            _LOGGER.info(
                "Gitea Installer: %s@%s geïnstalleerd naar %s (oud: %s)",
                domain,
                manifest.get("version"),
                dest,
                backup or "geen",
            )
            return domain, manifest
        finally:
            shutil.rmtree(tmp, ignore_errors=True)