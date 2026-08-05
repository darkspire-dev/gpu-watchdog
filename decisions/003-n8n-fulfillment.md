# Decision 003: n8n fulfillment workflow

**Date:** 2026-08-05

Built "GPU Watchdog - Stripe Fulfillment" in n8n (workflow ID `Y8WNONxudVMZZbsb`, active,
public webhook at `https://n8n.darkspirellc.com/webhook/gpu-watchdog-stripe`).

**Design:** Webhook (raw body mode) → Code node verifies Stripe HMAC signature, filters
to `checkout.session.completed` + `payment_status: paid`, generates the license key →
IF node branches on `shouldFulfill` → Send Email (SMTP) → Discord sale log → Respond.
Non-matching/unpaid events get a fast 200 without side effects (so Stripe doesn't retry
them as failures).

**Why re-fetch nothing from Stripe's API:** initially planned to independently re-fetch
the checkout session from Stripe's REST API for trust, which would have needed the raw
Stripe secret key inside n8n. Signature verification instead only needs the webhook's
own signing secret (`whsec_...`, scoped, low blast radius, obtained directly from
`PostWebhookEndpoints`'s response) — same trust guarantee, no need to hand Rob's full
API key to n8n.

**Real bug found and fixed during live testing:** n8n's Code node sandbox disallows
`require('crypto')` (`Module 'crypto' is disallowed`) — not documented anywhere I
checked beforehand, only surfaced by actually running it. Fixed by writing a
self-contained pure-JS SHA-256/HMAC-SHA256 implementation
(`tools/pure_js_hmac_sha256.js`), verified byte-identical to Node's `crypto` module
against multiple payloads (including a 5KB+ payload) before embedding it into the
workflow. `Buffer` itself is still available in the sandbox (only `require()` of
built-in modules is blocked), so base64/base64url encoding needed no workaround.

**Second bug found and fixed:** the Discord sale-logging node read `$json.amountTotal`
etc., but by that point in the chain the input `$json` was the *Send Email* node's SMTP
response object, not the original data — those fields don't survive through a node that
replaces its item's json. Fixed by referencing the earlier node explicitly:
`$('Build Email Content').item.json.amountTotal`. Also had to add
`authentication: "genericCredentialType", genericAuthType: "httpHeaderAuth"` to the HTTP
Request node's parameters — attaching a credential in the `credentials` field alone
without also setting these parameter flags produced silent 401s.

**Verification method (no real payment needed):** since I create the webhook endpoint
via the Stripe API, I have the real signing secret, so I can construct fully valid,
correctly-HMAC-signed synthetic events locally and POST them straight to the live public
URL — byte-identical in format to what Stripe would actually send. Ran three cases
against the live endpoint: wrong event type (correctly ignored), unpaid session
(correctly ignored), paid session (correctly fulfilled — real license email delivered
via SMTP, confirmed accepted by the relay; real Discord notification posted, confirmed
by reading the channel back; license key independently validated against the Python
daemon's `validate_license()`, confirmed `is_pro: True`).

**Status:** Task #4 complete. Fulfillment is real and tested, not just "looks right on
paper."
