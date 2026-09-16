# Gitea Installer — Home Assistant custom integration

Installeer en update **jouw eigen integraties rechtstreeks van je eigen Gitea**,
via de HA-UI — zonder HACS, zonder publieke GitHub-repo, zonder YAML te
bewerken.

- De **doel-integratie** (bv. je Telenet-integratie) kan volledig **privé** op
  je Gitea blijven staan.
- De **Gitea Installer** zelf is een generieke, publieke bootstrap die HACS kan
  installeren (of via het meegeleverde hostscript).
- Werkt op **HA Container**, HAOS en Supervised.

> ⚠️ **Beveiliging:** deze integratie downloadt en installeert **willekeurige
> code** van de URL die je zelf configureert. Deel haar daarom enkel met
> mensen die je vertrouwt, en gebruik per doel een eigen token als de repo
> privé is.

---

## Waarom hosttoegang nodig is om de bootstrap te installeren (FAQ)

Home Assistant **Container** heeft geen bestandseditor en geen
"installeer-uit-URL" in de web-UI. Custom integraties zijn Python-bestanden
die in `/config/custom_components/` moeten staan. Die kunnen er alleen
terechtkomen via:

1. de **host** van de container (de `/config`-map is een bind-mount) — via
   NAS-filemanager, `docker cp` of SSH, óf
2. **HACS** — maar HACS zelf is óók een custom integratie en vereist exact
   dezelfde **eenmalige** bestandstoegang.

Er bestaat dus **geen** weg om een custom integratie puur vanuit de HA-web-UI
te installeren. Deze repo lost dat op met één hostcommando dat de
Gitea Installer plaatst; **daarna** gebeurt alles (toevoegen, bijwerken,
installeren van doel-integraties) in de UI.

---

## Installatie van de Gitea Installer zelf

### Optie A — via het hostscript (eenmalig, geen HACS nodig)

Op de **docker-host** (waar de container draait), in deze map:

```bash
bash install_bootstrap.sh /pad/naar/deze-map
```

- detecteert automatisch de HA-container (of `HA_CONTAINER=<naam> bash
  install_bootstrap.sh`),
- plaatst de integratie in `/config/custom_components/gitea_installer`,
- vraagt of hij de container mag herstarten.

### Optie B — via HACS (publieke repo)

HACS → ⋮ → Custom repositories → voeg `https://github.com/Cagiva-Raptor/ha-gitea-installer`
toe (categorie **Integration**) → Install → herstart HA.

### Optie C — handmatig

Kopieer de map naar `<config>/custom_components/gitea_installer/` en herstart
HA.

---

## Gebruik

1. **Integratie toevoegen**: Instellingen → Apparaten & diensten →
   Integratie toevoegen → **Gitea Installer**.
2. Vul in (in de web-UI, geen YAML):
   - **Gitea-basis-URL** — bv. `http://192.168.4.10:32769`
   - **Eigenaar / gebruiker** — bv. `admin`
   - **Repository** — bv. `ha-telenet`
   - **Branch** — `main`
   - **Access token** — enkel nodig als de repo **privé** is
3. De flow test meteen de verbinding en leest `manifest.json` uit het ZIP.
4. Je krijgt:
   - een **update-entiteit** (`update.gitea_installer_<owner>_<repo>_update`) —
     toont de geïnstalleerde vs. beschikbare versie, met een install-knop,
   - een **knop** (`button.gitea_installer_<owner>_<repo>_force_update`) —
     "Nu bijwerken": forceert een herinstallatie.

De update-entiteit controleert elke **6 uur** op een nieuwe versie (in de
opties-flow bewerkbaar via de configuratie-opties van de integratie).

### Wat er bij een update gebeurt

1. ZIP downloaden van `…/api/v1/repos/<owner>/<repo>/archive/<branch>.zip`.
2. Bestaande installatie → verplaatst naar `<domain>.bak`.
3. Nieuwe versie uitpakken naar `custom_components/<domain>/` (detecteert
   zowel de `custom_components/<domain>/`-layout als `content_in_root`).
4. De config-entry van de doel-integratie **herladen** (geen herstart nodig).
   Is de doel-integratie nog nooit geconfigureerd, dan is eenmalig een
   herstart nodig.

---

## Vereisten aan de doel-repo op Gitea

- De repo moet een geldige HA-integratie bevatten: `manifest.json` met een
  `domain` (en bij voorkeur `version`).
- Enkel **HTTP/HTTPS zonder self-signed certificaat** wordt ondersteund
  (python `urllib` valideert TLS).
- Privé-repo? Maak een **access token** in Gitea
  (Settings → Applications → Generate New Token, scope repository read).

---

## Licentie

MIT License — copyright **Cagiva-Raptor** (2026). Zie `LICENSE`.