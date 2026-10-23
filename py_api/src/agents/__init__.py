"""AI agent initialisation.

Builds LangGraph / DeepAgents instances from the registry in
:py:data:`agent_map`.  Called once during application startup.
"""

import logging
import os
from pymongo import MongoClient

from .ua_agent import (
    system_prompt as ua_agent_system_prompt,
    tools as ua_agent_tools,
    Context as ua_agent_context,
    State as ua_agent_State,
)
from agents.tools import load_dwh_docs_mcp
from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.graph.state import CompiledStateGraph
from config import LLM_API_KEY, LLM_URL, MONGO_DB_NAME

logger = logging.getLogger("pyapi")

agent_map: dict[str, dict] = {
    "ua_agent": {
        "system_prompt": ua_agent_system_prompt,
        "model": ChatOpenAI(
            model="falcon-llm",
            base_url=LLM_URL,
            api_key=LLM_API_KEY,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": True},
                "top_k": 20,
            },
            temperature=0.7,
            top_p=0.8,
            presence_penalty=1.5,
        ),
        "tools": ua_agent_tools,
        "context_schema": ua_agent_context,
        "state_schema": ua_agent_State,
    },
}


async def init_agent(agent_name: str, mongo_client: MongoClient) -> CompiledStateGraph:
    """Build and return an agent instance.  Intended for startup use only."""
    logger.info("agent_init_start", extra={"agent_name": agent_name})
    try:
        agent_conf = agent_map[agent_name]
        skill_dir = os.path.join(os.path.dirname(__file__), "skills", agent_name)

        agent = create_deep_agent(
            system_prompt=agent_conf["system_prompt"],
            model=agent_conf["model"],
            checkpointer=MongoDBSaver(
                client=mongo_client,
                db_name=os.getenv("MONGO_DB_NAME", MONGO_DB_NAME),
                ttl=30 * 24 * 60 * 60,
            ),
            backend=CompositeBackend(
                default=StateBackend(),
                routes={
                    "/skills/": FilesystemBackend(
                        root_dir=skill_dir,
                        virtual_mode=True,
                    ),
                },
            ),
            skills=["/skills/"],
            tools=agent_conf["tools"],
            context_schema=agent_conf["context_schema"],
            state_schema=agent_conf["state_schema"],
            permissions=[
                FilesystemPermission(
                    operations=["write"],
                    paths=["/skills/"],
                    mode="deny",
                )
            ],
        )
        logger.info("agent_init_success", extra={"agent_name": agent_name})
        return agent
    except Exception as exc:
        logger.error(
            "agent_init_error",
            extra={"agent_name": agent_name, "error": str(exc)},
            exc_info=True,
        )
        raise
