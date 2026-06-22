import base64
import hashlib
import json
import secrets

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers


def canonical_json(payload):
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )


def sha256_hex(payload):
    if isinstance(payload, str):
        payload = payload.encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def base64url_decode(value):
    raw = str(value or "").encode("ascii")
    padding_chars = b"=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode(raw + padding_chars)


def generate_salt(byte_count=32):
    return secrets.token_hex(byte_count)


def verify_rsa_pss_sha256(public_key_jwk, message, signature):
    try:
        key_type = public_key_jwk.get("kty")
        algorithm = public_key_jwk.get("alg")

        if key_type != "RSA" or algorithm not in (None, "PS256"):
            return False

        modulus = int.from_bytes(base64url_decode(public_key_jwk["n"]), "big")
        exponent = int.from_bytes(base64url_decode(public_key_jwk["e"]), "big")
        signature_bytes = base64url_decode(signature)

        public_key = RSAPublicNumbers(exponent, modulus).public_key()

        public_key.verify(
            signature_bytes,
            message.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=32
            ),
            hashes.SHA256()
        )

        return True
    except (InvalidSignature, Exception):
        return False


def build_signed_action(action, lobby_id, player_name, payload=None):
    return {
        "action": action,
        "lobby_id": str(lobby_id or "").upper(),
        "player": player_name,
        "payload": payload or {}
    }


def verify_signed_action(public_key_jwk, envelope, expected_action, lobby_id, player_name):
    if not public_key_jwk:
        return False

    if not isinstance(envelope, dict):
        return False

    payload = envelope.get("payload")
    signature = envelope.get("signature")

    if not isinstance(payload, dict) or not signature:
        return False

    if payload.get("action") != expected_action:
        return False

    if payload.get("lobby_id") != str(lobby_id or "").upper():
        return False

    if payload.get("player") != player_name:
        return False

    return verify_rsa_pss_sha256(
        public_key_jwk,
        canonical_json(payload),
        signature
    )
