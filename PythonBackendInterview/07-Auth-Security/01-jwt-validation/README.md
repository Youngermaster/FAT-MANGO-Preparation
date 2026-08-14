# JWT Validation, OAuth 2.1 and OIDC

> **Prompt as you will hear it:** *"How do you validate a JWT?"* — and then, if you answer well,
> *"what attacks does each of those checks prevent?"*

The job description hammers on OAuth 2.0, OIDC and JWT, so treat this as certain to come up. The
way to stand out is to answer with the **checklist plus the attack each item stops**.

---

## Run it

```bash
uv run python 07-Auth-Security/01-jwt-validation/jwt_validation.py
uv run pytest 07-Auth-Security     # 20 tests
```

Real RSA keys, real tokens, real forgeries — the file attacks its own validator:

```
--- forgery ---
  rejected  alg:none with escalated claims
  rejected  HS256 confusion (public key as secret)
  rejected  unknown key id
  rejected  payload edited, signature kept
```

---

## OAuth 2.0 vs OIDC, in three lines

- **OAuth 2.0** is *authorisation* — delegated access to a resource. It says nothing about who you
  are.
- **OIDC** is a thin identity layer on top, adding the **ID token** (a JWT with `sub`, `iss`,
  `aud`, `exp`, `nonce`, and profile claims).
- **The ID token is for the client; the access token is for the API.** Never accept an ID token as
  an API credential — it is signed by the same issuer, so signature checks pass, but it was never
  scoped for your service. Tested here.

### Flows

| Flow | Use |
|---|---|
| **Authorization Code + PKCE** | SPAs, mobile, anything public — **the** answer |
| Client Credentials | service-to-service, no user |
| Device Code | TVs, CLIs |
| Refresh Token | getting a new access token |

⚠️ **OAuth 2.1 removed the implicit and password (ROPC) grants.** Proposing implicit flow reads as
having stopped learning around 2018.

**PKCE**, in one sentence: a public client cannot keep a secret (anyone can read a JS bundle or
decompile an app), so it sends `code_challenge = S256(verifier)` on the authorize request and the
`verifier` at token exchange — an intercepted authorization code is useless without it.

**`state` vs `nonce`:** `state` prevents CSRF on the redirect; `nonce` prevents token replay and
substitution. Different jobs, both required.

---

## The validation checklist

Each line, and the attack it stops:

| Check | Prevents |
|---|---|
| `alg` from an **allow-list**, never the header | `alg: none`, algorithm confusion |
| Signature against the right key | forgery |
| `kid` → JWKS lookup | key rotation; stops attacker-chosen keys |
| `iss` | tokens from another issuer |
| `aud` | replay of a token minted for a *different service* |
| `exp` / `nbf`, with leeway | replay of expired tokens |
| `require=[...]` on claims | a token with no `exp` never expires |
| token type / `typ` | ID token used as an API credential |

```python
jwt.decode(
    token,
    public_key,
    algorithms=["RS256"],  # <- allow-list. NEVER header["alg"]
    issuer=ISSUER,
    audience=AUDIENCE,
    leeway=30,
    options={"require": ["exp", "iat", "iss", "aud", "sub"]},
)
```

**The `aud` check deserves emphasis.** Without it, every service trusting the same IdP accepts
tokens minted for any other service — one leaked token becomes lateral movement across the whole
estate. It is the check people most often skip.

**Leeway matters operationally.** A few seconds of clock drift between the IdP and your pod causes
intermittent 401s that are miserable to debug. 30–60 seconds is normal.

---

## The two attacks worth being able to explain

### `alg: none`

The spec permits an "unsecured" JWT with no signature. A validator that honours the header's `alg`
accepts anything — edit the payload, drop the signature, done.
`test_a_naive_validator_ACCEPTS_alg_none` shows a naive validator handing over an admin session.

### Algorithm confusion (RS256 → HS256)

The better one to know, because far fewer candidates can explain it.

The RSA **public** key is public — the attacker has it. They set `alg: HS256` and sign the token
using **the public key as the HMAC secret**. A validator that picks the algorithm from the header
then verifies the HMAC with that same public key, and it matches. The signature is genuinely
valid, just under the wrong algorithm.

Two facts, kept separate because the distinction is the interesting part:

1. **The attack is real.** `test_confusion_signature_is_cryptographically_valid` verifies the
   forged HMAC by hand with `hmac.compare_digest` — no library involved.
2. **Modern pyjwt blocks it anyway.** `prepare_key` raises *"The specified key is an asymmetric key
   or x509 certificate and should not be used as an HMAC secret"* on **both** encode and decode.
   That is defence-in-depth added after the CVEs — which is why the "naive pyjwt validator"
   version of that test cannot even be written.

