# OpenHands + OpenClaw Best Practices

## Overview

This document outlines best practices for integrating OpenHands (AI coding agents) with OpenClaw (conversational AI agents) in the ClawGeeks platform.

## Architecture: Complementary Roles

```
┌─────────────────────────────────────────────────────────────┐
│                    ClawGeeks Platform                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │    OpenClaw     │◄───────►│   OpenHands     │           │
│  │                 │ Trigger │                 │           │
│  │ • Conversation  │ coding  │ • Code tasks    │           │
│  │ • Planning      │ tasks   │ • Terminal      │           │
│  │ • Coordination  │◄───────►│ • File editing  │           │
│  │ • User facing   │ Report  │ • Git ops       │           │
│  └─────────────────┘ results └─────────────────┘           │
│          │                           │                      │
│          ▼                           ▼                      │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │  Telegram/Slack │         │ Daytona/Docker  │           │
│  │  Discord/Web    │         │   Workspaces    │           │
│  └─────────────────┘         └─────────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Best Practice 1: Clear Role Separation

### OpenClaw handles:
- User conversation and intent understanding
- Task planning and decomposition
- Progress reporting and status updates
- Multi-step workflow coordination
- Non-coding tasks (calendar, email, research)

### OpenHands handles:
- Actual code writing/editing
- Terminal command execution
- File system operations
- Git operations
- Code testing and debugging

**Example flow:**
```
User → OpenClaw: "Add a login page to the app"
OpenClaw → Plans: 1) Create route 2) Add form 3) Add auth
OpenClaw → OpenHands: "Create /login route with form"
OpenHands → Executes: Creates files, writes code, tests
OpenHands → OpenClaw: "Done. Created login.py, login.html"
OpenClaw → User: "Login page added! Would you like me to explain?"
```

## Best Practice 2: Workspace Isolation

Always run OpenHands in isolated workspaces:

```python
# ✅ Good: Isolated Docker workspace
from openhands.workspace import DockerWorkspace

with DockerWorkspace(
    server_image="ghcr.io/openhands/agent-server:latest-python",
    host_port=8010,
) as workspace:
    conversation = Conversation(agent=agent, workspace=workspace)
    conversation.run()
# Container auto-cleaned up

# ❌ Bad: Running on host filesystem
conversation = Conversation(agent=agent, workspace="/home/user/code")
```

**For ClawGeeks tenants:**
- Use Daytona sandboxes for ephemeral coding workspaces
- Each tenant gets isolated environment
- Auto-cleanup after task completion

## Best Practice 3: Model Selection

### OpenClaw (conversation):
- Claude Opus/Sonnet for complex reasoning
- Lower cost models for routine tasks
- Streaming for real-time responses

### OpenHands (coding):
- Claude Sonnet 4 or GPT-4 for best code quality
- Qwen3-Coder for cost-effective tasks
- Match model to task complexity

```python
# OpenHands service with appropriate model
openhands_service = OpenHandsService(
    model="anthropic/claude-sonnet-4-5-20250929",  # Best for code
    api_key=os.getenv("ANTHROPIC_API_KEY")
)
```

## Best Practice 4: Error Handling

Always wrap OpenHands tasks with error recovery:

```python
async def run_coding_task(task: str, workspace: str) -> dict:
    try:
        result = await openhands_service.run_task(task, workspace)
        
        if result["status"] == "error":
            # Log for debugging
            logger.error(f"Coding task failed: {result['error']}")
            
            # Return user-friendly message
            return {
                "status": "error",
                "message": "The coding task encountered an issue. Would you like me to try a different approach?",
                "technical_error": result["error"]
            }
        
        return result
        
    except Exception as e:
        # Graceful degradation
        return {
            "status": "error", 
            "message": "Coding service temporarily unavailable",
            "fallback": "I can describe the changes needed for manual implementation"
        }
