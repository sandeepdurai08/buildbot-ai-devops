"""
BuildBot Analytics Engine
Comprehensive build analytics, trends, and insights.
Compatible with Python 3.14+
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class BuildRecord:
    """Record of a single build."""
    job_name: str
    build_number: int
    status: str
    duration: int  # seconds
    timestamp: datetime
    branch: str = ""
    repo_url: str = ""
    triggered_by: str = "manual"
    error_type: str = ""


@dataclass
class AnalyticsData:
    """Aggregated analytics data."""
    total_builds: int = 0
    success_count: int = 0
    failure_count: int = 0
    aborted_count: int = 0
    avg_duration: float = 0.0
    min_duration: float = 0.0
    max_duration: float = 0.0
    success_rate: float = 0.0
    builds_today: int = 0
    builds_this_week: int = 0
    builds_this_month: int = 0
    most_failed_job: str = ""
    most_built_job: str = ""
    peak_hour: int = 0
    trend: str = "stable"  # improving, declining, stable
    daily_builds: dict = field(default_factory=dict)
    hourly_distribution: dict = field(default_factory=dict)
    job_stats: dict = field(default_factory=dict)
    failure_patterns: list = field(default_factory=list)


class AnalyticsEngine:
    """Engine for build analytics and insights."""
    
    def __init__(self, data_file: str = "build_history.json"):
        self.data_file = Path(data_file)
        self.records: list[BuildRecord] = []
        self._load_data()
    
    def _load_data(self):
        """Load historical data from file."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.records = [
                        BuildRecord(
                            job_name=r['job_name'],
                            build_number=r['build_number'],
                            status=r['status'],
                            duration=r['duration'],
                            timestamp=datetime.fromisoformat(r['timestamp']),
                            branch=r.get('branch', ''),
                            repo_url=r.get('repo_url', ''),
                            triggered_by=r.get('triggered_by', 'manual'),
                            error_type=r.get('error_type', '')
                        )
                        for r in data
                    ]
            except Exception as e:
                logger.error(f"Failed to load analytics data: {e}")
                self.records = []
    
    def _save_data(self):
        """Save data to file."""
        try:
            data = [
                {
                    'job_name': r.job_name,
                    'build_number': r.build_number,
                    'status': r.status,
                    'duration': r.duration,
                    'timestamp': r.timestamp.isoformat(),
                    'branch': r.branch,
                    'repo_url': r.repo_url,
                    'triggered_by': r.triggered_by,
                    'error_type': r.error_type
                }
                for r in self.records
            ]
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save analytics data: {e}")
    
    def record_build(
        self,
        job_name: str,
        build_number: int,
        status: str,
        duration: int,
        branch: str = "",
        repo_url: str = "",
        triggered_by: str = "manual",
        error_type: str = ""
    ):
        """Record a new build."""
        record = BuildRecord(
            job_name=job_name,
            build_number=build_number,
            status=status,
            duration=duration,
            timestamp=datetime.now(),
            branch=branch,
            repo_url=repo_url,
            triggered_by=triggered_by,
            error_type=error_type
        )
        self.records.append(record)
        self._save_data()
        logger.info(f"Recorded build: {job_name} #{build_number} - {status}")
    
    def get_analytics(self, days: int = 30) -> AnalyticsData:
        """Get comprehensive analytics for the specified period."""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [r for r in self.records if r.timestamp >= cutoff]
        
        if not recent:
            return AnalyticsData()
        
        # Basic counts
        total = len(recent)
        success = len([r for r in recent if r.status == 'SUCCESS'])
        failure = len([r for r in recent if r.status == 'FAILURE'])
        aborted = len([r for r in recent if r.status == 'ABORTED'])
        
        # Duration stats
        durations = [r.duration for r in recent if r.duration > 0]
        avg_duration = statistics.mean(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        # Time-based counts
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        builds_today = len([r for r in recent if r.timestamp.date() == today])
        builds_week = len([r for r in recent if r.timestamp.date() >= week_ago])
        builds_month = len([r for r in recent if r.timestamp.date() >= month_ago])
        
        # Job stats
        job_counts: dict[str, dict] = {}
        for r in recent:
            if r.job_name not in job_counts:
                job_counts[r.job_name] = {'total': 0, 'success': 0, 'failure': 0}
            job_counts[r.job_name]['total'] += 1
            if r.status == 'SUCCESS':
                job_counts[r.job_name]['success'] += 1
            elif r.status == 'FAILURE':
                job_counts[r.job_name]['failure'] += 1
        
        # Most built/failed jobs
        most_built = max(job_counts.items(), key=lambda x: x[1]['total'])[0] if job_counts else ""
        most_failed = max(job_counts.items(), key=lambda x: x[1]['failure'])[0] if job_counts else ""
        
        # Hourly distribution
        hourly: dict[int, int] = {h: 0 for h in range(24)}
        for r in recent:
            hourly[r.timestamp.hour] += 1
        peak_hour = max(hourly.items(), key=lambda x: x[1])[0] if hourly else 0
        
        # Daily builds
        daily: dict[str, int] = {}
        for r in recent:
            day = r.timestamp.strftime('%Y-%m-%d')
            daily[day] = daily.get(day, 0) + 1
        
        # Trend analysis
        if len(recent) >= 14:
            first_week = [r for r in recent if r.timestamp >= cutoff and r.timestamp < cutoff + timedelta(days=7)]
            last_week = [r for r in recent if r.timestamp >= datetime.now() - timedelta(days=7)]
            
            first_rate = len([r for r in first_week if r.status == 'SUCCESS']) / len(first_week) if first_week else 0
            last_rate = len([r for r in last_week if r.status == 'SUCCESS']) / len(last_week) if last_week else 0
            
            if last_rate > first_rate + 0.1:
                trend = "improving"
            elif last_rate < first_rate - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # Failure patterns
        failure_patterns = []
        error_counts: dict[str, int] = {}
        for r in recent:
            if r.status == 'FAILURE' and r.error_type:
                error_counts[r.error_type] = error_counts.get(r.error_type, 0) + 1
        
        for error, count in sorted(error_counts.items(), key=lambda x: -x[1])[:5]:
            failure_patterns.append({'type': error, 'count': count})
        
        return AnalyticsData(
            total_builds=total,
            success_count=success,
            failure_count=failure,
            aborted_count=aborted,
            avg_duration=avg_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            success_rate=round((success / total * 100) if total > 0 else 0, 1),
            builds_today=builds_today,
            builds_this_week=builds_week,
            builds_this_month=builds_month,
            most_failed_job=most_failed,
            most_built_job=most_built,
            peak_hour=peak_hour,
            trend=trend,
            daily_builds=daily,
            hourly_distribution=hourly,
            job_stats=job_counts,
            failure_patterns=failure_patterns
        )
    
    def get_job_insights(self, job_name: str) -> dict:
        """Get insights for a specific job."""
        job_records = [r for r in self.records if r.job_name == job_name]
        
        if not job_records:
            return {"error": "No data for this job"}
        
        recent = job_records[-50:]  # Last 50 builds
        
        success_count = len([r for r in recent if r.status == 'SUCCESS'])
        failure_count = len([r for r in recent if r.status == 'FAILURE'])
        
        durations = [r.duration for r in recent if r.status == 'SUCCESS' and r.duration > 0]
        avg_duration = statistics.mean(durations) if durations else 0
        
        # Branch analysis
        branch_stats: dict[str, dict] = {}
        for r in recent:
            if r.branch:
                if r.branch not in branch_stats:
                    branch_stats[r.branch] = {'total': 0, 'success': 0}
                branch_stats[r.branch]['total'] += 1
                if r.status == 'SUCCESS':
                    branch_stats[r.branch]['success'] += 1
        
        # Find problematic branches
        problematic_branches = []
        for branch, stats in branch_stats.items():
            if stats['total'] >= 3:
                rate = stats['success'] / stats['total']
                if rate < 0.7:
                    problematic_branches.append({
                        'branch': branch,
                        'success_rate': round(rate * 100, 1)
                    })
        
        return {
            'total_builds': len(recent),
            'success_rate': round((success_count / len(recent) * 100) if recent else 0, 1),
            'avg_duration': round(avg_duration, 1),
            'last_status': recent[-1].status if recent else 'N/A',
            'problematic_branches': problematic_branches,
            'recommended_actions': self._get_recommendations(job_name, recent)
        }
    
    def _get_recommendations(self, job_name: str, records: list[BuildRecord]) -> list[str]:
        """Generate recommendations based on build history."""
        recommendations = []
        
        if not records:
            return ["No build history available"]
        
        recent = records[-10:]
        failure_rate = len([r for r in recent if r.status == 'FAILURE']) / len(recent)
        
        if failure_rate > 0.5:
            recommendations.append("⚠️ High failure rate (>50%) - Consider reviewing build configuration")
        
        if failure_rate > 0.3:
            recommendations.append("💡 Add more unit tests to catch issues early")
        
        durations = [r.duration for r in recent if r.duration > 0]
        if durations and statistics.mean(durations) > 600:  # > 10 minutes
            recommendations.append("⏱️ Long build times - Consider parallelizing build steps")
        
        # Check for flaky builds (alternating success/failure)
        statuses = [r.status for r in recent]
        flaky_count = sum(1 for i in range(1, len(statuses)) if statuses[i] != statuses[i-1])
        if flaky_count > len(statuses) * 0.6:
            recommendations.append("🎲 Flaky build detected - Check for intermittent test failures")
        
        if not recommendations:
            recommendations.append("✅ Build health looks good!")
        
        return recommendations
    
    def predict_outcome(self, job_name: str, branch: str) -> dict:
        """Predict build outcome based on historical data."""
        job_records = [r for r in self.records if r.job_name == job_name]
        branch_records = [r for r in job_records if r.branch == branch]
        
        # Use branch-specific data if available, otherwise job data
        relevant = branch_records if len(branch_records) >= 5 else job_records[-20:]
        
        if not relevant:
            return {
                'success_probability': 75,
                'confidence': 'low',
                'estimated_duration': 'Unknown',
                'risk_factors': ['No historical data available'],
                'suggestions': ['Monitor this build closely']
            }
        
        success_rate = len([r for r in relevant if r.status == 'SUCCESS']) / len(relevant)
        durations = [r.duration for r in relevant if r.status == 'SUCCESS' and r.duration > 0]
        avg_duration = statistics.mean(durations) if durations else 0
        
        risk_factors = []
        suggestions = []
        
        if success_rate < 0.7:
            risk_factors.append(f"⚠️ Historical success rate: {round(success_rate*100)}%")
        
        if 'hotfix' in branch.lower():
            risk_factors.append("🔥 Hotfix branch - ensure thorough testing")
            suggestions.append("Run smoke tests before deployment")
        
        if 'feature' in branch.lower():
            risk_factors.append("🆕 Feature branch - may have integration issues")
            suggestions.append("Check for merge conflicts with main")
        
        # Check recent trend
        recent = relevant[-5:]
        recent_failures = len([r for r in recent if r.status == 'FAILURE'])
        if recent_failures >= 3:
            risk_factors.append("📉 Recent builds have been failing")
            suggestions.append("Review recent changes before building")
        
        confidence = 'high' if len(relevant) >= 20 else 'medium' if len(relevant) >= 10 else 'low'
        
        return {
            'success_probability': round(success_rate * 100),
            'confidence': confidence,
            'estimated_duration': f"{int(avg_duration // 60)}m {int(avg_duration % 60)}s" if avg_duration else "Unknown",
            'risk_factors': risk_factors or ["✅ No significant risks identified"],
            'suggestions': suggestions or ["Build looks ready to go!"]
        }


# Global instance
analytics_engine = AnalyticsEngine()
