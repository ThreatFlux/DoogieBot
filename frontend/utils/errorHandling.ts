import { AxiosError } from 'axios';
import { NotificationType } from '@/contexts/NotificationContext';

/**
 * Error categories for proper handling and user messaging
 */
export enum ErrorCategory {
  NETWORK = 'network',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  VALIDATION = 'validation',
  RESOURCE_NOT_FOUND = 'resource_not_found',
  SERVER = 'server',
  CLIENT = 'client',
  UNKNOWN = 'unknown'
}

/**
 * Structured error interface for consistent handling
 */
export interface AppError {
  message: string;
  detail?: string;
  category: ErrorCategory;
  statusCode?: number;
  source?: string;
  context?: Record<string, any>;
  timestamp: Date;
  originalError?: any;
}

/**
 * Maps HTTP status codes to error categories
 */
const statusToCategoryMap: Record<number, ErrorCategory> = {
  400: ErrorCategory.VALIDATION,
  401: ErrorCategory.AUTHENTICATION,
  403: ErrorCategory.AUTHORIZATION,
  404: ErrorCategory.RESOURCE_NOT_FOUND,
  422: ErrorCategory.VALIDATION,
  500: ErrorCategory.SERVER,
  502: ErrorCategory.SERVER,
  503: ErrorCategory.SERVER,
  504: ErrorCategory.SERVER
};

/**
 * Maps error categories to user-friendly messages
 */
const categoryToMessageMap: Record<ErrorCategory, string> = {
  [ErrorCategory.NETWORK]: 'Network connection issue',
  [ErrorCategory.AUTHENTICATION]: 'Authentication error',
  [ErrorCategory.AUTHORIZATION]: 'You don\'t have permission to perform this action',
  [ErrorCategory.VALIDATION]: 'Please check your input',
  [ErrorCategory.RESOURCE_NOT_FOUND]: 'The requested resource was not found',
  [ErrorCategory.SERVER]: 'The server encountered an error',
  [ErrorCategory.CLIENT]: 'An error occurred in the application',
  [ErrorCategory.UNKNOWN]: 'An unexpected error occurred'
};

/**
 * Maps error categories to notification types
 */
const categoryToNotificationType: Record<ErrorCategory, NotificationType> = {
  [ErrorCategory.NETWORK]: 'error',
  [ErrorCategory.AUTHENTICATION]: 'error',
  [ErrorCategory.AUTHORIZATION]: 'error',
  [ErrorCategory.VALIDATION]: 'warning',
  [ErrorCategory.RESOURCE_NOT_FOUND]: 'warning',
  [ErrorCategory.SERVER]: 'error',
  [ErrorCategory.CLIENT]: 'error',
  [ErrorCategory.UNKNOWN]: 'error'
};

/**
 * Logger levels
 */
export enum LogLevel {
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
  DEBUG = 'debug'
}

/**
 * Function to create a standardized error object from any error source
 */
export const createAppError = (error: any, source?: string, context?: Record<string, any>): AppError => {
  let category = ErrorCategory.UNKNOWN;
  let message = 'An unexpected error occurred';
  let detail = '';
  let statusCode: number | undefined = undefined;

  if (error instanceof Error) {
    message = error.message;
  }

  // Handle Axios errors
  if (error?.isAxiosError) {
    const axiosError = error as AxiosError;
    
    // Network errors
    if (axiosError.code === 'ECONNABORTED' || axiosError.message.includes('timeout') || !axiosError.response) {
      category = ErrorCategory.NETWORK;
      message = 'Network connection issue';
      detail = 'Please check your internet connection and try again';
    } 
    // Server response errors
    else if (axiosError.response) {
      statusCode = axiosError.response.status;
      category = statusToCategoryMap[statusCode] || ErrorCategory.UNKNOWN;
      
      // Extract detailed message from response if available
      const responseData = axiosError.response.data as any;
      
      if (responseData) {
        if (typeof responseData === 'string') {
          detail = responseData;
        } else if (responseData.detail) {
          detail = responseData.detail;
        } else if (responseData.message) {
          detail = responseData.message;
        } else if (responseData.error) {
          detail = responseData.error;
        }
      }
      
      // Special handling for validation errors
      if (category === ErrorCategory.VALIDATION && responseData?.errors) {
        const validationErrors = responseData.errors;
        if (Array.isArray(validationErrors)) {
          detail = validationErrors.join(', ');
        } else if (typeof validationErrors === 'object') {
          detail = Object.entries(validationErrors)
            .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
            .join('; ');
        }
      }
    }
  }

  message = message || categoryToMessageMap[category];

  return {
    message,
    detail,
    category,
    statusCode,
    source: source || 'application',
    context,
    timestamp: new Date(),
    originalError: error
  };
};

