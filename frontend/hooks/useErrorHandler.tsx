import { useCallback } from 'react';
import { useNotification } from '@/contexts/NotificationContext';
import { 
  handleError, 
  AppError, 
  ErrorCategory, 
  NotificationType
} from '@/utils/errorHandling';

interface ErrorHandlerHook {
  /**
   * Handle an error with proper logging and user notification
   */
  handleError: (error: any, source?: string, context?: Record<string, any>) => AppError;
  
  /**
   * Create an async error handler that can be used with try/catch blocks
   */
  createAsyncErrorHandler: <T>(
    asyncFn: () => Promise<T>, 
    source?: string, 
    context?: Record<string, any>
  ) => Promise<T | undefined>;
  
  /**
   * Show a specific error message to the user
   */
  showErrorMessage: (message: string, detail?: string, category?: ErrorCategory) => void;
  
  /**
   * Create an error boundary fallback component
   */
  createErrorBoundaryFallback: (error: Error, resetErrorBoundary: () => void) => React.ReactNode;
}

/**
 * Custom hook for consistent error handling throughout the application
 * 
 * This hook connects the error handling utility with the notification system
 * to provide a clean API for components to handle errors.
 */
export const useErrorHandler = (): ErrorHandlerHook => {
  const { showNotification } = useNotification();
  
  const handleErrorWithNotification = useCallback(
    (error: any, source?: string, context?: Record<string, any>): AppError => {
      return handleError(error, source, context, showNotification);
    },
    [showNotification]
  );
  
  const showErrorMessage = useCallback(
    (message: string, detail?: string, category: ErrorCategory = ErrorCategory.CLIENT): void => {
      const notificationType: NotificationType = category === ErrorCategory.VALIDATION 
        ? 'warning' 
        : 'error';
      
      showNotification(
        detail ? `${message}: ${detail}` : message,
        notificationType
      );
    },
    [showNotification]
  );
  
  const createAsyncErrorHandler = useCallback(
    async <T,>(
      asyncFn: () => Promise<T>, 
      source?: string, 
      context?: Record<string, any>
    ): Promise<T | undefined> => {
      try {
        return await asyncFn();
      } catch (error) {
        handleErrorWithNotification(error, source, context);
        return undefined;
      }
    },
    [handleErrorWithNotification]
  );
  
  const createErrorBoundaryFallback = useCallback(
    (error: Error, resetErrorBoundary: () => void): React.ReactNode => {
      // This is a simple example, you might want to expand this
      // or use a dedicated component based on your UI requirements
      const appError = handleError(error, 'ErrorBoundary');
      
      return (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md m-4">
          <h2 className="text-lg font-semibold text-red-700 dark:text-red-400 mb-2">
            {appError.message}
          </h2>
          {appError.detail && (
            <p className="text-red-600 dark:text-red-300 text-sm mb-3">
              {appError.detail}
            </p>
          )}
          <button
            className="px-3 py-1 bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-300 rounded text-sm hover:bg-red-200 dark:hover:bg-red-700"
            onClick={resetErrorBoundary}
            aria-label="Try again"
          >
            Try again
          </button>
        </div>
      );
    },
    []
  );
  
  return {
    handleError: handleErrorWithNotification,
    createAsyncErrorHandler,
    showErrorMessage,
    createErrorBoundaryFallback
  };
};

export default useErrorHandler;
