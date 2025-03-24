import { ToastType } from '@/components/ui/Toast';

/**
 * Utility functions for displaying notifications
 * This is a thin wrapper around the useNotification hook functions
 * to make it easier to use in components
 */

// Function type for showing a notification
export type ShowNotificationFunction = (
  message: string,
  type?: ToastType,
  duration?: number
) => string | void;

/**
 * Shows a success notification with the given message
 * @param showNotification The showNotification function from the useNotification hook
 * @param message The message to display
 * @param duration The duration to show the notification (default: 5000ms)
 * @returns The ID of the notification
 */
export const showSuccess = (
  showNotification: ShowNotificationFunction,
  message: string, 
  duration?: number
): string | void => {
  return showNotification(message, 'success', duration);
};

/**
 * Shows an error notification with the given message
 * @param showNotification The showNotification function from the useNotification hook
 * @param message The message to display
 * @param duration The duration to show the notification (default: 5000ms)
 * @returns The ID of the notification
 */
export const showError = (
  showNotification: ShowNotificationFunction,
  message: string,
  duration?: number
): string | void => {
  return showNotification(message, 'error', duration);
};

/**
 * Shows an info notification with the given message
 * @param showNotification The showNotification function from the useNotification hook
 * @param message The message to display
 * @param duration The duration to show the notification (default: 5000ms)
 * @returns The ID of the notification
 */
export const showInfo = (
  showNotification: ShowNotificationFunction,
  message: string,
  duration?: number
): string | void => {
  return showNotification(message, 'info', duration);
};

/**
 * Shows a warning notification with the given message
 * @param showNotification The showNotification function from the useNotification hook
 * @param message The message to display
 * @param duration The duration to show the notification (default: 5000ms)
 * @returns The ID of the notification
 */
export const showWarning = (
  showNotification: ShowNotificationFunction,
  message: string,
  duration?: number
): string | void => {
  return showNotification(message, 'warning', duration);
};

/**
 * Error handler for API errors that shows an error notification
 * @param showNotification The showNotification function from the useNotification hook
 * @param error The error object
 * @param defaultMessage The default error message to display if the error doesn't have a message
 */
export const handleApiError = (
  showNotification: ShowNotificationFunction,
  error: any,
  defaultMessage = 'An unexpected error occurred'
): void => {
  let message = defaultMessage;
  
  if (error) {
    if (typeof error === 'string') {
      message = error;
    } else if (error.message) {
      message = error.message;
    } else if (error.error) {
      message = error.error;
    }
  }
  
  showNotification(message, 'error');
};
