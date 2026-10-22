from typing import Any
from bson import ObjectId


def objectid_to_str(v):
    return str(v) if isinstance(v, ObjectId) else v

def make_serializable(obj: Any) -> Any:
    """Recursively convert LangChain objects to JSON-serializable types."""
    if hasattr(obj, "model_dump"):
        return make_serializable(obj.model_dump())
    if hasattr(obj, "dict"):
        return make_serializable(obj.dict())
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    if hasattr(obj, "__str__"):
        return str(obj)
    return obj
