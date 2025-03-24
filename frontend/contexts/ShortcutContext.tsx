import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import ShortcutHelpDialog from '@/components/ui/ShortcutHelpDialog';
import { KeyboardShortcut, commonShortcuts } from '@/utils/keyboardShortcuts';

interface ShortcutContextType {
  isDialogOpen: boolean;
  openShortcutDialog: () => void;
  closeShortcutDialog: () => void;
  toggleShortcutDialog: () => void;
  registerShortcuts: (shortcuts: KeyboardShortcut[]) => void;
  unregisterShortcuts: (shortcuts: KeyboardShortcut[]) => void;
}

const ShortcutContext = createContext<ShortcutContextType>({
  isDialogOpen: false,
  openShortcutDialog: () => {},
  closeShortcutDialog: () => {},
  toggleShortcutDialog: () => {},
  registerShortcuts: () => {},
  unregisterShortcuts: () => {},
});

export const useShortcuts = () => useContext(ShortcutContext);

export const ShortcutProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [allShortcuts, setAllShortcuts] = useState<KeyboardShortcut[]>([...commonShortcuts]);
  
  const openShortcutDialog = useCallback(() => {
    setIsDialogOpen(true);
  }, []);
  
  const closeShortcutDialog = useCallback(() => {
    setIsDialogOpen(false);
  }, []);
  
  const toggleShortcutDialog = useCallback(() => {
    setIsDialogOpen(prev => !prev);
  }, []);
  
  // Register new shortcuts in the system
  const registerShortcuts = useCallback((shortcuts: KeyboardShortcut[]) => {
    setAllShortcuts(prev => {
      // Filter out any shortcuts that might be duplicates by key combo
      const filtered = prev.filter(existing => 
        !shortcuts.some(newShortcut => 
          newShortcut.key === existing.key &&
          newShortcut.ctrlKey === existing.ctrlKey &&
          newShortcut.altKey === existing.altKey &&
          newShortcut.shiftKey === existing.shiftKey
        )
      );
      return [...filtered, ...shortcuts];
    });
  }, []);
  
  // Unregister shortcuts from the system
  const unregisterShortcuts = useCallback((shortcuts: KeyboardShortcut[]) => {
    setAllShortcuts(prev => 
      prev.filter(existing => 
        !shortcuts.some(toRemove => 
          toRemove.key === existing.key &&
          toRemove.ctrlKey === existing.ctrlKey &&
          toRemove.altKey === existing.altKey &&
          toRemove.shiftKey === existing.shiftKey
        )
      )
    );
  }, []);
  
  // Register dialog toggle shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        (e.target instanceof HTMLElement && e.target.isContentEditable)
      ) {
        return;
      }
      
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const ctrlOrCmd = isMac ? e.metaKey : e.ctrlKey;
      
      // Ctrl+Shift+H or Cmd+Shift+H to toggle shortcuts dialog
      if ((e.key === 'h' || e.key === 'H') && ctrlOrCmd && e.shiftKey) {
        e.preventDefault();
        toggleShortcutDialog();
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [toggleShortcutDialog]);
  
  return (
    <ShortcutContext.Provider
      value={{
        isDialogOpen,
        openShortcutDialog,
        closeShortcutDialog,
        toggleShortcutDialog,
        registerShortcuts,
        unregisterShortcuts,
      }}
    >
      {children}
      <ShortcutHelpDialog
        isOpen={isDialogOpen}
        onClose={closeShortcutDialog}
        shortcuts={allShortcuts}
      />
    </ShortcutContext.Provider>
  );
};

export default ShortcutContext;
