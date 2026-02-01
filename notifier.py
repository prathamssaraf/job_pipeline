"""
Email Notifier module for Job Pipeline Tracker.
Supports both Resend API and SMTP for sending notifications.
"""

import os
from datetime import datetime
from config import config

# Try to import resend
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False


class Notifier:
    """Email notification sender for new jobs."""
    
    def __init__(self):
        self.resend_api_key = os.getenv("RESEND_API_KEY", "")
        self.sender = config.EMAIL_SENDER
        self.password = config.EMAIL_PASSWORD
        self.recipient = config.EMAIL_RECIPIENT
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
    
    def _create_email_html(self, jobs: list[dict]) -> str:
        """Create HTML email content for job notifications."""
        job_rows = ""
        for job in jobs:
            url = job.get("url", "")
            # Make relative URLs absolute for Meta
            if url and url.startswith("/"):
                url = f"https://www.metacareers.com{url}"
            title_html = f'<a href="{url}">{job.get("title", "Unknown")}</a>' if url else job.get("title", "Unknown")
            
            job_rows += f'''
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">
                    <strong>{title_html}</strong><br>
                    <span style="color: #666;">{job.get("company", "Unknown")} • {job.get("location", "Not specified")}</span>
                </td>
            </tr>
            '''
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px; }}
                .job-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #888; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 {len(jobs)} New Job Opening{"s" if len(jobs) != 1 else ""} Found!</h1>
                <p>The following new positions have been posted:</p>
                
                <table class="job-table">
                    {job_rows}
                </table>
                
                <div class="footer">
                    <p>Sent by Job Pipeline Tracker • {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
                </div>
            </div>
        </body>
        </html>
        '''
        return html
    
    def _create_email_text(self, jobs: list[dict]) -> str:
        """Create plain text email content for job notifications."""
        lines = [
            f"🎯 {len(jobs)} New Job Opening{'s' if len(jobs) != 1 else ''} Found!",
            "",
            "The following new positions have been posted:",
            ""
        ]
        
        for i, job in enumerate(jobs, 1):
            url = job.get("url", "")
            if url and url.startswith("/"):
                url = f"https://www.metacareers.com{url}"
            
            lines.append(f"{i}. {job.get('title', 'Unknown')}")
            lines.append(f"   Company: {job.get('company', 'Unknown')}")
            lines.append(f"   Location: {job.get('location', 'Not specified')}")
            if url:
                lines.append(f"   Link: {url}")
            lines.append("")
        
        lines.append("---")
        lines.append(f"Sent by Job Pipeline Tracker • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        return "\n".join(lines)
    
    def _send_resend(self, jobs: list[dict]) -> bool:
        """Send email using Resend API."""
        if not RESEND_AVAILABLE:
            print("[Notifier] Resend not installed. Run: pip install resend")
            return False
        
        try:
            resend.api_key = self.resend_api_key
            
            response = resend.Emails.send({
                "from": "Job Tracker <onboarding@resend.dev>",
                "to": [self.recipient],
                "subject": f"🎯 {len(jobs)} New Job Opening{'s' if len(jobs) != 1 else ''} Found!",
                "html": self._create_email_html(jobs)
            })
            
            print(f"[Notifier] Email sent via Resend to {self.recipient}")
            return True
            
        except Exception as e:
            print(f"[Notifier] Resend failed: {e}")
            return False
    
    def _send_smtp(self, jobs: list[dict]) -> bool:
        """Send email using SMTP."""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🎯 {len(jobs)} New Job Opening{'s' if len(jobs) != 1 else ''} Found!"
            msg["From"] = self.sender
            msg["To"] = self.recipient
            
            text_part = MIMEText(self._create_email_text(jobs), "plain")
            html_part = MIMEText(self._create_email_html(jobs), "html")
            msg.attach(text_part)
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg)
            
            print(f"[Notifier] Email sent via SMTP to {self.recipient}")
            return True
            
        except Exception as e:
            print(f"[Notifier] SMTP failed: {e}")
            return False
    
    def send(self, jobs: list[dict]) -> bool:
        """
        Send email notification for new jobs.
        Uses Resend API if configured, otherwise falls back to SMTP.
        
        Args:
            jobs: List of job dictionaries to notify about
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not jobs:
            print("[Notifier] No jobs to notify about")
            return True
        
        if not self.recipient:
            print("[Notifier] No recipient configured")
            return False
        
        # Try Resend first if API key is configured
        if self.resend_api_key:
            return self._send_resend(jobs)
        
        # Fall back to SMTP
        if self.sender and self.password:
            return self._send_smtp(jobs)
        
        print("[Notifier] No email configuration found (set RESEND_API_KEY or SMTP credentials)")
        return False


# Default notifier instance
notifier = Notifier()
