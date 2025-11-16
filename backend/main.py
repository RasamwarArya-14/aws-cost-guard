from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Health(BaseModel):
    status: str

@app.get("/")
def read_root():
    return {"app": "aws-cost-guard", "status": "ok"}

@app.get("/health")
def health():
    return Health(status="ok")
