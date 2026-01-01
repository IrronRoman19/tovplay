"""
SSL Certificate Monitoring Script

Checks SSL certificate expiry dates for TovPlay domains and updates Prometheus metrics.
This script should be run periodically (e.g., every 6 hours via cron/APScheduler).

Author: TovPlay Team
Last Updated: 2025-11-12
"""

import ssl
import socket
import os
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def get_ssl_certificate_info(hostname: str, port: int = 443) -> Optional[Dict]:
    """
    Get SSL certificate information for a given hostname.

    Args:
        hostname: Domain name to check
        port: Port number (default: 443)

    Returns:
        Dictionary with certificate info or None if failed
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()

                # Parse expiry date
                not_after = cert.get('notAfter')
                if not_after:
                    expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (expiry_date - datetime.utcnow()).days

                    return {
                        'hostname': hostname,
                        'expiry_date': expiry_date,
                        'days_until_expiry': days_until_expiry,
                        'subject': dict(x[0] for x in cert['subject']),
                        'issuer': dict(x[0] for x in cert['issuer'])
                    }
    except Exception as e:
        logger.error(f"Failed to get SSL certificate info for {hostname}: {e}")
        return None


def check_all_certificates():
    """
    Check SSL certificates for all TovPlay domains and update metrics.
    """
    from src.app.metrics import update_ssl_certificate_expiry, get_environment

    env = get_environment()

    # Define domains to check based on environment
    domains = []

    if env == 'production':
        domains = [
            'app.tovplay.org',
            'tovplay.vps.webdock.cloud'
        ]
    elif env == 'staging':
        domains = [
            'staging.tovplay.org'
        ]
    else:
        # Development - check production domains anyway for monitoring
        domains = [
            'app.tovplay.org',
            'staging.tovplay.org',
            'tovplay.vps.webdock.cloud'
        ]

    results = []

    for domain in domains:
        logger.info(f"Checking SSL certificate for {domain}...")
        cert_info = get_ssl_certificate_info(domain)

        if cert_info:
            days_left = cert_info['days_until_expiry']
            logger.info(
                f"✓ {domain}: Certificate expires in {days_left} days "
                f"(on {cert_info['expiry_date'].strftime('%Y-%m-%d')})"
            )

            # Update Prometheus metric
            update_ssl_certificate_expiry(domain, days_left)

            # Warn if certificate is expiring soon
            if days_left < 30:
                logger.warning(
                    f"⚠ WARNING: SSL certificate for {domain} expires in {days_left} days!"
                )

            if days_left < 7:
                logger.critical(
                    f"🚨 CRITICAL: SSL certificate for {domain} expires in {days_left} days! "
                    f"RENEW IMMEDIATELY!"
                )

            results.append(cert_info)
        else:
            logger.error(f"✗ {domain}: Failed to retrieve certificate information")

    return results


def check_certificate_command(hostname: str):
    """
    CLI command to check a specific certificate.

    Args:
        hostname: Domain name to check
    """
    cert_info = get_ssl_certificate_info(hostname)

    if cert_info:
        print(f"\n{'='*60}")
        print(f"SSL Certificate Information for {hostname}")
        print(f"{'='*60}")
        print(f"Subject:    {cert_info['subject'].get('commonName', 'N/A')}")
        print(f"Issuer:     {cert_info['issuer'].get('organizationName', 'N/A')}")
        print(f"Expires:    {cert_info['expiry_date'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Days Left:  {cert_info['days_until_expiry']} days")

        if cert_info['days_until_expiry'] < 30:
            print(f"\n⚠ WARNING: Certificate expires in less than 30 days!")
        if cert_info['days_until_expiry'] < 7:
            print(f"\n🚨 CRITICAL: Certificate expires in less than 7 days! RENEW NOW!")

        print(f"{'='*60}\n")
        return True
    else:
        print(f"✗ Failed to retrieve certificate information for {hostname}")
        return False


if __name__ == '__main__':
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) > 1:
        # Check specific domain from command line
        hostname = sys.argv[1]
        check_certificate_command(hostname)
    else:
        # Check all configured domains
        print("\nChecking SSL certificates for all TovPlay domains...\n")
        results = check_all_certificates()
        print(f"\n✓ Checked {len(results)} domain(s)")
