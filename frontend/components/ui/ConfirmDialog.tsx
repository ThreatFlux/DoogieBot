import React, { useEffect, useRef } from 'react';
import { Button } from './Button';
import { FocusTrap } from '@/utils/accessibilityUtils';

export interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmText?: string; // Alternative for confirmLabel
  cancelText?: string; // Alternative for cancelLabel
  confirmButtonClass?: string;
  cancelButtonClass?: string;
  variant?: 'danger' | 'warning' | 'info' | 'success';
  /**
   * Unique ID for the dialog element
   */
  id?: string;
  /**
   * Initial focus element selector when dialog opens
   */
  initialFocusSelector?: string;
}

// Helper function to get button class based on variant
const getConfirmButtonClass = (variant: 'danger' | 'warning' | 'info' | 'success'): string => {
  switch (variant) {
    case 'danger':
      return 'bg-red-500 hover:bg-red-600 text-white';
    case 'warning':
      return 'bg-yellow-500 hover:bg-yellow-600 text-white';
    case 'info':
      return 'bg-blue-500 hover:bg-blue-600 text-white';
    case 'success':
      return 'bg-green-500 hover:bg-green-600 text-white';
    default:
      return 'bg-primary-500 hover:bg-primary-600 text-white';
  }
};

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel,
  cancelLabel,
  confirmText,
  cancelText,
  confirmButtonClass,
  cancelButtonClass = '',
  variant = 'danger',
  id,
  initialFocusSelector
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelBtnRef = useRef<HTMLButtonElement>(null);
  const confirmBtnRef = useRef<HTMLButtonElement>(null);
  const focusTrapRef = useRef<FocusTrap | null>(null);
  
  // Generate a unique ID for the dialog if not provided
  const dialogId = id || `confirm-dialog-${Math.random().toString(36).substring(2, 9)}`;
  const titleId = `${dialogId}-title`;
  const messageId = `${dialogId}-message`;
  
  // Handle focus trap and initial focus element when dialog opens/closes
  useEffect(() => {
    if (isOpen && dialogRef.current) {
      // Create a focus trap to keep focus within the dialog
      focusTrapRef.current = new FocusTrap(dialogRef.current);
      focusTrapRef.current.activate();
      
      // Set initial focus to the specified element or default to cancel button
      if (initialFocusSelector) {
        const initialFocusElement = dialogRef.current.querySelector(initialFocusSelector) as HTMLElement;
        if (initialFocusElement) {
          initialFocusElement.focus();
        } else {
          cancelBtnRef.current?.focus();
        }
      } else {
        // Default focus to cancel button as it's the safer option
        cancelBtnRef.current?.focus();
      }
      
      // Prevent scrolling on the body when dialog is open
      document.body.style.overflow = 'hidden';
    } else {
      // Deactivate focus trap when dialog closes
      if (focusTrapRef.current) {
        focusTrapRef.current.deactivate();
        focusTrapRef.current = null;
      }
      
      // Re-enable scrolling
      document.body.style.overflow = '';
    }
    
    return () => {
      // Cleanup when component unmounts
      if (focusTrapRef.current) {
        focusTrapRef.current.deactivate();
      }
      document.body.style.overflow = '';
    };
  }, [isOpen, initialFocusSelector]);
  
  // Handle escape key to close dialog
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={messageId}
    >
      <div className="flex items-center justify-center min-h-screen p-4">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 bg-black bg-opacity-25 transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        ></div>
        
        {/* Dialog */}
        <div 
          ref={dialogRef}
          id={dialogId}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-xl transform animate-dialog-enter overflow-hidden max-w-lg w-full mx-auto z-50 relative"
        >
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 
              id={titleId}
              className="text-lg font-medium text-gray-900 dark:text-gray-100"
            >
              {title}
            </h3>
          </div>
          
          <div className="px-6 py-4">
            <p 
              id={messageId}
              className="text-gray-700 dark:text-gray-300"
            >
              {message}
            </p>
          </div>
          
          <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 flex justify-end space-x-3">
            <Button
              ref={cancelBtnRef}
              className={cancelButtonClass}
              onClick={onClose}
              variant="outline"
              ariaLabel="Cancel"
            >
              {cancelText || cancelLabel || 'Cancel'}
            </Button>
            <Button
              ref={confirmBtnRef}
              className={confirmButtonClass || getConfirmButtonClass(variant)}
              onClick={() => {
                onConfirm();
                onClose();
              }}
              ariaLabel={confirmText || confirmLabel || 'Confirm'}
            >
              {confirmText || confirmLabel || 'Confirm'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
