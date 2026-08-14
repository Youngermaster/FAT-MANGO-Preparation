"""JWT validation done properly -- and the attacks that work when it is not.

    uv run python 07-Auth-Security/01-jwt-validation/jwt_validation.py

Interviewers ask "how do you validate a JWT?" expecting a checklist. The way to stand out is to
answer with the checklist AND the attack each item prevents. This file mints real tokens with
`pyjwt`, then attacks its own validator, so every claim is demonstrated rather than asserted.

Library choice is itself a signal: `pyjwt` over `python-jose` (maintenance/CVE concerns), and
`argon2-cffi`/`pwdlib` over `passlib` (effectively unmaintained).
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "https://auth.example.com"
AUDIENCE = "https://api.example.com"
LEEWAY_SECONDS = 30  # tolerance for clock skew between the issuer and us


class InvalidToken(Exception):
    """Raised for any validation failure.

    Deliberately does NOT say why. Telling an attacker "signature invalid" vs "expired" vs
    "wrong audience" is a free oracle. Log the detail; return a generic 401.
    """


# ==========================================================================================
# A tiny JWKS: what an identity provider publishes at /.well-known/jwks.json
# ==========================================================================================


@dataclass
class KeyStore:
    """Stands in for a cached JWKS fetched from the IdP.

    In production this is fetched over HTTPS and cached. Two rules that matter:

      * CACHE IT. Fetching per request adds latency and lets an IdP outage take you down.
      * BUT refresh on an unknown `kid`, because keys rotate. Caching forever means every token
        signed with the new key fails until you redeploy. The usual shape is a TTL plus a
        one-shot refresh on cache miss, rate-limited so a bogus `kid` cannot become a DoS.
    """

    keys: dict[str, Any] = field(default_factory=dict)
    fetch_count: int = 0

    def add_rsa_key(self, kid: str) -> rsa.RSAPrivateKey:
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.keys[kid] = private
        return private

    def public_key(self, kid: str) -> Any:
        self.fetch_count += 1
        if kid not in self.keys:
            raise InvalidToken("unknown key id")
        return self.keys[kid].public_key()


# ==========================================================================================
# Validation
# ==========================================================================================

# THE MOST IMPORTANT LINE IN THE FILE.
# The algorithm is decided by US, not read from the token header. An attacker controls the
# header, so trusting `alg` from it enables both `alg: none` and algorithm confusion.
ALLOWED_ALGORITHMS = ["RS256"]


def validate_token(token: str, keystore: KeyStore) -> dict[str, Any]:
    """Validate an access token and return its claims.

    The checklist, each item with the attack it stops:

      1. `alg` from an ALLOW-LIST      -> `alg: none`, RS256/HS256 confusion
      2. signature against the right key -> forgery
      3. `kid` -> JWKS lookup           -> key rotation, and stops attacker-chosen keys
      4. `iss`                          -> a token from another issuer
      5. `aud`                          -> replay of a token minted for a different service
      6. `exp` / `nbf` (with leeway)    -> replay of an old token
      7. token type                     -> using an ID token as an API credential
    """
    try:
        # `get_unverified_header` is safe -- it parses without trusting. What is NOT safe is
        # using the `alg` it contains to choose the verification algorithm.
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise InvalidToken("malformed token") from exc

    kid = header.get("kid")
    if not kid:
        raise InvalidToken("no key id")

    public_key = keystore.public_key(kid)

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=ALLOWED_ALGORITHMS,  # <- allow-list, never header["alg"]
            issuer=ISSUER,
            audience=AUDIENCE,
            leeway=LEEWAY_SECONDS,
            options={
                "require": ["exp", "iat", "iss", "aud", "sub"],
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_signature": True,
            },
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken("token rejected") from exc

    # An ID token proves WHO the user is to the client. An access token authorises API calls.
    # Accepting an ID token as a credential is a classic senior trap: it is signed by the same
    # issuer, so signature checks pass, but it was never scoped for your API.
    if claims.get("typ") == "id":
        raise InvalidToken("id token used as an access token")

    return claims


def has_scope(claims: dict[str, Any], required: str) -> bool:
    """OAuth scopes arrive as a single space-delimited string, not a list."""
    return required in claims.get("scope", "").split()


# ==========================================================================================
# Minting, for the demo
# ==========================================================================================


def mint(
    keystore: KeyStore,
    kid: str,
    *,
    subject: str = "user-123",
    audience: str = AUDIENCE,
    issuer: str = ISSUER,
    expires_in: int = 900,
    scope: str = "orders:read",
    typ: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": subject,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + expires_in,
        "scope": scope,
        # `jti` is the hook for revocation: keep a denylist of jtis in Redis with a TTL equal
        # to the token's remaining lifetime.
        "jti": f"jti-{now}",
    }
    if typ:
        payload["typ"] = typ
    if extra:
        payload.update(extra)
    return jwt.encode(payload, keystore.keys[kid], algorithm="RS256", headers={"kid": kid})


# ==========================================================================================
# The attacks
# ==========================================================================================


def _b64(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def forge_alg_none(claims: dict[str, Any], kid: str) -> str:
    """The `alg: none` attack.

    The spec allows an "unsecured" JWT with no signature. A validator that reads `alg` from the
    header and honours `none` accepts anything -- an attacker just edits the payload and drops
    the signature. Our allow-list makes this a non-event.
    """
    header = _b64({"alg": "none", "typ": "JWT", "kid": kid})
    payload = _b64(claims)
    return f"{header}.{payload}."


def forge_algorithm_confusion(claims: dict[str, Any], public_key_pem: bytes, kid: str) -> str:
    """Algorithm confusion: RS256 -> HS256.

    The RSA public key is, by definition, public. If the validator picks the algorithm from the
    token header, an attacker sets `alg: HS256` and signs with the PUBLIC KEY AS THE HMAC
    SECRET. The validator then "verifies" with that same public key -- and it matches.

    This is the single best argument for the algorithm allow-list, and the one worth being able
    to explain: most candidates can name `alg: none`, far fewer can explain this one.

    The signature is built BY HAND here because pyjwt refuses to cooperate -- on BOTH sides:

        InvalidKeyError: The specified key is an asymmetric key or x509 certificate
                         and should not be used as an HMAC secret.

    That is library-level defence-in-depth added after the CVEs, and it is worth stating
    precisely, because the two facts are separate:

      * The attack is REAL -- the forged HMAC genuinely verifies against the public key. The
        test verifies it with `hmac.compare_digest`, no library involved.
      * Modern pyjwt blocks it ANYWAY, even if you were careless enough to trust the header.

    So the allow-list is what protects you in principle; a maintained library is a second
    layer. Hand-rolled verification, an old library, or another ecosystem's library has only
    the first -- which is exactly why this attack still appears in the wild.
    """
    import hashlib
    import hmac

    header = _b64({"alg": "HS256", "typ": "JWT", "kid": kid})
    payload = _b64(claims)
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(public_key_pem, signing_input, hashlib.sha256).digest()
    encoded_sig = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{encoded_sig}"


if __name__ == "__main__":
    store = KeyStore()
    store.add_rsa_key("key-1")
    store.add_rsa_key("key-2")  # the rotated-in key

    def check(label: str, token: str) -> None:
        try:
            claims = validate_token(token, store)
            print(f"  ACCEPTED  {label:<44} sub={claims['sub']}")
        except InvalidToken as exc:
            print(f"  rejected  {label:<44} ({exc})")

    print("\n--- valid tokens ---")
    check("well-formed token", mint(store, "key-1"))
    check("signed with the rotated key", mint(store, "key-2"))

    print("\n--- expiry and clock skew ---")
    check("expired 10 minutes ago", mint(store, "key-1", expires_in=-600))
    check("expired 10s ago (inside 30s leeway)", mint(store, "key-1", expires_in=-10))

    print("\n--- wrong audience / issuer ---")
    check("minted for another API", mint(store, "key-1", audience="https://other.example.com"))
    check("from another issuer", mint(store, "key-1", issuer="https://evil.example.com"))

    print("\n--- token confusion ---")
    check("ID token used as an access token", mint(store, "key-1", typ="id"))

    print("\n--- forgery ---")
    good = mint(store, "key-1")
    claims = jwt.decode(
        good,
        options={"verify_signature": False},
        algorithms=["RS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    escalated = {**claims, "sub": "admin", "scope": "orders:read orders:write admin"}

    check("alg:none with escalated claims", forge_alg_none(escalated, "key-1"))

    from cryptography.hazmat.primitives import serialization

    public_pem = (
        store.keys["key-1"]
        .public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    check(
        "HS256 confusion (public key as secret)",
        forge_algorithm_confusion(escalated, public_pem, "key-1"),
    )

    check("unknown key id", mint(store, "key-1").rsplit(".", 1)[0] + ".tampered")
    check("payload edited, signature kept", good[: len(good) // 2] + good[len(good) // 2 :][::-1])

    print("\n--- scopes ---")
    token = mint(store, "key-1", scope="orders:read profile")
    claims = validate_token(token, store)
    for scope in ["orders:read", "orders:write"]:
        print(f"  has {scope:<14} -> {has_scope(claims, scope)}")

    print(
        f"\n  JWKS lookups performed: {store.fetch_count} (cache these; refresh on unknown kid)\n"
    )
