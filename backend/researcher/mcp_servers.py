"""
MCP server configurations for the Alex Researcher
"""
from agents.mcp import MCPServerStdio


def create_playwright_mcp_server(timeout_seconds=60):
    """Create a Playwright MCP server instance for web browsing.
    
    Args:
        timeout_seconds: Client session timeout in seconds (default: 60)
        
    Returns:
        MCPServerStdio instance configured for Playwright
    """
    # Base arguments
    args = [
        "@playwright/mcp@latest",
        "--headless",
        "--isolated", 
        "--no-sandbox",
        "--ignore-https-errors",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ]
    
    # Search for Chrome executable at runtime in Docker environment
    import os
    import glob
    import pathlib
    
    if os.path.exists("/.dockerenv") or os.environ.get("AWS_EXECUTION_ENV"):
        print("DEBUG: Running in containerized environment, searching for Chrome...")
        
        chrome_path = None
        
        # Try multiple search patterns to find Chrome
        search_patterns = [
            "/root/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
            "/root/.cache/ms-playwright/chromium-*/chrome-linux/chrome-headless-shell",
            "/root/.cache/ms-playwright/chromium-*/chrome",
        ]
        
        for pattern in search_patterns:
            chrome_paths = glob.glob(pattern)
            if chrome_paths:
                # Verify the path actually exists and is executable
                for path in chrome_paths:
                    if os.path.exists(path) and os.access(path, os.X_OK):
                        chrome_path = path
                        print(f"DEBUG: Found Chrome via glob: {chrome_path}")
                        break
                if chrome_path:
                    break
        
        # If still not found, try to find any chromium directory
        if not chrome_path:
            playwright_cache = pathlib.Path("/root/.cache/ms-playwright")
            if playwright_cache.exists():
                chromium_dirs = list(playwright_cache.glob("chromium-*"))
                if chromium_dirs:
                    # Try common paths within the chromium directory
                    for chromium_dir in chromium_dirs:
                        possible_paths = [
                            chromium_dir / "chrome-linux" / "chrome",
                            chromium_dir / "chrome-linux" / "chrome-headless-shell",
                            chromium_dir / "chrome",
                        ]
                        for possible_path in possible_paths:
                            if possible_path.exists() and possible_path.is_file() and os.access(possible_path, os.X_OK):
                                chrome_path = str(possible_path)
                                print(f"DEBUG: Found Chrome via directory search: {chrome_path}")
                                break
                        if chrome_path:
                            break
        
        if chrome_path:
            args.extend(["--executable-path", chrome_path])
        else:
            # Let Playwright MCP handle it automatically
            print("DEBUG: Chrome not found via search, Playwright MCP will use its default browser")
    
    params = {
        "command": "npx",
        "args": args
    }
    
    return MCPServerStdio(params=params, client_session_timeout_seconds=timeout_seconds)