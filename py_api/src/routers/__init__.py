"""Router initializers.

Re-exports every sub-router so that ``main.py`` can import them in a
single line via ``from routers import …``.
"""

from .agent import router as agent_router
from .health import router as health_router
from .user import router as user_router
from .yolo import router as yolo_router
