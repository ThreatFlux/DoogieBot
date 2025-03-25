import { useState, useEffect } from 'react';

// Key used for localStorage
const SIDEBAR_PINNED_KEY = 'sidebar_pinned';
const SIDEBAR_VISIBLE_KEY = 'sidebar_visible';

/**
 * Hook to manage sidebar settings like pinning and visibility state
 * This hook handles persistence of these settings across page navigation and sessions
 * 
 * @param defaultIsPinned - Default value for pinned state (if nothing is in localStorage)
 * @param defaultIsVisible - Default value for visibility state (if nothing is in localStorage)
 * @returns Object containing state and setters for sidebar settings
 */
export function useSidebarSettings(
  defaultIsPinned = false,
  defaultIsVisible = false
) {
  // Initialize state from localStorage or use defaults
  const [isPinned, setIsPinned] = useState<boolean>(() => {
    // Only run in client-side
    if (typeof window !== 'undefined') {
      const storedValue = localStorage.getItem(SIDEBAR_PINNED_KEY);
      return storedValue ? JSON.parse(storedValue) : defaultIsPinned;
    }
    return defaultIsPinned;
  });

  const [isVisible, setIsVisible] = useState<boolean>(() => {
    // Only run in client-side
    if (typeof window !== 'undefined') {
      const storedValue = localStorage.getItem(SIDEBAR_VISIBLE_KEY);
      return storedValue ? JSON.parse(storedValue) : defaultIsVisible;
    }
    return defaultIsVisible;
  });

  // Update localStorage when state changes
  useEffect(() => {
    localStorage.setItem(SIDEBAR_PINNED_KEY, JSON.stringify(isPinned));
  }, [isPinned]);

  useEffect(() => {
    localStorage.setItem(SIDEBAR_VISIBLE_KEY, JSON.stringify(isVisible));
  }, [isVisible]);

  // Toggle functions
  const togglePinned = () => setIsPinned(prev => !prev);
  const toggleVisibility = () => setIsVisible(prev => !prev);

  return {
    isPinned,
    isVisible,
    setIsPinned,
    setIsVisible,
    togglePinned,
    toggleVisibility,
  };
}

export default useSidebarSettings;
