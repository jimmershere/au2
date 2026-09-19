#!/usr/bin/env python3
"""Regenerate merch.html AND the per-product detail pages from
assets/data/products.json. The catalog is the source of truth; run this after
any catalog edit (or after scripts/fetch-printify.py):

    python3 scripts/build-merch.py

Behavior
  * merch.html: designs section, filter chips, product grid rebuilt between
    the merch:* markers. Each grid card links to its detail page.
  * merch-<product-id>.html: one detail page per product — mockup gallery
    (Printify images when fetched, design art otherwise), exact color dots,
    price, buy state, related items. Pages are written from the template
    below; stale merch-*.html files for products no longer in the catalog
    are reported (never deleted automatically).
  * Buy buttons follow etsy_url: a listing URL renders "Buy on Etsy"; null
    renders a disabled "Drops Soon" chip.

No network, no AI, stdlib only.
"""
import json, html, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "merch.html"
CAT = ROOT / "assets" / "data" / "products.json"
IMG = ROOT / "assets" / "img" / "merch"

CATEGORIES = {
    "apparel": "Apparel",
    "drinkware": "Drinkware",
    "stickers-magnets": "Stickers & Magnets",
    "cards-prints": "Cards & Prints",
}
GRID_SIZES = "(max-width: 700px) 46vw, 300px"
DESIGN_SIZES = "(max-width: 700px) 92vw, 420px"
DETAIL_SIZES = "(max-width: 900px) 92vw, 560px"

def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr); sys.exit(1)

def stem_exists(stem):
    return all((IMG / f"{stem}-{w}w.{ext}").exists()
               for w in (520, 1000) for ext in ("jpg", "webp"))

def picture(stem, alt, sizes, indent, eager=False, cls=""):
    base = f"assets/img/merch/{stem}"
    i = " " * indent
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    c = f' class="{cls}"' if cls else ""
    return (f'{i}<picture{c}>\n'
            f'{i}  <source type="image/webp" srcset="{base}-520w.webp 520w, {base}-1000w.webp 1000w" sizes="{sizes}">\n'
            f'{i}  <img src="{base}-520w.jpg" srcset="{base}-520w.jpg 520w, {base}-1000w.jpg 1000w" sizes="{sizes}"\n'
            f'{i}       alt="{html.escape(alt, quote=True)}" {load}>\n'
            f'{i}</picture>')

def display_name(prod, designs):
    return prod["name"] or designs[prod["design"]]["name"]

def hero_stem(prod):
    return prod["images"][0] if prod["images"] else f"design-{prod['design']}"

def buy_button(prod, big=False):
    size = " btn-lg" if big else ""
    if prod.get("etsy_url"):
        return (f'<a class="btn btn-red btn-buy{size}" href="{prod["etsy_url"]}" '
                f'target="_blank" rel="noopener">Buy on Etsy</a>')
    return f'<span class="btn btn-ghost btn-buy{size} is-soon" aria-disabled="true">Drops Soon</span>'

def color_dots(prod, indent):
    if not prod["colors"]:
        return ""
    i = " " * indent
    dots = "\n".join(
        f'{i}  <span class="dot" style="background:{c["hex"]}" title="{html.escape(c["name"], quote=True)}"></span>'
        for c in prod["colors"])
    return (f'{i}<div class="color-dots" aria-label="Available colors">\n{dots}\n{i}</div>\n'
            f'{i}<p class="muted small">Available in {len(prod["colors"])} colors — '
            f'pick yours at checkout.</p>')

