---
name: langgraph-agent
description: >-
  Comprehensive guide and production patterns for building LangGraph agents with
  external tool calling. Covers StateGraph workflows, Pydantic v2 @tool definitions,
  ToolNode integration, conditional edge routing, memory checkpointers (MemorySaver,
  AsyncPostgresSaver), human-in-the-loop (HITL) approval breakpoints, token streaming,
  error handling, and FastAPI integration. Use when creating, extending, or debugging
  LangGraph tool-calling agents.
---

# LangGraph Agent with External Tools Skill

## 1. Role & Core Philosophy

You are an expert **LangGraph AI Engineer** responsible for designing, implementing, debugging, testing, and deploying production-grade, stateful AI agents with external tool execution.

### Architectural Principles
- **ReAct Loop (Reason + Act)**: The LLM reasons, chooses whether to invoke external tools, inspects tool outputs, and repeats until a final answer is reached.
- **Explicit State Management**: State is defined via typed dictionaries or Pydantic models with explicit reducers (`add_messages`).
- **Resilient Tool Execution**: Tools validate inputs with Pydantic v2 schemas and return graceful error messages to the model instead of crashing the graph.
- **Persistence & Checkpointing**: Every multi-turn session is scoped by a `thread_id` backed by a persistent checkpointer.
- **Safety & Human-in-the-Loop (HITL)**: High-impact actions (deleting data, making payments, sending emails) require interrupt breakpoints for human review.

---

## 2. Technology Standards

* **Python**: 3.11+
* **LangGraph**: `>= 0.2.0`
* **LangChain Core**: `>= 0.3.0`
* **Pydantic**: `v2.x`
* **Checkpointers**: `langgraph-checkpoint`, `langgraph-checkpoint-postgres`, `langgraph-checkpoint-sqlite`
* **LLM Providers**: `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`
* **Async HTTP Client for Tools**: `httpx`

---

## 3. Defining External Tools

Tools are the interface between the agent and external APIs, databases, or local services.

### Best Practices for `@tool` Definitions
1. **Clear Docstrings**: The LLM reads the docstring and argument descriptions to decide *when* and *how* to call the tool.
2. **Pydantic v2 Schemas**: Use `args_schema` for complex or multi-parameter validation.
3. **Async Support**: Use `async def` for I/O operations (HTTP, DB queries).
4. **Graceful Error Handling**: Catch exceptions inside tools and return error strings so the LLM can self-correct.

```python
from typing import Type
import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# 1. Define explicit argument schema with Pydantic v2
class WeatherInput(BaseModel):
    city: str = Field(
        description="The city name to fetch weather for, e.g. 'San Francisco', 'London'",
        min_length=1,
    )
    units: str = Field(
        default="celsius",
        description="Temperature unit: 'celsius' or 'fahrenheit'",
    )


class DatabaseSearchInput(BaseModel):
    query: str = Field(description="Search query to find relevant customer records")
    limit: int = Field(default=5, ge=1, le=20, description="Max number of records to return")


# 2. Async tool with input schema and error handling
@tool(args_schema=WeatherInput)
async def get_weather(city: str, units: str = "celsius") -> str:
    """Fetch the current weather conditions for a given city."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.weather.example.com/v1/current",
                params={"city": city, "units": units},
            )
            response.raise_for_status()
            data = response.json()
            return f"Weather in {city}: {data['condition']}, {data['temperature']}°{units[0].upper()}"
    except httpx.HTTPStatusError as exc:
        return f"Weather API error ({exc.response.status_code}): Could not retrieve data for '{city}'."
    except Exception as exc:
        return f"Failed to get weather for '{city}': {str(exc)}"


@tool(args_schema=DatabaseSearchInput)
async def search_database(query: str, limit: int = 5) -> str:
    """Search internal database for customer records and order history."""
    try:
        # Simulate database search
        return f"Found {limit} records matching '{query}': [Customer #101: Active, Customer #102: Pending]"
    except Exception as exc:
        return f"Database query error: {str(exc)}"


# Group tools into a list
tools = [get_weather, search_database]
```

---

## 4. Agent State Definition

LangGraph passes state between all nodes in the graph.

### Option A: Standard `MessagesState` (Recommended for most chatbots)
```python
from langgraph.graph import MessagesState

# MessagesState automatically has:
# messages: Annotated[list[AnyMessage], add_messages]
```

### Option B: Custom State with Extra Context (Auth, User Metadata, Counters)
```python
from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str
    tenant_id: str
    tool_call_count: int
```

---

## 5. Building the Custom StateGraph

Construct a robust ReAct agent using `StateGraph`, `ToolNode`, and conditional edges:

```python
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.tools import tools

# 1. Initialize Model & Bind Tools
llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools(tools)

# 2. System Prompt
SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are a helpful, expert AI assistant. You have access to external tools "
        "to fetch real-time information and query databases. Always use the appropriate "
        "tool when needed. If a tool returns an error, explain the situation clearly."
    )
)


# 3. Model Node
async def call_model(state: MessagesState):
    messages = state["messages"]
    # Prepend system message if not already present
    if not messages or not isinstance(messages[0], SystemMessage):
        full_messages = [SYSTEM_PROMPT] + list(messages)
    else:
        full_messages = messages

    response = await llm_with_tools.ainvoke(full_messages)
    return {"messages": [response]}


# 4. Assemble the Graph
def build_agent_graph():
    builder = StateGraph(MessagesState)

    # Add Nodes
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(tools))

    # Add Edges
    builder.add_edge(START, "agent")

    # Conditional edge: if model returned tool_calls -> 'tools', else -> END
    builder.add_conditional_edges(
        "agent",
        tools_condition,
    )

    # After tool execution, loop back to the agent to reason on tool output
    builder.add_edge("tools", "agent")

    return builder
```

