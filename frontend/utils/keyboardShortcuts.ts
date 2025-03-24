import { useEffect } from 'react';

/**
 * Represents a keyboard shortcut with key combination and action
 */
export interface KeyboardShortcut {
  /**
   * The key to trigger the shortcut (e.g., 'n', 'Escape', 'ArrowUp')
   */
  key: string;
  
  /**
   * Whether Ctrl key (or Cmd on Mac) is required
   */
  ctrlKey?: boolean;
  
  /**
   * Whether Alt key (or Option on Mac) is required
   */
  altKey?: boolean;
  
  /**
   * Whether Shift key is required
   */
  shiftKey?: boolean;
  
  /**
   * Description of what the shortcut does (for display in help menus)
   */
  description: string;
  
  /**
   * Function to execute when the shortcut is triggered
   */
  action: () => void;
  
  /**
   * Optional scope restriction (global, chat, admin, etc.)
   */
  scope?: string;
}

/**
 * Generate a human-readable label for a keyboard shortcut
 */
export const getShortcutLabel = (shortcut: KeyboardShortcut): string => {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  
  const parts: string[] = [];
  if (shortcut.ctrlKey) parts.push(isMac ? '⌘' : 'Ctrl');
  if (shortcut.altKey) parts.push(isMac ? '⌥' : 'Alt');
  if (shortcut.shiftKey) parts.push('Shift');
  
  // Convert key to a readable format
  let key = shortcut.key;
  
  // Map special keys to symbols or more readable names
  const keyMap: Record<string, string> = {
    'ArrowUp': '↑',
    'ArrowDown': '↓',
    'ArrowLeft': '←',
    'ArrowRight': '→',
    'Escape': 'Esc',
    ' ': 'Space',
    'Delete': 'Del',
    'Insert': 'Ins',
  };
  
  if (keyMap[key]) {
    key = keyMap[key];
  } else if (key.length === 1) {
    // Capitalize single characters
    key = key.toUpperCase();
  }
  
  parts.push(key);
  return parts.join('+');
};

/**
 * React hook to register multiple keyboard shortcuts
 * @param shortcuts Array of keyboard shortcuts to register
 * @param currentScope Optional current scope to filter shortcuts
 */
export const useKeyboardShortcuts = (
  shortcuts: KeyboardShortcut[],
  currentScope: string = 'global'
) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs, textareas, or content editable elements
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        (e.target instanceof HTMLElement && e.target.isContentEditable)
      ) {
        return;
      }
      
      for (const shortcut of shortcuts) {
        // Skip shortcuts not in the current scope (if scope is specified)
        if (shortcut.scope && shortcut.scope !== currentScope && shortcut.scope !== 'global') {
          continue;
        }
        
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatch = Boolean(e.ctrlKey || e.metaKey) === Boolean(shortcut.ctrlKey);
        const altMatch = Boolean(e.altKey) === Boolean(shortcut.altKey);
        const shiftMatch = Boolean(e.shiftKey) === Boolean(shortcut.shiftKey);
        
        if (keyMatch && ctrlMatch && altMatch && shiftMatch) {
          e.preventDefault();
          shortcut.action();
          break;
        }
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [shortcuts, currentScope]);
};

/**
 * Common application shortcuts that can be used across the app
 */
export const commonShortcuts: KeyboardShortcut[] = [
  {
    key: 'n',
    ctrlKey: true,
    description: 'New chat',
    action: () => {}, // Will be implemented in the component
    scope: 'chat'
  },
  {
    key: '/',
    description: 'Focus search',
    action: () => {}, // Will be implemented in the component
    scope: 'global'
  },
  {
    key: 'Escape',
    description: 'Close dialogs',
    action: () => {}, // Will be implemented in the component
    scope: 'global'
  },
  {
    key: 'e',
    ctrlKey: true,
    description: 'Edit current chat title',
    action: () => {}, // Will be implemented in the component
    scope: 'chat'
  },
  {
    key: 'h',
    ctrlKey: true,
    shiftKey: true,
    description: 'Show keyboard shortcuts help',
    action: () => {}, // Will be implemented in the component
    scope: 'global'
  }
];
