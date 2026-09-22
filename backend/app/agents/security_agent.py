"""
Security Agent — detects over-permissioned roles, public exposure,
unencrypted storage, and misconfigured security groups (rule-based, demo mode).
"""

from __future__ import annotations

from datetime import datetime

from ..schemas import CloudMetrics, RecommendationItem


def analyze(metrics: CloudMetrics, context: dict | None = None) -> dict:
    findings: list[str] = []
    recs: list[RecommendationItem] = []
    score = 100

    ctx = context or {}
    region = metrics.region
    provider = metrics.provider

    # ── Public S3 / Blob storage exposure (demo heuristic) ───────────────────
    # In real mode this would call provider SDK to enumerate bucket ACLs
    has_public_storage = ctx.get("public_storage_buckets", 0)
    if has_public_storage:
        score -= 40
        findings.append(f"{has_public_storage} public storage bucket(s) detected")
        recs.append(RecommendationItem(
            id="sec-001",
            category="security",
            priority="critical",
            title="Public storage buckets detected — immediate remediation required",
            description=f"{has_public_storage} bucket(s) are publicly accessible. "
                        "Any sensitive data they contain is exposed to the internet.",
            impact_summary="Data breach risk — make buckets private immediately",
            estimated_monthly_savings_usd=0,
            effort="low",
            action="block_public_storage_access",
            evidence=[f"Public buckets: {has_public_storage}"],
            confidence=0.99,
        ))

    # ── Open security groups (demo: flag if no context provided) ─────────────
    open_ports = ctx.get("open_security_group_ports", ["0.0.0.0/0:22", "0.0.0.0/0:3389"])
    critical_open = [p for p in open_ports if "0.0.0.0/0" in p]
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
    unencrypted_volumes = ctx.get("unencrypted_volumes", 0)
    if unencrypted_volumes:
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
    admin_users = ctx.get("admin_users_without_mfa", 0)
    if admin_users:
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
    if not findings:
        findings.append("No critical security issues detected in demo mode — "
                        "connect live provider for full IAM/network audit")
        score -= 5  # small penalty since we can't fully verify in demo

    return {
        "agent": "SecurityAgent",
        "status": "completed",
        "findings": findings,
        "recommendations": recs,
        "score": max(0, min(100, score)),
        "analyzed_at": datetime.utcnow().isoformat(),
    }
