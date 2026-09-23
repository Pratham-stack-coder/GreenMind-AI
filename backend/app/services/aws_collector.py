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
                    name_tag = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), inst["InstanceId"])
                    instances.append({
                        "id": inst["InstanceId"],
                        "name": name_tag,
                        "type": inst.get("InstanceType", "t3.medium"),
                        "state": inst.get("State", {}).get("Name", "running"),
                        "launch_time": str(inst.get("LaunchTime", "")),
                        "private_ip": inst.get("PrivateIpAddress", ""),
                        "public_ip": inst.get("PublicIpAddress", ""),
                    })
            return instances
        except Exception as e:
            logger.warning(f"Error querying EC2 describe_instances: {e}")
            return []
