from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta
import os

app = FastAPI(title="aws-cost-guard")

# Allow frontend dev server to call backend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Health(BaseModel):
    status: str

@app.get("/")
def read_root():
    return {"app": "aws-cost-guard", "status": "ok"}

@app.get("/health")
def health():
    return Health(status="ok")

def get_ce_client():
    # boto3 will pick up credentials from AWS CLI configuration or env vars
    return boto3.client("ce", region_name=os.getenv("AWS_REGION", "us-east-1"))

@app.get("/costs/last7")
def costs_last7():
    """
    Returns daily cost for the last 7 days using the Cost Explorer API.
    """
    try:
        ce = get_ce_client()

        # last 7 days: AWS CE expects YYYY-MM-DD
        end = datetime.utcnow().date() - timedelta(days=1)   # end = yesterday (complete day)
        start = end - timedelta(days=6)                     # 7 days total
        time_period = {"Start": start.isoformat(), "End": (end + timedelta(days=1)).isoformat()}

        response = ce.get_cost_and_usage(
            TimePeriod=time_period,
            Granularity="DAILY",
            Metrics=["UnblendedCost"]
        )

        # Parse results
        results = []
        for day in response.get("ResultsByTime", []):
            date = day.get("TimePeriod", {}).get("Start")
            amount = "0"
            if "Total" in day and "UnblendedCost" in day["Total"]:
                amount = day["Total"]["UnblendedCost"].get("Amount", "0")
            results.append({"date": date, "amount": amount})

        return {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "results_by_date": results
        }

    except (BotoCoreError, ClientError) as e:
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
