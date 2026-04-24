# Idea: One Player, Many Exam Packs

## Problem

Right now the app behaves like a finished product for a single exam, not like a reusable platform.

The current coupling is strong in three places:

- The packaged app bundles one database file and one image set.
- The main process assumes a single `questions` table from a single source.
- The product identity and content identity are effectively the same thing.

That means every new exam requires rebuilding and republishing the whole app, even if only the question bank changes.

## Product Idea

Split the system into two independent parts:

1. `Player`
   A generic Electron application responsible for UI, exam flow, scoring, review mode, timer, progress, and local content management.

2. `Exam Pack`
   A portable content bundle that contains metadata, questions, options, answers, explanations, objectives, and assets for a specific certification or exam code.

The player should not know or care whether the active pack is:

- CompTIA Server+ `SK0-005`
- AWS Solutions Architect `SAA-C03`
- Microsoft Azure `AZ-104`
- Cisco `CCNA 200-301`

It should only understand the normalized pack contract.

## Recommended Direction

Treat the app as an `exam engine` and each question bank as an `installable content pack`.

That gives you these advantages:

- Release the player separately from the content.
- Add new vendors and exam codes without forking the app.
- Update a pack without forcing a player rebuild.
- Support multiple installed exams on one machine.
- Enable future marketplace, import/export, licensing, or private distribution models.

## User Experience Goal

The top-level app should feel like a library-based study player:

- Open app.
- See installed exam packs.
- Choose vendor, certification, and exam code.
- Start practice or timed exam.
- Optionally import a new pack from file.

## Commercial Product Idea

If you want this to become a real product, think of it as two sellable layers:

1. `Exam Engine`
   The player application, session engine, analytics, progress tracking, import flow, subscription enforcement, and account experience.

2. `Exam Content`
   The Q&A packs, organized by vendor, certification family, exam code, and version.

Possible commercial packaging:

- `Engine only`: free or low-cost player, useful for attracting installs.
- `Engine + subscription`: recurring subscription unlocks one or more pack families.
- `Credits`: users spend credits to unlock a pack permanently or temporarily.
- `Hybrid`: subscription includes access to a catalog, credits unlock premium or permanent packs.

Recommended business direction:

- Sell the player as the platform.
- Sell access to packs through entitlements.
- Treat the local `.exam-pack` file as a delivery artifact, not as the source of truth for authorization.

That distinction matters because once a file is on the user machine, perfect protection is not realistic. The monetization control point should be `entitlements`, not just file hiding.

## Recommended Packaging Model

Use a file-based content pack with a stable extension, for example:

- `.exam-pack`

Internally this can just be a zip archive containing:

- `manifest.json`
- `content.db` or `content.jsonl`
- `assets/`

This is better than hardcoding raw CSV or raw SQL files because it gives you:

- versioned schemas
- compatibility checks
- metadata for display and filtering
- checksum validation
- clean import/export

## Key Principle

Do not decouple only the file path.

Decouple the `product boundary`:

- The player owns behavior.
- The pack owns content.

That is the change that turns this into a reusable exam practice platform instead of a single-exam desktop app.