import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { KeyboardShortcut } from '@/utils/keyboardShortcuts';

interface ShortcutHelpDialogProps {
  isOpen: boolean;
  onClose: () => void;
  shortcuts: KeyboardShortcut[];
}

const ShortcutHelpDialog: React.FC<ShortcutHelpDialogProps> = ({
  isOpen,
  onClose,
  shortcuts
}) => {
  const [mounted, setMounted] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Handle safe mounting for SSR
  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  // Focus search input when dialog opens
  useEffect(() => {
    if (isOpen && mounted && searchInputRef.current) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 100);
    }
  }, [isOpen, mounted]);

  // Listen for Escape key to close dialog
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!mounted || !isOpen) return null;

  // Group shortcuts by scope/category
  const groupedShortcuts = shortcuts.reduce<Record<string, KeyboardShortcut[]>>((groups, shortcut) => {
    const category = shortcut.scope || 'general';
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(shortcut);
    return groups;
  }, {});

  // Get all unique categories
  const categories = Object.keys(groupedShortcuts).sort();

  // If no active category is set, use the first available
  if (!activeCategory && categories.length > 0) {
    setActiveCategory(categories[0]);
  }

  // Filter shortcuts based on search
  const filteredShortcuts = shortcuts.filter(shortcut => {
    if (!searchTerm) {
      return activeCategory ? (shortcut.scope || 'general') === activeCategory : true;
    }

    const searchLower = searchTerm.toLowerCase();
    return (
      shortcut.description.toLowerCase().includes(searchLower) ||
      shortcut.key.toLowerCase().includes(searchLower) ||
      (shortcut.scope || 'general').toLowerCase().includes(searchLower)
    );
  });

  // Format shortcut key for display
  const formatShortcutKey = (shortcut: KeyboardShortcut) => {
    const keys: string[] = [];
    
    const isMac = typeof navigator !== 'undefined' && 
      navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    
    if (shortcut.ctrlKey) keys.push(isMac ? '⌘' : 'Ctrl');
    if (shortcut.altKey) keys.push(isMac ? '⌥' : 'Alt');
    if (shortcut.shiftKey) keys.push('Shift');
    
    keys.push(shortcut.key.toUpperCase());
    
    return keys.map(key => (
      <span 
        key={key} 
        className="inline-flex items-center justify-center px-2 py-1 text-xs font-medium bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded mx-0.5"
      >
        {key}
      </span>
    ));
  };

  return createPortal(
    <div 
      className="fixed inset-0 z-50 overflow-y-auto"
      aria-labelledby="shortcut-dialog-title"
      role="dialog"
      aria-modal="true"
    >
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Dialog */}
      <div className="flex items-center justify-center min-h-screen p-4">
        <div 
          ref={dialogRef}
          className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] flex flex-col"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-700 p-4">
            <h2 
              id="shortcut-dialog-title" 
              className="text-lg font-semibold text-gray-900 dark:text-white"
            >
              Keyboard Shortcuts
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Search */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="relative">
              <input
                ref={searchInputRef}
                type="text"
                value={searchTerm}
                onChange={e => {
                  setSearchTerm(e.target.value);
                  if (e.target.value) {
                    setActiveCategory(null);
                  } else if (categories.length > 0) {
                    setActiveCategory(categories[0]);
                  }
                }}
                placeholder="Search shortcuts..."
                className="w-full px-4 py-2 pl-10 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Search shortcuts"
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex flex-1 overflow-hidden">
            {/* Categories (only shown when not searching) */}
            {!searchTerm && (
              <div className="w-1/4 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
                <nav className="py-2">
                  {categories.map(category => (
                    <button
                      key={category}
                      onClick={() => setActiveCategory(category)}
                      className={`w-full text-left px-4 py-2 text-sm ${
                        activeCategory === category 
                          ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300' 
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      {category.charAt(0).toUpperCase() + category.slice(1)}
                    </button>
                  ))}
                </nav>
              </div>
            )}

            {/* Shortcut List */}
            <div className={`${searchTerm ? 'w-full' : 'w-3/4'} overflow-y-auto p-4`}>
              {filteredShortcuts.length > 0 ? (
                <div className="space-y-4">
                  {searchTerm ? (
                    // Search results grouped by category
                    Object.entries(
                      filteredShortcuts.reduce<Record<string, KeyboardShortcut[]>>((groups, shortcut) => {
                        const category = shortcut.scope || 'general';
                        if (!groups[category]) {
                          groups[category] = [];
                        }
                        groups[category].push(shortcut);
                        return groups;
                      }, {})
                    ).map(([category, shortcuts]) => (
                      <div key={category}>
                        <h3 className="text-md font-medium text-gray-900 dark:text-white mb-2">
                          {category.charAt(0).toUpperCase() + category.slice(1)}
                        </h3>
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg overflow-hidden">
                          <table className="w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                              {shortcuts.map((shortcut, index) => (
                                <tr key={`${shortcut.key}-${index}`}>
                                  <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                                    {shortcut.description}
                                  </td>
                                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-right">
                                    {formatShortcutKey(shortcut)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))
                  ) : (
                    // Category-specific shortcuts
                    <div>
                      <h3 className="text-md font-medium text-gray-900 dark:text-white mb-2">
                        {activeCategory ? 
                          activeCategory.charAt(0).toUpperCase() + activeCategory.slice(1) : 
                          'General'
                        }
                      </h3>
                      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg overflow-hidden">
                        <table className="w-full divide-y divide-gray-200 dark:divide-gray-700">
                          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                            {filteredShortcuts.map((shortcut, index) => (
                              <tr key={`${shortcut.key}-${index}`}>
                                <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                                  {shortcut.description}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-right">
                                  {formatShortcutKey(shortcut)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-10">
                  <p className="text-gray-500 dark:text-gray-400">
                    No shortcuts found matching "{searchTerm}"
                  </p>
                </div>
              )}
            </div>
          </div>
          
          {/* Footer */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4 text-center text-sm text-gray-500 dark:text-gray-400">
            Press <span className="inline-flex items-center justify-center px-2 py-1 text-xs font-medium bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded mx-0.5">Esc</span> to close
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default ShortcutHelpDialog;
