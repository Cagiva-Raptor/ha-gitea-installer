"""Button platform: dwingt een (her)installatie van de remote repo af."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Gitea Installer button entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GiteaInstallerButton(coordinator)])


class GiteaInstallerButton(CoordinatorEntity, ButtonEntity):
    """Forceert een herinstallatie (ook als de versie gelijk is)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.owner}_{coordinator.repo}_force_update"
        )
        self._attr_name = "Nu bijwerken"
        self._attr_icon = "mdi:download"

    async def async_press(self) -> None:
        """Download + installeer + herlaad."""
        await self.coordinator.async_install()