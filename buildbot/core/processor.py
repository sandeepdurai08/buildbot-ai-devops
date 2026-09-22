"""
BuildBot Request Processor - Token Optimized
Handles most commands directly without LLM to minimize token usage.
Only uses LLM for complex natural language that needs parsing.
"""

import logging
import re
import time
from typing import Optional, Callable
from datetime import datetime

from .models import (
    BuildRequest, BuildInfo, BuildResult, BuildStatus, 
    Intent, ArtifactInfo
)
from .conversation import ConversationManager

import sys
sys.path.append('..')
from config import settings

logger = logging.getLogger(__name__)


# Direct command patterns (no LLM needed)
DIRECT_COMMANDS = {
    # Exact matches - Help
    "help": Intent.HELP,
    "h": Intent.HELP,
    "?": Intent.HELP,
    
    # Jobs & Views
    "list jobs": Intent.LIST_JOBS,
    "jobs": Intent.LIST_JOBS,
    "show jobs": Intent.LIST_JOBS,
    "list views": Intent.LIST_VIEWS,
    "views": Intent.LIST_VIEWS,
    "show views": Intent.LIST_VIEWS,
    
    # Status
    "status": Intent.CHECK_STATUS,
    "check status": Intent.CHECK_STATUS,
    "build status": Intent.CHECK_STATUS,
    
    # Rebuild
    "rebuild": Intent.REBUILD,
    "rebuild last": Intent.REBUILD,
    "retry": Intent.REBUILD,
    "retry last": Intent.REBUILD,
    
    # Artifacts
    "latest artifacts": Intent.GET_LATEST_ARTIFACTS,
    "artifacts": Intent.GET_LATEST_ARTIFACTS,
    "show artifacts": Intent.GET_LATEST_ARTIFACTS,
    "get artifacts": Intent.GET_LATEST_ARTIFACTS,
    
    # Queue
    "queue": Intent.QUEUE_STATUS,
    "queue status": Intent.QUEUE_STATUS,
    "show queue": Intent.QUEUE_STATUS,
    "build queue": Intent.QUEUE_STATUS,
    "pending builds": Intent.QUEUE_STATUS,
    "queued builds": Intent.QUEUE_STATUS,
    
    # Nodes/Agents
    "nodes": Intent.NODE_LIST,
    "list nodes": Intent.NODE_LIST,
    "agents": Intent.NODE_LIST,
    "list agents": Intent.NODE_LIST,
    "show nodes": Intent.NODE_LIST,
    "show agents": Intent.NODE_LIST,
    "workers": Intent.NODE_LIST,
    
    # System
    "system": Intent.SYSTEM_INFO,
    "system info": Intent.SYSTEM_INFO,
    "system status": Intent.SYSTEM_INFO,
    "jenkins info": Intent.SYSTEM_INFO,
    "server info": Intent.SYSTEM_INFO,
    "server status": Intent.SYSTEM_INFO,
    
    # Plugins
    "plugins": Intent.PLUGIN_LIST,
    "list plugins": Intent.PLUGIN_LIST,
    "show plugins": Intent.PLUGIN_LIST,
    "installed plugins": Intent.PLUGIN_LIST,
    
    # Credentials
    "credentials": Intent.CREDENTIALS_LIST,
    "list credentials": Intent.CREDENTIALS_LIST,
    "show credentials": Intent.CREDENTIALS_LIST,
}

# Regex patterns for direct matching
BUILD_PATTERN = re.compile(r'^build\s+(\S+)(?:\s+from\s+(\S+))?$', re.IGNORECASE)
HISTORY_PATTERN = re.compile(r'^history(?:\s+of)?\s+(\S+)$', re.IGNORECASE)
ARTIFACTS_PATTERN = re.compile(r'^(?:latest\s+)?artifacts\s+(?:of|from)\s+(\S+)$', re.IGNORECASE)
VIEW_JOBS_PATTERN = re.compile(r'^jobs\s+in\s+(?:view\s+)?(\S+)$', re.IGNORECASE)

# New patterns for expanded commands
ABORT_PATTERN = re.compile(r'^(?:abort|stop|cancel)\s+(?:build\s+)?(\S+)(?:\s+#?(\d+))?$', re.IGNORECASE)
DISABLE_PATTERN = re.compile(r'^disable\s+(?:job\s+)?(\S+)$', re.IGNORECASE)
ENABLE_PATTERN = re.compile(r'^enable\s+(?:job\s+)?(\S+)$', re.IGNORECASE)
NODE_STATUS_PATTERN = re.compile(r'^(?:node|agent)\s+(?:status\s+)?(\S+)$', re.IGNORECASE)
NODE_OFFLINE_PATTERN = re.compile(r'^(?:take\s+)?(?:node|agent)\s+(\S+)\s+offline$', re.IGNORECASE)
NODE_ONLINE_PATTERN = re.compile(r'^(?:bring\s+)?(?:node|agent)\s+(\S+)\s+online$', re.IGNORECASE)
SEARCH_LOGS_PATTERN = re.compile(r'^search\s+(?:logs?\s+)?(?:for\s+)?["\']?(.+?)["\']?\s+in\s+(\S+)(?:\s+#?(\d+))?$', re.IGNORECASE)
COMPARE_PATTERN = re.compile(r'^compare\s+(?:builds?\s+)?(\S+)\s+#?(\d+)\s+(?:and|vs|with)\s+#?(\d+)$', re.IGNORECASE)
CHANGES_PATTERN = re.compile(r'^(?:changes|commits|changelog)\s+(?:for\s+)?(\S+)(?:\s+#?(\d+))?$', re.IGNORECASE)
STAGES_PATTERN = re.compile(r'^(?:stages|pipeline)\s+(?:of\s+)?(\S+)(?:\s+#?(\d+))?$', re.IGNORECASE)
WIPE_PATTERN = re.compile(r'^(?:wipe|clean|cleanup)\s+(?:workspace\s+)?(?:of\s+)?(\S+)$', re.IGNORECASE)
POLL_PATTERN = re.compile(r'^(?:poll|scm\s+poll)\s+(\S+)$', re.IGNORECASE)
JOB_INFO_PATTERN = re.compile(r'^(?:info|details?)\s+(?:about\s+)?(?:job\s+)?(\S+)$', re.IGNORECASE)
QUEUE_CANCEL_PATTERN = re.compile(r'^cancel\s+queue(?:d)?\s+(?:item\s+)?#?(\d+)$', re.IGNORECASE)


