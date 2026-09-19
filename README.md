# appearance-unlimited.com

Source for the Appearance Unlimited site — Northern Michigan auto body,
detailing & classic restoration (Traverse City, MI). Static HTML/CSS/JS, no
build step, no framework.

| | |
|---|---|
| Live | https://appearance-unlimited.com |
| Hosting | nginx on the droplet, docroot `/var/www/appearance-unlimited.com` |
| Working copy | `/app/AU2` on quasimodo (fleet source of truth) |
| Deploy | `./deploy.sh` on quasimodo — dry-run by default, `--apply` publishes; never uses `--delete` |

## Pages

`index` · `services` · `portfolio` · `process` · `about` · `specials` ·
`contact` · `merch` · two documented build pages (`build-indy-500-truck`,
`build-pace-car`). The four `build-*` stubs left over from the draft era are
`noindex` redirects to the portfolio.

Photography is the shop's own work, pulled from its Facebook page and processed
(resized, EXIF/GPS stripped) by the pipeline in the `expansion` repo
(`photos/site-frames.md` there maps every frame).

## Merch (`merch.html`)

Data-driven from **`assets/data/products.json`** — the catalog is the source of
truth for designs, products, prices and Etsy listing URLs.

```bash
python3 scripts/build-merch.py     # regenerate merch.html after editing the catalog
```

- A product with `"etsy_url": "https://www.etsy.com/listing/…"` renders a
  **Buy on Etsy** button; `null` renders a disabled *Drops Soon* chip.
- `shop.etsy_shop_url` switches the page banner from "checkout opens soon" to a
  storefront link.
- Design art lives in `assets/img/merch/` (JPEG+WebP at 520/1000w, generated
  from the master PNGs — masters are not in this repo).

### Printify integration

Two read/write layers, deliberately separate:

**Pull (read-only, scripted):** `scripts/fetch-printify.py` syncs any catalog
product that has a `printify_product_id` — downloads its rendered mockups into
`assets/img/merch/products/<id>/`, writes its **exact** color options
(name + hex, filtered to enabled variants) into the catalog, and fills a null
price from the cheapest enabled variant. The API key is loaded at runtime and
never written to disk:

```bash
PRINTIFY_API_KEY=$(ssh quasimodo-lan "grep '^PRINTIFY_API_KEY=' /app/cc/empire/.env | cut -d= -f2-") \
    python3 scripts/fetch-printify.py
python3 scripts/build-merch.py
```

Each product gets a detail page (`merch-<id>.html`) with a mockup gallery and
color-sample dots straight from Printify's data.

**Push (gated — human publishes, always):** new Printify products are created
either by hand in the Printify UI (then mapped via `printify_product_id`), or
as drafts via `tee-empire/scripts/publish_merch_draft.py` (`visible: false`).
Pushing a listing live on Etsy stays a human action in the Printify/Etsy UI
(fleet rule 5). Once live, paste listing URLs into `products.json`, rebuild,
deploy.

## Conventions

- Photos: responsive `<picture>` with explicit `width`/`height` (CLS zero);
  frames use `.ph.has-photo`.
- Every claim on the site needs a source; no invented builds, no stock art
  passed off as shop work.
