/**
 * Utility function to get an accessible color based on background color
 * Ensures proper contrast for text on different backgrounds
 * @param backgroundColor - Background color in hex format (e.g. #FFFFFF)
 * @param lightColor - Color to use on dark backgrounds (default: white)
 * @param darkColor - Color to use on light backgrounds (default: black)
 * @param contrastThreshold - Minimum contrast ratio required (default: 4.5:1 for WCAG AA)
 * @returns The appropriate text color to use
 */
export const getAccessibleTextColor = (
  backgroundColor: string,
  {
    lightColor = '#FFFFFF',
    darkColor = '#000000',
    contrastThreshold = 4.5
  } = {}
): string => {
  // Default to dark text if unable to compute
  if (!backgroundColor || backgroundColor === 'transparent') {
    return darkColor;
  }
  
  // Calculate contrast ratio with each option
  const lightRatio = getContrastRatio(backgroundColor, lightColor);
  const darkRatio = getContrastRatio(backgroundColor, darkColor);
  
  // Find the highest contrast ratio
  const highestContrast = Math.max(lightRatio, darkRatio);
  
  // Return the color with the highest contrast
  // If neither meets threshold, return the better one with a warning to console
  if (highestContrast < contrastThreshold) {
    console.warn(
      `Warning: Neither text color option (${lightColor}, ${darkColor}) meets the minimum contrast ratio of ${contrastThreshold}:1 against ${backgroundColor}. Using best available option.`
    );
  }
  
  return lightRatio > darkRatio ? lightColor : darkColor;
};

/**
 * Helper function to darken or lighten a color to meet contrast requirements
 * @param color - Base color in hex format
 * @param targetColor - Color to contrast with
 * @param targetRatio - Target contrast ratio to achieve
 * @param isDarken - Whether to darken or lighten the color
 * @returns Adjusted color with improved contrast
 */
export const adjustColorForContrast = (
  color: string,
  targetColor: string,
  targetRatio = 4.5,
  isDarken = true
): string => {
  if (!color || !targetColor) return color;
  
  // Convert hex to rgb
  const hexToRgb = (hex: string): { r: number; g: number; b: number } => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
      ? {
          r: parseInt(result[1], 16),
          g: parseInt(result[2], 16),
          b: parseInt(result[3], 16),
        }
      : { r: 0, g: 0, b: 0 };
  };
  
  // Convert rgb to hex
  const rgbToHex = (r: number, g: number, b: number): string => {
    return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
  };
  
  const rgb = hexToRgb(color);
  let ratio = getContrastRatio(color, targetColor);
  let attempts = 0;
  const maxAttempts = 20; // Prevent infinite loops
  
  // Keep adjusting until we reach the target contrast ratio or max attempts
  while (ratio < targetRatio && attempts < maxAttempts) {
    if (isDarken) {
      // Darken the color
      rgb.r = Math.max(0, rgb.r - 10);
      rgb.g = Math.max(0, rgb.g - 10);
      rgb.b = Math.max(0, rgb.b - 10);
    } else {
      // Lighten the color
      rgb.r = Math.min(255, rgb.r + 10);
      rgb.g = Math.min(255, rgb.g + 10);
      rgb.b = Math.min(255, rgb.b + 10);
    }
    
    const newColor = rgbToHex(rgb.r, rgb.g, rgb.b);
    ratio = getContrastRatio(newColor, targetColor);
    attempts++;
    
    // If we've reached the target, return the new color
    if (ratio >= targetRatio) {
      return newColor;
    }
  }
  
  // Return the best we could get
  return rgbToHex(rgb.r, rgb.g, rgb.b);
};/**
 * Accessibility utilities for improving screen reader support, keyboard navigation,
 * and overall accessibility throughout the application.
 */

/**
 * Hide content visually but keep it accessible to screen readers
 * Use this class for "Skip to content" links or other elements that should
 * be available to screen readers but not visually displayed by default
 */
export const srOnly = 'sr-only';

/**
 * Make content visible when focused, used with srOnly to reveal content when tabbed to
 */
export const srOnlyFocusable = 'sr-only-focusable';

/**
 * Interface for standardized announcement options
 */
export interface AnnouncementOptions {
  message: string;
  politeness?: 'assertive' | 'polite';
  timeout?: number;
}

/**
 * Map of common ARIA landmarks that can be used to improve navigation
 */
export const ariaLandmarks = {
  banner: 'banner',       // Site header
  navigation: 'navigation', // Navigation menu
  main: 'main',           // Main content area
  complementary: 'complementary', // Supporting content (sidebars)
  contentinfo: 'contentinfo', // Site footer
  search: 'search',       // Search functionality
  form: 'form'            // Important forms
};

/**
 * Announcement function for screen readers
 * Creates a visually hidden element that announces content to screen readers
 * @param options - The announcement options
 */
export const announce = (options: AnnouncementOptions): void => {
  const { message, politeness = 'polite', timeout = 1000 } = options;
  
  if (typeof document === 'undefined') return;

  // Create or use existing live region
  let liveRegion = document.getElementById(`aria-live-${politeness}`);
  
  if (!liveRegion) {
    liveRegion = document.createElement('div');
    liveRegion.id = `aria-live-${politeness}`;
    liveRegion.setAttribute('aria-live', politeness);
    liveRegion.setAttribute('role', 'status');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = srOnly;
    document.body.appendChild(liveRegion);
  }
  
  // Clear previous announcements
  liveRegion.textContent = '';
  
  // Ensure the DOM has updated
  setTimeout(() => {
    liveRegion!.textContent = message;
    
    // Clear announcement after specified timeout
    if (timeout > 0) {
      setTimeout(() => {
        liveRegion!.textContent = '';
      }, timeout);
    }
  }, 100);
};