# ---------------------------------------------------------------- detail page
def detail_page(prod, cat, designs, skeleton):
    name = display_name(prod, designs)
    d = designs.get(prod["design"]) if prod["design"] else None
    title = f"{name} {prod['type']} | AU Merch — Appearance Unlimited, Traverse City MI"
    desc = (f"{name} — {prod['type']} from Appearance Unlimited's merch line. "
            "Printed on demand, shipped to your door.")

    # gallery
    stems = prod["images"] or [f"design-{prod['design']}"]
    main = picture(stems[0], f"{name} — {prod['type']}", DETAIL_SIZES, 12, eager=True)
    thumbs = ""
    if len(stems) > 1:
        t = []
        for n, s in enumerate(stems):
            t.append(f'            <button class="thumb{" active" if n == 0 else ""}" '
                     f'data-stem="assets/img/merch/{s}" aria-label="View image {n+1}">'
                     f'<img src="assets/img/merch/{s}-520w.jpg" alt="" loading="lazy"></button>')
        thumbs = '\n          <div class="thumb-row">\n' + "\n".join(t) + '\n          </div>'

    dots = color_dots(prod, 12)
    tagline = html.escape(d["tagline"]) if d else "Official Appearance Unlimited gear."
    price = f'${prod["price"]:g}' if prod["price"] else "—"

    related = [q for q in cat["products"] if q["id"] != prod["id"] and
               (q["design"] == prod["design"] if prod["design"] else q["category"] == prod["category"])][:3]
    rel_cards = []
    for q in related:
        rel_cards.append(
            '          <a class="merch-card" href="merch-' + q["id"] + '.html">\n'
            '            <div class="merch-art">\n'
            + picture(hero_stem(q), display_name(q, designs), GRID_SIZES, 14) + '\n'
            '            </div>\n'
            '            <div class="merch-meta">\n'
            f'              <span class="badge badge-line">{html.escape(q["type"])}</span>\n'
            f'              <div class="merch-name">{html.escape(display_name(q, designs))}</div>\n'
            '            </div>\n'
            '          </a>')
    related_html = ""
    if rel_cards:
        related_html = f"""
    <!-- Related -->
    <section class="section-tight reveal">
      <div class="wrap">
        <p class="kicker">More Like This</p>
        <h2 class="mb-3">Keep <span class="chrome">Shopping</span></h2>
        <div class="grid grid-3">
{chr(10).join(rel_cards)}
        </div>
      </div>
    </section>"""

    main_block = f"""<main>

    <!-- Product -->
    <section class="reveal">
      <div class="wrap">
        <p class="small mb-2"><a href="merch.html">&laquo; All merch</a></p>
        <div class="grid grid-2 product-grid">
          <div class="merch-art product-gallery">
{main}{thumbs}
          </div>
          <div>
            <span class="badge badge-line">{html.escape(prod["type"])}</span>
            <h1 class="mt-1">{html.escape(name)}</h1>
            <p class="lead">{tagline}</p>
            <p class="price price-lg mt-1">{price}</p>
{dots}
            <div class="svc-cta-row">
              {buy_button(prod, big=True)}
              <a class="card-link" href="contact.html">Questions? Talk to the shop &raquo;</a>
            </div>
            <ul class="svc-list mt-2">
              <li>Printed on demand through Printify's US network</li>
              <li>Checkout &amp; buyer protection on Etsy</li>
              <li>Original artwork by the Appearance Unlimited crew</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
{related_html}

  </main>"""

    s = skeleton
    s = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", s, count=1, flags=re.S)
    s = re.sub(r'<meta name="description" content=".*?">',
               f'<meta name="description" content="{html.escape(desc, quote=True)}">', s, count=1, flags=re.S)
    s = re.sub(r"<main>.*?</main>", lambda _: main_block, s, count=1, flags=re.S)
    if len(prod["images"] or []) > 1:
        gallery_js = """
  <script>
    /* Detail-page gallery */
    (function () {
      var pic = document.querySelector(".product-gallery > picture");
      document.querySelectorAll(".thumb-row .thumb").forEach(function (b) {
        b.addEventListener("click", function () {
          var s = b.getAttribute("data-stem");
          pic.querySelector("source").srcset = s + "-520w.webp 520w, " + s + "-1000w.webp 1000w";
          var img = pic.querySelector("img");
          img.srcset = s + "-520w.jpg 520w, " + s + "-1000w.jpg 1000w";
          img.src = s + "-520w.jpg";
          document.querySelectorAll(".thumb-row .thumb").forEach(function (x) { x.classList.remove("active"); });
          b.classList.add("active");
        });
      });
    })();
  </script>
</body>"""
        s = s.replace("</body>", gallery_js, 1)
    return s

