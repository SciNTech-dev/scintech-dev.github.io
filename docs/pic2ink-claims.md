# Pic2Ink — claims ledger (site pages)

Built from spec 0003 §7.1 (approved by the owner 2026-10-31). Every sentence below a hero on a
`/pic2ink/` page, and every Pic2Ink sentence on hub pages and in `llms.txt`, maps to a row here.
Evidence paths are in the private app repository `di2g/einksend`, branch
`ccr-528f7859-k0giz8` @ `6fb6fe2` (2026-10-31), version 0.1.0 (build 1), unless a row names
another commit. `data_safety.md` = `docs/play/data_safety.md`, which traces each statement of the
policy to code; "policy" = `docs/privacy/index.html` (the source of `/pic2ink/privacy/#policy`).

Status: **Verified** (read in code or a shipped file), **OWNER** (the owner's commitment, stated
in the policy or in spec 0003 §12), **TO-VERIFY** (kept off the pages), **Poetic** (hero only,
not a claim).

## S1 — privacy page, hub privacy card, footer, llms.txt

| claim | status | evidence | scope / notes | on the site |
|---|---|---|---|---|
| Hero: "Your picture goes to your frame, and nowhere else." | Poetic | backed by the next two rows | the feedback screenshot can carry the picture; the cards and policy say so directly below | privacy H1 |
| Pictures are prepared on the phone and sent only to the frame you tap, over NFC | Verified | policy "What stays on the phone" item 1; `data_safety.md` "The only network traffic is a feedback report the user sends"; Firebase is the only network dependency (`android/app/build.gradle:94-98`) | a shared picture is copied to the app's private cache (policy) | privacy lede + glance "Stays on the phone", hub `/privacy/` card, llms.txt |
| Measured bezels and settings stay in the app's own storage | Verified | policy "What stays on the phone" item 3 | — | privacy glance |
| A bezel photo is read in memory and the camera's file is deleted | Verified | `src/lib/photocal/capture.ts:3-18` (`Filesystem.deleteFile` of the camera's `Pictures/JPEG_*`); policy item 2; spec 0001 §8, §9.5 | — | privacy glance |
| Nothing is uploaded unless you send feedback; feedback leaves only on Send | Verified | `src/lib/feedback/store.svelte.ts:154-180` (`sendFeedback`); Send disabled while blank `FeedbackDialog.svelte:28` (lines per `data_safety.md`) | a queued report is retried later (policy "Where reports are stored") | privacy glance "May be sent", hub card, llms.txt |
| No automatic reports: nothing at start-up or on a schedule | Verified | `data_safety.md` "Nothing is sent at start-up, in the background without a report, or on a schedule"; spec 0002 §7.5 (crash/self-test code not ported) | retries of a report the user sent are not automatic reports | privacy glance "Not in the app", llms.txt |
| The screenshot is ticked by default and shows the user's picture if it is on screen | Verified | `src/lib/feedback/store.svelte.ts:31` `ALL_ON = { metadata, logs, screenshot, settings: true }`, `:116` defaults; spec 0002 §22.2; policy "Feedback you choose to send" | unlike Watermark Remover, where a screenshot is sent only if attached | privacy glance "May be sent", llms.txt |
| Picture details, app logs and current settings go with feedback while ticked; all four can be unticked before Send | Verified | same `ALL_ON`; `report.ts:124-137` (fields per box, lines per `data_safety.md`); policy | — | privacy glance "May be sent", "Yours to choose" |
| No account, advertising, usage-analytics or crash-analytics software | Verified | `android/app/build.gradle:94-98` (Firebase BoM: auth, firestore, storage, appcheck-playintegrity only); policy "Advertising and analytics"; anonymous sign-in creates no user-facing account (`FirebaseGate.kt:39`) | stated as a privacy fact, not a selling point (owner rule 2026-09-23 for WR, kept) | privacy glance "Not in the app", llms.txt |
| Reports carry three anonymous identifiers (install id, Android ID, Firebase uid), used only to group reports from one phone | Verified | `data_safety.md` rows "Android ID" (`FeedbackRepository.kt:114`), "Firebase anonymous uid" (`FirebaseGate.kt:39`), "`install_id`" (`store.svelte.ts:81-89`); policy "Identifiers" | none is an advertising identifier (policy) | privacy glance "Not in the app", llms.txt |
| Uninstalling or clearing storage deletes everything kept on the phone | Verified | policy "Removing your data" paragraph 1 | — | privacy glance "Yours to choose" |
| Sent reports are deleted within 30 days of a request; how to ask is in "Removing your data" | OWNER | policy "Removing your data" paragraph 2 (owner's commitment) | the policy names no e-mail address (owner Q3 = no, 2026-10-31); it points to the Play listing's contact, which exists only after launch — see the S1 PR's notes | privacy glance (link to `#delete`), llms.txt |
| Questions and reports go through the app's Send feedback button | Verified | `src/lib/ui/Fab.svelte:12` (`aria-label="Send feedback"`), `src/lib/ui/TopBar.svelte:18` (⋮ menu ends with "Send feedback") | site support channel, as for the other apps | privacy page footer |
| Status: closed test, not yet on Google Play; package `com.scintech.pic2ink`, version 0.1.0 | Verified | spec 0003 §2 (`PLAY_RELEASE.md:7`); no Play link anywhere on the site (AC-5) | the closed test does not exist in Play Console yet (owner brief 2026-10-31) | llms.txt, hub intro line of llms.txt |
| Based on DITHR by redphx (MIT licence) | Verified | `README.md` lines 8-10; policy footer line | — | privacy policy (verbatim), llms.txt |
| The full policy at `#policy` is the policy of `docs/privacy/index.html`, verbatim | Verified | text compared after stripping tags and collapsing whitespace: identical (2026-10-31); headings h2→h3 and the summary box → `.callout` are the only markup changes | parity check from the app repository: `check_play_listing.py --site` (spec 0003 §9.2) | privacy `#policy` |
