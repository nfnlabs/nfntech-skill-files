---
name: release-readiness
description: The pre-release verification pass for Flutter on Android and iOS — signing identities and SHA fingerprints in Firebase, APNs keys and push entitlements, Crashlytics symbols and dSYMs, per-flavor console configuration, and store submission gates. Read before shipping any build to a store.
---

# Release Readiness

> Console configuration is the half of a release source control cannot verify. Check the consoles against the artifact that will actually ship, and record who looked.

Build commands and flavor wiring → `environments.md`. Crash-reporting code → `foundation.md`. Diagnosing a symbolicated report → `diagnostics.md`.

## 1 · Gather the map first

A release check is worthless without knowing which console each build talks to. Write this
down before touching anything:

| Item | Where to read it | Why it matters |
|---|---|---|
| Flavor → Firebase project | `flavorizr.yaml`, `config/firebase/`, `firebase_options_<flavor>.dart` | every flavor is a separate project with its own keys and fingerprints |
| Flavor → application ID / bundle ID | `flavorizr.yaml`, Gradle, Xcode build settings | one Firebase app per ID; a shared ID silently merges environments |
| Signing setup | `android/signing.properties`, `key.properties`, Xcode signing, fastlane `match` | which identities exist |
| Push provider | `firebase_messaging` in `pubspec.yaml`, APNs config in the console | whether APNs credentials are in scope |
| Obfuscation | the release build script's flags | whether symbol upload is mandatory |

If a flavor's Firebase project is ambiguous, stop and resolve that first. Every check below is
per-flavor, and "we added it" without naming the project is not an answer.

## 2 · Android signing identities — the most common release defect

There are **three distinct signing identities** in an Android release, and confusing them is
the root cause of the "works locally, broken in the store" class of bug:

| Identity | Who holds it | Present in |
|---|---|---|
| Debug keystore | each developer's machine (`~/.android/debug.keystore`) | local debug builds only |
| Upload keystore | your team / CI secret | what you upload to Play |
| Play App Signing key | Google, generated on enrolment | **what end users actually run** |

Play App Signing means Google strips your upload signature and re-signs the artifact with its
own key. **The certificate fingerprint on the device is therefore never your upload
keystore's.** Any Google service that authenticates the calling app by signature — phone
auth and SMS-based OTP, Google Sign-In, Dynamic Links, App Links, Safety Net / Play Integrity
— will work in a locally-signed build and fail in the store build if only the upload
fingerprint is registered.

So every Firebase Android app needs, at minimum:

- **SHA-1 and SHA-256 of the upload keystore** — so internal-test and CI-signed builds work
- **SHA-1 and SHA-256 of the Play App Signing key** — so the live build works
- **SHA-1 of each developer's debug keystore**, if debug builds must authenticate

```sh
# upload keystore (and any local keystore)
keytool -list -v -keystore upload-keystore.jks -alias upload | grep -A2 "SHA1\|SHA256"

# every variant's signing config at once — fastest way to spot a missing one
cd android && ./gradlew signingReport

# debug keystore
keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android
```

The **Play App Signing** fingerprints are not derivable locally — read them from
Play Console → your app → *Test and release* → *App integrity* → *App signing*. That page
shows both the app signing key certificate and the upload key certificate; both belong in
Firebase.

**After adding a fingerprint, re-download `google-services.json`** and commit it for that
flavor. Adding the SHA in the console without refreshing the config file leaves the client
unaware of it, and the symptom is identical to not having added it at all.

**Digital Asset Links** is a separate registration with its own fingerprint requirement. App
Links verification and SMS Retriever behaviour depend on `assetlinks.json` served from the
domain listing the **Play App Signing** SHA-256 — not the upload key's. Verify the hosted file
directly rather than trusting the console's cached status:

```sh
curl -s https://example.com/.well-known/assetlinks.json | jq .
# then confirm Android accepts it
adb shell pm get-app-links com.example.app
```

## 3 · iOS push credentials

Prefer an **APNs authentication key** (`.p8`) over legacy push certificates: one key works for
every app under the team, covers development and production, and does not expire — where
certificates expire annually and silently break push on a date nobody diarised.

Upload to Firebase → Project settings → Cloud Messaging → the iOS app, with all three parts:
the `.p8` file, its **Key ID**, and your **Team ID**. A key uploaded to the wrong flavor's
project produces push that works in one environment and fails in another with no client-side
error.

Then confirm the app side, because a valid key with a misconfigured target still fails:

| Requirement | Where | Failure symptom if missing |
|---|---|---|
| Push Notifications capability | Xcode → Signing & Capabilities | no APNs token issued at all |
| Background Modes → Remote notifications | same | silent/data pushes dropped |
| `aps-environment` entitlement | generated entitlements file | token issued against the wrong APNs environment |
| Provisioning profile includes push | Apple Developer / `match` | constant registration fails on device |
| Bundle ID matches the Firebase iOS app | Xcode ↔ Firebase | constants register to a project that never sends |

The entitlement is the one that produces the most confusing report: `development` works on a
debug device, then TestFlight and App Store builds receive nothing, because a
production-signed app must present the `production` APNs environment. Release builds should
carry it automatically — verify rather than assume:

```sh
codesign -d --entitlements :- Runner.app | grep aps-environment
```

`.p8` files are download-once. Store it in the team secret manager the day it is created, or
the next person regenerates the key and invalidates the one in production.

## 4 · Crash symbols

An obfuscated release without uploaded symbols produces crash reports nobody can read, and
you cannot retrofit them — the mapping only exists at build time.

**Android.** Obfuscated Dart needs `--split-debug-info`, and the resulting symbol directory
must be archived per release and uploaded to Crashlytics. If the app has native code or R8 is
enabled, the NDK symbols and the R8 mapping file are separate uploads.

