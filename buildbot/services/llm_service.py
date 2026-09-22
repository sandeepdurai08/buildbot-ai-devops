"""
BuildBot LLM Service
Handles communication with Exterro LLM (OpenAI-compatible API).
Compatible with Python 3.14+
"""

import json
import logging
import urllib3
import requests
from typing import Optional

import sys
sys.path.append('..')
from config import settings
from core.models import BuildRequest, Intent

logger = logging.getLogger(__name__)

# System prompt for parsing build requests
SYSTEM_PROMPT = """You are BuildBot, a helpful assistant that parses developer build requests.

Your job is to extract structured information from natural language build requests.

IMPORTANT RULES:
1. Return ONLY valid JSON - no markdown, no code fences, no explanation
2. Extract repository URL and branch name exactly as stated
3. If information is missing, add it to the "missing" array
4. Never invent or guess URLs or branch names
5. For system commands like "list jobs", "queue", "nodes", "system info" - just set the intent, no repo/branch needed

INTENT VALUES:
- new_build: User wants to trigger a new build
- rebuild: User wants to rebuild last request
- abort_build: User wants to stop/abort a running build
- check_status: User asking about build status
- get_artifacts: User wants specific artifacts
- get_latest_artifacts: User wants latest artifacts from a job
- list_jobs: User wants to see available jobs
- list_views: User wants to see Jenkins views
- view_jobs: User wants jobs in a specific view
- job_history: User wants build history of a job
- job_info: User wants details about a specific job
- queue_status: User wants to see the build queue
- queue_cancel: User wants to cancel a queued item
- node_list: User wants to see all nodes/agents
- node_status: User wants status of a specific node
- node_offline: User wants to take a node offline
- node_online: User wants to bring a node online
- disable_job: User wants to disable a job
- enable_job: User wants to enable a job
- search_logs: User wants to search build logs
- compare_builds: User wants to compare two builds
- build_changes: User wants to see commits in a build
- pipeline_stages: User wants to see pipeline stages
- workspace_cleanup: User wants to wipe a job workspace
- scm_poll: User wants to trigger SCM polling
- system_info: User wants Jenkins system information
- plugin_list: User wants to see installed plugins
- credentials_list: User wants to see credential domains
- help: User needs help
- unknown: Cannot understand request

OUTPUT FORMAT (JSON only, no markdown):
{
    "intent": "<intent_value>",
    "repo_url": "extracted URL or null",
    "branch": "extracted branch name or null",
    "job_name": "specific job name if mentioned or null",
    "build_number": "specific build number or null",
    "node_name": "node/agent name or null",
    "search_term": "search term for log search or null",
    "compare_builds": [build1, build2] or [],
    "artifacts": ["list", "of", "specific", "files", "requested"],
    "missing": ["list of missing required fields"]
}

EXAMPLES:
Input: "build https://github.com/acme/api from main"
Output: {"intent":"new_build","repo_url":"https://github.com/acme/api","branch":"main","job_name":null,"build_number":null,"node_name":null,"search_term":null,"compare_builds":[],"artifacts":[],"missing":[]}

Input: "abort my-job #42"
Output: {"intent":"abort_build","repo_url":null,"branch":null,"job_name":"my-job","build_number":42,"node_name":null,"search_term":null,"compare_builds":[],"artifacts":[],"missing":[]}

Input: "show me the queue"
Output: {"intent":"queue_status","repo_url":null,"branch":null,"job_name":null,"build_number":null,"node_name":null,"search_term":null,"compare_builds":[],"artifacts":[],"missing":[]}

Input: "what's the status of node slave1"
Output: {"intent":"node_status","repo_url":null,"branch":null,"job_name":null,"build_number":null,"node_name":"slave1","search_term":null,"compare_builds":[],"artifacts":[],"missing":[]}

Input: "search for NullPointer in my-job build 10"
Output: {"intent":"search_logs","repo_url":null,"branch":null,"job_name":"my-job","build_number":10,"node_name":null,"search_term":"NullPointer","compare_builds":[],"artifacts":[],"missing":[]}

Input: "compare builds 5 and 10 of my-job"
Output: {"intent":"compare_builds","repo_url":null,"branch":null,"job_name":"my-job","build_number":null,"node_name":null,"search_term":null,"compare_builds":[5,10],"artifacts":[],"missing":[]}

Input: "list jobs"
Output: {"intent":"list_jobs","repo_url":null,"branch":null,"job_name":null,"build_number":null,"node_name":null,"search_term":null,"compare_builds":[],"artifacts":[],"missing":[]}

Input: "disable job my-job"
Output: {"intent":"disable_job","repo_url":null,"branch":null,"job_name":"my-job","build_number":null,"node_name":null,"search_term":null,"compare_builds":[],"artifacts":[],"missing":[]}

Input: "show me jenkins system info"
Output: {"intent":"system_info","repo_url":null,"branch":null,"job_name":null,"build_number":null,"node_name":null,"search_term":null,"compare_builds":[],"artifacts":[],"missing":[]}
"""


