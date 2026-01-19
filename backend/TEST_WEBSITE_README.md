# Simple Website Testing Script

Quick and easy way to test if a website passes automated tests.

## Usage

### Basic Usage (Functional Test)
```powershell
cd backend
.\.venv\Scripts\python.exe test_website.py https://example.com
```

### With Test Type
```powershell
.\.venv\Scripts\python.exe test_website.py https://example.com functional
.\.venv\Scripts\python.exe test_website.py https://example.com regression
.\.venv\Scripts\python.exe test_website.py https://example.com performance
.\.venv\Scripts\python.exe test_website.py https://example.com accessibility
```

## Test Types

- **functional** - Tests basic page functionality (title, content, links)
- **regression** - Tests for broken functionality (JS errors, broken images)
- **performance** - Tests page load time and performance metrics
- **accessibility** - Tests WCAG compliance (alt text, headings, etc.)

## Output

The script will display:
- ✅ **PASS** or ❌ **FAIL** status
- Pass rate percentage
- Fail rate percentage
- List of issues found (if any)
- Screenshot locations (if any)

## Examples

### Test a simple website
```powershell
.\.venv\Scripts\python.exe test_website.py https://example.com
```

### Test performance
```powershell
.\.venv\Scripts\python.exe test_website.py https://google.com performance
```

### Test accessibility
```powershell
.\.venv\Scripts\python.exe test_website.py https://github.com accessibility
```

## Exit Codes

- `0` - Test passed
- `1` - Test failed or error occurred

This makes it easy to use in scripts or CI/CD pipelines.

## Standalone Version

For testing without Django setup, use `test_website_simple.py`:

```powershell
.\.venv\Scripts\python.exe test_website_simple.py https://example.com
```

