import React, { TextareaHTMLAttributes } from 'react';

export interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  /**
   * Optional description text that provides more context about the textarea
   */
  description?: string;
  /**
   * Unique ID for the textarea field. If not provided, one will be generated.
   */
  textareaId?: string;
  /**
   * Auto-resize the textarea height based on content
   */
  autoResize?: boolean;
}

const TextArea = React.forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ className = '', label, error, description, textareaId, autoResize = false, rows = 3, ...props }, ref) => {
    const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
    const [height, setHeight] = React.useState<number | undefined>(undefined);

    // Combine the forwarded ref with our local ref
    const setRefs = React.useCallback(
      (element: HTMLTextAreaElement | null) => {
        textareaRef.current = element;
        
        // Handle forwarded ref
        if (ref) {
          if (typeof ref === 'function') {
            ref(element);
          } else {
            ref.current = element;
          }
        }
      },
      [ref]
    );

    // Auto-resize logic
    const adjustHeight = React.useCallback(() => {
      if (!autoResize || !textareaRef.current) return;
      
      // Reset the height momentarily to get the correct scrollHeight value
      textareaRef.current.style.height = 'auto';
      
      // Get the scrollHeight and set the height
      const scrollHeight = textareaRef.current.scrollHeight;
      setHeight(scrollHeight);
      textareaRef.current.style.height = `${scrollHeight}px`;
    }, [autoResize]);

    // Adjust height on component mount
    React.useEffect(() => {
      adjustHeight();
    }, [adjustHeight]);

    // Adjust height when content changes
    const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
      adjustHeight();
      props.onInput?.(e);
    };

    const textareaClasses = `w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 
      ${error ? 'border-red-500' : 'border-gray-300 dark:border-gray-700'} 
      ${error ? 'text-red-900' : 'text-gray-900 dark:text-gray-100'} 
      ${error ? 'placeholder-red-300' : 'placeholder-gray-400 dark:placeholder-gray-600'} 
      bg-white dark:bg-gray-800 
      ${className}`;
    
    // Generate a unique ID for the textarea if not provided
    const generatedId = React.useMemo(() => textareaId || `textarea-${Math.random().toString(36).substring(2, 9)}`, [textareaId]);
    
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
        <textarea 
          ref={setRefs} 
          className={textareaClasses} 
          id={generatedId}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={ariaDescribedBy}
          rows={rows}
          style={height ? { height: `${height}px` } : undefined}
          onInput={handleInput}
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

TextArea.displayName = 'TextArea';

export { TextArea };