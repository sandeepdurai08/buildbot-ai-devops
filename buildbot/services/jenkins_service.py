"""
BuildBot Jenkins Service
Handles all interactions with Jenkins REST API.
Compatible with Python 3.14+
"""

import logging
import time
from typing import Optional, Callable
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth

import sys
sys.path.append('..')
from config import settings
from core.models import BuildInfo, BuildStatus, JobInfo, ArtifactInfo

logger = logging.getLogger(__name__)


class JenkinsService:
    """Service for interacting with Jenkins via REST API."""
    
    def __init__(self):
        self.base_url = settings.jenkins.url.rstrip("/")
        self.user = settings.jenkins.user
        self.token = settings.jenkins.api_token
        self.auth = HTTPBasicAuth(self.user, self.token) if self.token else None
    
    def _get(self, path: str, params: dict = None) -> dict:
        """Make GET request to Jenkins API."""
        url = f"{self.base_url}{path}"
        response = requests.get(url, auth=self.auth, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def _post(self, path: str, params: dict = None) -> requests.Response:
        """Make POST request to Jenkins API."""
        url = f"{self.base_url}{path}"
        response = requests.post(url, auth=self.auth, params=params, timeout=30)
        response.raise_for_status()
        return response
    
    def list_jobs(self) -> list[JobInfo]:
        """List all Jenkins jobs."""
        try:
            data = self._get("/api/json")
            jobs = []
            
            for job in data.get("jobs", []):
                job_info = JobInfo(
                    name=job.get("name", ""),
                    url=job.get("url", ""),
                    color=job.get("color", "")
                )
                
                # Get last build number if available
                try:
                    job_detail = self._get(f"/job/{job_info.name}/api/json")
                    last_build = job_detail.get("lastBuild")
                    if last_build:
                        job_info.last_build_number = last_build.get("number")
                except Exception:
                    pass
                
                jobs.append(job_info)
            
            return jobs
        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            raise
    
    def list_views(self) -> list[dict]:
        """List all Jenkins views."""
        try:
            data = self._get("/api/json")
            views = []
            
            for view in data.get("views", []):
                views.append({
                    "name": view.get("name", ""),
                    "url": view.get("url", ""),
                    "description": view.get("description", "")
                })
            
            return views
        except Exception as e:
            logger.error(f"Error listing views: {e}")
            raise
    
    def get_jobs_in_view(self, view_name: str) -> list[JobInfo]:
        """Get jobs in a specific view."""
        try:
            data = self._get(f"/view/{view_name}/api/json")
            jobs = []
            
            for job in data.get("jobs", []):
                job_info = JobInfo(
                    name=job.get("name", ""),
                    url=job.get("url", ""),
                    color=job.get("color", "")
                )
                
                # Get last build number
                try:
                    job_detail = self._get(f"/job/{job_info.name}/api/json")
                    last_build = job_detail.get("lastBuild")
                    if last_build:
                        job_info.last_build_number = last_build.get("number")
                except Exception:
                    pass
                
                jobs.append(job_info)
            
            return jobs
        except Exception as e:
            logger.error(f"Error getting jobs in view '{view_name}': {e}")
            raise
    
    def get_job_info(self, job_name: str) -> dict:
        """Get detailed job information."""
        return self._get(f"/job/{job_name}/api/json")
    
    def get_build_history(self, job_name: str, limit: int = 10) -> list[dict]:
        """Get build history for a job."""
        try:
            data = self._get(f"/job/{job_name}/api/json", params={"tree": "builds[number,result,duration,timestamp]"})
            builds = data.get("builds", [])[:limit]
            
            result = []
            for build in builds:
                timestamp = build.get("timestamp", 0)
                dt = datetime.fromtimestamp(timestamp / 1000) if timestamp else None
                
                result.append({
                    "number": build.get("number"),
                    "result": build.get("result"),
                    "duration": build.get("duration", 0),
                    "timestamp": timestamp,
                    "datetime": dt
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting build history for '{job_name}': {e}")
            raise
    
    def get_last_successful_build(self, job_name: str) -> Optional[dict]:
        """Get the last successful build."""
        try:
            data = self._get(f"/job/{job_name}/lastSuccessfulBuild/api/json")
            timestamp = data.get("timestamp", 0)
            return {
                "number": data.get("number"),
                "result": data.get("result"),
                "duration": data.get("duration", 0),
                "datetime": datetime.fromtimestamp(timestamp / 1000) if timestamp else None
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    def get_last_failed_build(self, job_name: str) -> Optional[dict]:
        """Get the last failed build."""
        try:
            data = self._get(f"/job/{job_name}/lastFailedBuild/api/json")
            timestamp = data.get("timestamp", 0)
            return {
                "number": data.get("number"),
                "result": data.get("result"),
                "duration": data.get("duration", 0),
                "datetime": datetime.fromtimestamp(timestamp / 1000) if timestamp else None
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    def trigger_build(self, job_name: str, params: dict = None) -> dict:
        """
        Trigger a build with parameters.
        
        Returns:
            Dict with queue_url for tracking
        """
        if params:
            path = f"/job/{job_name}/buildWithParameters"
            response = self._post(path, params=params)
        else:
            path = f"/job/{job_name}/build"
            response = self._post(path)
        
        # Get queue URL from Location header
        queue_url = response.headers.get("Location", "")
        
        logger.info(f"Build triggered for {job_name}, queue URL: {queue_url}")
        
        return {
            "job_name": job_name,
            "queue_url": queue_url,
            "params": params
        }
    
    def wait_for_build_start(self, queue_info: dict, timeout: int = 60) -> BuildInfo:
        """
        Wait for a queued build to start.
        
        Args:
            queue_info: Dict from trigger_build
            timeout: Max seconds to wait
            
        Returns:
            BuildInfo once build starts
        """
        job_name = queue_info["job_name"]
        queue_url = queue_info.get("queue_url", "")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to get queue item info
                if queue_url:
                    queue_api_url = f"{queue_url}api/json"
                    response = requests.get(queue_api_url, auth=self.auth, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check if build has started
                        executable = data.get("executable")
                        if executable:
                            build_number = executable.get("number")
                            build_url = executable.get("url", "")
                            
                            return BuildInfo(
                                job_name=job_name,
                                build_number=build_number,
                                status=BuildStatus.BUILDING,
                                url=build_url,
                                building=True
                            )
                
                # Fallback: check latest build
                job_data = self._get(f"/job/{job_name}/api/json")
                last_build = job_data.get("lastBuild")
                
                if last_build:
                    build_data = self._get(f"/job/{job_name}/{last_build['number']}/api/json")
                    
                    if build_data.get("building"):
                        return BuildInfo(
                            job_name=job_name,
                            build_number=last_build["number"],
                            status=BuildStatus.BUILDING,
                            url=build_data.get("url", ""),
                            building=True
                        )
                
            except Exception as e:
                logger.debug(f"Waiting for build to start: {e}")
            
            time.sleep(2)
        
        raise TimeoutError(f"Build did not start within {timeout} seconds")
    
    def get_build_status(self, job_name: str, build_number: int) -> BuildInfo:
        """Get current status of a build."""
        data = self._get(f"/job/{job_name}/{build_number}/api/json")
        
        result = data.get("result")
        building = data.get("building", False)
        
        if building:
            status = BuildStatus.BUILDING
        elif result:
            status = BuildStatus[result] if result in BuildStatus.__members__ else BuildStatus.UNKNOWN
        else:
            status = BuildStatus.UNKNOWN
        
        timestamp = data.get("timestamp", 0)
        
        return BuildInfo(
            job_name=job_name,
            build_number=build_number,
            status=status,
            url=data.get("url", ""),
            building=building,
            duration=data.get("duration", 0),
            timestamp=datetime.fromtimestamp(timestamp / 1000) if timestamp else None
        )
    
    def poll_until_complete(
        self,
        job_name: str,
        build_number: int,
        poll_interval: int = 5,
        timeout: int = 1800,
        status_callback: Optional[Callable[[BuildInfo], None]] = None
    ) -> BuildInfo:
        """
        Poll build until completion.
        
        Args:
            job_name: Jenkins job name
            build_number: Build number to poll
            poll_interval: Seconds between polls
            timeout: Max seconds to wait
            status_callback: Optional callback for status updates
            
        Returns:
            Final BuildInfo
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            info = self.get_build_status(job_name, build_number)
            
            if status_callback:
                status_callback(info)
            
            if not info.building:
                return info
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Build #{build_number} did not complete within {timeout} seconds")
    
    def get_console_output(self, job_name: str, build_number: int, last_n_lines: int = 50) -> str:
        """Get console output from a build."""
        url = f"{self.base_url}/job/{job_name}/{build_number}/consoleText"
        response = requests.get(url, auth=self.auth, timeout=30)
        response.raise_for_status()
        
        text = response.text
        
        if last_n_lines:
            lines = text.split("\n")
            text = "\n".join(lines[-last_n_lines:])
        
        return text
    
    def get_artifacts(self, job_name: str, build_number: int) -> list[ArtifactInfo]:
        """Get list of artifacts from a build."""
        data = self._get(f"/job/{job_name}/{build_number}/api/json")
        artifacts = []
        
        for artifact in data.get("artifacts", []):
            artifacts.append(ArtifactInfo(
                filename=artifact.get("fileName", ""),
                path=artifact.get("relativePath", ""),
                url=f"{self.base_url}/job/{job_name}/{build_number}/artifact/{artifact.get('relativePath', '')}"
            ))
        
        return artifacts
    
    def get_latest_artifacts_path(self, job_name: str) -> tuple[str, Optional[int], list[ArtifactInfo]]:
        """
        Get artifacts from the latest completed build.
        
        Returns:
            Tuple of (artifacts_url, build_number, list of artifacts)
        """
        try:
            # Get last completed build
            job_data = self._get(f"/job/{job_name}/api/json")
            last_completed = job_data.get("lastCompletedBuild")
            
            if not last_completed:
                return "", None, []
            
            build_number = last_completed.get("number")
            artifacts_url = f"{self.base_url}/job/{job_name}/{build_number}/artifact/"
            
            # Get artifacts list
            artifacts = self.get_artifacts(job_name, build_number)
            
            return artifacts_url, build_number, artifacts
            
        except Exception as e:
            logger.error(f"Error getting latest artifacts for '{job_name}': {e}")
            raise
    
    def download_artifact(self, job_name: str, build_number: int, artifact_path: str) -> bytes:
        """Download an artifact file."""
        url = f"{self.base_url}/job/{job_name}/{build_number}/artifact/{artifact_path}"
        response = requests.get(url, auth=self.auth, timeout=60)
        response.raise_for_status()
        return response.content
    
    def test_connection(self) -> tuple[bool, str]:
        """Test connection to Jenkins."""
        try:
            data = self._get("/api/json")
            job_count = len(data.get("jobs", []))
            return True, f"Connected to Jenkins. Found {job_count} job(s)."
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return False, "403 Forbidden - Check your API token"
            return False, f"HTTP Error: {e}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def get_job_parameters(self, job_name: str) -> list[dict]:
        """
        Return the declared build parameters for a Jenkins job.

        Each entry is a dict with keys:
          name        – parameter name  (e.g. "BRANCH")
          type        – short type name (e.g. "StringParameterDefinition")
          description – human-readable hint (may be empty)
          default     – default value string, or None
          choices     – list of strings for choice params, else []

        Returns an empty list when the job has no parameters or on error.
        """
        try:
            data = self._get(f"/job/{job_name}/api/json")
        except Exception:
            return []

        params: list[dict] = []
        for prop in data.get("property", []):
            for pd in prop.get("parameterDefinitions", []):
                ptype   = pd.get("type", "")
                choices: list[str] = []

                if ptype == "ChoiceParameterDefinition":
                    choices = pd.get("choices", [])
                    default = choices[0] if choices else None
                elif ptype == "BooleanParameterDefinition":
                    default = str(
                        pd.get("defaultParameterValue", {}).get("value", "false")
                    ).lower()
                else:
                    default = pd.get("defaultParameterValue", {}).get("value", None)

                params.append({
                    "name":        pd.get("name", ""),
                    "type":        ptype,
                    "description": pd.get("description", ""),
                    "default":     default,
                    "choices":     choices,
                })
        return params

    # ─────────────────────────────────────────────────────────────────────
    #  QUEUE MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────
    def get_queue_status(self) -> list[dict]:
        """Get current Jenkins build queue."""
        try:
            data = self._get("/queue/api/json")
            items = []
            for item in data.get("items", []):
                task = item.get("task", {})
                items.append({
                    "id": item.get("id"),
                    "job_name": task.get("name", "Unknown"),
                    "why": item.get("why", "Waiting"),
                    "stuck": item.get("stuck", False),
                    "blocked": item.get("blocked", False),
                    "in_queue_since": item.get("inQueueSince", 0),
                    "url": task.get("url", "")
                })
            return items
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            raise

    def cancel_queue_item(self, queue_id: int) -> bool:
        """Cancel a queued build by queue ID."""
        try:
            self._post(f"/queue/cancelItem", params={"id": queue_id})
            return True
        except Exception as e:
            logger.error(f"Error canceling queue item {queue_id}: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────
    #  BUILD OPERATIONS
    # ─────────────────────────────────────────────────────────────────────
    def abort_build(self, job_name: str, build_number: int) -> bool:
        """Abort a running build."""
        try:
            self._post(f"/job/{job_name}/{build_number}/stop")
            return True
        except Exception as e:
            logger.error(f"Error aborting build {job_name}#{build_number}: {e}")
            return False

    def get_build_changes(self, job_name: str, build_number: int) -> list[dict]:
        """Get SCM changes (commits) for a build."""
        try:
            data = self._get(f"/job/{job_name}/{build_number}/api/json")
            changes = []
            for changeset in data.get("changeSet", {}).get("items", []):
                changes.append({
                    "author": changeset.get("author", {}).get("fullName", "Unknown"),
                    "message": changeset.get("msg", ""),
                    "commit_id": changeset.get("commitId", "")[:8] if changeset.get("commitId") else "",
                    "timestamp": changeset.get("timestamp", 0),
                    "files": [f.get("file", "") for f in changeset.get("affectedPaths", [])][:5]
                })
            return changes
        except Exception as e:
            logger.error(f"Error getting build changes: {e}")
            return []

    def compare_builds(self, job_name: str, build1: int, build2: int) -> dict:
        """Compare two builds of the same job."""
        try:
            info1 = self.get_build_status(job_name, build1)
            info2 = self.get_build_status(job_name, build2)
            
            changes1 = self.get_build_changes(job_name, build1)
            changes2 = self.get_build_changes(job_name, build2)
            
            return {
                "build1": {
                    "number": build1,
                    "status": info1.status.name,
                    "duration": info1.duration,
                    "changes": len(changes1)
                },
                "build2": {
                    "number": build2,
                    "status": info2.status.name,
                    "duration": info2.duration,
                    "changes": len(changes2)
                },
                "duration_diff": info2.duration - info1.duration,
                "status_changed": info1.status != info2.status
            }
        except Exception as e:
            logger.error(f"Error comparing builds: {e}")
            raise

    def search_console_logs(self, job_name: str, build_number: int, search_term: str) -> list[dict]:
        """Search for a term in build console logs."""
        try:
            log = self.get_console_output(job_name, build_number, last_n_lines=None)
            results = []
            for i, line in enumerate(log.split("\n"), 1):
                if search_term.lower() in line.lower():
                    results.append({
                        "line_number": i,
                        "content": line.strip()[:200]
                    })
            return results[:50]  # Limit to 50 matches
        except Exception as e:
            logger.error(f"Error searching logs: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────
    #  NODE/AGENT MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────
    def get_nodes(self) -> list[dict]:
        """Get all Jenkins nodes/agents."""
        try:
            data = self._get("/computer/api/json")
            nodes = []
            for computer in data.get("computer", []):
                nodes.append({
                    "name": computer.get("displayName", ""),
                    "offline": computer.get("offline", False),
                    "temporarily_offline": computer.get("temporarilyOffline", False),
                    "idle": computer.get("idle", True),
                    "num_executors": computer.get("numExecutors", 0),
                    "description": computer.get("description", ""),
                    "offline_reason": computer.get("offlineCauseReason", "")
                })
            return nodes
        except Exception as e:
            logger.error(f"Error getting nodes: {e}")
            raise

    def get_node_status(self, node_name: str = "master") -> dict:
        """Get detailed status of a specific node."""
        try:
            # Handle master node special case
            node_path = "(master)" if node_name.lower() in ("master", "built-in") else node_name
            data = self._get(f"/computer/{node_path}/api/json")
            
            return {
                "name": data.get("displayName", node_name),
                "offline": data.get("offline", False),
                "temporarily_offline": data.get("temporarilyOffline", False),
                "idle": data.get("idle", True),
                "num_executors": data.get("numExecutors", 0),
                "busy_executors": len([e for e in data.get("executors", []) if e.get("currentExecutable")]),
                "description": data.get("description", ""),
                "offline_reason": data.get("offlineCauseReason", ""),
                "jnlp_agent": data.get("jnlpAgent", False),
                "launch_supported": data.get("launchSupported", False)
            }
        except Exception as e:
            logger.error(f"Error getting node status for {node_name}: {e}")
            raise

    def set_node_offline(self, node_name: str, reason: str = "Taken offline by BuildBot") -> bool:
        """Take a node offline."""
        try:
            node_path = "(master)" if node_name.lower() in ("master", "built-in") else node_name
            self._post(f"/computer/{node_path}/toggleOffline", params={"offlineMessage": reason})
            return True
        except Exception as e:
            logger.error(f"Error setting node offline: {e}")
            return False

    def set_node_online(self, node_name: str) -> bool:
        """Bring a node back online."""
        try:
            node_path = "(master)" if node_name.lower() in ("master", "built-in") else node_name
            self._post(f"/computer/{node_path}/toggleOffline")
            return True
        except Exception as e:
            logger.error(f"Error setting node online: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────
    #  JOB MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────
    def disable_job(self, job_name: str) -> bool:
        """Disable a Jenkins job."""
        try:
            self._post(f"/job/{job_name}/disable")
            return True
        except Exception as e:
            logger.error(f"Error disabling job {job_name}: {e}")
            return False

    def enable_job(self, job_name: str) -> bool:
        """Enable a Jenkins job."""
        try:
            self._post(f"/job/{job_name}/enable")
            return True
        except Exception as e:
            logger.error(f"Error enabling job {job_name}: {e}")
            return False

    def delete_job(self, job_name: str) -> bool:
        """Delete a Jenkins job (use with caution!)."""
        try:
            self._post(f"/job/{job_name}/doDelete")
            return True
        except Exception as e:
            logger.error(f"Error deleting job {job_name}: {e}")
            return False

    def trigger_scm_poll(self, job_name: str) -> bool:
        """Trigger SCM polling for a job."""
        try:
            self._post(f"/job/{job_name}/polling")
            return True
        except Exception as e:
            logger.error(f"Error triggering SCM poll for {job_name}: {e}")
            return False

    def wipe_workspace(self, job_name: str) -> bool:
        """Wipe the workspace of a job."""
        try:
            self._post(f"/job/{job_name}/doWipeOutWorkspace")
            return True
        except Exception as e:
            logger.error(f"Error wiping workspace for {job_name}: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────
    #  PIPELINE
    # ─────────────────────────────────────────────────────────────────────
    def get_pipeline_stages(self, job_name: str, build_number: int) -> list[dict]:
        """Get pipeline stages for a build (requires Pipeline Stage View plugin)."""
        try:
            data = self._get(f"/job/{job_name}/{build_number}/wfapi/describe")
            stages = []
            for stage in data.get("stages", []):
                stages.append({
                    "name": stage.get("name", ""),
                    "status": stage.get("status", "UNKNOWN"),
                    "duration": stage.get("durationMillis", 0),
                    "start_time": stage.get("startTimeMillis", 0)
                })
            return stages
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return []  # Not a pipeline job or plugin not installed
            raise
        except Exception as e:
            logger.error(f"Error getting pipeline stages: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────
    #  SYSTEM INFORMATION
    # ─────────────────────────────────────────────────────────────────────
    def get_system_info(self) -> dict:
        """Get Jenkins system information."""
        try:
            data = self._get("/api/json")
            
            # Get executor info
            computer_data = self._get("/computer/api/json")
            total_executors = sum(c.get("numExecutors", 0) for c in computer_data.get("computer", []))
            busy_executors = sum(
                len([e for e in c.get("executors", []) if e.get("currentExecutable")])
                for c in computer_data.get("computer", [])
            )
            
            return {
                "mode": data.get("mode", "UNKNOWN"),
                "node_description": data.get("nodeDescription", ""),
                "num_executors": data.get("numExecutors", 0),
                "quiet_mode": data.get("quietingDown", False),
                "slave_agent_port": data.get("slaveAgentPort", -1),
                "use_crumbs": data.get("useCrumbs", False),
                "use_security": data.get("useSecurity", False),
                "job_count": len(data.get("jobs", [])),
                "view_count": len(data.get("views", [])),
                "total_executors": total_executors,
                "busy_executors": busy_executors,
                "idle_executors": total_executors - busy_executors
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            raise

    def get_plugins(self) -> list[dict]:
        """Get list of installed plugins."""
        try:
            data = self._get("/pluginManager/api/json", params={"depth": 1})
            plugins = []
            for plugin in data.get("plugins", []):
                plugins.append({
                    "name": plugin.get("shortName", ""),
                    "long_name": plugin.get("longName", ""),
                    "version": plugin.get("version", ""),
                    "enabled": plugin.get("enabled", True),
                    "active": plugin.get("active", True),
                    "has_update": plugin.get("hasUpdate", False)
                })
            return sorted(plugins, key=lambda p: p["name"].lower())
        except Exception as e:
            logger.error(f"Error getting plugins: {e}")
            raise

    def get_credentials_domains(self) -> list[dict]:
        """Get credentials domains (not the secrets themselves)."""
        try:
            data = self._get("/credentials/store/system/api/json")
            domains = []
            for domain in data.get("domains", {}).values():
                domains.append({
                    "name": domain.get("displayName", "Global"),
                    "description": domain.get("description", ""),
                    "url": domain.get("url", "")
                })
            return domains
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return [{"name": "Credentials API not available", "description": "", "url": ""}]
            raise
        except Exception as e:
            logger.error(f"Error getting credentials domains: {e}")
            return []

    def restart_jenkins(self, safe: bool = True) -> bool:
        """
        Restart Jenkins.
        
        Args:
            safe: If True, waits for builds to complete first
        """
        try:
            endpoint = "/safeRestart" if safe else "/restart"
            self._post(endpoint)
            return True
        except Exception as e:
            logger.error(f"Error restarting Jenkins: {e}")
            return False
