"""
Labyrinth Analytics - License Key Generator

Generates signed Ed25519 license keys for LoreConvo and LoreDocs Pro.

Usage:
    python scripts/generate_license_key.py \\
        --product loreconvo \\
        --email customer@example.com \\
        --exp 2027-04-03

    python scripts/generate_license_key.py \\
        --product lore_suite \\
        --email customer@example.com \\
        --exp never

Required environment variable:
    LAB_LICENSE_PRIVATE_KEY  -- PEM-encoded Ed25519 private key (single line,
                                no newlines, or full multi-line PEM block).

Valid products:
    loreconvo   -- LoreConvo only
    loredocs    -- LoreDocs only
    lore_suite  -- Both LoreConvo AND LoreDocs (bundle license)

Expiry formats:
    YYYY-MM-DD  -- expires on this date (not inclusive)
    never       -- lifetime license (no expiry check)

Output:
    LAB-{base64url(payload)}.{base64url(signature)}

SECURITY:
    - The private key (LAB_LICENSE_PRIVATE_KEY) must NEVER be committed to git.
    - Store it in a secure password manager or secrets vault.
    - The public key embedded in the products can only verify keys, not generate them.
    - Each customer gets a unique key (different email/exp produces a different signature).
    - Revocation is not supported in v1.0 -- set appropriate expiry dates.
"""

import argparse
import base64
import json
import os
import sys
import textwrap
from datetime import date

VALID_PRODUCTS = {"loreconvo", "loredocs", "lore_suite"}
KEY_PREFIX = "LAB-"
ISSUER_VERSION = "1.0"


def load_private_key():
    """Load the Ed25519 private key from the LAB_LICENSE_PRIVATE_KEY env var.

    The env var can contain:
      - A raw base64-encoded PKCS8 DER blob
      - A full PEM block (-----BEGIN PRIVATE KEY----- ... -----END PRIVATE KEY-----)
      - A single-line PEM (all on one line, newlines replaced with spaces)
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    raw_env = os.environ.get("LAB_LICENSE_PRIVATE_KEY", "").strip()
    if not raw_env:
        print(
            "ERROR: LAB_LICENSE_PRIVATE_KEY environment variable is not set.",
            file=sys.stderr,
        )
        print(
            "Set it to the PEM-encoded Ed25519 private key for Labyrinth Analytics.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Normalize single-line PEM (spaces instead of newlines)
    pem_str = raw_env.replace("\\n", "\n")
    if "BEGIN PRIVATE KEY" in pem_str and "\n" not in pem_str:
        # Try to reconstruct multi-line PEM
        pem_str = (
            pem_str
            .replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
            .replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----\n")
        )

    try:
        pem_bytes = pem_str.encode("utf-8")
        return load_pem_private_key(pem_bytes, password=None)
    except Exception as e:
        print(f"ERROR: Could not load private key from LAB_LICENSE_PRIVATE_KEY: {e}", file=sys.stderr)
        sys.exit(1)


def _b64url_encode(data: bytes) -> str:
    """Encode bytes as base64url without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_license_key(product: str, email: str, exp: str) -> str:
    """Generate a signed license key.

    Args:
        product: One of loreconvo, loredocs, lore_suite.
        email:   Customer email (for support reference).
        exp:     Expiry date YYYY-MM-DD or "never".

    Returns:
        A LAB-... license key string.
    """
    if product not in VALID_PRODUCTS:
        raise ValueError(f"Invalid product '{product}'. Choose from: {sorted(VALID_PRODUCTS)}")

    if exp != "never":
        try:
            exp_date = date.fromisoformat(exp)
        except ValueError:
            raise ValueError(f"Invalid expiry date '{exp}'. Use YYYY-MM-DD or 'never'.")
        if exp_date <= date.today():
            raise ValueError(f"Expiry date {exp} must be in the future.")

    payload = {
        "product": product,
        "tier": "pro",
        "exp": exp,
        "iss": ISSUER_VERSION,
        "email": email,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_bytes = payload_json.encode("utf-8")

    private_key = load_private_key()
    sig_bytes = private_key.sign(payload_bytes)

    encoded_payload = _b64url_encode(payload_bytes)
    encoded_sig = _b64url_encode(sig_bytes)

    return f"{KEY_PREFIX}{encoded_payload}.{encoded_sig}"


def main():
    parser = argparse.ArgumentParser(
        description="Generate a signed Labyrinth Analytics license key.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # LoreConvo Pro, expires 2027-04-03
              python scripts/generate_license_key.py \\
                  --product loreconvo \\
                  --email alice@example.com \\
                  --exp 2027-04-03

              # Lore Suite (both products), lifetime license
              python scripts/generate_license_key.py \\
                  --product lore_suite \\
                  --email bob@company.com \\
                  --exp never

            Required env var:
              LAB_LICENSE_PRIVATE_KEY=<PEM-encoded Ed25519 private key>
        """),
    )
    parser.add_argument(
        "--product",
        required=True,
        choices=sorted(VALID_PRODUCTS),
        help="Product to license.",
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Customer email address (included in license for support reference).",
    )
    parser.add_argument(
        "--exp",
        required=True,
        help="Expiry date as YYYY-MM-DD or 'never' for lifetime license.",
    )
    args = parser.parse_args()

    try:
        key = generate_license_key(args.product, args.email, args.exp)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print()
    print("=" * 70)
    print("LABYRINTH ANALYTICS LICENSE KEY")
    print("=" * 70)
    print(f"Product : {args.product}")
    print(f"Email   : {args.email}")
    print(f"Expires : {args.exp}")
    print()
    print("License Key:")
    print(key)
    print("=" * 70)
    print()
    print("Customer instructions:")
    if args.product in ("loreconvo", "lore_suite"):
        print(f"  Set LORECONVO_PRO={key}")
        print("  in your Claude settings MCP env block for LoreConvo.")
    if args.product in ("loredocs", "lore_suite"):
        print(f"  Set LOREDOCS_PRO={key}")
        print("  in your Claude settings MCP env block for LoreDocs.")
    print()


if __name__ == "__main__":
    main()
