"""
Event Broadcasting Module
WebSocket-based real-time event streaming + HTTP polling for agent actions.
"""

import asyncio
from typing import Any, Dict, List, Set, Optional
from datetime import datetime

from loguru import logger


class AgentEvent:
    """Represents an agent action event."""
    
    def __init__(self, event_type: str, agent: str, agent_name: str, 
                 emoji: str, role: str, message: str, session_id: str,
                 phase: str = "", metadata: Optional[Dict[str, Any]] = None):
        self.event_type = event_type
        self.agent = agent
        self.agent_name = agent_name
        self.emoji = emoji
        self.role = role
        self.message = message
        self.session_id = session_id
        self.phase = phase
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "agent": self.agent,
            "agent_name": self.agent_name,
            "emoji": self.emoji,
            "role": self.role,
            "message": self.message,
            "session_id": self.session_id,
            "phase": self.phase,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "index": 0,  # Will be set by EventStore
        }


class EventStore:
    """
    Thread-safe event storage for HTTP polling.
    """
    
    def __init__(self):
        self._events: Dict[str, List[Dict]] = {}
        self._index: Dict[str, int] = {}
    
    def add_event(self, session_id: str, event_data: Dict) -> int:
        if session_id not in self._events:
            self._events[session_id] = []
            self._index[session_id] = 0
        
        event_data["index"] = self._index[session_id]
        self._events[session_id].append(event_data)
        self._index[session_id] += 1
        return event_data["index"]
    
    def get_events(self, session_id: str, since_index: int = 0) -> List[Dict]:
        events = self._events.get(session_id, [])
        return [e for e in events if e["index"] >= since_index]
    
    def get_count(self, session_id: str) -> int:
        return len(self._events.get(session_id, []))


class EventBroadcaster:
    """
    Singleton event broadcaster for WebSocket streaming + HTTP polling.
    """
    
    def __init__(self):
        self._connections: Dict[str, Set] = {}
        self._lock = asyncio.Lock()
        self._store = EventStore()
    
    async def connect(self, websocket, session_id: str):
        async with self._lock:
            if session_id not in self._connections:
                self._connections[session_id] = set()
            self._connections[session_id].add(websocket)
            logger.info(f"WebSocket connected for session {session_id}")
    
    async def disconnect(self, websocket, session_id: str):
        async with self._lock:
            if session_id in self._connections:
                self._connections[session_id].discard(websocket)
                if not self._connections[session_id]:
                    del self._connections[session_id]
    
    async def broadcast(self, event: AgentEvent):
        """Broadcast event via WebSocket + store for HTTP polling."""
        data = event.to_dict()
        idx = self._store.add_event(event.session_id, data)
        data["index"] = idx
        
        async with self._lock:
            connections = self._connections.get(event.session_id, set()).copy()
        
        if not connections:
            return
        
        disconnected = set()
        for ws in connections:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.warning(f"WebSocket send failed: {e}")
                disconnected.add(ws)
        
        if disconnected:
            async with self._lock:
                if event.session_id in self._connections:
                    self._connections[event.session_id] -= disconnected
    
    @property
    def store(self) -> EventStore:
        return self._store


# Global instance
broadcaster = EventBroadcaster()


async def emit_agent_thinking(session_id: str, agent: str, agent_name: str, 
                               emoji: str, role: str, message: str, phase: str = ""):
    event = AgentEvent(
        event_type="thinking", agent=agent, agent_name=agent_name,
        emoji=emoji, role=role, message=message, session_id=session_id, phase=phase,
    )
    await broadcaster.broadcast(event)


async def emit_agent_message(session_id: str, agent: str, agent_name: str, 
                              emoji: str, role: str, message: str, phase: str = "",
                              metadata: Optional[Dict[str, Any]] = None):
    event = AgentEvent(
        event_type="message", agent=agent, agent_name=agent_name,
        emoji=emoji, role=role, message=message, session_id=session_id,
        phase=phase, metadata=metadata,
    )
    await broadcaster.broadcast(event)


async def emit_phase_start(session_id: str, phase: str, message: str = ""):
    event = AgentEvent(
        event_type="phase_start", agent="system", agent_name="System",
        emoji="🚀", role="Orchestrator", message=message or f"Starting {phase} phase...",
        session_id=session_id, phase=phase,
    )
    await broadcaster.broadcast(event)


async def emit_phase_complete(session_id: str, phase: str, message: str = ""):
    event = AgentEvent(
        event_type="phase_complete", agent="system", agent_name="System",
        emoji="✅", role="Orchestrator", message=message or f"Completed {phase} phase.",
        session_id=session_id, phase=phase,
    )
    await broadcaster.broadcast(event)


async def emit_error(session_id: str, message: str, agent: str = "system"):
    event = AgentEvent(
        event_type="error", agent=agent, agent_name="System",
        emoji="❌", role="Error", message=message, session_id=session_id,
    )
    await broadcaster.broadcast(event)