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

### Wiring real products (gated — human publishes, always)

Printify drafts + rendered mockups come from the Portwright Press tooling in
`tee-empire`:

```bash
cd /app/tee-empire
./.venv/bin/python scripts/publish_merch_draft.py --brand <brand> \
  --product bottle|mug|sticker --design <art.png> --slug au2-<x> \
  --name "…" --price 28
```

That creates a **draft only** (`visible: false`) and downloads mockups; pushing
a listing live on Etsy stays a human action in the Printify/Etsy UI (fleet
rule 5). Requires `PRINTIFY_API_KEY` in `tee-empire/.env` — not present on
pop-os as of 2026-09-19. Once listings are live, paste their URLs into
`products.json`, run the builder, deploy.

## Conventions

- Photos: responsive `<picture>` with explicit `width`/`height` (CLS zero);
  frames use `.ph.has-photo`.
- Every claim on the site needs a source; no invented builds, no stock art
  passed off as shop work.
