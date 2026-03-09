#!/usr/bin/env python3
"""
Full test for Tagger agent via Lambda
"""

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_db = _backend / "database"
if _db.exists() and str(_db) not in sys.path:
    sys.path.insert(0, str(_db))

import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

from src import Database

def test_tagger_lambda():
    """Test the Tagger agent via Lambda invocation"""
    
    db = Database()
    region = os.getenv("DEFAULT_AWS_REGION", "us-west-2")
    lambda_client = boto3.client("lambda", region_name=region)
    
    # Test instruments that need tagging
    test_instruments = [
        {"symbol": "ARKK", "name": "ARK Innovation ETF"},
        {"symbol": "SOFI", "name": "SoFi Technologies Inc"},
        {"symbol": "TSLA", "name": "Tesla Inc"}
    ]
    
    print("Testing Tagger Lambda")
    print("=" * 60)
    print(f"Region: {region}")
    print(f"Instruments to tag: {[i['symbol'] for i in test_instruments]}")
    
    # Invoke Lambda
    try:
        response = lambda_client.invoke(
            FunctionName="alex-tagger",
            InvocationType="RequestResponse",
            Payload=json.dumps({"instruments": test_instruments}),
        )
        
        raw = json.loads(response["Payload"].read())
        # Unwrap API-style response
        if "body" in raw and "statusCode" in raw:
            status_code = raw["statusCode"]
            body = raw["body"]
            body = json.loads(body) if isinstance(body, str) else body
        else:
            status_code = 200
            body = raw
        
        print(f"\nLambda status: {status_code}")
        print(f"Body: {json.dumps(body, indent=2)}")
        
        tagged = body.get("tagged", 0)
        errors = body.get("errors", [])
        
        if tagged == 0:
            print("\n⚠️  Agent returned 0 classifications (nothing written to DB).")
            if errors:
                print("   Errors from Lambda:", errors)
            print("   Check CloudWatch Logs for /aws/lambda/alex-tagger for Bedrock/agent errors.")
            print("=" * 60)
            return
        
        # Check database for updated instruments
        print("\n✅ Checking database for tagged instruments:")
        for inst in test_instruments:
            instrument = db.instruments.find_by_symbol(inst["symbol"])
            if instrument:
                if instrument.get("allocation_asset_class"):
                    print(f"  ✅ {inst['symbol']}: Tagged successfully")
                    print(f"     Asset: {instrument.get('allocation_asset_class')}")
                    print(f"     Regions: {instrument.get('allocation_regions')}")
                else:
                    print(f"  ❌ {inst['symbol']}: No allocations found")
            else:
                print(f"  ⚠️  {inst['symbol']}: Not found in database")
                
    except Exception as e:
        print(f"Error invoking Lambda: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    test_tagger_lambda()