```

## Best Practice 5: Progress Streaming

Use WebSocket for real-time updates:

```python
# OpenHands provides event callbacks
def event_callback(event):
    if event.type == "command_output":
        # Stream to user via OpenClaw
        send_to_user(f"📟 {event.output}")
    elif event.type == "file_edit":
        send_to_user(f"✏️ Editing {event.path}")

conversation = Conversation(
    agent=agent,
    workspace=workspace,
    callbacks=[event_callback],
    visualize=True,  # Enable progress visualization
)
```

## Best Practice 6: Resource Limits

Set appropriate limits for tenant tiers:

```python
TIER_LIMITS = {
    "starter": {
        "tasks_per_month": 10,
        "max_runtime_seconds": 300,      # 5 min per task
        "max_workspace_size_mb": 100,
    },
    "pro": {
        "tasks_per_month": 100,
        "max_runtime_seconds": 600,      # 10 min
        "max_workspace_size_mb": 500,
    },
    "business": {
        "tasks_per_month": 500,
        "max_runtime_seconds": 1800,     # 30 min
        "max_workspace_size_mb": 2000,
    },
    "enterprise": {
        "tasks_per_month": -1,           # Unlimited
        "max_runtime_seconds": 3600,     # 1 hour
        "max_workspace_size_mb": 10000,
    }
}
```

## Best Practice 7: Security

### Never expose:
- API keys in workspaces
- Host filesystem access
- Network to internal services

### Always:
- Use secrets management (env vars, not files)
- Sandbox all code execution
- Review generated code before deployment

```python
# Safe: Inject API key at runtime, not in workspace
agent = Agent(
    llm=LLM(api_key=SecretStr(os.getenv("LLM_API_KEY"))),
    tools=[...],
)

# Unsafe: Don't let agent access arbitrary env vars
# Don't mount host directories with secrets
```

## Best Practice 8: Integration with OpenClaw Skills

Create a skill for OpenClaw to invoke OpenHands:

```markdown
# SKILL.md - OpenHands Coding Agent

## When to use
- User requests code changes
- Bug fixes needed
- File modifications
- Project scaffolding

## How to invoke
1. Parse user request into specific task
2. Call /coding/task endpoint
3. Poll for completion
4. Report results to user

## Example
User: "Add a dark mode toggle to the settings page"

Task breakdown:
1. Create DarkModeToggle component
2. Add to settings page
3. Wire up state management
4. Test the implementation
```

## Best Practice 9: Daytona + OpenHands Synergy

OpenHands officially supports Daytona for workspaces:

```python
from openhands.workspace import DaytonaWorkspace

# Create ephemeral coding environment
with DaytonaWorkspace(
    api_key=os.getenv("DAYTONA_API_KEY"),
    image="ghcr.io/openhands/sandbox:latest",
) as workspace:
    # Clone repo, run tasks, auto-cleanup
    conversation = Conversation(agent=agent, workspace=workspace)
    conversation.send_message("Fix the failing tests in this repo")
    conversation.run()
```

## Best Practice 10: Monitoring & Observability

Track OpenHands usage alongside OpenClaw:

```python
# Metrics to track
- coding_tasks_total (counter)
- coding_task_duration_seconds (histogram)
- coding_task_success_rate (gauge)
- coding_tokens_used (counter by model)
- workspace_size_bytes (gauge)

# Integrate with OpenClaw session tracking
session_id = openclaw_session.id
openhands_task = run_task(task, metadata={"session_id": session_id})
```

## Summary

| Aspect | OpenClaw | OpenHands |
|--------|----------|-----------|
| Primary role | Conversation & coordination | Code execution |
| User interaction | Direct | Via OpenClaw |
| Workspace | Persistent | Ephemeral |
| Model preference | Flexible | Code-optimized |
| Safety | Auth & RBAC | Sandboxed |
| Billing | Per message/token | Per task |

The combination provides a powerful AI workforce: OpenClaw as the "project manager" and OpenHands as the "developer."
