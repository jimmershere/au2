#!/usr/bin/env python3
"""Regenerate the data-driven sections of merch.html from assets/data/products.json.

The catalog is the source of truth; this script rewrites everything between the
merch:* marker comments and validates the catalog while it's at it. No network,
no AI, stdlib only — run it after any catalog edit:

    python3 scripts/build-merch.py

Buy buttons follow etsy_url: a listing URL renders "Buy on Etsy"; null renders a
disabled "Drops Soon" chip. Fill shop.etsy_shop_url to switch the page banner
from "checkout opens soon" to a storefront link.
"""
import json, html, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "merch.html"
CAT = ROOT / "assets" / "data" / "products.json"

CATEGORIES = {
    "apparel": "Apparel",
    "drinkware": "Drinkware",
    "stickers-magnets": "Stickers & Magnets",
    "cards-prints": "Cards & Prints",
}
SIZES = "(max-width: 700px) 46vw, 300px"
DSIZES = "(max-width: 700px) 92vw, 420px"

def picture(design_id, alt, sizes, indent):
    base = f"assets/img/merch/design-{design_id}"
    i = " " * indent
    return (f'{i}<picture>\n'
            f'{i}  <source type="image/webp" srcset="{base}-520w.webp 520w, {base}-1000w.webp 1000w" sizes="{sizes}">\n'
            f'{i}  <img src="{base}-520w.jpg" srcset="{base}-520w.jpg 520w, {base}-1000w.jpg 1000w" sizes="{sizes}"\n'
            f'{i}       width="1000" height="1250" alt="{html.escape(alt, quote=True)}" loading="lazy" decoding="async">\n'
            f'{i}</picture>')

def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr); sys.exit(1)

def main():
    cat = json.loads(CAT.read_text())
    designs = {d["id"]: d for d in cat["designs"]}
    shop = cat["shop"]

    # ---- validate
    for d in designs.values():
        for suffix in ("520w.jpg", "1000w.jpg", "520w.webp", "1000w.webp"):
            f = ROOT / "assets" / "img" / "merch" / f"design-{d['id']}-{suffix}"
            if not f.exists():
                fail(f"missing image {f.relative_to(ROOT)}")
    seen = set()
    for p in cat["products"]:
        if p["id"] in seen: fail(f"duplicate product id {p['id']}")
        seen.add(p["id"])
        if p["design"] not in designs: fail(f"{p['id']}: unknown design {p['design']}")
        if p["category"] not in CATEGORIES: fail(f"{p['id']}: unknown category {p['category']}")
        if not (isinstance(p["price"], (int, float)) and p["price"] > 0): fail(f"{p['id']}: bad price")
        u = p.get("etsy_url")
        if u is not None and not str(u).startswith("https://www.etsy.com/"):
            fail(f"{p['id']}: etsy_url must be null or an https://www.etsy.com/ URL")

    # ---- banner
    if shop.get("etsy_shop_url"):
        banner = (f'        <p class="merch-note">Printed on demand &middot; ships to your door &middot; '
                  f'checkout on <a href="{shop["etsy_shop_url"]}" target="_blank" rel="noopener">our Etsy shop</a>.</p>')
    else:
        tel = shop.get("phone", "")
        banner = (f'        <p class="merch-note">{html.escape(shop["checkout_note_when_closed"])}'
                  + (f' <a href="tel:{tel}">({tel[2:5]}) {tel[5:8]}-{tel[8:]}</a> &middot; <a href="contact.html">Send a message</a>' if tel else ""))
        banner += '</p>'

    # ---- designs section
    dcards = []
    for d in cat["designs"]:
        dcards.append(
            '          <div class="merch-design reveal">\n'
            '            <div class="merch-art">\n'
            + picture(d["id"], f'{d["name"]} — {d["tagline"]}', DSIZES, 14) + '\n'
            '            </div>\n'
            '            <div class="build-meta">\n'
            f'              <div class="build-name">{html.escape(d["name"])}</div>\n'
            f'              <div class="build-sub">{html.escape(d["tagline"])}</div>\n'
            f'              <p class="muted small mt-1">{html.escape(d["blurb"])}</p>\n'
            '            </div>\n'
            '          </div>')
    designs_html = '        <div class="grid grid-3">\n' + "\n".join(dcards) + '\n        </div>'

    # ---- filter chips + product grid
    chips = ['          <button class="chip active" data-filter="all">All</button>']
    for slug, label in CATEGORIES.items():
        chips.append(f'          <button class="chip" data-filter="{slug}">{label}</button>')
    chips_html = '        <div class="filter-chips" role="tablist" aria-label="Product categories">\n' + "\n".join(chips) + '\n        </div>'

    pcards = []
    for p in cat["products"]:
        d = designs[p["design"]]
        alt = f'{d["name"]} {p["type"].split(" ·")[0]}'
        if p.get("etsy_url"):
            buy = f'                <a class="btn btn-red btn-buy" href="{p["etsy_url"]}" target="_blank" rel="noopener">Buy on Etsy</a>'
        else:
            buy = '                <span class="btn btn-ghost btn-buy is-soon" aria-disabled="true">Drops Soon</span>'
        pcards.append(
            f'          <div class="merch-card" data-cat="{p["category"]}">\n'
            '            <div class="merch-art">\n'
            + picture(p["design"], alt, SIZES, 14) + '\n'
            '            </div>\n'
            '            <div class="merch-meta">\n'
            f'              <span class="badge badge-line">{html.escape(p["type"])}</span>\n'
            f'              <div class="merch-name">{html.escape(d["name"])}</div>\n'
            '              <div class="merch-row">\n'
            f'                <span class="price">${p["price"]:g}</span>\n'
            + buy + '\n'
            '              </div>\n'
            '            </div>\n'
            '          </div>')
    products_html = chips_html + '\n        <div class="grid grid-4 merch-grid">\n' + "\n".join(pcards) + '\n        </div>'

    # ---- splice
    text = PAGE.read_text()
    for marker, block in (("banner", banner), ("designs", designs_html), ("products", products_html)):
        start, end = f"<!-- merch:{marker}:start -->", f"<!-- merch:{marker}:end -->"
        if start not in text or end not in text: fail(f"marker {marker} missing in merch.html")
        text = re.sub(re.escape(start) + r".*?" + re.escape(end),
                      start + "\n" + block + "\n        " + end, text, flags=re.S)
    PAGE.write_text(text)
    live = sum(1 for p in cat["products"] if p.get("etsy_url"))
    print(f"merch.html rebuilt: {len(cat['products'])} products ({live} live on Etsy, "
          f"{len(cat['products']) - live} drops-soon), {len(designs)} designs")

if __name__ == "__main__":
    main()
