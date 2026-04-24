# Implementation Plan

## Goal

Move from a single bundled Server+ application to a reusable player that supports interchangeable exam packs from multiple vendors and exam codes.

## Guiding Rules

- Do not redesign the entire UI first.
- Preserve the current practice and timed-exam behavior.
- Introduce a stable content contract before adding more vendors.
- Convert the existing Server+ bank into the first pack before onboarding a second exam.

## Phase 1: Define the Content Contract

### Deliverables

- Pack manifest schema.
- Normalized runtime question model.
- Pack compatibility policy.
- Pack storage location policy.

### Concrete Tasks

- Define `manifest.json` schema and versioning rules.
- Decide whether the pack payload is SQLite, JSONL, or hybrid.
- Define asset path rules inside a pack.
- Define stable question IDs and answer model.

### Exit Criteria

- One written schema spec exists.
- One sample `Server+` pack can be described end-to-end.

## Phase 2: Refactor the Player Around a Library

### Deliverables

- `ContentLibraryService` in the Electron main process.
- New IPC endpoints for packs and active selection.
- Active pack state persisted locally.

### Concrete Tasks

- Replace direct `questions.db` assumptions in `src/main.js`.
- Introduce a pack discovery layer.
- Add `packs:list` and `packs:setActive` IPC methods.
- Keep a temporary compatibility path for the current bundled DB.

### Exit Criteria

- Player can load content through an abstraction, not a hardcoded DB path.
- Renderer can display questions from an active pack, not just the built-in bank.

## Phase 3: Build the First Pack Format and Converter

### Deliverables

- `Server+` exported as `.exam-pack`.
- Pack extraction and install logic.
- Content validation checks during import.

### Concrete Tasks

- Update `extract_questions.py` or add a new builder script that emits pack artifacts.
- Package the current SQLite content plus assets into `.exam-pack`.
- Implement pack import flow in Electron main.
- Install imported packs under `%APPDATA%`.

### Exit Criteria

- The current Server+ content runs entirely through the pack pipeline.
- The player no longer depends on a baked-in `questions.db` path for normal operation.

## Phase 4: Add Pack Selection UX

### Deliverables

- Exam library screen.
- Active exam selection.
- Pack details screen.

### Concrete Tasks

- Add a landing page that lists installed packs.
- Show vendor, product, exam code, question count, and version.
- Allow switching packs before starting practice or exam mode.
- Show import/remove actions.

### Exit Criteria

- A user can install and switch between at least two packs without restarting the app.

## Phase 5: Support a Second Exam Pack

### Deliverables

- One additional vendor or exam code installed successfully.
- Validation that the player is no longer Server+-specific.

### Concrete Tasks

- Build a second pack from another source.
- Verify session creation, scoring, and review mode work without code changes.
- Identify any Server+-specific labels or assumptions still left in the UI.

### Exit Criteria

- Two different exams from different products can run in the same player.

## Phase 6: Separate Release Pipelines

### Deliverables

- Player release pipeline.
- Pack release pipeline.

### Concrete Tasks

- Keep GitHub Actions for the player binary.
- Add a separate workflow to build and publish exam packs.
- Decide whether packs are released via GitHub Releases, a CDN, or manual distribution.

### Exit Criteria

- You can release a new pack version without rebuilding the player.

## Phase 7: Add Security and Entitlements

### Deliverables

- License or entitlement service.
- Pack signature verification.
- Offline lease support.
- Optional encrypted pack payload support.

### Concrete Tasks

- Define account, subscription, credit, and entitlement data model.
- Add player sign-in and local secure token storage.
- Add signature verification for imported packs.
- Add entitlement checks before activation.
- Add offline lease expiration behavior.
- Optionally encrypt `content.db` or package payloads.
- Add native device-key generation and local key protection.
- Add a first license-service endpoint that returns signed time-bounded decryption rights.

### Exit Criteria

- A user with valid entitlement can use the pack.
- A user without entitlement cannot activate the pack.
- Offline access works for the lease period and then revalidation is required.

## Phase 8: Add Enterprise DRM Controls

### Deliverables

- Native crypto broker.
- Device registration flow.
- Device-bound wrapped CEK flow.
- Short-lived signed license token contract.

### Concrete Tasks

- Move CEK unwrap and decrypt logic out of Electron JavaScript.
- Generate a device key pair and protect the private key with DPAPI or TPM-backed storage when available.
- Register the device public key with the backend.
- Require license issuance per `packId` and `packVersion`.
- Bind the license to `deviceId`, `sku`, and lease expiry.
- Add token signature verification and decrypt-handle caching logic.

### Exit Criteria

- The player can open a protected pack only after license issuance.
- A copied encrypted pack is not usable on a second device without a fresh license.
- Decryption no longer depends on a plaintext reusable key in Electron code.

## Phase 9: Commercial Catalog and Selling Model

### Deliverables

- SKU catalog model.
- Subscription rules.
- Credit redemption rules.
- In-app catalog and purchase-entry UX.

### Concrete Tasks

- Define whether SKUs are per pack, per vendor family, or per catalog tier.
- Define whether credits grant permanent unlock, temporary lease, or conversion to entitlement.
- Add catalog metadata to manifest and backend models.
- Decide whether checkout is external web-based or in-app.

### Exit Criteria

- The system can sell the engine, sell access to packs, and express both subscription and credit-based access clearly.

## Recommended Technical Sequence

If you want the safest execution order, do it like this:

1. Define manifest and runtime schema.
2. Add content library abstraction in `src/main.js`.
3. Convert current Server+ bank into the first pack.
4. Make the app load that pack.
5. Add pack selection UI.
6. Onboard a second exam.
7. Split release workflows.
8. Add entitlement and signature validation.
9. Add native DRM and device-bound license issuance.
10. Add subscription and credit commerce flows.

## Risks

### Risk 1: Overfitting to today’s SQLite export

If you directly expose the current `questions` table as the permanent contract, you will recreate the same coupling at a different layer.

Mitigation:

- define a player-facing normalized model first
- use adapters to map storage to runtime

### Risk 2: Asset path breakage during import

Image questions and explanations already rely on local asset resolution.

Mitigation:

- keep all asset paths pack-relative
- never store absolute machine paths in imported content

### Risk 3: Player and pack version drift

Future UI features may require new content metadata.

Mitigation:

- add `schemaVersion` and `compatiblePlayer` to manifest now

### Risk 4: Server+-specific assumptions remain in labels or defaults

Mitigation:

- audit copy, exam defaults, and renderer naming after the second pack is added

### Risk 5: Overinvesting in offline protection

If a determined user fully controls the machine, perfect offline secrecy is not possible.

Mitigation:

- focus on entitlement enforcement, not just obfuscation
- use signed packs and short offline leases
- accept that local hardening only raises cost, it does not create absolute security

### Risk 6: Putting key logic in Electron JavaScript

If the decrypt path lives entirely in renderer or main-process JavaScript, reverse engineering cost drops substantially.

Mitigation:

- move unwrap and decrypt into a signed native broker
- keep long-lived private keys out of JavaScript memory where possible
- use license expiry and device binding so compromise has a smaller blast radius

## Recommended First Milestone

The best first milestone is not multi-vendor support.

It is this:

`The current Server+ content is loaded as an installable pack through a generic content library service.`

Once that works, the rest becomes incremental.

## Suggested Future Enhancements

- pack update checks
- objective-level analytics
- licensing per pack
- cloud sync of progress independent of content
- search and filter by vendor, product, exam code, and language
- pack signing for trusted distribution
- subscription family bundles
- credit packs and promotional unlocks