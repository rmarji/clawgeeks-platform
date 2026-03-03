"""
Daytona Provisioner for ClawGeeks Platform

Manages OpenClaw deployments in Daytona sandboxes.
Supports full lifecycle: create, configure, start, stop, delete.
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import logging

# Daytona SDK
from daytona import Daytona, DaytonaConfig, CreateSandboxFromSnapshotParams

logger = logging.getLogger(__name__)


class SandboxState(str, Enum):
    """Sandbox lifecycle states."""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    DELETED = "deleted"


@dataclass
class SandboxConfig:
    """Configuration for a Daytona sandbox."""
    name: str
    tenant_id: str
    snapshot: str = "daytona-medium"  # OpenClaw needs 2GB+ memory
    auto_stop: int = 0  # 0 = never auto-stop
    labels: Dict[str, str] = field(default_factory=dict)
    
    # OpenClaw config
    anthropic_api_key: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_allowed_users: List[str] = field(default_factory=list)
    whatsapp_phone: Optional[str] = None
    gateway_token: Optional[str] = None
    
    # Resources (for future custom snapshots)
    cpu: int = 2
    memory: int = 4  # GB
    disk: int = 10  # GB


@dataclass
class SandboxInfo:
    """Information about a provisioned sandbox."""
    id: str
    name: str
    tenant_id: str
    state: SandboxState
    created_at: datetime
    gateway_token: Optional[str] = None
    preview_url: Optional[str] = None
    dashboard_url: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tenant_id": self.tenant_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "gateway_token": self.gateway_token,
            "preview_url": self.preview_url,
            "dashboard_url": self.dashboard_url,
            "labels": self.labels,
        }


class DaytonaProvisioner:
    """
    Provision and manage OpenClaw instances in Daytona sandboxes.
    
    Usage:
        provisioner = DaytonaProvisioner(api_key="dtn_xxx")
        
        # Create sandbox with OpenClaw
        config = SandboxConfig(
            name="client-acme",
            tenant_id="tenant_123",
            anthropic_api_key="sk-ant-xxx",
            telegram_bot_token="123:ABC",
        )
        sandbox = await provisioner.create(config)
        
        # Get dashboard URL
        url = await provisioner.get_dashboard_url(sandbox.id)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = "https://app.daytona.io/api",
        target: str = "us",
    ):
        """
        Initialize the Daytona provisioner.
        
        Args:
            api_key: Daytona API key (or set DAYTONA_API_KEY env var)
            api_url: Daytona API URL
            target: Target region (us, eu)
        """
        self.api_key = api_key or os.getenv("DAYTONA_API_KEY")
        if not self.api_key:
            raise ValueError("Daytona API key required (api_key or DAYTONA_API_KEY)")
        
        self.config = DaytonaConfig(
            api_key=self.api_key,
            api_url=api_url,
            target=target,
        )
        self.daytona = Daytona(self.config)
        self._sandboxes: Dict[str, SandboxInfo] = {}
    
    async def create(self, config: SandboxConfig) -> SandboxInfo:
        """
        Create a new Daytona sandbox with OpenClaw installed and configured.
        
        Args:
            config: Sandbox configuration
            
        Returns:
            SandboxInfo with sandbox details
        """
        logger.info(f"Creating sandbox: {config.name}")
        
        # Build labels
        labels = {
            "clawgeeks": "true",
            "tenant_id": config.tenant_id,
            "name": config.name,
            **config.labels,
        }
        
        # Create sandbox from snapshot
        try:
            sandbox = self.daytona.create(
                CreateSandboxFromSnapshotParams(
                    snapshot=config.snapshot,
                    labels=labels,
                    auto_stop_interval=config.auto_stop,
                )
            )
            
            sandbox_id = sandbox.id
            logger.info(f"Sandbox created: {sandbox_id}")
            
            # Configure OpenClaw
            await self._configure_openclaw(sandbox, config)
            
            # Start gateway
            gateway_token = config.gateway_token or None
            gateway_token = await self._start_gateway(sandbox, gateway_token)
            
            # Get preview URL for dashboard access
            preview_result = sandbox.create_signed_preview_url(18789)
            preview_url = preview_result.url if preview_result else None
            dashboard_url = f"{preview_url}?token={gateway_token}" if preview_url else None
            
            # Build info
            info = SandboxInfo(
                id=sandbox_id,
                name=config.name,
                tenant_id=config.tenant_id,
                state=SandboxState.RUNNING,
                created_at=datetime.utcnow(),
                gateway_token=gateway_token,
                preview_url=preview_url,
                dashboard_url=dashboard_url,
                labels=labels,
            )
            
            self._sandboxes[sandbox_id] = info
            return info
            
        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            raise
    
    async def _configure_openclaw(self, sandbox, config: SandboxConfig) -> None:
        """Configure OpenClaw inside the sandbox."""
        logger.info(f"Configuring OpenClaw in sandbox {sandbox.id}")
        
        # Set Anthropic API key
        if config.anthropic_api_key:
            sandbox.process.exec(
                f"openclaw config set model.anthropicApiKey {config.anthropic_api_key}"
            )
        
        # Configure Telegram
        if config.telegram_bot_token:
            sandbox.process.exec("openclaw config set channels.telegram.enabled true")
            sandbox.process.exec(
                f"openclaw config set channels.telegram.botToken {config.telegram_bot_token}"
            )
            
            # Set allowed users if provided
            for user in config.telegram_allowed_users:
                sandbox.process.exec(
                    f"openclaw config set channels.telegram.allowedUsers.+ {user}"
                )
        
        # Configure WhatsApp (phone number only, QR linking done separately)
        if config.whatsapp_phone:
            sandbox.process.exec("openclaw config set channels.whatsapp.enabled true")
            sandbox.process.exec(
                f"openclaw config set channels.whatsapp.myNumber {config.whatsapp_phone}"
            )
        
        logger.info("OpenClaw configured")
    
    async def _start_gateway(self, sandbox, gateway_token: Optional[str] = None) -> str:
        """Start the OpenClaw gateway and return the gateway token."""
        logger.info(f"Starting gateway in sandbox {sandbox.id}")
        
        # Generate a gateway token if not provided
        if not gateway_token:
            import secrets
            gateway_token = f"clawgeeks_{secrets.token_urlsafe(16)}"
        
        # Start gateway with --dev mode (creates config if missing)
        # --allow-unconfigured allows starting without full model config
        # --bind lan allows external access via preview URL
        sandbox.process.exec(
            f"nohup openclaw gateway run --dev --allow-unconfigured --token {gateway_token} --bind lan > /tmp/gateway.log 2>&1 &"
        )
        
        # Wait for gateway to start
        await asyncio.sleep(5)
        
        # Verify it's running by checking if port is responding
        result = sandbox.process.exec("curl -s http://localhost:18789/ | head -1 || echo 'not running'")
        if "not running" in result.result:
            logger.warning("Gateway may not have started properly")
        else:
            logger.info("Gateway started and responding")
        
        return gateway_token
    
    async def get(self, sandbox_id: str) -> Optional[SandboxInfo]:
        """Get sandbox info by ID."""
        if sandbox_id in self._sandboxes:
            return self._sandboxes[sandbox_id]
        
        # Try to fetch from Daytona
        try:
            sandbox = self.daytona.get(sandbox_id)
            if sandbox:
                labels = sandbox.labels or {}
                return SandboxInfo(
                    id=sandbox.id,
                    name=labels.get("name", sandbox.id),
                    tenant_id=labels.get("tenant_id", "unknown"),
                    state=SandboxState.RUNNING,  # TODO: map actual state
                    created_at=datetime.utcnow(),
                    labels=labels,
                )
        except Exception as e:
            logger.error(f"Failed to get sandbox {sandbox_id}: {e}")
        
        return None
    
    async def list(self, tenant_id: Optional[str] = None) -> List[SandboxInfo]:
        """List all ClawGeeks sandboxes, optionally filtered by tenant."""
        labels = {"clawgeeks": "true"}
        if tenant_id:
            labels["tenant_id"] = tenant_id
        
        try:
            result = self.daytona.list(labels=labels)
            sandboxes = result.items if hasattr(result, 'items') else []
            return [
                SandboxInfo(
                    id=s.id,
                    name=s.labels.get("name", s.id) if s.labels else s.id,
                    tenant_id=s.labels.get("tenant_id", "unknown") if s.labels else "unknown",
                    state=SandboxState.RUNNING,
                    created_at=datetime.utcnow(),
                    labels=s.labels or {},
                )
                for s in sandboxes
            ]
        except Exception as e:
            logger.error(f"Failed to list sandboxes: {e}")
            return []
    
    async def get_preview_url(self, sandbox_id: str, port: int = 18789) -> Optional[str]:
        """Get a signed preview URL for accessing a sandbox port externally."""
        try:
            sandbox = self.daytona.get(sandbox_id)
            if sandbox:
                result = sandbox.create_signed_preview_url(port)
                return result.url
        except Exception as e:
            logger.error(f"Failed to get preview URL for sandbox {sandbox_id}: {e}")
        return None
    
    async def stop(self, sandbox_id: str) -> bool:
        """Stop a sandbox (preserves state)."""
        try:
            sandbox = self.daytona.get(sandbox_id)
            if sandbox:
                sandbox.stop()
                if sandbox_id in self._sandboxes:
                    self._sandboxes[sandbox_id].state = SandboxState.STOPPED
                logger.info(f"Stopped sandbox {sandbox_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to stop sandbox {sandbox_id}: {e}")
        return False
    
    async def start(self, sandbox_id: str) -> bool:
        """Start a stopped sandbox."""
        try:
            sandbox = self.daytona.get(sandbox_id)
            if sandbox:
                sandbox.start()
                
                # Restart gateway
                sandbox.process.exec(
                    "nohup openclaw gateway run > /tmp/gateway.log 2>&1 &"
                )
                
                if sandbox_id in self._sandboxes:
                    self._sandboxes[sandbox_id].state = SandboxState.RUNNING
                logger.info(f"Started sandbox {sandbox_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to start sandbox {sandbox_id}: {e}")
        return False
    
    async def delete(self, sandbox_id: str) -> bool:
        """Delete a sandbox permanently."""
        try:
            sandbox = self.daytona.get(sandbox_id)
            if sandbox:
                sandbox.delete()
                if sandbox_id in self._sandboxes:
                    del self._sandboxes[sandbox_id]
                logger.info(f"Deleted sandbox {sandbox_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete sandbox {sandbox_id}: {e}")
        return False
    
    async def exec(self, sandbox_id: str, command: str) -> Optional[str]:
        """Execute a command in a sandbox."""
        try:
            sandbox = self.daytona.get(sandbox_id)
            if sandbox:
                result = sandbox.process.exec(command)
                return result.result
        except Exception as e:
            logger.error(f"Failed to exec in sandbox {sandbox_id}: {e}")
        return None
    
    async def get_logs(self, sandbox_id: str, lines: int = 100) -> Optional[str]:
        """Get gateway logs from a sandbox."""
        return await self.exec(sandbox_id, f"tail -n {lines} /tmp/gateway.log")
    
    async def restart_gateway(self, sandbox_id: str) -> bool:
        """Restart the OpenClaw gateway in a sandbox."""
        try:
            sandbox = self.daytona.get(sandbox_id)
            if sandbox:
                sandbox.process.exec("openclaw gateway stop 2>/dev/null || true")
                await asyncio.sleep(1)
                sandbox.process.exec(
                    "nohup openclaw gateway run > /tmp/gateway.log 2>&1 &"
                )
                logger.info(f"Restarted gateway in sandbox {sandbox_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to restart gateway in sandbox {sandbox_id}: {e}")
        return False
    
    async def configure_soul(
        self, 
        sandbox_id: str, 
        soul_content: str,
        workspace_path: str = "/home/daytona/workspace"
    ) -> bool:
        """Upload a SOUL.md file to customize agent personality."""
        try:
            sandbox = self.daytona.get(sandbox_id)
            if sandbox:
                # Write SOUL.md
                sandbox.fs.write_file(
                    f"{workspace_path}/SOUL.md",
                    soul_content.encode()
                )
                logger.info(f"Configured SOUL.md in sandbox {sandbox_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to configure soul in sandbox {sandbox_id}: {e}")
        return False
    
    async def install_skill(self, sandbox_id: str, skill_name: str) -> bool:
        """Install a skill from ClawHub."""
        result = await self.exec(sandbox_id, f"clawhub install {skill_name}")
        return result is not None and "installed" in result.lower()


