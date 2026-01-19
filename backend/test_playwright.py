"""
Quick test script to verify Playwright is installed and working.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_playwright_import():
    """Test if Playwright can be imported."""
    print("1. Testing Playwright import...")
    try:
        from playwright.async_api import async_playwright  # type: ignore[import-untyped]
        print("   [OK] Playwright imported successfully")
        return True
    except ImportError as e:
        print(f"   [FAIL] Failed to import Playwright: {e}")
        return False

async def test_playwright_browser():
    """Test if Playwright can launch a browser."""
    print("2. Testing browser launch...")
    try:
        from playwright.async_api import async_playwright  # type: ignore[import-untyped]
        
        async with async_playwright() as p:
            print("   [OK] Playwright context created")
            
            browser = await p.chromium.launch(headless=True)
            print("   [OK] Chromium browser launched")
            
            context = await browser.new_context()
            print("   [OK] Browser context created")
            
            page = await context.new_page()
            print("   [OK] New page created")
            
            # Navigate to a simple page
            await page.goto("https://example.com", timeout=10000)
            print("   [OK] Navigated to https://example.com")
            
            # Get page title
            title = await page.title()
            print(f"   [OK] Page title: {title}")
            
            await browser.close()
            print("   [OK] Browser closed successfully")
            
        return True
    except Exception as e:
        print(f"   [FAIL] Browser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_browser_automation_service():
    """Test if the browser automation service can be imported."""
    print("3. Testing browser automation service...")
    try:
        from common.browser_automation import BrowserAutomationService, run_test_sync
        print("   [OK] Browser automation service imported")
        
        service = BrowserAutomationService()
        print("   [OK] Service instance created")
        return True
    except ImportError as e:
        print(f"   [FAIL] Failed to import browser automation: {e}")
        return False
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False

async def test_full_automation():
    """Test the full automation workflow."""
    print("4. Testing full automation workflow...")
    try:
        from common.browser_automation import BrowserAutomationService  # type: ignore[import]
        
        service = BrowserAutomationService()
        print("   Running functional test on https://example.com...")
        
        results = await service.run_test(
            url="https://example.com",
            test_type="functional",
            screenshots_dir=None
        )
        
        print(f"   [OK] Test completed!")
        print(f"   Status: {results['status']}")
        print(f"   Pass Rate: {results['pass_rate']}%")
        print(f"   Fail Rate: {results['fail_rate']}%")
        print(f"   Issues Found: {len(results['issues'])}")
        print(f"   Screenshots: {len(results['screenshots'])}")
        
        if results['issues']:
            print("\n   Issues:")
            for issue in results['issues'][:3]:  # Show first 3
                print(f"     - {issue['severity'].upper()}: {issue['title']}")
        
        return True
    except Exception as e:
        print(f"   [FAIL] Automation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("Playwright Verification Test")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: Import
    results.append(("Import", test_playwright_import()))
    
    if not results[-1][1]:
        print("\n[FAIL] Cannot continue - Playwright not installed")
        return
    
    # Test 2: Browser launch
    results.append(("Browser Launch", await test_playwright_browser()))
    
    # Test 3: Service import
    results.append(("Service Import", test_browser_automation_service()))
    
    # Test 4: Full automation (only if service exists)
    if results[-1][1]:
        results.append(("Full Automation", await test_full_automation()))
    
    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print()
    if all_passed:
        print("[SUCCESS] All tests passed! Playwright is working correctly.")
    else:
        print("[ERROR] Some tests failed. Check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

