"""
Briefer Agent - generates short, high-signal briefs.
"""

import os
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple

from agents import function_tool, RunContextWrapper
from agents.extensions.models.litellm_model import LitellmModel

from templates import build_briefer_task
from tools import fetch_market_overview, fetch_ticker_quotes

# Disable litellm background logger to avoid Lambda event loop warnings
os.environ["LITELLM_DISABLE_BACKGROUND_LOGGER"] = "true"

logger = logging.getLogger()


@dataclass
class BrieferContext:
    """Context for the Briefer agent."""

    job_id: Optional[str]
    mode: str
    interests: Optional[str]
    portfolio_data: Optional[Dict[str, Any]] = None


def create_agent(
    job_id: Optional[str],
    mode: str,
    interests: Optional[str],
    portfolio_data: Optional[Dict[str, Any]],
) -> Tuple[LitellmModel, List, str, BrieferContext]:
    """Create the Briefer agent."""

    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")
    os.environ["AWS_REGION_NAME"] = bedrock_region

    model = LitellmModel(model=f"bedrock/{model_id}")

    context = BrieferContext(
        job_id=job_id,
        mode=mode,
        interests=interests,
        portfolio_data=portfolio_data,
    )

    # HTTP-based tools for lightweight market data lookup
    tools: List = [fetch_market_overview, fetch_ticker_quotes]

    task = build_briefer_task(mode, interests, None)
    return model, tools, task, context

