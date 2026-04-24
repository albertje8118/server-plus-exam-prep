# Security and Monetization

## The Real Question

The choice is not really:

- protect the exam pack, or
- protect the player

The real question is:

`Where is the trust boundary and where is the commercial control point?`

For a paid product, the right answer is:

- the `server` is the trust anchor for entitlement
- the `player` enforces entitlement locally and manages offline access
- the `pack` is a signed and optionally encrypted delivery artifact

## Short Answer

If you must choose only one thing to protect more seriously, protect the `entitlement system`, not just the pack file or the player binary.

Why:

- a local pack file can always be copied, reverse engineered, or unpacked eventually
- a local player binary can always be patched eventually
- a server-side entitlement decision is the only place where you still control access centrally

So the practical recommendation is:

- lightly harden the player
- sign and optionally encrypt the pack
- strongly protect the license and entitlement service

## Threat Model Reality

You should assume:

- users control their own machine
- files can be copied
- JavaScript and Electron apps can be inspected
- static secrets embedded in the player can be extracted

That means `perfect offline DRM` is not realistic.

Your goal should be:

- prevent casual copying
- detect tampering
- bind value to account entitlements
- require periodic revalidation

## Decision Matrix

### Option A: Protect the Exam Pack Only

Examples:

- zip encryption
- SQLite encryption
- obfuscated assets
- custom binary container

Pros:

- reduces casual file sharing
- makes direct extraction harder
- useful as one layer in a broader design

Cons:

- the player still needs the key or decryption logic
- reverse engineering remains possible
- does not solve subscription or credit enforcement by itself

Conclusion:

- necessary as a hardening layer
- insufficient as the main business control

### Option B: Protect the Player Only

Examples:

- obfuscation
- binary signing
- anti-tamper checks
- integrity verification

Pros:

- raises patching cost
- helps preserve trust in official builds

Cons:

- does not stop pack copying if content is plain
- does not solve entitlement without backend checks
- Electron apps are inspectable enough that local-only protection is weak

Conclusion:

- necessary for integrity and supportability
- insufficient as the main commercial barrier

### Option C: Protect the Service and Use Player + Pack as Enforcement Layers

Examples:

- account login
- entitlement API
- signed packs
- optional encrypted packs
- offline lease tokens

Pros:

- best fit for subscription and credit business models
- flexible across many vendors and pack types
- lets you revoke, expire, and upgrade access centrally

Cons:

- more engineering effort
- requires backend operations
- requires careful offline policy design

Conclusion:

- this is the recommended architecture

## Recommended Selling Model

### What to Sell

You can sell three things independently:

1. `Engine Access`
   Access to the player platform and core features.

2. `Pack Access`
   Access to individual exam packs or vendor bundles.

3. `Premium Services`
   Analytics, sync, streaks, readiness scores, curated exams, cloud history.

## Business Model Options

### Model 1: Subscription Only

User pays monthly or yearly for access to a catalog tier.

Examples:

- Starter: one vendor family
- Pro: all standard packs
- Premium: all packs plus analytics and sync

Pros:

- predictable recurring revenue
- easiest entitlement model

Cons:

- some users dislike subscriptions for exam prep

### Model 2: Credits Only

User buys credits, then redeems them for packs or exam attempts.

Examples:

- 10 credits unlock a pack permanently
- 3 credits unlock 30 days of access
- 1 credit unlocks a premium curated mock exam

Pros:

- attractive for one-time exam takers
- flexible pricing per pack difficulty or vendor

Cons:

- more complex pricing logic
- harder to forecast revenue

### Model 3: Hybrid Subscription + Credits

This is the most commercially flexible model.

Recommended interpretation:

- subscription gives broad access to standard packs
- credits unlock premium packs, permanent ownership, or special content

Pros:

- maximizes user choice
- fits both recurring and one-time users
- lets you run promotions and bundles cleanly

Cons:

- more product design work

## Recommended Monetization Strategy

For this product, the best default is:

- `free player download`
- `account required for protected packs`
- `subscription for catalog access`
- `optional credits for premium or permanent unlocks`

That gives you:

- low friction acquisition
- recurring revenue
- upsell path for high-value packs

## Entitlement Model

Use SKUs, not raw file names, as the thing that users buy.

Examples:

- `engine.pro.monthly`
- `catalog.standard.monthly`
- `pack.comptia.serverplus.sk0-005`
- `pack.aws.saa-c03`
- `mockexam.premium.001`

User account should resolve to effective entitlements, for example:

```json
{
  "accountId": "user-123",
  "entitlements": [
    "catalog.standard.monthly",
    "pack.comptia.serverplus.sk0-005"
  ],
  "credits": 14,
  "offlineLeaseExpiresAt": "2026-04-29T12:00:00Z"
}
```

## Recommended Security Layers

### Layer 1: Official Player Integrity

- code signing for Windows builds
- app integrity checks for critical assets
- trusted update channel

### Layer 2: Pack Integrity

- manifest schema validation
- checksum verification
- publisher signature verification

### Layer 3: Pack Confidentiality

- optional encryption of `content.db`
- per-pack or per-session content key

### Layer 4: Entitlement Enforcement

- authenticated user account
- entitlement checks against backend
- time-bounded offline lease
- activation and revocation rules

### Layer 5: Operational Monitoring

- suspicious activation patterns
- unusual device churn
- excessive import or unlock attempts

## Recommended DRM Approach

If you want something `simple, but powerful`, use a `license-token DRM` model.

This is the closest practical shape to your Microsoft RMS analogy:

1. user authenticates
2. service validates entitlement
3. service issues a signed short-lived security token
4. token contains the right to open one pack on one device for one period
5. token carries a wrapped content key used to decrypt the pack locally

