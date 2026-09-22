"""
BuildBot Rollback Manager
Automated rollback suggestions and management.
Compatible with Python 3.14+
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RollbackCandidate:
    """Candidate build for rollback."""
    job_name: str
    build_number: int
    timestamp: datetime
    branch: str
    commit: str = ""
    status: str = "SUCCESS"
    duration: int = 0
    artifacts_available: bool = True
    confidence_score: float = 0.0
    reason: str = ""


@dataclass
class RollbackPlan:
    """Plan for executing a rollback."""
    id: str
    current_build: int
    target_build: int
    job_name: str
    steps: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    estimated_time: str = ""
    requires_approval: bool = True
    approved_by: str = ""
    status: str = "pending"  # pending, approved, executing, completed, failed


class RollbackManager:
    """Manages rollback suggestions and execution."""
    
    def __init__(self, jenkins_service=None):
        self.jenkins = jenkins_service
        self.rollback_history: list[RollbackPlan] = []
    
    def set_jenkins(self, jenkins_service):
        """Set the Jenkins service."""
        self.jenkins = jenkins_service
    
    def analyze_failure(self, job_name: str, failed_build: int) -> dict:
        """Analyze a failed build and suggest rollback options."""
        if not self.jenkins:
            return {"error": "Jenkins service not available"}
        
        try:
            # Get build history
            history = self.jenkins.get_build_history(job_name, limit=20)
            
            # Find successful builds before the failure
            candidates = []
            for build in history:
                if build['number'] < failed_build and build['result'] == 'SUCCESS':
                    candidates.append(RollbackCandidate(
                        job_name=job_name,
                        build_number=build['number'],
                        timestamp=build.get('datetime', datetime.now()),
                        branch=build.get('branch', 'unknown'),
                        status='SUCCESS',
                        duration=build.get('duration', 0)
                    ))
            
            if not candidates:
                return {
                    "can_rollback": False,
                    "reason": "No successful builds found for rollback",
                    "candidates": [],
                    "recommendation": None
                }
            
            # Score candidates
            for candidate in candidates:
                candidate.confidence_score = self._calculate_confidence(candidate, failed_build)
                candidate.reason = self._get_candidate_reason(candidate)
            
            # Sort by confidence
            candidates.sort(key=lambda x: x.confidence_score, reverse=True)
            
            # Get recommendation
            best = candidates[0] if candidates else None
            
            return {
                "can_rollback": True,
                "candidates": candidates[:5],  # Top 5 candidates
                "recommendation": best,
                "analysis": self._generate_analysis(job_name, failed_build, best)
            }
            
        except Exception as e:
            logger.error(f"Rollback analysis failed: {e}")
            return {"error": str(e)}
    
    def _calculate_confidence(self, candidate: RollbackCandidate, failed_build: int) -> float:
        """Calculate confidence score for a rollback candidate."""
        score = 100.0
        
        # Penalize older builds
        builds_back = failed_build - candidate.build_number
        score -= builds_back * 5  # -5 points per build
        
        # Penalize if too old (more than 7 days)
        age_days = (datetime.now() - candidate.timestamp).days
        if age_days > 7:
            score -= (age_days - 7) * 2
        
        # Bonus for recent successful builds
        if builds_back == 1:
            score += 20  # Previous build bonus
        
        return max(0, min(100, score))
    
    def _get_candidate_reason(self, candidate: RollbackCandidate) -> str:
        """Get reason string for a candidate."""
        age = datetime.now() - candidate.timestamp
        
        if age.days == 0:
            time_str = f"{age.seconds // 3600}h ago"
        else:
            time_str = f"{age.days}d ago"
        
        return f"Build #{candidate.build_number} ({time_str}) - {candidate.confidence_score:.0f}% confidence"
    
    def _generate_analysis(self, job_name: str, failed_build: int, best: Optional[RollbackCandidate]) -> dict:
        """Generate analysis for rollback decision."""
        if not best:
            return {
                "summary": "No suitable rollback candidate found",
                "risks": ["Manual intervention may be required"],
                "steps": ["Review build logs", "Fix the issue manually"]
            }
        
        builds_back = failed_build - best.build_number
        
        return {
            "summary": f"Recommend rollback to build #{best.build_number} ({builds_back} build(s) back)",
            "risks": self._assess_risks(best, builds_back),
            "steps": self._generate_rollback_steps(job_name, failed_build, best.build_number),
            "estimated_time": "5-10 minutes"
        }
    
    def _assess_risks(self, candidate: RollbackCandidate, builds_back: int) -> list[str]:
        """Assess risks of rolling back."""
        risks = []
        
        if builds_back > 5:
            risks.append("⚠️ Rolling back multiple builds may lose recent features")
        
        age_days = (datetime.now() - candidate.timestamp).days
        if age_days > 3:
            risks.append("⚠️ Target build is more than 3 days old")
        
        if not candidate.artifacts_available:
            risks.append("❌ Artifacts may not be available")
        
        if not risks:
            risks.append("✅ Low risk rollback")
        
        return risks
    
    def _generate_rollback_steps(self, job_name: str, current: int, target: int) -> list[str]:
        """Generate steps for rollback execution."""
        return [
            f"1. Verify build #{target} artifacts are available",
            f"2. Create rollback branch from build #{target}",
            f"3. Deploy artifacts from build #{target}",
            f"4. Run smoke tests",
            f"5. Monitor for 15 minutes",
            f"6. Mark rollback as complete or escalate"
        ]
    
    def create_rollback_plan(
        self,
        job_name: str,
        current_build: int,
        target_build: int
    ) -> RollbackPlan:
        """Create a rollback plan."""
        import uuid
        
        plan = RollbackPlan(
            id=str(uuid.uuid4())[:8],
            current_build=current_build,
            target_build=target_build,
            job_name=job_name,
            steps=self._generate_rollback_steps(job_name, current_build, target_build),
            risks=self._assess_risks(
                RollbackCandidate(job_name=job_name, build_number=target_build, timestamp=datetime.now(), branch=""),
                current_build - target_build
            ),
            estimated_time="5-10 minutes"
        )
        
        self.rollback_history.append(plan)
        return plan
    
    def approve_rollback(self, plan_id: str, approved_by: str) -> bool:
        """Approve a rollback plan."""
        for plan in self.rollback_history:
            if plan.id == plan_id:
                plan.approved_by = approved_by
                plan.status = "approved"
                return True
        return False
    
    def execute_rollback(self, plan_id: str) -> dict:
        """Execute an approved rollback plan."""
        for plan in self.rollback_history:
            if plan.id == plan_id:
                if plan.status != "approved":
                    return {"error": "Rollback not approved"}
                
                plan.status = "executing"
                
                try:
                    # Trigger build with target build's parameters
                    # In production, this would restore artifacts or trigger a specific build
                    if self.jenkins:
                        result = self.jenkins.trigger_build(
                            plan.job_name,
                            {"ROLLBACK_TO": str(plan.target_build)}
                        )
                        plan.status = "completed"
                        return {"success": True, "result": result}
                    else:
                        plan.status = "completed"
                        return {"success": True, "message": "Rollback plan marked as executed (dry run)"}
                        
                except Exception as e:
                    plan.status = "failed"
                    return {"error": str(e)}
        
        return {"error": "Plan not found"}
    
    def get_rollback_history(self, job_name: str = None) -> list[RollbackPlan]:
        """Get rollback history."""
        if job_name:
            return [p for p in self.rollback_history if p.job_name == job_name]
        return self.rollback_history
    
    def suggest_prevention(self, job_name: str, failure_count: int) -> list[str]:
        """Suggest ways to prevent future failures."""
        suggestions = []
        
        if failure_count >= 3:
            suggestions.append("🔍 Review recent code changes for patterns")
            suggestions.append("🧪 Add more comprehensive tests")
        
        if failure_count >= 5:
            suggestions.append("🚦 Consider adding pre-commit hooks")
            suggestions.append("📋 Implement code review requirements")
        
        suggestions.append("📊 Enable build notifications for early detection")
        suggestions.append("⏰ Schedule regular health checks")
        
        return suggestions


# Global instance
rollback_manager = RollbackManager()
