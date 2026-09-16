#!/usr/bin/env bash
# Eenmalige installatie van de Gitea Installer-integratie op een HA Container,
# vanaf de DOCKER-HOST (dus NIET in HA zelf; HA Container heeft geen add-ons).
#
# Gebruik:   bash install_bootstrap.sh [pad-naar-deze-map]
# optioneel: HA_CONTAINER=<naam> bash install_bootstrap.sh
set -euo pipefail

SRC="${1:-$(pwd)}"
DOMAIN="gitea_installer"

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

echo "[1/2] Plaatsen in custom_components/$DOMAIN ..."
docker exec "$CONTAINER" rm -rf "/config/custom_components/$DOMAIN"
docker cp "$SRC" "$CONTAINER:/config/custom_components/$DOMAIN"
docker exec "$CONTAINER" rm -rf \
  "/config/custom_components/$DOMAIN/.git" \
  "/config/custom_components/$DOMAIN/__pycache__" \
  "/config/custom_components/$DOMAIN/install_bootstrap.sh"

echo "[2/2] Geïnstalleerd. Controle:"
docker exec "$CONTAINER" ls "/config/custom_components/$DOMAIN/"

echo
echo "Volgende stappen:"
echo "  1. Herstart HA (docker restart $CONTAINER), zodat de integratie geladen wordt."
echo "  2. Instellingen → Apparaten & diensten → Integratie toevoegen → 'Gitea Installer'."
echo "  3. Vul je Gitea-URL, eigenaar, repo en (optioneel) token in."
echo
read -r -p "Nu herstarten? [y/N] " -n 1 ANSWER
echo
if [[ "$ANSWER" =~ ^[Yy]$ ]]; then
  docker restart "$CONTAINER"
  echo "Herstart aangevraagd."
else
  echo "Oké — herstart later zelf: docker restart $CONTAINER"
fi