That gives you a clear trust boundary without forcing the app to stream every question from the cloud.

For the enterprise version of this model, prefer:

- `OIDC + PKCE` for user authentication
- `device registration` for player installations
- `signed license tokens` for time-bounded decryption rights
- `native broker unwrap` instead of JavaScript-only key handling
- `KMS or HSM` for server-side key custody

## DRM Building Blocks

### 1. Encrypted Pack Payload

Each protected pack should be encrypted with a random symmetric key:

- algorithm: `AES-256-GCM`
- scope: `content.db` and optionally sensitive assets
- key: one `CEK` per pack version

### 2. Device Key Pair

Each player installation generates a device key pair.

- private key stays on the machine
- on Windows, protect it with `DPAPI`
- public key is registered with the license service

This lets the service return a pack key that is useful only to that player installation.

### 3. License Token

After successful authentication, the license service returns a signed token containing:

- user identity
- device identity
- pack identity
- entitlement type
- lease expiry
- wrapped content key

Recommended properties:

- short-lived
- pack-bound
- device-bound
- signed with an asymmetric server key

### 4. Local Unwrap and Decrypt

The player:

- verifies the service signature
- unwraps the CEK using the local device private key
- decrypts the pack payload only after token validation

## Why This Is Better Than Simple Pack Encryption

If you only encrypt the pack, the player still needs some reusable decryption secret.

If you use a license token model:

- the decryption right is granted per user, per device, per pack, per time window
- the service can revoke or stop renewing access
- copied files are much less useful without a valid token

## Why This Is Better Than Trusting the Player Alone

If the player is the only authority, a patched binary can simply say `access granted`.

In the license-token model, local bypass is less damaging because:

- the player still needs a valid signed token
- the token still needs a usable wrapped key
- the token expires
- the service controls renewal

This does not stop a determined reverse engineer forever, but it reduces the attack from `copy one file once` to `continuously break a moving authorization system`.

## Minimal Recommended Version 1 DRM

Keep version 1 intentionally narrow:

- signed player build
- signed pack manifest and checksums
- encrypted `content.db`
- one CEK per pack version
- device key pair protected by DPAPI
- signed license token with wrapped CEK
- offline lease for 3 to 7 days

This is a good first version because it avoids overengineering while giving you real commercial leverage.

## License Token Example

```json
{
   "iss": "license.yourcompany.com",
   "aud": "desktop-player",
   "sub": "user-123",
   "deviceId": "device-abc",
   "packId": "comptia-serverplus-sk0-005",
   "packVersion": "1.0.0",
   "sku": "pack.comptia.serverplus.sk0-005",
   "offlineLeaseExpiresAt": "2026-04-29T12:00:00Z",
   "wrappedKey": "base64-encrypted-cek",
   "keyWrapAlgorithm": "rsa-oaep-256",
   "contentCipher": "aes-256-gcm"
}
```

## What Happens If the Pack Is Stolen

If the encrypted `.exam-pack` file is copied:

- the attacker still needs a valid license token
- the wrapped key is ideally device-bound
- the service can stop renewing access

Result:

- pack leakage is contained better than with plain files

## What Happens If the Player Is Patched

If someone bypasses the UI or local auth checks:

- the player can still be blocked from decrypting new protected packs without a valid service token
- the lease expiry forces revalidation
- revocation remains possible on the service side

Result:

- local tampering becomes a containment problem instead of a total business failure

## Practical Simplicity Rule

Do not try to build enterprise-grade DRM in version 1.

Keep the system limited to these responsibilities:

- `authentication service`: who is the user
- `entitlement service`: what are they allowed to open
- `license service`: issue short-lived signed decryption rights
- `player`: verify token, unwrap key, decrypt payload

That is simple enough to implement and operate, while still being materially stronger than plain encrypted files.

## Enterprise Design Position

If you want the strict enterprise interpretation of your requirement, state it this way:

- decryption is never granted anonymously
- decryption rights are minted only by the license service
- decryption rights are bound to an authenticated user, a registered device, a specific pack, and an expiry window
- raw pack possession does not imply usable access

That is the correct policy language for both engineering and commercial control.

See `05-enterprise-drm-spec.md` for the detailed component model, Microsoft stack, and API contract.

## Offline Access Recommendation

Do not force the app to be online at all times.

Recommended policy:

- user signs in and activates pack while online
- player stores an offline lease for a bounded period, for example 3 to 14 days
- after the lease expires, the player revalidates the entitlement

This is a good compromise between usability and commercial control.

## Example Secure Pack Activation Flow

1. User signs into player.
2. Player requests entitlements from backend.
3. Backend returns allowed SKUs and lease expiry.
4. User imports or downloads a protected `.exam-pack`.
5. Player verifies signature and checksums.
6. If the pack requires entitlement, player checks the matching SKU.
7. If valid, backend issues a short-lived pack key or unlock token.
8. Player installs pack and stores only lease-scoped authorization locally.

## Recommended Final Position

If your goal is to sell the engine plus Q&A packs, the best position is:

- `Player` is the platform and customer relationship surface.
- `Packs` are licensed content products.
- `Entitlement service` is the real security boundary.

So the answer to your question is:

- do not choose between pack and player protection in isolation
- prioritize protecting entitlement and delivery flow
- use pack and player protection as supporting layers

## Practical Recommendation for Your Next Step

Build toward this version-1 commercial architecture:

1. free downloadable player
2. signed `.exam-pack` format
3. account login
4. subscription entitlements per catalog or vendor family
5. optional credit redemption for premium packs
6. offline lease support

That is realistic, sellable, and maintainable.