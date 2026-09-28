---
name: au2-merch
description: >-
  Run the AU2 merch factory line end to end — take a piece of art from print-ready
  file to a live product card on appearance-unlimited.com/merch. Use when asked to
  add merch, create a product, refresh the merch page, publish a drop, or wire a
  Printify item into the AU2 site. Covers drafting on Printify, reviewing mockups,
  pulling listing data (colors, sizes, copy, Etsy URL) into the catalog, rebuilding
  the pages, and deploying.
---

# AU2 merch factory line

One design in, one live product card out. Every stage is a deterministic script —
this skill sequences them and holds the gates. **No LLM or image-model API calls
belong anywhere in this pipeline**; see `/app/CLAUDE.md` constraint 1.

## The line

```
art file
  │  1. draft      tee-empire/scripts/publish_merch_draft.py     → Printify draft (visible:false)
  │  2. REVIEW     human looks at data/mockups/<slug>/            ← GATE
  │  3. publish    Printify dashboard, by a human                 ← GATE  → Etsy listing
  │  4. catalog    add entry to assets/data/products.json
  │  5. fetch      scripts/fetch-printify.py                      → colors, sizes, copy, images, etsy_url
  │  6. build      scripts/build-merch.py                         → merch.html + detail page
  │  7. verify     serve locally, read the page
  │  8. deploy     ./deploy.sh --apply    (ON QUASIMODO ONLY)     ← GATE
live card
```

Stages 1–7 are safe and repeatable. **Stages 2, 3 and 8 are human gates** and must
never be automated away — `/app/CLAUDE.md` principle 5.

## Hard facts (verified 2026-09-27, don't re-derive)

| | |
|---|---|
| Printify shop | `27415408` "EarlBiggersDammit", `sales_channel: etsy` — the only shop on the account |
| Credentials | `PRINTIFY_API_KEY` in `/app/tee-empire/.env` (gitignored, mode 600). Never commit it, never echo it. |
| Python | `/app/tee-empire/.venv/bin/python` — this box has no system pip and no Pillow |
| Blueprints | 887 bottle · 478 mug · 635 accent mug · 400 sticker · 12 B+C 3001 tee · 6 Gildan 5000 |
| Deploy host | `clawfirm-droplet` → `/var/www/appearance-unlimited.com`. **Run `deploy.sh` on quasimodo — pop-os has no route.** |
| Not deployed | `scripts/`, `assets/data/`, `deploy.sh` are excluded from the rsync — build tooling stays home |

## Running it

**1. Draft.** Square art on a wrap product (bottle/mug) needs `--scale 0.33`; the
built-in 0.6 wraps two-thirds of the design around the back. See
`/app/tee-empire/CLAUDE.md`.

```bash
cd /app/tee-empire && ./.venv/bin/python scripts/publish_merch_draft.py \
  --brand au2 --product bottle --design data/art/<art>.png \
  --slug <slug> --name "<Title>" --price 28 --scale 0.33
```

Re-scale without creating a duplicate: add `--update <product_id>`.

**2–3. Review, then publish.** Look at every mockup in
`/app/tee-empire/data/mockups/<slug>/`. Publishing to Etsy happens in the Printify
dashboard, by a person. The script never calls `publish_product()`.

**4. Catalog.** Add to `assets/data/products.json` → `products[]`:

```json
{
  "id": "<kebab-id>", "design": "<design-id|null>", "name": "<Display Name>",
  "type": "<Blueprint · sizes>", "category": "drinkware|apparel|stickers-magnets|cards-prints",
  "price": null, "etsy_url": null, "printify_blueprint": 887,
  "printify_product_id": "<printify id>",
  "colors": [], "sizes": [], "images": [], "description": []
}
```

Leave `price`, `etsy_url`, `colors`, `sizes`, `images`, `description` empty — stage 5
fills them from Printify. `design` links to a `designs[]` entry for the tagline;
`null` is fine.

**5. Fetch.** Read-only against Printify; never creates or publishes.

```bash
cd /app/appearance-unlimited-site
export PRINTIFY_API_KEY=$(grep '^PRINTIFY_API_KEY=' /app/tee-empire/.env | cut -d= -f2-)
export PRINTIFY_SHOP_ID=27415408
/app/tee-empire/.venv/bin/python scripts/fetch-printify.py --only <kebab-id> --max-images 6
```

Pulls enabled-variant colors with exact hex, enabled sizes, the listing copy, the
price (and per-size range), responsive mockups, and — if the product has been
published — adopts `external.handle` as `etsy_url`. That last one is what flips
the card from "Drops Soon" to a live buy button.

**6–7. Build and verify.**

```bash
/app/tee-empire/.venv/bin/python scripts/build-merch.py
python3 -m http.server 8811 --directory /app/appearance-unlimited-site
```

`build-merch.py` regenerates `merch.html` between its `merch:*` markers plus one
detail page per product. Products no longer in the catalog are **stubbed to a
redirect, never deleted**.

**8. Deploy.** Dry run first — it is read-only by default.

```bash
./deploy.sh            # shows exactly what would change
./deploy.sh --apply    # publishes; ON QUASIMODO
```

## Duplicating the line for another brand

The scripts are brand-agnostic; only the catalog and the art differ.

1. `brands/<slug>/brand.yaml` in tee-empire — set `printify_shop_id`.
2. A site with `assets/data/products.json`, `scripts/fetch-printify.py`,
   `scripts/build-merch.py` and the `merch:*` markers in its merch page.
3. Point stage 1 at `--brand <slug>` and stage 5 at that site.

Nothing in `fetch-printify.py` or `build-merch.py` is AU2-specific — they key off
the catalog, not the brand.

## Gotchas that have already bitten

- **Wrap-product scale.** Printify's `scale` is a fraction of print-area *width*,
  which on drinkware is the whole circumference. Square art wants ~0.33.
- **Mockups are `.jpg`, not `.png`.** A `data/mockups/*.png` ignore rule silently
  fails to cover them. tee-empire's `.gitignore` now ignores the directory.
- **`visible: false` ≠ unpublished.** A product can be hidden in Printify and still
  have a live Etsy listing — check `external.handle`, not `visible`.
- **Detail pages for removed products become redirect stubs.** If a page 404s after
  a catalog edit, that is the stub, not a build failure.
- **`deploy.sh` never uses `--delete`.** The docroot is shared nginx territory.

## What this line does NOT do

Checkout is **Etsy's**. The site links out; Etsy takes payment, computes shipping
and tax, and Printify auto-fulfills against the connected shop. There is no cart,
no payment handling and no order API call anywhere in this repo — the site is
static nginx with no backend. Moving checkout onto appearance-unlimited.com is a
separate build with real money at stake; see `docs/checkout-options.md`.
