import React, { ReactNode, useState, useEffect, useRef } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useShortcuts } from '@/contexts/ShortcutContext';
import Link from 'next/link';
import { ariaLandmarks, srOnly, srOnlyFocusable, announce } from '@/utils/accessibilityUtils';
import SkipLink from '@/components/ui/SkipLink';

interface LayoutProps {
  children: ReactNode;
  title?: string;
  description?: string;
  chatHistory?: ReactNode;       // Kept for backward compatibility
  activeConversationId?: string; // Kept for backward compatibility
  sidebarContent?: ReactNode;    // New prop that replaces chatHistory
  isSidebarOpen?: boolean;       // New prop to control initial sidebar visibility
}

const Layout: React.FC<LayoutProps> = ({
  children,
  title = 'Doogie Chat Bot',
  description = 'A sophisticated chat bot with a Hybrid RAG system',
  chatHistory,
  activeConversationId,
  sidebarContent,
  isSidebarOpen = false
}) => {
  const { isAuthenticated, isAdmin, user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const shortcuts = useShortcuts();
  const router = useRouter();
  
  // Sidebar states
  const [isSidebarVisible, setSidebarVisible] = useState(isSidebarOpen);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const mainContentRef = useRef<HTMLDivElement>(null);
  const autoHideTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Track if we're hovering over the sidebar trigger area
  const [isHoveringTrigger, setIsHoveringTrigger] = useState(false);
  
  // Determine what to show in the sidebar
  const sidebarContentToShow = sidebarContent || (
    isAuthenticated && router.pathname.startsWith('/chat') && chatHistory ? (
      <div className="mb-4">
        <h2 className="text-lg font-medium text-white mb-2">Conversations</h2>
        {chatHistory}
      </div>
    ) : null
  );
  
  // Update sidebar visibility when isSidebarOpen prop changes
  useEffect(() => {
    setSidebarVisible(isSidebarOpen);
  }, [isSidebarOpen]);
  
  // Handle focus detection for sidebar
  useEffect(() => {
    // Function to check if focus is within the sidebar
    const handleFocusCheck = () => {
      if (sidebarRef.current && sidebarRef.current.contains(document.activeElement)) {
        setSidebarVisible(true);
        
        // Clear any existing auto-hide timeout
        if (autoHideTimeoutRef.current) {
          clearTimeout(autoHideTimeoutRef.current);
          autoHideTimeoutRef.current = null;
        }
      }
    };
    
    // Set up listeners
    document.addEventListener('focusin', handleFocusCheck);
    return () => document.removeEventListener('focusin', handleFocusCheck);
  }, []);
  
  // Handle clicks outside the sidebar to close it
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        isSidebarVisible && 
        sidebarRef.current && 
        !sidebarRef.current.contains(event.target as Node) &&
        !isHoveringTrigger
      ) {
        setSidebarVisible(false);
        announce({ 
          message: 'Sidebar closed', 
          politeness: 'polite' 
        });
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isSidebarVisible, isHoveringTrigger]);
  
  // Handle escape key to close sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isSidebarVisible) {
        setSidebarVisible(false);
        announce({ 
          message: 'Sidebar closed', 
          politeness: 'polite' 
        });
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSidebarVisible]);

  // Add focus outline styles when using keyboard navigation
  useEffect(() => {
    const handleFirstTab = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        document.body.classList.add('user-is-tabbing');
        window.removeEventListener('keydown', handleFirstTab);
      }
    };

    window.addEventListener('keydown', handleFirstTab);
    return () => {
      window.removeEventListener('keydown', handleFirstTab);
    };
  }, []);
  
  // Handle mouseenter on sidebar to clear auto-hide timeout
  useEffect(() => {
    const sidebarElement = sidebarRef.current;
    
    const handleMouseEnter = () => {
      if (autoHideTimeoutRef.current) {
        clearTimeout(autoHideTimeoutRef.current);
        autoHideTimeoutRef.current = null;
      }
    };
    
    sidebarElement?.addEventListener('mouseenter', handleMouseEnter);
    return () => {
      sidebarElement?.removeEventListener('mouseenter', handleMouseEnter);
    };
  }, []);
  
  // Navigation items
  const navItems = [
    ...(isAuthenticated
      ? [
          {
            path: '/chat',
            label: 'Chat',
            icon: (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            ),
          },
          {
            path: '/profile',
            label: 'Profile',
            icon: (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            ),
          },
          ...(isAdmin
            ? [
                {
                  path: '/admin',
                  label: 'Admin',
                  icon: (
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  ),
                },
              ]
            : []),
        ]
      : [
          {
            path: '/login',
            label: 'Login',
            icon: (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
              </svg>
            ),
          },
          {
            path: '/register',
            label: 'Register',
            icon: (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
            ),
          },
        ]),
  ];

  const isActive = (path: string) => {
    if (path === '/chat' && router.pathname === '/chat') {
      return true;
    }
    if (path === '/admin' && router.pathname.startsWith('/admin')) {
      return true;
    }
    return router.pathname === path;
  };

  return (
    <>
      {/* Skip links for keyboard navigation - visually hidden until focused */}
      <div className="sr-only" aria-label="Accessibility navigation">
        <SkipLink target="main-content" label="Skip to main content" position="top-center" />
        <SkipLink target="nav-sidebar" label="Skip to navigation" position="top-center" />
      </div>
      
      <Head>
        <title>{title}</title>
        <meta name="description" content={description} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex">
        {/* Mobile backdrop overlay - only shown on mobile when sidebar is open */}
        {isSidebarVisible && (
          <div 
            className="md:hidden sidebar-backdrop"
            onClick={() => {
              setSidebarVisible(false);
              announce({ 
                message: 'Sidebar closed', 
                politeness: 'polite' 
              });
            }}
            aria-hidden="true"
          />
        )}
        
        {/* Sidebar trigger area - desktop only */}
        <div 
          className="fixed left-0 top-0 bottom-0 w-12 z-30 hidden md:block"
          onMouseEnter={() => {
            setIsHoveringTrigger(true);
            setSidebarVisible(true);
            announce({ 
              message: 'Sidebar opened', 
              politeness: 'polite' 
            });
          }}
          onMouseLeave={() => {
            setIsHoveringTrigger(false);
            // Set a timeout to close the sidebar after a delay
            autoHideTimeoutRef.current = setTimeout(() => {
              if (!sidebarRef.current?.contains(document.activeElement)) {
                setSidebarVisible(false);
                announce({ 
                  message: 'Sidebar closed', 
                  politeness: 'polite' 
                });
              }
            }, 1000); // 1 second delay
          }}
          aria-hidden="true"
        />
        
        {/* Accessible keyboard trigger button - visually hidden until focused */}
        <button
          className="fixed left-0 top-1/2 transform -translate-y-1/2 bg-gray-800 dark:bg-gray-900 text-white p-1 rounded-r-md focus:outline-none focus:ring-2 focus:ring-primary-500 sr-only focus:not-sr-only z-30"
          onClick={() => {
            setSidebarVisible(true);
            announce({ 
              message: 'Sidebar opened', 
              politeness: 'polite' 
            });
          }}
          aria-label="Open navigation sidebar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
        </button>
        
        {/* Combined Navigation and Chat History Sidebar */}
        <div 
          ref={sidebarRef}
          id="nav-sidebar"
          className={`fixed left-0 top-0 bottom-0 z-30 w-64 md:w-72 lg:w-80 bg-gray-800 dark:bg-gray-900 shadow-lg transition-transform duration-300 transform ${
            isSidebarVisible ? 'translate-x-0' : '-translate-x-full'
          }`}
          role={ariaLandmarks.navigation}
          aria-label="Main Navigation and Chat History"
          aria-expanded={isSidebarVisible}
        >
          {/* App Logo and Title */}
          <div className="p-4 border-b border-gray-700 flex items-center justify-between">
            <button
              onClick={() => {
                setSidebarVisible(false);
                announce({ 
                  message: 'Sidebar closed', 
                  politeness: 'polite' 
                });
              }}
              className="absolute right-4 text-gray-300 hover:text-white"
              aria-label="Close sidebar"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
            <Link href="/" className="flex items-center mx-auto py-2">
              <img 
                src="/images/logo.png" 
                alt="Doogie Chat Bot Logo" 
                className="h-12 w-auto" 
                aria-hidden="false"
              />
              <span className="sr-only">Doogie Chat Bot</span>
            </Link>
          </div>
          
          <div className="h-full overflow-hidden flex flex-col">
            {/* Integrated Chat History and Navigation */}
            <nav className="flex-grow overflow-y-auto p-4" aria-label="Main Menu">
              {/* If we have sidebar content to show, display it first */}
              {sidebarContentToShow && (
                <div className="sidebar-chat-history">
                  {sidebarContentToShow}
                </div>
              )}
              
              {/* Navigation Section */}
              <ul className="space-y-2">
                {navItems.map((item) => (
                  <li key={item.path}>
                    <Link
                      href={item.path}
                      className={`flex items-center px-3 py-2 rounded-md ${
                        isActive(item.path)
                          ? 'bg-primary-700 text-white'
                          : 'text-gray-300 hover:bg-gray-700'
                      }`}
                      aria-current={isActive(item.path) ? 'page' : undefined}
                    >
                      <span className="flex-shrink-0" aria-hidden="true">{item.icon}</span>
                      <span className="ml-3">{item.label}</span>
                    </Link>
                  </li>
                ))}
                {isAuthenticated && (
                  <li>
                    <button
                      onClick={logout}
                      className="flex items-center w-full px-3 py-2 rounded-md text-gray-300 hover:bg-gray-700"
                      aria-label="Logout"
                    >
                      <span className="flex-shrink-0" aria-hidden="true">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                      </span>
                      <span className="ml-3">Logout</span>
                    </button>
                  </li>
                )}
              </ul>
            </nav>
            
            {/* Bottom section with theme toggle and shortcuts */}
            <div className="p-4 border-t border-gray-700 mt-auto">
              <div className="flex flex-col space-y-4">
                {/* Theme toggle */}
                <button
                  onClick={() => {
                    toggleTheme();
                    announce({ 
                      message: `Switched to ${theme === 'dark' ? 'light' : 'dark'} mode`, 
                      politeness: 'polite' 
                    });
                  }}
                  className="flex items-center text-gray-300 hover:text-white"
                  aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode, current mode is ${theme === 'dark' ? 'dark' : 'light'}`}
                  aria-pressed={theme === 'dark'}
                  data-testid="theme-toggle"
                >
                  {theme === 'dark' ? (
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
                    </svg>
                  )}
                  <span className="ml-3">{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
                </button>
                
                {/* Keyboard shortcuts button - if using ShortcutContext */}
                {shortcuts && (
                  <button
                    onClick={shortcuts.toggleShortcutDialog}
                    className="flex items-center text-gray-300 hover:text-white"
                    aria-label="Show keyboard shortcuts"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    <span className="ml-3">Shortcuts</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
        
        {/* Main content */}
        <div className="flex-1 flex flex-col min-h-screen">
          {/* Main content area */}
          <main 
            className="flex-1 p-6 pt-4 overflow-auto"
            role={ariaLandmarks.main}
            id="main-content"
            ref={mainContentRef}
            tabIndex={-1}
            aria-label="Main content"
          >
            {/* App header for mobile - only shown on smaller screens */}
            <div className="flex items-center md:hidden mb-4">
              <button
                onClick={() => {
                  setSidebarVisible(!isSidebarVisible);
                  announce({ 
                    message: isSidebarVisible ? 'Sidebar closed' : 'Sidebar opened', 
                    politeness: 'polite' 
                  });
                }}
                className="text-gray-700 dark:text-gray-300 mr-2"
                aria-label={isSidebarVisible ? "Close navigation" : "Open navigation"}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <h1 className="text-lg font-bold flex items-center">
                <img 
                  src="/images/logo.png" 
                  alt="Doogie Chat Bot Logo" 
                  className="h-8 w-auto mr-2" 
                  aria-hidden="true"
                />
                <span>{title}</span>
              </h1>
            </div>
            
            {children}
          </main>
          
          {/* Footer */}
          <footer 
            className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-2 text-center"
            role={ariaLandmarks.contentinfo}
          >
            <p className="text-xs text-gray-500 dark:text-gray-400">
              &copy; {new Date().getFullYear()} Doogie Chat Bot
            </p>
          </footer>
        </div>
      </div>
    </>
  );
};

export default Layout;