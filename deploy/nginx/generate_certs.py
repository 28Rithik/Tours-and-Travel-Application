"""
Siva Gayathri Tours & Travels — Python SSL/TLS Certificate Provisioner
Uses Python's cryptography package to create 4096-bit self-signed SSL certificates.
"""

import os
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import ipaddress

CERTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certs')
os.makedirs(CERTS_DIR, exist_ok=True)

privkey_path = os.path.join(CERTS_DIR, 'privkey.pem')
fullchain_path = os.path.join(CERTS_DIR, 'fullchain.pem')
chain_path = os.path.join(CERTS_DIR, 'chain.pem')

if os.path.exists(privkey_path) and os.path.exists(fullchain_path):
    print("✅ SSL certificates already exist in", CERTS_DIR)
else:
    print("[*] Generating 4096-bit RSA Private Key via cryptography...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Tamil Nadu"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Coimbatore"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Siva Gayathri Tours and Travels"),
        x509.NameAttribute(NameOID.COMMON_NAME, "erp.sivagayathiritravels.com"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("erp.sivagayathiritravels.com"),
                x509.DNSName("sivagayathiritravels.com"),
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    with open(privkey_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    with open(fullchain_path, "wb") as f:
        f.write(cert_pem)
    with open(chain_path, "wb") as f:
        f.write(cert_pem)

    print(f"✅ Successfully generated 4096-bit RSA SSL certificates in {CERTS_DIR}")
