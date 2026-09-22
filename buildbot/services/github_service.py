"""
BuildBot GitHub Service
Validates GitHub repositories and branches.
Compatible with Python 3.14+
"""

import logging
import re
from typing import Optional
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for validating GitHub repositories and branches."""
    
    def __init__(self, token: str = ""):
        self.token = token
        self.api_base = "https://api.github.com"
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self.headers["Authorization"] = f"token {token}"
    
    def _parse_repo_url(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse a GitHub URL to extract owner and repo.
        
        Supports formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - github.com/owner/repo
        - git@github.com:owner/repo.git
        
        Returns:
            Tuple of (owner, repo) or (None, None) if invalid
        """
        if not url:
            return None, None
        
        url = url.strip()
        
        # Handle SSH format
        if url.startswith("git@"):
            match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
            if match:
                return match.group(1), match.group(2)
        
        # Handle HTTPS format
        # Remove trailing .git
        if url.endswith(".git"):
            url = url[:-4]
        
        # Add https:// if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            parsed = urlparse(url)
            if "github.com" not in parsed.netloc:
                return None, None
            
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        except Exception:
            pass
        
        return None, None
    
    def check_repository_exists(self, url: str) -> tuple[bool, str, Optional[dict]]:
        """
        Check if a GitHub repository exists and is accessible.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            Tuple of (exists, message, repo_info or None)
        """
        owner, repo = self._parse_repo_url(url)
        
        if not owner or not repo:
            return False, f"❌ Invalid GitHub URL format: `{url}`", None
        
        try:
            api_url = f"{self.api_base}/repos/{owner}/{repo}"
            response = requests.get(api_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return True, f"✅ Repository `{owner}/{repo}` found!", data
            elif response.status_code == 404:
                return False, f"❌ Repository `{owner}/{repo}` not found.\n\n💡 Check if:\n- The URL is correct\n- The repository is public (or you have access)", None
            elif response.status_code == 403:
                return False, f"⚠️ Rate limited or access denied for `{owner}/{repo}`", None
            else:
                return False, f"❌ GitHub API returned status {response.status_code}", None
                
        except requests.exceptions.Timeout:
            return False, "⚠️ GitHub API timeout - try again", None
        except Exception as e:
            logger.error(f"Error checking repository: {e}")
            return False, f"⚠️ Error checking repository: {str(e)}", None
    
    def check_branch_exists(self, url: str, branch: str) -> tuple[bool, str]:
        """
        Check if a branch exists in a repository.
        
        Args:
            url: GitHub repository URL
            branch: Branch name to check
            
        Returns:
            Tuple of (exists, message)
        """
        owner, repo = self._parse_repo_url(url)
        
        if not owner or not repo:
            return False, f"❌ Invalid GitHub URL: `{url}`"
        
        if not branch:
            return False, "❌ Branch name is required"
        
        try:
            api_url = f"{self.api_base}/repos/{owner}/{repo}/branches/{branch}"
            response = requests.get(api_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return True, f"✅ Branch `{branch}` exists in `{owner}/{repo}`"
            elif response.status_code == 404:
                # Get available branches for suggestion
                branches = self.list_branches(url, limit=5)
                suggestion = ""
                if branches:
                    suggestion = f"\n\n💡 Available branches: {', '.join(f'`{b}`' for b in branches)}"
                return False, f"❌ Branch `{branch}` not found in `{owner}/{repo}`{suggestion}"
            else:
                return False, f"⚠️ GitHub API returned status {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error checking branch: {e}")
            return False, f"⚠️ Error checking branch: {str(e)}"
    
    def list_branches(self, url: str, limit: int = 10) -> list[str]:
        """
        List branches in a repository.
        
        Args:
            url: GitHub repository URL
            limit: Max number of branches to return
            
        Returns:
            List of branch names
        """
        owner, repo = self._parse_repo_url(url)
        
        if not owner or not repo:
            return []
        
        try:
            api_url = f"{self.api_base}/repos/{owner}/{repo}/branches"
            params = {"per_page": limit}
            response = requests.get(api_url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                return [b["name"] for b in response.json()]
            return []
            
        except Exception as e:
            logger.error(f"Error listing branches: {e}")
            return []
    
    def get_default_branch(self, url: str) -> Optional[str]:
        """
        Get the default branch of a repository.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            Default branch name or None
        """
        owner, repo = self._parse_repo_url(url)
        
        if not owner or not repo:
            return None
        
        try:
            api_url = f"{self.api_base}/repos/{owner}/{repo}"
            response = requests.get(api_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json().get("default_branch")
            return None
            
        except Exception as e:
            logger.error(f"Error getting default branch: {e}")
            return None


# Global instance
github_service = GitHubService()
