from fastapi import APIRouter

router = APIRouter()

@router.get("/query/ping")
def ping():
    return {"ok": True}