"""
Selenium WebDriver setup and configuration for Doogie Chat Bot UI testing.
This module provides the necessary setup functions for browser instances and testing environment.
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.safari.options import Options as SafariOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# Default settings
DEFAULT_BROWSER = os.environ.get('SELENIUM_BROWSER', 'chrome')
DEFAULT_HEADLESS = os.environ.get('SELENIUM_HEADLESS', 'true').lower() == 'true'
DEFAULT_BASE_URL = os.environ.get('SELENIUM_BASE_URL', 'http://localhost:3000')
DEFAULT_WAIT_TIME = int(os.environ.get('SELENIUM_WAIT_TIME', '10'))
DEFAULT_WINDOW_WIDTH = int(os.environ.get('SELENIUM_WINDOW_WIDTH', '1366'))
DEFAULT_WINDOW_HEIGHT = int(os.environ.get('SELENIUM_WINDOW_HEIGHT', '768'))


def create_chrome_driver(headless=DEFAULT_HEADLESS):
    """Create and configure a Chrome WebDriver instance."""
    options = ChromeOptions()
    
    if headless:
        options.add_argument('--headless')
    
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument(f'--window-size={DEFAULT_WINDOW_WIDTH},{DEFAULT_WINDOW_HEIGHT}')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-notifications')
    options.add_argument('--ignore-certificate-errors')
    
    # For Docker container compatibility
    if os.environ.get('SELENIUM_DOCKER', 'false').lower() == 'true':
        options.add_argument('--remote-debugging-port=9222')
    
    # Performance settings
    options.page_load_strategy = 'normal'  # 'normal', 'eager', or 'none'
    
    # Improved logging
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    
    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def create_firefox_driver(headless=DEFAULT_HEADLESS):
    """Create and configure a Firefox WebDriver instance."""
    options = FirefoxOptions()
    
    if headless:
        options.add_argument('--headless')
    
    options.add_argument(f'--width={DEFAULT_WINDOW_WIDTH}')
    options.add_argument(f'--height={DEFAULT_WINDOW_HEIGHT}')
    options.set_preference('dom.disable_open_during_load', True)
    options.set_preference('app.update.auto', False)
    
    # Performance settings
    options.page_load_strategy = 'normal'
    
    service = FirefoxService(GeckoDriverManager().install())
    return webdriver.Firefox(service=service, options=options)


def create_edge_driver(headless=DEFAULT_HEADLESS):
    """Create and configure an Edge WebDriver instance."""
    options = EdgeOptions()
    
    if headless:
        options.add_argument('--headless')
        
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--window-size={DEFAULT_WINDOW_WIDTH},{DEFAULT_WINDOW_HEIGHT}')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-notifications')
    
    # Performance settings
    options.page_load_strategy = 'normal'
    
    service = EdgeService(EdgeChromiumDriverManager().install())
    return webdriver.Edge(service=service, options=options)


def create_safari_driver():
    """Create and configure a Safari WebDriver instance."""
    options = SafariOptions()
    driver = webdriver.Safari(options=options)
    driver.set_window_size(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
    return driver


def create_driver(browser=DEFAULT_BROWSER, headless=DEFAULT_HEADLESS):
    """
    Create a WebDriver instance for the specified browser.
    
    Args:
        browser (str): The browser to use ('chrome', 'firefox', 'edge', or 'safari')
        headless (bool): Whether to run in headless mode (ignored for Safari)
        
    Returns:
        WebDriver: A configured WebDriver instance
    """
    browser = browser.lower()
    
    if browser == 'chrome':
        return create_chrome_driver(headless)
    elif browser == 'firefox':
        return create_firefox_driver(headless)
    elif browser == 'edge':
        return create_edge_driver(headless)
    elif browser == 'safari':
        # Safari doesn't support headless mode
        return create_safari_driver()
    else:
        raise ValueError(f"Unsupported browser: {browser}")


def wait_for_page_load(driver, timeout=DEFAULT_WAIT_TIME):
    """
    Wait for the page to be fully loaded.
    
    Args:
        driver (WebDriver): The WebDriver instance
        timeout (int): Maximum time to wait in seconds
    """
    start_time = time.time()
    
    # Wait for the page to be in a ready state
    while time.time() - start_time < timeout:
        ready_state = driver.execute_script("return document.readyState")
        if ready_state == "complete":
            return True
        time.sleep(0.1)
    
    raise TimeoutError(f"Page did not load completely within {timeout} seconds")


def wait_for_element(driver, by, value, timeout=DEFAULT_WAIT_TIME, visible=True):
    """
    Wait for an element to be present and optionally visible.
    
    Args:
        driver (WebDriver): The WebDriver instance
        by: The locator strategy (e.g., By.ID, By.CSS_SELECTOR)
        value: The locator value
        timeout (int): Maximum time to wait in seconds
        visible (bool): Whether to wait for visibility as well
        
    Returns:
        WebElement: The found element
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    condition = EC.visibility_of_element_located if visible else EC.presence_of_element_located
    return WebDriverWait(driver, timeout).until(condition((by, value)))


def wait_for_url_contains(driver, substring, timeout=DEFAULT_WAIT_TIME):
    """
    Wait for the URL to contain a specific substring.
    
    Args:
        driver (WebDriver): The WebDriver instance
        substring (str): The substring to look for in the URL
        timeout (int): Maximum time to wait in seconds
        
    Returns:
        bool: True if the condition is met within the timeout
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    return WebDriverWait(driver, timeout).until(EC.url_contains(substring))


def capture_screenshot(driver, filename):
    """
    Capture a screenshot and save it to the specified file.
    
    Args:
        driver (WebDriver): The WebDriver instance
        filename (str): The file path where to save the screenshot
    """
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    driver.save_screenshot(filename)


def get_console_logs(driver):
    """
    Get the browser console logs (Chrome only).
    
    Args:
        driver (WebDriver): The WebDriver instance
        
    Returns:
        list: The console log entries
    """
    if driver.name.lower() != 'chrome':
        return "Console logs are only available in Chrome"
    
    return driver.get_log('browser')


def get_performance_metrics(driver):
    """
    Get performance metrics (Chrome only).
    
    Args:
        driver (WebDriver): The WebDriver instance
        
    Returns:
        dict: Performance metrics
    """
    if driver.name.lower() != 'chrome':
        return {"error": "Performance metrics are only available in Chrome"}
    
    try:
        # Performance metrics from Chrome DevTools Protocol
        metrics = driver.execute_script("""
            return window.performance.timing.toJSON();
        """)
        
        # Calculate some derived metrics
        metrics['pageLoadTime'] = metrics['loadEventEnd'] - metrics['navigationStart']
        metrics['domContentLoadedTime'] = metrics['domContentLoadedEventEnd'] - metrics['navigationStart']
        metrics['firstPaintTime'] = metrics['responseEnd'] - metrics['navigationStart']
        
        return metrics
    except Exception as e:
        return {"error": str(e)}