```sh
flutter build appbundle --release --flavor prod --dart-define=mode=PROD \
  --obfuscate --split-debug-info=build/symbols/prod-1.2.3
```

**iOS.** Upload dSYMs for every release. When Apple re-signs or thins the binary the UUIDs
change, so the authoritative dSYMs are the ones downloaded from App Store Connect
(*Activity* → build → *Download dSYM*), not necessarily the local archive — which is why
crash reports for a TestFlight build can arrive unsymbolicated even though the local upload
succeeded.

```sh
find ~/Library/Developer/Xcode/Archives -name "*.dSYM" | tail
# Crashlytics upload script bundled with the SDK
"${PODS_ROOT}/FirebaseCrashlytics/upload-symbols" -gsp ios/Runner/GoogleService-Info.plist \
  -p ios <path-to-dSYMs>
```

Verify by forcing one crash per release channel and confirming the report arrives **and is
symbolicated**. An untested crash pipeline is usually a broken one, and you find out during
the incident you needed it for.

## 5 · Per-flavor configuration matrix

Fill this in per release rather than from memory. The point of the grid is that a gap is
visible, where prose lets one cell hide.

| Check | dev | qa | uat | prod |
|---|---|---|---|---|
| Firebase project named and correct | | | | |
| `google-services.json` current (post-SHA refresh) | | | | |
| `GoogleService-Info.plist` current | | | | |
| Upload-key SHA-1 + SHA-256 registered | | | | |
| Play App Signing SHA-1 + SHA-256 registered | | | | |
| `assetlinks.json` served, listing the signing SHA-256 | | | | |
| APNs `.p8` uploaded with Key ID + Team ID | | | | |
| Push entitlement matches the build type | | | | |
| Auth providers enabled; test numbers removed for prod | | | | |
| Remote Config / feature flag defaults sane | | | | |
| Crash collection on (off for dev) | | | | |
| API base URL points at the intended backend | | | | |
| Symbols/dSYMs uploaded and archived | | | | |

Two rules make the grid trustworthy. A cell is ticked when **someone opened the console and
looked**, not when someone believes it was done earlier. And any flavor sharing a Firebase
project or application ID with another is a finding in itself — record it.

## 6 · Submission gates

Before uploading, in this order:

1. Version name and build number **strictly greater** than anything on that track, per
   platform. Play and App Store Connect track them independently.
2. Flavor and environment define agree — a prod-signed app talking to QA compiles cleanly.
3. Codegen committed; `flutter analyze`, `dart run custom_lint` and tests clean.
4. `git diff | grep -iE "key|token|secret|password"` clean; no keystore, `.p8` or
   `signing.properties` in the tree.
5. Release notes, store listing, screenshots, privacy declarations and data-safety answers
   current for this version.
6. Permission usage strings present and accurate for every permission the binary requests —
   a missing iOS usage description is a review rejection, not a runtime bug.
7. Deep links and universal links resolve to the shipped build.
8. Minimum OS versions unchanged, or the change is deliberate and communicated.

## 7 · Failure modes

| Symptom | Root cause | Fix |
|---|---|---|
| OTP / phone auth works locally, fails in the store build | only the upload-key SHA registered; the live build is signed by Google's key | add Play App Signing SHA-1 **and** SHA-256, re-download `google-services.json`, ship |
| Google Sign-In fails for store users only | same signature mismatch | as above |
| SHA added but nothing changed | config file not refreshed after the console edit | re-download and commit `google-services.json` |
| App Links open the browser instead of the app | `assetlinks.json` missing, unreachable, or listing the wrong fingerprint | serve it with the signing SHA-256; verify with `pm get-app-links` |
| Push works on debug device, silent in TestFlight/App Store | `aps-environment` still `development` | confirm the release entitlement; check the provisioning profile includes push |
| No APNs token at all | Push Notifications capability absent | enable the capability; regenerate the profile |
| Push works on one flavor only | `.p8` uploaded to a single Firebase project | upload per project, with Key ID and Team ID |
| Push stopped working on a specific date | legacy certificate expired | migrate to a `.p8` auth key |
| Crash reports show hex addresses | symbols or dSYMs never uploaded | upload; for iOS use the App Store Connect dSYMs |
| TestFlight crashes unsymbolicated, local build fine | Apple re-signed and the UUIDs changed | download dSYMs from App Store Connect and upload those |
| Store upload rejected on version code | build number not above the track's highest | bump; remember the two stores count separately |
| Prod build hitting the QA backend | flavor and environment define disagreed | make the build script the only way to build |
| Test phone numbers accept any OTP in production | debug auth settings left enabled | remove them from the prod project before release |

## 8 · After the build is live

The store artifact is not the artifact you tested. Install from the actual track — internal
testing, TestFlight, or production — and confirm on the real thing:

- Sign-in, including OTP or social flows that depend on the signing certificate
- One push notification received in the background and one in the foreground
- The about or debug surface reports the expected environment and backend
- A forced crash arrives in the correct Firebase project, symbolicated
- A deep link opens the installed app rather than a browser

This last pass exists because signature-dependent and entitlement-dependent features are
precisely the ones that cannot fail until the store has re-signed and distributed the build.
Testing a locally-signed build proves the code works; it proves nothing about the release.

## 9 · Done when

- Every cell in §5's grid is ticked against a console someone actually opened
- Both upload and Play App Signing fingerprints registered, config files refreshed and committed
- APNs key present per project, entitlement matching the build type
- Symbols and dSYMs uploaded, archived alongside the release tag
- §6's gates all pass
- §8's post-release pass completed on the store artifact, and any gap logged against the next
  release rather than left as tribal knowledge
