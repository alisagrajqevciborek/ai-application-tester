"""
Jira integration service for exporting bugs and console logs.
"""
import logging
import os
from typing import Dict, List, Optional
from io import BytesIO
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class JiraService:
    """Service for interacting with Jira API."""
    
    def __init__(self):
        """Initialize Jira service with configuration from settings."""
        self.jira_url = getattr(settings, 'JIRA_URL', os.getenv('JIRA_URL', ''))
        self.jira_email = getattr(settings, 'JIRA_EMAIL', os.getenv('JIRA_EMAIL', ''))
        self.jira_api_token = getattr(settings, 'JIRA_API_TOKEN', os.getenv('JIRA_API_TOKEN', ''))
        self.jira_project_key = getattr(settings, 'JIRA_PROJECT_KEY', os.getenv('JIRA_PROJECT_KEY', ''))
        self.jira_issue_type = getattr(settings, 'JIRA_ISSUE_TYPE', os.getenv('JIRA_ISSUE_TYPE', 'Task'))
        
        self._jira_client = None
    
    def _get_jira_client(self):
        """Get or create Jira client instance."""
        if self._jira_client is None:
            try:
                from jira import JIRA
                
                if not all([self.jira_url, self.jira_email, self.jira_api_token, self.jira_project_key]):
                    raise ValueError("Missing required Jira configuration. Please set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_PROJECT_KEY.")
                
                self._jira_client = JIRA(
                    server=self.jira_url,
                    basic_auth=(self.jira_email, self.jira_api_token)
                )
            except ImportError:
                raise ImportError("Jira library not installed. Please install it with: pip install jira")
            except Exception as e:
                logger.error(f"Failed to initialize Jira client: {e}")
                raise
        
        return self._jira_client
    
    def format_console_logs_for_jira(self, logs: List[Dict], log_type: str) -> str:
        """
        Format console logs as markdown for Jira description.
        
        Args:
            logs: List of console log entries
            log_type: Type of logs ('error' or 'warning')
        
        Returns:
            Formatted markdown string
        """
        if not logs:
            return ""
        
        markdown = f"h3. {log_type.capitalize()} Logs ({len(logs)} total)\n\n"
        markdown += "||#||Message||Location||\n"
        
        for idx, log in enumerate(logs, 1):
            message = log.get('text', 'Unknown message')
            # Escape pipe characters for Jira table
            message = message.replace('|', '\\|')
            location = log.get('location', 'N/A')
            location = location.replace('|', '\\|')
            markdown += f"|{idx}|{message}|{location}|\n"
        
        return markdown
    
    def download_screenshot(self, url: str) -> Optional[BytesIO]:
        """
        Download screenshot from URL.
        
        Args:
            url: Screenshot URL
        
        Returns:
            BytesIO object with image data, or None if download fails
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return BytesIO(response.content)
        except Exception as e:
            logger.warning(f"Failed to download screenshot from {url}: {e}")
            return None
    
    def create_jira_ticket(
        self,
        title: str,
        description: str,
        screenshot_urls: Optional[List[str]] = None
    ) -> Optional[Dict[str, str]]:
        """
        Create a Jira ticket with optional screenshot attachments.
        
        Args:
            title: Ticket title
            description: Ticket description (supports Jira markdown)
            screenshot_urls: Optional list of screenshot URLs to attach
        
        Returns:
            Dict with 'key' and 'url' of created ticket, or None if creation fails
        """
        try:
            jira = self._get_jira_client()
            
            # Create issue
            issue_dict = {
                'project': {'key': self.jira_project_key},
                'summary': title,
                'description': description,
                'issuetype': {'name': self.jira_issue_type},
            }
            
            new_issue = jira.create_issue(fields=issue_dict)
            
            # Attach screenshots if provided
            if screenshot_urls:
                for screenshot_url in screenshot_urls:
                    try:
                        screenshot_data = self.download_screenshot(screenshot_url)
                        if screenshot_data:
                            # Reset BytesIO position to beginning
                            screenshot_data.seek(0)
                            
                            # Extract filename from URL or use default
                            filename = screenshot_url.split('/')[-1].split('?')[0]
                            if not filename or '.' not in filename:
                                filename = 'screenshot.png'
                            
                            jira.add_attachment(
                                issue=new_issue.key,
                                attachment=screenshot_data,
                                filename=filename
                            )
                            logger.info(f"Attached screenshot {filename} to ticket {new_issue.key}")
                    except Exception as e:
                        logger.warning(f"Failed to attach screenshot {screenshot_url} to ticket {new_issue.key}: {e}")
            
            ticket_url = f"{self.jira_url}/browse/{new_issue.key}"
            
            return {
                'key': new_issue.key,
                'url': ticket_url
            }
        except Exception as e:
            logger.error(f"Failed to create Jira ticket: {e}", exc_info=True)
            raise
    
    def export_console_logs_to_jira(
        self,
        application_name: str,
        application_url: str,
        test_run_id: int,
        test_type: str,
        test_date: str,
        console_logs: List[Dict],
        screenshot_urls: Optional[List[str]] = None
    ) -> Dict[str, Optional[Dict[str, str]]]:
        """
        Export console logs to Jira as grouped tickets (errors and warnings).
        
        Args:
            application_name: Name of the application
            application_url: URL of the application
            test_run_id: ID of the test run
            test_type: Type of test
            test_date: Date of the test run
            console_logs: List of console log entries
            screenshot_urls: Optional list of screenshot URLs (not required)
        
        Returns:
            Dict with 'error_ticket' and 'warning_ticket' (each can be None)
        """
        # Filter errors and warnings
        errors = [log for log in console_logs if log.get('type') == 'error']
        warnings = [log for log in console_logs if log.get('type') == 'warning']
        
        # Get screenshot URLs for errors and warnings (optional)
        error_screenshot_urls = []
        warning_screenshot_urls = []
        
        # Only collect screenshots if they exist in console logs
        for log in errors:
            if log.get('screenshot'):
                error_screenshot_urls.append(log['screenshot'])
        
        for log in warnings:
            if log.get('screenshot'):
                warning_screenshot_urls.append(log['screenshot'])
        
        result: Dict[str, Optional[Dict[str, str]]] = {
            'error_ticket': None,
            'warning_ticket': None
        }
        
        # Create error ticket if errors exist
        if errors:
            try:
                error_title = f"[TestFlow] Console Errors - {application_name} - Test Run #{test_run_id}"
                error_description = self._build_ticket_description(
                    application_name=application_name,
                    application_url=application_url,
                    test_run_id=test_run_id,
                    test_type=test_type,
                    test_date=test_date,
                    logs=errors,
                    log_type='error',
                    screenshot_urls=error_screenshot_urls
                )
                
                result['error_ticket'] = self.create_jira_ticket(
                    title=error_title,
                    description=error_description,
                    screenshot_urls=error_screenshot_urls[:10] if error_screenshot_urls else None  # Limit to 10 attachments, only if available
                )
            except Exception as e:
                logger.error(f"Failed to create error ticket: {e}", exc_info=True)
        
        # Create warning ticket if warnings exist
        if warnings:
            try:
                warning_title = f"[TestFlow] Console Warnings - {application_name} - Test Run #{test_run_id}"
                warning_description = self._build_ticket_description(
                    application_name=application_name,
                    application_url=application_url,
                    test_run_id=test_run_id,
                    test_type=test_type,
                    test_date=test_date,
                    logs=warnings,
                    log_type='warning',
                    screenshot_urls=warning_screenshot_urls
                )
                
                result['warning_ticket'] = self.create_jira_ticket(
                    title=warning_title,
                    description=warning_description,
                    screenshot_urls=warning_screenshot_urls[:10] if warning_screenshot_urls else None  # Limit to 10 attachments, only if available
                )
            except Exception as e:
                logger.error(f"Failed to create warning ticket: {e}", exc_info=True)
        
        return result
    
    def _build_ticket_description(
        self,
        application_name: str,
        application_url: str,
        test_run_id: int,
        test_type: str,
        test_date: str,
        logs: List[Dict],
        log_type: str,
        screenshot_urls: List[str]
    ) -> str:
        """
        Build Jira ticket description with test run information and console logs.
        
        Args:
            application_name: Name of the application
            application_url: URL of the application
            test_run_id: ID of the test run
            test_type: Type of test
            test_date: Date of the test run
            logs: List of console log entries
            log_type: Type of logs ('error' or 'warning')
            screenshot_urls: List of screenshot URLs
        
        Returns:
            Formatted Jira markdown description
        """
        description = f"h2. Test Run Information\n\n"
        description += f"*Application:* {application_name}\n"
        description += f"*Application URL:* {application_url}\n"
        description += f"*Test Run ID:* {test_run_id}\n"
        description += f"*Test Type:* {test_type}\n"
        description += f"*Test Date:* {test_date}\n"
        description += f"*Total {log_type.capitalize()}s:* {len(logs)}\n\n"
        
        description += f"h2. Console {log_type.capitalize()}s\n\n"
        description += self.format_console_logs_for_jira(logs, log_type)
        
        # Only mention screenshots if they exist
        if screenshot_urls:
            description += f"\nh3. Screenshots\n\n"
            description += f"{{color:green}}{len(screenshot_urls)} screenshot(s) attached to this ticket.{{color}}\n\n"
        
        description += f"\nh2. Additional Information\n\n"
        description += f"This ticket was automatically created by TestFlow AI Application Tester.\n"
        description += f"For more details, please refer to the test run report.\n"
        
        return description

