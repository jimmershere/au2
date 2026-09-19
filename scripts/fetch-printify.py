#!/usr/bin/env python3
"""Pull mockup images + exact color options from Printify into the merch catalog.

For every product in assets/data/products.json that carries a
``printify_product_id``, this fetches the product from the Printify API and:

  * writes its color options (name + exact hex, filtered to ENABLED variants)
    into the catalog as ``colors``;
  * downloads up to ``--max-images`` mockups to
    assets/img/merch/products/<catalog-id>/imgN{-520w,-1000w}.{jpg,webp}
    and records them in the catalog as ``images`` (path stems);
  * fills a null catalog ``price`` from the cheapest enabled variant.

Credentials: PRINTIFY_API_KEY in the environment (PRINTIFY_SHOP_ID optional —
defaults to the account's first shop). The key is never written to disk; load
it at runtime, e.g.:

    PRINTIFY_API_KEY=$(ssh quasimodo-lan "grep '^PRINTIFY_API_KEY=' /app/cc/empire/.env | cut -d= -f2-") \
        python3 scripts/fetch-printify.py

Then regenerate the pages:  python3 scripts/build-merch.py
Read-only against Printify — it never creates, edits or publishes anything.
"""
import argparse, io, json, os, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "assets" / "data" / "products.json"
OUTBASE = ROOT / "assets" / "img" / "merch" / "products"
API = "https://api.printify.com/v1"

def api(path):
    req = urllib.request.Request(API + path, headers={
        "Authorization": "Bearer " + os.environ["PRINTIFY_API_KEY"],
        "User-Agent": "au2-merch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "au2-merch/1.0", "Accept": "image/*"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-images", type=int, default=8)
    ap.add_argument("--only", help="catalog product id to refresh (default: all mapped)")
    args = ap.parse_args()

    if not os.environ.get("PRINTIFY_API_KEY"):
        sys.exit("PRINTIFY_API_KEY is not in the environment — see the docstring.")
    from PIL import Image  # Pillow required for the resize step

    shop = os.environ.get("PRINTIFY_SHOP_ID") or str(api("/shops.json")[0]["id"])
    cat = json.loads(CAT.read_text())
    touched = 0
    for prod in cat["products"]:
        pid = prod.get("printify_product_id")
        if not pid or (args.only and prod["id"] != args.only):
            continue
        p = api(f"/shops/{shop}/products/{pid}.json")
        enabled = [v for v in p["variants"] if v.get("is_enabled")]
        enabled_opt_ids = {oid for v in enabled for oid in v["options"]}

        colors = []
        for o in p.get("options", []):
            if o.get("type") != "color":
                continue
            for v in o["values"]:
                if v["id"] in enabled_opt_ids and v.get("colors"):
                    colors.append({"name": v["title"], "hex": v["colors"][0]})
        prod["colors"] = colors

        if prod.get("price") is None and enabled:
            prod["price"] = round(min(v["price"] for v in enabled) / 100)

        # mockups: defaults first, then first occurrence of each camera position
        imgs = p.get("images", [])
        picked, seen_pos = [], set()
        for im in imgs:
            if im.get("is_default"):
                picked.append(im); seen_pos.add(im.get("position"))
        for im in imgs:
            if len(picked) >= args.max_images: break
            if im in picked: continue
            pos = im.get("position")
            if pos not in seen_pos:
                picked.append(im); seen_pos.add(pos)
        for im in imgs:                       # then pad with whatever's left
            if len(picked) >= args.max_images: break
            if im not in picked: picked.append(im)

        outdir = OUTBASE / prod["id"]
        outdir.mkdir(parents=True, exist_ok=True)
        stems = []
        for n, im in enumerate(picked, 1):
            raw = fetch_bytes(im["src"])
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            stem = f"products/{prod['id']}/img{n}"
            for w in (1000, 520):
                v = img.copy(); v.thumbnail((w, 10_000), Image.LANCZOS)
                v.save(ROOT / "assets" / "img" / "merch" / f"{stem}-{w}w.jpg",
                       quality=86, optimize=True, progressive=True)
                v.save(ROOT / "assets" / "img" / "merch" / f"{stem}-{w}w.webp",
                       quality=84, method=6)
            stems.append(stem)
        prod["images"] = stems
        touched += 1
        print(f"  {prod['id']}: {len(colors)} colors, {len(stems)} mockups "
              f"({p['title'][:50]!r}), price ${prod['price']}")

    CAT.write_text(json.dumps(cat, indent=2) + "\n")
    print(f"{touched} product(s) refreshed -> {CAT.relative_to(ROOT)}")
    if touched:
        print("now run: python3 scripts/build-merch.py")

if __name__ == "__main__":
    main()
