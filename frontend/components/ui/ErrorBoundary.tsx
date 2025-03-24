import React, { Component, ErrorInfo, ReactNode, useEffect, useState } from 'react';
import axios from 'axios';
import { createAppError, getUserFriendlyMessage, logError, ErrorCategory } from '@/utils/errorHandling';

// Patch Axios globally to prevent unhandled promise rejections
// This is a global safety net that works alongside our other error handling
if (typeof window !== 'undefined') {
  const originalAxios = axios.create;
  axios.create = function(...args) {
    const instance = originalAxios.apply(this, args);
    
    // Add a global response interceptor to catch all errors
    instance.interceptors.response.use(
      response => response,
      error => {
        console.log('Global axios error interceptor caught:', error);
        // Return a rejected promise, but in a controlled way that won't crash React
        return Promise.reject({
          ...error,
          _handledGlobally: true, // Mark as handled so we know it won't crash
          message: error.message || 'Network request failed'
        });
      }
    );
    
    return instance;
  };
}

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: string;
}

// Functional component to display the error UI
const ErrorDisplay = ({ error, onReset }: { error: Error | null, onReset: () => void }) => {
  // Use our error handling utility to get a standardized error message
  const appError = createAppError(error, 'ErrorBoundary');
  const errorMessage = appError.message;
  const errorDetail = appError.detail || '';
  
  // Categorize the error for appropriate styling
  let bgClass = 'bg-red-50 dark:bg-red-900/20';
  let borderClass = 'border-red-200 dark:border-red-800';
  let textClass = 'text-red-700 dark:text-red-400';
  let detailClass = 'text-red-600 dark:text-red-300';
  let buttonClass = 'bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-700';
  
  if (appError.category === ErrorCategory.VALIDATION) {
    bgClass = 'bg-yellow-50 dark:bg-yellow-900/20';
    borderClass = 'border-yellow-200 dark:border-yellow-800';
    textClass = 'text-yellow-700 dark:text-yellow-400';
    detailClass = 'text-yellow-600 dark:text-yellow-300';
    buttonClass = 'bg-yellow-100 dark:bg-yellow-800 text-yellow-700 dark:text-yellow-300 hover:bg-yellow-200 dark:hover:bg-yellow-700';
  } else if (appError.category === ErrorCategory.NETWORK) {
    bgClass = 'bg-blue-50 dark:bg-blue-900/20';
    borderClass = 'border-blue-200 dark:border-blue-800';
    textClass = 'text-blue-700 dark:text-blue-400';
    detailClass = 'text-blue-600 dark:text-blue-300';
    buttonClass = 'bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-700';
  }
  
  return (
    <div className={`p-4 ${bgClass} border ${borderClass} rounded-md m-4`}>
      <h2 className={`text-lg font-semibold ${textClass} mb-2`}>
        {errorMessage}
      </h2>
      {errorDetail && (
        <p className={`${detailClass} text-sm mb-3`}>
          {errorDetail}
        </p>
      )}
      <button
        className={`px-3 py-1 ${buttonClass} rounded text-sm`}
        onClick={onReset}
        aria-label="Try again"
      >
        Try again
      </button>
    </div>
  );
};

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: ''
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: error.stack || ''
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const appError = createAppError(error, 'ErrorBoundary', {
      componentStack: errorInfo.componentStack
    });
    
    logError(appError);
    
    // Here you could also log the error to a monitoring service
    // if (process.env.NODE_ENV === 'production') {
    //   // Send to monitoring service (e.g., Sentry)
    //   // Sentry.captureException(error, { extra: { componentStack: errorInfo.componentStack } });
    // }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: ''
    });
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      return <ErrorDisplay error={this.state.error} onReset={this.handleReset} />;
    }

    return this.props.children;
  }
}

export default ErrorBoundary;