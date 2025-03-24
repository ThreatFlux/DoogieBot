/**
 * Utilities for managing loading states throughout the application
 */

/**
 * Loading state types - represents different contexts
 * where loading states might be needed
 */
export type LoadingContext =
  | 'button'
  | 'page'
  | 'card'
  | 'form'
  | 'list'
  | 'modal'
  | 'chat'
  | 'file-upload'
  | 'search'
  | 'auth'
  | 'api';

/**
 * Loading state configuration for different contexts
 */
export interface LoadingConfig {
  /**
   * Minimum loading time in milliseconds
   */
  minTime?: number;
  /**
   * Message to display during loading
   */
  message?: string;
  /**
   * Whether to display a loading overlay
   */
  overlay?: boolean;
  /**
   * Type of spinner to use
   */
  spinnerType?: 'circle' | 'dots' | 'pulse';
  /**
   * Whether to block user interaction during loading
   */
  blockInteraction?: boolean;
}

/**
 * Default loading configurations for different contexts
 */
export const DEFAULT_LOADING_CONFIGS: Record<LoadingContext, LoadingConfig> = {
  button: {
    minTime: 500,
    message: 'Processing...',
    overlay: false,
    spinnerType: 'circle',
    blockInteraction: true,
  },
  page: {
    minTime: 300,
    message: 'Loading content...',
    overlay: true,
    spinnerType: 'circle',
    blockInteraction: false,
  },
  card: {
    minTime: 300,
    message: 'Loading...',
    overlay: false,
    spinnerType: 'circle',
    blockInteraction: false,
  },
  form: {
    minTime: 500,
    message: 'Submitting...',
    overlay: false,
    spinnerType: 'circle',
    blockInteraction: true,
  },
  list: {
    minTime: 400,
    message: 'Loading items...',
    overlay: false,
    spinnerType: 'dots',
    blockInteraction: false,
  },
  modal: {
    minTime: 300,
    message: 'Loading...',
    overlay: true,
    spinnerType: 'circle',
    blockInteraction: true,
  },
  chat: {
    minTime: 0, // Don't delay chat messages
    message: 'Thinking...',
    overlay: false,
    spinnerType: 'dots',
    blockInteraction: false,
  },
  'file-upload': {
    minTime: 0, // Don't delay file uploads
    message: 'Uploading...',
    overlay: false,
    spinnerType: 'circle',
    blockInteraction: true,
  },
  search: {
    minTime: 300,
    message: 'Searching...',
    overlay: false,
    spinnerType: 'dots',
    blockInteraction: false,
  },
  auth: {
    minTime: 500,
    message: 'Authenticating...',
    overlay: true,
    spinnerType: 'circle',
    blockInteraction: true,
  },
  api: {
    minTime: 0,
    message: 'Loading data...',
    overlay: false,
    spinnerType: 'circle',
    blockInteraction: false,
  },
};

/**
 * Hook for tracking loading state with a minimum duration
 * @param initialState - Initial loading state
 * @param config - Loading configuration
 * @returns Loading state and setter function
 */
export const useLoadingWithMinDuration = (
  initialState: boolean = false,
  config: Partial<LoadingConfig> = {}
): [boolean, (state: boolean) => void] => {
  const [isLoading, setIsLoadingState] = React.useState(initialState);
  const [timerId, setTimerId] = React.useState<number | null>(null);
  const startTimeRef = React.useRef<number>(0);
  
  // Combine with default config
  const mergedConfig: LoadingConfig = {
    minTime: config.minTime ?? DEFAULT_LOADING_CONFIGS.button.minTime,
    message: config.message,
    overlay: config.overlay,
    spinnerType: config.spinnerType,
    blockInteraction: config.blockInteraction,
  };

  /**
   * Set loading state with minimum duration
   */
  const setIsLoading = React.useCallback((state: boolean) => {
    if (state === isLoading) return;
    
    // Clear any existing timer
    if (timerId !== null) {
      window.clearTimeout(timerId);
      setTimerId(null);
    }
    
    if (state) {
      // Start loading
      startTimeRef.current = Date.now();
      setIsLoadingState(true);
    } else {
      // Calculate remaining time to satisfy minimum duration
      const elapsedTime = Date.now() - startTimeRef.current;
      const remainingTime = Math.max(0, (mergedConfig.minTime || 0) - elapsedTime);
      
      if (remainingTime === 0) {
        // End loading immediately
        setIsLoadingState(false);
      } else {
        // Set a timer to end loading after the remaining time
        const id = window.setTimeout(() => {
          setIsLoadingState(false);
          setTimerId(null);
        }, remainingTime);
        setTimerId(Number(id));
      }
    }
  }, [isLoading, timerId, mergedConfig.minTime]);

  /**
   * Clean up timer on unmount
   */
  React.useEffect(() => {
    return () => {
      if (timerId !== null) {
        window.clearTimeout(timerId);
      }
    };
  }, [timerId]);

  return [isLoading, setIsLoading];
};

/**
 * Calculate loading stage message for multi-stage loading
 * @param stage - Current stage number
 * @param totalStages - Total number of stages
 * @param stageMessages - Custom messages for each stage
 * @returns Loading stage message
 */
export const getLoadingStageMessage = (
  stage: number,
  totalStages: number,
  stageMessages: Record<number, string> = {}
): string => {
  // Default messages if not provided
  const defaultMessages: Record<number, string> = {
    1: 'Preparing data...',
    2: 'Processing...',
    3: 'Almost there...',
  };

  // Use custom message if available, otherwise fallback to default or generic
  const message = stageMessages[stage] || defaultMessages[stage] || `Step ${stage} of ${totalStages}`;
  
  return message;
};

/**
 * Get loading state text based on context
 * @param context - Loading context
 * @param customMessage - Optional custom message
 * @returns Loading message
 */
export const getLoadingMessage = (
  context: LoadingContext,
  customMessage?: string
): string => {
  return customMessage || DEFAULT_LOADING_CONFIGS[context].message || 'Loading...';
};

/**
 * Determine if skeleton loading is appropriate based on context and load time
 * @param context - Loading context 
 * @param estimatedLoadTime - Estimated load time in milliseconds
 * @returns Whether to use skeleton loading
 */
export const shouldUseSkeletonLoading = (
  context: LoadingContext,
  estimatedLoadTime: number = 0
): boolean => {
  // For these contexts, always prefer skeleton loading for better UX
  const preferSkeletonContexts: LoadingContext[] = ['page', 'card', 'list'];
  
  // Always use skeleton for longer loading operations
  if (estimatedLoadTime > 500) {
    return true;
  }
  
  // Use skeleton for specific contexts
  if (preferSkeletonContexts.includes(context)) {
    return true;
  }
  
  return false;
};

// Import React at runtime to avoid circular dependencies
import React from 'react';
