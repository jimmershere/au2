# Selling direct on appearance-unlimited.com — the checkout decision

Written 2026-09-27. The merch pages are live and Printify-driven; what follows is
the one piece that is **not** built, and why it needs a decision before it is.

## Where things stand

The line runs end to end today — art → Printify draft → human review → Etsy
listing → catalog → live product card. What "end to end order processing" means
right now is: **the customer clicks Buy on Etsy and Etsy does the rest.**

That is not a placeholder. Etsy takes the payment, computes shipping and sales
tax in every US jurisdiction, handles refunds and chargebacks, and Printify
auto-fulfils against the connected shop. The AU2 bottle
(`etsy.com/listing/4584376010`) works this way now.

## What moving checkout onto the site actually requires

The site is **static HTML served by nginx** on the droplet. It has no backend, no
database and no server-side code. A cart is not a front-end feature — you cannot
take money from a static page. Direct checkout needs, at minimum:

| Piece | Why | Who can do it |
|---|---|---|
| Payment capture | Charge the customer | Stripe Checkout (hosted page — card data never touches the droplet) |
| A backend service | Create the Stripe session, receive the webhook | New: a small service behind nginx |
| Order submission | Send the paid order to Printify | `POST /v1/shops/27415408/orders.json` — **verified working, token has `orders.write`** |
| Shipping cost | Quote before payment | `GET /v1/catalog/blueprints/{bp}/print_providers/{pp}/shipping.json` (flat first-item / additional-item by region) |
| Sales tax | Legally required; Michigan + nexus rules | Stripe Tax, or an accountant's answer |
| Refunds / chargebacks | Someone must own the dispute | You, instead of Etsy |

The technically interesting half is the easy half. Printify fulfilment is a
solved API call. **Tax, refunds and chargebacks are the real cost of leaving
Etsy** — Etsy's ~9% is partly rent on exactly that.

## The three options

**A. Stay on Etsy (what works today).**
Zero new infrastructure. Etsy fee ≈ 6.5% transaction + ~3% payment + $0.20
listing. Buyers arrive with an account and buyer protection. The AU2 site is a
catalogue that sends traffic to the listing.
*Cost: ~9% and no customer relationship. Benefit: nothing to build, nothing to
maintain, no liability.*

**B. Stripe Checkout + a small order service.**
Own the customer, the email list and the margin. Stripe ≈ 2.9% + $0.30 — roughly
**6 points better than Etsy**, about $1.70 per $28 bottle. The build is a
backend service, a webhook handler, a Printify order call, shipping quotes, tax
configuration, and an order/refund runbook. This breaks the current fleet rule
*"no auth, no multi-user schemas, no deployment scaffolding until it works on
localhost"* — not fatally, but deliberately.
*Cost: a real service to run and secure, plus tax and dispute liability.
Benefit: ~6 points of margin and the customer.*

**C. Hosted cart drop-in (Snipcart, Shopify Buy Button, Ecwid).**
JavaScript cart on the static page; the vendor handles payment and often tax.
Roughly 2% platform + payment fees, or a flat monthly. No backend to write, but
Printify fulfilment is then either manual or needs a webhook shim anyway.
*Cost: a monthly fee and a third-party dependency in the buying path.
Benefit: most of B's ownership for a fraction of the build.*

## Recommendation

**Stay on A until the merch line has sales worth optimising, then go to B.**

At current volume the 6-point saving is small and the liability is not. The
Etsy path is live, tested and costs nothing to keep. Revisit the moment merch
revenue is large enough that 6% of it exceeds what the service costs to build and
run — and when that happens, B rather than C, because the Printify order call is
already authorised and working.

What makes this cheap to defer: **the catalog schema does not change.** Direct
checkout replaces one field's behaviour (`etsy_url` → a buy handler). Everything
upstream — drafting, mockups, colors, sizes, copy, page generation — is identical
either way. Nothing built so far is wasted by choosing later.

## Decision

| # | Answer |
|---|---|
| ~~AU-9~~ | **DECIDED 2026-09-27 — option A, stay on Etsy.** jimmer's call. Checkout remains the Etsy listing; the site is the catalogue. Revisit when merch revenue makes ~6 points worth a backend, and go to **B** when it does (the Printify order call is already authorised). Do not build a cart, a payment flow or an order service until that is reopened. |

The pre-drop banner was also retired the same day: a "drops soon, call the shop"
note above a working Buy button reads as broken, so `build-merch.py` now shows the
open-shop banner as soon as any product has an `etsy_url`.
