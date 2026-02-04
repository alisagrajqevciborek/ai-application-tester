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
        # Get the test run (without select_for_update since we're not in a transaction yet)
        test_run = TestRun.objects.get(pk=test_run_id)  # type: ignore[attr-defined]
        
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
                service.run_test(
                    url, 
                    test_type, 
                    screenshots_dir=None,
                    check_broken_links=test_run.check_broken_links or (test_type == 'broken_links'),
                    check_auth=test_run.check_auth or (test_type == 'authentication'),
                    auth_credentials={
                        'username': test_run.application.test_username,
                        'password': test_run.application.test_password,
                        'login_url': test_run.application.login_url,
                    } if (test_run.check_auth or test_type == 'authentication') else None
                )
            )
        finally:
            loop.close()
        
        # DEBUG: Log what we got from browser automation
        logger.info(f"Test results received: status={results.get('status')}, screenshots={results.get('screenshots', [])}")
        logger.info(f"Full results keys: {list(results.keys())}")
        
        # Update test run with results quickly so the UI can stop polling.
        with transaction.atomic():  # type: ignore[call-overload]
            test_run = TestRun.objects.select_for_update().get(pk=test_run_id)  # type: ignore[attr-defined]
            test_run.status = results.get('status', 'failed')
            test_run.pass_rate = results.get('pass_rate', 0)
            test_run.fail_rate = results.get('fail_rate', 100)
            test_run.completed_at = timezone.now()
            test_run.save()

        # Generate report from test results (can be slow; do NOT hold DB transaction).
        try:
            from apps.reports.models import Report
            from common.ai_helpers import generate_ai_report, enhance_issue_description

            issues = results.get('issues', [])
            screenshot_urls = results.get('screenshots', [])

            # Group similar issues together
            from common.issue_grouper import group_similar_issues
            grouped_issues = group_similar_issues(issues)

            # Enhance ALL issues with AI for better user-friendly descriptions
            enhanced_issues = []
            for issue in grouped_issues:
                try:
                    screenshot_url = issue.get('element_screenshot') or (
                        issue.get('all_screenshots', [None])[0] if issue.get('is_grouped') else None
                    )
                    enhanced_issue = enhance_issue_description(
                        issue,
                        screenshot_url=screenshot_url,
                        test_type=test_type,
                    )
                    enhanced_issues.append(enhanced_issue)
                except Exception as e:
                    logger.warning(f"Failed to enhance issue with AI: {e}. Using original issue.")
                    enhanced_issues.append(issue)

            final_issues = enhanced_issues

            # Generate AI-powered report (single comprehensive call)
            try:
                report_data = generate_ai_report(
                    test_results=results,
                    application_name=test_run.application.name,
                    application_url=test_run.application.url,
                    test_type=test_type,
                    screenshot_urls=screenshot_urls,
                    console_logs=results.get('console_logs', []),
                    network_failures=results.get('network_failures', []),
                    network_requests=results.get('network_requests', []),
                )
                summary = report_data.get('summary', '')
                detailed_report = report_data.get('detailed_report', '')
                logger.info(f"AI-enhanced report generated for test run {test_run_id}")
            except Exception as e:
                logger.warning(f"AI report generation failed, using fallback: {e}")
                pass_rate = results.get('pass_rate', 0)
                fail_rate = results.get('fail_rate', 100)
                status_result = results.get('status', 'failed')

                if status_result == 'success':
                    summary = f"Test suite completed successfully with {pass_rate}% pass rate. All critical user flows were validated."
                else:
                    critical_count = sum(1 for issue in final_issues if issue.get('severity') == 'critical')
                    major_count = sum(1 for issue in final_issues if issue.get('severity') == 'major')
                    summary = f"Test suite encountered {fail_rate}% failures. {critical_count} critical and {major_count} major issues found."

                detailed_report = f"Test execution completed for {test_run.application.name} ({test_run.application.url}).\n\n"
                detailed_report += f"Test Type: {test_type}\n"
                detailed_report += f"Status: {status_result}\n"
                detailed_report += f"Pass Rate: {pass_rate}%\n"
                detailed_report += f"Fail Rate: {fail_rate}%\n\n"

                if final_issues:
                    detailed_report += "Issues Found:\n"
                    for idx, issue in enumerate(final_issues, 1):
                        detailed_report += f"\n{idx}. [{issue.get('severity', 'unknown').upper()}] {issue.get('title', 'Unknown issue')}\n"
                        detailed_report += f"   Description: {issue.get('description', 'No description')}\n"
                        detailed_report += f"   Location: {issue.get('location', 'Unknown')}\n"
                else:
                    detailed_report += "No issues found during testing.\n"

            # Ensure failure diagnostics are visible to the user (video/trace URLs)
            # Artifacts are stored separately in TestArtifact model and accessible via API
            # No need to include them in the detailed_report text

            Report.objects.update_or_create(
                test_run=test_run,
                defaults={
                    'summary': summary,
                    'detailed_report': detailed_report,
                    'issues_json': final_issues,
                    'console_logs_json': results.get('console_logs', []),
                },
            )
            logger.info(f"Report generated for test run {test_run_id}")
        except Exception as e:
            logger.error(f"Error generating report for test run {test_run_id}: {e}", exc_info=True)

        # Save screenshots and artifacts (outside transaction)
        try:
            from .models import Screenshot, TestArtifact

            # Save screenshots
            screenshot_urls = results.get('screenshots', [])
            if screenshot_urls:
                for screenshot_url in screenshot_urls:
                    if screenshot_url:
                        try:
                            Screenshot.objects.create(  # type: ignore[attr-defined]
                                test_run=test_run,
                                cloudinary_url=screenshot_url,
                            )
                        except Exception as e:
                            logger.error(f"Error saving screenshot: {e}")

            # Save artifacts (videos, traces, before/after)
            artifacts = results.get('artifacts', [])
            logger.info(f"Found {len(artifacts)} artifacts to save")
            if artifacts:
                for idx, artifact in enumerate(artifacts):
                    if isinstance(artifact, dict) and artifact.get('url'):
                        try:
                            logger.info(f"Saving artifact {idx+1}/{len(artifacts)}: kind={artifact.get('kind')}, url={artifact.get('url')[:50]}...")
                            TestArtifact.objects.create(  # type: ignore[attr-defined]
                                test_run=test_run,
                                kind=artifact.get('kind', 'playwright_trace'),
                                url=artifact['url'],
                                step_name=artifact.get('note'),
                            )
                            logger.info(f"Successfully saved artifact {idx+1}")
                        except Exception as e:
                            logger.error(f"Error saving artifact {idx+1}: {e}", exc_info=True)
            else:
                logger.warning("No artifacts found in results")
        except Exception:
            logger.exception("Error saving screenshots/artifacts")
        
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


