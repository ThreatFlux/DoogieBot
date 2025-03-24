import { ONBOARDING_STORAGE_KEY } from '@/contexts/OnboardingContext';

/**
 * Utility functions for managing onboarding experience
 */

/**
 * Check if the user has completed the onboarding tour
 * @returns boolean indicating if onboarding has been completed
 */
export const hasCompletedOnboarding = (): boolean => {
  // Don't attempt to access localStorage during SSR
  if (typeof window === 'undefined') return false;
  
  return localStorage.getItem(ONBOARDING_STORAGE_KEY) === 'true';
};

/**
 * Mark onboarding as completed
 */
export const completeOnboarding = (): void => {
  // Don't attempt to access localStorage during SSR
  if (typeof window === 'undefined') return;
  
  localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true');
};

/**
 * Reset onboarding status (useful for testing or when user wants to see the tour again)
 */
export const resetOnboarding = (): void => {
  // Don't attempt to access localStorage during SSR
  if (typeof window === 'undefined') return;
  
  localStorage.removeItem(ONBOARDING_STORAGE_KEY);
};

/**
 * Prepares HTML elements for onboarding 
 * This function adds/updates the necessary IDs to elements that will be highlighted during onboarding
 * Call this function once the component is mounted to ensure elements have proper IDs
 */
export const prepareElementsForOnboarding = (): void => {
  // Don't attempt to access DOM during SSR
  if (typeof window === 'undefined') return;
  
  // Ensure we add IDs to elements that should be targeted during onboarding
  // These IDs must match those used in the OnboardingContext
  
  // New chat button
  const newChatButton = document.querySelector('.sidebar-header button');
  if (newChatButton && !newChatButton.id) {
    newChatButton.id = 'new-chat-button';
  }
  
  // Chat sidebar
  const chatSidebar = document.querySelector('.sidebar-container');
  if (chatSidebar && !chatSidebar.id) {
    chatSidebar.id = 'chat-sidebar';
  }
  
  // Search input
  const searchInput = document.querySelector('.sidebar-header input[type="search"]');
  if (searchInput && !searchInput.id) {
    searchInput.id = 'search-chats';
  }
  
  // Chat input
  const chatInput = document.querySelector('.chat-input textarea, .chat-input input');
  if (chatInput && !chatInput.id) {
    chatInput.id = 'chat-input';
  }
  
  // User menu
  const userMenu = document.querySelector('.user-menu-button, .profile-button');
  if (userMenu && !userMenu.id) {
    userMenu.id = 'user-menu';
  }
};

/**
 * Check if a user should see onboarding tour based on various factors
 * @param isFirstTimeUser Boolean indicating if the user is new to the app
 * @returns Boolean indicating if onboarding should be shown
 */
export const shouldShowOnboarding = (isFirstTimeUser: boolean): boolean => {
  // Don't attempt to access localStorage during SSR
  if (typeof window === 'undefined') return false;
  
  // Already completed onboarding
  if (hasCompletedOnboarding()) return false;
  
  // Always show for first-time users
  if (isFirstTimeUser) return true;
  
  // Could add additional logic here, like:
  // - Show again after major app updates
  // - Show for users who've only used the app a few times
  
  return false;
};

/**
 * Ensure elements have appropriate ARIA attributes for accessibility
 * @param isOnboardingActive Boolean indicating if onboarding is currently active
 */
export const updateAriaForOnboarding = (isOnboardingActive: boolean): void => {
  // Don't attempt to access DOM during SSR
  if (typeof window === 'undefined') return;
  
  // Add aria-describedby attributes to elements being highlighted
  const onboardingElements = [
    'new-chat-button',
    'chat-sidebar',
    'search-chats',
    'chat-input',
    'user-menu'
  ];
  
  onboardingElements.forEach(id => {
    const element = document.getElementById(id);
    if (element) {
      if (isOnboardingActive) {
        element.setAttribute('aria-describedby', 'onboarding-tooltip');
      } else {
        element.removeAttribute('aria-describedby');
      }
    }
  });
};