# ------------------------------------------------------------------- main
def main():
    cat = json.loads(CAT.read_text())
    designs = {d["id"]: d for d in cat["designs"]}
    shop = cat["shop"]

    # ---- validate
    for d in designs.values():
        if not stem_exists(f"design-{d['id']}"):
            fail(f"missing card images for design {d['id']}")
    seen = set()
    for p in cat["products"]:
        if p["id"] in seen: fail(f"duplicate product id {p['id']}")
        seen.add(p["id"])
        if not re.fullmatch(r"[a-z0-9-]+", p["id"]): fail(f"bad product id {p['id']}")
        if p["design"] is None and not p.get("name"): fail(f"{p['id']}: needs design or name")
        if p["design"] is not None and p["design"] not in designs: fail(f"{p['id']}: unknown design")
        if p["category"] not in CATEGORIES: fail(f"{p['id']}: unknown category {p['category']}")
        if p["price"] is not None and not (isinstance(p["price"], (int, float)) and p["price"] > 0):
            fail(f"{p['id']}: bad price")
        u = p.get("etsy_url")
        if u is not None and not str(u).startswith("https://www.etsy.com/"):
            fail(f"{p['id']}: etsy_url must be null or an https://www.etsy.com/ URL")
        for c in p["colors"]:
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", c["hex"]): fail(f"{p['id']}: bad hex {c['hex']}")
        for s in p["images"]:
            if not stem_exists(s): fail(f"{p['id']}: missing image files for stem {s}")

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
            + picture(f"design-{d['id']}", f'{d["name"]} — {d["tagline"]}', DESIGN_SIZES, 14) + '\n'
            '            </div>\n'
            '            <div class="build-meta">\n'
            f'              <div class="build-name">{html.escape(d["name"])}</div>\n'
            f'              <div class="build-sub">{html.escape(d["tagline"])}</div>\n'
            f'              <p class="muted small mt-1">{html.escape(d["blurb"])}</p>\n'
            '            </div>\n'
            '          </div>')
    designs_html = '        <div class="grid grid-3">\n' + "\n".join(dcards) + '\n        </div>'

    # ---- chips + grid
    chips = ['          <button class="chip active" data-filter="all">All</button>']
    for slug, label in CATEGORIES.items():
        chips.append(f'          <button class="chip" data-filter="{slug}">{label}</button>')
    chips_html = '        <div class="filter-chips" role="tablist" aria-label="Product categories">\n' + "\n".join(chips) + '\n        </div>'

    pcards = []
    for p in cat["products"]:
        name = display_name(p, designs)
        dots = ""
        if p["colors"]:
            shown = p["colors"][:6]
            extra = len(p["colors"]) - len(shown)
            dot_spans = "".join(f'<span class="dot" style="background:{c["hex"]}" title="{html.escape(c["name"], quote=True)}"></span>' for c in shown)
            if extra > 0:
                dot_spans += f'<span class="dot-more">+{extra}</span>'
            dots = f'              <div class="color-dots color-dots-sm">{dot_spans}</div>\n'
        price = f'${p["price"]:g}' if p["price"] else "—"
        pcards.append(
            f'          <div class="merch-card" data-cat="{p["category"]}">\n'
            f'            <a class="merch-art" href="merch-{p["id"]}.html">\n'
            + picture(hero_stem(p), f'{name} {p["type"]}', GRID_SIZES, 14) + '\n'
            '            </a>\n'
            '            <div class="merch-meta">\n'
            f'              <span class="badge badge-line">{html.escape(p["type"])}</span>\n'
            f'              <div class="merch-name"><a href="merch-{p["id"]}.html">{html.escape(name)}</a></div>\n'
            + dots +
            '              <div class="merch-row">\n'
            f'                <span class="price">{price}</span>\n'
            f'                {buy_button(p)}\n'
            '              </div>\n'
            '            </div>\n'
            '          </div>')
    products_html = chips_html + '\n        <div class="grid grid-4 merch-grid">\n' + "\n".join(pcards) + '\n        </div>'

    # ---- splice merch.html
    text = PAGE.read_text()
    for marker, block in (("banner", banner), ("designs", designs_html), ("products", products_html)):
        start, end = f"<!-- merch:{marker}:start -->", f"<!-- merch:{marker}:end -->"
        if start not in text or end not in text: fail(f"marker {marker} missing in merch.html")
        text = re.sub(re.escape(start) + r".*?" + re.escape(end),
                      lambda _m, b=block, s=start, e=end: s + "\n" + b + "\n        " + e,
                      text, flags=re.S)
    PAGE.write_text(text)

    # ---- detail pages
    for p in cat["products"]:
        (ROOT / f"merch-{p['id']}.html").write_text(detail_page(p, cat, designs, text))
    stale = [f.name for f in ROOT.glob("merch-*.html")
             if f.name != "merch.html" and f.name[len("merch-"):-len(".html")] not in seen]
    if stale:
        print(f"note: stale detail pages not in catalog (delete by hand): {stale}")

    live = sum(1 for p in cat["products"] if p.get("etsy_url"))
    with_mock = sum(1 for p in cat["products"] if p["images"])
    print(f"merch.html + {len(cat['products'])} detail pages rebuilt "
          f"({live} live on Etsy, {with_mock} with Printify mockups, {len(designs)} designs)")

if __name__ == "__main__":
    main()
