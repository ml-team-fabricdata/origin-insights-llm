def format(result: dict) -> dict:
    return {
        "ok": True,
        "source": result.get("type"),
        "result": result.get("data")
    }