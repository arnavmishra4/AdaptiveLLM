from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import requests
import json
from Router import route
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

app = FastAPI()

proxy_client = OpenAI(
    base_url='http://litellm-proxy:4000',
    api_key="sk-12112002"
)

SEMANTIC_CACHE_URL = "http://semantic-cache:8090"
TOOLS_SERVER_URL = "http://tools:8095/mcp"


class ChatRequest(BaseModel):
    text: str
    history: list[dict] = []


# ---------------------------------------------------------
# MCP client helpers
# ---------------------------------------------------------

async def get_mcp_tools_as_openai_schema():
    async with streamable_http_client(TOOLS_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await session.list_tools()

    openai_tools = []
    for t in mcp_tools.tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema,
            },
        })
    return openai_tools


async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    async with streamable_http_client(TOOLS_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result.content[0].text if result.content else ""
# ---------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------

@app.post("/chat")
async def chat(req: ChatRequest):
    # 1. check semantic cache
    check_resp = requests.post(f"{SEMANTIC_CACHE_URL}/check", json={"text": req.text})
    cached = check_resp.json().get("cached")
    if cached:
        return {"reply": cached, "model_used": "cache"}

    # 2. classify which model to use
    model_choice = route(req.text)
    messages = req.history + [{"role": "user", "content": req.text}]

    # 3. fetch available tools from the MCP server
    tools = await get_mcp_tools_as_openai_schema()

    # 4. call the model, giving it the option to use tools
    response = proxy_client.chat.completions.create(
        model=model_choice,
        messages=messages,
        tools=tools,
    )
    message = response.choices[0].message

    # 5. if the model wants to call a tool, execute it and loop back
    while message.tool_calls:
        messages.append(message.model_dump())
        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            result = await call_mcp_tool(tool_call.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        response = proxy_client.chat.completions.create(
            model=model_choice,
            messages=messages,
            tools=tools,
        )
        message = response.choices[0].message

    assistant_message = message.content

    # 6. save to cache
    requests.post(f"{SEMANTIC_CACHE_URL}/save", json={
        "prompt": req.text,
        "response": assistant_message
    })

    return {
        "reply": assistant_message,
        "model_used": model_choice
    }


@app.get("/health")
def health():
    return {"status": "ok"}