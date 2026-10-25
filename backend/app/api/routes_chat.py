import json
import asyncio
from typing import Dict, Any, List
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agents.graph import build_data_analyst_graph
from ..agents.state import AgentState

router = APIRouter(prefix="/api/chat", tags=["Agent Chat & Logs"])

# In-memory session store for multi-turn history
SESSION_STORE: Dict[str, List[Dict[str, str]]] = {}

class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"

@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """
    Server-Sent Events (SSE) streaming endpoint that yields real-time agent monologue,
    tool execution logs, SQL statements, anomaly flags, chart specs, and final synthesis.
    """
    queue: asyncio.Queue = asyncio.Queue()

    def log_hook(event: Dict[str, Any]):
        """Synchronous callback from LangGraph node pushed into async queue."""
        asyncio.run_coroutine_threadsafe(
            queue.put({"type": "log", "data": event}),
            loop
        )

    loop = asyncio.get_running_loop()

    # Load session history
    history = SESSION_STORE.setdefault(req.session_id, [])

    initial_state: AgentState = {
        "session_id": req.session_id,
        "query": req.query,
        "messages": history.copy(),
        "active_logs": [],
    }

    async def run_agent():
        try:
            graph = build_data_analyst_graph(log_hook=log_hook)
            # Run graph in thread pool so it doesn't block async loop
            final_state = await asyncio.to_thread(graph.invoke, initial_state)

            # Stream tool artifacts
            if final_state.get("sql_query"):
                await queue.put({
                    "type": "sql",
                    "data": {
                        "query": final_state["sql_query"],
                        "pandas": final_state.get("pandas_code", ""),
                        "row_count": len(final_state.get("sql_rows", [])),
                        "columns": final_state.get("sql_columns", []),
                    }
                })

            if final_state.get("chart_spec"):
                await queue.put({
                    "type": "chart",
                    "data": final_state["chart_spec"]
                })

            if final_state.get("anomalies"):
                await queue.put({
                    "type": "anomalies",
                    "data": final_state["anomalies"]
                })

            # Stream final completion
            await queue.put({
                "type": "complete",
                "data": {
                    "answer": final_state.get("final_answer", "Analysis complete."),
                    "reasoning": final_state.get("reasoning", ""),
                    "model_used": final_state.get("model_used", "NVIDIA Nemotron 30B"),
                    "provider": final_state.get("provider", "NVIDIA"),
                }
            })

            # Append to session history
            history.append({"role": "user", "content": req.query})
            history.append({"role": "assistant", "content": final_state.get("final_answer", "")})

        except Exception as e:
            await queue.put({
                "type": "error",
                "data": {"message": str(e)}
            })
        finally:
            await queue.put(None)  # Sentinel to close stream

    # Start agent in background
    asyncio.create_task(run_agent())

    async def event_generator():
        while True:
            item = await queue.get()
            if item is None:
                break
            payload = f"data: {json.dumps(item)}\n\n"
            yield payload.encode("utf-8")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.delete("/history/{session_id}")
async def clear_session_history(session_id: str):
    """Resets conversation context for a session."""
    if session_id in SESSION_STORE:
        del SESSION_STORE[session_id]
    return {"status": "success", "message": f"Session '{session_id}' cleared."}