---

## 6. Prebuilt Agent Alternative (`create_react_agent`)

For standard ReAct workflows without custom routing, use LangGraph's prebuilt agent:

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

memory = MemorySaver()

agent = create_react_agent(
    model=llm,
    tools=tools,
    state_modifier="You are a helpful assistant with access to tools.",
    checkpointer=memory,
)
```

---

## 7. Persistence & Multi-turn Memory (Checkpointers)

Checkpointers persist graph state across turns using `thread_id`:

### In-Memory Checkpointer (Development / Testing)
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)
```

### Async PostgreSQL Checkpointer (Production)
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool


async def init_production_graph(db_uri: str):
    async with AsyncConnectionPool(conninfo=db_uri, max_size=20) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()  # Creates checkpointer tables

        builder = build_agent_graph()
        app = builder.compile(checkpointer=checkpointer)
        return app
```

### Invoking with `thread_id`
```python
from langchain_core.messages import HumanMessage

config = {"configurable": {"thread_id": "user_session_42"}}

# First turn
result = await app.ainvoke(
    {"messages": [HumanMessage(content="What's the weather in San Francisco?")]},
    config=config,
)

# Follow-up turn (remembers previous context)
result2 = await app.ainvoke(
    {"messages": [HumanMessage(content="What about in Fahrenheit?")]},
    config=config,
)
```

---

## 8. Human-in-the-Loop (HITL) & Tool Approvals

For sensitive tools (e.g. `delete_user`, `execute_transfer`), interrupt execution before the `tools` node:

```python
# 1. Compile with interrupt_before
app = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["tools"],
)

# 2. Run graph until breakpoint
config = {"configurable": {"thread_id": "tx_999"}}
state_output = await app.ainvoke(
    {"messages": [HumanMessage(content="Transfer $500 to Account #12345")]},
    config=config,
)

# 3. Inspect pending state
current_state = await app.aget_state(config)
pending_tool_calls = current_state.values["messages"][-1].tool_calls
print("Pending tool call for approval:", pending_tool_calls)

# 4. Resume execution after human approval (pass None to continue)
final_result = await app.ainvoke(None, config=config)
```

---

## 9. Streaming Execution

Stream graph progress and model tokens in real time:

### Stream Events (Token-level streaming)
```python
async for event in app.astream_events(
    {"messages": [HumanMessage(content="Search database for customer John")]},
    config=config,
    version="v2",
):
    kind = event["event"]

    # Stream model tokens as they generate
    if kind == "on_chat_model_stream":
        content = event["data"]["chunk"].content
        if content:
            print(content, end="", flush=True)

    # Monitor tool start and end
    elif kind == "on_tool_start":
        print(f"\n[Tool Calling: {event['name']} with {event['data'].get('input')}]")
    elif kind == "on_tool_end":
        print(f"\n[Tool Output: {event['data'].get('output')}]")
```

---

## 10. FastAPI Integration (Server-Sent Events)

Expose the LangGraph agent via FastAPI with streaming responses:

```python
import json
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

router = APIRouter(prefix="/agent", tags=["Agent"])


class ChatRequest(BaseModel):
    message: str
    thread_id: str


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    config = {"configurable": {"thread_id": request.thread_id}}

    async def event_generator():
        async for event in agent_app.astream_events(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
            version="v2",
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content
                if chunk:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            elif kind == "on_tool_start":
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['name']})}\n\n"
            elif kind == "on_tool_end":
                yield f"data: {json.dumps({'type': 'tool_end', 'output': str(event['data']['output'])})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 11. Testing LangGraph Agents

### Unit Testing Tools in Isolation
```python
import pytest
from app.tools import get_weather


@pytest.mark.asyncio
async def test_get_weather_tool():
    result = await get_weather.ainvoke({"city": "San Francisco", "units": "celsius"})
    assert "Weather in San Francisco" in result or "error" in result.lower()
```

### Testing Graph Execution with Mocked Model/Tools
```python
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_agent_graph_execution(mocker):
    # Mock external tool API
    mocker.patch("app.tools.httpx.AsyncClient.get", return_value=AsyncMock(
        status_code=200,
        json=lambda: {"condition": "Sunny", "temperature": 22},
        raise_for_status=lambda: None,
    ))

    builder = build_agent_graph()
    app = builder.compile()

    config = {"configurable": {"thread_id": "test_thread"}}
    result = await app.ainvoke(
        {"messages": [HumanMessage(content="What is the weather in Tokyo?")]},
        config=config,
    )

    assert len(result["messages"]) >= 2
    # Verify tool execution occurred
    assert any(isinstance(msg, ToolMessage) for msg in result["messages"])
```

---

## 12. Troubleshooting Common LangGraph Issues

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **Infinite Tool Loop** | Model repeats tool call without progressing | Ensure tool output is meaningful; add loop detection counter in state; check system prompt instructions. |
| **Missing `thread_id` Error** | Checkpointer compiled but no `thread_id` passed in `config` | Always pass `config={"configurable": {"thread_id": "..."}}` when compiling with a checkpointer. |
| **Tool Argument Validation Error** | LLM generated invalid JSON or missed required fields | Use strict Pydantic v2 `Field` definitions with clear descriptions; return validation errors as string. |
| **Tool Not Executed** | Missing `tools_condition` or `builder.add_edge("tools", "agent")` | Verify graph wiring: `START -> agent -> tools_condition -> tools -> agent -> END`. |
| **State Resetting Between Turns** | Checkpointer not passed during `.compile(checkpointer=...)` | Pass persistent checkpointer (`MemorySaver` or `AsyncPostgresSaver`) to `.compile()`. |
