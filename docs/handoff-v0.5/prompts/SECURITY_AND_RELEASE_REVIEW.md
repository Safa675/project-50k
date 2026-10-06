# Independent security/release review prompt

Act as a skeptical reviewer of the implemented slice, not its author. Read documents 19, 20 and 25; the contracts; and actual code/tests.

Trace anonymous, user A, user B, admin, worker and model tool access. Test service-role leakage, user-metadata admin escalation, ownership isolation, cookie/CSRF flow, JWT validation, prompt injection/SSRF, source licensing, replay cutoffs, source delays, confidence labeling and email idempotency/consent. Verify remote-action authorizations and competition pre-work ruling.

Separate confirmed vulnerabilities, plausible risks, missing tests and accepted constraints. Report reproducible steps and affected requirement IDs. Do not modify production settings, send test email to unapproved recipients or inspect unrelated private data. Recommend release only for the actually tested declared scope. A package unit-test pass is not a deployment/security sign-off.