@shared_task(bind=True, max_retries=3)
def execute_generated_test_case_task(self, test_run_id, test_steps):
    """
    Execute a test run using custom generated test case steps.
    
    Args:
        test_run_id: The ID of the TestRun to execute
        test_steps: List of test steps to execute
    """
    try:
        # Get the test run
        test_run = TestRun.objects.get(pk=test_run_id)  # type: ignore[attr-defined]
        
        # Update status to running
        test_run.status = 'running'
        test_run.save()
        
        # Get application URL and test type
        url = test_run.application.url
        test_type = test_run.test_type
        
        logger.info(f"Starting generated test case run {test_run_id} for {url} (type: {test_type})")
        
        # Run the browser automation test with custom steps
        from common.browser_automation.generated_test_runner import GeneratedTestRunner
        
        # Import asyncio for running async test
        import asyncio
        
        # Create event loop and run test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            runner = GeneratedTestRunner()
            results = loop.run_until_complete(
                runner.run_test_case(
                    url=url,
                    test_type=test_type,
                    steps=test_steps,
                )
            )
        finally:
            loop.close()
        
        logger.info(f"Generated test results received: status={results.get('status')}")
        
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
            from common.issue_grouper import group_similar_issues

            issues = results.get('issues', [])
            screenshot_urls = results.get('screenshots', [])

            # Group similar issues together (like normal tests)
            grouped_issues = group_similar_issues(issues)

            # Build summary and detailed report
            pass_rate = results.get('pass_rate', 0)
            fail_rate = results.get('fail_rate', 100)
            status_result = results.get('status', 'failed')
            console_error_count = results.get('console_error_count', 0)
            console_warning_count = results.get('console_warning_count', 0)
            
            total_steps = len(test_steps)
            passed_steps = results.get('passed_steps', 0)
            failed_steps = results.get('failed_steps', 0)

            if status_result == 'success':
                summary = f"Generated test case completed successfully. {passed_steps}/{total_steps} steps passed ({pass_rate}% pass rate)."
                if console_warning_count > 0:
                    summary += f" {console_warning_count} console warnings detected."
            else:
                summary = f"Generated test case encountered failures. {passed_steps}/{total_steps} steps passed, {failed_steps} failed ({fail_rate}% fail rate)."
                if console_error_count > 0:
                    summary += f" {console_error_count} console errors detected."

            detailed_report = f"Generated Test Case Execution Report\n"
            detailed_report += f"{'=' * 50}\n\n"
            detailed_report += f"Application: {test_run.application.name} ({test_run.application.url})\n"
            detailed_report += f"Test Type: {test_type}\n"
            detailed_report += f"Status: {status_result}\n"
            detailed_report += f"Pass Rate: {pass_rate}%\n\n"
            
            detailed_report += f"Step Results:\n"
            detailed_report += f"{'-' * 30}\n"
            
            step_results = results.get('step_results', [])
            for idx, step_result in enumerate(step_results, 1):
                status_icon = "✓" if step_result.get('passed') else "✗"
                detailed_report += f"\n{idx}. [{status_icon}] {step_result.get('description', 'Unknown step')}\n"
                if not step_result.get('passed'):
                    detailed_report += f"   Error: {step_result.get('error', 'Unknown error')}\n"

            if grouped_issues:
                detailed_report += f"\n\nIssues Found:\n"
                detailed_report += f"{'-' * 30}\n"
                for idx, issue in enumerate(grouped_issues, 1):
                    frequency = issue.get('frequency', 1)
                    freq_text = f" ({frequency} occurrences)" if frequency > 1 else ""
                    detailed_report += f"\n{idx}. [{issue.get('severity', 'unknown').upper()}] {issue.get('title', 'Unknown issue')}{freq_text}\n"
                    detailed_report += f"   Description: {issue.get('description', 'No description')}\n"

            Report.objects.update_or_create(
                test_run=test_run,
                defaults={
                    'summary': summary,
                    'detailed_report': detailed_report,
                    'issues_json': grouped_issues,  # Use grouped issues
                    'console_logs_json': results.get('console_logs', []),
                },
            )
            logger.info(f"Report generated for generated test run {test_run_id}")
        except Exception as e:
            logger.error(f"Error generating report for test run {test_run_id}: {e}", exc_info=True)

        # Save screenshots
        try:
            from .models import Screenshot

            screenshot_urls = results.get('screenshots', [])
            if screenshot_urls:
                for screenshot_url in screenshot_urls:
                    if screenshot_url:
                        try:
                            Screenshot.objects.create(  # type: ignore[attr-defined]
                                test_run=test_run,
                                cloudinary_url=screenshot_url,
                            )
                        except Exception as e:
                            logger.error(f"Error saving screenshot: {e}")
        except Exception:
            logger.exception("Error saving screenshots")
        
        logger.info(f"Generated test run {test_run_id} completed with status: {test_run.status}")
        
    except TestRun.DoesNotExist:  # type: ignore[attr-defined]
        logger.error(f"TestRun {test_run_id} does not exist")
    except Exception as exc:
        logger.error(f"Error executing generated test run {test_run_id}: {exc}", exc_info=True)
        
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
