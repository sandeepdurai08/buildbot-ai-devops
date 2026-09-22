"""
BuildBot Build Scheduler
Schedule and manage recurring builds.
Compatible with Python 3.14+
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import threading
import time

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """Types of build schedules."""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    CRON = "cron"


@dataclass
class ScheduledBuild:
    """Represents a scheduled build."""
    id: str
    job_name: str
    branch: str
    repo_url: str = ""
    schedule_type: ScheduleType = ScheduleType.ONCE
    schedule_time: str = ""  # HH:MM for daily, day,HH:MM for weekly
    cron_expression: str = ""
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_by: str = "system"
    description: str = ""
    
    def calculate_next_run(self) -> Optional[datetime]:
        """Calculate the next run time."""
        now = datetime.now()
        
        if self.schedule_type == ScheduleType.ONCE:
            if self.last_run:
                return None
            try:
                return datetime.fromisoformat(self.schedule_time)
            except ValueError:
                return None
        
        elif self.schedule_type == ScheduleType.HOURLY:
            return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        elif self.schedule_type == ScheduleType.DAILY:
            try:
                hour, minute = map(int, self.schedule_time.split(':'))
                next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_time <= now:
                    next_time += timedelta(days=1)
                return next_time
            except ValueError:
                return None
        
        elif self.schedule_type == ScheduleType.WEEKLY:
            try:
                parts = self.schedule_time.split(',')
                day_name = parts[0].lower()
                hour, minute = map(int, parts[1].split(':'))
                
                days = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
                        'friday': 4, 'saturday': 5, 'sunday': 6}
                target_day = days.get(day_name, 0)
                
                current_day = now.weekday()
                days_ahead = target_day - current_day
                if days_ahead <= 0:
                    days_ahead += 7
                
                next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                next_time += timedelta(days=days_ahead)
                return next_time
            except (ValueError, IndexError):
                return None
        
        return None


class BuildScheduler:
    """Manages scheduled builds."""
    
    def __init__(self, data_file: str = "schedules.json"):
        self.data_file = Path(data_file)
        self.schedules: list[ScheduledBuild] = []
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.build_callback: Optional[Callable] = None
        self._load_data()
    
    def _load_data(self):
        """Load schedules from file."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.schedules = []
                    for s in data:
                        schedule = ScheduledBuild(
                            id=s['id'],
                            job_name=s['job_name'],
                            branch=s['branch'],
                            repo_url=s.get('repo_url', ''),
                            schedule_type=ScheduleType(s['schedule_type']),
                            schedule_time=s.get('schedule_time', ''),
                            cron_expression=s.get('cron_expression', ''),
                            enabled=s.get('enabled', True),
                            created_at=datetime.fromisoformat(s['created_at']),
                            last_run=datetime.fromisoformat(s['last_run']) if s.get('last_run') else None,
                            created_by=s.get('created_by', 'system'),
                            description=s.get('description', '')
                        )
                        schedule.next_run = schedule.calculate_next_run()
                        self.schedules.append(schedule)
            except Exception as e:
                logger.error(f"Failed to load schedules: {e}")
                self.schedules = []
    
    def _save_data(self):
        """Save schedules to file."""
        try:
            data = [
                {
                    'id': s.id,
                    'job_name': s.job_name,
                    'branch': s.branch,
                    'repo_url': s.repo_url,
                    'schedule_type': s.schedule_type.value,
                    'schedule_time': s.schedule_time,
                    'cron_expression': s.cron_expression,
                    'enabled': s.enabled,
                    'created_at': s.created_at.isoformat(),
                    'last_run': s.last_run.isoformat() if s.last_run else None,
                    'created_by': s.created_by,
                    'description': s.description
                }
                for s in self.schedules
            ]
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")
    
    def add_schedule(
        self,
        job_name: str,
        branch: str,
        schedule_type: ScheduleType,
        schedule_time: str = "",
        repo_url: str = "",
        description: str = "",
        created_by: str = "user"
    ) -> ScheduledBuild:
        """Add a new scheduled build."""
        import uuid
        
        schedule = ScheduledBuild(
            id=str(uuid.uuid4())[:8],
            job_name=job_name,
            branch=branch,
            repo_url=repo_url,
            schedule_type=schedule_type,
            schedule_time=schedule_time,
            created_by=created_by,
            description=description
        )
        schedule.next_run = schedule.calculate_next_run()
        
        self.schedules.append(schedule)
        self._save_data()
        
        logger.info(f"Added schedule: {schedule.id} - {job_name} ({schedule_type.value})")
        return schedule
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a scheduled build."""
        for i, s in enumerate(self.schedules):
            if s.id == schedule_id:
                del self.schedules[i]
                self._save_data()
                logger.info(f"Removed schedule: {schedule_id}")
                return True
        return False
    
    def toggle_schedule(self, schedule_id: str) -> bool:
        """Enable/disable a scheduled build."""
        for s in self.schedules:
            if s.id == schedule_id:
                s.enabled = not s.enabled
                self._save_data()
                return True
        return False
    
    def get_schedules(self) -> list[ScheduledBuild]:
        """Get all schedules."""
        return sorted(self.schedules, key=lambda x: x.next_run or datetime.max)
    
    def get_upcoming(self, hours: int = 24) -> list[ScheduledBuild]:
        """Get builds scheduled in the next N hours."""
        cutoff = datetime.now() + timedelta(hours=hours)
        return [
            s for s in self.schedules 
            if s.enabled and s.next_run and s.next_run <= cutoff
        ]
    
    def set_build_callback(self, callback: Callable):
        """Set the callback function for triggering builds."""
        self.build_callback = callback
    
    def start(self):
        """Start the scheduler background thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Build scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Build scheduler stopped")
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                self._check_schedules()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            time.sleep(60)  # Check every minute
    
    def _check_schedules(self):
        """Check and execute due schedules."""
        now = datetime.now()
        
        for schedule in self.schedules:
            if not schedule.enabled:
                continue
            
            if schedule.next_run and schedule.next_run <= now:
                self._execute_schedule(schedule)
                schedule.last_run = now
                schedule.next_run = schedule.calculate_next_run()
                self._save_data()
    
    def _execute_schedule(self, schedule: ScheduledBuild):
        """Execute a scheduled build."""
        logger.info(f"Executing scheduled build: {schedule.job_name} from {schedule.branch}")
        
        if self.build_callback:
            try:
                self.build_callback(
                    job_name=schedule.job_name,
                    branch=schedule.branch,
                    repo_url=schedule.repo_url,
                    triggered_by=f"scheduler:{schedule.id}"
                )
            except Exception as e:
                logger.error(f"Failed to execute scheduled build: {e}")


# Global instance
build_scheduler = BuildScheduler()
