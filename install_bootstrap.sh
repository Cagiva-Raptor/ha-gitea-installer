#!/usr/bin/env bash
# Eenmalige installatie van de Gitea Installer + Config Editor Panel op een
# HA Container, vanaf de DOCKER-HOST (dus NIET in HA zelf; HA Container heeft
# geen add-ons).
#
# Gebruik:   bash install_bootstrap.sh [pad-naar-deze-map]
# optioneel: HA_CONTAINER=<naam> bash install_bootstrap.sh
set -euo pipefail

SRC="${1:-$(pwd)}"
DOMAIN="gitea_installer"
EDITOR_REPO="MataCrate/config-editor-panel"
EDITOR_DOMAIN="config_editor"

if [[ ! -f "$SRC/manifest.json" ]] || ! grep -q '"domain"' "$SRC/manifest.json"; then
  echo "FOUT: '$SRC' lijkt niet de map van de Gitea Installer te zijn (geen manifest.json)." >&2
  exit 1
fi

CONTAINER="${HA_CONTAINER:-}"
if [[ -z "$CONTAINER" ]]; then
  CONTAINER=$(docker ps --format '{{.Names}}' | grep -iE 'homeassistant|home-assistant|hass' | head -1 || true)
fi
if [[ -z "$CONTAINER" ]]; then
  echo "FOUT: kan de HA-container niet vinden. Geef hem door: HA_CONTAINER=<naam> bash install_bootstrap.sh" >&2
  echo "Lopende containers:" >&2
  docker ps --format '{{.Names}}' >&2 || true
  exit 1
fi

echo "Doel-container: $CONTAINER"
echo "Bron-map:       $SRC"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "[1/3] Gitea Installer plaatsen in custom_components/$DOMAIN ..."
docker exec "$CONTAINER" rm -rf "/config/custom_components/$DOMAIN"
docker cp "$SRC" "$CONTAINER:/config/custom_components/$DOMAIN"
docker exec "$CONTAINER" rm -rf \
  "/config/custom_components/$DOMAIN/.git" \
  "/config/custom_components/$DOMAIN/__pycache__" \
  "/config/custom_components/$DOMAIN/install_bootstrap.sh"

echo "[2/3] Config Editor Panel downloaden ($EDITOR_REPO) ..."
HTTP_CODE=$(curl -sSL -o "$TMP/config-editor-panel.zip" -w "%{http_code}" \
  "https://github.com/$EDITOR_REPO/archive/refs/heads/main.zip" || true)
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "FOUT: Config Editor Panel downloaden mislukt (HTTP $HTTP_CODE)." >&2
  exit 1
fi

echo "[3/3] Config Editor Panel plaatsen in custom_components/$EDITOR_DOMAIN ..."
if command -v unzip >/dev/null 2>&1; then
  unzip -q "$TMP/config-editor-panel.zip" -d "$TMP"
elif command -v busybox >/dev/null 2>&1 && busybox --list | grep -qx unzip; then
  busybox unzip -q "$TMP/config-editor-panel.zip" -d "$TMP"
elif command -v python3 >/dev/null 2>&1; then
  python3 -m zipfile -e "$TMP/config-editor-panel.zip" "$TMP"
else
  echo "FOUT: geen 'unzip', 'busybox unzip' of 'python3' om het ZIP uit te pakken." >&2
  exit 1
fi
docker exec "$CONTAINER" rm -rf "/config/custom_components/$EDITOR_DOMAIN"
docker cp "$TMP/config-editor-panel-main/custom_components/$EDITOR_DOMAIN" \
  "$CONTAINER:/config/custom_components/$EDITOR_DOMAIN"

echo
echo "Geïnstalleerd:"
docker exec "$CONTAINER" ls "/config/custom_components/$DOMAIN/"
echo "  + $EDITOR_DOMAIN (Config Editor Panel)"
echo
echo "Volgende stappen:"
echo "  1. Herstart HA (docker restart $CONTAINER), zodat beide integraties geladen worden."
echo "  2. Instellingen → Apparaten & diensten → Integratie toevoegen → 'Gitea Installer'."
echo "  3. Instellingen → Apparaten & diensten → Integratie toevoegen → 'Config Editor Panel'."
echo "     (dan verschijnt 'Configuratie' in de zijbalk om configuration.yaml te bewerken)"
echo
read -r -p "Nu herstarten? [y/N] " -n 1 ANSWER
echo
if [[ "$ANSWER" =~ ^[Yy]$ ]]; then
  docker restart "$CONTAINER"
  echo "Herstart aangevraagd."
else
  echo "Oké — herstart later zelf: docker restart $CONTAINER"
fi