# Convenience functions for quick operations
async def create_demo_sandbox(
    api_key: str,
    name: str = "demo",
    anthropic_key: Optional[str] = None,
) -> SandboxInfo:
    """Quick helper to spin up a demo sandbox."""
    provisioner = DaytonaProvisioner(api_key=api_key)
    config = SandboxConfig(
        name=name,
        tenant_id="demo",
        anthropic_api_key=anthropic_key or os.getenv("ANTHROPIC_API_KEY"),
    )
    return await provisioner.create(config)


# CLI for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Daytona Provisioner CLI")
    parser.add_argument("action", choices=["create", "list", "stop", "start", "delete", "logs"])
    parser.add_argument("--name", help="Sandbox name")
    parser.add_argument("--id", help="Sandbox ID")
    parser.add_argument("--tenant", help="Tenant ID")
    parser.add_argument("--api-key", help="Daytona API key")
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.getenv("DAYTONA_API_KEY")
    if not api_key:
        print("Error: DAYTONA_API_KEY required")
        exit(1)
    
    provisioner = DaytonaProvisioner(api_key=api_key)
    
    async def main():
        if args.action == "create":
            if not args.name:
                print("Error: --name required")
                return
            config = SandboxConfig(
                name=args.name,
                tenant_id=args.tenant or "default",
            )
            info = await provisioner.create(config)
            print(json.dumps(info.to_dict(), indent=2))
        
        elif args.action == "list":
            sandboxes = await provisioner.list(tenant_id=args.tenant)
            for s in sandboxes:
                print(f"{s.id}\t{s.name}\t{s.state.value}")
        
        elif args.action == "stop":
            if not args.id:
                print("Error: --id required")
                return
            await provisioner.stop(args.id)
            print(f"Stopped {args.id}")
        
        elif args.action == "start":
            if not args.id:
                print("Error: --id required")
                return
            await provisioner.start(args.id)
            print(f"Started {args.id}")
        
        elif args.action == "delete":
            if not args.id:
                print("Error: --id required")
                return
            await provisioner.delete(args.id)
            print(f"Deleted {args.id}")
        
        elif args.action == "logs":
            if not args.id:
                print("Error: --id required")
                return
            logs = await provisioner.get_logs(args.id)
            print(logs or "No logs")
    
    asyncio.run(main())
