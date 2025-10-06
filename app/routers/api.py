from fastapi import APIRouter
from pydantic import BaseModel
from app.supervisor import handle_query

router = APIRouter()

class QueryRequest(BaseModel):
    prompt: str | None = None
    query: str | None = None
    user_id: str | None = None
    thread_id: str | None = None
    lang: str | None = None

    def text(self) -> str:
        return (self.prompt or self.query or "").strip()

@router.post("/query")
async def query(req: QueryRequest):
    text = req.text()
    return handle_query(
        text,
        user_id=req.user_id,
        thread_id=req.thread_id,
        lang=req.lang,
    )
