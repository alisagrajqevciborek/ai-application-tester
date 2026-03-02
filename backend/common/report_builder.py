"""
Shared helpers for building and persisting test reports.
"""

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def persist_report(
    test_run: Any,
    *,
    summary: str,
    detailed_report: str,
    issues_json: List[Dict[str, Any]],
    console_logs_json: List[Dict[str, Any]],
) -> None:
    """Create or update a Report row for a test run."""
    from apps.reports.models import Report

    Report.objects.update_or_create(  # type: ignore[attr-defined]
        test_run=test_run,
        defaults={
            "summary": summary,
            "detailed_report": detailed_report,
            "issues_json": issues_json,
            "console_logs_json": console_logs_json,
        },
    )


def build_failure_report_payload(
    *,
    summary: str,
    detail_prefix: str,
    console_error_prefix: str,
    exc: Exception,
) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build a standard payload for fatal task failures."""
    return (
        summary,
        f"{detail_prefix}\n\nError: {exc}",
        [],
        [
            {
                "type": "error",
                "text": f"{console_error_prefix}: {exc}",
            }
        ],
    )


def persist_failure_report(
    test_run: Any,
    *,
    summary: str,
    detail_prefix: str,
    console_error_prefix: str,
    exc: Exception,
) -> None:
    """Build and persist a standard failure report payload."""
    (
        report_summary,
        detailed_report,
        issues_json,
        console_logs_json,
    ) = build_failure_report_payload(
        summary=summary,
        detail_prefix=detail_prefix,
        console_error_prefix=console_error_prefix,
        exc=exc,
    )
    persist_report(
        test_run,
        summary=report_summary,
        detailed_report=detailed_report,
        issues_json=issues_json,
        console_logs_json=console_logs_json,
    )


def build_basic_suite_report_payload(
    *,
    application_name: str,
    application_url: str,
    test_type: str,
    status_result: str,
    pass_rate: int,
    fail_rate: int,
    issues: List[Dict[str, Any]],
) -> Tuple[str, str]:
    """Build the non-AI fallback report for single-suite runs."""
    if status_result == "success":
        summary = (
            f"Test suite completed successfully with {pass_rate}% pass rate. "
            "All critical user flows were validated."
        )
    else:
        critical_count = sum(1 for issue in issues if issue.get("severity") == "critical")
        major_count = sum(1 for issue in issues if issue.get("severity") == "major")
        summary = (
            f"Test suite encountered {fail_rate}% failures. "
            f"{critical_count} critical and {major_count} major issues found."
        )

    detailed_report = f"Test execution completed for {application_name} ({application_url}).\n\n"
    detailed_report += f"Test Type: {test_type}\n"
    detailed_report += f"Status: {status_result}\n"
    detailed_report += f"Pass Rate: {pass_rate}%\n"
    detailed_report += f"Fail Rate: {fail_rate}%\n\n"

    if issues:
        detailed_report += "Issues Found:\n"
        for idx, issue in enumerate(issues, 1):
            detailed_report += (
                f"\n{idx}. [{issue.get('severity', 'unknown').upper()}] "
                f"{issue.get('title', 'Unknown issue')}\n"
            )
            detailed_report += f"   Description: {issue.get('description', 'No description')}\n"
            detailed_report += f"   Location: {issue.get('location', 'Unknown')}\n"
    else:
        detailed_report += "No issues found during testing.\n"

    return summary, detailed_report


def build_single_suite_report_payload(
    *,
    test_run: Any,
    results: Dict[str, Any],
    test_type: str,
) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    Build summary, detailed report, and issue payload for regular single-suite runs.
    """
    from common.ai_helpers import generate_ai_report, enhance_issue_description
    from common.issue_grouper import group_similar_issues

    issues = results.get("issues", []) or []
    screenshot_urls = results.get("screenshots", []) or []

    grouped_issues = group_similar_issues(issues)

    enhanced_issues: List[Dict[str, Any]] = []
    for issue in grouped_issues:
        try:
            screenshot_url = issue.get("element_screenshot") or (
                issue.get("all_screenshots", [None])[0] if issue.get("is_grouped") else None
            )
            enhanced_issue = enhance_issue_description(
                issue,
                screenshot_url=screenshot_url,
                test_type=test_type,
            )
            enhanced_issues.append(enhanced_issue)
        except Exception as exc:
            logger.warning(f"Failed to enhance issue with AI: {exc}. Using original issue.")
            enhanced_issues.append(issue)

    try:
        report_data = generate_ai_report(
            test_results=results,
            application_name=test_run.application.name,
            application_url=test_run.application.url,
            test_type=test_type,
            screenshot_urls=screenshot_urls,
            console_logs=results.get("console_logs", []),
            network_failures=results.get("network_failures", []),
            network_requests=results.get("network_requests", []),
        )
        summary = report_data.get("summary", "")
        detailed_report = report_data.get("detailed_report", "")
    except Exception as exc:
        logger.warning(f"AI report generation failed, using fallback: {exc}")
        summary, detailed_report = build_basic_suite_report_payload(
            application_name=test_run.application.name,
            application_url=test_run.application.url,
            test_type=test_type,
            status_result=str(results.get("status", "failed")),
            pass_rate=int(results.get("pass_rate", 0)),
            fail_rate=int(results.get("fail_rate", 100)),
            issues=enhanced_issues,
        )

    return summary, detailed_report, enhanced_issues


