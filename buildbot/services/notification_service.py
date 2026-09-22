"""
BuildBot Notification Service
Sends notifications via Google Chat and Email.
Compatible with Python 3.14+
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import requests

import sys
sys.path.append('..')
from config import settings
from core.models import BuildResult, BuildStatus

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending build notifications."""
    
    def __init__(self):
        self.gchat_webhook = settings.notifications.gchat_webhook_url
        self.smtp_host = settings.notifications.smtp_host
        self.smtp_port = settings.notifications.smtp_port
        self.smtp_user = settings.notifications.smtp_user
        self.smtp_password = settings.notifications.smtp_password
        self.email_from = settings.notifications.smtp_from
        self.email_to = settings.notifications.smtp_to
    
    def notify_build_complete(
        self,
        result: BuildResult,
        repo_url: str = "",
        branch: str = ""
    ) -> None:
        """
        Send notifications for completed build.
        
        Args:
            result: BuildResult with build information
            repo_url: Repository URL
            branch: Branch name
        """
        # Send Google Chat notification
        if self.gchat_webhook:
            try:
                self._send_gchat(result, repo_url, branch)
            except Exception as e:
                logger.error(f"Failed to send Google Chat notification: {e}")
        
        # Send email notification
        if self.smtp_host and self.email_to:
            try:
                self._send_email(result, repo_url, branch)
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")
    
    def _send_gchat(self, result: BuildResult, repo_url: str, branch: str) -> None:
        """Send notification to Google Chat."""
        build = result.build_info
        
        # Status emoji and color
        status_config = {
            BuildStatus.SUCCESS: ("✅", "#28a745"),
            BuildStatus.FAILURE: ("❌", "#dc3545"),
            BuildStatus.UNSTABLE: ("⚠️", "#ffc107"),
            BuildStatus.ABORTED: ("⏹️", "#6c757d"),
        }
        
        emoji, color = status_config.get(build.status, ("❓", "#6c757d"))
        
        # Build message card
        card = {
            "cards": [{
                "header": {
                    "title": f"{emoji} Build #{build.build_number} {build.status.value}",
                    "subtitle": f"Job: {build.job_name}"
                },
                "sections": [{
                    "widgets": [
                        {
                            "keyValue": {
                                "topLabel": "Repository",
                                "content": repo_url or "N/A"
                            }
                        },
                        {
                            "keyValue": {
                                "topLabel": "Branch",
                                "content": branch or "N/A"
                            }
                        },
                        {
                            "keyValue": {
                                "topLabel": "Duration",
                                "content": build.duration_str
                            }
                        }
                    ]
                }]
            }]
        }
        
        # Add artifacts path if available
        if result.artifacts_path:
            card["cards"][0]["sections"][0]["widgets"].append({
                "keyValue": {
                    "topLabel": "Artifacts",
                    "content": result.artifacts_path
                }
            })
        
        # Add link to Jenkins
        if build.url:
            card["cards"][0]["sections"].append({
                "widgets": [{
                    "buttons": [{
                        "textButton": {
                            "text": "VIEW IN JENKINS",
                            "onClick": {
                                "openLink": {
                                    "url": build.url
                                }
                            }
                        }
                    }]
                }]
            })
        
        # Send to webhook
        response = requests.post(
            self.gchat_webhook,
            json=card,
            timeout=10
        )
        response.raise_for_status()
        
        logger.info(f"Google Chat notification sent for build #{build.build_number}")
    
    def _send_email(self, result: BuildResult, repo_url: str, branch: str) -> None:
        """Send notification via email."""
        build = result.build_info
        
        # Status emoji
        status_emoji = {
            BuildStatus.SUCCESS: "✅",
            BuildStatus.FAILURE: "❌",
            BuildStatus.UNSTABLE: "⚠️",
            BuildStatus.ABORTED: "⏹️",
        }.get(build.status, "❓")
        
        subject = f"{status_emoji} Build #{build.build_number} {build.status.value} - {build.job_name}"
        
        # Build HTML body
        html = f"""
        <html>
        <body>
        <h2>{status_emoji} Build #{build.build_number} {build.status.value}</h2>
        
        <table style="border-collapse: collapse;">
            <tr>
                <td style="padding: 5px; font-weight: bold;">Job:</td>
                <td style="padding: 5px;">{build.job_name}</td>
            </tr>
            <tr>
                <td style="padding: 5px; font-weight: bold;">Repository:</td>
                <td style="padding: 5px;">{repo_url or 'N/A'}</td>
            </tr>
            <tr>
                <td style="padding: 5px; font-weight: bold;">Branch:</td>
                <td style="padding: 5px;">{branch or 'N/A'}</td>
            </tr>
            <tr>
                <td style="padding: 5px; font-weight: bold;">Duration:</td>
                <td style="padding: 5px;">{build.duration_str}</td>
            </tr>
        """
        
        if result.artifacts_path:
            html += f"""
            <tr>
                <td style="padding: 5px; font-weight: bold;">Artifacts:</td>
                <td style="padding: 5px;">{result.artifacts_path}</td>
            </tr>
            """
        
        html += """
        </table>
        """
        
        if build.url:
            html += f"""
            <p><a href="{build.url}">View in Jenkins</a></p>
            """
        
        # Add console output for failures
        if build.status == BuildStatus.FAILURE and result.console_output:
            html += f"""
            <h3>Console Output (last lines):</h3>
            <pre style="background: #f5f5f5; padding: 10px; overflow-x: auto;">
{result.console_output[-2000:]}
            </pre>
            """
        
        html += """
        <hr>
        <p style="color: #666; font-size: 12px;">Sent by BuildBot</p>
        </body>
        </html>
        """
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = self.email_to
        
        msg.attach(MIMEText(html, "html"))
        
        # Send email
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.email_from, self.email_to.split(","), msg.as_string())
        
        logger.info(f"Email notification sent for build #{build.build_number}")
    
    def send_simple_gchat(self, message: str) -> bool:
        """Send a simple text message to Google Chat."""
        if not self.gchat_webhook:
            return False
        
        try:
            response = requests.post(
                self.gchat_webhook,
                json={"text": message},
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Google Chat message: {e}")
            return False
