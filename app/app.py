from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from runner import run_validation

app = FastAPI()

class ValidateRequest(BaseModel):
    declaration_type: str
    xml: str

@app.post("/validate")
def validate(req: ValidateRequest):
    try:
        result = run_validation(req.declaration_type, req.xml)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