The allow-list protects you in principle; a maintained library is a second layer. Hand-rolled
verification or an older library has only the first, which is why this still appears in the wild.

---

## JWKS caching

```python
keystore.public_key(kid)
```

Two rules in tension:

- **Cache it.** Fetching JWKS per request adds latency and lets an IdP outage take you down.
- **But refresh on an unknown `kid`.** Keys rotate; caching forever means every token signed with
  the new key fails until you redeploy.

The usual shape is a TTL plus a one-shot refresh on cache miss, **rate-limited** so a stream of
bogus `kid`s cannot turn into a DoS against your IdP.

`kid` is also what makes zero-downtime rotation possible: publish both keys, start signing with
the new one, retire the old after the longest token lifetime.

---

## HS256 or RS256?

**Asymmetric (RS256/ES256) for anything multi-service.** Only the auth server holds the private
key; every resource server verifies with the public JWKS. With HS256 the shared secret must live
in every service that validates — so any one of them can also *mint* tokens, and rotating means
coordinating a redeploy everywhere.

---

## Revocation: the honest answer

You cannot revoke a JWT natively — that is the price of being stateless. Mitigations, in order of
how often they are actually used:

1. **Short TTLs** (5–15 min) so the window is small.
2. **A `jti` denylist** in Redis with a TTL equal to the token's remaining life.
3. **A `token_version` claim** compared against the user record — one lookup, invalidates all of a
   user's tokens at once (password change, forced logout).
4. **Reference tokens + introspection** (RFC 7662) — stateful, so revocation is instant, at the
   cost of a call per request.

Saying "you can't, here is what I'd do instead" is the answer. Claiming you can revoke one is not.

---

## Storage and refresh rotation

`localStorage` is readable by any XSS. The production default:

- **Access token in memory**, short-lived.
- **Refresh token in an `HttpOnly`, `Secure`, `SameSite` cookie**, with **rotation** — each use
  issues a new one — and **reuse detection**: if an old refresh token is presented again, revoke
  the entire token family, because it means one was stolen.

Be honest about the trade-off: cookies move the risk from XSS to CSRF, which you then handle with
`SameSite` and CSRF tokens.

---

## Scopes vs roles, and BOLA

**Scopes** are what the *client application* may request. **Roles/permissions** are what the *user*
may do. They are not interchangeable.

Parse scopes correctly: OAuth sends them **space-delimited in one string**, so
`"orders:read" in claims["scope"]` on the raw string also matches `orders:readonly`. Split first —
tested here.

Embedding roles in the JWT means role changes do not take effect until expiry. Name that trade-off
rather than pretending it does not exist.

And the biggest real-world API bug, **OWASP API1 — BOLA**: a valid token is not authorisation for
*that object*. Authentication says who you are; you still have to check the resource belongs to
them. `GET /orders/{id}` with a valid token for a different user is the most common serious API
vulnerability there is.

---

## Error messages

Distinguishing "expired" from "bad signature" from "wrong audience" in the response gives an
attacker a free oracle. **Log the detail, return one generic 401.**
`test_error_message_does_not_leak_the_reason` asserts all three failures produce the identical
message.

---

## Library choices are a signal

| Use | Not | Why |
|---|---|---|
| `pyjwt`, `joserfc`, `authlib` | `python-jose` | maintenance and CVE concerns |
| `argon2-cffi`, `pwdlib` | `passlib` | effectively unmaintained |
| `secrets.compare_digest` | `==` for API keys | timing attacks |

Knowing *why* a popular tutorial dependency is a bad pick in 2026 is cheap, memorable signal.

---

## Say it out loud

> OAuth 2.0 is authorisation and OIDC adds identity on top via the ID token — and the ID token is
> for the client, never an API credential. For any public client the flow is authorization code
> with PKCE; implicit and password grants were removed in OAuth 2.1. To validate an access token
> I check the signature, but the critical part is that the algorithm comes from my own allow-list
> and never from the token header — otherwise you're open to `alg: none` and to algorithm
> confusion, where an attacker signs with HS256 using the RSA public key as the HMAC secret and a
> header-trusting validator accepts it. Then issuer, audience, expiry with some leeway for clock
> skew, and I resolve the `kid` against a cached JWKS that refreshes on an unknown key id so
> rotation works. Audience is the one people skip, and without it a token for one service is
> accepted by every other service sharing the IdP. I return a generic 401 rather than saying which
> check failed. Revocation is the real limitation — you can't revoke a JWT, so short TTLs plus a
> `jti` denylist or a token-version claim. And none of that is authorisation for a specific
> object: checking the order actually belongs to the caller is BOLA, which is the most common
> serious API vulnerability.
