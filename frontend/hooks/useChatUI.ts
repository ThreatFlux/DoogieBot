import { useState, useEffect } from 'react';

export interface UseChatUIReturn {
  isSidebarOpen: boolean;
  setIsSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>;
  deleteDialogOpen: boolean;
  setDeleteDialogOpen: React.Dispatch<React.SetStateAction<boolean>>;
  chatToDelete: string | null;
  setChatToDelete: React.Dispatch<React.SetStateAction<string | null>>;
  // Add other UI states here if needed, e.g., export menu state if not in useCurrentChat
}

export const useChatUI = (initialSidebarOpen = true): UseChatUIReturn => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(initialSidebarOpen);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [chatToDelete, setChatToDelete] = useState<string | null>(null);

  // Example: Auto-close sidebar on mobile when navigating (if needed here)
  // useEffect(() => {
  //   const handleResize = () => {
  //     if (window.innerWidth >= 768) {
  //       setIsSidebarOpen(true); // Or restore based on user preference
  //     }
  //   };
  //   window.addEventListener('resize', handleResize);
  //   // Initial check
  //   if (window.innerWidth < 768) {
  //       // setIsSidebarOpen(false); // Decide initial mobile state
  //   }
  //   return () => window.removeEventListener('resize', handleResize);
  // }, []);


  // Note: The edit dialog state (editDialogOpen) is managed within useCurrentChat
  // as it's tightly coupled with editing the current chat's title.

  return {
    isSidebarOpen,
    setIsSidebarOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    chatToDelete,
    setChatToDelete,
  };
};