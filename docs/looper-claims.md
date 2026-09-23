# Website evidence record

Last verified: 2026-08-04

This document is the working source inventory, claims ledger, research record, unresolved-question list, demonstration plan, structured-data plan, and final-review checklist for the product website. “Verified” means supported by the cited primary evidence within the stated scope; it does not mean universal behavior on every Android device or every media file.

## Site map

| URL | Purpose |
|---|---|
| `/` | Product, differentiation, workflow, limitations, trust summary |
| `/how-it-works/` | Candidate search, alignment, seam construction, render model |
| `/examples/` | Current Play screenshots, evidence boundaries, future demo protocol |
| `/compatibility/` | OS, input/output, tested configurations, FAQ |
| `/privacy/` | Operational privacy guide and policy details |
| `/privacy/policy/` | Unchanged previously published privacy-policy text |

Thin Compare, Technical Notes, and Support content is merged into the five main pages rather than padded into separate pages. Recent public release notes appear on Compatibility; older release history remains an unresolved future deliverable.

## Primary-source inventory

| Source | Scope used |
|---|---|
| Public Google Play listing HTML, retrieved 2026-08-04 | Current public screenshots; listing wording; update date/version presentation |
| `fastlane/metadata/android/en-US/*` | Store description and title source |
| `app/build.gradle.kts` | `minSdk=26`, `targetSdk=36`, code version 1.3.6 as of this review (re-verify before citing a version number — the app has since shipped past 1.3.6; none of the site's own pages state a version number, so this is an internal-record staleness note only) |
| `app/src/main/AndroidManifest.xml` | Picker/share intents and declared permissions |
| Merged manifest and `docs/2026-07-30_permissions_audit.md` | Eight Play-surfaced permissions, legacy API-28 storage declaration, and internal signature permission |
| `model/Models.kt` | Blend, audio, search, and synthesis modes |
| `processing/MediaCodecPipeline.kt` | H.264 video, AAC audio, orientation and frame-rate behavior |
| `work/RenderWorker.kt` | Disk cache, MP4 output, foreground WorkManager, cleanup |
| `ui/synthesis/SynthesisScreen.kt` | Shift/zoom controls and user-facing descriptions |
| `ui/settings/SettingsScreen.kt` and golden captures | Reporting controls and result count |
| Hosted privacy policy as of 2026-08-04 | Report categories, Firebase services, identifiers, deletion path |
| `RatingRepository.kt`, Render sharing UI, and Easy-mode flow | Firebase result/rating records submitted when a render is shared |
| `docs/2026-08-01_v135_release_and_ci_handoff.md` | v1.3.5 production promotion and recent physical-device observations |
| `testdata/goldens/*` | Real in-app Settings, Feedback, About, and Hardware Test screens |
| `docs/2026-07-30_pr_media_review.md` | Prior outside-in listing review; treated as dated developer research |

## Claims ledger

| Claim | Status | Evidence | Last verified | Scope / notes |
|---|---|---|---|---|
| Android 8.0+ | Verified | `minSdk=26` | 2026-08-04 | Documented platform minimum, not a performance guarantee |
| Target SDK 36 | Verified | `app/build.gradle.kts` | 2026-08-04 | Reviewed code, not a visitor-facing compatibility promise |
| Media analysis and rendering occur locally | Verified | pipeline/worker source; privacy policy | 2026-08-04 | Does not mean the app has no network paths |
| Source videos are not uploaded for processing | Verified | implementation and privacy policy | 2026-08-04 | User-initiated screenshot attachment may show video content |
| Feedback, crash, Hardware Test, and share/result records use Firebase | Verified | repositories, sharing flows, and policy where it agrees | 2026-08-04 | Anonymous Auth and Firestore; Storage for optional feedback screenshot. Existing policy omits share/result records |
| Crash and Hardware Test reporting can be disabled | Verified | Settings UI/source and policy | 2026-08-04 | Both described as on by default in policy |
| Automatic loop-point search | Verified | EasyModeOrchestrator, CutPointFinder, Play screens | 2026-08-04 | Search ranking is not a guarantee of subjective best result |
| Up to four candidates | Verified | Settings golden and listing docs | 2026-08-04 | User-configured current maximum in Easy mode |
| Appearance and motion ranking modes | Verified | `Metric` enum and search implementation | 2026-08-04 | Website avoids inferring behavior only from labels |
| Hard cut, crossfade, optical-flow warp, warp crossfade, RIFE interpolation | Verified | `BlendMethod` and render dispatch | 2026-08-04 | Availability/performance varies by Hardware Test |
| Seam alignment supports Auto, Shift, Zoom, and Shift + Zoom | Verified | stabilization source and Advanced UI | 2026-08-04 | No arbitrary rotation/perspective claim |
| Camera drift supports Dance and Lock | Verified | Advanced UI and stabilization source | 2026-08-04 | Dance preserves camera movement near the seam; Lock steadies the background across the clip and may crop/vibrate more |
| Tracking supports Auto, Feature, and Optical flow | Verified | Advanced UI and stabilization source | 2026-08-04 | Feature needs texture; optical flow is slower and device-dependent |
| Border handling offers Mid frame, Panorama, Gray, and Crop zoom | Verified | Advanced UI and stabilization source | 2026-08-04 | Different artifact/crop trade-offs |
| Audio mute/crossfade/zero-crossing modes | Verified | `AudioMode`, `AudioProcessor` | 2026-08-04 | Audio is re-encoded when retained |
| Output MP4 with H.264 video and AAC-LC audio | Verified | MediaCodec pipeline | 2026-08-04 | AAC only when audio retained |
| Original quality is preserved | Rejected | Re-encoding implementation | 2026-08-04 | Site explicitly says no lossless claim |
| No watermark | Partly verified | Current Play listing and prior listing audit | 2026-08-04 | No fresh production render test solely for watermark |
| Core features are free and work offline | Verified for current listing/source + owner promise | Play listing; no billing flow in reviewed source; release note "Fully offline — video never leaves your device"; owner 2026-09-23 "we will always have core functionality free and offline" | 2026-09-23 | Copy no longer markets "no ads / subscription / purchase" (owner: don't shame accounts or paid services); network paths exist for reports only |
| Works on all formats/devices | Unverified | No exhaustive matrix exists | 2026-08-04 | Not published |
| HDR preserved | Unverified | No verified contract found | 2026-08-04 | Explicitly shown as unknown |
| Variable frame rate preserved | Unverified | Output uses resolved integer FPS | 2026-08-04 | No preservation claim |
| Maximum duration/file size | Unverified | Runtime safety checks only | 2026-08-04 | No universal limit published |
| Runs in background | Verified | WorkManager foreground service, notification screenshot | 2026-08-04 | Force-stop/reboot recovery not guaranteed |
| Sharing a render submits a technical result record | Verified | `RatingRepository.submitRating`, Render UI, Easy flow | 2026-08-04 | Includes identifiers, device/app details, source metadata, selections/results, timing, and optional rating; video file is not attached |
| No user-created account is required | Verified | Firebase anonymous authentication flow | 2026-08-04 | Firebase creates an anonymous app-account ID for reporting |
| Submitted data is not sold or legally “shared” | Unverified | Current policy does not use those legal terms | 2026-08-04 | Site does not make this claim |

## Hands-on and test record used

| Device | Android | App evidence | What it supports |
|---|---:|---|---|
| Samsung SM-G715W (Galaxy XCover Pro class) | 13 / API 33 | Stored Hardware Test capture and release logs | Physical-device Hardware Test and pipeline execution; Amber tier shown in capture |
| Pixel 10 Pro | Android 16 in release notes | Recent release diagnostics | Physical-device regression discovery; not generalized to all Pixels |
| Pixel 2 API 30 ATD | 30 | Managed-device test configuration | Behavioral automation only; not used as visual truth |

The repository contains extensive corpus and benchmark artifacts. They are research evidence, not automatically current production-app examples, so the website does not present them as current Android output.

## Unresolved questions

1. What exact input containers/codecs are supported across the target device population? Android decoder availability varies and no exhaustive allow-list is published.
2. Is HDR or wide colour preserved, tone-mapped, or flattened on each pipeline tier? No verified public contract was found.
3. How does variable-frame-rate input behave across representative devices? Output uses a resolved integer frame rate; a preservation claim is not justified.
4. What is the maximum tested duration/file size for each device class? No current release-wide matrix was found.
5. What is the server-side retention schedule for submitted Firebase records? The policy specifies a 30-day local screenshot cache, not a fixed server deletion period.
6. Does the feedback-report deletion route also cover crash, Hardware Test, and share/result records? The current policy does not say.
7. A fresh production render test should independently re-check watermark behavior.
8. A complete historical changelog still needs release-by-release source material; the site currently publishes the verified v1.3.5 summary only.
9. **Flagged, not a site issue but adjacent:** live Play Store screenshot assets (`assets/play-07.png`/`play-08.png`, downloaded 2026-08-04, not used on this site) carry the caption "100% on-device. Nothing uploaded." per `docs/2026-07-07_play_listing_research.md`, `docs/2026-07-10_listing_update_package.md`, and `docs/2026-07-09_play_page_excellence_review.md` in the app repo. That conflicts with this site's own privacy disclosures (Feedback, Crash, Hardware Test, and Shared-result records are all uploaded to Firebase). This site does not repeat that claim anywhere and both source images were removed from `assets/` since they were unused — but the Play Store listing itself should be checked and the caption corrected or scoped to "your source and rendered video are never uploaded."

## Screenshot and demonstration plan

Current screenshots are copied from the public Play CDN without retouching. Future loop demos require:

1. Static/organic motion, camera drift/zoom, moving foreground, and failed/difficult footage.
2. Original, untreated repeat, and production-app output.
3. App/device/Android version; input and output media properties; settings; cut frames; measured time.
4. Disclosure of any web transcode, with downloadable originals when licensing permits.
5. Native pause/replay controls, muted default, captions, and no forced playback under `prefers-reduced-motion`.

## Structured data

- Home: `MobileApplication` with verified OS minimum, free offer, category, URL, and Play download URL.
- Compatibility: `FAQPage` only for questions visibly rendered on that page, plus `BreadcrumbList`.
- Interior pages: `BreadcrumbList` matching visible breadcrumbs.
- `VideoObject` is intentionally omitted until real, reproducible demonstrations are published.

## Accessibility and final-review checklist

- Semantic header/nav/main/footer landmarks and one page-level `h1`.
- Skip link, keyboard-native links/details, visible `:focus-visible` outline.
- No custom pointer-only controls; minimum 50px primary action height and 64px FAQ summaries.
- Text alternatives for every screenshot; captions provide scope.
- Status is conveyed by label text as well as colour.
- Responsive layout down to 320px and horizontally scrollable compatibility table.
- `prefers-reduced-motion` disables smooth scrolling and decorative transforms.
- `prefers-contrast: more` increases muted-text and border contrast.
- Unique titles, descriptions, canonicals, Open Graph fields, sitemap, and robots file.
- All internal links checked locally before handoff.
