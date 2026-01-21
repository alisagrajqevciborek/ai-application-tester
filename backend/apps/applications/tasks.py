"""
Celery tasks for test execution.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import TestRun
from common.browser_automation import BrowserAutomationService
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def execute_test_run_task(self, test_run_id):
    """
    Execute a test run using browser automation.
    
    Args:
        test_run_id: The ID of the TestRun to execute
    """
    try:
        # Get the test run
        test_run = TestRun.objects.select_for_update().get(pk=test_run_id)  # type: ignore[attr-defined]
        
        # Update status to running
        test_run.status = 'running'
        test_run.save()
        
        # Get application URL and test type
        url = test_run.application.url
        test_type = test_run.test_type
        
        logger.info(f"Starting test run {test_run_id} for {url} (type: {test_type})")
        
        # Run the browser automation test
        service = BrowserAutomationService()
        
        # Import asyncio for running async test
        import asyncio
        
        # Create event loop and run test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                service.run_test(url, test_type, screenshots_dir=None)
            )
        finally:
            loop.close()
        
        # Update test run with results
        with transaction.atomic():  # type: ignore[call-overload]
            test_run = TestRun.objects.select_for_update().get(pk=test_run_id)  # type: ignore[attr-defined]
            test_run.status = results.get('status', 'failed')
            test_run.pass_rate = results.get('pass_rate', 0)
            test_run.fail_rate = results.get('fail_rate', 100)
            test_run.completed_at = timezone.now()
            test_run.save()
            
            # Generate report from test results
            try:
                from apps.reports.models import Report
                issues = results.get('issues', [])
                
                # Create summary
                pass_rate = results.get('pass_rate', 0)
                fail_rate = results.get('fail_rate', 100)
                status_result = results.get('status', 'failed')
                
                if status_result == 'success':
                    summary = f"Test suite completed successfully with {pass_rate}% pass rate. All critical user flows were validated."
                else:
                    critical_count = sum(1 for issue in issues if issue.get('severity') == 'critical')
                    major_count = sum(1 for issue in issues if issue.get('severity') == 'major')
                    summary = f"Test suite encountered {fail_rate}% failures. {critical_count} critical and {major_count} major issues found."
                
                # Create detailed report
                detailed_report = f"Test execution completed for {test_run.application.name} ({test_run.application.url}).\n\n"
                detailed_report += f"Test Type: {test_run.test_type}\n"
                detailed_report += f"Status: {status_result}\n"
                detailed_report += f"Pass Rate: {pass_rate}%\n"
                detailed_report += f"Fail Rate: {fail_rate}%\n\n"
                
                if issues:
                    detailed_report += "Issues Found:\n"
                    for idx, issue in enumerate(issues, 1):
                        detailed_report += f"\n{idx}. [{issue.get('severity', 'unknown').upper()}] {issue.get('title', 'Unknown issue')}\n"
                        detailed_report += f"   Description: {issue.get('description', 'No description')}\n"
                        detailed_report += f"   Location: {issue.get('location', 'Unknown')}\n"
                else:
                    detailed_report += "No issues found during testing.\n"
                
                # Create or update report
                Report.objects.update_or_create(
                    test_run=test_run,
                    defaults={
                        'summary': summary,
                        'detailed_report': detailed_report,
                        'issues_json': issues
                    }
                )
                logger.info(f"Report generated for test run {test_run_id}")
            except Exception as e:
                logger.error(f"Error generating report for test run {test_run_id}: {e}")
            
            # Save screenshots if any
            from .models import Screenshot
            import requests  # noqa: F401
            from django.core.files.base import ContentFile
            screenshot_paths = results.get('screenshots', [])
            for screenshot_url in screenshot_paths:
                if screenshot_url:
                    try:
                        # Download the image from Cloudinary URL and save it
                        # Cloudinary storage will handle the upload automatically
                        response = requests.get(screenshot_url, timeout=10)
                        if response.status_code == 200:
                            # Extract filename from URL
                            filename = screenshot_url.split('/')[-1].split('?')[0]
                            if not filename.endswith('.png'):
                                filename = f"screenshot_{test_run_id}_{len(screenshot_paths)}.png"
                            
                            # Create Screenshot with the downloaded image
                            screenshot = Screenshot(test_run=test_run)
                            screenshot.image.save(  # type: ignore[attr-defined]
                                filename,
                                ContentFile(response.content),
                                save=True
                            )
                            logger.info(f"Saved screenshot: {screenshot_url}")
                    except Exception as e:
                        logger.error(f"Error saving screenshot from {screenshot_url}: {e}")
        
        logger.info(f"Test run {test_run_id} completed with status: {test_run.status}")
        
    except TestRun.DoesNotExist:  # type: ignore[attr-defined]
        logger.error(f"TestRun {test_run_id} does not exist")
    except Exception as exc:
        logger.error(f"Error executing test run {test_run_id}: {exc}", exc_info=True)
        
        # Mark test run as failed
        try:
            with transaction.atomic():  # type: ignore[call-overload]
                test_run = TestRun.objects.select_for_update().get(pk=test_run_id)  # type: ignore[attr-defined]
                test_run.status = 'failed'
                test_run.completed_at = timezone.now()
                test_run.save()
        except Exception:
            pass
        
        # Retry the task
        raise self.retry(exc=exc, countdown=60)
