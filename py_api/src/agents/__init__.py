from functools import lru_cache
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langgraph.checkpoint.mongodb import MongoDBSaver
import os
from .ua_agent import (
    system_prompt as ua_agent_system_prompt,
    tools as ua_agent_tools,
    Context as ua_agent_context,
    State as ua_agent_State,
)
from pymongo import MongoClient


agent_map = {
    "agent_a": {
        "system_prompt": ua_agent_system_prompt,
        "model": ChatOpenAI(
            model="falcon-llm",
            base_url=os.getenv("LLM_URL"),
            api_key=os.getenv("LLM_API_KEY"),
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

@lru_cache()
def get_agent(agent_name: str, mongo_client: MongoClient):
    
    agent_conf = agent_map[agent_name]
    skill_dir = os.path.join(os.path.dirname(__file__), "skills", agent_name)

    return create_deep_agent(
        system_prompt=agent_conf["system_prompt"],
        model=agent_conf["model"], 
        checkpointer=MongoDBSaver(client=mongo_client, db_name=os.getenv("MONGO_DB_NAME", "growx_agent"), ttl=30*24*60*60),
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
                mode="deny"
            )
        ],
    )