/**
 * Log an error with appropriate level and context
 */
export const logError = (
  error: AppError, 
  level: LogLevel = LogLevel.ERROR,
  additionalContext?: Record<string, any>
): void => {
  const logData = {
    message: error.message,
    detail: error.detail,
    category: error.category,
    statusCode: error.statusCode,
    source: error.source,
    timestamp: error.timestamp.toISOString(),
    context: { ...error.context, ...additionalContext }
  };

  switch (level) {
    case LogLevel.INFO:
      console.info(`[${error.source}] ${error.message}`, logData);
      break;
    case LogLevel.WARN:
      console.warn(`[${error.source}] ${error.message}`, logData);
      break;
    case LogLevel.DEBUG:
      console.debug(`[${error.source}] ${error.message}`, logData);
      break;
    case LogLevel.ERROR:
    default:
      console.error(`[${error.source}] ${error.message}`, logData);
      if (error.originalError) {
        console.error('Original error:', error.originalError);
      }
  }

  // Here you could also send the error to your monitoring service
  // e.g., Sentry, LogRocket, etc.
};

/**
 * Get appropriate notification type for an error
 */
export const getNotificationTypeForError = (error: AppError): NotificationType => {
  return categoryToNotificationType[error.category] || 'error';
};

/**
 * Get user-friendly message for an error
 */
export const getUserFriendlyMessage = (error: AppError): string => {
  // For auth errors, provide more specific guidance
  if (error.category === ErrorCategory.AUTHENTICATION) {
    return 'Your session has expired. Please sign in again.';
  }
  
  // For validation errors, use the detail if available
  if (error.category === ErrorCategory.VALIDATION && error.detail) {
    return error.detail;
  }
  
  // For 404 errors
  if (error.category === ErrorCategory.RESOURCE_NOT_FOUND) {
    return `${error.detail || 'The requested resource was not found'}`;
  }

  // For network errors, provide more helpful information
  if (error.category === ErrorCategory.NETWORK) {
    return 'Unable to connect to the server. Please check your internet connection and try again.';
  }
  
  // For server errors
  if (error.category === ErrorCategory.SERVER) {
    return 'The server encountered an unexpected error. Please try again later.';
  }
  
  // Return the message from the error, or a default message from the category
  return error.message || categoryToMessageMap[error.category];
};

/**
 * Function to handle errors consistently across the application
 * This can be used by components to display errors to users
 */
export const handleError = (
  error: any,
  source?: string,
  context?: Record<string, any>,
  showNotificationFn?: (message: string, type: NotificationType) => void
): AppError => {
  const appError = createAppError(error, source, context);
  
  // Log the error
  logError(appError);
  
  // Show notification if the function is provided
  if (showNotificationFn) {
    const notificationType = getNotificationTypeForError(appError);
    const userMessage = getUserFriendlyMessage(appError);
    showNotificationFn(userMessage, notificationType);
  }
  
  return appError;
};

/**
 * Check if an error is related to authentication/session
 */
export const isAuthError = (error: AppError): boolean => {
  return error.category === ErrorCategory.AUTHENTICATION;
};

/**
 * Special handling for authentication errors (redirect to login)
 */
export const handleAuthError = (error: AppError): void => {
  if (isAuthError(error)) {
    // Clear tokens and redirect to login
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }
};

/**
 * Custom error class for application-specific errors
 */
export class ApplicationError extends Error {
  category: ErrorCategory;
  detail?: string;
  statusCode?: number;
  context?: Record<string, any>;

  constructor(
    message: string,
    category: ErrorCategory = ErrorCategory.CLIENT,
    detail?: string,
    statusCode?: number,
    context?: Record<string, any>
  ) {
    super(message);
    this.name = 'ApplicationError';
    this.category = category;
    this.detail = detail;
    this.statusCode = statusCode;
    this.context = context;
  }
}
