"""
Security Agent — detects over-permissioned roles, public exposure,
unencrypted storage, and misconfigured security groups (rule-based, demo mode).
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..schemas import CloudMetrics, RecommendationItem


def analyze(metrics: CloudMetrics, context: dict | None = None) -> dict:
    findings: list[str] = []
    recs: list[RecommendationItem] = []
    score = 100

    ctx = context if isinstance(context, dict) else {}
    supplied_checks: set[str] = set()

    def observed_count(key: str) -> int | None:
        value = ctx.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            supplied_checks.add(key)
            return value
        return None

    public_buckets = observed_count("public_storage_buckets")
    unencrypted_volumes = observed_count("unencrypted_volumes")
    admin_users = observed_count("admin_users_without_mfa")
    raw_ports = ctx.get("open_security_group_ports")
    open_ports: list[str] = []
    if isinstance(raw_ports, (list, tuple, set)) and all(isinstance(port, str) for port in raw_ports):
        supplied_checks.add("open_security_group_ports")
        open_ports = list(raw_ports)
    critical_open = [port for port in open_ports if "0.0.0.0/0" in port]
    # ── Public S3 / Blob storage exposure (demo heuristic) ───────────────────
    # In real mode this would call provider SDK to enumerate bucket ACLs
    if public_buckets is not None and public_buckets > 0:
        score -= 40
        findings.append(f"{public_buckets} public storage bucket(s) detected")
        recs.append(RecommendationItem(
            id="sec-001",
            category="security",
            priority="critical",
            title="Public storage buckets detected — immediate remediation required",
            description=f"{public_buckets} bucket(s) are publicly accessible. "
                        "Any sensitive data they contain is exposed to the internet.",
            impact_summary="Data breach risk — make buckets private immediately",
            estimated_monthly_savings_usd=0,
            effort="low",
            action="block_public_storage_access",
            evidence=[f"Public buckets: {public_buckets}"],
            confidence=0.99,
        ))

    # ── Open security groups (demo: flag if no context provided) ─────────────
    if critical_open:
        score -= 25
        findings.append(f"Security group exposes {len(critical_open)} port(s) to 0.0.0.0/0")
        recs.append(RecommendationItem(
            id="sec-002",
            category="security",
            priority="high",
            title="Restrict SSH/RDP access to specific IP ranges",
            description=f"Ports {', '.join(critical_open)} are open to the entire internet. "
                        "Restrict to known IP ranges or use a VPN/bastion host.",
            impact_summary="Reduce attack surface — close public SSH/RDP",
            estimated_monthly_savings_usd=0,
            effort="low",
            action="restrict_security_group_ingress",
            evidence=[f"Open ports: {critical_open}"],
            confidence=0.95,
        ))

    # ── Encryption at rest ────────────────────────────────────────────────────
    if unencrypted_volumes is not None and unencrypted_volumes > 0:
        score -= 20
        findings.append(f"{unencrypted_volumes} unencrypted storage volume(s) found")
        recs.append(RecommendationItem(
            id="sec-003",
            category="security",
            priority="high",
            title="Enable encryption at rest for all storage volumes",
            description=f"{unencrypted_volumes} volume(s) lack encryption. "
                        "Enable EBS/disk encryption to protect data at rest.",
            impact_summary="Compliance risk — encrypt volumes to meet PCI/HIPAA/SOC2",
            estimated_monthly_savings_usd=0,
            effort="medium",
            action="enable_encryption_at_rest",
            evidence=[f"Unencrypted volumes: {unencrypted_volumes}"],
            confidence=0.93,
        ))

    # ── IAM / RBAC over-permissions ───────────────────────────────────────────
    if admin_users is not None and admin_users > 0:
        score -= 20
        findings.append(f"{admin_users} admin user(s) without MFA")
        recs.append(RecommendationItem(
            id="sec-004",
            category="security",
            priority="critical",
            title="Enforce MFA for all admin accounts",
            description=f"{admin_users} administrator account(s) do not have MFA enabled. "
                        "Admin account compromise without MFA is a leading cause of cloud breaches.",
            impact_summary="Account takeover prevention — enforce MFA now",
            estimated_monthly_savings_usd=0,
            effort="low",
            action="enforce_mfa",
            evidence=[f"Admin users without MFA: {admin_users}"],
            confidence=0.98,
        ))

    # ── Demo default security finding ─────────────────────────────────────────
    if not supplied_checks:
        findings.append(
            "Security posture data is unavailable; no security risks were inferred from telemetry."
        )
        status = "skipped"
    elif not findings:
        findings.append(
            "No issues were found in supplied posture checks; other security checks remain unverified."
        )
        status = "completed"
    else:
        status = "completed"

    return {
        "agent": "SecurityAgent",
        "status": status,
        "findings": findings,
        "recommendations": recs,
        "score": max(0, min(100, score)),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
