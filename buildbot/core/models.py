"""
BuildBot Data Models
Defines all data structures used throughout the application.
Compatible with Python 3.14+
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


class Intent(Enum):
    """User intent types."""
    # Build operations
    NEW_BUILD = "new_build"
    REBUILD = "rebuild"
    ABORT_BUILD = "abort_build"
    
    # Status & Info
    CHECK_STATUS = "check_status"
    JOB_HISTORY = "job_history"
    LIST_JOBS = "list_jobs"
    LIST_VIEWS = "list_views"
    VIEW_JOBS = "view_jobs"
    JOB_INFO = "job_info"
    
    # Artifacts
    GET_ARTIFACTS = "get_artifacts"
    GET_LATEST_ARTIFACTS = "get_latest_artifacts"
    
    # Queue management
    QUEUE_STATUS = "queue_status"
    QUEUE_CANCEL = "queue_cancel"
    
    # Node/Agent management
    NODE_STATUS = "node_status"
    NODE_LIST = "node_list"
    NODE_OFFLINE = "node_offline"
    NODE_ONLINE = "node_online"
    
    # Job management
    DISABLE_JOB = "disable_job"
    ENABLE_JOB = "enable_job"
    DELETE_JOB = "delete_job"
    
    # Log & analysis
    SEARCH_LOGS = "search_logs"
    COMPARE_BUILDS = "compare_builds"
    BUILD_CHANGES = "build_changes"
    
    # Pipeline
    PIPELINE_STAGES = "pipeline_stages"
    
    # System
    SYSTEM_INFO = "system_info"
    PLUGIN_LIST = "plugin_list"
    CREDENTIALS_LIST = "credentials_list"
    
    # Workspace
    WORKSPACE_CLEANUP = "workspace_cleanup"
    
    # SCM
    SCM_POLL = "scm_poll"
    
    # Misc
    HELP = "help"
    UNKNOWN = "unknown"


class BuildStatus(Enum):
    """Build status types."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    BUILDING = "BUILDING"
    QUEUED = "QUEUED"
    ABORTED = "ABORTED"
    UNSTABLE = "UNSTABLE"
    NOT_BUILT = "NOT_BUILT"
    UNKNOWN = "UNKNOWN"


@dataclass
class BuildRequest:
    """Represents a parsed build request from user input."""
    intent: Intent = Intent.UNKNOWN
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    job_name: Optional[str] = None
    build_number: Optional[int] = None  # For specific build operations
    node_name: Optional[str] = None  # For node operations
    search_term: Optional[str] = None  # For log search
    compare_builds: list[int] = field(default_factory=list)  # Build numbers to compare
    artifacts: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    raw_message: str = ""


@dataclass
class BuildInfo:
    """Information about a Jenkins build."""
    job_name: str
    build_number: int
    status: BuildStatus = BuildStatus.UNKNOWN
    url: str = ""
    building: bool = False
    duration: int = 0  # milliseconds
    timestamp: Optional[datetime] = None
    
    @property
    def duration_str(self) -> str:
        """Format duration as human-readable string."""
        if self.duration <= 0:
            return "0s"
        
        seconds = self.duration // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


@dataclass
class BuildResult:
    """Complete build result with all information."""
    build_info: BuildInfo
    console_output: str = ""
    artifacts_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class JobInfo:
    """Information about a Jenkins job."""
    name: str
    url: str = ""
    color: str = ""
    last_build_number: Optional[int] = None
    last_build_status: Optional[BuildStatus] = None
    
    @property
    def status_emoji(self) -> str:
        """Get emoji for job status."""
        color_map = {
            "blue": "✅",
            "green": "✅",
            "red": "❌",
            "yellow": "⚠️",
            "grey": "⏸️",
            "disabled": "🚫",
            "aborted": "⏹️",
            "notbuilt": "🔘",
        }
        # Remove "_anime" suffix for building jobs
        base_color = self.color.replace("_anime", "") if self.color else ""
        return color_map.get(base_color, "❓")
    
    @property
    def status_text(self) -> str:
        """Get status text."""
        if "_anime" in self.color:
            return "Building"
        
        color_map = {
            "blue": "Last Success",
            "green": "Last Success",
            "red": "Last Failed",
            "yellow": "Unstable",
            "grey": "Pending",
            "disabled": "Disabled",
            "aborted": "Aborted",
            "notbuilt": "Not Built",
        }
        return color_map.get(self.color, "Unknown")


@dataclass
class ArtifactInfo:
    """Information about a build artifact."""
    filename: str
    path: str
    size: int = 0
    url: str = ""
