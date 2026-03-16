"""
Celery tasks for test execution.
"""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, List

from celery import shared_task, chord
from django.db import transaction
from django.utils import timezone

from common.browser_automation import BrowserAutomationService
from common.report_builder import (
    build_generated_test_case_report_payload,
    build_single_suite_report_payload,
    persist_failure_report,
    persist_report,
)
from .models import TestRun, TestRunStepResult

logger = logging.getLogger(__name__)


PARALLEL_GENERAL_STEP_CONFIG = [
    {"step_key": "functional", "step_label": "Functional Suite", "test_type": "functional"},
    {"step_key": "regression", "step_label": "Regression Suite", "test_type": "regression"},
    {"step_key": "performance", "step_label": "Performance Suite", "test_type": "performance"},
    {"step_key": "accessibility", "step_label": "Accessibility Suite", "test_type": "accessibility"},
]


def _upsert_step_result(
    test_run: TestRun,
    step_key: str,
    step_label: str,
    *,
    status: str,
    pass_rate: int | None = None,
    fail_rate: int | None = None,
    error_message: str | None = None,
    details_json: Dict[str, Any] | None = None,
    mark_started: bool = False,
    mark_completed: bool = False,
) -> None:
    step, _ = TestRunStepResult.objects.get_or_create(  # type: ignore[attr-defined]
        test_run=test_run,
        step_key=step_key,
        defaults={"step_label": step_label},
    )
    step.step_label = step_label
    step.status = status
    if pass_rate is not None:
        step.pass_rate = pass_rate
    if fail_rate is not None:
        step.fail_rate = fail_rate
    if error_message is not None:
        step.error_message = error_message
    if details_json is not None:
        step.details_json = details_json
    if mark_started and step.started_at is None:
        step.started_at = timezone.now()
    if mark_completed:
        step.completed_at = timezone.now()
    step.save()


def _build_parallel_general_steps(test_run: TestRun) -> List[Dict[str, Any]]:
    """Build per-suite step config for general test runs."""
    steps: List[Dict[str, Any]] = [dict(item) for item in PARALLEL_GENERAL_STEP_CONFIG]

    has_auth_creds = bool(
        test_run.application.test_username and
        test_run.application.test_password and
        test_run.application.login_url
    )
    if bool(test_run.check_broken_links):
        steps.append(
            {
                "step_key": "broken_links",
                "step_label": "Broken Links Check",
                "test_type": "functional",
                "check_broken_links": True,
                "check_auth": False,
                "auth_credentials": None,
            }
        )

    if bool(test_run.check_auth) and has_auth_creds:
        steps.append(
            {
                "step_key": "authentication",
                "step_label": "Authentication Check",
                "test_type": "functional",
                "check_broken_links": False,
                "check_auth": True,
                "auth_credentials": {
                    "username": test_run.application.test_username,
                    "password": test_run.application.test_password,
                    "login_url": test_run.application.login_url,
                },
            }
        )

    return steps


