# OpenHands Integration Spec

## Overview

Integrate OpenHands Software Agent SDK into ClawGeeks platform to provide AI-powered coding agents alongside our existing mentor and advisor agents.

## Integration Points

### 1. SDK Integration (Phase 1)
```python
# New service: provisioning/services/openhands.py
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool
from openhands.tools.task_tracker import TaskTrackerTool

class OpenHandsService:
    """Coding agent powered by OpenHands SDK"""
    
    def create_coding_agent(self, llm_config: dict) -> Agent:
        llm = LLM(
            model=llm_config.get("model", "anthropic/claude-sonnet-4-5-20250929"),
            api_key=llm_config.get("api_key"),
        )
        return Agent(
            llm=llm,
            tools=[
                Tool(name=TerminalTool.name),
                Tool(name=FileEditorTool.name),
                Tool(name=TaskTrackerTool.name),
            ],
        )
    
    async def run_task(self, agent: Agent, workspace: str, task: str) -> str:
        conversation = Conversation(agent=agent, workspace=workspace)
        conversation.send_message(task)
        return await conversation.run()
```

### 2. New Agent Archetype: Developer Agent
Add to Board of Mentors:
```python
{
    "archetype": "developer_agent",
    "name": "Devin",
    "emoji": "👨‍💻",
    "domain": "software_engineering",
    "title": "AI Software Engineer",
    "tagline": "I turn ideas into working code.",
    "capabilities": [
        "code_generation",
        "debugging",
        "refactoring",
        "documentation",
        "testing",
        "dependency_updates"
    ],
    "powered_by": "openhands"
}
```

### 3. API Endpoints
```
POST /api/v1/coding/task
  - workspace_id: str
  - task: str
  - model: str (optional)
  → Returns task_id

GET /api/v1/coding/task/{task_id}
  → Returns status + output

POST /api/v1/coding/conversation
  - Create interactive coding session
```

### 4. Tenant Features
- **Starter:** 10 coding tasks/month
- **Pro:** 100 coding tasks/month
- **Business:** 500 coding tasks/month
- **Enterprise:** Unlimited + self-hosted OpenHands

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  ClawGeeks Platform                  │
├─────────────────────────────────────────────────────┤
│  HR Dept │ Mentors │ Advisors │ Coding Agents      │
│     ↓        ↓          ↓            ↓              │
│  Analyze   Guide     Advise    Build/Fix Code      │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│               OpenHands SDK Layer                    │
├─────────────────────────────────────────────────────┤
│  LLM  │  Agent  │  Tools  │  Workspace             │
│   ↓        ↓         ↓           ↓                 │
│ Claude  Terminal  FileEditor  Docker/K8s           │
│ GPT     Git       TaskTracker  Local               │
│ Qwen    Browser   Custom...    Daytona             │
└─────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: SDK Integration (2 hours)
- [ ] Add `openhands-sdk` to requirements.txt
- [ ] Create `provisioning/services/openhands.py`
- [ ] Add coding agent to mentors list
- [ ] Basic API endpoint for running tasks

### Phase 2: Workspace Integration (4 hours)
- [ ] Connect to Daytona for ephemeral workspaces
- [ ] Git repo cloning support
- [ ] Output streaming via WebSocket

### Phase 3: GUI Option (8 hours)
- [ ] Deploy OpenHands GUI as optional add-on
- [ ] SSO integration with ClawGeeks auth
- [ ] Usage tracking and billing

## Dependencies

```txt
# Add to requirements.txt
openhands-sdk>=1.0.0
```

## Environment Variables

```env
OPENHANDS_API_KEY=  # If using hosted
OPENHANDS_WORKSPACE_PROVIDER=daytona  # or docker, local
```

## Status

🔴 **SPEC** — Ready for implementation
