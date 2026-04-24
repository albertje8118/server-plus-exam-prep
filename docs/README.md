# Content Decoupling Docs

This folder proposes how to evolve the app from a single bundled CompTIA Server+ player into a generic exam player that can load interchangeable question-and-answer content packs.

Documents:

- `01-idea.md`: product idea, goals, and recommended direction.
- `02-design.md`: target architecture, data model, and pack format.
- `03-implementation-plan.md`: phased delivery plan with milestones and risks.
- `04-security-and-monetization.md`: security model, entitlement strategy, and selling options for the engine plus content packs.
- `05-enterprise-drm-spec.md`: enterprise DRM reference architecture, Microsoft stack mapping, sequence flows, and license-service API contract.

Implementation artifacts:

- `openapi/license-service.openapi.yaml`: machine-readable contract for device registration, entitlement lookup, and license issuance.
- `schemas/exam-pack-manifest.schema.json`: strict JSON Schema for `manifest.json`.
- `schemas/license-token.schema.json`: strict JSON Schema for the signed DRM license token payload.

Current anchor in the codebase:

- The player currently loads one bundled SQLite database via `questions.db` or `questions_sqlite.sql` in `src/main.js`.
- The build packages those assets directly into the app, which ties the product to one exam bank.

Recommended outcome:

- One reusable exam player application.
- Many interchangeable exam packs, each representing a vendor, product, exam code, and version.
- A clear compatibility contract between the player and content packs.