@shared_task(bind=True, max_retries=1)
def execute_test_run_step_task(
    self,
    test_run_id: int,
    step_key: str,
    step_label: str,
    step_test_type: str,
    check_broken_links: bool = False,
    check_auth: bool = False,
    auth_credentials: Dict[str, Any] | None = None,
):
    """
    Execute one test step (suite) for a parallelized general run.
    Returns a JSON-serializable result payload for chord aggregation.
    """
    logger.info(
        "Parallel step task started: run_id=%s step_key=%s label=%s type=%s "
        "check_broken_links=%s check_auth=%s",
        test_run_id,
        step_key,
        step_label,
        step_test_type,
        check_broken_links,
        check_auth,
    )
    try:
        test_run = TestRun.objects.get(pk=test_run_id)  # type: ignore[attr-defined]
        _upsert_step_result(
            test_run,
            step_key,
            step_label,
            status='running',
            mark_started=True,
            details_json={"test_type": step_test_type},
        )

        service = BrowserAutomationService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                service.run_test(
                    test_run.application.url,
                    step_test_type,
                    screenshots_dir=None,
                    check_broken_links=check_broken_links,
                    check_auth=check_auth,
                    auth_credentials=auth_credentials,
                )
            )
        finally:
            loop.close()

        pass_rate = int(results.get('pass_rate', 0))
        fail_rate = int(results.get('fail_rate', 100))
        status_value = str(results.get('status', 'failed'))

        _upsert_step_result(
            test_run,
            step_key,
            step_label,
            status=status_value,
            pass_rate=pass_rate,
            fail_rate=fail_rate,
            details_json={
                "issues_count": len(results.get("issues", [])),
                "screenshots_count": len(results.get("screenshots", [])),
                "test_type": step_test_type,
            },
            mark_completed=True,
        )

        logger.info(
            "Parallel step task completed: run_id=%s step_key=%s status=%s "
            "pass_rate=%s fail_rate=%s issues=%s screenshots=%s",
            test_run_id,
            step_key,
            status_value,
            pass_rate,
            fail_rate,
            len(results.get("issues", [])),
            len(results.get("screenshots", [])),
        )

        return {
            "step_key": step_key,
            "step_label": step_label,
            "status": status_value,
            "pass_rate": pass_rate,
            "fail_rate": fail_rate,
            "issues": results.get("issues", []),
            "screenshots": results.get("screenshots", []),
            "console_logs": results.get("console_logs", []),
            "network_requests": results.get("network_requests", []),
            "network_failures": results.get("network_failures", []),
            "artifacts": results.get("artifacts", []),
        }
    except Exception as exc:
        logger.error(f"Step task failed for run={test_run_id}, step={step_key}: {exc}", exc_info=True)
        try:
            test_run = TestRun.objects.get(pk=test_run_id)  # type: ignore[attr-defined]
            _upsert_step_result(
                test_run,
                step_key,
                step_label,
                status='failed',
                pass_rate=0,
                fail_rate=100,
                error_message=str(exc),
                details_json={"test_type": step_test_type},
                mark_started=True,
                mark_completed=True,
            )
        except Exception:
            logger.exception("Failed to save step failure status")

        return {
            "step_key": step_key,
            "step_label": step_label,
            "status": "failed",
            "pass_rate": 0,
            "fail_rate": 100,
            "issues": [{"severity": "critical", "title": f"{step_label} failed", "description": str(exc)}],
            "screenshots": [],
            "console_logs": [{"type": "error", "text": f"{step_label} failed: {exc}"}],
            "network_requests": [],
            "network_failures": [],
            "artifacts": [],
        }


