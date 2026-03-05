"""
Script code generation for AI-generated test cases.

This module takes the normalized JSON test case structure produced by
`generate_test_case_from_prompt` and renders executable test scripts
for different automation frameworks.

Supported frameworks:
- "playwright" -> Playwright TypeScript (@playwright/test)
- "selenium"   -> Selenium Python (pytest-style test function)
- "cypress"    -> Cypress JavaScript
"""

from __future__ import annotations

import re
from typing import Dict, List, Literal, Optional


FrameworkName = Literal["playwright", "selenium", "cypress"]


def generate_script(
    test_case: Dict,
    framework: FrameworkName,
) -> str:
    """
    Generate a test script for the given framework from a normalized test case.

    The `test_case` dict is expected to have at least:
      - name: str
      - description: str
      - steps: List[Dict] with keys:
          - order: int
          - action: str
          - selector: Optional[str]
          - value: Optional[str]
          - description: str
          - expected_result: str
    """
    name = str(test_case.get("name") or "Generated Test Case")
    description = str(test_case.get("description") or "")
    steps: List[Dict] = list(test_case.get("steps") or [])

    if framework == "playwright":
        return _render_playwright_ts(name, description, steps)
    if framework == "selenium":
        return _render_selenium_py(name, description, steps)
    if framework == "cypress":
        return _render_cypress_js(name, description, steps)

    raise ValueError(f"Unsupported framework: {framework}")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _slugify_name(name: str) -> str:
    """Create a safe identifier-like slug from a test name."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_")
    if not slug:
        slug = "generated_test"
    if slug[0].isdigit():
        slug = f"test_{slug}"
    return slug.lower()


def _escape_js_string(value: str) -> str:
    """Escape a string for inclusion in single-quoted JS/TS string literals."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _escape_py_string(value: str) -> str:
    """Escape a string for inclusion in single-quoted Python string literals."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _indent(line: str, level: int = 1, size: int = 2) -> str:
    return (" " * (level * size)) + line if line else ""


# ---------------------------------------------------------------------------
# Playwright TypeScript (@playwright/test)
# ---------------------------------------------------------------------------


def _render_playwright_ts(name: str, description: str, steps: List[Dict]) -> str:
    test_id = _slugify_name(name)
    lines: List[str] = []

    lines.append("import { test, expect } from '@playwright/test';")
    lines.append("")
    lines.append(f"test('{_escape_js_string(name)}', async ({'{ page }'}) => {{")
    if description:
        lines.append(_indent(f"// {description}", 1, 2))
    lines.append("")

    for step in sorted(steps, key=lambda s: int(s.get("order", 0))):
        action = str(step.get("action") or "wait").lower()
        selector = step.get("selector")
        value = step.get("value")
        step_desc = step.get("description") or f"Step {step.get('order')}"
        expected = step.get("expected_result") or ""

        # Comment describing the step
        lines.append(_indent(f"// {step_desc}", 1, 2))

        if action == "navigate":
            url = _escape_js_string(str(value or ""))
            lines.append(_indent(f"await page.goto('{url}');", 1, 2))

        elif action in ("click", "check", "uncheck", "hover", "scroll"):
            if not selector:
                lines.append(_indent("// TODO: selector missing for this step", 1, 2))
            else:
                sel = _escape_js_string(selector)
                if action == "click":
                    lines.append(_indent(f"await page.click('{sel}');", 1, 2))
                elif action == "check":
                    lines.append(_indent(f"await page.check('{sel}');", 1, 2))
                elif action == "uncheck":
                    lines.append(_indent(f"await page.uncheck('{sel}');", 1, 2))
                elif action == "hover":
                    lines.append(_indent(f"await page.hover('{sel}');", 1, 2))
                elif action == "scroll":
                    lines.append(
                        _indent(
                            f"await page.locator('{sel}').scrollIntoViewIfNeeded();", 1, 2
                        )
                    )

        elif action in ("fill", "type"):
            if not selector or value is None:
                lines.append(_indent("// TODO: selector or value missing for this step", 1, 2))
            else:
                sel = _escape_js_string(selector)
                val = _escape_js_string(str(value))
                lines.append(_indent(f"await page.fill('{sel}', '{val}');", 1, 2))

        elif action == "select":
            if not selector or value is None:
                lines.append(_indent("// TODO: selector or value missing for this step", 1, 2))
            else:
                sel = _escape_js_string(selector)
                val = _escape_js_string(str(value))
                lines.append(_indent(f"await page.selectOption('{sel}', '{val}');", 1, 2))

        elif action == "wait":
            if selector:
                sel = _escape_js_string(selector)
                lines.append(_indent(f"await page.waitForSelector('{sel}');", 1, 2))
            else:
                timeout_ms = 2000
                lines.append(_indent(f"await page.waitForTimeout({timeout_ms});", 1, 2))

        elif action == "assert":
            if selector:
                sel = _escape_js_string(selector)
                if value is not None:
                    expected_text = _escape_js_string(str(value))
                    lines.append(
                        _indent(
                            f"await expect(page.locator('{sel}')).toContainText('{expected_text}');",
                            1,
                            2,
                        )
                    )
                else:
                    lines.append(
                        _indent(
                            f"await expect(page.locator('{sel}')).toBeVisible();", 1, 2
                        )
                    )
            else:
                lines.append(_indent("// TODO: assertion without selector", 1, 2))

        elif action == "screenshot":
            file_name = f"{test_id}_step_{step.get('order', 0)}.png"
            lines.append(
                _indent(f"await page.screenshot({{ path: '{file_name}', fullPage: true }});", 1, 2)
            )

        else:
            lines.append(_indent(f"// TODO: unsupported action '{action}'", 1, 2))

        if expected:
            lines.append(_indent(f"// Expected: {expected}", 1, 2))
        lines.append("")

    lines.append("});")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Selenium Python (pytest-style)
# ---------------------------------------------------------------------------


def _render_selenium_py(name: str, description: str, steps: List[Dict]) -> str:
    func_name = _slugify_name(name)
    lines: List[str] = []

    lines.append("from selenium import webdriver")
    lines.append("from selenium.webdriver.common.by import By")
    lines.append("from selenium.webdriver.support.ui import WebDriverWait")
    lines.append("from selenium.webdriver.support import expected_conditions as EC")
    lines.append("import time")
    lines.append("")
    lines.append("")
    lines.append(f"def test_{func_name}():")
    lines.append(_indent("driver = webdriver.Chrome()", 1, 4))
    lines.append(_indent("wait = WebDriverWait(driver, 10)", 1, 4))
    lines.append(_indent("try:", 1, 4))

    if description:
        lines.append(_indent(f"# {description}", 2, 4))
        lines.append("")

    for step in sorted(steps, key=lambda s: int(s.get("order", 0))):
        action = str(step.get("action") or "wait").lower()
        selector = step.get("selector")
        value = step.get("value")
        step_desc = step.get("description") or f"Step {step.get('order')}"
        expected = step.get("expected_result") or ""

        lines.append(_indent(f"# {step_desc}", 2, 4))

        if action == "navigate":
            url = _escape_py_string(str(value or ""))
            lines.append(_indent(f"driver.get('{url}')", 2, 4))

        elif action in ("click", "check", "uncheck", "hover", "scroll"):
            if not selector:
                lines.append(_indent("# TODO: selector missing for this step", 2, 4))
            else:
                sel = _escape_py_string(selector)
                lines.append(
                    _indent(
                        f"element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '{sel}')))",
                        2,
                        4,
                    )
                )
                if action == "click":
                    lines.append(_indent("element.click()", 2, 4))
                elif action == "hover":
                    lines.append(
                        _indent(
                            "# TODO: Implement hover (e.g., using ActionChains)", 2, 4
                        )
                    )
                elif action == "scroll":
                    lines.append(
                        _indent(
                            "driver.execute_script('arguments[0].scrollIntoView(true);', element)",
                            2,
                            4,
                        )
                    )
                elif action in ("check", "uncheck"):
                    lines.append(
                        _indent(
                            "# TODO: Implement check/uncheck behavior if needed", 2, 4
                        )
                    )

        elif action in ("fill", "type"):
            if not selector or value is None:
                lines.append(_indent("# TODO: selector or value missing for this step", 2, 4))
            else:
                sel = _escape_py_string(selector)
                val = _escape_py_string(str(value))
                lines.append(
                    _indent(
                        f"element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '{sel}')))",
                        2,
                        4,
                    )
                )
                lines.append(_indent("element.clear()", 2, 4))
                lines.append(_indent(f"element.send_keys('{val}')", 2, 4))

        elif action == "select":
            lines.append(
                _indent(
                    "# TODO: Implement select (e.g., using Select from selenium.webdriver.support.ui)",
                    2,
                    4,
                )
            )

        elif action == "wait":
            if selector:
                sel = _escape_py_string(selector)
                lines.append(
                    _indent(
                        f"wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '{sel}')))",
                        2,
                        4,
                    )
                )
            else:
                lines.append(_indent("time.sleep(2)", 2, 4))

        elif action == "assert":
            if selector:
                sel = _escape_py_string(selector)
                if value is not None:
                    expected_text = _escape_py_string(str(value))
                    lines.append(
                        _indent(
                            f"element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '{sel}')))",
                            2,
                            4,
                        )
                    )
                    lines.append(
                        _indent(f"assert '{expected_text}' in element.text", 2, 4)
                    )
                else:
                    lines.append(
                        _indent(
                            f"wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '{sel}')))",
                            2,
                            4,
                        )
                    )
            else:
                lines.append(_indent("# TODO: assertion without selector", 2, 4))

        elif action == "screenshot":
            file_name = f"{func_name}_step_{step.get('order', 0)}.png"
            lines.append(
                _indent(f"driver.save_screenshot('{_escape_py_string(file_name)}')", 2, 4)
            )

        else:
            lines.append(_indent(f"# TODO: unsupported action '{action}'", 2, 4))

        if expected:
            lines.append(_indent(f"# Expected: {expected}", 2, 4))
        lines.append("")

    lines.append(_indent("finally:", 1, 4))
    lines.append(_indent("driver.quit()", 2, 4))
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Cypress JavaScript
# ---------------------------------------------------------------------------


def _render_cypress_js(name: str, description: str, steps: List[Dict]) -> str:
    lines: List[str] = []

    lines.append(f"describe('{_escape_js_string(name)}', () => {{")
    lines.append(_indent("it('runs the generated test case', () => {", 1, 2))
    if description:
        lines.append(_indent(f"// {description}", 2, 2))
        lines.append("")

    for step in sorted(steps, key=lambda s: int(s.get("order", 0))):
        action = str(step.get("action") or "wait").lower()
        selector = step.get("selector")
        value = step.get("value")
        step_desc = step.get("description") or f"Step {step.get('order')}"
        expected = step.get("expected_result") or ""

        lines.append(_indent(f"// {step_desc}", 2, 2))

        if action == "navigate":
            url = _escape_js_string(str(value or ""))
            lines.append(_indent(f"cy.visit('{url}');", 2, 2))

        elif action in ("click", "check", "uncheck", "hover", "scroll"):
            if not selector:
                lines.append(_indent("// TODO: selector missing for this step", 2, 2))
            else:
                sel = _escape_js_string(selector)
                if action == "click":
                    lines.append(_indent(f"cy.get('{sel}').click();", 2, 2))
                elif action == "check":
                    lines.append(_indent(f"cy.get('{sel}').check();", 2, 2))
                elif action == "uncheck":
                    lines.append(_indent(f"cy.get('{sel}').uncheck();", 2, 2))
                elif action == "hover":
                    lines.append(
                        _indent(
                            "cy.get('{sel}').trigger('mouseover');".format(sel=sel), 2, 2
                        )
                    )
                elif action == "scroll":
                    lines.append(_indent(f"cy.get('{sel}').scrollIntoView();", 2, 2))

        elif action in ("fill", "type"):
            if not selector or value is None:
                lines.append(_indent("// TODO: selector or value missing for this step", 2, 2))
            else:
                sel = _escape_js_string(selector)
                val = _escape_js_string(str(value))
                lines.append(_indent(f"cy.get('{sel}').clear().type('{val}');", 2, 2))

        elif action == "select":
            if not selector or value is None:
                lines.append(_indent("// TODO: selector or value missing for this step", 2, 2))
            else:
                sel = _escape_js_string(selector)
                val = _escape_js_string(str(value))
                lines.append(_indent(f"cy.get('{sel}').select('{val}');", 2, 2))

        elif action == "wait":
            if selector:
                sel = _escape_js_string(selector)
                lines.append(_indent(f"cy.get('{sel}').should('be.visible');", 2, 2))
            else:
                lines.append(_indent("cy.wait(2000);", 2, 2))

        elif action == "assert":
            if selector:
                sel = _escape_js_string(selector)
                if value is not None:
                    expected_text = _escape_js_string(str(value))
                    lines.append(
                        _indent(
                            f"cy.get('{sel}').should('contain.text', '{expected_text}');",
                            2,
                            2,
                        )
                    )
                else:
                    lines.append(
                        _indent(
                            f"cy.get('{sel}').should('be.visible');", 2, 2
                        )
                    )
            else:
                lines.append(_indent("// TODO: assertion without selector", 2, 2))

        elif action == "screenshot":
            file_name = f"step_{step.get('order', 0)}"
            lines.append(_indent(f"cy.screenshot('{_escape_js_string(file_name)}');", 2, 2))

        else:
            lines.append(_indent(f"// TODO: unsupported action '{action}'", 2, 2))

        if expected:
            lines.append(_indent(f"// Expected: {expected}", 2, 2))
        lines.append("")

    lines.append(_indent("});", 1, 2))
    lines.append("});")
    return "\n".join(lines).rstrip() + "\n"

