import React from 'react';
import Spinner from './Spinner';
import { LoadingContext, DEFAULT_LOADING_CONFIGS } from '@/utils/loadingUtils';

export interface LoadingOverlayProps {
  /**
   * Whether the loading overlay is visible
   */
  isLoading: boolean;
  /**
   * Optional custom message to display
   */
  message?: string;
  /**
   * Whether to block user interaction with underlying content
   */
  blockInteraction?: boolean;
  /**
   * Whether to show backdrop/overlay or just the spinner
   */
  showBackdrop?: boolean;
  /**
   * The spinner variant to use
   */
  spinnerVariant?: 'circle' | 'dots' | 'pulse';
  /**
   * The size of the spinner
   */
  spinnerSize?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /**
   * Whether to fade in/out the overlay
   */
  animate?: boolean;
  /**
   * The z-index of the overlay
   */
  zIndex?: number;
  /**
   * The loading context, which determines default behavior
   */
  context?: LoadingContext;
  /**
   * Additional CSS class names
   */
  className?: string;
  /**
   * Target element for relative positioning, defaults to 'relative'
   */
  position?: 'fixed' | 'absolute' | 'relative';
  /**
   * Whether to cover the full viewport
   */
  fullScreen?: boolean;
}

/**
 * A versatile loading overlay component that can be configured for different contexts
 */
export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isLoading,
  message,
  blockInteraction,
  showBackdrop = true,
  spinnerVariant,
  spinnerSize = 'md',
  animate = true,
  zIndex = 50,
  context = 'page',
  className = '',
  position = 'relative',
  fullScreen = false,
}) => {
  // Get default config based on context
  const defaultConfig = DEFAULT_LOADING_CONFIGS[context];
  
  // Determine final values, with explicit props taking precedence over context defaults
  const finalMessage = message ?? defaultConfig.message;
  const finalBlockInteraction = blockInteraction ?? defaultConfig.blockInteraction;
  const finalSpinnerVariant = spinnerVariant ?? defaultConfig.spinnerType ?? 'circle';
  const finalShowBackdrop = showBackdrop ?? defaultConfig.overlay;
  
  // If not loading, don't render anything
  if (!isLoading) {
    return null;
  }

  // Build class list
  const classes = [
    position,
    position === 'fixed' || fullScreen ? 'inset-0' : 'inset-0',
    'flex items-center justify-center',
    finalBlockInteraction ? 'pointer-events-auto' : 'pointer-events-none',
    animate ? 'transition-opacity duration-200' : '',
    isLoading ? 'opacity-100' : 'opacity-0',
    className,
  ].join(' ');

  // Backdrop classes
  const backdropClasses = [
    'absolute inset-0',
    finalShowBackdrop ? 'bg-gray-900/50 dark:bg-gray-900/70' : 'bg-transparent',
    finalBlockInteraction ? 'cursor-not-allowed' : '',
  ].join(' ');

  // Content classes
  const contentClasses = [
    'flex flex-col items-center justify-center p-4 rounded-lg',
    finalShowBackdrop ? 'bg-white dark:bg-gray-800 shadow-lg' : '',
    'text-center',
  ].join(' ');

  return (
    <div 
      className={classes} 
      style={{ zIndex }}
      role="status"
      aria-live="polite"
      aria-busy={isLoading}
    >
      {/* Semi-transparent backdrop */}
      <div className={backdropClasses} />
      
      {/* Loading indicator and message */}
      <div className={contentClasses}>
        <Spinner 
          variant={finalSpinnerVariant}
          size={spinnerSize}
          label={finalMessage || 'Loading...'}
          showLabel={!!finalMessage}
        />
        
        {/* If no visible label, include for screen readers */}
        {!finalMessage && (
          <span className="sr-only">Loading, please wait...</span>
        )}
      </div>
    </div>
  );
};

/**
 * Full-screen loading overlay variant
 */
export const FullScreenLoading: React.FC<Omit<LoadingOverlayProps, 'position' | 'fullScreen'>> = (props) => (
  <LoadingOverlay {...props} position="fixed" fullScreen />
);

/**
 * Loading overlay specifically for forms
 */
export const FormLoadingOverlay: React.FC<Omit<LoadingOverlayProps, 'context'>> = (props) => (
  <LoadingOverlay {...props} context="form" />
);

/**
 * Loading overlay for modals and dialogs
 */
export const ModalLoadingOverlay: React.FC<Omit<LoadingOverlayProps, 'context'>> = (props) => (
  <LoadingOverlay {...props} context="modal" position="absolute" />
);

/**
 * Inline loading indicator without backdrop
 */
export const InlineLoading: React.FC<{
  isLoading: boolean;
  message?: string;
  spinnerSize?: 'xs' | 'sm' | 'md';
  className?: string;
}> = ({ isLoading, message, spinnerSize = 'sm', className = '' }) => {
  if (!isLoading) return null;
  
  return (
    <div className={`inline-flex items-center space-x-2 ${className}`}>
      <Spinner 
        variant="circle" 
        size={spinnerSize} 
        label={message || 'Loading...'}
        showLabel={!!message}
      />
      {message && (
        <span className="text-sm text-gray-600 dark:text-gray-300">{message}</span>
      )}
    </div>
  );
};

export default LoadingOverlay;
