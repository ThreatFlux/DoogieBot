import React, { useEffect, useState, useRef, AriaAttributes } from 'react';
import { createPortal } from 'react-dom';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastProps extends Pick<AriaAttributes, 'aria-live' | 'aria-relevant'> {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
  onClose: (id: string) => void;
  /**
   * Optional title for the toast message
   */
  title?: string;
  /**
   * Whether the toast can be dismissed by clicking outside
   */
  dismissOnClickOutside?: boolean;
}

const Toast: React.FC<ToastProps> = ({
  id,
  message,
  type = 'info',
  duration = 5000,
  onClose,
  title,
  dismissOnClickOutside = true,
  'aria-live': ariaLive = 'polite',
  'aria-relevant': ariaRelevant = 'additions text'
}) => {
  const [visible, setVisible] = useState(true);
  const [progress, setProgress] = useState(100);
  const [mounted, setMounted] = useState(false);
  const toastRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  
  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);
  
  // Get toast priority for screen readers based on type
  const getAriaLive = () => {
    // Override with prop value if provided
    if (ariaLive) return ariaLive;
    
    // Default values based on type
    switch (type) {
      case 'error':
        return 'assertive'; // High priority
      default:
        return 'polite'; // Normal priority
    }
  };
  
  // Get appropriate role based on type
  const getRole = () => {
    switch (type) {
      case 'error':
        return 'alert';
      case 'warning':
        return 'status';
      default:
        return 'status';
    }
  };
  
  // For accessibility: add keyboard support
  useEffect(() => {
    if (visible && toastRef.current) {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          setVisible(false);
        }
      };
      
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [visible]);
  
  useEffect(() => {
    if (duration === 0) return;
    
    // Start animation
    const startTime = Date.now();
    const endTime = startTime + duration;
    
    const updateProgress = () => {
      const now = Date.now();
      if (now >= endTime) {
        setVisible(false);
        return;
      }
      
      const remaining = endTime - now;
      const newProgress = (remaining / duration) * 100;
      setProgress(newProgress);
      requestAnimationFrame(updateProgress);
    };
    
    const animationFrame = requestAnimationFrame(updateProgress);
    
    // Set timer to auto-dismiss
    const timer = setTimeout(() => {
      setVisible(false);
    }, duration);
    
    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(animationFrame);
    };
  }, [duration]);
  
  // Handle animation end
  useEffect(() => {
    if (!visible) {
      // Give time for exit animation
      const timer = setTimeout(() => {
        onClose(id);
      }, 300); // Match animation duration
      
      return () => clearTimeout(timer);
    }
  }, [visible, onClose, id]);
  
  const getTypeStyles = (): { bgColor: string; iconColor: string; icon: JSX.Element } => {
    switch (type) {
      case 'success':
        return {
          bgColor: 'bg-green-50 dark:bg-green-900/20 border-l-4 border-l-green-500',
          iconColor: 'text-green-500',
          icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )
        };
      case 'error':
        return {
          bgColor: 'bg-red-50 dark:bg-red-900/20 border-l-4 border-l-red-500',
          iconColor: 'text-red-500',
          icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )
        };
      case 'warning':
        return {
          bgColor: 'bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-l-yellow-500',
          iconColor: 'text-yellow-500',
          icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          )
        };
      default:
        return {
          bgColor: 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-l-blue-500',
          iconColor: 'text-blue-500',
          icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )
        };
    }
  };
  
  const { bgColor, iconColor, icon } = getTypeStyles();
  
  // If not mounted (during SSR), don't render
  if (!mounted) return null;
  
  return createPortal(
    <div
      className={`fixed z-50 transition-all duration-300 ease-in-out ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
      style={{
        right: '1rem',
        top: '1rem',
        maxWidth: 'calc(100% - 2rem)'
      }}
      ref={toastRef}
      role={getRole()}
      aria-live={getAriaLive()}
      aria-relevant={ariaRelevant}
      aria-atomic="true"
      onClick={dismissOnClickOutside ? () => setVisible(false) : undefined}
    >
      <div className={`${bgColor} shadow-lg rounded-md p-4 mb-4 flex items-start`}>
        <div className={`flex-shrink-0 ${iconColor} mr-3`}>
          {icon}
        </div>
        <div className="flex-grow">
          {title && (
            <h3 className="text-sm font-medium text-gray-800 dark:text-gray-200">
              {title}
            </h3>
          )}
          <p className="text-gray-800 dark:text-gray-200 font-medium">{message}</p>
        </div>
        <button
          ref={closeButtonRef}
          onClick={(e) => {
            e.stopPropagation(); // Prevent triggering the toast's onClick
            setVisible(false);
          }}
          className="ml-4 flex-shrink-0 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
          aria-label="Close notification"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
      {duration > 0 && (
        <div className="h-1 rounded-full bg-gray-200 dark:bg-gray-700 w-full overflow-hidden -mt-4 mb-4" role="progressbar" aria-hidden="true">
          <div
            className={`h-full ${
              type === 'success'
                ? 'bg-green-500'
                : type === 'error'
                ? 'bg-red-500'
                : type === 'warning'
                ? 'bg-yellow-500'
                : 'bg-blue-500'
            } transition-all duration-100 ease-linear`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>,
    document.body
  );
};

export default Toast;
