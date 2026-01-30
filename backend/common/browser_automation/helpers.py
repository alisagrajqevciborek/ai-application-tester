"""
Helper functions for additional test checks.
"""
import logging
from typing import List, Dict
from playwright.async_api import Page
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


async def check_broken_links(page: Page, url: str, issues: List[Dict]) -> None:
    """Scan page for broken internal links."""
    logger.info(f"Checking for broken links on {url}")
    
    links = await page.evaluate('''() => {
        const anchors = Array.from(document.querySelectorAll('a[href]'));
        return anchors.map(a => ({
            href: a.href,
            text: (a.innerText || a.textContent || '').trim().substring(0, 50)
        })).filter(link => 
            link.href.startsWith('http') && 
            !link.href.includes('mailto:') && 
            !link.href.includes('tel:')
        );
    }''')
    
    base_domain = urlparse(url).netloc
    internal_links = [l for l in links if urlparse(l['href']).netloc == base_domain][:20]
    
    for link in internal_links:
        try:
            response = await page.context.request.get(link['href'], timeout=5000)
            if response.status >= 400:
                issues.append({
                    'severity': 'major',
                    'title': 'Broken Link Found',
                    'description': f"Link to '{link['href']}' with text '{link['text']}' returned status {response.status}.",
                    'location': url,
                    'type': 'broken_link'
                })
            await response.dispose()
        except Exception as e:
            logger.debug(f"Failed to check link {link['href']}: {e}")


async def test_authentication(page: Page, url: str, issues: List[Dict], credentials: Dict) -> None:
    """Test login or signup functionality."""
    login_url = credentials.get('login_url')
    username = credentials.get('username')
    password = credentials.get('password')
    
    if not login_url or not username or not password:
        return
    
    logger.info(f"Testing authentication at {login_url}")
    
    try:
        await page.goto(login_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(3000)  # Wait for JS to execute instead of networkidle
        
        user_selectors = ['input[type="email"]', 'input[name="email"]', 'input[name="username"]', 'input[id="username"]', 'input[id="email"]']
        pass_selectors = ['input[type="password"]', 'input[name="password"]', 'input[id="password"]']
        submit_selectors = ['button[type="submit"]', 'input[type="submit"]', 'button:has-text("Login")', 'button:has-text("Sign in")']
        
        user_field = None
        for s in user_selectors:
            try:
                if await page.is_visible(s):
                    user_field = s
                    break
            except:
                continue
        
        pass_field = None
        for s in pass_selectors:
            try:
                if await page.is_visible(s):
                    pass_field = s
                    break
            except:
                continue
        
        if user_field and pass_field:
            await page.fill(user_field, username)
            await page.fill(pass_field, password)
            
            submit_btn = None
            for s in submit_selectors:
                try:
                    if await page.is_visible(s):
                        submit_btn = s
                        break
                except:
                    continue
            
            if submit_btn:
                await page.click(submit_btn)
                await page.wait_for_timeout(3000)
                
                error_indicators = [':has-text("Invalid")', ':has-text("failed")', '.error', '.alert-danger']
                found_error = False
                for s in error_indicators:
                    try:
                        if await page.is_visible(s):
                            found_error = True
                            break
                    except:
                        continue
                
                if found_error:
                    issues.append({
                        'severity': 'major',
                        'title': 'Authentication Failure',
                        'description': "Login attempt failed. Error message detected on the page.",
                        'location': login_url,
                        'type': 'auth_failure'
                    })
            else:
                issues.append({
                    'severity': 'minor',
                    'title': 'Authentication Test Incomplete',
                    'description': "Could not find a login submit button on the page.",
                    'location': login_url,
                    'type': 'auth_warning'
                })
        else:
            issues.append({
                'severity': 'minor',
                'title': 'Authentication Test Incomplete',
                'description': "Could not identify username or password fields on the login page.",
                'location': login_url,
                'type': 'auth_warning'
            })
    except Exception as e:
        logger.error(f"Error during authentication test: {e}")
        issues.append({
            'severity': 'minor',
            'title': 'Authentication Test Error',
            'description': f"An error occurred during authentication testing: {str(e)[:100]}",
            'location': login_url,
            'type': 'auth_error'
        })
