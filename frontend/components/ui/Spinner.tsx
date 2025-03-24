import React from 'react';

export type SpinnerSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';
export type SpinnerVariant = 'circle' | 'dots' | 'pulse';

export interface SpinnerProps {
  /**
   * The size of the spinner
   */
  size?: SpinnerSize;
  /**
   * The visual style of the spinner
   */
  variant?: SpinnerVariant;
  /**
   * Additional CSS classes to apply
   */
  className?: string;
  /**
   * Text to be announced to screen readers
   */
  label?: string;
  /**
   * Determines if the label should be shown visually
   */
  showLabel?: boolean;
  /**
   * Center the spinner in its container
   */
  center?: boolean;
  /**
   * The color of the spinner - will default to the current text color
   */
  color?: string;
}

/**
 * Get the size of the spinner in pixels
 */
const getSpinnerSize = (size: SpinnerSize): string => {
  switch (size) {
    case 'xs':
      return 'h-3 w-3';
    case 'sm':
      return 'h-4 w-4';
    case 'md':
      return 'h-6 w-6';
    case 'lg':
      return 'h-8 w-8';
    case 'xl':
      return 'h-12 w-12';
    default:
      return 'h-6 w-6';
  }
};

/**
 * Circle spinner component
 */
const CircleSpinner: React.FC<SpinnerProps> = ({ size = 'md', className = '', color }) => {
  const sizeClass = getSpinnerSize(size);
  
  return (
    <svg
      className={`animate-spin-pulse ${sizeClass} ${className}`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      style={color ? { color } : undefined}
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
      ></circle>
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      ></path>
    </svg>
  );
};

/**
 * Dots spinner component
 */
const DotsSpinner: React.FC<SpinnerProps> = ({ size = 'md', className = '', color }) => {
  const baseSize = getSpinnerSize(size);
  const dotSize = size === 'xs' ? 'h-1 w-1' : size === 'sm' ? 'h-1.5 w-1.5' : 'h-2 w-2';
  
  return (
    <div className={`flex items-center justify-center space-x-1 ${baseSize} ${className}`}>
      <div className={`${dotSize} rounded-full bg-current animate-bounce [animation-delay:-0.3s]`} style={color ? { backgroundColor: color } : undefined}></div>
      <div className={`${dotSize} rounded-full bg-current animate-bounce [animation-delay:-0.15s]`} style={color ? { backgroundColor: color } : undefined}></div>
      <div className={`${dotSize} rounded-full bg-current animate-bounce`} style={color ? { backgroundColor: color } : undefined}></div>
    </div>
  );
};

/**
 * Pulse spinner component
 */
const PulseSpinner: React.FC<SpinnerProps> = ({ size = 'md', className = '', color }) => {
  const sizeClass = getSpinnerSize(size);
  
  return (
    <div className={`relative ${sizeClass} ${className}`}>
      <div
        className="absolute inset-0 rounded-full bg-current opacity-75 animate-ping"
        style={color ? { backgroundColor: color } : undefined}
      ></div>
      <div
        className="relative rounded-full bg-current opacity-90 h-full w-full"
        style={color ? { backgroundColor: color } : undefined}
      ></div>
    </div>
  );
};

/**
 * Spinner component that displays a loading indicator
 */
export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  variant = 'circle',
  className = '',
  label = 'Loading...',
  showLabel = false,
  center = false,
  color,
}) => {
  // Container classes for centering if needed
  const containerClasses = center ? 'flex flex-col items-center justify-center' : '';
  
  let SpinnerComponent;
  switch (variant) {
    case 'dots':
      SpinnerComponent = <DotsSpinner size={size} className={className} color={color} />;
      break;
    case 'pulse':
      SpinnerComponent = <PulseSpinner size={size} className={className} color={color} />;
      break;
    default:
      SpinnerComponent = <CircleSpinner size={size} className={className} color={color} />;
  }
  
  return (
    <div className={containerClasses} role="status" aria-live="polite">
      {SpinnerComponent}
      
      {/* Visible label if requested */}
      {showLabel && <div className="mt-2 text-sm text-center font-medium text-gray-600 dark:text-gray-300">{label}</div>}
      
      {/* Hidden label for screen readers */}
      {!showLabel && <span className="sr-only">{label}</span>}
    </div>
  );
};

export default Spinner;
