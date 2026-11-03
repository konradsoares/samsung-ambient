# Samsung Ambient Gallery v3 — 200 landscape stock photos

This combines the **Samsung Tizen app** and **GitHub Pages** gallery into one repository. The app asks for your GitHub Pages URL, downloads `catalog.json`, and lets you choose a group. The browser version uses the same interface.

## Photo packs automatically included in your published site

At the first GitHub Actions deployment, `scripts/import_stock_photos.py` fetches **200 actual Wikimedia Commons featured photographs** (8 groups × 25), checks landscape orientation and reusable-license metadata, crops to **1920×1080** JPEG, and writes `docs/images/<group>/stock-XXX.jpg`, `docs/ATTRIBUTION.md` and `docs/attribution.json`. It then generates `docs/catalog.json`. The published site includes the images; **they are not embedded in the source ZIP** because this development environment cannot reach the image servers. You must let the workflow run to download and publish the photos. Workflow failure means the site was not fully populated; check Actions logs.

### Initial groups

| Group | Photos |
|---|---:|
| Mountains | 25 |
| Forests | 25 |
| Coasts | 25 |
| Water | 25 |
| Islands | 25 |
| Volcanoes | 25 |
| Countryside | 25 |
| Landscapes | 25 |
| **Total** | **200** |

Categories derive from Commons featured pictures collections, with fallback collections for landscape images. Only clearly marked CC0, public domain, CC BY and CC BY-SA files are accepted. Source, creator, precise license and modifications are recorded. **If a run cannot find enough eligible photos, it fails rather than pretending to have 200.** Wikimedia Commons and photography metadata can change; review attributions and any generated photos before wider distribution. Do not use this as a stock-image resale service.

## Setup

1. Create a **public** repository, e.g. `samsung-ambient` and upload all ZIP contents (including `.github/`).
2. Under **Settings → Pages → Build and deployment**, set source to **GitHub Actions** (not Deploy from branch).
3. Under **Actions**, run **Publish Samsung Ambient Gallery (200 licensed photos)** manually, or push to `main`.
4. Wait for the deployment job to succeed; open `https://YOURUSER.github.io/samsung-ambient/` to verify the groups.
5. Open the installed Tizen app on TV and enter that URL (or load the same URL in Samsung Internet). The app loads the groups and lists their photos.
6. On TV choose a group, interval and clock, then select Start screensaver. The app saves your last URL and group.

## Build locally (if you have internet)

```bash
python -m pip install -r requirements.txt
python scripts/import_stock_photos.py
python scripts/generate_catalog.py
python -m http.server 8000 -d docs
```

### Developer Mode and limitations

The **Tizen app still requires Developer Mode to install**; the GitHub Pages link works in Samsung's browser without installation. Neither method replaces Samsung's built-in idle screensaver. The initial photo download runs inside the GitHub Actions runner; images are then served from GitHub Pages and referenced in `catalog.json`. GitHub Pages is public. Respect its storage/bandwidth limits, licensing and content policies.

### Repository layout

```text
.github/workflows/pages.yml  # Builds the photo pack and deploys
scripts/import_stock_photos.py # Wikimedia API importer, filtering, licensing, 16:9 crop
scripts/generate_catalog.py    # Builds image catalog from group folders
docs/index.html                # Browser app
docs/catalog.json              # Generated at build time
docs/images/<group>/           # 200 photos after build
docs/ATTRIBUTION.md            # Generated credits and licenses
tizen-app/index.html           # Native Tizen app (same UI)
tizen-app/config.xml           # Tizen manifest
```

## v3.1: rate-limit and retry fix

Wikimedia Commons can return HTTP 429 from shared GitHub Actions IP ranges. The importer now respects `Retry-After`, applies exponential backoff and request pacing, and does not silently switch to unrelated images when the API is temporarily unavailable.

The workflow processes one group at a time and caches **each successful 25-image group**. If an API limit occurs later, re-run the workflow after the server permits requests again: completed groups are restored instead of re-downloaded. The cache is keyed by group and 1920×1080/25 settings. Source photos are still downloaded into the GitHub Actions runner rather than the repository.

To run locally instead of GitHub Actions:

```bash
python -m pip install -r requirements.txt
for group in mountains forests coasts water islands volcanoes countryside landscapes; do
  python scripts/import_stock_photos.py --group "$group" --per-group 25 || break
done
python scripts/import_stock_photos.py --finalize-credits
python scripts/generate_catalog.py
```

A real authenticated/contactable User-Agent is preferable for production Wikimedia API usage: set `WIKIMEDIA_USER_AGENT` in the Actions environment with a contact URL/email. This importer cannot guarantee Commons will permit all 200 downloads on shared runners.
