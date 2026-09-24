"""
AWS CloudWatch Collector Service.
Uses boto3 to collect CloudWatch metrics for EC2 instances.

CloudWatch Standard Metrics provided without agent:
- CPUUtilization (%)
- NetworkIn / NetworkOut (Bytes)
- DiskReadBytes / DiskWriteBytes

NOTE ON MEMORY & DISK METRICS:
Standard AWS CloudWatch does NOT provide OS-level Memory utilization or Disk space by default.
Retrieving Memory % or Storage % requires the AWS CloudWatch Agent (CWAgent namespace)
configured on the EC2 instances. If the agent is not installed, GreenMind AI transparently
notes the metric status as estimated/simulated or requires CloudWatch Agent configuration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AWSCollector:
    """Collects real-time metrics from AWS CloudWatch when credentials are provided."""

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self._cw_client = None
        self._ec2_client = None
        self._ce_client = None  # AWS Cost Explorer (requires ce:GetCostAndUsage)
        self.is_configured = bool(
            settings.aws_access_key_id and settings.aws_secret_access_key
        )
        if self.is_configured:
            try:
                import boto3

                session = boto3.Session(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_default_region or self.region,
                )
                self._cw_client = session.client("cloudwatch")
                self._ec2_client = session.client("ec2")
                # Cost Explorer is global (us-east-1) — always use that region
                self._ce_client = session.client("ce", region_name="us-east-1")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS boto3 clients: {e}")
                self.is_configured = False

    def collect_cpu_utilization(self, instance_id: str | None = None) -> float | None:
        """Collect average EC2 CPUUtilization over the last 15 minutes."""
        if not self._cw_client:
            return None

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=15)

        dimensions = []
        if instance_id:
            dimensions.append({"Name": "InstanceId", "Value": instance_id})

        try:
            resp = self._cw_client.get_metric_data(
                MetricDataQueries=[
                    {
                        "Id": "cpu",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/EC2",
                                "MetricName": "CPUUtilization",
                                "Dimensions": dimensions,
                            },
                            "Period": 300,
                            "Stat": "Average",
                        },
                        "ReturnData": True,
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
            )
            values = resp.get("MetricDataResults", [{}])[0].get("Values", [])
            if values:
                return round(float(values[0]), 2)
        except Exception as e:
            logger.warning(f"Error reading AWS CloudWatch CPU: {e}")
        return None

    def collect_network_mbps(self, instance_id: str | None = None) -> float | None:
        """Collect NetworkIn + NetworkOut rate converted to Mbps."""
        if not self._cw_client:
            return None

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=15)
        dimensions = []
        if instance_id:
            dimensions.append({"Name": "InstanceId", "Value": instance_id})

        try:
            resp = self._cw_client.get_metric_data(
                MetricDataQueries=[
                    {
                        "Id": "net_in",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/EC2",
                                "MetricName": "NetworkIn",
                                "Dimensions": dimensions,
                            },
                            "Period": 300,
                            "Stat": "Average",
                        },
                        "ReturnData": True,
                    },
                    {
                        "Id": "net_out",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/EC2",
                                "MetricName": "NetworkOut",
                                "Dimensions": dimensions,
                            },
                            "Period": 300,
                            "Stat": "Average",
                        },
                        "ReturnData": True,
                    },
                ],
                StartTime=start_time,
                EndTime=end_time,
            )
            results = {r["Id"]: r.get("Values", []) for r in resp.get("MetricDataResults", [])}
            net_in_bytes = results.get("net_in", [0])[0] if results.get("net_in") else 0
            net_out_bytes = results.get("net_out", [0])[0] if results.get("net_out") else 0
            total_bytes_per_sec = (net_in_bytes + net_out_bytes) / 300.0
            mbps = (total_bytes_per_sec * 8) / (1024 * 1024)
            return round(mbps, 2)
        except Exception as e:
            logger.warning(f"Error reading AWS CloudWatch Network: {e}")
        return None

    def collect_memory_utilization(self, instance_id: str | None = None) -> tuple[float | None, str]:
        """
        Attempts to query CloudWatch Agent CWAgent namespace (mem_used_percent).
        Returns (utilization_or_none, note_string).
        """
        if not self._cw_client:
            return None, "AWS credentials not configured"

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=15)
        dimensions = []
        if instance_id:
            dimensions.append({"Name": "InstanceId", "Value": instance_id})

        try:
            resp = self._cw_client.get_metric_data(
                MetricDataQueries=[
                    {
                        "Id": "mem",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "CWAgent",
                                "MetricName": "mem_used_percent",
                                "Dimensions": dimensions,
                            },
                            "Period": 300,
                            "Stat": "Average",
                        },
                        "ReturnData": True,
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
            )
            values = resp.get("MetricDataResults", [{}])[0].get("Values", [])
            if values:
                return round(float(values[0]), 2), "Live CWAgent metric"
        except Exception:
            pass

        return None, "Standard CloudWatch does not supply EC2 memory; install CWAgent for OS-level metrics."

    def list_ec2_instances(self) -> list[dict[str, Any]]:
        """List live EC2 instances if client is configured."""
        if not self._ec2_client:
            return []

        try:
            resp = self._ec2_client.describe_instances()
            instances = []
            for res in resp.get("Reservations", []):
                for inst in res.get("Instances", []):
                    tags = inst.get("Tags", [])
                    name_tag = next((t["Value"] for t in tags if t["Key"] == "Name"), inst["InstanceId"])
                    instances.append({
                        "id": inst["InstanceId"],
                        "name": name_tag,
                        "type": inst.get("InstanceType", "t3.medium"),
                        "state": inst.get("State", {}).get("Name", "running"),
                        "launch_time": str(inst.get("LaunchTime", "")),
                        "private_ip": inst.get("PrivateIpAddress", ""),
                        "public_ip": inst.get("PublicIpAddress", ""),
                        "tags": tags,  # raw [{"Key": ..., "Value": ...}] list
                    })
            return instances
        except Exception as e:
            logger.warning(f"Error querying EC2 describe_instances: {e}")
            return []

    def collect_daily_cost(self) -> float | None:
        """Fetch yesterday's total AWS cost via Cost Explorer.

        Returns the total USD cost for yesterday, or None if:
        - No Cost Explorer client (no credentials)
        - Missing ce:GetCostAndUsage permission
        - Any API error

        This method NEVER raises — always returns None on any failure.
        """
        if not self._ce_client:
            return None

        from datetime import date, timedelta
        end = date.today()
        start = end - timedelta(days=1)

        try:
            resp = self._ce_client.get_cost_and_usage(
                TimePeriod={"Start": str(start), "End": str(end)},
                Granularity="DAILY",
                Metrics=["AmortizedCost"],
            )
            results = resp.get("ResultsByTime", [])
            if results:
                total = float(results[0]["Total"]["AmortizedCost"]["Amount"])
                return round(total, 4)
            return 0.0
        except Exception as e:
            logger.warning(f"AWS Cost Explorer query failed (this is OK if no ce permission): {type(e).__name__}: {e}")
            return None

    def collect_cost_explorer(self, days: int = 7) -> dict[str, Any] | None:
        """Fetch N-day cost breakdown via Cost Explorer with service-level granularity.

        Returns dict with total_usd and top_services, or None on any failure.
        Requires ce:GetCostAndUsage with GROUP_BY Service.
        """
        if not self._ce_client:
            return None

        from datetime import date, timedelta
        end = date.today()
        start = end - timedelta(days=days)

        try:
            resp = self._ce_client.get_cost_and_usage(
                TimePeriod={"Start": str(start), "End": str(end)},
                Granularity="MONTHLY",
                Metrics=["AmortizedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )

            total = 0.0
            top_services: list[dict[str, Any]] = []
            for period in resp.get("ResultsByTime", []):
                for group in period.get("Groups", []):
                    service_name = group["Keys"][0]
                    amount = float(group["Metrics"]["AmortizedCost"]["Amount"])
                    total += amount
                    top_services.append({"service": service_name, "cost_usd": round(amount, 4), "source": "LIVE_AWS"})

            # Sort by cost desc, keep top 10
            top_services = sorted(top_services, key=lambda x: -x["cost_usd"])[:10]
            return {"total_usd": round(total, 4), "top_services": top_services}
        except Exception as e:
            logger.warning(f"AWS Cost Explorer breakdown failed: {type(e).__name__}: {e}")
            return None


    def test_connection(
        self,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region_name: str | None = None,
        session_token: str | None = None,
    ) -> dict[str, Any]:
        """Test AWS credentials and connectivity using STS and CloudWatch read calls."""
        ak = access_key_id or settings.aws_access_key_id
        sk = secret_access_key or settings.aws_secret_access_key
        rg = region_name or settings.aws_default_region or self.region

        if not (ak and sk):
            return {
                "success": False,
                "status": "not_configured",
                "mode": "DEMO",
                "message": "AWS credentials not provided. Running in Demo mode.",
                "details": {"region": rg},
                "last_tested": datetime.now(timezone.utc).isoformat(),
            }

        try:
            import boto3
            from botocore.exceptions import ClientError, EndpointConnectionError

            session = boto3.Session(
                aws_access_key_id=ak,
                aws_secret_access_key=sk,
                aws_session_token=session_token,
                region_name=rg,
            )
            sts = session.client("sts")
            caller = sts.get_caller_identity()
            account = caller.get("Account", "unknown")
            arn = caller.get("Arn", "")
            masked_arn = arn[:20] + "..." if len(arn) > 20 else arn

            cw = session.client("cloudwatch")
            cw.list_metrics(Namespace="AWS/EC2")

            return {
                "success": True,
                "status": "connected",
                "mode": "LIVE",
                "message": f"Successfully authenticated with AWS Account {account} ({rg}).",
                "details": {
                    "account_id": account,
                    "region": rg,
                    "arn": masked_arn,
                },
                "last_tested": datetime.now(timezone.utc).isoformat(),
            }

        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "ClientError")
            msg = e.response.get("Error", {}).get("Message", str(e))
            if code in ["InvalidClientTokenId", "AuthFailure", "SignatureDoesNotMatch", "UnrecognizedClientException"]:
                status = "authentication_failed"
                user_msg = f"AWS authentication failed: {code}."
            elif code in ["AccessDenied", "UnauthorizedOperation", "AccessDeniedException"]:
                status = "permission_denied"
                user_msg = f"AWS credentials valid, but missing required read permissions: {code}."
            else:
                status = "service_unavailable"
                user_msg = f"AWS service error ({code}): {msg}"

            return {
                "success": False,
                "status": status,
                "mode": "DEMO",
                "message": user_msg,
                "details": {"code": code, "region": rg},
                "last_tested": datetime.now(timezone.utc).isoformat(),
            }
        except EndpointConnectionError:
            return {
                "success": False,
                "status": "service_unavailable",
                "mode": "DEMO",
                "message": f"Could not connect to AWS endpoint in region {rg}. Check network or region.",
                "details": {"region": rg},
                "last_tested": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "status": "service_unavailable",
                "mode": "DEMO",
                "message": f"Unexpected error testing AWS connection: {type(e).__name__}",
                "details": {"error": str(e)[:100]},
                "last_tested": datetime.now(timezone.utc).isoformat(),
            }

