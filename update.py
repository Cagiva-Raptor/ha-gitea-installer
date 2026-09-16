"""Update platform: toont beschikbare versie van de remote repo."""

from __future__ import annotations

import json
import logging
import os

from homeassistant.components.update import UpdateEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Gitea Installer update entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GiteaInstallerUpdateEntity(coordinator)])


class GiteaInstallerUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Update-entiteit: laat zien of er een nieuwe versie is + installeren."""

    _attr_has_entity_name = True

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.owner}_{coordinator.repo}_update"
        )
        self._attr_name = "Update"

    @property
    def _local_manifest(self) -> dict | None:
        remote = self.coordinator.remote_manifest
        if not remote:
            return None
        domain = remote.get("domain")
        if not domain:
            return None
        path = os.path.join(
            self.hass.config.config_dir,
            "custom_components",
            domain,
            "manifest.json",
        )
        if not os.path.isfile(path):
            return None
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    @property
    def installed_version(self) -> str | None:
        manifest = self._local_manifest
        return manifest.get("version") if manifest else None

    @property
    def latest_version(self) -> str | None:
        remote = self.coordinator.remote_manifest
        return remote.get("version") if remote else None

    @property
    def release_summary(self) -> str | None:
        remote = self.coordinator.remote_manifest
        return remote.get("name") if remote else None

    async def async_install(self, version: str | None, backup: bool) -> None:
        """Installeer de nieuwe versie."""
        await self.coordinator.async_install()