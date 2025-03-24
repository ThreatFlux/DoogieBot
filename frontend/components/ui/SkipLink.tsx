import React from 'react';
import { srOnly, srOnlyFocusable } from '@/utils/accessibilityUtils';

export interface SkipLinkProps {
  /**
   * ID of the element to skip to
   */
  target: string;
  /**
   * Text to display when focused
   */
  label?: string;
  /**
   * Additional CSS classes
   */
  className?: string;
  /**
   * Position when focused
   */
  position?: 'top-left' | 'top-center' | 'top-right';
  /**
   * Z-index when focused (default: 9999)
   */
  zIndex?: number;
}

/**
 * SkipLink component for keyboard accessibility
 * Allows keyboard users to bypass navigation menus
 */
const SkipLink: React.FC<SkipLinkProps> = ({
  target,
  label = 'Skip to main content',
  className = '',
  position = 'top-left',
  zIndex = 9999
}) => {
  // Get position classes based on position prop
  const getPositionClasses = () => {
    switch (position) {
      case 'top-center':
        return 'top-4 left-1/2 transform -translate-x-1/2';
      case 'top-right':
        return 'top-4 right-4';
      case 'top-left':
      default:
        return 'top-4 left-4';
    }
  };

  // Handle click to focus the target element
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const targetElement = document.getElementById(target);
    if (targetElement) {
      // Set tabindex to make it focusable if it isn't already
      if (!targetElement.hasAttribute('tabindex')) {
        targetElement.setAttribute('tabindex', '-1');
      }
      
      // Focus and scroll to the element
      targetElement.focus();
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <a
      href={`#${target}`}
      // Use standard sr-only class with sr-only-focusable
      className={`${srOnly} ${srOnlyFocusable} ${getPositionClasses()} ${className}`}
      style={{ 
        zIndex, 
        backgroundColor: 'var(--color-primary-600, #4F46E5)',
      }}
      onClick={handleClick}
      onKeyDown={(e) => {
        // Handle enter key
        if (e.key === 'Enter') {
          handleClick(e as unknown as React.MouseEvent<HTMLAnchorElement>);
        }
      }}
    >
      {label}
    </a>
  );
};

export default SkipLink;