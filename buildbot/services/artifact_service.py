"""
BuildBot Artifact Service
Handles copying and managing build artifacts.
Compatible with Python 3.14+
"""

import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

import sys
sys.path.append('..')
from config import settings

logger = logging.getLogger(__name__)


class ArtifactService:
    """Service for managing build artifacts."""
    
    def __init__(self):
        self.shared_path = Path(settings.app.artifacts_shared_path)
    
    def ensure_path_exists(self, path: Path) -> None:
        """Ensure a directory path exists."""
        path.mkdir(parents=True, exist_ok=True)
    
    def copy_artifacts(
        self,
        artifacts: list[tuple[str, bytes]],
        build_number: int
    ) -> str:
        """
        Copy artifacts to shared path.
        
        Args:
            artifacts: List of (filename, content) tuples
            build_number: Build number for folder naming
            
        Returns:
            Path where artifacts were copied
        """
        # Create timestamped folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_folder = self.shared_path / f"{build_number}_{timestamp}"
        
        self.ensure_path_exists(dest_folder)
        
        copied = []
        for filename, content in artifacts:
            dest_file = dest_folder / filename
            
            # Ensure parent directories exist
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            dest_file.write_bytes(content)
            copied.append(filename)
            logger.info(f"Copied artifact: {filename}")
        
        logger.info(f"Copied {len(copied)} artifact(s) to {dest_folder}")
        
        return str(dest_folder)
    
    def copy_selected_artifacts(
        self,
        artifacts: list[tuple[str, bytes]],
        build_number: int,
        requested: list[str]
    ) -> tuple[str, list[str], list[str]]:
        """
        Copy only selected artifacts.
        
        Args:
            artifacts: List of (filename, content) tuples
            build_number: Build number
            requested: List of requested filenames (can be partial matches)
            
        Returns:
            Tuple of (dest_path, copied_files, not_found_files)
        """
        # Create folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_folder = self.shared_path / f"{build_number}_{timestamp}"
        
        self.ensure_path_exists(dest_folder)
        
        copied = []
        not_found = list(requested)
        
        for filename, content in artifacts:
            # Check if this file was requested
            for req in requested:
                if req.lower() in filename.lower():
                    dest_file = dest_folder / filename
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    dest_file.write_bytes(content)
                    
                    copied.append(filename)
                    if req in not_found:
                        not_found.remove(req)
                    
                    logger.info(f"Copied selected artifact: {filename}")
                    break
        
        return str(dest_folder), copied, not_found
    
    def list_recent_artifacts(self, limit: int = 10) -> list[dict]:
        """
        List recent artifact folders.
        
        Args:
            limit: Max number of folders to return
            
        Returns:
            List of dicts with folder info
        """
        if not self.shared_path.exists():
            return []
        
        folders = []
        
        for item in sorted(self.shared_path.iterdir(), reverse=True):
            if item.is_dir():
                files = list(item.rglob("*"))
                file_count = len([f for f in files if f.is_file()])
                
                folders.append({
                    "path": str(item),
                    "name": item.name,
                    "file_count": file_count,
                    "created": datetime.fromtimestamp(item.stat().st_ctime)
                })
                
                if len(folders) >= limit:
                    break
        
        return folders
    
    def get_artifact_path(self, build_number: int) -> Optional[str]:
        """
        Find artifact folder for a specific build.
        
        Args:
            build_number: Build number to find
            
        Returns:
            Path string or None if not found
        """
        if not self.shared_path.exists():
            return None
        
        # Look for folder starting with build number
        for item in self.shared_path.iterdir():
            if item.is_dir() and item.name.startswith(f"{build_number}_"):
                return str(item)
        
        return None