class RequestProcessor:
    """Token-optimized processor - handles simple commands directly."""
    
    def __init__(
        self,
        llm_service,
        jenkins_service,
        notification_service,
        artifact_service,
        conversation: ConversationManager,
        github_service=None
    ):
        self.llm = llm_service
        self.jenkins = jenkins_service
        self.notifications = notification_service
        self.artifacts = artifact_service
        self.conversation = conversation
        self.allowed_repos = settings.app.get_allowed_repos_list()
        
        if github_service:
            self.github = github_service
        else:
            from services.github_service import github_service as gh_svc
            self.github = gh_svc
    
    def _try_direct_parse(self, message: str) -> Optional[BuildRequest]:
        """
        Try to parse message directly without LLM.
        Returns BuildRequest if parsed, None if LLM needed.
        """
        msg = message.strip().lower()
        
        # Check exact matches first
        if msg in DIRECT_COMMANDS:
            return BuildRequest(
                intent=DIRECT_COMMANDS[msg],
                raw_message=message
            )
        
        # Check build pattern: "build X from Y" or "build X"
        match = BUILD_PATTERN.match(message.strip())
        if match:
            job_or_repo = match.group(1)
            branch = match.group(2)
            
            # Determine if it's a job name or repo URL
            if '/' in job_or_repo and ('github' in job_or_repo.lower() or 'http' in job_or_repo.lower()):
                return BuildRequest(
                    intent=Intent.NEW_BUILD,
                    repo_url=job_or_repo,
                    branch=branch,
                    raw_message=message
                )
            else:
                return BuildRequest(
                    intent=Intent.NEW_BUILD,
                    job_name=job_or_repo,
                    branch=branch or "main",
                    raw_message=message
                )
        
        # Check history pattern: "history of X" or "history X"
        match = HISTORY_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.JOB_HISTORY,
                job_name=match.group(1),
                raw_message=message
            )
        
        # Check artifacts pattern: "artifacts of X"
        match = ARTIFACTS_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.GET_LATEST_ARTIFACTS,
                job_name=match.group(1),
                raw_message=message
            )
        
        # Check view jobs pattern: "jobs in view X"
        match = VIEW_JOBS_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.VIEW_JOBS,
                job_name=match.group(1),  # Using job_name to store view name
                raw_message=message
            )
        
        # ── New patterns ──────────────────────────────────────────────────
        
        # Abort build: "abort job_name #123" or "stop job_name"
        match = ABORT_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.ABORT_BUILD,
                job_name=match.group(1),
                build_number=int(match.group(2)) if match.group(2) else None,
                raw_message=message
            )
        
        # Disable job: "disable job_name"
        match = DISABLE_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.DISABLE_JOB,
                job_name=match.group(1),
                raw_message=message
            )
        
        # Enable job: "enable job_name"
        match = ENABLE_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.ENABLE_JOB,
                job_name=match.group(1),
                raw_message=message
            )
        
        # Node status: "node master" or "agent slave1"
        match = NODE_STATUS_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.NODE_STATUS,
                node_name=match.group(1),
                raw_message=message
            )
        
        # Node offline: "take node X offline"
        match = NODE_OFFLINE_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.NODE_OFFLINE,
                node_name=match.group(1),
                raw_message=message
            )
        
        # Node online: "bring node X online"
        match = NODE_ONLINE_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.NODE_ONLINE,
                node_name=match.group(1),
                raw_message=message
            )
        
        # Search logs: "search 'error' in job_name #123"
        match = SEARCH_LOGS_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.SEARCH_LOGS,
                search_term=match.group(1),
                job_name=match.group(2),
                build_number=int(match.group(3)) if match.group(3) else None,
                raw_message=message
            )
        
        # Compare builds: "compare job_name #1 and #2"
        match = COMPARE_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.COMPARE_BUILDS,
                job_name=match.group(1),
                compare_builds=[int(match.group(2)), int(match.group(3))],
                raw_message=message
            )
        
        # Build changes: "changes for job_name #123"
        match = CHANGES_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.BUILD_CHANGES,
                job_name=match.group(1),
                build_number=int(match.group(2)) if match.group(2) else None,
                raw_message=message
            )
        
        # Pipeline stages: "stages of job_name #123"
        match = STAGES_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.PIPELINE_STAGES,
                job_name=match.group(1),
                build_number=int(match.group(2)) if match.group(2) else None,
                raw_message=message
            )
        
        # Wipe workspace: "wipe workspace of job_name"
        match = WIPE_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.WORKSPACE_CLEANUP,
                job_name=match.group(1),
                raw_message=message
            )
        
        # SCM Poll: "poll job_name"
        match = POLL_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.SCM_POLL,
                job_name=match.group(1),
                raw_message=message
            )
        
        # Job info: "info about job_name"
        match = JOB_INFO_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.JOB_INFO,
                job_name=match.group(1),
                raw_message=message
            )
        
        # Queue cancel: "cancel queue #123"
        match = QUEUE_CANCEL_PATTERN.match(message.strip())
        if match:
            return BuildRequest(
                intent=Intent.QUEUE_CANCEL,
                build_number=int(match.group(1)),  # Using build_number for queue ID
                raw_message=message
            )
        
        # Check for simple keywords
        msg_words = msg.split()
        if len(msg_words) <= 3:
            if "help" in msg_words:
                return BuildRequest(intent=Intent.HELP, raw_message=message)
            if "jobs" in msg_words and "list" in msg_words:
                return BuildRequest(intent=Intent.LIST_JOBS, raw_message=message)
            if "status" in msg_words:
                return BuildRequest(intent=Intent.CHECK_STATUS, raw_message=message)
            if "rebuild" in msg_words:
                return BuildRequest(intent=Intent.REBUILD, raw_message=message)
            if "queue" in msg_words:
                return BuildRequest(intent=Intent.QUEUE_STATUS, raw_message=message)
            if "nodes" in msg_words or "agents" in msg_words:
                return BuildRequest(intent=Intent.NODE_LIST, raw_message=message)
            if "system" in msg_words:
                return BuildRequest(intent=Intent.SYSTEM_INFO, raw_message=message)
            if "plugins" in msg_words:
                return BuildRequest(intent=Intent.PLUGIN_LIST, raw_message=message)
        
        # Can't parse directly - need LLM
        return None
    
    def _validate_branch_name(self, branch: str) -> tuple[bool, str]:
        """Validate branch name format."""
        if not branch:
            return False, "Branch name is required"
        
        branch = branch.strip()
        dangerous_chars = [';', '|', '`', '$', '(', ')', '{', '}', '<', '>', '&', '\\']
        for char in dangerous_chars:
            if char in branch:
                return False, f"Invalid character '{char}' in branch name"
        
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9/_.-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$'
        if not re.match(pattern, branch):
            return False, "Invalid branch name format"
        
        return True, ""
    
    def _validate_repo_url(self, url: str) -> tuple[bool, str]:
        """Validate repository URL."""
        if not url:
            return False, "Repository URL is required"
        
        url_normalized = url.lower().strip()
        for prefix in ['https://', 'http://', 'git@', 'git://']:
            if url_normalized.startswith(prefix):
                url_normalized = url_normalized[len(prefix):]
                break
        
        if '..' in url or ';' in url or '|' in url:
            return False, "Invalid characters in URL"
        
        for allowed in self.allowed_repos:
            if allowed.lower() in url_normalized:
                return True, ""
        
        return False, f"Repository not allowed. Allowed: {', '.join(self.allowed_repos)}"
    
    def process_message(
        self, 
        message: str,
        status_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Process a user message and return a response."""
        def update_status(text: str):
            if status_callback:
                status_callback(text)

        msg_lower = message.strip().lower()

        # ── 1. User is answering a parameter prompt ───────────────────────
        if self.conversation.has_pending_params():
            next_prompt = self.conversation.collect_param_value(message)
            if next_prompt:
                # More params to collect
                return next_prompt
            else:
                # All params collected — proceed to confirmation or build
                request = self.conversation.context.pending_request
                params  = self.conversation.get_collected_params()
                # Store collected params on the request for _handle_build_request
                request._extra_params = params
                self.conversation.set_awaiting_confirmation(request)
                return self._confirmation_prompt(request, params)

        # ── 2. User is answering the yes/no confirmation ──────────────────
        if self.conversation.is_awaiting_confirmation():
            if msg_lower in ("yes", "y", "confirm", "ok", "go", "do it",
                             "proceed", "sure", "yep", "yeah", "trigger"):
                request = self.conversation.confirm_build()
                if request:
                    return self._execute_build(request, update_status)
                return "❌ Lost the build request — please try again."
            elif msg_lower in ("no", "n", "cancel", "stop", "abort",
                               "nope", "nah", "never mind", "nevermind"):
                self.conversation.cancel_confirmation()
                return "🚫 Build cancelled. What else can I help with?"
            else:
                # Still pending — re-ask
                return ("Please reply **yes** to trigger the build or "
                        "**no** to cancel.")

        # ── 3. User is completing a missing-field prompt ──────────────────
        if self.conversation.has_pending_request():
            completed = self.conversation.complete_pending_request(message)
            if completed:
                # If what was pending was "job_name", handle numeric selection
                if completed.job_name and completed.job_name.isdigit():
                    try:
                        jobs = self.jenkins.list_jobs()
                        idx  = int(completed.job_name) - 1
                        if 0 <= idx < len(jobs):
                            completed.job_name = jobs[idx].name
                        else:
                            return f"❌ No job #{completed.job_name}. Try again."
                    except Exception:
                        pass
                return self._start_build_flow(completed, update_status)
            else:
                awaiting = self.conversation.context.awaiting_field
                return f"I still need the **{awaiting}**. What is it?"

        # ── 4. Normal parse → route ───────────────────────────────────────
        request = self._try_direct_parse(message)
        if request is None:
            update_status("Processing…")
            context = self.conversation.get_context_summary()
            request = self.llm.parse_build_request(message, context)
        else:
            logger.info(f"Direct parse success: {request.intent}")

        request = self.conversation.resolve_references(request)

        if request.intent == Intent.UNKNOWN:
            return self._handle_unknown(request)
        elif request.intent == Intent.HELP:
            return self._handle_help()
        elif request.intent == Intent.LIST_JOBS:
            return self._handle_list_jobs()
        elif request.intent == Intent.LIST_VIEWS:
            return self._handle_list_views()
        elif request.intent == Intent.VIEW_JOBS:
            return self._handle_view_jobs(request.job_name or message)
        elif request.intent == Intent.JOB_HISTORY:
            return self._handle_job_history(request.job_name or message)
        elif request.intent == Intent.JOB_INFO:
            return self._handle_job_info(request.job_name or message)
        elif request.intent == Intent.CHECK_STATUS:
            return self._handle_status_check()
        elif request.intent == Intent.GET_ARTIFACTS:
            return self._handle_artifact_request(request)
        elif request.intent == Intent.GET_LATEST_ARTIFACTS:
            return self._handle_latest_artifacts(request.job_name or message)
        elif request.intent in (Intent.NEW_BUILD, Intent.REBUILD):
            return self._handle_build_request(request, update_status)
        
        # ── Queue management ──────────────────────────────────────────────
        elif request.intent == Intent.QUEUE_STATUS:
            return self._handle_queue_status()
        elif request.intent == Intent.QUEUE_CANCEL:
            return self._handle_queue_cancel(request.build_number)
        
        # ── Build operations ──────────────────────────────────────────────
        elif request.intent == Intent.ABORT_BUILD:
            return self._handle_abort_build(request)
        elif request.intent == Intent.BUILD_CHANGES:
            return self._handle_build_changes(request)
        elif request.intent == Intent.COMPARE_BUILDS:
            return self._handle_compare_builds(request)
        elif request.intent == Intent.SEARCH_LOGS:
            return self._handle_search_logs(request)
        elif request.intent == Intent.PIPELINE_STAGES:
            return self._handle_pipeline_stages(request)
        
        # ── Node/Agent management ─────────────────────────────────────────
        elif request.intent == Intent.NODE_LIST:
            return self._handle_node_list()
        elif request.intent == Intent.NODE_STATUS:
            return self._handle_node_status(request.node_name)
        elif request.intent == Intent.NODE_OFFLINE:
            return self._handle_node_offline(request.node_name)
        elif request.intent == Intent.NODE_ONLINE:
            return self._handle_node_online(request.node_name)
        
        # ── Job management ────────────────────────────────────────────────
        elif request.intent == Intent.DISABLE_JOB:
            return self._handle_disable_job(request.job_name)
        elif request.intent == Intent.ENABLE_JOB:
            return self._handle_enable_job(request.job_name)
        elif request.intent == Intent.WORKSPACE_CLEANUP:
            return self._handle_workspace_cleanup(request.job_name)
        elif request.intent == Intent.SCM_POLL:
            return self._handle_scm_poll(request.job_name)
        
        # ── System information ────────────────────────────────────────────
        elif request.intent == Intent.SYSTEM_INFO:
            return self._handle_system_info()
        elif request.intent == Intent.PLUGIN_LIST:
            return self._handle_plugin_list()
        elif request.intent == Intent.CREDENTIALS_LIST:
            return self._handle_credentials_list()

        return self._handle_unknown(request)
    
    def _handle_unknown(self, request: BuildRequest) -> str:
        return (
            "I couldn't understand that. Try:\n\n"
            "• `list jobs` - See all jobs\n"
            "• `build <job> from <branch>` - Trigger build\n"
            "• `history <job>` - Build history\n"
            "• `status` - Check status\n"
            "• `help` - All commands"
        )
    
    def _handle_help(self) -> str:
        return """
**🔧 Jenkins Build Bot - Complete Command Reference**

**📦 Build Operations:**
• `build <job> from <branch>` - Trigger new build
• `rebuild` - Rebuild last job
• `abort <job> #N` - Stop a running build
• `status` - Check last build status

**📋 Job Management:**
• `list jobs` or `jobs` - All jobs
• `list views` or `views` - All views  
• `jobs in view <name>` - Jobs in a view
• `history <job>` - Build history
• `info <job>` - Job details & parameters
• `disable <job>` - Disable a job
• `enable <job>` - Enable a job
• `poll <job>` - Trigger SCM polling
• `wipe <job>` - Clean workspace

**📊 Build Analysis:**
• `changes <job> #N` - Commits in a build
• `compare <job> #1 vs #2` - Compare builds
• `stages <job> #N` - Pipeline stages
• `search "error" in <job> #N` - Search logs

**📦 Artifacts:**
• `artifacts` - Latest artifacts
• `artifacts of <job>` - From specific job

**🖥️ Nodes & Agents:**
• `nodes` or `agents` - List all nodes
• `node <name>` - Node status
• `node <name> offline` - Take offline
• `node <name> online` - Bring online

**⏳ Queue Management:**
• `queue` - Show build queue
• `cancel queue #ID` - Cancel queued item

**🔧 System:**
• `system info` - Jenkins overview
• `plugins` - Installed plugins
• `credentials` - Credential domains

**Examples:**
• `build HOT_fix_job from develop`
• `abort HOT_fix_job #42`
• `compare HOT_fix_job #10 vs #15`
• `search "NullPointer" in HOT_fix_job #42`
"""
    
    def _handle_list_jobs(self) -> str:
        try:
            jobs = self.jenkins.list_jobs()
            if not jobs:
                return "No jobs found in Jenkins."
            
            lines = ["**📋 Jenkins Jobs:**\n"]
            for job in jobs:
                emoji = job.status_emoji
                build = f"#{job.last_build_number}" if job.last_build_number else "No builds"
                lines.append(f"• {emoji} **{job.name}** - {job.status_text} ({build})")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error listing jobs: {e}"
    
    def _handle_list_views(self) -> str:
        try:
            views = self.jenkins.list_views()
            if not views:
                return "No views found."
            
            lines = ["**📁 Jenkins Views:**\n"]
            for view in views:
                lines.append(f"• **{view['name']}**")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error listing views: {e}"
    
    def _handle_view_jobs(self, message: str) -> str:
        # Extract view name
        view_name = message
        match = VIEW_JOBS_PATTERN.match(message)
        if match:
            view_name = match.group(1)
        else:
            # Try to extract from message
            words = message.lower().replace("jobs in view", "").replace("jobs in", "").strip().split()
            if words:
                view_name = words[0]
        
        try:
            jobs = self.jenkins.get_jobs_in_view(view_name)
            if not jobs:
                return f"No jobs in view '{view_name}'."
            
            lines = [f"**Jobs in {view_name}:**\n"]
            for job in jobs:
                lines.append(f"• {job.status_emoji} **{job.name}**")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_job_history(self, message: str) -> str:
        # Extract job name
        job_name = message
        match = HISTORY_PATTERN.match(message)
        if match:
            job_name = match.group(1)
        else:
            # Try to find job name
            for word in message.split():
                if word.lower() not in ['history', 'of', 'for', 'show']:
                    job_name = word
                    break
        
        try:
            history = self.jenkins.get_build_history(job_name, limit=10)
            if not history:
                return f"No build history for '{job_name}'."
            
            lines = [f"**📊 History of {job_name}:**\n"]
            for build in history:
                result = build.get("result", "UNKNOWN")
                emoji = "✅" if result == "SUCCESS" else "❌" if result == "FAILURE" else "🔄"
                num = build.get("number", "?")
                lines.append(f"• {emoji} **#{num}** - {result}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_status_check(self) -> str:
        last = self.conversation.context.last_build
        if not last:
            return "No recent builds. Use `list jobs` to see available jobs."
        
        try:
            info = self.jenkins.get_build_status(last.job_name, last.build_number)
            emoji = "✅" if info.status == BuildStatus.SUCCESS else "❌" if info.status == BuildStatus.FAILURE else "🔄"
            return f"{emoji} **{last.job_name} #{last.build_number}** - {info.status.name}"
        except Exception as e:
            return f"❌ Error checking status: {e}"
    
    def _handle_latest_artifacts(self, message: str) -> str:
        # Determine job name
        job_name = None
        match = ARTIFACTS_PATTERN.match(message)
        if match:
            job_name = match.group(1)
        elif self.conversation.context.last_build:
            job_name = self.conversation.context.last_build.job_name
        else:
            job_name = settings.jenkins.default_job
        
        try:
            url, build_num, artifacts = self.jenkins.get_latest_artifacts_path(job_name)
            
            if not artifacts:
                return f"No artifacts found for **{job_name}**."
            
            lines = [f"**📦 Artifacts from {job_name} #{build_num}:**\n"]
            for art in artifacts[:10]:
                lines.append(f"• `{art.filename}`")
            
            if url:
                lines.append(f"\n📁 **Path:** {url}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    # ─────────────────────────────────────────────────────────────────────
    #  JOB INFO HANDLER
    # ─────────────────────────────────────────────────────────────────────
    def _handle_job_info(self, message: str) -> str:
        """Get detailed job information."""
        job_name = message
        match = JOB_INFO_PATTERN.match(message)
        if match:
            job_name = match.group(1)
        
        try:
            info = self.jenkins.get_job_info(job_name)
            params = self.jenkins.get_job_parameters(job_name)
            
            # Basic info
            color = info.get("color", "unknown")
            last_build = info.get("lastBuild", {})
            last_success = info.get("lastSuccessfulBuild", {})
            last_failed = info.get("lastFailedBuild", {})
            
            emoji = "✅" if "blue" in color or "green" in color else "❌" if "red" in color else "🔄" if "anime" in color else "⏸️"
            
            lines = [f"**{emoji} Job: {job_name}**\n"]
            
            if last_build:
                lines.append(f"• **Last Build:** #{last_build.get('number', '?')}")
            if last_success:
                lines.append(f"• **Last Success:** #{last_success.get('number', '?')}")
            if last_failed:
                lines.append(f"• **Last Failed:** #{last_failed.get('number', '?')}")
            
            lines.append(f"• **Buildable:** {'Yes' if info.get('buildable', False) else 'No'}")
            
            if info.get("description"):
                lines.append(f"• **Description:** {info['description'][:100]}")
            
            # Parameters
            if params:
                lines.append(f"\n**📋 Parameters ({len(params)}):**")
                for p in params[:8]:
                    default = f" = `{p['default']}`" if p['default'] else ""
                    lines.append(f"• `{p['name']}`{default}")
                if len(params) > 8:
                    lines.append(f"  ... and {len(params) - 8} more")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error getting job info: {e}"
    
    # ─────────────────────────────────────────────────────────────────────
    #  QUEUE MANAGEMENT HANDLERS
    # ─────────────────────────────────────────────────────────────────────
    def _handle_queue_status(self) -> str:
        """Show current build queue."""
        try:
            items = self.jenkins.get_queue_status()
            
            if not items:
                return "✅ **Build queue is empty.** No pending builds."
            
            lines = [f"**⏳ Build Queue ({len(items)} item{'s' if len(items) != 1 else ''}):**\n"]
            
            for item in items:
                stuck = "🔴 STUCK" if item["stuck"] else ""
                blocked = "🚫 BLOCKED" if item["blocked"] else ""
                status = stuck or blocked or "⏳"
                lines.append(f"• {status} **{item['job_name']}** (Queue #{item['id']})")
                if item["why"]:
                    lines.append(f"  ↳ {item['why'][:80]}")
            
            lines.append("\n💡 Use `cancel queue #ID` to remove an item.")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error getting queue: {e}"
    
    def _handle_queue_cancel(self, queue_id: int) -> str:
        """Cancel a queued build."""
        if not queue_id:
            return "❌ Please specify a queue ID: `cancel queue #123`"
        
        try:
            success = self.jenkins.cancel_queue_item(queue_id)
            if success:
                return f"✅ Cancelled queue item **#{queue_id}**"
            return f"❌ Failed to cancel queue item #{queue_id}"
        except Exception as e:
            return f"❌ Error: {e}"
    
    # ─────────────────────────────────────────────────────────────────────
    #  BUILD OPERATION HANDLERS
    # ─────────────────────────────────────────────────────────────────────
    def _handle_abort_build(self, request: BuildRequest) -> str:
        """Abort a running build."""
        job_name = request.job_name
        build_num = request.build_number
        
        if not job_name:
            if self.conversation.context.last_build:
                job_name = self.conversation.context.last_build.job_name
                build_num = build_num or self.conversation.context.last_build.build_number
            else:
                return "❌ Please specify a job: `abort job_name #123`"
        
        if not build_num:
            # Get latest running build
            try:
                info = self.jenkins.get_job_info(job_name)
                last = info.get("lastBuild", {})
                if last:
                    status = self.jenkins.get_build_status(job_name, last["number"])
                    if status.building:
                        build_num = last["number"]
                    else:
                        return f"❌ No running build found for **{job_name}**"
                else:
                    return f"❌ No builds found for **{job_name}**"
            except Exception as e:
                return f"❌ Error: {e}"
        
        try:
            success = self.jenkins.abort_build(job_name, build_num)
            if success:
                return f"🛑 Aborted **{job_name} #{build_num}**"
            return f"❌ Failed to abort build"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_build_changes(self, request: BuildRequest) -> str:
        """Show commits/changes in a build."""
        job_name = request.job_name
        build_num = request.build_number
        
        if not job_name:
            if self.conversation.context.last_build:
                job_name = self.conversation.context.last_build.job_name
                build_num = build_num or self.conversation.context.last_build.build_number
            else:
                return "❌ Please specify: `changes job_name #123`"
        
        if not build_num:
            try:
                info = self.jenkins.get_job_info(job_name)
                build_num = info.get("lastBuild", {}).get("number")
            except Exception:
                pass
        
        if not build_num:
            return f"❌ Please specify build number: `changes {job_name} #123`"
        
        try:
            changes = self.jenkins.get_build_changes(job_name, build_num)
            
            if not changes:
                return f"📝 No SCM changes found in **{job_name} #{build_num}**"
            
            lines = [f"**📝 Changes in {job_name} #{build_num}:**\n"]
            for c in changes[:10]:
                lines.append(f"• **{c['commit_id']}** by {c['author']}")
                lines.append(f"  ↳ {c['message'][:80]}")
            
            if len(changes) > 10:
                lines.append(f"\n... and {len(changes) - 10} more commits")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_compare_builds(self, request: BuildRequest) -> str:
        """Compare two builds."""
        job_name = request.job_name
        builds = request.compare_builds
        
        if not job_name or len(builds) < 2:
            return "❌ Usage: `compare job_name #1 vs #2`"
        
        try:
            result = self.jenkins.compare_builds(job_name, builds[0], builds[1])
            
            b1, b2 = result["build1"], result["build2"]
            
            # Duration comparison
            diff_ms = result["duration_diff"]
            diff_sec = abs(diff_ms) // 1000
            faster = "faster" if diff_ms < 0 else "slower"
            
            lines = [
                f"**📊 Comparing {job_name} #{builds[0]} vs #{builds[1]}**\n",
                f"| Build | Status | Duration | Changes |",
                f"|-------|--------|----------|---------|",
                f"| #{b1['number']} | {b1['status']} | {b1['duration']//1000}s | {b1['changes']} |",
                f"| #{b2['number']} | {b2['status']} | {b2['duration']//1000}s | {b2['changes']} |",
                f"",
                f"**Summary:**",
            ]
            
            if result["status_changed"]:
                lines.append(f"• ⚠️ Status changed: {b1['status']} → {b2['status']}")
            else:
                lines.append(f"• ✅ Status unchanged: {b1['status']}")
            
            if diff_sec > 0:
                lines.append(f"• ⏱️ Build #{builds[1]} is **{diff_sec}s {faster}**")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_search_logs(self, request: BuildRequest) -> str:
        """Search build logs for a term."""
        job_name = request.job_name
        build_num = request.build_number
        search_term = request.search_term
        
        if not job_name or not search_term:
            return "❌ Usage: `search \"error\" in job_name #123`"
        
        if not build_num:
            try:
                info = self.jenkins.get_job_info(job_name)
                build_num = info.get("lastBuild", {}).get("number")
            except Exception:
                pass
        
        if not build_num:
            return f"❌ Please specify build number"
        
        try:
            results = self.jenkins.search_console_logs(job_name, build_num, search_term)
            
            if not results:
                return f"🔍 No matches for **\"{search_term}\"** in {job_name} #{build_num}"
            
            lines = [f"**🔍 Found {len(results)} match{'es' if len(results) != 1 else ''} for \"{search_term}\":**\n"]
            
            for r in results[:15]:
                lines.append(f"• **Line {r['line_number']}:** `{r['content'][:100]}`")
            
            if len(results) > 15:
                lines.append(f"\n... and {len(results) - 15} more matches")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_pipeline_stages(self, request: BuildRequest) -> str:
        """Show pipeline stages for a build."""
        job_name = request.job_name
        build_num = request.build_number
        
        if not job_name:
            return "❌ Usage: `stages job_name #123`"
        
        if not build_num:
            try:
                info = self.jenkins.get_job_info(job_name)
                build_num = info.get("lastBuild", {}).get("number")
            except Exception:
                pass
        
        if not build_num:
            return f"❌ Please specify build number"
        
        try:
            stages = self.jenkins.get_pipeline_stages(job_name, build_num)
            
            if not stages:
                return f"📋 No pipeline stages found for **{job_name} #{build_num}**\n(Job may not be a Pipeline or plugin not installed)"
            
            lines = [f"**📋 Pipeline Stages for {job_name} #{build_num}:**\n"]
            
            for s in stages:
                emoji = "✅" if s["status"] == "SUCCESS" else "❌" if s["status"] == "FAILED" else "🔄" if s["status"] == "IN_PROGRESS" else "⏸️"
                dur = s["duration"] // 1000
                lines.append(f"• {emoji} **{s['name']}** - {s['status']} ({dur}s)")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    # ─────────────────────────────────────────────────────────────────────
    #  NODE/AGENT HANDLERS
    # ─────────────────────────────────────────────────────────────────────
    def _handle_node_list(self) -> str:
        """List all Jenkins nodes/agents."""
        try:
            nodes = self.jenkins.get_nodes()
            
            if not nodes:
                return "No nodes found."
            
            lines = [f"**🖥️ Jenkins Nodes ({len(nodes)}):**\n"]
            
            for node in nodes:
                if node["offline"]:
                    emoji = "🔴"
                    status = "Offline"
                elif not node["idle"]:
                    emoji = "🟡"
                    status = "Busy"
                else:
                    emoji = "🟢"
                    status = "Online"
                
                executors = node["num_executors"]
                lines.append(f"• {emoji} **{node['name']}** - {status} ({executors} executor{'s' if executors != 1 else ''})")
                
                if node["offline"] and node["offline_reason"]:
                    lines.append(f"  ↳ {node['offline_reason'][:60]}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_node_status(self, node_name: str) -> str:
        """Get detailed status of a node."""
        if not node_name:
            return "❌ Please specify a node: `node master`"
        
        try:
            status = self.jenkins.get_node_status(node_name)
            
            if status["offline"]:
                emoji = "🔴"
                state = "OFFLINE"
            elif status["busy_executors"] > 0:
                emoji = "🟡"
                state = "BUSY"
            else:
                emoji = "🟢"
                state = "IDLE"
            
            lines = [
                f"**{emoji} Node: {status['name']}** ({state})\n",
                f"• **Executors:** {status['busy_executors']}/{status['num_executors']} busy",
                f"• **Temporarily Offline:** {'Yes' if status['temporarily_offline'] else 'No'}",
            ]
            
            if status["description"]:
                lines.append(f"• **Description:** {status['description'][:80]}")
            
            if status["offline_reason"]:
                lines.append(f"• **Offline Reason:** {status['offline_reason']}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_node_offline(self, node_name: str) -> str:
        """Take a node offline."""
        if not node_name:
            return "❌ Please specify: `node agent1 offline`"
        
        try:
            success = self.jenkins.set_node_offline(node_name, "Taken offline by BuildBot")
            if success:
                return f"🔴 Node **{node_name}** is now offline"
            return f"❌ Failed to take node offline"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_node_online(self, node_name: str) -> str:
        """Bring a node back online."""
        if not node_name:
            return "❌ Please specify: `node agent1 online`"
        
        try:
            success = self.jenkins.set_node_online(node_name)
            if success:
                return f"🟢 Node **{node_name}** is now online"
            return f"❌ Failed to bring node online"
        except Exception as e:
            return f"❌ Error: {e}"
    
    # ─────────────────────────────────────────────────────────────────────
    #  JOB MANAGEMENT HANDLERS
    # ─────────────────────────────────────────────────────────────────────
    def _handle_disable_job(self, job_name: str) -> str:
        """Disable a Jenkins job."""
        if not job_name:
            return "❌ Please specify: `disable job_name`"
        
        try:
            success = self.jenkins.disable_job(job_name)
            if success:
                return f"🚫 Job **{job_name}** has been disabled"
            return f"❌ Failed to disable job"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_enable_job(self, job_name: str) -> str:
        """Enable a Jenkins job."""
        if not job_name:
            return "❌ Please specify: `enable job_name`"
        
        try:
            success = self.jenkins.enable_job(job_name)
            if success:
                return f"✅ Job **{job_name}** has been enabled"
            return f"❌ Failed to enable job"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_workspace_cleanup(self, job_name: str) -> str:
        """Wipe job workspace."""
        if not job_name:
            return "❌ Please specify: `wipe job_name`"
        
        try:
            success = self.jenkins.wipe_workspace(job_name)
            if success:
                return f"🧹 Workspace for **{job_name}** has been wiped"
            return f"❌ Failed to wipe workspace"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_scm_poll(self, job_name: str) -> str:
        """Trigger SCM polling for a job."""
        if not job_name:
            return "❌ Please specify: `poll job_name`"
        
        try:
            success = self.jenkins.trigger_scm_poll(job_name)
            if success:
                return f"🔄 SCM polling triggered for **{job_name}**"
            return f"❌ Failed to trigger polling"
        except Exception as e:
            return f"❌ Error: {e}"
    
    # ─────────────────────────────────────────────────────────────────────
    #  SYSTEM INFORMATION HANDLERS
    # ─────────────────────────────────────────────────────────────────────
    def _handle_system_info(self) -> str:
        """Get Jenkins system information."""
        try:
            info = self.jenkins.get_system_info()
            
            lines = [
                f"**🔧 Jenkins System Information**\n",
                f"• **Mode:** {info['mode']}",
                f"• **Jobs:** {info['job_count']}",
                f"• **Views:** {info['view_count']}",
                f"• **Total Executors:** {info['total_executors']}",
                f"• **Busy Executors:** {info['busy_executors']}",
                f"• **Idle Executors:** {info['idle_executors']}",
                f"• **Quiet Mode:** {'Yes ⏸️' if info['quiet_mode'] else 'No'}",
                f"• **Security Enabled:** {'Yes 🔒' if info['use_security'] else 'No'}",
            ]
            
            if info["node_description"]:
                lines.insert(2, f"• **Description:** {info['node_description'][:60]}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_plugin_list(self) -> str:
        """List installed plugins."""
        try:
            plugins = self.jenkins.get_plugins()
            
            if not plugins:
                return "No plugins found."
            
            # Count stats
            enabled = sum(1 for p in plugins if p["enabled"])
            has_update = sum(1 for p in plugins if p["has_update"])
            
            lines = [f"**🔌 Installed Plugins ({len(plugins)})**"]
            lines.append(f"✅ {enabled} enabled • 🔄 {has_update} have updates\n")
            
            # Show first 20 plugins
            for p in plugins[:20]:
                status = "✅" if p["enabled"] else "⏸️"
                update = " 🔄" if p["has_update"] else ""
                lines.append(f"• {status} **{p['name']}** v{p['version']}{update}")
            
            if len(plugins) > 20:
                lines.append(f"\n... and {len(plugins) - 20} more plugins")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _handle_credentials_list(self) -> str:
        """List credential domains."""
        try:
            domains = self.jenkins.get_credentials_domains()
            
            if not domains:
                return "No credential domains found."
            
            lines = [f"**🔐 Credential Domains:**\n"]
            
            for d in domains:
                lines.append(f"• **{d['name']}**")
                if d["description"]:
                    lines.append(f"  ↳ {d['description'][:60]}")
            
            lines.append("\n⚠️ Actual credentials are not exposed for security.")
            
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"
    
    # ── Build flow helpers ────────────────────────────────────────────────

    def _confirmation_prompt(self, request: BuildRequest, params: dict) -> str:
        """Build the 'are you sure?' message shown before triggering."""
        job    = request.job_name or settings.jenkins.default_job
        branch = request.branch   or "main"
        lines  = [
            f"🔨 **Ready to build** `{job}` from branch `{branch}`",
        ]
        if params:
            lines.append("\n**Parameters:**")
            for k, v in params.items():
                lines.append(f"  • `{k}` = `{v}`")
        lines.append("\nReply **yes** to trigger or **no** to cancel.")
        return "\n".join(lines)

    def _start_build_flow(self, request: BuildRequest, update_status) -> str:
        """
        After we know job + branch:
        1. Check if the job has parameters we haven't collected yet.
        2. If yes → start param collection (multi-turn).
        3. If no  → go straight to confirmation.
        """
        job_name = request.job_name or settings.jenkins.default_job

        # Fetch job parameters from Jenkins
        try:
            declared = self.jenkins.get_job_parameters(job_name)
        except Exception:
            declared = []

        # Filter out params already supplied (BRANCH / GITHUB_URL)
        already_have = {"BRANCH", "GITHUB_URL"}
        if request.branch:
            already_have.add("BRANCH")
        if request.repo_url:
            already_have.add("GITHUB_URL")

        missing_params = [
            p for p in declared
            if p["name"].upper() not in already_have
        ]

        if missing_params:
            first_prompt = self.conversation.start_param_collection(
                request, missing_params
            )
            return (
                f"📋 **{job_name}** has {len(declared)} parameter(s). "
                f"I'll ask for each one — press Enter to use the default.\n\n"
                + first_prompt
            )

        # No extra params — go straight to confirmation
        self.conversation.set_awaiting_confirmation(request)
        return self._confirmation_prompt(request, {})

    def _handle_build_request(self, request: BuildRequest, update_status) -> str:
        """
        Entry point for NEW_BUILD / REBUILD intents.

        Flow:
          1. Resolve job name — if ambiguous, ask the user to pick.
          2. Ask for branch if missing.
          3. Delegate to _start_build_flow for param collection + confirmation.
        """
        # ── Job name resolution ───────────────────────────────────────────
        job_name = request.job_name

        if not job_name:
            # No job name at all — ask the user to pick from the job list
            try:
                jobs = self.jenkins.list_jobs()
            except Exception:
                jobs = []

            if not jobs:
                # Fall back to default
                request.job_name = settings.jenkins.default_job
            elif len(jobs) == 1:
                request.job_name = jobs[0].name
            else:
                # Present a numbered list and ask
                lines = ["🤔 Which job would you like to build?\n"]
                for i, j in enumerate(jobs, 1):
                    lines.append(f"  {i}. {j.status_emoji} **{j.name}**")
                lines.append("\nType the job name or number:")
                # Park the request waiting for job_name
                request.missing_fields = ["job_name"]
                self.conversation.set_pending_request(request, "job_name")
                return "\n".join(lines)

        # ── Numeric reply resolution (user typed "2") ─────────────────────
        # Handled in complete_pending_request → falls through here on retry

        # ── Branch resolution ─────────────────────────────────────────────
        if not request.branch:
            request.missing_fields = ["branch"]
            self.conversation.set_pending_request(request, "branch")
            return (
                f"🌿 Which **branch** should I build `{request.job_name}` from?\n"
                f"(e.g. `main`, `develop`, `hotfix/PAY-123`)"
            )

        # Validate branch
        valid, err = self._validate_branch_name(request.branch)
        if not valid:
            return f"❌ Invalid branch name: {err}"

        # Validate repo URL if provided
        if request.repo_url:
            valid, err = self._validate_repo_url(request.repo_url)
            if not valid:
                return f"❌ Invalid repo: {err}"

        return self._start_build_flow(request, update_status)
    
    def _execute_build(self, request: BuildRequest, update_status) -> str:
        """Actually trigger Jenkins and poll to completion."""
        job_name = request.job_name or settings.jenkins.default_job
        branch   = request.branch   or "main"

        # Merge collected extra params (from param-collection flow)
        params: dict = {"BRANCH": branch}
        if request.repo_url:
            params["GITHUB_URL"] = request.repo_url
        extra = getattr(request, "_extra_params", {}) or \
                self.conversation.get_collected_params()
        params.update(extra)

        try:
            update_status(f"Triggering **{job_name}**…")
            queue_info = self.jenkins.trigger_build(job_name, params)

            update_status("Waiting for build to start…")
            build_info = self.jenkins.wait_for_build_start(queue_info, timeout=60)

            self.conversation.context.last_build   = build_info
            self.conversation.context.last_request = request
            # Clear collected params now that build is triggered
            self.conversation.context.collected_params = {}

            update_status(f"Building **#{build_info.build_number}**…")

            final_info = self.jenkins.poll_until_complete(
                job_name, build_info.build_number,
                poll_interval=5, timeout=1800
            )

            # Human-readable duration
            ds = (final_info.duration or 0) // 1000
            if ds < 60:      dur = f"{ds}s"
            elif ds < 3600:  dur = f"{ds//60}m {ds%60}s" if ds%60 else f"{ds//60}m"
            else:            dur = f"{ds//3600}h {(ds%3600)//60}m"

            emoji  = "✅" if final_info.status == BuildStatus.SUCCESS else "❌"
            result = (f"{emoji} **Build #{final_info.build_number}** — "
                      f"{final_info.status.name}\n⏱️ {dur}")

            if final_info.status == BuildStatus.FAILURE:
                try:
                    logs = self.jenkins.get_console_output(
                        job_name, final_info.build_number, last_n_lines=10)
                    result += f"\n\n**Last 10 lines:**\n```\n{logs}\n```"
                except Exception:
                    pass

            try:
                self.notifications.send_build_notification(final_info)
            except Exception:
                pass

            return result

        except Exception as e:
            return f"❌ Build error: {e}"
