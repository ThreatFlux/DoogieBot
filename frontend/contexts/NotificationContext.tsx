import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';

// Define notification types
export type NotificationType = 'success' | 'error' | 'info' | 'warning';

// Define the shape of a notification object
export interface Notification {
  id: string;
  message: string;
  type: NotificationType;
  duration?: number; // in milliseconds
}

// Define the shape of the context
interface NotificationContextType {
  notifications: Notification[];
  showNotification: (message: string, type?: NotificationType, duration?: number) => void;
  dismissNotification: (id: string) => void;
  clearAllNotifications: () => void;
}

// Create the context with default values
const NotificationContext = createContext<NotificationContextType>({
  notifications: [],
  showNotification: () => {},
  dismissNotification: () => {},
  clearAllNotifications: () => {},
});

// Create a provider component
export const NotificationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  // Function to show a notification
  const showNotification = (
    message: string,
    type: NotificationType = 'info',
    duration: number = 5000 // Default duration: 5 seconds
  ) => {
    // Generate a unique ID
    const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // Add the notification to the list
    setNotifications(currentNotifications => [
      ...currentNotifications,
      { id, message, type, duration },
    ]);
    
    // Set up auto-dismiss if duration is provided
    if (duration > 0) {
      setTimeout(() => {
        dismissNotification(id);
      }, duration);
    }
    
    return id; // Return the ID in case the caller wants to dismiss it manually
  };

  // Function to dismiss a notification
  const dismissNotification = (id: string) => {
    setNotifications(currentNotifications =>
      currentNotifications.filter(notification => notification.id !== id)
    );
  };

  // Function to clear all notifications
  const clearAllNotifications = () => {
    setNotifications([]);
  };
  
  // Add the showNotification function to the window object for global access
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Add the function to the window object
      (window as any).showNotification = showNotification;
    }
    
    // Clean up on unmount
    return () => {
      if (typeof window !== 'undefined') {
        delete (window as any).showNotification;
      }
    };
  }, []);

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        showNotification,
        dismissNotification,
        clearAllNotifications,
      }}
    >
      {children}
      
      {/* Render notification toasts */}
      {notifications.length > 0 && (
        <div className="fixed bottom-0 right-0 p-4 z-50 space-y-2">
          {notifications.map(notification => (
            <div
              key={notification.id}
              className={`
                px-4 py-3 rounded-md shadow-lg transition-all duration-300 
                flex items-center justify-between max-w-md w-full
                ${notification.type === 'success' ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200' : ''}
                ${notification.type === 'error' ? 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200' : ''}
                ${notification.type === 'warning' ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200' : ''}
                ${notification.type === 'info' ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200' : ''}
              `}
              role="alert"
              aria-live="assertive"
            >
              <div className="flex items-center">
                {/* Icon based on notification type */}
                {notification.type === 'success' && (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                )}
                {notification.type === 'error' && (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                )}
                {notification.type === 'warning' && (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                )}
                {notification.type === 'info' && (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                )}
                <span>{notification.message}</span>
              </div>
              
              <button
                onClick={() => dismissNotification(notification.id)}
                className="ml-4 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                aria-label="Dismiss notification"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </NotificationContext.Provider>
  );
};

// Create a custom hook to use the notification context
export const useNotification = () => useContext(NotificationContext);
