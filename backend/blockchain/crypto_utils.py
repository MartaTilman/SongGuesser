import base64
import hashlib
import hmac
import json
import secrets


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
    padding = b"=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def generate_salt(byte_count=32):
    return secrets.token_hex(byte_count)


def mgf1(seed, length, hash_name="sha256"):
    output = b""
    counter = 0

    while len(output) < length:
        output += hashlib.new(
            hash_name,
            seed + counter.to_bytes(4, "big")
        ).digest()
        counter += 1

    return output[:length]


def verify_rsa_pss_sha256(public_key_jwk, message, signature):
    try:
        key_type = public_key_jwk.get("kty")
        algorithm = public_key_jwk.get("alg")

        if key_type != "RSA" or algorithm not in (None, "PS256"):
            return False

        modulus = int.from_bytes(base64url_decode(public_key_jwk["n"]), "big")
        exponent = int.from_bytes(base64url_decode(public_key_jwk["e"]), "big")
        signature_bytes = base64url_decode(signature)

        modulus_length = (modulus.bit_length() + 7) // 8
        if len(signature_bytes) != modulus_length:
            return False

        encoded = pow(
            int.from_bytes(signature_bytes, "big"),
            exponent,
            modulus
        ).to_bytes(modulus_length, "big")

        return verify_pss_encoded_message(
            encoded,
            hashlib.sha256(message.encode("utf-8")).digest(),
            modulus.bit_length() - 1
        )
    except Exception:
        return False


def verify_pss_encoded_message(encoded, message_hash, em_bits):
    hash_length = hashlib.sha256().digest_size
    salt_length = hash_length
    encoded_length = (em_bits + 7) // 8

    if len(encoded) != encoded_length:
        return False

    if encoded_length < hash_length + salt_length + 2:
        return False

    if encoded[-1] != 0xBC:
        return False

    masked_db = encoded[:encoded_length - hash_length - 1]
    digest = encoded[encoded_length - hash_length - 1:-1]

    leftmost_bits = 8 * encoded_length - em_bits
    if leftmost_bits and masked_db[0] >> (8 - leftmost_bits):
        return False

    db_mask = mgf1(digest, encoded_length - hash_length - 1)
    db = bytes(a ^ b for a, b in zip(masked_db, db_mask))

    if leftmost_bits:
        db = bytes([db[0] & (0xFF >> leftmost_bits)]) + db[1:]

    padding_length = encoded_length - hash_length - salt_length - 2
    if db[:padding_length] != b"\x00" * padding_length:
        return False

    if db[padding_length] != 0x01:
        return False

    salt = db[-salt_length:]
    expected = hashlib.sha256(b"\x00" * 8 + message_hash + salt).digest()
    return hmac.compare_digest(digest, expected)


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
