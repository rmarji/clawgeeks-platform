"""OpenHands SDK integration for AI coding agents."""

from typing import Optional, Any
import os


class OpenHandsService:
    """
    Service for AI-powered coding tasks using OpenHands SDK.
    
    Requires Python 3.12+ and openhands-sdk package.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "anthropic/claude-sonnet-4-5-20250929"):
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self._sdk_available = self._check_sdk()
    
    def _check_sdk(self) -> bool:
        """Check if OpenHands SDK is available."""
        try:
            from openhands.sdk import LLM, Agent, Conversation, Tool
            return True
        except ImportError:
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if the service is available."""
        return self._sdk_available and self.api_key is not None
    
    def create_agent(self, tools: Optional[list[str]] = None) -> Any:
        """
        Create an OpenHands coding agent.
        
        Args:
            tools: List of tool names to enable. Defaults to terminal, file_editor, task_tracker.
            
        Returns:
            Agent instance
        """
        if not self._sdk_available:
            raise RuntimeError("OpenHands SDK not installed. Run: pip install openhands-sdk")
        
        from openhands.sdk import LLM, Agent, Tool
        from openhands.tools.file_editor import FileEditorTool
        from openhands.tools.terminal import TerminalTool
        from openhands.tools.task_tracker import TaskTrackerTool
        
        llm = LLM(
            model=self.model,
            api_key=self.api_key,
        )
        
        # Default tools
        default_tools = [
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ]
        
        return Agent(llm=llm, tools=default_tools)
    
    async def run_task(
        self, 
        task: str, 
        workspace: Optional[str] = None,
        agent: Optional[Any] = None
    ) -> dict:
        """
        Run a coding task.
        
        Args:
            task: Natural language description of the task
            workspace: Path to workspace directory (defaults to cwd)
            agent: Optional pre-configured agent
            
        Returns:
            Dict with status and output
        """
        if not self._sdk_available:
            return {
                "status": "error",
                "error": "OpenHands SDK not installed",
                "output": None
            }
        
        from openhands.sdk import Conversation
        
        if agent is None:
            agent = self.create_agent()
        
        workspace = workspace or os.getcwd()
        conversation = Conversation(agent=agent, workspace=workspace)
        
        try:
            conversation.send_message(task)
            output = await conversation.run()
            return {
                "status": "completed",
                "output": output,
                "error": None
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "output": None
            }


# Developer Agent archetype for Board of Mentors
DEVELOPER_AGENT = {
    "archetype": "developer_agent",
    "name": "Devin",
    "emoji": "👨‍💻",
    "domain": "software_engineering",
    "title": "AI Software Engineer",
    "tagline": "I turn ideas into working code.",
    "description": """
        AI-powered software engineer that can write, debug, and refactor code.
        Uses OpenHands SDK for autonomous coding tasks.
    """,
    "capabilities": [
        "code_generation",
        "debugging", 
        "refactoring",
        "documentation",
        "testing",
        "dependency_updates",
        "code_review"
    ],
    "powered_by": "openhands",
    "tier_limits": {
        "starter": 10,      # tasks/month
        "pro": 100,
        "business": 500,
        "enterprise": -1    # unlimited
    }
}


def get_openhands_service() -> OpenHandsService:
    """Factory function for dependency injection."""
    return OpenHandsService()
