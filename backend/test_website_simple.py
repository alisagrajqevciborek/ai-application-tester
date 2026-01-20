"""
Standalone simple test script (no Django required).
Usage: python test_website_simple.py <url> [test_type]
"""
import asyncio
import sys
from common.browser_automation import BrowserAutomationService


async def test_website_async(url: str, test_type: str = "functional"):
    """Test a website asynchronously."""
    service = BrowserAutomationService()
    return await service.run_test(url, test_type)


def test_website(url: str, test_type: str = "functional") -> int:
    """
    Test a website and display results.
    
    Args:
        url: The website URL to test
        test_type: Type of test (functional, regression, performance, accessibility)
    """
    print("=" * 60)
    print(f"Testing Website: {url}")
    print(f"Test Type: {test_type}")
    print("=" * 60)
    print()
    
    print("Running tests...")
    print("-" * 60)
    
    try:
        # Run the test
        service = BrowserAutomationService()
        results = asyncio.run(service.run_test(url, test_type))
        
        # Display results
        print()
        print("=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print()
        
        # Status
        status = results['status']
        status_symbol = "[PASS]" if status == "success" else "[FAIL]"
        
        print(f"Status: {status_symbol} {status.upper()}")
        print(f"Pass Rate: {results['pass_rate']}%")
        print(f"Fail Rate: {results['fail_rate']}%")
        print()
        
        # Issues
        issues = results['issues']
        if issues:
            print(f"Issues Found: {len(issues)}")
            print("-" * 60)
            for i, issue in enumerate(issues, 1):
                severity = issue['severity'].upper()
                print(f"{i}. [{severity}] {issue['title']}")
                print(f"   {issue['description']}")
                if 'location' in issue:
                    print(f"   Location: {issue['location']}")
                print()
        else:
            print("No issues found!")
            print()
        
        # Screenshots
        screenshots = results['screenshots']
        if screenshots:
            print(f"Screenshots: {len(screenshots)} captured")
            for screenshot in screenshots:
                print(f"  - {screenshot}")
            print()
        
        # Final verdict
        print("=" * 60)
        if status == "success":
            print("[SUCCESS] Website PASSED the tests!")
        else:
            print("[FAILURE] Website FAILED the tests!")
        print("=" * 60)
        
        # Return exit code
        return 0 if status == "success" else 1
        
    except Exception as e:
        print()
        print("=" * 60)
        print("[ERROR] Test execution failed!")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_website_simple.py <url> [test_type]")
        print()
        print("Examples:")
        print("  python test_website_simple.py https://example.com")
        print("  python test_website_simple.py https://example.com functional")
        print("  python test_website_simple.py https://example.com performance")
        print()
        print("Test types: functional, regression, performance, accessibility")
        sys.exit(1)
    
    url = sys.argv[1]
    test_type = sys.argv[2] if len(sys.argv) > 2 else "functional"
    
    # Validate URL
    if not url.startswith(('http://', 'https://')):
        print(f"Error: URL must start with http:// or https://")
        print(f"Received: {url}")
        sys.exit(1)
    
    # Validate test type
    valid_types = ['functional', 'regression', 'performance', 'accessibility']
    if test_type not in valid_types:
        print(f"Error: Invalid test type '{test_type}'")
        print(f"Valid types: {', '.join(valid_types)}")
        sys.exit(1)
    
    # Run the test
    exit_code = test_website(url, test_type)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

