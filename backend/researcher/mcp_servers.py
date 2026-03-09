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

        try:
            # Try multiple search patterns to find Chrome
            search_patterns = [
                "/root/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
                "/root/.cache/ms-playwright/chromium-*/chrome-linux/chrome-headless-shell",
                "/root/.cache/ms-playwright/chromium-*/chrome",
            ]

            for pattern in search_patterns:
                try:
                    chrome_paths = glob.glob(pattern)
                except PermissionError:
                    # In restricted environments (like Lambda), we may not be able to read this path.
                    print(f"DEBUG: Permission denied while globbing pattern: {pattern}")
                    continue

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
                try:
                    cache_exists = playwright_cache.exists()
                except PermissionError:
                    print("DEBUG: Permission denied accessing Playwright cache directory; skipping cache search")
                    cache_exists = False

                if cache_exists:
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
                                try:
                                    if possible_path.exists() and possible_path.is_file() and os.access(possible_path, os.X_OK):
                                        chrome_path = str(possible_path)
                                        print(f"DEBUG: Found Chrome via directory search: {chrome_path}")
                                        break
                                except PermissionError:
                                    # Skip paths we can't stat
                                    continue
                            if chrome_path:
                                break
        except Exception as e:
            # Never fail agent creation just because Chrome detection failed
            print(f"DEBUG: Error while searching for Chrome executable: {e}")

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