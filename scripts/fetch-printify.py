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
import argparse, io, json, os, re, sys, urllib.request
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


def clean_description(raw, max_paras=4):
    """Printify descriptions are HTML. Reduce to plain paragraphs.

    Only the text is kept — the site's own CSS owns presentation, and passing
    marketplace markup straight into the page is how you inherit someone else's
    inline styles. Returns a list of paragraph strings.
    """
    import html as _html
    # <br>, </p>, </li> mark paragraph breaks; bullets keep a leading marker.
    t = re.sub(r"(?i)<\s*li[^>]*>", "\n• ", raw)
    t = re.sub(r"(?i)<\s*(br|/p|/li|/ul|/div)\s*/?>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", "", t)                 # strip remaining tags
    t = _html.unescape(t)
    paras = [re.sub(r"[ \t]+", " ", p).strip() for p in t.split("\n")]
    paras = [p for p in paras if len(p) > 1]
    return paras[:max_paras]

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

        colors, sizes = [], []
        for o in p.get("options", []):
            if o.get("type") == "color":
                for v in o["values"]:
                    if v["id"] in enabled_opt_ids and v.get("colors"):
                        colors.append({"name": v["title"], "hex": v["colors"][0]})
            elif o.get("type") == "size":
                for v in o["values"]:
                    if v["id"] in enabled_opt_ids:
                        sizes.append(v["title"])
        prod["colors"] = colors
        prod["sizes"] = sizes

        # Printify's own listing copy, so the site and the marketplace agree.
        # It ships as HTML; keep the text, drop the tags the page templates
        # don't style, and cap it so a detail page stays readable.
        prod["description"] = clean_description(p.get("description") or "")

        # `external.handle` is the Etsy listing URL Printify created, but its
        # EXISTENCE never meant the listing was buyable: Printify pushes to Etsy
        # as a DRAFT, and a shopper hitting a draft sees "This item is unavailable".
        #
        # `etsy_live` is the authority, and only a human can set it. Activating a
        # listing happens in Etsy's dashboard, and Printify does not learn about
        # it — a product activated on Etsy still reports visible:false here — so
        # Printify's flag is a stale proxy, not a source of truth. Whoever opened
        # the listing and saw it live sets `etsy_live: true` in the catalog.
        #
        # Printify's `visible` is kept as a fallback for products published from
        # the Printify side, and as a negative signal: without human confirmation,
        # a hidden product is assumed to be an Etsy draft and demoted rather than
        # advertised with a dead buy button.
        ext = p.get("external") or {}
        prod["printify_visible"] = bool(p.get("visible"))
        if ext.get("handle"):
            prod["etsy_listing_url"] = ext["handle"]      # recorded either way

        # Printify's handle has now been wrong in BOTH directions:
        #   false negative — visible:false on a listing that is live (the flag exists for this)
        #   false positive — a handle pointing at a DELETED listing. The AU2 bottle
        #     kept reporting 4584376010 long after that listing 404'd, so the site
        #     shipped a buy button onto "Sorry, this item is unavailable".
        # Etsy bot-blocks scripted requests (curl gets the same Cloudflare page for
        # a live listing and a dead one), so this cannot be verified automatically —
        # only a human with a browser can tell them apart. Hence `etsy_live`:
        #   true      -> trust Printify's handle
        #   "<url>"   -> use THIS url instead; Printify's handle is wrong or stale
        #   false     -> known not buyable; show "Drops Soon" whatever Printify says
        #   unset     -> fall back to Printify's `visible`
        confirmed = prod.get("etsy_live")                 # None = never confirmed
        if isinstance(confirmed, str) and confirmed.startswith("http"):
            prod["etsy_url"] = confirmed                  # human-verified, wins outright
        elif confirmed is False:
            prod["etsy_url"] = None
        elif ext.get("handle") and (confirmed or (confirmed is None and p.get("visible"))):
            prod["etsy_url"] = ext["handle"]
        else:
            prod["etsy_url"] = None

        # Per-size pricing: cheapest enabled variant is the headline price, and
        # the spread is recorded so the page can say "from $X".
        if enabled:
            lo = min(v["price"] for v in enabled)
            hi = max(v["price"] for v in enabled)
            if prod.get("price") is None:
                prod["price"] = round(lo / 100)
            prod["price_range"] = [round(lo / 100), round(hi / 100)]

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
        print(f"  {prod['id']}: {len(colors)} colors, {len(sizes)} sizes, "
              f"{len(stems)} mockups, {len(prod['description'])} para "
              f"({p['title'][:44]!r}), ${prod['price']}"
              + (f"  etsy=LIVE{'(confirmed)' if prod.get('etsy_live') else ''} {prod['etsy_url'][:34]}"
                 if prod.get('etsy_url')
                 else ("  etsy=NOT LIVE (etsy_live:false — listing dead or unpublished)"
                       if prod.get('etsy_live') is False
                       else ("  etsy=DRAFT (not confirmed live — activate on Etsy, then set "
                             "etsy_live:true in the catalog)"
                             if prod.get('etsy_listing_url') else "  (no etsy listing)"))))

    CAT.write_text(json.dumps(cat, indent=2) + "\n")
    print(f"{touched} product(s) refreshed -> {CAT.relative_to(ROOT)}")
    if touched:
        print("now run: python3 scripts/build-merch.py")

if __name__ == "__main__":
    main()
