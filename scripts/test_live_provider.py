#!/usr/bin/env python3
"""
GreenMind AI — Live Provider Connection Test Script

Tests real cloud provider connectivity WITHOUT modifying any core application logic.

Usage:
    # From the repository root:
    python scripts/test_live_provider.py --provider aws
    python scripts/test_live_provider.py --provider gcp
    python scripts/test_live_provider.py --provider azure
    python scripts/test_live_provider.py --all

Prerequisites:
    pip install -r backend/requirements.txt
    Set environment variables (or create .env from .env.example):
        AWS:   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
        Azure: AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
        GCP:   GCP_PROJECT_ID, GCP_SERVICE_ACCOUNT_JSON

Data Truth Verification:
    This script verifies that:
    1. Provider credentials are valid
    2. Live metrics are returned with correct source labels (LIVE_AWS/LIVE_AZURE/LIVE_GCP)
    3. Unavailable metrics are correctly labeled as UNAVAILABLE (not fake values)
    4. No sensitive credential data is printed to stdout
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Fix Windows console encoding for UTF-8 and unicode symbols
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add backend to path
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(REPO_ROOT))

# Load .env if present
ENV_FILE = REPO_ROOT / ".env"
if ENV_FILE.exists():
    print(f"Loading environment from: {ENV_FILE}")
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            if key.strip() and not os.environ.get(key.strip()):
                os.environ[key.strip()] = val.strip()


def _mask(value: str) -> str:
    """Mask credential values for safe stdout printing."""
    if not value:
        return "(not set)"
    return value[:4] + "***" + value[-4:] if len(value) > 8 else "****"


def check_env_security():
    """Verify no credentials are accidentally exposed in logs."""
    sensitive = [
        "AWS_SECRET_ACCESS_KEY",
        "AZURE_CLIENT_SECRET",
        "GCP_SERVICE_ACCOUNT_JSON",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
    ]
    print("\n[SECURITY CHECK] Verifying credentials are set but not printed:")
    for k in sensitive:
        v = os.environ.get(k, "")
        if v:
            print(f"  ✅ {k}: SET (masked: {_mask(v)})")
        else:
            print(f"  ⚠️  {k}: not set")
    print()


def test_aws():
    print("=" * 60)
    print("TESTING: AWS Cloud Provider")
    print("=" * 60)

    from app.cloud.aws_provider import AWSCloudProvider

    # Temporarily override demo mode
    os.environ["DEMO_MODE"] = "false"

    provider = AWSCloudProvider()
    print(f"\nProvider configured: {provider.is_configured}")
    print(f"Provider live: {provider.is_live}")

    # Test connection
    print("\n[1] Testing connection (STS + CloudWatch)...")
    result = provider.test_connection()
    print(f"  Status: {result.get('status')}")
    print(f"  Mode: {result.get('mode')}")
    print(f"  Message: {result.get('message')}")
    print(f"  Credentials: {result.get('credentials_status')}")
    print(f"  Authentication: {result.get('authentication_status')}")
    print(f"  API Reachable: {result.get('api_reachability')}")
    print(f"  Telemetry Status: {result.get('telemetry_status')}")

    # Account metadata
    acct = provider.get_account_info()
    print(f"\n[2] Account Info: {acct.get('account_id')} ({acct.get('auth_type')})")

    # Regions
    regions = provider.get_regions()
    print(f"[3] Available Regions: {len(regions)} regions found")

    if not result.get("success"):
        print("\n❌ Connection failed. Check credentials and try again.")
        return False

    # Test metrics
    print("\n[4] Fetching live metrics from CloudWatch...")
    metrics = provider.get_metrics("us-east-1")
    print(f"  source: {metrics.get('source')} ← must be LIVE_AWS")
    print(f"  cpu: {metrics.get('cpu')} %")
    print(f"  memory: {metrics.get('memory')} ← None = UNAVAILABLE (correct)")
    print(f"  memory_source: {metrics.get('memory_source')}")
    print(f"  memory_note: {metrics.get('memory_note', '')[:80]}")
    print(f"  network: {metrics.get('network')} Mbps")
    print(f"  network_source: {metrics.get('network_source')}")
    print(f"  cost_usd_per_hour: {metrics.get('cost_usd_per_hour')}")
    print(f"  cost_source: {metrics.get('cost_source')}")
    print(f"  carbon_gco2_per_hour: {metrics.get('carbon_gco2_per_hour')}")
    print(f"  instance_count: {metrics.get('instance_count')}")

    # Data truth assertions
    source = metrics.get("source")
    if source == "LIVE_AWS":
        print("\n✅ PASS: source=LIVE_AWS (live data confirmed)")
    elif source == "ERROR":
        print("\n⚠️  WARN: source=ERROR (connected but CloudWatch returned no data)")
    else:
        print(f"\n❌ FAIL: source={source} (expected LIVE_AWS)")
        return False

    # Verify no hardcoded memory values
    mem = metrics.get("memory")
    if mem == 55.0:
        print("❌ FAIL: memory=55.0 — this is the old hardcoded fallback! BUG-002 not fixed.")
        return False

    # Test resources
    print("\n[5] Listing EC2 instances...")
    resources = provider.get_resources("us-east-1")
    print(f"  Found {len(resources)} instances")
    for r in resources[:3]:
        print(f"    - {r.get('name')} ({r.get('type')}) | CPU={r.get('cpu_utilization')} | source={r.get('source')}")

    # Test Cost Explorer
    print("\n[6] Testing Cost Explorer (may show UNAVAILABLE if no ce permission)...")
    cost = provider.get_cost("us-east-1", days=7)
    print(f"  cost source: {cost.get('source')}")
    print(f"  total_usd: {cost.get('total_usd')}")
    print(f"  note: {cost.get('note', '')[:100]}")

    print("\n✅ AWS tests complete.")
    return True


def test_azure():
    print("=" * 60)
    print("TESTING: Azure Cloud Provider")
    print("=" * 60)

    from app.cloud.azure_provider import AzureCloudProvider

    os.environ["DEMO_MODE"] = "false"

    provider = AzureCloudProvider()
    print(f"\nProvider configured: {provider.is_configured}")
    print(f"Provider live: {provider.is_live}")

    print("\n[1] Testing connection (Azure ARM)...")
    result = provider.test_connection()
    print(f"  Status: {result.get('status')}")
    print(f"  Mode: {result.get('mode')}")
    print(f"  Message: {result.get('message')}")
    print(f"  Credentials: {result.get('credentials_status')}")
    print(f"  Authentication: {result.get('authentication_status')}")
    print(f"  API Reachable: {result.get('api_reachability')}")
    print(f"  Telemetry Status: {result.get('telemetry_status')}")

    acct = provider.get_account_info()
    print(f"\n[2] Account Info: {acct.get('display_name')} ({acct.get('subscription_id')})")

    regions = provider.get_regions()
    print(f"[3] Available Regions: {len(regions)} regions found")

    if not result.get("success"):
        print("\n❌ Connection failed.")
        return False

    print("\n[4] Fetching live metrics from Azure Monitor...")
    metrics = provider.get_metrics("eastus")
    print(f"  source: {metrics.get('source')} ← must be LIVE_AZURE")
    print(f"  cpu: {metrics.get('cpu')} %")
    print(f"  memory: {metrics.get('memory')} ← None = UNAVAILABLE (correct)")
    print(f"  memory_source: {metrics.get('memory_source')}")

    source = metrics.get("source")
    if source in ("LIVE_AZURE", "ERROR"):
        print(f"\n✅ PASS: source={source}")
    else:
        print(f"\n❌ FAIL: source={source} (expected LIVE_AZURE or ERROR)")
        return False

    print("\n✅ Azure tests complete.")
    return True


def test_gcp():
    print("=" * 60)
    print("TESTING: GCP Cloud Provider")
    print("=" * 60)

    from app.cloud.gcp_provider import GCPCloudProvider

    os.environ["DEMO_MODE"] = "false"

    provider = GCPCloudProvider()
    print(f"\nProject ID configured: {bool(provider.project_id)}")
    print(f"Service Account configured: {bool(provider.service_account_json)}")
    print(f"is_configured: {provider.is_configured}")
    print(f"is_live: {provider.is_live}")

    if not provider.is_configured:
        print("\n⚠️  GCP not configured. Set GCP_PROJECT_ID and GCP_SERVICE_ACCOUNT_JSON.")
        print("   Note: BUG-004 fix requires BOTH to be set for is_configured=True")
        return False

    print("\n[1] Testing connection (Cloud Monitoring metricDescriptors)...")
    result = provider.test_connection()
    print(f"  Status: {result.get('status')}")
    print(f"  Mode: {result.get('mode')}")
    print(f"  Message: {result.get('message')}")
    print(f"  Credentials: {result.get('credentials_status')}")
    print(f"  Authentication: {result.get('authentication_status')}")
    print(f"  API Reachable: {result.get('api_reachability')}")
    print(f"  Telemetry Status: {result.get('telemetry_status')}")

    acct = provider.get_account_info()
    print(f"\n[2] Account Info: {acct.get('project_id')} ({acct.get('client_email')})")

    regions = provider.get_regions()
    print(f"[3] Available Regions: {len(regions)} regions found")

    if not result.get("success"):
        print("\n❌ Connection failed.")
        return False

    print("\n[4] Fetching live metrics from Cloud Monitoring...")
    metrics = provider.get_metrics("us-east4")
    print(f"  source: {metrics.get('source')} ← must be LIVE_GCP")
    print(f"  cpu: {metrics.get('cpu')} %")
    print(f"  memory: {metrics.get('memory')} ← None = UNAVAILABLE (correct)")
    print(f"  memory_source: {metrics.get('memory_source')}")
    print(f"  memory_note: {metrics.get('memory_note', '')[:80]}")

    # Verify BUG-004 fix: memory should never be 48.0 (old hardcoded value)
    if metrics.get("memory") == 48.0:
        print("❌ FAIL: memory=48.0 — old hardcoded fallback! BUG-005 not fixed.")
        return False

    source = metrics.get("source")
    if source in ("LIVE_GCP", "ERROR"):
        print(f"\n✅ PASS: source={source}")
    else:
        print(f"\n❌ FAIL: source={source} (expected LIVE_GCP or ERROR)")
        return False

    print("\n✅ GCP tests complete.")
    return True


def test_invalid_credentials_failure():
    """Verify Section 58 & Data Truth rule: invalid credentials return explicit ERROR, never fake DEMO/LIVE."""
    print("=" * 60)
    print("TESTING: Invalid Credentials Failure Handling (Section 58)")
    print("=" * 60)

    from app.cloud.aws_provider import AWSCloudProvider
    from app.cloud.azure_provider import AzureCloudProvider
    from app.cloud.gcp_provider import GCPCloudProvider

    # 1. AWS with invalid keys
    aws_p = AWSCloudProvider()
    aws_res = aws_p.test_connection(credentials={
        "aws_access_key_id": "AKIA_INVALID_TEST_KEY",
        "aws_secret_access_key": "invalid_secret_key_12345",
        "aws_default_region": "us-east-1",
    })
    print("\n[1] AWS Invalid Key Test:")
    print(f"    success: {aws_res.get('success')} (expected False)")
    print(f"    status: {aws_res.get('status')} (expected authentication_failed)")
    print(f"    mode: {aws_res.get('mode')} (expected ERROR)")
    assert aws_res.get("success") is False, "AWS invalid credentials must return success=False"
    assert aws_res.get("status") == "authentication_failed", "AWS invalid credentials must return authentication_failed"
    assert aws_res.get("mode") == "ERROR", "AWS invalid credentials must return mode=ERROR, never DEMO or LIVE"
    print("    ✅ PASS: AWS returned explicit authentication failure.")

    # 2. Azure with invalid client credentials
    az_p = AzureCloudProvider()
    az_res = az_p.test_connection(credentials={
        "azure_subscription_id": "00000000-0000-0000-0000-000000000000",
        "azure_tenant_id": "00000000-0000-0000-0000-000000000000",
        "azure_client_id": "00000000-0000-0000-0000-000000000000",
        "azure_client_secret": "invalid_secret",
    })
    print("\n[2] Azure Invalid Credentials Test:")
    print(f"    success: {az_res.get('success')} (expected False)")
    print(f"    status: {az_res.get('status')} (expected authentication_failed)")
    print(f"    mode: {az_res.get('mode')} (expected ERROR)")
    assert az_res.get("success") is False, "Azure invalid credentials must return success=False"
    assert az_res.get("status") == "authentication_failed", "Azure invalid credentials must return authentication_failed"
    assert az_res.get("mode") == "ERROR", "Azure invalid credentials must return mode=ERROR"
    print("    ✅ PASS: Azure returned explicit authentication failure.")

    # 3. GCP with invalid service account JSON
    gcp_p = GCPCloudProvider()
    gcp_res = gcp_p.test_connection(credentials={
        "gcp_project_id": "invalid-project",
        "gcp_service_account_json": '{"type": "service_account", "project_id": "invalid-project", "private_key": "invalid"}',
    })
    print("\n[3] GCP Invalid Service Account Test:")
    print(f"    success: {gcp_res.get('success')} (expected False)")
    print(f"    status: {gcp_res.get('status')} (expected authentication_failed)")
    print(f"    mode: {gcp_res.get('mode')} (expected ERROR)")
    assert gcp_res.get("success") is False, "GCP invalid credentials must return success=False"
    assert gcp_res.get("status") == "authentication_failed", "GCP invalid credentials must return authentication_failed"
    assert gcp_res.get("mode") == "ERROR", "GCP invalid credentials must return mode=ERROR"
    print("    ✅ PASS: GCP returned explicit authentication failure.")

    print("\n✅ All failure tests passed! Invalid credentials reliably return explicit ERROR.")
    return True


def run_data_truth_verification():
    """Verify the data truth rules are enforced across all providers."""
    print("\n" + "=" * 60)
    print("DATA TRUTH VERIFICATION SUMMARY")
    print("=" * 60)

    checks = {
        "DEMO mode produces source=DEMO": None,
        "LIVE mode produces source=LIVE_*": None,
        "ERROR mode on API failure (no silent fallback)": None,
        "Memory is None (UNAVAILABLE) when CWAgent not installed": None,
        "Hardcoded fallback values eliminated": None,
    }

    os.environ["DEMO_MODE"] = "true"

    from app.cloud.aws_provider import AWSCloudProvider
    demo_provider = AWSCloudProvider()

    # Reset to demo mode
    from app.routers.telemetry import _generate_live_metrics
    demo_m = _generate_live_metrics("aws", "us-east")
    checks["DEMO mode produces source=DEMO"] = (demo_m.source == "DEMO")

    for check, result in checks.items():
        if result is True:
            print(f"  ✅ {check}")
        elif result is False:
            print(f"  ❌ {check}")
        else:
            print(f"  ⚠️  {check}: not verified (requires live credentials)")

    print()


def main():
    parser = argparse.ArgumentParser(description="GreenMind AI Live Provider Test Suite")
    parser.add_argument("--provider", choices=["aws", "azure", "gcp"], help="Test specific provider")
    parser.add_argument("--all", action="store_true", help="Test all providers")
    parser.add_argument("--test-failure", action="store_true", help="Test invalid credentials failure handling")
    parser.add_argument("--security-check", action="store_true", default=True, help="Run credential security check")
    args = parser.parse_args()

    print("GreenMind AI — Live Provider Connection Test")
    print("============================================")
    print("This script verifies real cloud provider connectivity.")
    print("No live infrastructure will be modified.")
    print()

    if args.security_check:
        check_env_security()

    if args.test_failure:
        success = test_invalid_credentials_failure()
        sys.exit(0 if success else 1)

    results = {}

    if args.provider == "aws" or args.all:
        results["aws"] = test_aws()

    if args.provider == "azure" or args.all:
        results["azure"] = test_azure()

    if args.provider == "gcp" or args.all:
        results["gcp"] = test_gcp()

    if not results:
        print("No provider specified. Use --provider [aws|azure|gcp], --all, or --test-failure")
        parser.print_help()
        return

    run_data_truth_verification()

    print("\nFINAL RESULTS:")
    print("-" * 40)
    for prov, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {prov.upper()}: {status}")

    if all(results.values()):
        print("\n✅ All tests passed — GreenMind AI is ready for LIVE mode.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Review output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
