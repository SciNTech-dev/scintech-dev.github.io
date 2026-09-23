# Watermark Remover — claims ledger (site pages)

Copied from spec 0069 §9 on 2026-09-23 and extended by chunk S3. Every sentence below a hero on
a `/watermark-remover/` page maps to a row here. Evidence paths are in the app repo
`watermark-remover` at `origin/main` @ `ed7db45` (2026-09-23; the spec was written at `b2daec4`),
version 0.2.4 (versionCode 50). Status: **Verified** (read in code or a shipped file),
**OWNER / listing** (the app's own wording, labelled as such on the page), **TO-VERIFY**
(kept off the page), **TO-MEASURE** (S4), **Poetic** (hero only, not a claim).

| claim | status | evidence | scope / notes | on the site |
|---|---|---|---|---|
| Android 8.0+ | Verified | `android/app/build.gradle.kts:182` `minSdk = 26` | platform minimum, not a performance promise | home proof line, compat table, JSON-LD `operatingSystem` |
| Targets Android 16 (API 36) | Verified | `build.gradle.kts:183` | internal fact; not shown | — |
| Photos and results are processed on the device; none is uploaded | Verified | privacy template "On-device photo processing"; manifest comment "The ONLY network use … Firebase report submission" (`AndroidManifest.xml:4`); listing | feedback may carry a screenshot the user attaches | home hero + privacy panel, privacy glance, FAQ "What leaves the phone?" |
| No account, no ads, no analytics / crash-analytics SDK | Verified | `build.gradle.kts:331-336` deps: firebase auth/firestore/storage/appcheck only; no billing/ads/analytics dep (grep 2026-09-23); template "Advertising and analytics" | anonymous Firebase uid, Android ID and an install id exist; the policy names them | home, privacy glance, compat table |
| Free, no subscription, no in-app purchase | Verified for current release | listing "Free, no account, no ads"; no billing dependency | "current release" | FAQ "Is it free?", JSON-LD `offers` price 0 |
| Learns the mark from the photo itself (one photo) | Verified | commit `46b14fd` "require a repeat from one image"; listing | needs a repeating mark | home "Handles", how-it-works |
| Removes repeating / tiled semi-transparent marks | Verified in scope | listing "WHAT IT HANDLES"; 0012 baseline (10 repeating archetypes) | no number quoted until S4 | home, llms.txt |
| Does not remove a single standalone logo; declines | Verified | listing "WHAT IT DOES NOT DO"; spec 0069 §4.3 refusal | S4 shows the refusal | home, how-it-works callout, FAQ |
| Fill under an opaque mark is a reconstruction: MI-GAN on device (standard build), classical fill (lite build) | Verified | `inpainting/InpaintingEngines.kt:57-59` | — | how-it-works step 4, FAQ, compat table |
| Preview what will be removed; paint over missed spots | Verified | screenshots 04, 05 + listing captions | — | home steps, how-it-works |
| Save as JPEG or PNG; Android 10+ in Pictures/WatermarkRemover; share as PNG | Verified | `export/ImageExporter.kt:17-35`; `ui/QuickRemoveScreen.kt:204-207`; `ui/ShareOut.kt:40-46` | JPEG quality not shown | compat table, home step 4 |
| Input: images from the Android picker or shared to the app | Verified | `WorkbenchScreen.kt:276-279` `GetMultipleContents`, `QuickRemoveScreen.kt:92` `GetContent`, `launch("image/*")`; manifest SEND/SEND_MULTIPLE `image/*` | which formats decode (HEIC etc.) is Android's decoder: TO-VERIFY, not stated | compat table |
| No photo-library permission; network used only for reports | Verified | manifest permissions: INTERNET, FOREGROUND_SERVICE(+MEDIA_PROCESSING, DATA_SYNC), POST_NOTIFICATIONS, WAKE_LOCK; template "the app receives access to that selected file" | — | compat table, privacy glance |
| A long removal keeps running with a notification | Verified | manifest `FOREGROUND_SERVICE_MEDIA_PROCESSING` + comment (spec 0015 C2) | durations not quoted | compat table |
| Hardware check picks the engine; results shared by default, switchable | Verified | `AppPreferences.kt:238` + `build.gradle.kts:204-210` `HWCHECK_REPORT_DEFAULT` (ON, owner 2026-09-22); whatsnew v0.2.3; screenshot 07 | default ON since 0.2.3 | compat table, FAQ, privacy glance, beta page |
| Daily self-check on built-in samples, default ON only in closed-test builds, switchable | Verified | whatsnew v0.2.2; `AppPreferences.kt:247-260` `SELFTEST_REPORT_DEFAULT`; template "Daily self-test reports" | — | FAQ, privacy glance, beta page |
| Crash and memory reports on by default, switchable | Verified | `AppPreferences.kt:69` default true; template | — | FAQ, privacy glance |
| Feedback from the corner button or Settings, optional screenshot; no email | Verified | `res/values/strings.xml:55,323-324` ("Send feedback from the button in the corner"); screenshot 08; template "Optional screenshot" | owner decision: the site's only support channel | FAQ, beta, footer, privacy |
| Reports sent while offline wait on the phone | Verified | template "reports sent from the app's offline queue", "unsent reports queued on the device are dropped after 14 days" | 14-day drop stated in the policy only | FAQ "offline" |
| First analysis "about a minute on mid-range phones" | OWNER / listing | listing text, whatsnew v0.2.0; one-device self-test 56.8 s on SM-A125F (0068 §1.1) | page says "the app's own estimate … not a measured average"; replace with §6.5 rows at ≥ 3 devices | FAQ "Why does the first analysis take a while?" |
| Closed test on Play; ≥ 12 testers for 14 days before production | Verified | 0054 rows "Review passed", "closed test → production" | until O7 | FAQ "beta", beta page |
| Opt-in link | Verified | 0054 "Review passed" row: `https://play.google.com/apps/testing/com.watermarkremover.android` | untagged (a `referrer` on it is PREDICTED not to work) | beta step 2 |
| Testers group lets members into the WM test | **TO-VERIFY (owner O3)** | spec 0069 §8 O3: add the Looper testers group to WM Remover's closed track — not yet done | until O3, step 1 → 2 will not grant access; the page does not name the group's display name | beta step 1 |
| Opt-in page: sign in with the group's Google account and become a tester; Play then offers the test build | Platform knowledge | Play closed-testing flow, not measured here | — | beta steps 2–3 |
| Deletion / privacy requests via in-app feedback; Android ID matches earlier reports | **TO-VERIFY (owner approval)** | owner decision 2026-09-23 "no email on the site"; `FeedbackRepository.kt:112` Android ID in every report (docs/privacy/README.md) | replaces the template's `{{CONTACT_EMAIL}}` section (`tools/wmr_privacy.py` NO_EMAIL_CONTACT); the app repo template and Play Data-safety answers should adopt the same wording | privacy `#delete` |
| Whole-frame dB per example vs. true clean | TO-MEASURE | S4 `SITE_EXAMPLES_OK` | never on real photos | examples region (S4) |
| Deterministic engine (re-run reproduces hashes) | TO-VERIFY | S4 `reproducible=` | gate of S4 | — |
| Out-of-memory: the app refuses rather than crashes on large photos | TO-VERIFY | 0024 OOM work; wording not read from code | kept off the page | — |
| Which build (standard or lite) the user has is shown in About | TO-VERIFY | wording not read | kept off the page | — |
| "See the photo, not the stamp", "Many copies give the mark away", "Your photos stay where they are", "Help it see more photos clearly" | Poetic | hero only | §4 voice rule | heroes |
