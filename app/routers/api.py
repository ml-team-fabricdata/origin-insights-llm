from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class QueryRequest(BaseModel):
    prompt: str

@router.post("/query")
async def query(req: QueryRequest):
    # TODO: aquí luego enchufamos tu lógica real (LLM/Bedrock/Aurora)
    return {"ok": True, "answer": f"Echo: {req.prompt}"}
