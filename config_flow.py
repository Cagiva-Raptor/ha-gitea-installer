"""Config flow voor de Gitea Installer-integratie."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_BRANCH,
    CONF_GITEA_URL,
    CONF_OWNER,
    CONF_REPO,
    CONF_TOKEN,
    DEFAULT_BRANCH,
    DOMAIN,
)
from .installer import InstallError, fetch_remote_manifest


def _schema(data: dict | None = None) -> vol.Schema:
    data = data or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_GITEA_URL, default=data.get(CONF_GITEA_URL, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.URL, autocomplete="off"
                )
            ),
            vol.Required(
                CONF_OWNER, default=data.get(CONF_OWNER, "")
            ): selector.TextSelector(),
            vol.Required(
                CONF_REPO, default=data.get(CONF_REPO, "")
            ): selector.TextSelector(),
            vol.Required(
                CONF_BRANCH, default=data.get(CONF_BRANCH, DEFAULT_BRANCH)
            ): selector.TextSelector(),
            vol.Optional(
                CONF_TOKEN, default=data.get(CONF_TOKEN, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD, autocomplete="off"
                )
            ),
        }
    )


async def _test_connection(hass, user_input: dict) -> dict | None:
    manifest = await hass.async_add_executor_job(
        fetch_remote_manifest,
        user_input[CONF_GITEA_URL],
        user_input[CONF_OWNER],
        user_input[CONF_REPO],
        user_input.get(CONF_BRANCH, DEFAULT_BRANCH),
        user_input.get(CONF_TOKEN) or None,
    )
    return manifest


class GiteaInstallerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gitea Installer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        errors: dict = {}
        if user_input is not None:
            try:
                manifest = await _test_connection(self.hass, user_input)
            except InstallError:
                errors["base"] = "cannot_connect"
            else:
                if manifest is None:
                    errors["base"] = "invalid_archive"
                else:
                    repo_id = (
                        f"{user_input[CONF_OWNER]}/{user_input[CONF_REPO]}"
                    )
                    await self.async_set_unique_id(repo_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=repo_id, data=user_input
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return GiteaInstallerOptionsFlow(config_entry)


class GiteaInstallerOptionsFlow(config_entries.OptionsFlow):
    """Options flow: bewerk Gitea-URL, repo, branch en token."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict = {}
        if user_input is not None:
            try:
                manifest = await _test_connection(self.hass, user_input)
            except InstallError:
                errors["base"] = "cannot_connect"
            else:
                if manifest is None:
                    errors["base"] = "invalid_archive"
                else:
                    return self.async_create_entry(
                        title="", data=user_input
                    )
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(dict(self._config_entry.data)),
            errors=errors,
        )