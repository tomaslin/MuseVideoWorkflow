# Muse media-generation diagnostic — draft for support

This is a local draft. No support request has been sent.

On 2026-10-29, a Muse for Mac production returned
`error_code: integrity_check_failed` and `check_type: media_guard` on several
video-generation requests. No more specific reason, account status, quota
message, or outage code was returned. The requests were for original fictional
adult characters and scenes in a studio wuxia horror trailer. The source
packets are in `projects/the-five-outcasts/prompts/` at the project's recorded
GitHub revision.

Affected shots: s02, s03, s04, s08, s09, s10, s11, s12, s14, s15 and s17.
Shots s02–s04 failed on the first attempt and on one subsequent retry.
Different requests in the same project and session succeeded: s01, s05, s06,
s07, s13 and s16. The successes are saved as actual MP4s and are unreviewed;
the failures have no fabricated clips. S18 was not sent because its group
reference still needs correction.

Please clarify what `integrity_check_failed` / `media_guard` means in these
requests and what supported next steps are available. We have paused the failed
shots and are not attempting to evade the provider's controls. We can provide
specific packet hashes and request timestamps if the support channel asks.
