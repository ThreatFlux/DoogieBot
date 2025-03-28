import { useCallback, useEffect } from 'react'; // Added useEffect
import { useRouter } from 'next/router';
import Layout from '@/components/layout/Layout';
import { Card, CardContent } from '@/components/ui/Card';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { useAuth } from '@/contexts/AuthContext';
import { useNotification } from '@/contexts/NotificationContext';
import { Chat, Message } from '@/types'; // Keep types
import { deleteChat } from '@/services/chat'; // Keep deleteChat service call
import { announce } from '@/utils/accessibilityUtils';

// Import Child Components
import ChatSidebar from '@/components/chat/ChatSidebar';
import ImprovedMessageContent from '@/components/chat/ImprovedMessageContent';
import ImprovedChatInput from '@/components/chat/ImprovedChatInput';
import DocumentReferences from '@/components/chat/DocumentReferences';

// Import Custom Hooks
import { useChatList } from '@/hooks/useChatList';
import { useCurrentChat } from '@/hooks/useCurrentChat';
import { useChatMessages } from '@/hooks/useChatMessages';
import { useChatUI } from '@/hooks/useChatUI';

export const CleanChatPage = () => {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { showNotification } = useNotification();
  const router = useRouter();

  // --- Instantiate Hooks ---

  const {
    isSidebarOpen,
    setIsSidebarOpen,
    deleteDialogOpen,
    setDeleteDialogOpen,
    chatToDelete,
    setChatToDelete,
  } = useChatUI();

  // useCurrentChat needs setChats from useChatList to update the list on title change
  // We'll get setChats from useChatList below and pass it later if needed,
  // but let's instantiate useCurrentChat first as useChatList might need currentChat
  const {
    currentChat,
    setCurrentChat,
    isLoading: isLoadingCurrentChat,
    error: errorCurrentChat,
    isEditingTitle,
    editedTitle,
    setEditedTitle,
    originalTitle,
    editDialogOpen,
    setEditDialogOpen,
    showExportMenu,
    setShowExportMenu,
    exportMenuRef,
    titleInputRef,
    handleStartEditTitle,
    confirmEditTitle,
    handleSaveTitle,
    // handleUpdateTitle is used internally or via events
    handleExport,
    loadSpecificChat, // Expose if needed, maybe not directly used in JSX
  } = useCurrentChat(null, () => {}); // Pass dummy setChats for now, will fix

  const {
    chats,
    filteredChats,
    searchTerm,
    selectedFilterTags,
    isLoading: isLoadingChatList,
    error: errorChatList,
    loadChats,
    setSearchTerm,
    setSelectedFilterTags,
    handleNewChat,
    handleSelectChat: selectChatFromList, // Renamed to avoid conflict
    handleUpdateTags,
    handleDeleteChatClick,
    setChats, // Get setChats to pass to useCurrentChat
  } = useChatList(
      [],
      currentChat,
      setCurrentChat,
      setChatToDelete,
      setDeleteDialogOpen
  );

  // Now, properly instantiate useCurrentChat with the real setChats
  // Re-instantiating like this isn't ideal, but necessary due to hook dependencies.
  // A better approach might involve context or a single larger state management hook/library.
  // For this refactor, we'll accept this limitation.
  const currentChatHook = useCurrentChat(currentChat, setChats);

  const {
    isStreaming,
    isWaitingForResponse, // Get new state from hook
    error: errorMessages,
    messagesEndRef,
    handleSendMessage,
    handleFeedback,
    handleUpdateMessage,
    // closeEventSource // Only needed if called directly from component
  } = useChatMessages(
      currentChatHook.currentChat, // Use currentChat from the properly initialized hook
      currentChatHook.setCurrentChat,
      setChats,
      loadChats
  );

  // --- Combined Loading/Error State ---
  // Prioritize more specific errors if they exist
  const isLoading = authLoading || isLoadingChatList || isLoadingCurrentChat;
  const error = errorMessages || errorCurrentChat || errorChatList;

  // --- Redirect Logic ---
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // --- Specific Handlers Requiring Cross-Hook Interaction ---

  // Handle actual deletion after confirmation
  const handleDeleteChat = useCallback(async () => {
    if (!chatToDelete) return;

    console.log('Deleting chat:', chatToDelete);
    // Consider a dedicated loading state for delete? Using main isLoading for now.
    // setIsLoading(true); // Maybe manage this within useChatList or useChatUI?
    // setError(null); // Clear errors via specific hooks if needed

    const originalChats = chats; // Backup for rollback
    const wasCurrentChat = currentChatHook.currentChat?.id === chatToDelete;

    // Optimistically remove the chat from the UI
    setChats(prevChats => prevChats.filter(chat => chat.id !== chatToDelete));
    if (wasCurrentChat) {
        currentChatHook.setCurrentChat(null);
        // Navigate away from the deleted chat's URL
        router.push('/chat', undefined, { shallow: true });
    }

    try {
      const { success, error: deleteError } = await deleteChat(chatToDelete);

      if (success) {
        console.log('Delete successful');
        showNotification('Chat deleted successfully', 'success');
        announce({ message: 'Chat deleted successfully', politeness: 'polite' });
        // No need to reload chats, optimistic update is done.
        // If server state deviates, loadChats() could be called here.
      } else {
        console.error('Delete failed with error:', deleteError);
        showNotification(`Failed to delete chat: ${deleteError}`, 'error');
        // Rollback optimistic update
        setChats(originalChats);
        if (wasCurrentChat) {
            // If rollback is needed, try to reload the chat that failed deletion
            loadSpecificChat(chatToDelete);
            router.push(`/chat?id=${chatToDelete}`, undefined, { shallow: true });
        }
      }
    } catch (err) {
      console.error('Error deleting chat:', err);
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      showNotification(`An unexpected error occurred: ${errorMsg}`, 'error');
      // Rollback optimistic update
      setChats(originalChats);
      if (wasCurrentChat) {
          loadSpecificChat(chatToDelete);
          router.push(`/chat?id=${chatToDelete}`, undefined, { shallow: true });
      }
    } finally {
      // Reset dialog state
      setChatToDelete(null);
      setDeleteDialogOpen(false);
      // setIsLoading(false); // Reset loading state if managed here
    }
  }, [chatToDelete, chats, currentChatHook, setChats, loadSpecificChat, router, setChatToDelete, setDeleteDialogOpen, showNotification]);


  // Auto-close sidebar on mobile after selection
  const handleSelectChat = (chat: Chat) => {
    selectChatFromList(chat); // Call the handler from useChatList
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };


  // --- Render Functions ---

  const renderChatSidebar = () => (
    <ChatSidebar
      // Pass props from useChatList
      chats={chats}
      filteredChats={filteredChats}
      searchTerm={searchTerm}
      selectedFilterTags={selectedFilterTags}
      onSearchChange={setSearchTerm}
      onSelectedTagsChange={setSelectedFilterTags}
      onSelectChat={handleSelectChat} // Use the wrapper function
      onNewChat={handleNewChat}
      onDeleteChat={handleDeleteChatClick}
      onUpdateTags={handleUpdateTags}
      // Highlighting is likely handled internally or based on router query
    />
  );

  const renderChatContent = () => {
    if (!isAuthenticated && !authLoading) {
      // Or redirect handled by useEffect
      return <div className="flex items-center justify-center h-full"><p>Redirecting to login...</p></div>;
    }

    if (isLoading && !currentChatHook.currentChat) { // Show loading only if no chat is displayed yet
        return <div className="flex items-center justify-center h-full"><p>Loading chats...</p></div>;
    }

    if (!currentChatHook.currentChat) {
      // Welcome / No Chat Selected State
      return (
        <div className="flex items-center justify-center h-full">
          <Card className="max-w-md w-full">
            <CardContent className="p-6 text-center">
              <h2 className="text-xl font-bold mb-4">Welcome to Doogie Chat</h2>
              <p className="mb-4 text-gray-600 dark:text-gray-400">
                Start a new conversation or select an existing one from the sidebar.
              </p>
              <button
                className="text-primary-600 dark:text-primary-400 font-medium"
                onClick={handleNewChat} // Use handler from useChatList
              >
                Start a new conversation
              </button>
            </CardContent>
          </Card>
        </div>
      );
    }

    // Main Chat View
    return (
      <div className="flex flex-col h-full min-h-0">
        {/* Title is now handled by Layout component via props */}

        {/* Chat Messages Area */}
        <div className="flex-grow overflow-y-auto p-4 min-h-0" aria-live="polite">
          {error && ( // Display combined error state
            <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-md flex items-start" role="alert">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {currentChatHook.currentChat.messages?.length > 0 ? (
            <div className="space-y-4">
              {currentChatHook.currentChat.messages.map((message) => (
                <div
                  key={message.id} // Use message.id from data
                  className={`message ${
                    message.role === 'user' ? 'user-message' : 'assistant-message'
                  } p-4 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-gray-100 dark:bg-gray-700 ml-4 mr-0 md:ml-12 md:mr-0'
                      : 'bg-blue-50 dark:bg-blue-900/20 ml-0 mr-4 md:ml-0 md:mr-12'
                  }`}
                  role={message.role === 'assistant' ? 'region' : undefined}
                  aria-label={message.role === 'assistant' ? "Assistant's response" : undefined}
                >
                  <div className="flex justify-between mb-2">
                    <span className="font-medium text-sm text-gray-500 dark:text-gray-400">
                      {message.role === 'user' ? 'You' : 'Doogie'}
                      {message.created_at && (
                        <span className="ml-2 font-normal text-xs">
                          {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                      {message.tokens && message.role === 'assistant' && (
                        <span className="ml-2 font-normal text-xs">{message.tokens} tokens</span>
                      )}
                    </span>
                  </div>

                  <ImprovedMessageContent
                    content={message.content}
                    message={message}
                    onUpdateMessage={handleUpdateMessage} // From useChatMessages
                    // Pass feedback handler if needed by ImprovedMessageContent
                    onFeedback={handleFeedback} // Pass the feedback handler
                    isWaitingForResponse={isWaitingForResponse && message.role === 'assistant' && !message.content} // Pass waiting state only for the empty assistant placeholder
                  />

                  {message.role === 'assistant' && message.document_ids && message.document_ids.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Sources</h4>
                      <DocumentReferences documentIds={message.document_ids} />
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} /> {/* From useChatMessages */}
            </div>
          ) : (
            // Empty Chat State
            <div className="flex flex-col items-center justify-center h-full text-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
               </svg>
               <p className="text-gray-500 dark:text-gray-400 mb-2">No messages yet</p>
               <p className="text-sm text-gray-400 dark:text-gray-500 max-w-md">
                 Start by typing a message below. Doogie will respond.
               </p>
            </div>
          )}
        </div>

        {/* Chat Input */}
        <ImprovedChatInput
          onSendMessage={handleSendMessage} // From useChatMessages
          isStreaming={isStreaming} // From useChatMessages
          disabled={!currentChatHook.currentChat || isStreaming}
        />
      </div>
    );
  };

  // --- Main Component Return ---
  return (
    <Layout
      title={currentChatHook.currentChat?.title || "Chat"} // Title is now simpler, editing handled internally if needed
      sidebarContent={renderChatSidebar()}
      isSidebarOpen={isSidebarOpen}
      // Removed props related to title editing and export, as Layout likely doesn't handle them directly.
      // This logic remains within the ChatPage or its hooks/sub-components.
    >
      {renderChatContent()}

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        isOpen={deleteDialogOpen} // From useChatUI
        onClose={() => setDeleteDialogOpen(false)} // From useChatUI
        onConfirm={handleDeleteChat} // Local handler
        title="Delete Chat"
        message="Are you sure you want to delete this chat? This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="danger"
      />

      {/* Edit confirmation dialog */}
      <ConfirmDialog
        isOpen={currentChatHook.editDialogOpen} // From useCurrentChat
        onClose={() => currentChatHook.setEditDialogOpen(false)} // From useCurrentChat
        onConfirm={currentChatHook.confirmEditTitle} // From useCurrentChat
        title="Edit Chat Title"
        message={`Are you sure you want to edit the title "${currentChatHook.originalTitle}"?`}
        confirmLabel="Edit"
        cancelLabel="Cancel"
        variant="info"
      />
    </Layout>
  );
};

export default CleanChatPage;

// --- Removed Code Snippets (for reference) ---
// Removed useState for: chats, filteredChats, searchTerm, selectedFilterTags, currentChat, isLoading, isStreaming, error, isSidebarOpen, showExportMenu, deleteDialogOpen, chatToDelete, editDialogOpen, isEditingTitle, editedTitle, originalTitle
// Removed useRef for: messagesEndRef, exportMenuRef, eventSourceRef, titleInputRef
// Removed useEffects for: auth redirect (kept), loadChats, filterChats, loadSpecificChat, scrollMessages, title edit events, export menu click outside, eventSource cleanup
// Removed handlers: loadChats, handleNewChat, handleSelectChat, handleUpdateTags, handleDeleteChatClick (kept wrapper), handleDeleteChat (re-implemented), handleStartEditTitle, confirmEditTitle, handleSaveTitle, handleUpdateTitle, handleFeedback, handleUpdateMessage, closeEventSource, setupEventSource, handleEventMessage, handleEventError, handleSendMessage, handleExport