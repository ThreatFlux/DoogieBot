import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/router';
import Layout from '@/components/layout/Layout';
import { Card, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { useAuth } from '@/contexts/AuthContext';
import { useNotification } from '@/contexts/NotificationContext';
import { Chat, Message } from '@/types';
import { getChats, createChat, getChat, deleteChat, submitFeedback, updateChatTags, updateChat } from '@/services/chat';
import { exportChat, ExportFormat } from '@/utils/exportUtils';
import { getApiUrl } from '@/services/api';
import { announce } from '@/utils/accessibilityUtils';
import ChatInput from "@/components/chat/ChatInput";


// Import our components
import ChatSidebar from '@/components/chat/ChatSidebar';
import MessageContent from '@/components/chat/MessageContent';
import { FeedbackType } from '@/components/chat/FeedbackButton';
import DocumentReferences from '@/components/chat/DocumentReferences';

export const CleanChatPage = () => {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const { showNotification } = useNotification();
  const router = useRouter();
  
  // State
  const [chats, setChats] = useState<Chat[]>([]);
  const [filteredChats, setFilteredChats] = useState<Chat[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFilterTags, setSelectedFilterTags] = useState<string[]>([]);
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [showExportMenu, setShowExportMenu] = useState(false);
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const exportMenuRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);
  
  // Confirmation dialog states
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [chatToDelete, setChatToDelete] = useState<string | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  
  // Edit title state
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editedTitle, setEditedTitle] = useState('');
  const [originalTitle, setOriginalTitle] = useState('');

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load chats function
  const loadChats = async () => {
    if (!isAuthenticated) return;
    
    try {
      const { chats, error } = await getChats();
      if (chats) {
        setChats(chats);
        setFilteredChats(chats);
      } else if (error) {
        setError(`Failed to load chats: ${error}`);
      } else {
        // If no chats data and no error, set empty array
        setChats([]);
        setFilteredChats([]);
      }
    } catch (err) {
      console.error('Error loading chats:', err);
      setError('An unexpected error occurred while loading chats.');
      // Ensure chats is initialized to an empty array on error
      setChats([]);
      setFilteredChats([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Load chats on mount and when auth changes
  useEffect(() => {
    loadChats();
  }, [isAuthenticated]);
  
  // Filter chats when search term, tags, or chats change
  useEffect(() => {
    let filtered = [...chats];
    
    // Filter by search term if present
    if (searchTerm.trim()) {
      const lowerCaseSearchTerm = searchTerm.toLowerCase();
      filtered = filtered.filter(chat => 
        chat.title.toLowerCase().includes(lowerCaseSearchTerm)
      );
    }
    
    // Filter by selected tags if any
    if (selectedFilterTags.length > 0) {
      filtered = filtered.filter(chat => 
        chat.tags && selectedFilterTags.some(tag => chat.tags?.includes(tag))
      );
    }
    
    setFilteredChats(filtered);
  }, [searchTerm, selectedFilterTags, chats]);

  // Load chat if ID is in URL
  useEffect(() => {
    const chatId = router.query.id ? String(router.query.id) : null;
    
    const loadChat = async () => {
      if (!chatId || !isAuthenticated) return;
      
      try {
        const { chat, error } = await getChat(chatId);
        if (chat) {
          setCurrentChat(chat);
        } else if (error) {
          setError(`Failed to load chat: ${error}`);
        }
      } catch (err) {
        console.error('Error loading chat:', err);
        setError('An unexpected error occurred while loading the chat.');
      }
    };

    loadChat();
  }, [router.query.id, isAuthenticated, router]);

  // Scroll to bottom when messages change or during streaming
  useEffect(() => {
    // Use a small timeout to ensure the DOM has updated before scrolling
    const scrollTimeout = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({
        behavior: isStreaming ? 'auto' : 'smooth',
        block: 'end'
      });
    }, 10);
    
    return () => clearTimeout(scrollTimeout);
  }, [currentChat?.messages, isStreaming]);

  const handleNewChat = async () => {
    // Clear all relevant state
    setCurrentChat(null);
    setError(null);
    setIsStreaming(false);
    // Create a new chat first with a default title
    try {
      console.log('Creating new chat...');
      const { chat: newChat, error: createError } = await createChat('New Conversation');
      
      if (newChat) {
        console.log('New chat created successfully:', newChat);
        // Force a re-render with the new chat
        router.push(`/chat?id=${newChat.id}`, undefined, { shallow: true });
        // Refresh the chat list to include the new chat
        await loadChats();
        
        // Announce success for screen readers
        announce({ 
          message: 'New chat created successfully', 
          politeness: 'polite' 
        });
      } else {
        setError(createError || 'Failed to create new chat');
        showNotification(createError || 'Failed to create new chat', 'error');
        // Still clear current chat to show empty state
        router.push('/chat', undefined, { shallow: true });
      }
    } catch (err) {
      console.error('Error creating new chat:', err);
      setError('An unexpected error occurred while creating a new chat');
      // Still clear current chat to show empty state
      router.push('/chat', undefined, { shallow: true });
    }
  };

  const handleSelectChat = (chat: Chat) => {
    router.push(`/chat?id=${chat.id}`, undefined, { shallow: true });
    // Auto-close sidebar on mobile
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
    
    // Announce for screen readers
    announce({ 
      message: `Selected chat: ${chat.title}`, 
      politeness: 'polite' 
    });
  };

  // Handle updating chat tags
  const handleUpdateTags = async (chatId: string, tags: string[]) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const { success, error } = await updateChatTags(chatId, tags);
      
      if (success) {
        // Update the chat in local state
        setChats(prevChats => 
          prevChats.map(chat => 
            chat.id === chatId ? { ...chat, tags } : chat
          )
        );
        
        // If it's the current chat, update that too
        if (currentChat?.id === chatId) {
          setCurrentChat(prev => prev ? { ...prev, tags } : null);
        }
        
        showNotification('Tags updated successfully', 'success');
      } else {
        setError(`Failed to update tags: ${error}`);
        showNotification(`Failed to update tags: ${error}`, 'error');
      }
    } catch (err) {
      console.error('Error updating tags:', err);
      setError('An unexpected error occurred while updating tags.');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle opening the delete confirmation dialog
  const handleDeleteChatClick = (chatId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setChatToDelete(chatId);
    setDeleteDialogOpen(true);
  };
  
  // Handle actual deletion after confirmation
  const handleDeleteChat = async () => {
    if (!chatToDelete) return;
    
    console.log('Deleting chat:', chatToDelete);
    setIsLoading(true);
    setError(null);
    
    try {
      // Optimistically remove the chat from the UI
      setChats(prevChats => prevChats.filter(chat => chat.id !== chatToDelete));
      
      const { success, error } = await deleteChat(chatToDelete);
      
      if (success) {
        console.log('Delete successful, updating UI...');
        if (currentChat?.id === chatToDelete) {
          console.log('Current chat was deleted, redirecting...');
          setCurrentChat(null);
          router.push('/chat', undefined, { shallow: true });
        }
        // Reload the full list to ensure consistency
        await loadChats();
        
        showNotification('Chat deleted successfully', 'success');
        
        // Announce for screen readers
        announce({ 
          message: 'Chat deleted successfully', 
          politeness: 'polite' 
        });
      } else {
        console.error('Delete failed with error:', error);
        setError(`Failed to delete chat: ${error}`);
        showNotification(`Failed to delete chat: ${error}`, 'error');
        // Restore the chat list since deletion failed
        await loadChats();
      }
    } catch (err) {
      console.error('Error deleting chat:', err);
      setError('An unexpected error occurred while deleting the chat.');
      // Restore the chat list since deletion failed
      await loadChats();
    } finally {
      setIsLoading(false);
      setChatToDelete(null);
      setDeleteDialogOpen(false);
    }
  };
  
  // Start editing the chat title by opening the confirmation dialog
  const handleStartEditTitle = () => {
    if (currentChat) {
      setOriginalTitle(currentChat.title);
      setEditedTitle(currentChat.title);
      setEditDialogOpen(true);
    }
  };
  
  // Start actual title editing after confirmation
  const confirmEditTitle = () => {
    setEditDialogOpen(false);
    setIsEditingTitle(true);
    // Focus on the input after rendering
    setTimeout(() => {
      titleInputRef.current?.focus();
      titleInputRef.current?.select();
    }, 50);
  };
  
  // Save the edited chat title
  const handleSaveTitle = async () => {
    if (!currentChat || !editedTitle.trim()) {
      setIsEditingTitle(false);
      return;
    }
    
    if (editedTitle === currentChat.title) {
      setIsEditingTitle(false);
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const { success, error } = await updateChat(currentChat.id, { title: editedTitle });
      
      if (success) {
        // Update chat in state
        setCurrentChat(prev => prev ? { ...prev, title: editedTitle } : null);
        setChats(prevChats => 
          prevChats.map(chat => 
            chat.id === currentChat.id ? { ...chat, title: editedTitle } : chat
          )
        );
        
        showNotification('Chat title updated successfully', 'success');
        
        // Announce for screen readers
        announce({ 
          message: 'Chat title updated successfully', 
          politeness: 'polite' 
        });
      } else {
        setError(`Failed to update title: ${error}`);
        showNotification(`Failed to update title: ${error}`, 'error');
        // Reset to original title
        setEditedTitle(currentChat.title);
      }
    } catch (err) {
      console.error('Error updating chat title:', err);
      setError('An unexpected error occurred while updating the chat title.');
    } finally {
      setIsLoading(false);
      setIsEditingTitle(false);
    }
  };

  const handleFeedback = async (messageId: string, feedback: FeedbackType, feedbackText?: string) => {
    try {
      const { message: updatedMessage, error: feedbackError } = await submitFeedback(
        String(currentChat?.id),
        messageId,
        feedback,
        feedbackText
      );

      if (feedbackError) {
        throw new Error(feedbackError);
      }

      // Update the message in the UI
      setCurrentChat(prev => {
        if (!prev) return null;
        return {
          ...prev,
          messages: prev.messages?.map(msg =>
            String(msg.id) === messageId
              ? { ...msg, feedback, feedback_text: feedbackText }
              : msg
          )
        };
      });
      
      showNotification('Feedback submitted successfully', 'success');
      
      // Announce for screen readers
      announce({ 
        message: 'Feedback submitted successfully', 
        politeness: 'polite' 
      });
    } catch (err) {
      console.error('Error submitting feedback:', err);
      setError('Failed to submit feedback');
    }
  };

  // Function to close any existing EventSource
  const closeEventSource = useCallback(() => {
    if (eventSourceRef.current) {
      console.log('Closing existing EventSource connection');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);
  
  // Clean up EventSource on unmount
  useEffect(() => {
    return () => {
      closeEventSource();
    };
  }, [closeEventSource]);

  // Handle clicking outside the export menu
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target as Node)) {
        setShowExportMenu(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Set up EventSource for streaming
  const setupEventSource = (chatId: string, content: string) => {
    // Close any existing EventSource
    closeEventSource();
    
    // Get token for authentication
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('No authentication token found');
    }

    // Create URL with cache-busting parameter
    const timestamp = Date.now();
    const streamUrl = getApiUrl(
      `/chats/${chatId}/stream?content=${encodeURIComponent(content)}&token=${encodeURIComponent(token)}&_=${timestamp}`,
      false
    );
    
    console.log('Setting up EventSource connection to:', streamUrl);
    
    // Create EventSource
    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;
    
    return eventSource;
  };

  // Handle incoming EventSource messages
  const handleEventMessage = (event: MessageEvent) => {
    try {
      // Log only basic info to reduce console noise
      console.log('Received event data:', event.data.substring(0, 50) + '...');
      
      const data = JSON.parse(event.data);
      
      // Check for error condition
      if (data.error) {
        setError(data.content || 'An error occurred during streaming');
        closeEventSource();
        setIsStreaming(false);
        return;
      }
      
      // Force a refresh of the current chat to ensure we have the latest state
      setCurrentChat((prev) => {
        if (!prev) return prev;
        // Find the last assistant message (searching from the end of the array)
        const messages = prev.messages || [];
        let lastAssistantIndex = -1;
        
        // Search from the end of the array to find the last assistant message
        for (let i = messages.length - 1; i >= 0; i--) {
          if (messages[i].role === 'assistant') {
            lastAssistantIndex = i;
            break;
          }
        }
        
        if (lastAssistantIndex === -1) return prev;
        
        // Create a new messages array with the updated content
        const updatedMessages = [...messages];
        
        // Update the assistant message with the new content from the server
        // The backend sends the full content in each chunk, not just the delta
        updatedMessages[lastAssistantIndex] = {
          ...updatedMessages[lastAssistantIndex],
          content: data.content,
          tokens: data.tokens,
          tokens_per_second: data.tokens_per_second,
          model: data.model,
          provider: data.provider
        };
        
        // Return a new chat object with the updated messages
        return {
          ...prev,
          messages: updatedMessages
        };
      });
      
      // If this is the final chunk, complete the process
      if (data.done) {
        console.log('Received final chunk, closing EventSource');
        closeEventSource();
        setIsStreaming(false);
        
        // Refresh the chat list to ensure the chat appears with the correct title
        loadChats();
        
        // Refresh the current chat to ensure we have the latest messages from the database
        if (currentChat) {
          console.log('Refreshing current chat from database');
          const refreshChat = async () => {
            try {
              const { chat: refreshedChat } = await getChat(currentChat.id);
              if (refreshedChat) {
                setCurrentChat(refreshedChat);
              }
            } catch (err) {
              console.error('Error refreshing chat:', err);
            }
          };
          refreshChat();
        }
        
        showNotification('Response completed successfully', 'success');
        
        // Announce for screen readers
        announce({ 
          message: 'Response completed successfully', 
          politeness: 'polite' 
        });
      }
    } catch (e) {
      console.error('Error processing event data:', e);
      console.error('Raw event data:', event.data);
      setError('Error processing streaming response');
      closeEventSource();
      setIsStreaming(false);
    }
  };

  // Handle EventSource errors
  const handleEventError = (error: Event) => {
    console.error('EventSource error:', error);
    
    // Get the current state of the EventSource
    const eventSource = eventSourceRef.current;
    if (!eventSource) return;
    
    console.error('EventSource readyState:', eventSource.readyState);
    
    let errorMessage = 'Connection error during streaming.';
    
    // Simple error handling without complex retry logic
    if (eventSource.readyState === EventSource.CLOSED) {
      errorMessage = 'Connection closed unexpectedly. Please try again.';
    }
    
    setError(errorMessage);
    showNotification(errorMessage, 'error');
    closeEventSource();
    setIsStreaming(false);
  };

  const handleSendMessage = async (messageContent: string) => {
    if (isStreaming) return;
    setError(null); // Clear any previous errors

    // Create new chat if none exists
    let chat = currentChat;
    if (!chat) {
      setIsLoading(true); // Show loading state
      console.log('No current chat, creating new one with title:', messageContent.slice(0, 30));
      
      const title = messageContent.slice(0, 30) + (messageContent.length > 30 ? '...' : '');
      const { chat: newChat, error: createError } = await createChat(title);
      
      setIsLoading(false); // Hide loading state
      
      if (!newChat) {
        const errorMsg = createError || 'Failed to create chat';
        console.error('Chat creation failed:', errorMsg);
        setError(errorMsg);
        showNotification(errorMsg, 'error');
        return;
      }
      
      console.log('New chat created successfully:', newChat);
      chat = newChat;
      setCurrentChat(chat);

      // Ensure the URL is updated with the new chat ID
      router.push(`/chat?id=${chat.id}`, undefined, { shallow: true });

      // Wait a moment for the router to update
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    // Add user message to UI immediately
    const userMessage: Message = {
      id: Date.now(),
      chat_id: typeof chat.id === 'string' ? parseInt(chat.id, 10) : chat.id,
      role: 'user' as const,
      content: messageContent,
      created_at: new Date().toISOString(),
    };

    setCurrentChat(prev => ({
      ...(prev || chat),
      messages: (prev || chat).messages ? [...(prev || chat).messages, userMessage] : [userMessage],
    }));

    // Set streaming state
    setIsStreaming(true);
    setError(null);
    
    // Create placeholder for assistant response
    const assistantMessage: Message = {
      id: Date.now() + 1,
      chat_id: typeof chat.id === 'string' ? parseInt(chat.id, 10) : chat.id,
      role: 'assistant' as const,
      content: '',
      created_at: new Date().toISOString(),
    };

    setCurrentChat(prev => ({
      ...(prev || chat),
      messages: (prev || chat).messages ? [...(prev || chat).messages, assistantMessage] : [assistantMessage],
    }));
    
    // Force scroll to bottom immediately after adding the assistant message placeholder
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({
        behavior: 'auto',
        block: 'end'
      });
    }, 10);

    try {
      // Refresh chat list to show new chat with correct title
      await loadChats();
      
      // Ensure we have the latest chat state
      if (!currentChat || currentChat.id !== chat.id) {
        const { chat: refreshedChat } = await getChat(chat.id);
        if (refreshedChat) {
          // Keep our newly added messages
          refreshedChat.messages = refreshedChat.messages || [];
          if (refreshedChat.messages.length === 0) {
            refreshedChat.messages = [userMessage, assistantMessage];
          }
          setCurrentChat(refreshedChat);
        }
      }
      
      // Set up EventSource
      const eventSource = setupEventSource(chat.id, messageContent);
      
      // Set up event handlers
      eventSource.onmessage = handleEventMessage;
      eventSource.onerror = handleEventError;
      
      // Announce for screen readers
      announce({ 
        message: 'Message sent, waiting for response', 
        politeness: 'polite' 
      });
    } catch (err) {
      console.error('Error sending message:', err);
      const errorMessage = 'An unexpected error occurred while sending your message.';
      setError(errorMessage);
      showNotification(errorMessage, 'error');
      setIsStreaming(false);
    }
  };
  
  // Handle export button click
  const handleExport = (format: ExportFormat) => {
    if (currentChat) {
      exportChat(currentChat, format);
      setShowExportMenu(false);
      showNotification(`Chat exported successfully as ${format}`, 'success');
      
      // Announce for screen readers
      announce({ 
        message: `Chat exported successfully as ${format}`, 
        politeness: 'polite' 
      });
    }
  };
  
  // Render chat sidebar content 
  const renderChatSidebar = () => (
    <ChatSidebar
      chats={chats}
      filteredChats={filteredChats}
      searchTerm={searchTerm}
      selectedFilterTags={selectedFilterTags}
      onSearchChange={setSearchTerm}
      onSelectedTagsChange={setSelectedFilterTags}
      onSelectChat={handleSelectChat}
      onNewChat={handleNewChat}
      onDeleteChat={handleDeleteChatClick}
      onUpdateTags={handleUpdateTags}
    />
  );

  // Render chat content
  const renderChatContent = () => {
    if (!isAuthenticated) {
      return (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-500 dark:text-gray-400">Loading...</p>
        </div>
      );
    }

    if (!currentChat) {
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
                onClick={handleNewChat}
              >
                Start a new conversation
              </button>
            </CardContent>
          </Card>
        </div>
      );
    }

    return (
      <div className="flex flex-col h-full">
        {/* Chat header */}
        <div className="flex-none p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            {isEditingTitle ? (
              <div className="flex-grow">
                <Input
                  ref={titleInputRef}
                  value={editedTitle}
                  onChange={(e) => setEditedTitle(e.target.value)}
                  onBlur={handleSaveTitle}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleSaveTitle();
                    } else if (e.key === 'Escape') {
                      setIsEditingTitle(false);
                    }
                  }}
                  className="font-bold text-lg"
                />
              </div>
            ) : (
              <h1 
                className="text-lg font-bold cursor-pointer hover:text-primary-600 dark:hover:text-primary-400 mr-2 flex-grow"
                onClick={handleStartEditTitle}
                title="Click to edit title"
                role="button"
                tabIndex={0}
                aria-label={`Edit chat title: ${currentChat.title}`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    handleStartEditTitle();
                  }
                }}
              >
                {currentChat.title}
              </h1>
            )}

            <div className="flex space-x-2">
              {/* Export button */}
              <button
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                onClick={() => setShowExportMenu(!showExportMenu)}
                aria-label="Export chat"
                title="Export chat"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
              
              {showExportMenu && (
                <div 
                  ref={exportMenuRef}
                  className="absolute right-0 mt-10 w-48 bg-white dark:bg-gray-800 shadow-lg rounded-md z-10 py-1"
                  role="menu"
                  aria-orientation="vertical"
                  aria-labelledby="export-menu-button"
                >
                  <button
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    onClick={() => handleExport(ExportFormat.JSON)}
                    role="menuitem"
                  >
                    Export as JSON
                  </button>
                  <button
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    onClick={() => handleExport(ExportFormat.MD)}
                    role="menuitem"
                  >
                    Export as Markdown
                  </button>
                  <button
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    onClick={() => handleExport(ExportFormat.TXT)}
                    role="menuitem"
                  >
                    Export as Text
                  </button>
                </div>
              )}

              {/* Delete button */}
              <button
                className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                onClick={() => handleDeleteChatClick(currentChat.id)}
                aria-label="Delete chat"
                title="Delete chat"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-grow overflow-y-auto p-4" aria-live="polite">
          {error && (
            <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-md flex items-start" role="alert">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {currentChat.messages && currentChat.messages.length > 0 ? (
            <div className="space-y-4">
              {currentChat.messages.map((message, index) => (
                <div
                  key={message.id}
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
                          {new Date(message.created_at).toLocaleTimeString([], {
                            hour: '2-digit', 
                            minute: '2-digit'
                          })}
                        </span>
                      )}
                      {message.tokens && message.role === 'assistant' && (
                        <span className="ml-2 font-normal text-xs">
                          {message.tokens} tokens
                        </span>
                      )}
                    </span>
                    
                    {message.role === 'assistant' && (
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => handleFeedback(String(message.id), 'positive')}
                          className="p-1 text-green-500 hover:bg-green-100 dark:hover:bg-green-900/30 rounded"
                          aria-label="Mark as helpful"
                          title="Helpful"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                            <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleFeedback(String(message.id), 'negative')}
                          className="p-1 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                          aria-label="Mark as not helpful"
                          title="Not helpful"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                            <path d="M18 9.5a1.5 1.5 0 11-3 0v-6a1.5 1.5 0 013 0v6zM14 9.667v-5.43a2 2 0 00-1.105-1.79l-.05-.025A4 4 0 0011.055 2H5.64a2 2 0 00-1.962 1.608l-1.2 6A2 2 0 004.44 12H8v4a2 2 0 002 2 1 1 0 001-1v-.667a4 4 0 01.8-2.4l1.4-1.866a4 4 0 00.8-2.4z" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </div>
                  
                  <MessageContent content={message.content} message={message} />
                  
                  {message.role === 'assistant' && message.document_ids && message.document_ids.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Sources
                      </h4>
                      <DocumentReferences documentIds={message.document_ids} />
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p className="text-gray-500 dark:text-gray-400 mb-2">
                No messages yet
              </p>
              <p className="text-sm text-gray-400 dark:text-gray-500 max-w-md">
                Start by typing a message below. Doogie will respond using the knowledge from your documents.
              </p>
            </div>
          )}
        </div>

        {/* Chat Input */}
        <ChatInput
          onSendMessage={handleSendMessage}
          isStreaming={isStreaming}
          disabled={!currentChat || isStreaming}
        />
      </div>
    );
  };

  return (
    <Layout 
      title={currentChat?.title || "Chat"} 
      sidebarContent={renderChatSidebar()}
      isSidebarOpen={isSidebarOpen}
    >
      {renderChatContent()}
      
      {/* Delete confirmation dialog */}
      <ConfirmDialog
        isOpen={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleDeleteChat}
        title="Delete Chat"
        message="Are you sure you want to delete this chat? This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="danger"
      />
      
      {/* Edit confirmation dialog */}
      <ConfirmDialog
        isOpen={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        onConfirm={confirmEditTitle}
        title="Edit Chat Title"
        message={`Are you sure you want to edit the title of "${originalTitle}"?`}
        confirmLabel="Edit"
        cancelLabel="Cancel"
        variant="info"
      />
    </Layout>
  );
};

export default CleanChatPage;