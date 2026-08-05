# Decision 002: Stripe product/price/payment-link IDs

**Date:** 2026-08-05
**Account:** acct_1T4PXPRW7vLer5V5 ("Darkspire Holding")

- Product: `prod_V1DPbdGVZ7y9Ws` — "GPU Watchdog — Pro License"
- Price: `price_1U1AyTRW7vLer5V5Gaq11qOr` — $39.00 USD, one-time
- Payment Link: `plink_1U1AybRW7vLer5V5kI3QoO1U`
  - URL: https://buy.stripe.com/aFadRb41LcZHdYabJ65gc00
  - After completion: hosted confirmation page, custom message telling the buyer their
    license key will arrive by email within a few minutes.

**Live mode** — this processes real charges. Not distributed anywhere publicly yet;
safe to sit idle until fulfillment (n8n webhook, task #4) and the landing page (task #5)
are wired up, since nobody can find the link before launch (task #6).

**Not yet done:** webhook subscription for `checkout.session.completed` pointing at the
n8n fulfillment workflow — next step.
