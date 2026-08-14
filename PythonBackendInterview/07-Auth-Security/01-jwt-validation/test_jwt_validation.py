"""Proves the validator rejects each attack -- and that each attack is genuinely dangerous.

The second half is the important half: a rejection only means something if the thing being
rejected would otherwise have worked. So for `alg: none` there is a test showing a naive
validator handing over an admin session, and for algorithm confusion there is a test verifying
the forged HMAC by hand -- because modern pyjwt refuses to perform that verification at all,
which is itself worth knowing.
"""

from __future__ import annotations

from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from jwt_validation import (
    AUDIENCE,
    ISSUER,
    InvalidToken,
    KeyStore,
    forge_alg_none,
    forge_algorithm_confusion,
    has_scope,
    mint,
    validate_token,
)


@pytest.fixture
def store() -> KeyStore:
    ks = KeyStore()
    ks.add_rsa_key("key-1")
    ks.add_rsa_key("key-2")
    return ks


@pytest.fixture
def escalated_claims(store: KeyStore) -> dict[str, Any]:
    """Claims an attacker would want: a different subject and extra scopes."""
    good = mint(store, "key-1")
    claims = jwt.decode(
        good,
        options={"verify_signature": False},
        algorithms=["RS256"],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    return {**claims, "sub": "admin", "scope": "orders:read orders:write admin"}


# ------------------------------------------------------------------------------------------
# Happy path
# ------------------------------------------------------------------------------------------


def test_valid_token_is_accepted(store: KeyStore) -> None:
    claims = validate_token(mint(store, "key-1"), store)
    assert claims["sub"] == "user-123"
    assert claims["iss"] == ISSUER


def test_rotated_key_works_via_kid(store: KeyStore) -> None:
    """`kid` is what makes rotation possible without downtime: both keys are live at once."""
    assert validate_token(mint(store, "key-2"), store)["sub"] == "user-123"


# ------------------------------------------------------------------------------------------
# Time
# ------------------------------------------------------------------------------------------


def test_expired_token_is_rejected(store: KeyStore) -> None:
    with pytest.raises(InvalidToken):
        validate_token(mint(store, "key-1", expires_in=-600), store)


def test_leeway_tolerates_small_clock_skew(store: KeyStore) -> None:
    """Without leeway, a few seconds of drift between the IdP and your server causes
    intermittent 401s that are miserable to debug."""
    assert validate_token(mint(store, "key-1", expires_in=-10), store)["sub"] == "user-123"


def test_leeway_does_not_tolerate_real_expiry(store: KeyStore) -> None:
    with pytest.raises(InvalidToken):
        validate_token(mint(store, "key-1", expires_in=-120), store)


# ------------------------------------------------------------------------------------------
# Audience / issuer / type
# ------------------------------------------------------------------------------------------


def test_token_for_another_audience_is_rejected(store: KeyStore) -> None:
    """Without an `aud` check, any service trusting the same IdP accepts tokens minted for any
    other service -- lateral movement across your whole estate with one leaked token."""
    with pytest.raises(InvalidToken):
        validate_token(mint(store, "key-1", audience="https://other.example.com"), store)


def test_token_from_another_issuer_is_rejected(store: KeyStore) -> None:
    with pytest.raises(InvalidToken):
        validate_token(mint(store, "key-1", issuer="https://evil.example.com"), store)


def test_id_token_cannot_be_used_as_an_access_token(store: KeyStore) -> None:
    """Signed by the same issuer, so the signature checks pass -- but it was never scoped for
    your API. A classic senior trap."""
    with pytest.raises(InvalidToken, match="id token"):
        validate_token(mint(store, "key-1", typ="id"), store)


# ------------------------------------------------------------------------------------------
# Forgery -- and why the allow-list is load-bearing
# ------------------------------------------------------------------------------------------


def test_alg_none_is_rejected(store: KeyStore, escalated_claims: dict[str, Any]) -> None:
    with pytest.raises(InvalidToken):
        validate_token(forge_alg_none(escalated_claims, "key-1"), store)


def test_a_naive_validator_ACCEPTS_alg_none(
    store: KeyStore, escalated_claims: dict[str, Any]
) -> None:
    """The attack works when the algorithm is taken from the token header.

    This is the whole reason for `algorithms=ALLOWED_ALGORITHMS`.
    """
    forged = forge_alg_none(escalated_claims, "key-1")
    header_alg = jwt.get_unverified_header(forged)["alg"]

    naive = jwt.decode(
        forged,
        options={"verify_signature": False},  # what "trusting alg: none" amounts to
        algorithms=[header_alg],
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    assert naive["sub"] == "admin", "a naive validator hands the attacker an admin session"


def test_algorithm_confusion_is_rejected(store: KeyStore, escalated_claims: dict[str, Any]) -> None:
    public_pem = _public_pem(store, "key-1")
    forged = forge_algorithm_confusion(escalated_claims, public_pem, "key-1")

    with pytest.raises(InvalidToken):
        validate_token(forged, store)


def test_confusion_signature_is_cryptographically_valid(
    store: KeyStore, escalated_claims: dict[str, Any]
) -> None:
    """The forged HMAC really does verify against the public key -- checked by hand.

    Two separate facts, and the distinction is the interesting part of this topic:

    1. THE ATTACK IS REAL. Signing with the public key as an HMAC secret produces a signature
       that any validator following `alg: HS256` with that key will accept. Verified below with
       `hmac.compare_digest`, no library involved.

    2. MODERN pyjwt BLOCKS IT ANYWAY. `prepare_key` raises `InvalidKeyError: The specified key
       is an asymmetric key or x509 certificate and should not be used as an HMAC secret` --
       on BOTH encode and decode. That is library-level defence-in-depth added after the CVEs,
       and it is why the "naive pyjwt validator" version of this test cannot even be written.

    So the honest answer in an interview is: the allow-list is what protects you in principle,
    and a maintained library gives you a second layer. Hand-rolled verification, an older
    library, or another language's library has only the first.
    """
    import base64
    import hashlib
    import hmac

    public_pem = _public_pem(store, "key-1")
    forged = forge_algorithm_confusion(escalated_claims, public_pem, "key-1")
    header_b64, payload_b64, signature_b64 = forged.split(".")

    assert jwt.get_unverified_header(forged)["alg"] == "HS256"

    expected = hmac.new(public_pem, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    padding = "=" * (-len(signature_b64) % 4)
    actual = base64.urlsafe_b64decode(signature_b64 + padding)

    assert hmac.compare_digest(expected, actual), (
        "the forged signature verifies under HS256 using the PUBLIC key -- the attack is real"
    )

    # And the payload the attacker smuggled in:
    claims_padding = "=" * (-len(payload_b64) % 4)
    smuggled = jwt.api_jws.json.loads(base64.urlsafe_b64decode(payload_b64 + claims_padding))
    assert smuggled["sub"] == "admin"

    # pyjwt's second line of defence, demonstrated:
    with pytest.raises(jwt.exceptions.InvalidKeyError, match="asymmetric key"):
        jwt.decode(forged, public_pem, algorithms=["HS256"], audience=AUDIENCE, issuer=ISSUER)


def test_tampered_payload_is_rejected(store: KeyStore) -> None:
    good = mint(store, "key-1")
    header, payload, signature = good.split(".")
    tampered_payload = payload[:-4] + ("AAAA" if not payload.endswith("AAAA") else "BBBB")

    with pytest.raises(InvalidToken):
        validate_token(f"{header}.{tampered_payload}.{signature}", store)


def test_unknown_kid_is_rejected(store: KeyStore) -> None:
    other = KeyStore()
    other.add_rsa_key("attacker-key")
    token = mint(other, "attacker-key")

    with pytest.raises(InvalidToken, match="unknown key id"):
        validate_token(token, store)


def test_missing_kid_is_rejected(store: KeyStore) -> None:
    token = jwt.encode({"sub": "x"}, store.keys["key-1"], algorithm="RS256")
    with pytest.raises(InvalidToken, match="no key id"):
        validate_token(token, store)


def test_garbage_is_rejected(store: KeyStore) -> None:
    for junk in ["", "not-a-token", "a.b.c", "..."]:
        with pytest.raises(InvalidToken):
            validate_token(junk, store)


def test_required_claims_are_enforced(store: KeyStore) -> None:
    """A token without `exp` never expires. `require` makes its absence an error rather than
    a silently skipped check."""
    import time

    now = int(time.time())
    token = jwt.encode(
        {"sub": "x", "iss": ISSUER, "aud": AUDIENCE, "iat": now},  # no exp
        store.keys["key-1"],
        algorithm="RS256",
        headers={"kid": "key-1"},
    )
    with pytest.raises(InvalidToken):
        validate_token(token, store)


# ------------------------------------------------------------------------------------------
# Errors and scopes
# ------------------------------------------------------------------------------------------


def test_error_message_does_not_leak_the_reason(store: KeyStore) -> None:
    """Distinguishing "expired" from "bad signature" from "wrong audience" gives an attacker a
    free oracle. Log the detail; return one generic message."""
    reasons = set()
    for token in [
        mint(store, "key-1", expires_in=-600),
        mint(store, "key-1", audience="https://other.example.com"),
        mint(store, "key-1", issuer="https://evil.example.com"),
    ]:
        with pytest.raises(InvalidToken) as caught:
            validate_token(token, store)
        reasons.add(str(caught.value))

    assert reasons == {"token rejected"}, f"leaked distinct reasons: {reasons}"


def test_scope_parsing_is_space_delimited(store: KeyStore) -> None:
    claims = validate_token(mint(store, "key-1", scope="orders:read profile"), store)
    assert has_scope(claims, "orders:read")
    assert has_scope(claims, "profile")
    assert not has_scope(claims, "orders:write")


def test_scope_check_is_not_a_substring_match(store: KeyStore) -> None:
    """`"orders:read" in claims["scope"]` on the raw string would match "orders:read_only"
    and similar -- split on whitespace instead."""
    claims = validate_token(mint(store, "key-1", scope="orders:readonly"), store)
    assert not has_scope(claims, "orders:read")


def _public_pem(store: KeyStore, kid: str) -> bytes:
    return (
        store.keys[kid]
        .public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