def build_generated_test_case_report_payload(
    *,
    test_run: Any,
    results: Dict[str, Any],
    test_type: str,
    total_steps: int,
) -> Tuple[str, str, List[Dict[str, Any]]]:
    """Build summary, detailed report, and issue payload for generated test-case runs."""
    from common.issue_grouper import group_similar_issues

    issues = results.get("issues", []) or []
    grouped_issues = group_similar_issues(issues)

    pass_rate = int(results.get("pass_rate", 0))
    fail_rate = int(results.get("fail_rate", 100))
    status_result = str(results.get("status", "failed"))
    console_error_count = int(results.get("console_error_count", 0) or 0)
    console_warning_count = int(results.get("console_warning_count", 0) or 0)

    passed_steps = int(results.get("passed_steps", 0) or 0)
    failed_steps = int(results.get("failed_steps", 0) or 0)

    if status_result == "success":
        summary = (
            f"Generated test case completed successfully. {passed_steps}/{total_steps} "
            f"steps passed ({pass_rate}% pass rate)."
        )
        if console_warning_count > 0:
            summary += f" {console_warning_count} console warnings detected."
    else:
        summary = (
            f"Generated test case encountered failures. {passed_steps}/{total_steps} "
            f"steps passed, {failed_steps} failed ({fail_rate}% fail rate)."
        )
        if console_error_count > 0:
            summary += f" {console_error_count} console errors detected."

    detailed_report = "Generated Test Case Execution Report\n"
    detailed_report += f"{'=' * 50}\n\n"
    detailed_report += f"Application: {test_run.application.name} ({test_run.application.url})\n"
    detailed_report += f"Test Type: {test_type}\n"
    detailed_report += f"Status: {status_result}\n"
    detailed_report += f"Pass Rate: {pass_rate}%\n\n"

    detailed_report += "Step Results:\n"
    detailed_report += f"{'-' * 30}\n"

    step_results = results.get("step_results", []) or []
    for idx, step_result in enumerate(step_results, 1):
        status_icon = "\u2713" if step_result.get("passed") else "\u2717"
        detailed_report += (
            f"\n{idx}. [{status_icon}] {step_result.get('description', 'Unknown step')}\n"
        )
        if not step_result.get("passed"):
            detailed_report += f"   Error: {step_result.get('error', 'Unknown error')}\n"

    if grouped_issues:
        detailed_report += "\n\nIssues Found:\n"
        detailed_report += f"{'-' * 30}\n"
        for idx, issue in enumerate(grouped_issues, 1):
            frequency = int(issue.get("frequency", 1) or 1)
            freq_text = f" ({frequency} occurrences)" if frequency > 1 else ""
            detailed_report += (
                f"\n{idx}. [{issue.get('severity', 'unknown').upper()}] "
                f"{issue.get('title', 'Unknown issue')}{freq_text}\n"
            )
            detailed_report += f"   Description: {issue.get('description', 'No description')}\n"

    return summary, detailed_report, grouped_issues