/**
 * Focus trap utility for modals, dialogs, and other components
 * that need to trap focus within them when open
 */
export class FocusTrap {
  private element: HTMLElement;
  private focusableElements: HTMLElement[] = [];
  private previouslyFocused: HTMLElement | null = null;
  
  constructor(element: HTMLElement) {
    this.element = element;
    this.updateFocusableElements();
  }
  
  /**
   * Update the list of focusable elements within the trap
   */
  public updateFocusableElements(): void {
    const selector = [
      'a[href]:not([tabindex="-1"])',
      'button:not([disabled]):not([tabindex="-1"])',
      'textarea:not([disabled]):not([tabindex="-1"])',
      'input:not([disabled]):not([tabindex="-1"])',
      'select:not([disabled]):not([tabindex="-1"])',
      '[tabindex]:not([tabindex="-1"])'
    ].join(',');
    
    this.focusableElements = Array.from(
      this.element.querySelectorAll<HTMLElement>(selector)
    );
  }
  
  /**
   * Activate the focus trap
   */
  public activate(): void {
    // Save currently focused element
    this.previouslyFocused = document.activeElement as HTMLElement;
    
    // Focus the first focusable element in the trap
    if (this.focusableElements.length > 0) {
      this.focusableElements[0].focus();
    } else {
      // If no focusable elements, focus the container itself
      this.element.setAttribute('tabindex', '-1');
      this.element.focus();
    }
    
    // Add event listeners
    this.element.addEventListener('keydown', this.handleKeyDown);
  }
  
  /**
   * Deactivate the focus trap
   */
  public deactivate(): void {
    // Remove event listeners
    this.element.removeEventListener('keydown', this.handleKeyDown);
    
    // Restore focus to previously focused element
    if (this.previouslyFocused && 'focus' in this.previouslyFocused) {
      this.previouslyFocused.focus();
    }
  }
  
  /**
   * Handle keydown events to trap focus
   */
  private handleKeyDown = (event: KeyboardEvent): void => {
    if (event.key !== 'Tab') return;
    
    // If there are no focusable elements, do nothing
    if (this.focusableElements.length === 0) return;
    
    const firstFocusableElement = this.focusableElements[0];
    const lastFocusableElement = this.focusableElements[this.focusableElements.length - 1];
    
    // If Shift+Tab on first element, wrap to last element
    if (event.shiftKey && document.activeElement === firstFocusableElement) {
      event.preventDefault();
      lastFocusableElement.focus();
    } 
    // If Tab on last element, wrap to first element
    else if (!event.shiftKey && document.activeElement === lastFocusableElement) {
      event.preventDefault();
      firstFocusableElement.focus();
    }
  };
}

/**
 * Check if an element is visible and focusable
 * @param element - Element to check
 */
export const isElementFocusable = (element: HTMLElement): boolean => {
  if (!element) return false;
  
  // Check if element is visible
  const style = window.getComputedStyle(element);
  if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
    return false;
  }
  
  // Check if element is focusable
  const tabindex = element.getAttribute('tabindex');
  if (tabindex && parseInt(tabindex, 10) < 0) {
    return false;
  }
  
  // Check if element is disabled
  if (element.hasAttribute('disabled')) {
    return false;
  }
  
  return true;
};

/**
 * Calculate contrast ratio between two colors
 * @param color1 - Color 1 in hex format (#RRGGBB)
 * @param color2 - Color 2 in hex format (#RRGGBB)
 * @returns The contrast ratio
 */
export const getContrastRatio = (color1: string, color2: string): number => {
  // Convert hex to rgb
  const hexToRgb = (hex: string): { r: number; g: number; b: number } => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
      ? {
          r: parseInt(result[1], 16),
          g: parseInt(result[2], 16),
          b: parseInt(result[3], 16),
        }
      : { r: 0, g: 0, b: 0 };
  };

  // Calculate luminance from RGB
  const getLuminance = (rgb: { r: number; g: number; b: number }): number => {
    const a = [rgb.r, rgb.g, rgb.b].map(v => {
      v /= 255;
      return v <= 0.03928
        ? v / 12.92
        : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
  };

  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);
  const l1 = getLuminance(rgb1);
  const l2 = getLuminance(rgb2);
  
  // Calculate contrast ratio
  const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  
  return parseFloat(ratio.toFixed(2));
};

/**
 * Check if a contrast ratio is accessible
 * WCAG 2.0 requires 4.5:1 for normal text, 3:1 for large text
 * @param ratio - Contrast ratio to check
 * @param isLargeText - Whether the text is large (>=18pt or >=14pt bold)
 * @returns Whether the contrast ratio is accessible
 */
export const isAccessibleContrast = (
  ratio: number,
  isLargeText: boolean = false
): boolean => {
  return isLargeText ? ratio >= 3 : ratio >= 4.5;
};

/**
 * Add a skip link to the page
 * @param containerId - ID of the main content container to skip to
 */
export const addSkipToContentLink = (containerId: string = 'main-content'): void => {
  if (typeof document === 'undefined') return;
  
  // Check if skip link already exists
  if (document.getElementById('skip-to-content')) return;
  
  const skipLink = document.createElement('a');
  skipLink.id = 'skip-to-content';
  skipLink.href = `#${containerId}`;
  skipLink.className = `${srOnly} ${srOnlyFocusable}`;
  skipLink.textContent = 'Skip to main content';
  
  // Insert as first element in body
  document.body.insertBefore(skipLink, document.body.firstChild);
};
