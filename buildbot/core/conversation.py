"""
BuildBot Conversation Manager
Manages chat history and context for multi-turn conversations.
Compatible with Python 3.14+
"""

from dataclasses import dataclass, field
from typing import Optional
from .models import BuildRequest, BuildInfo, Intent


@dataclass
class ConversationContext:
    """Stores conversation context and state."""
    last_request:    Optional[BuildRequest] = None
    last_build:      Optional[BuildInfo]    = None
    pending_request: Optional[BuildRequest] = None
    awaiting_field:  Optional[str]          = None

    # ── New: tracks which job params still need values ──────────────────
    # List of param dicts (same schema as get_job_parameters returns).
    # Each turn pops the front item, fills the value, moves to next.
    pending_params:        list[dict] = field(default_factory=list)
    collected_params:      dict       = field(default_factory=dict)

    # ── New: "confirm before build" gate ────────────────────────────────
    awaiting_confirmation: bool = False

    message_history: list[dict] = field(default_factory=list)


class ConversationManager:
    """
    Manages conversation state and history.
    Enables multi-turn conversations and reference resolution.
    """
    
    def __init__(self, max_history: int = 20):
        self.context = ConversationContext()
        self.max_history = max_history
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to history."""
        self.context.message_history.append({
            "role": role,
            "content": content
        })
        
        # Trim history if too long
        if len(self.context.message_history) > self.max_history:
            self.context.message_history = self.context.message_history[-self.max_history:]
    
    def get_context_summary(self) -> str:
        """Get a summary of conversation context for LLM."""
        parts = []
        
        if self.context.last_request:
            req = self.context.last_request
            parts.append(f"Last request: repo={req.repo_url}, branch={req.branch}")
        
        if self.context.last_build:
            build = self.context.last_build
            parts.append(f"Last build: #{build.build_number} ({build.status.value})")
        
        return " | ".join(parts) if parts else "No previous context"
    
    def set_last_request(self, request: BuildRequest) -> None:
        """Store the last successful request."""
        self.context.last_request = request
    
    def set_last_build(self, build: BuildInfo) -> None:
        """Store the last build info."""
        self.context.last_build = build
    
    def set_pending_request(self, request: BuildRequest, awaiting: str) -> None:
        """Store a pending request that needs more info."""
        self.context.pending_request = request
        self.context.awaiting_field  = awaiting

    # ── Confirmation gate ─────────────────────────────────────────────────
    def set_awaiting_confirmation(self, request: BuildRequest) -> None:
        """Park a fully-parsed request until the user says yes/no."""
        self.context.pending_request        = request
        self.context.awaiting_confirmation  = True
        self.context.awaiting_field         = None

    def is_awaiting_confirmation(self) -> bool:
        return self.context.awaiting_confirmation

    def confirm_build(self) -> Optional[BuildRequest]:
        """User said yes — return the parked request and clear the gate."""
        req = self.context.pending_request
        self.context.awaiting_confirmation = False
        self.context.pending_request       = None
        return req

    def cancel_confirmation(self) -> None:
        """User said no — discard the parked request."""
        self.context.awaiting_confirmation = False
        self.context.pending_request       = None
        self.context.pending_params        = []
        self.context.collected_params      = {}

    # ── Parameter collection ──────────────────────────────────────────────
    def start_param_collection(self, request: BuildRequest,
                                params: list[dict]) -> str:
        """
        Begin collecting values for *params* (list from get_job_parameters).
        Returns the prompt string for the first parameter.
        """
        self.context.pending_request  = request
        self.context.pending_params   = list(params)   # copy so we can pop
        self.context.collected_params = {}
        self.context.awaiting_field   = "__param__"
        return self._param_prompt(self.context.pending_params[0])

    def has_pending_params(self) -> bool:
        return (
            self.context.awaiting_field == "__param__"
            and bool(self.context.pending_params)
        )

    def collect_param_value(self, value: str) -> Optional[str]:
        """
        Feed user's answer for the current param.
        Returns the prompt for the NEXT param, or None when all are collected.
        """
        ctx = self.context
        current = ctx.pending_params.pop(0)
        param_name = current["name"]

        # Use default if user just pressed enter with no value
        effective = value.strip() or str(current.get("default") or "")
        ctx.collected_params[param_name] = effective

        if ctx.pending_params:
            return self._param_prompt(ctx.pending_params[0])

        # All done — embed collected params into the request and signal done
        ctx.awaiting_field = None
        return None  # caller checks has_pending_params() == False

    def get_collected_params(self) -> dict:
        return dict(self.context.collected_params)

    def _param_prompt(self, param: dict) -> str:
        """Build a friendly prompt for one parameter."""
        name    = param["name"]
        desc    = param.get("description", "")
        default = param.get("default")
        choices = param.get("choices", [])
        ptype   = param.get("type", "")

        lines = [f"**{name}**"]
        if desc:
            lines.append(f"*{desc}*")
        if choices:
            opts = " / ".join(f"`{c}`" for c in choices)
            lines.append(f"Choices: {opts}")
        if default is not None and default != "":
            lines.append(f"Default: `{default}` (press Enter to use)")
        if ptype == "BooleanParameterDefinition":
            lines.append("Enter `true` or `false`")

        return "📝 " + " — ".join(lines)
    
    def has_pending_request(self) -> bool:
        """Check if there's a pending request."""
        return self.context.pending_request is not None
    
    def complete_pending_request(self, value: str) -> Optional[BuildRequest]:
        """
        Complete a pending request with the provided value.
        Returns the completed request or None if still incomplete.
        """
        if not self.context.pending_request:
            return None

        request  = self.context.pending_request
        awaiting = self.context.awaiting_field

        if awaiting == "branch":
            request.branch = value.strip()
        elif awaiting == "repo_url":
            request.repo_url = value.strip()
        elif awaiting == "job_name":
            request.job_name = value.strip()

        # Remove from missing_fields list if present
        if awaiting in (request.missing_fields or []):
            request.missing_fields.remove(awaiting)

        if request.missing_fields:
            self.context.awaiting_field = request.missing_fields[0]
            return None

        self.clear_pending()
        return request
    
    def clear_pending(self) -> None:
        """Clear pending request and all associated state."""
        self.context.pending_request       = None
        self.context.awaiting_field        = None
        self.context.awaiting_confirmation = False
        self.context.pending_params        = []
        self.context.collected_params      = {}
    
    def resolve_references(self, request: BuildRequest) -> BuildRequest:
        """
        Resolve references like 'same branch', 'last repo' etc.
        """
        if not self.context.last_request:
            return request
        
        last = self.context.last_request
        
        # If rebuild intent, copy from last request
        if request.intent == Intent.REBUILD:
            if not request.repo_url and last.repo_url:
                request.repo_url = last.repo_url
            if not request.branch and last.branch:
                request.branch = last.branch
            if not request.job_name and last.job_name:
                request.job_name = last.job_name
        
        return request
    
    def clear(self) -> None:
        """Clear all conversation state."""
        self.context = ConversationContext()
