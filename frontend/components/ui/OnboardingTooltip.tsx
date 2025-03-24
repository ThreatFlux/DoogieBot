import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

export interface OnboardingTooltipProps {
  targetId: string;
  title: string;
  content: string;
  step: number;
  totalSteps: number;
  position?: 'top' | 'right' | 'bottom' | 'left';
  isOpen: boolean;
  onClose: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onSkip: () => void;
}

const OnboardingTooltip: React.FC<OnboardingTooltipProps> = ({
  targetId,
  title,
  content,
  step,
  totalSteps,
  position = 'bottom',
  isOpen,
  onClose,
  onNext,
  onPrevious,
  onSkip
}) => {
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const [arrowPosition, setArrowPosition] = useState({ top: 0, left: 0 });
  const [mounted, setMounted] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);
  
  // Mount safely for SSR
  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);
  
  // Position the tooltip relative to the target element
  useEffect(() => {
    if (!isOpen || !mounted) return;
    
    const calculatePosition = () => {
      const targetElement = document.getElementById(targetId);
      if (!targetElement || !tooltipRef.current) return;
      
      const targetRect = targetElement.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();
      
      const spacing = 12; // Space between target and tooltip
      
      let newTop = 0;
      let newLeft = 0;
      let arrowTop = 0;
      let arrowLeft = 0;
      
      switch (position) {
        case 'top':
          newTop = targetRect.top - tooltipRect.height - spacing;
          newLeft = targetRect.left + targetRect.width / 2 - tooltipRect.width / 2;
          arrowTop = tooltipRect.height;
          arrowLeft = tooltipRect.width / 2 - 8; // 8px is half of arrow width
          break;
        case 'right':
          newTop = targetRect.top + targetRect.height / 2 - tooltipRect.height / 2;
          newLeft = targetRect.right + spacing;
          arrowTop = tooltipRect.height / 2 - 8;
          arrowLeft = -8;
          break;
        case 'bottom':
          newTop = targetRect.bottom + spacing;
          newLeft = targetRect.left + targetRect.width / 2 - tooltipRect.width / 2;
          arrowTop = -8;
          arrowLeft = tooltipRect.width / 2 - 8;
          break;
        case 'left':
          newTop = targetRect.top + targetRect.height / 2 - tooltipRect.height / 2;
          newLeft = targetRect.left - tooltipRect.width - spacing;
          arrowTop = tooltipRect.height / 2 - 8;
          arrowLeft = tooltipRect.width;
          break;
      }
      
      // Adjust position to keep tooltip within viewport
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      
      if (newLeft < 20) newLeft = 20;
      if (newLeft + tooltipRect.width > viewportWidth - 20) {
        newLeft = viewportWidth - tooltipRect.width - 20;
      }
      
      if (newTop < 20) newTop = 20;
      if (newTop + tooltipRect.height > viewportHeight - 20) {
        newTop = viewportHeight - tooltipRect.height - 20;
      }
      
      // Highlight the target element with a subtle animation
      targetElement.style.position = 'relative';
      targetElement.style.zIndex = '1000';
      targetElement.style.transition = 'box-shadow 0.3s ease';
      targetElement.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.5)';
      
      setTooltipPosition({ top: newTop, left: newLeft });
      setArrowPosition({ top: arrowTop, left: arrowLeft });
    };
    
    calculatePosition();
    
    // Recalculate on resize
    window.addEventListener('resize', calculatePosition);
    return () => {
      window.removeEventListener('resize', calculatePosition);
      
      // Remove highlighting from target element
      const targetElement = document.getElementById(targetId);
      if (targetElement) {
        targetElement.style.boxShadow = '';
        targetElement.style.zIndex = '';
      }
    };
  }, [isOpen, targetId, position, mounted]);
  
  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen) return;
    
    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowRight':
        case 'Enter':
          onNext();
          break;
        case 'ArrowLeft':
          onPrevious();
          break;
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, onNext, onPrevious]);
  
  if (!mounted || !isOpen) return null;
  
  // Add a subtle overlay to focus attention on the tooltip
  const renderOverlay = () => {
    return (
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
        aria-hidden="true"
      />
    );
  };
  
  // Determine arrow classes based on position
  const getArrowClasses = () => {
    switch (position) {
      case 'top': return 'border-t-blue-500 border-l-transparent border-r-transparent bottom-[-8px]';
      case 'right': return 'border-r-blue-500 border-t-transparent border-b-transparent left-[-8px]';
      case 'bottom': return 'border-b-blue-500 border-l-transparent border-r-transparent top-[-8px]';
      case 'left': return 'border-l-blue-500 border-t-transparent border-b-transparent right-[-8px]';
    }
  };
  
  return createPortal(
    <>
      {renderOverlay()}
      <div
        ref={tooltipRef}
        className="fixed z-50 max-w-xs rounded-lg shadow-lg bg-white dark:bg-gray-800 border border-blue-500 p-4"
        style={{
          top: tooltipPosition.top,
          left: tooltipPosition.left,
        }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
      >
        {/* Arrow */}
        <div
          className={`absolute w-0 h-0 border-8 ${getArrowClasses()}`}
          style={{
            top: arrowPosition.top,
            left: arrowPosition.left,
          }}
        />
        
        {/* Header with step indicator */}
        <div className="flex items-center justify-between mb-2">
          <h3 id="onboarding-title" className="text-lg font-semibold text-gray-900 dark:text-white">
            {title}
          </h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {step} of {totalSteps}
          </span>
        </div>
        
        {/* Content */}
        <div className="text-sm text-gray-700 dark:text-gray-300 mb-4">
          {content}
        </div>
        
        {/* Navigation buttons */}
        <div className="flex justify-between items-center">
          <div>
            <button
              className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              onClick={onSkip}
              aria-label="Skip tour"
            >
              Skip tour
            </button>
          </div>
          <div className="flex space-x-2">
            {step > 1 && (
              <button
                className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                onClick={onPrevious}
                aria-label="Previous step"
              >
                Previous
              </button>
            )}
            <button
              className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              onClick={step < totalSteps ? onNext : onClose}
              aria-label={step < totalSteps ? "Next step" : "Finish tour"}
            >
              {step < totalSteps ? 'Next' : 'Finish'}
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body
  );
};

export default OnboardingTooltip;