class LLMService:
    """Service for interacting with Exterro LLM."""
    
    def __init__(self):
        self.url = settings.llm.url
        self.model = settings.llm.model
        self.api_key = settings.llm.api_key
        self.temperature = settings.llm.temperature
        self.max_tokens = settings.llm.max_tokens
        self.verify_ssl = settings.llm.verify_ssl
        
        # Disable SSL warnings if verification is off
        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("SSL verification disabled for LLM connection")
    
    def parse_build_request(self, message: str, context: str = "") -> BuildRequest:
        """
        Parse a natural language message into a structured BuildRequest.
        
        Args:
            message: User's natural language message
            context: Optional conversation context
            
        Returns:
            BuildRequest with extracted information
        """
        # Build the prompt
        user_content = f"Parse this build request:\n{message}"
        if context:
            user_content += f"\n\nContext: {context}"
        
        try:
            # Call LLM API
            response = self._call_llm(user_content)
            
            # Parse JSON response
            return self._parse_response(response, message)
            
        except Exception as e:
            logger.error(f"LLM parsing error: {e}")
            # Return unknown intent on error
            return BuildRequest(
                intent=Intent.UNKNOWN,
                raw_message=message
            )
    
    def _call_llm(self, user_content: str) -> str:
        """Call the LLM API and return the response text."""
        headers = {"Content-Type": "application/json"}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        logger.debug(f"Calling LLM: {self.url}")
        
        response = requests.post(
            self.url,
            headers=headers,
            json=payload,
            timeout=30,
            verify=self.verify_ssl
        )
        
        response.raise_for_status()
        
        data = response.json()
        
        # Extract content from OpenAI-compatible response
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
            return content.strip()
        
        raise ValueError("Unexpected LLM response format")
    
    def _parse_response(self, response: str, original_message: str) -> BuildRequest:
        """Parse LLM response JSON into BuildRequest."""
        # Clean up response - remove markdown code fences if present
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        response = response.strip()
        
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response was: {response[:200]}")
            return BuildRequest(intent=Intent.UNKNOWN, raw_message=original_message)
        
        # Map intent string to enum
        intent_str = data.get("intent", "unknown").lower()
        intent_map = {
            # Build operations
            "new_build": Intent.NEW_BUILD,
            "rebuild": Intent.REBUILD,
            "abort_build": Intent.ABORT_BUILD,
            "check_status": Intent.CHECK_STATUS,
            
            # Job info
            "list_jobs": Intent.LIST_JOBS,
            "list_views": Intent.LIST_VIEWS,
            "view_jobs": Intent.VIEW_JOBS,
            "job_history": Intent.JOB_HISTORY,
            "job_info": Intent.JOB_INFO,
            
            # Artifacts
            "get_artifacts": Intent.GET_ARTIFACTS,
            "get_latest_artifacts": Intent.GET_LATEST_ARTIFACTS,
            
            # Queue
            "queue_status": Intent.QUEUE_STATUS,
            "queue_cancel": Intent.QUEUE_CANCEL,
            
            # Nodes
            "node_list": Intent.NODE_LIST,
            "node_status": Intent.NODE_STATUS,
            "node_offline": Intent.NODE_OFFLINE,
            "node_online": Intent.NODE_ONLINE,
            
            # Job management
            "disable_job": Intent.DISABLE_JOB,
            "enable_job": Intent.ENABLE_JOB,
            
            # Logs & analysis
            "search_logs": Intent.SEARCH_LOGS,
            "compare_builds": Intent.COMPARE_BUILDS,
            "build_changes": Intent.BUILD_CHANGES,
            "pipeline_stages": Intent.PIPELINE_STAGES,
            
            # Workspace
            "workspace_cleanup": Intent.WORKSPACE_CLEANUP,
            "scm_poll": Intent.SCM_POLL,
            
            # System
            "system_info": Intent.SYSTEM_INFO,
            "plugin_list": Intent.PLUGIN_LIST,
            "credentials_list": Intent.CREDENTIALS_LIST,
            
            # Misc
            "help": Intent.HELP,
            "unknown": Intent.UNKNOWN
        }
        intent = intent_map.get(intent_str, Intent.UNKNOWN)
        
        # Parse build number if present
        build_number = data.get("build_number")
        if build_number is not None:
            try:
                build_number = int(build_number)
            except (ValueError, TypeError):
                build_number = None
        
        # Parse compare_builds list
        compare_builds = data.get("compare_builds", [])
        if compare_builds:
            try:
                compare_builds = [int(b) for b in compare_builds]
            except (ValueError, TypeError):
                compare_builds = []
        
        return BuildRequest(
            intent=intent,
            repo_url=data.get("repo_url"),
            branch=data.get("branch"),
            job_name=data.get("job_name"),
            build_number=build_number,
            node_name=data.get("node_name"),
            search_term=data.get("search_term"),
            compare_builds=compare_builds,
            artifacts=data.get("artifacts", []),
            missing_fields=data.get("missing", []),
            raw_message=original_message
        )
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Test connection to the LLM service.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            response = self._call_llm("Say OK")
            return True, f"LLM connected: {response[:50]}"
        except requests.exceptions.SSLError:
            return False, "SSL Certificate Error - Set LLM_VERIFY_SSL=false in .env"
        except Exception as e:
            return False, f"LLM connection failed: {str(e)}"
