"""Gitea Installer-integratie: installeer/update integraties van een eigen Gitea."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_BRANCH,
    CONF_GITEA_URL,
    CONF_OWNER,
    CONF_REPO,
    CONF_TOKEN,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_BRANCH,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
    PLATFORMS,
)
from .installer import InstallError, fetch_remote_manifest, install_from_gitea

_LOGGER = logging.getLogger(__name__)

_PLATFORMS = [Platform.UPDATE, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stel de Gitea Installer in via een config entry."""
    coordinator = GiteaInstallerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    return True


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Herlaad de entry wanneer de opties (URL/repo/token) veranderen."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Verwijder de entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, _PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


class GiteaInstallerCoordinator(DataUpdateCoordinator):
    """Coördineert remote-versiecheck en installatie."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        hours = int(
            entry.data.get(CONF_UPDATE_INTERVAL_HOURS)
            or DEFAULT_UPDATE_INTERVAL_HOURS
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=hours) if hours > 0 else None,
        )
        self.entry = entry
        self.config = dict(entry.data)
        self.remote_manifest: dict | None = None

    @property
    def base_url(self) -> str:
        return self.config[CONF_GITEA_URL]

    @property
    def owner(self) -> str:
        return self.config[CONF_OWNER]

    @property
    def repo(self) -> str:
        return self.config[CONF_REPO]

    @property
    def branch(self) -> str:
        return self.config.get(CONF_BRANCH, DEFAULT_BRANCH)

    @property
    def token(self) -> str | None:
        return self.config.get(CONF_TOKEN) or None

    async def _async_update_data(self) -> dict | None:
        try:
            self.remote_manifest = await self.hass.async_add_executor_job(
                fetch_remote_manifest,
                self.base_url,
                self.owner,
                self.repo,
                self.branch,
                self.token,
            )
        except InstallError as err:
            raise UpdateFailed(str(err)) from err
        return self.remote_manifest

    async def async_install(self) -> tuple[str, dict]:
        """Download + installeer de doel-integratie en herlaad die daarna."""
        try:
            domain, manifest = await self.hass.async_add_executor_job(
                install_from_gitea,
                self.base_url,
                self.owner,
                self.repo,
                self.branch,
                self.token,
                self.hass.config.config_dir,
            )
        except InstallError:
            _LOGGER.exception("Gitea Installer: installatie mislukt")
            raise
        await self._reload_target(domain)
        await self.async_request_refresh()
        return domain, manifest

    async def _reload_target(self, domain: str) -> None:
        """Herlaad een bestaande config-entry van de doel-integratie."""
        entries = self.hass.config_entries.async_entries(domain)
        if not entries:
            _LOGGER.info(
                "Gitea Installer: %s is nieuw geïnstalleerd — herstart HA "
                "om het te laden.",
                domain,
            )
            return
        # Wis de gecachte Python-modules zodat de nieuwe code effectief geladen wordt.
        for mod in list(sys.modules):
            if mod == f"custom_components.{domain}" or mod.startswith(
                f"custom_components.{domain}."
            ):
                sys.modules.pop(mod, None)
        await asyncio.gather(
            *(
                self.hass.config_entries.async_reload(entry.entry_id)
                for entry in entries
            )
        )
        _LOGGER.info("Gitea Installer: %s opnieuw geladen.", domain)