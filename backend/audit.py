"""
Audit trail for AI decisions (8_enterprise guide Section 5).
Logs to CloudWatch for compliance and long-term retention.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class AuditLogger:
    """Comprehensive audit log for all AI decisions."""

    @staticmethod
    def log_ai_decision(
        agent_name: str,
        job_id: str,
        input_data: Dict[str, Any],
        output_data: Any,
        model_used: str,
        duration_ms: int,
        compliance_check: str = "PASS",
    ) -> Dict[str, Any]:
        """
        Log an AI decision for compliance and auditability.
        Store in CloudWatch via structured JSON log.
        """
        try:
            input_str = json.dumps(input_data, sort_keys=True, default=str)
            input_hash = hashlib.sha256(input_str.encode()).hexdigest()
        except (TypeError, ValueError):
            input_hash = "(unserializable)"

        try:
            output_str = json.dumps(output_data, default=str) if output_data is not None else ""
            output_size = len(output_str.encode())
            output_type = type(output_data).__name__
        except (TypeError, ValueError):
            output_size = 0
            output_type = "unknown"

        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "AI_DECISION",
            "agent": agent_name,
            "job_id": job_id,
            "model": model_used,
            "input_hash": input_hash,
            "output_summary": {
                "type": output_type,
                "size_bytes": output_size,
            },
            "duration_ms": duration_ms,
            "compliance_check": compliance_check,
        }

        logger.info(json.dumps(audit_entry))
        return audit_entry
