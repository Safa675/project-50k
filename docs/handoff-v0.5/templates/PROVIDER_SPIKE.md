# Provider spike report
Provider / endpoint / SDK / exact version:
Date and deployment region:
Entitlement document and allowed use (storage/display/non-display/derived alerts/redistribution):
Credential source (never paste key):
Request shape and rate policy:
Sanitized sample response path + hash:
Actual observed fields, units, publication/availability times:
History depth and missing values:
Venue/chain coverage:
Corporate-action / NAV / finality behavior:
Failure, stale-response and retry tests:
Results: DOCUMENTED / CODE_INSPECTED / LIVE_TESTED / RIGHTS_APPROVED (independent flags)
Detector capabilities enabled:
Detector capabilities explicitly disabled:
Open issues and owner:


## TEFAS-specific admission cases
- Pin immutable source/transport version; certificate verification enabled; bad certificates surface an error.
- Preserve raw allocation date; malformed/missing date is quarantined, never replaced by today.
- Historical AUM/investor placeholders remain missing; no flow/investor alarm without actual dated history.
- Confirm access, storage, analytics, display and model-processing rights independently.
