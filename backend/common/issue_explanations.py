"""Deterministic, user-friendly issue explanations.

This module provides a structured explanation for *any* detected issue,
without requiring an external AI provider.

The UI currently renders descriptions as plain text, so the output here is
structured with headings and line breaks that remain readable even without
Markdown rendering.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


_URL_RE = re.compile(r"https?://[^\s\)\]\"\']+")


def _norm(s: Optional[str]) -> str:
    return (s or "").strip()


def _lower(s: Optional[str]) -> str:
    return _norm(s).lower()


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _extract_urls(text: str) -> List[str]:
    return _URL_RE.findall(text or "")


def _extract_status_code(text: str) -> Optional[str]:
    m = re.search(r"\b(\d{3})\b", text or "")
    return m.group(1) if m else None


def _filenames_from_urls(urls: List[str]) -> List[str]:
    names = []
    for u in urls:
        # strip query string
        u2 = u.split("?", 1)[0]
        names.append(u2.rsplit("/", 1)[-1])
    return [n for n in names if n]


def _resource_summary(issue: Dict) -> Tuple[List[str], List[str]]:
    """Return (resource_types, filenames) from issue context."""
    resource_types = issue.get("resource_types") or []
    urls = issue.get("resource_urls") or []
    title = _norm(issue.get("title"))
    desc = _norm(issue.get("description"))

    if not urls:
        urls = _extract_urls(f"{title} {desc}")

    filenames = _filenames_from_urls(urls)

    # Infer type if missing
    if not resource_types:
        blob = _lower(f"{title} {desc} {' '.join(filenames)}")
        if any(ext in blob for ext in [".woff", ".woff2", ".ttf", ".otf", ".eot"]):
            resource_types = ["font"]
        elif any(ext in blob for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]):
            resource_types = ["image"]
        elif any(ext in blob for ext in [".js", ".mjs"]):
            resource_types = ["script"]
        elif ".css" in blob:
            resource_types = ["stylesheet"]
        else:
            resource_types = []

    return _dedupe_keep_order([str(x) for x in resource_types if x]), _dedupe_keep_order(filenames)


def _classify(issue: Dict) -> str:
    title = _lower(issue.get("title"))
    desc = _lower(issue.get("description"))
    group_type = _lower(issue.get("group_type"))
    error_types = " ".join([_lower(x) for x in (issue.get("error_types") or [])])

    blob = " ".join([title, desc, group_type, error_types])

    if "cors" in blob or "cross-origin" in blob:
        return "cors"
    if "font" in blob and ("load" in blob or "failed" in blob):
        return "font_loading"
    if "alt" in blob and ("missing" in blob or "no" in blob):
        return "missing_alt_text"
    if "meta" in blob and "missing" in blob:
        return "missing_meta"
    if "aria" in blob:
        return "accessibility_aria"
    if "heading" in blob:
        return "accessibility_headings"
    if "contrast" in blob:
        return "accessibility_contrast"
    if "performance" in blob or "slow" in blob or "load time" in blob:
        return "performance"

    status = _extract_status_code(blob)
    if status:
        if status.startswith("4"):
            return "network_4xx"
        if status.startswith("5"):
            return "network_5xx"

    if "failed to load" in blob or "err_failed" in blob or "network" in blob:
        return "network"

    if "console" in blob and "error" in blob:
        return "console_error"

    return "generic"


def build_structured_issue_explanation(issue: Dict, test_type: str = "functional") -> str:
    """Generate a structured, user-friendly explanation for an issue.

    The output is plain text with line breaks so it stays readable even if the UI
    doesn't render Markdown.
    """

    title = _norm(issue.get("title", "Issue"))
    location = _norm(issue.get("location", ""))
    severity = _lower(issue.get("severity", ""))
    is_grouped = bool(issue.get("is_grouped"))
    frequency = int(issue.get("frequency") or 1)

    resource_types, filenames = _resource_summary(issue)
    kind = _classify(issue)

    # Short “context header”
    context_bits = []
    if location:
        context_bits.append(f"Location: {location}")
    if test_type:
        context_bits.append(f"Test: {test_type}")
    if severity:
        context_bits.append(f"Severity: {severity}")

    if is_grouped and frequency > 1:
        context_bits.append(f"Occurrences: {frequency}")

    context_line = " | ".join(context_bits)

    def files_line(max_files: int = 5) -> str:
        if not filenames:
            return ""
        show = filenames[:max_files]
        extra = len(filenames) - len(show)
        if extra > 0:
            return f"Files: {', '.join(show)} (+{extra} more)"
        return f"Files: {', '.join(show)}"

    # Helpers to keep language consistent
    def header(h: str) -> str:
        return f"{h}:"

    def bullet(s: str) -> str:
        return f"- {s}"

    def numbered(items: List[str]) -> str:
        return "\n".join([f"{i+1}. {items[i]}" for i in range(len(items))])

    lines: List[str] = []
    lines.append(f"{title}")
    if context_line:
        lines.append(context_line)

    fl = files_line()
    if fl:
        lines.append(fl)

    lines.append("")

    # Category-specific templates
    if kind == "cors":
        lines.append(header("What’s happening"))
        if resource_types:
            rt = ", ".join(resource_types)
            lines.append(bullet(f"The page tried to load {rt} files from another site, but the browser blocked them because of a security rule (CORS)."))
        else:
            lines.append(bullet("The page tried to load a resource from another site, but the browser blocked it because of a security rule (CORS)."))

        lines.append("")
        lines.append(header("Why it happens"))
        lines.append(bullet("When a file is hosted on a different domain/subdomain/port, the server must explicitly allow your site to use it."))
        lines.append(bullet("If the font/server/CDN response is missing the right 'Access-Control-Allow-Origin' header (or redirects to a host that’s missing it), the browser refuses to use the file."))

        lines.append("")
        lines.append(header("What visitors may notice"))
        if "font" in resource_types or any(re.search(r"\.(woff2?|ttf|otf|eot)$", f, re.I) for f in filenames):
            lines.append(bullet("Text may display in a fallback font (default system font) instead of your intended brand font."))
            lines.append(bullet("This can change spacing and cause minor layout shifts."))
        else:
            lines.append(bullet("Some assets may fail to display or behave as expected."))

        lines.append("")
        lines.append(header("Suggested fix"))
        steps = [
            "Confirm where the blocked files are served from (open DevTools → Network → click the failed request).",
            "On the server/CDN that serves those files, allow your website origin via CORS headers (for fonts, images, scripts, etc. as needed).",
            "Avoid cross-domain redirects for these assets, or ensure every redirect target sends the same CORS headers.",
            "Re-test and verify the requests are no longer blocked and the assets load successfully.",
        ]
        lines.append(numbered(steps))

        lines.append("")
        lines.append(header("Quick check"))
        lines.append(bullet("In the browser console, the CORS error disappears."))
        lines.append(bullet("In Network → the resource requests return 200 and are shown as loaded/used."))

    elif kind == "font_loading":
        lines.append(header("What’s happening"))
        lines.append(bullet("The page referenced custom fonts, but one or more font files failed to load."))

        lines.append("")
        lines.append(header("Why it happens"))
        lines.append(bullet("The font file URL is wrong, the file is missing, or it’s blocked by CORS/security headers."))
        lines.append(bullet("Sometimes a server serves fonts with the wrong content type or redirects to a different host."))

        lines.append("")
        lines.append(header("What visitors may notice"))
        lines.append(bullet("Text renders in a default font instead of your designed font."))
        lines.append(bullet("Branding looks inconsistent; spacing/line breaks may change."))

        lines.append("")
        lines.append(header("Suggested fix"))
        lines.append(numbered([
            "Check the failing font request(s) in DevTools → Network → Font and confirm the status code and response headers.",
            "If fonts are hosted on another domain, enable CORS for font extensions (.woff2/.woff/.ttf/.otf).",
            "Verify the font files exist at the referenced paths and that @font-face URLs are correct.",
            "Re-test to confirm fonts load and typography matches the design.",
        ]))

        lines.append("")
        lines.append(header("Quick check"))
        lines.append(bullet("No 'Failed to load font' errors in the console."))
        lines.append(bullet("Network shows the font files as loaded successfully."))

    elif kind in ("network_4xx", "network_5xx", "network"):
        status = _extract_status_code(_norm(issue.get("description"))) or _extract_status_code(_norm(issue.get("title")))
        lines.append(header("What’s happening"))
        if status:
            lines.append(bullet(f"A request failed while loading the page (HTTP {status})."))
        else:
            lines.append(bullet("A request failed while loading the page."))

        lines.append("")
        lines.append(header("Why it happens"))
        if status and status.startswith("4"):
            lines.append(bullet("The browser asked for a file/endpoint that the server couldn’t find (wrong path, removed file, or bad URL)."))
        elif status and status.startswith("5"):
            lines.append(bullet("The server encountered an error while trying to respond (backend crash, misconfiguration, or dependency issue)."))
        else:
            lines.append(bullet("The request may have been blocked, timed out, or the server returned an error."))

        lines.append("")
        lines.append(header("What visitors may notice"))
        lines.append(bullet("Parts of the page may be missing (images, styles, scripts) or features may not work."))
        lines.append(bullet("In some cases the page can look broken or stop responding."))

        lines.append("")
        lines.append(header("Suggested fix"))
        fix = [
            "Open DevTools → Network and find the failed request(s).",
            "Confirm the URL is correct and the resource exists.",
            "If it’s an API call, check server logs for the matching time and fix the backend error.",
            "Deploy the fix and re-run the test.",
        ]
        lines.append(numbered(fix))

        lines.append("")
        lines.append(header("Quick check"))
        lines.append(bullet("Failed requests no longer appear in Network."))

    elif kind == "missing_alt_text":
        lines.append(header("What’s happening"))
        lines.append(bullet("Some images are missing alternative text (alt text)."))

        lines.append("")
        lines.append(header("Why it matters"))
        lines.append(bullet("Screen readers use alt text to describe images to visually impaired users."))
        lines.append(bullet("It also helps when images fail to load."))

        lines.append("")
        lines.append(header("Suggested fix"))
        lines.append(numbered([
            "For each informative image, add a clear, short alt description.",
            "For decorative images, use empty alt text (alt=\"\") so screen readers skip them.",
            "If images come from a CMS, require alt text at upload time.",
        ]))

        lines.append("")
        lines.append(header("Quick check"))
        lines.append(bullet("Re-run the accessibility test and confirm the issue is gone."))

    elif kind.startswith("accessibility_"):
        lines.append(header("What’s happening"))
        lines.append(bullet("An accessibility issue was detected that can make the site harder to use for people with assistive technologies."))

        lines.append("")
        lines.append(header("Suggested fix"))
        lines.append(numbered([
            "Review the affected element(s) on the page and ensure labels/roles/structure are correct.",
            "Follow WCAG guidance for the specific problem (ARIA labels, heading order, color contrast, etc.).",
            "Re-test with both automated checks and keyboard navigation.",
        ]))

    elif kind == "performance":
        lines.append(header("What’s happening"))
        lines.append(bullet("The page appears to load or respond slower than expected."))

        lines.append("")
        lines.append(header("Why it happens"))
        lines.append(bullet("Large assets, too many requests, slow APIs, or heavy JavaScript can delay rendering."))

        lines.append("")
        lines.append(header("Suggested fix"))
        lines.append(numbered([
            "Check the slowest network requests in DevTools → Network (especially large JS/CSS/images).",
            "Enable caching/compression and optimize images and bundles.",
            "If APIs are slow, profile backend endpoints and add caching/indexing.",
        ]))

        lines.append("")
        lines.append(header("Quick check"))
        lines.append(bullet("Re-run the performance test and confirm load times improve."))

    else:
        # Generic fallback
        original = _norm(issue.get("description"))
        lines.append(header("What’s happening"))
        lines.append(bullet("An issue was detected during the automated test."))

        if original:
            lines.append("")
            lines.append(header("Details (from the test)"))
            lines.append(original)

        lines.append("")
        lines.append(header("Suggested next step"))
        lines.append(numbered([
            "Open the affected page and reproduce the problem manually if possible.",
            "Check the browser console and network tab for related errors.",
            "Fix the underlying cause and re-run the test to confirm it’s resolved.",
        ]))

    return "\n".join([l for l in lines if l is not None])
