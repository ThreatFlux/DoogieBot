import React, { InputHTMLAttributes } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  /**
   * Optional description text that provides more context about the input
   */
  description?: string;
  /**
   * Unique ID for the input field. If not provided, one will be generated.
   */
  inputId?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', label, error, description, inputId, ...props }, ref) => {
    const inputClasses = `w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 
      ${error ? 'border-red-500' : 'border-gray-300 dark:border-gray-700'} 
      ${error ? 'text-red-900' : 'text-gray-900 dark:text-gray-100'} 
      ${error ? 'placeholder-red-300' : 'placeholder-gray-400 dark:placeholder-gray-600'} 
      bg-white dark:bg-gray-800 
      ${className}`;
    
    // Generate a unique ID for the input if not provided
    const generatedId = React.useMemo(() => inputId || `input-${Math.random().toString(36).substring(2, 9)}`, [inputId]);
    
    // Generate unique IDs for the description and error message for aria-describedby
    const descriptionId = description ? `${generatedId}-description` : undefined;
    const errorId = error ? `${generatedId}-error` : undefined;
    
    // Combine description and error IDs for aria-describedby
    const ariaDescribedBy = [descriptionId, errorId].filter(Boolean).join(' ') || undefined;

    return (
      <div className="w-full">
        {label && (
          <label 
            htmlFor={generatedId}
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            {label}
          </label>
        )}
        <input 
          ref={ref} 
          className={inputClasses} 
          id={generatedId}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={ariaDescribedBy}
          {...props} 
        />
        {description && !error && (
          <p 
            id={descriptionId} 
            className="mt-1 text-sm text-gray-500 dark:text-gray-400"
          >
            {description}
          </p>
        )}
        {error && (
          <p 
            id={errorId} 
            className="mt-1 text-sm text-red-600 dark:text-red-400"
            role="alert"
          >
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };