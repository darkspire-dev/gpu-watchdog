# Decision 005: Secret leak incident — Stripe webhook signing secret

**Date:** 2026-08-05
**Severity:** Real, but narrow blast radius, caught within ~20 minutes of the leaking
commit and fully remediated same-day.

## What happened

`tools/build_n8n_workflow.py` and `tools/test_webhook.py` had the Stripe webhook
signing secret (`whsec_...`) hardcoded at the top of the file — internal dev/test
tooling used to build and verify the n8n fulfillment workflow, never meant to ship, but
committed and pushed to the **public** GitHub mirror along with everything else.
GitHub's own secret scanning caught it and emailed an alert
(`support@github.com`, "Possible valid secrets detected") ~20 minutes after the commit
went public. Rob relayed it after checking his own inbox.

## Why it mattered

This secret is what n8n's fulfillment workflow trusts to prove a webhook payload really
came from Stripe. Anyone with it could have forged a fake `checkout.session.completed`
event and gotten a free Pro license key issued via email, without paying — a direct
paywall bypass, not just an info leak.

(For contrast: `LICENSE_SECRET` also appears in the public repo, in
`gpu_watchdog/license.py` — that one is *intentional* and documented in
[[decisions/001-why-this-product]] as an accepted tradeoff of offline license
validation. Not the same category of problem.)

## Remediation (in order)

1. Disabled the leaking Stripe webhook endpoint (`we_1U1B3QRW7vLer5V5Fnz8LgEQ`).
2. Created a new one with a fresh secret (`we_1U1BlQRW7vLer5V5OmeDnHcF`).
3. Moved all fulfillment secrets out of source entirely — `tools/*.py` now load from
   `/home/administrator/auth` (`GPUWATCHDOG_WEBHOOK_SECRET` etc.) instead of hardcoding.
4. Redeployed the n8n workflow with the new secret, re-verified the full
   sign→verify→fulfill path still works (`tools/test_webhook.py paid` → real email,
   real Discord log).
5. **Verified the fix, not just assumed it**: replayed a forged request signed with the
   OLD leaked secret against the live endpoint — correctly rejected
   (`"reason":"signature mismatch"`), no email sent to the fake address used in the
   test.
6. Stopped tracking `tools/` going forward (`.gitignore`'d) — it's internal ops
   tooling, never should have been in a public product repo regardless of secrets.
7. Rewrote git history with `git-filter-repo` to purge `tools/` (and the dead secret
   string) from **every** past commit, not just HEAD — verified 0 occurrences left
   anywhere in history before force-pushing. Applied identically to both the GitHub
   mirror and the local working copy (which feeds Gitea) so nothing diverges going
   forward.
8. Marked the GitHub secret-scanning alert resolved (`resolution: revoked`) with a
   comment explaining the fix.

## Lesson

Internal build/ops scripts (workflow generators, one-off test scripts) should never be
committed into the same repo as the public product in the first place — this wouldn't
have happened if `tools/` had lived in a separate, non-public location from the start.
Going forward: anything that touches a live secret gets written to load from
`/home/administrator/auth` from the very first draft, not hardcoded "just for now, I'll
fix it before it's public."
