"""
Briefer Agent Lambda Handler
"""

import os
import json
import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from agents import Agent, Runner, trace

from src import Database
from guardrails import sanitize_user_input, truncate_response
from audit import AuditLogger

from agent import create_agent
from observability import observe

logger = logging.getLogger()
logger.setLevel(logging.INFO)

db = Database()


async def run_briefer(job_id: Optional[str], mode: str, interests: Optional[str]) -> Dict[str, Any]:
    """Run the briefer agent."""
    portfolio_data: Optional[Dict[str, Any]] = None

    if job_id:
        job = db.jobs.find_by_id(job_id)
        if job:
            user_id = job["clerk_user_id"]
            user = db.users.find_by_clerk_id(user_id)
            accounts = db.accounts.find_by_user(user_id)

            portfolio_data = {
                "user_id": user_id,
                "job_id": job_id,
                "years_until_retirement": user.get("years_until_retirement", 30) if user else 30,
                "accounts": [],
            }

            for account in accounts:
                account_data = {
                    "id": account["id"],
                    "name": account["account_name"],
                    "type": account.get("account_type", "investment"),
                    "cash_balance": float(account.get("cash_balance", 0)),
                    "positions": [],
                }

                positions = db.positions.find_by_account(account["id"])
                for position in positions:
                    instrument = db.instruments.find_by_symbol(position["symbol"])
                    if instrument:
                        account_data["positions"].append(
                            {
                                "symbol": position["symbol"],
                                "quantity": float(position["quantity"]),
                                "instrument": instrument,
                            }
                        )

                portfolio_data["accounts"].append(account_data)

            logger.info(f"Briefer: Loaded {len(portfolio_data['accounts'])} accounts with positions")

    model, tools, task, context = create_agent(job_id, mode, interests, portfolio_data)

    with trace("Briefer Agent"):
        # Briefer runs as a lightweight Lambda using HTTP tools only (no MCP/Playwright).
        agent = Agent(
            name="Briefer",
            instructions=task,
            model=model,
            tools=tools,
        )
        result = await Runner.run(agent, input="Generate brief.", max_turns=10)

    # Full brief for UI
    full_text = result.final_output or ""
    # Shorter summary for storage and embeddings (guard against extreme length)
    summary_text = truncate_response(full_text, max_length=4000)

    # Persist into jobs table similarly to reporter (store the shorter summary)
    if job_id:
        payload = {
            "content": summary_text,
            "generated_at": datetime.utcnow().isoformat(),
            "agent": "briefer",
            "mode": mode,
        }
        db.jobs.update_report(job_id, payload)

    # Store brief into S3 Vectors bucket as an additional research document
    try:
        import boto3

        bucket = os.getenv("VECTOR_BUCKET")
        index_name = os.getenv("BRIEFER_INDEX_NAME", "financial-research")
        if bucket and summary_text:
            # Get embedding via SageMaker like ingest_s3vectors
            sagemaker_endpoint = os.getenv("SAGEMAKER_ENDPOINT", "alex-embedding-endpoint")
            sagemaker = boto3.client(
                "sagemaker-runtime", region_name=os.getenv("DEFAULT_AWS_REGION", "us-east-1")
            )
            # Further truncate for embeddings to stay within model token limits
            embedding_text = summary_text[:2000]

            resp = sagemaker.invoke_endpoint(
                EndpointName=sagemaker_endpoint,
                ContentType="application/json",
                Body=json.dumps({"inputs": embedding_text}),
            )
            result_body = json.loads(resp["Body"].read().decode())
            if isinstance(result_body, list) and result_body:
                if isinstance(result_body[0], list) and result_body[0]:
                    embedding = result_body[0][0] if isinstance(result_body[0][0], list) else result_body[0]
                else:
                    embedding = result_body[0]
            else:
                embedding = result_body

            s3v = boto3.client(
                "s3vectors", region_name=os.getenv("DEFAULT_AWS_REGION", "us-east-1")
            )
            import uuid as _uuid

            vector_id = str(_uuid.uuid4())

            # Truncate metadata text to stay under 2048 bytes
            metadata_bytes = summary_text.encode("utf-8")
            if len(metadata_bytes) > 1900:
                metadata_text = metadata_bytes[:1900].decode("utf-8", errors="ignore")
            else:
                metadata_text = summary_text
            s3v.put_vectors(
                vectorBucketName=bucket,
                indexName=index_name,
                vectors=[
                    {
                        "key": vector_id,
                        "data": {"float32": embedding},
                        "metadata": {
                            "text": metadata_text,
                            "timestamp": datetime.utcnow().isoformat(),
                            "source": "briefer",
                            "mode": mode,
                            "job_id": job_id or "",
                        },
                    }
                ],
            )
    except Exception as e:
        logger.warning(f"Briefer: failed to store brief in S3 Vectors: {e}")

    # Always return the full brief to the caller UI
    return {"success": True, "content": full_text}


def lambda_handler(event, context):
    """
    Expected event:
    {
      "mode": "market_overview" | "user_focus",
      "interests": "...",  # optional
      "job_id": "uuid"     # optional
    }
    """
    with observe():
        try:
            if isinstance(event, str):
                event = json.loads(event)

            mode = event.get("mode", "market_overview")
            if mode not in ("market_overview", "user_focus"):
                mode = "market_overview"

            interests = event.get("interests")
            if interests:
                interests = sanitize_user_input(str(interests))

            job_id = event.get("job_id")

            start_time = time.perf_counter()
            result = asyncio.run(run_briefer(job_id, mode, interests))
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            AuditLogger.log_ai_decision(
                agent_name="briefer",
                job_id=job_id or "none",
                input_data={"mode": mode, "has_interests": bool(interests)},
                output_data=result,
                model_used=os.getenv("BEDROCK_MODEL_ID", ""),
                duration_ms=duration_ms,
            )

            return {"statusCode": 200, "body": json.dumps(result)}
        except Exception as e:
            logger.error(f"Error in Briefer: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "body": json.dumps({"success": False, "error": str(e)}),
            }