@shared_task(bind=True, max_retries=1)
def aggregate_general_test_run_results(self, step_results, test_run_id: int):
    """Aggregate parallel suite results for a general test run."""
    logger.info(
        "Aggregation task started for run_id=%s with %s raw step_results entries",
        test_run_id,
        len(step_results or []),
    )
    try:
        test_run = TestRun.objects.get(pk=test_run_id)  # type: ignore[attr-defined]
    except TestRun.DoesNotExist:  # type: ignore[attr-defined]
        logger.error(f"Cannot aggregate results; TestRun {test_run_id} not found")
        return

    valid_results = [r for r in (step_results or []) if isinstance(r, dict)]
    logger.info(
        "Aggregation task: run_id=%s has %s valid step results",
        test_run_id,
        len(valid_results),
    )
    if not valid_results:
        valid_results = [
            {
                "step_key": "aggregation",
                "step_label": "Aggregation",
                "status": "failed",
                "pass_rate": 0,
                "fail_rate": 100,
                "issues": [{"severity": "critical", "title": "No step results", "description": "No results were returned from parallel step tasks."}],
                "screenshots": [],
                "console_logs": [{"type": "error", "text": "No parallel step results were returned."}],
                "network_requests": [],
                "network_failures": [],
                "artifacts": [],
            }
        ]

    pass_rates = [int(r.get("pass_rate", 0) or 0) for r in valid_results]
    avg_pass_rate = round(sum(pass_rates) / len(pass_rates)) if pass_rates else 0
    fail_rate = 100 - avg_pass_rate
    overall_status = 'success' if avg_pass_rate >= 70 else 'failed'

    all_issues: List[Dict[str, Any]] = []
    all_screenshots: List[str] = []
    all_console_logs: List[Dict[str, Any]] = []
    all_network_requests: List[Dict[str, Any]] = []
    all_network_failures: List[Dict[str, Any]] = []
    all_artifacts: List[Dict[str, Any]] = []

    for result in valid_results:
        all_issues.extend(result.get("issues", []) or [])
        all_console_logs.extend(result.get("console_logs", []) or [])
        all_network_requests.extend(result.get("network_requests", []) or [])
        all_network_failures.extend(result.get("network_failures", []) or [])
        all_artifacts.extend(result.get("artifacts", []) or [])
        for shot in (result.get("screenshots", []) or []):
            if isinstance(shot, str) and shot and shot not in all_screenshots:
                all_screenshots.append(shot)

    combined_results: Dict[str, Any] = {
        "status": overall_status,
        "pass_rate": avg_pass_rate,
        "fail_rate": fail_rate,
        "issues": all_issues,
        "screenshots": all_screenshots,
        "console_logs": all_console_logs,
        "network_requests": all_network_requests,
        "network_failures": all_network_failures,
        "artifacts": all_artifacts,
        "parallel_steps": [
            {
                "step_key": r.get("step_key"),
                "step_label": r.get("step_label"),
                "status": r.get("status"),
                "pass_rate": r.get("pass_rate"),
                "fail_rate": r.get("fail_rate"),
            }
            for r in valid_results
        ],
    }

    # Update final run status quickly so UI can stop polling.
    with transaction.atomic():  # type: ignore[call-overload]
        locked = TestRun.objects.select_for_update().get(pk=test_run_id)  # type: ignore[attr-defined]
        locked.status = overall_status
        locked.pass_rate = avg_pass_rate
        locked.fail_rate = fail_rate
        locked.completed_at = timezone.now()
        locked.save()

    # Persist report, screenshots, and artifacts — full detailed report like single-run flow.
    try:
        from common.ai_helpers import generate_ai_report, enhance_issue_description
        from common.issue_grouper import group_similar_issues

        # --- Step outcomes header (always present) ---
        step_lines = []
        for step in combined_results["parallel_steps"]:
            step_lines.append(
                f"- **{step.get('step_label')}**: {step.get('status')} "
                f"(pass {step.get('pass_rate', 0)}%, fail {step.get('fail_rate', 100)}%)"
            )
        step_outcomes_block = "## Step Outcomes\n\n" + "\n".join(step_lines) + "\n"

        # --- Group & AI-enhance issues (same as single-run path) ---
        grouped_issues = group_similar_issues(all_issues)

        enhanced_issues: List[Dict[str, Any]] = []
        for issue in grouped_issues:
            try:
                screenshot_url = issue.get('element_screenshot') or (
                    issue.get('all_screenshots', [None])[0] if issue.get('is_grouped') else None
                )
                enhanced_issue = enhance_issue_description(
                    issue,
                    screenshot_url=screenshot_url,
                    test_type='general',
                )
                enhanced_issues.append(enhanced_issue)
            except Exception as e:
                logger.warning(f"Failed to enhance issue with AI: {e}. Using original issue.")
                enhanced_issues.append(issue)

        final_issues = enhanced_issues

        # --- Generate AI-powered detailed report ---
        try:
            report_data = generate_ai_report(
                test_results=combined_results,
                application_name=test_run.application.name,
                application_url=test_run.application.url,
                test_type='general',
                screenshot_urls=all_screenshots,
                console_logs=all_console_logs,
                network_failures=all_network_failures,
                network_requests=all_network_requests,
            )
            summary = report_data.get('summary', '')
            detailed_report = report_data.get('detailed_report', '')
            logger.info(f"AI-enhanced report generated for parallel test run {test_run_id}")
        except Exception as e:
            logger.warning(f"AI report generation failed for parallel run, using fallback: {e}")
            # Fallback: build a rich text report manually
            if overall_status == 'success':
                summary = (
                    f"Parallel general test completed successfully with {avg_pass_rate}% pass rate "
                    f"across {len(combined_results['parallel_steps'])} parallel steps."
                )
            else:
                critical_count = sum(1 for i in final_issues if i.get('severity') == 'critical')
                major_count = sum(1 for i in final_issues if i.get('severity') == 'major')
                summary = (
                    f"Parallel general test encountered {fail_rate}% failures across "
                    f"{len(combined_results['parallel_steps'])} parallel steps. "
                    f"{critical_count} critical and {major_count} major issues found."
                )

            detailed_report = (
                f"Test execution completed for {test_run.application.name} "
                f"({test_run.application.url}).\n\n"
                f"Test Type: general (parallel)\n"
                f"Status: {overall_status}\n"
                f"Pass Rate: {avg_pass_rate}%\n"
                f"Fail Rate: {fail_rate}%\n\n"
            )

            if final_issues:
                detailed_report += "Issues Found:\n"
                for idx, issue in enumerate(final_issues, 1):
                    detailed_report += (
                        f"\n{idx}. [{issue.get('severity', 'unknown').upper()}] "
                        f"{issue.get('title', 'Unknown issue')}\n"
                        f"   Description: {issue.get('description', 'No description')}\n"
                        f"   Location: {issue.get('location', 'Unknown')}\n"
                    )
            else:
                detailed_report += "No issues found during testing.\n"

        # Prepend step outcomes block so it's always visible at the top
        detailed_report = step_outcomes_block + "\n---\n\n" + detailed_report

        # --- Per-step detailed sections ---
        detailed_report += "\n\n---\n\n## Detailed Results by Step\n"
        for result in valid_results:
            step_label = result.get("step_label", result.get("step_key", "Unknown"))
            step_status = result.get("status", "unknown")
            step_pass = result.get("pass_rate", 0)
            step_fail = result.get("fail_rate", 100)
            step_issues = result.get("issues", [])

            detailed_report += f"\n### {step_label}\n"
            detailed_report += f"- **Status:** {step_status}\n"
            detailed_report += f"- **Pass rate:** {step_pass}%\n"
            detailed_report += f"- **Fail rate:** {step_fail}%\n"
            detailed_report += f"- **Issues found:** {len(step_issues)}\n"

            if step_issues:
                detailed_report += "\n| # | Severity | Title | Location |\n"
                detailed_report += "|---|----------|-------|----------|\n"
                for idx, issue in enumerate(step_issues, 1):
                    sev = issue.get('severity', 'unknown').upper()
                    title = issue.get('title', 'Unknown issue')
                    loc = issue.get('location', 'Unknown')
                    detailed_report += f"| {idx} | {sev} | {title} | {loc} |\n"
                detailed_report += "\n"

                # Include full descriptions for each issue
                for idx, issue in enumerate(step_issues, 1):
                    detailed_report += (
                        f"**{idx}. [{issue.get('severity', 'unknown').upper()}] "
                        f"{issue.get('title', 'Unknown issue')}**\n\n"
                        f"{issue.get('description', 'No description')}\n\n"
                    )
            else:
                detailed_report += "\nNo issues found in this step.\n"

        persist_report(
            test_run,
            summary=summary,
            detailed_report=detailed_report,
            issues_json=final_issues,
            console_logs_json=all_console_logs,
        )
        logger.info(
            "Full detailed report persisted for parallel test run %s with overall_status=%s "
            "avg_pass_rate=%s fail_rate=%s issues=%s screenshots=%s artifacts=%s",
            test_run_id,
            overall_status,
            avg_pass_rate,
            fail_rate,
            len(all_issues),
            len(all_screenshots),
            len(all_artifacts),
        )
    except Exception:
        logger.exception("Failed to persist aggregated report")

    try:
        from .models import Screenshot, TestArtifact
        for screenshot_url in all_screenshots:
            if screenshot_url:
                try:
                    Screenshot.objects.create(test_run=test_run, cloudinary_url=screenshot_url)  # type: ignore[attr-defined]
                except Exception:
                    logger.exception("Failed to save aggregated screenshot")

        seen_artifact_keys: set = set()
        for artifact in all_artifacts:
            if isinstance(artifact, dict) and artifact.get("url"):
                artifact_key = (artifact.get("kind", "playwright_trace"), artifact["url"])
                if artifact_key in seen_artifact_keys:
                    continue
                seen_artifact_keys.add(artifact_key)
                try:
                    TestArtifact.objects.get_or_create(  # type: ignore[attr-defined]
                        test_run=test_run,
                        kind=artifact.get("kind", "playwright_trace"),
                        url=artifact["url"],
                        defaults={"step_name": artifact.get("note")},
                    )
                except Exception:
                    logger.exception("Failed to save aggregated artifact")
    except Exception:
        logger.exception("Failed to persist aggregated screenshots/artifacts")


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

        # Parallel slice: execute "general" runs as parallel suite steps via Celery chord.
        if test_type == 'general':
            step_configs = _build_parallel_general_steps(test_run)
            TestRunStepResult.objects.filter(test_run=test_run).delete()  # type: ignore[attr-defined]
            for step in step_configs:
                _upsert_step_result(
                    test_run,
                    step["step_key"],
                    step["step_label"],
                    status='pending',
                    details_json={"test_type": step.get("test_type", "functional")},
                )

            signatures = [
                execute_test_run_step_task.s(  # pyright: ignore[reportCallIssue]
                    test_run_id,
                    step["step_key"],
                    step["step_label"],
                    step.get("test_type", "functional"),
                    bool(step.get("check_broken_links", False)),
                    bool(step.get("check_auth", False)),
                    step.get("auth_credentials"),
                )
                for step in step_configs
            ]
            chord(signatures, aggregate_general_test_run_results.s(test_run_id)).apply_async()  # pyright: ignore[reportCallIssue]
            logger.info(
                "Queued parallel general execution for test run %s with %s steps",
                test_run_id,
                len(step_configs),
            )
            return
        
        # Run the browser automation test
        service = BrowserAutomationService()
        
        # Create event loop and run test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # "general" test_type is handled by the parallel branch above (which
            # returns early), so we only reach here for single-suite runs.
            app = test_run.application
            has_auth_creds = bool(app.test_username and app.test_password and app.login_url)

            check_broken_links = bool(test_run.check_broken_links) or (test_type == 'broken_links')

            auth_requested = bool(test_run.check_auth) or (test_type == 'authentication')
            auth_credentials = (
                {
                    'username': app.test_username,
                    'password': app.test_password,
                    'login_url': app.login_url,
                }
                if auth_requested and has_auth_creds
                else None
            )
            check_auth = auth_requested and auth_credentials is not None

            results = loop.run_until_complete(
                service.run_test(
                    url, 
                    test_type, 
                    screenshots_dir=None,
                    check_broken_links=check_broken_links,
                    check_auth=check_auth,
                    auth_credentials=auth_credentials,
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
            summary, detailed_report, final_issues = build_single_suite_report_payload(
                test_run=test_run,
                results=results,
                test_type=test_type,
            )

            # Ensure failure diagnostics are visible to the user (video/trace URLs)
            # Artifacts are stored separately in TestArtifact model and accessible via API
            # No need to include them in the detailed_report text
            persist_report(
                test_run,
                summary=summary,
                detailed_report=detailed_report,
                issues_json=final_issues,
                console_logs_json=results.get('console_logs', []),
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
                seen_screenshot_urls = set()
                for screenshot_url in screenshot_urls:
                    if screenshot_url:
                        if screenshot_url in seen_screenshot_urls:
                            continue
                        seen_screenshot_urls.add(screenshot_url)
                        try:
                            Screenshot.objects.get_or_create(  # type: ignore[attr-defined]
                                test_run=test_run,
                                cloudinary_url=screenshot_url,
                            )
                        except Exception as e:
                            logger.error(f"Error saving screenshot: {e}")

            # Save artifacts (videos, traces, before/after)
            artifacts = results.get('artifacts', [])
            logger.info(f"Found {len(artifacts)} artifacts to save")
            if artifacts:
                seen_artifact_keys = set()
                for idx, artifact in enumerate(artifacts):
                    if isinstance(artifact, dict):
                        url = artifact.get('url')
                        if not isinstance(url, str) or not url:
                            continue
                        kind = artifact.get('kind', 'playwright_trace')
                        artifact_key = (kind, url)
                        if artifact_key in seen_artifact_keys:
                            continue
                        seen_artifact_keys.add(artifact_key)
                        try:
                            logger.info(f"Saving artifact {idx+1}/{len(artifacts)}: kind={kind}, url={url[:50]}...")
                            TestArtifact.objects.get_or_create(  # type: ignore[attr-defined]
                                test_run=test_run,
                                kind=kind,
                                url=url,
                                defaults={'step_name': artifact.get('note')},
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
            try:
                persist_failure_report(
                    test_run,
                    summary='Test run failed before results were generated.',
                    detail_prefix='The test run failed during execution and no results were produced.',
                    console_error_prefix='Test run failed',
                    exc=exc,
                )
                logger.info(f"Fallback report generated for failed test run {test_run_id}")
            except Exception as report_exc:
                logger.error(f"Failed to create fallback report for test run {test_run_id}: {report_exc}")
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
            summary, detailed_report, grouped_issues = build_generated_test_case_report_payload(
                test_run=test_run,
                results=results,
                test_type=test_type,
                total_steps=len(test_steps),
            )
            persist_report(
                test_run,
                summary=summary,
                detailed_report=detailed_report,
                issues_json=grouped_issues,
                console_logs_json=results.get('console_logs', []),
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
            try:
                persist_failure_report(
                    test_run,
                    summary='Generated test case failed before results were generated.',
                    detail_prefix='The generated test case failed during execution and no results were produced.',
                    console_error_prefix='Generated test case failed',
                    exc=exc,
                )
                logger.info(f"Fallback report generated for failed generated test run {test_run_id}")
            except Exception as report_exc:
                logger.error(f"Failed to create fallback report for generated test run {test_run_id}: {report_exc}")
        except Exception:
            pass
        
        # Retry the task
        raise self.retry(exc=exc, countdown=60)


@shared_task(name='applications.cleanup_stalled_tests')
def cleanup_stalled_tests():
    """
    Periodic task: mark tests stuck in 'running' or 'pending' for over 1 hour as failed.
    Runs every 15 minutes via Celery Beat instead of blocking the stats endpoint.
    """
    timeout = timezone.now() - timedelta(hours=1)
    stalled = TestRun.objects.filter(  # type: ignore[attr-defined]
        status__in=['running', 'pending'],
        started_at__lt=timeout,
    )
    count = stalled.update(status='failed', pass_rate=0, fail_rate=100, completed_at=timezone.now())
    if count:
        logger.info(f"cleanup_stalled_tests: marked {count} stalled test(s) as failed")
    return count
