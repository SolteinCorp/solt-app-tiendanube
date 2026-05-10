# -*- coding: utf-8 -*-
"""Ed25519 request signing/verification for the TiendaNube destination module.

Both keypairs (destination and master public key set) are hardcoded here so
the customer doesn't need to perform any setup — installing the module is
enough to participate in the signed sync flow. The destination private key
embedded below is shared by every install of this module; the per-customer
identity comes from the sync_token tied to the installation record on the
master side, not from cryptographic uniqueness on the destination.
"""

import base64
import hashlib
import logging
import time
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_logger = logging.getLogger(__name__)

CLOCK_SKEW_SECONDS = 300
NONCE_TTL_SECONDS = 600
NONCE_MODEL = 'solt.tiendanube.sync.nonce'

HEADER_KEY_ID = 'X-TN-KeyId'
HEADER_TIMESTAMP = 'X-TN-Timestamp'
HEADER_NONCE = 'X-TN-Nonce'
HEADER_SIGNATURE = 'X-TN-Signature'

# ---------------------------------------------------------------------------
# Soltein master public keys.
# Map key_id -> PEM-encoded Ed25519 public key.
# Add a new entry when rotating; keep the old one for the rotation window so
# both old and new signatures are accepted, then remove the deprecated entry.
# Soltein operators: get the active master key by running the server action
# "Show TiendaNube master public key" on tiendanube.soltein.net.
# ---------------------------------------------------------------------------
MASTER_PUBLIC_KEYS = {
    'soltein-master-2026-05-62b65662b435': '''-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA4EGMILcCcYeswPjf2UAt4bnRFivCJ24xD39teoSDzAw=
-----END PUBLIC KEY-----''',
}

# ---------------------------------------------------------------------------
# Destination Ed25519 keypair, shared by every installation of this module.
# The master keeps the matching public key (under the same key_id) inside
# its own TARGET_PUBLIC_KEYS dict to verify signed callbacks. To rotate,
# generate a new keypair, ship a new module version with the new key_id and
# private key, and update the master's TARGET_PUBLIC_KEYS dict in lockstep.
# ---------------------------------------------------------------------------
TARGET_KEY_ID = 'soltein-target-2026-05-b6a89ab4b100'

TARGET_PRIVATE_KEY = '''-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIO7Fsjyph0G3C8OsCui9nIjuYRNSUHfU1BlwY9eTttwj
-----END PRIVATE KEY-----'''

TARGET_PUBLIC_KEY = '''-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAKDUnOQveQlbkqTeBLbpnHNPeqUlL9DouhzGwZYcXU7M=
-----END PUBLIC KEY-----'''


class SignatureError(Exception):
    """Raised when an inbound request fails signature verification."""


def get_master_public_key(key_id):
    """Return the PEM-encoded master pubkey for the given key_id, or None."""
    if not key_id:
        return None
    return MASTER_PUBLIC_KEYS.get(key_id)


def generate_keypair():
    """Return (private_pem, public_pem) as ASCII strings."""
    priv = Ed25519PrivateKey.generate()
    private_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('ascii')
    public_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode('ascii')
    return private_pem, public_pem


def _canonical_request(method, path, timestamp, nonce, body_bytes):
    body_hash = hashlib.sha256(body_bytes or b'').hexdigest()
    return f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}".encode('utf-8')


def sign_request(private_pem, method, path, body_bytes, key_id):
    """Sign a request and return headers to attach to the outgoing call."""
    if isinstance(private_pem, str):
        private_pem = private_pem.encode('ascii')
    priv = serialization.load_pem_private_key(private_pem, password=None)
    if not isinstance(priv, Ed25519PrivateKey):
        raise SignatureError("Private key is not Ed25519")

    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    canonical = _canonical_request(method, path, timestamp, nonce, body_bytes or b'')
    signature = base64.b64encode(priv.sign(canonical)).decode('ascii')
    return {
        HEADER_KEY_ID: key_id,
        HEADER_TIMESTAMP: timestamp,
        HEADER_NONCE: nonce,
        HEADER_SIGNATURE: signature,
    }


def _load_public_key(public_pem):
    if isinstance(public_pem, str):
        public_pem = public_pem.encode('ascii')
    pub = serialization.load_pem_public_key(public_pem)
    if not isinstance(pub, Ed25519PublicKey):
        raise SignatureError("Public key is not Ed25519")
    return pub


def verify_signature(public_pem, method, path, headers, body_bytes):
    """Verify signature headers against body. Raises SignatureError on failure."""
    timestamp = headers.get(HEADER_TIMESTAMP)
    nonce = headers.get(HEADER_NONCE)
    signature_b64 = headers.get(HEADER_SIGNATURE)
    if not (timestamp and nonce and signature_b64):
        raise SignatureError("Missing signature headers")
    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError):
        raise SignatureError("Invalid timestamp")
    if abs(int(time.time()) - timestamp_int) > CLOCK_SKEW_SECONDS:
        raise SignatureError("Timestamp outside clock skew window")
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except (ValueError, base64.binascii.Error):
        raise SignatureError("Malformed signature encoding")

    pub = _load_public_key(public_pem)
    canonical = _canonical_request(method, path, timestamp, nonce, body_bytes or b'')
    try:
        pub.verify(signature, canonical)
    except InvalidSignature:
        raise SignatureError("Signature mismatch")
    return nonce


def consume_nonce(env, key_id, nonce):
    """Atomically claim a nonce. Raises SignatureError if already used."""
    Nonce = env[NONCE_MODEL].sudo()
    Nonce.gc_expired()
    expires_at = int(time.time()) + NONCE_TTL_SECONDS
    try:
        Nonce.create({'key_id': key_id, 'value': nonce, 'expires_at': expires_at})
    except Exception:
        raise SignatureError("Nonce already used")
