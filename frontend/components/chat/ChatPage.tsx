import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/router';
import Layout from '@/components/layout/Layout';
import { Card, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { useAuth } from '@/contexts/AuthContext';
import { useNotification } from '@/contexts/NotificationContext';
import { Chat, Message } from '@/types';
import { getChats, createChat, getChat, deleteChat, submitFeedback, updateChatTags, updateChat, updateMessage } from '@/services/chat';
import { exportChat, ExportFormat } from '@/utils/exportUtils';
import { getApiUrl } from '@/services/api';
import { announce } from '@/utils/accessibilityUtils';

// Import our components
import ChatSidebar from '@/components/chat/ChatSidebar';
import ImprovedMessageContent from '@/components/chat/ImprovedMessageContent';
import ImprovedChatInput from '@/components/chat/ImprovedChatInput';
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
  
  // Listen for custom event to edit title from the Layout component
  useEffect(() => {
    const handleEditTitleEvent = (event: CustomEvent<{chatId: string}>) => {
      if (currentChat && currentChat.id === event.detail.chatId) {
        handleStartEditTitle();
      }
    };
    
    const handleEditCompletedEvent = (event: CustomEvent<{chatId: string, newTitle: string}>) => {
      if (currentChat && currentChat.id === event.detail.chatId) {
        // Update title in backend and state
        handleUpdateTitle(event.detail.newTitle);
      }
    };
    
    document.addEventListener('edit-chat-title', handleEditTitleEvent as EventListener);
    document.addEventListener('edit-chat-title-completed', handleEditCompletedEvent as EventListener);
    
    return () => {
      document.removeEventListener('edit-chat-title', handleEditTitleEvent as EventListener);
      document.removeEventListener('edit-chat-title-completed', handleEditCompletedEvent as EventListener);
    };
  }, [currentChat]);

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
    console.log('Updating tags for chat:', chatId, 'New tags:', tags);
    setError(null);
    
    // Optimistically update the UI immediately for a responsive feel
    setChats(prevChats => 
      prevChats.map(chat => 
        chat.id === chatId ? { ...chat, tags } : chat
      )
    );
    
    // Also update current chat if it's the one being tagged
    if (currentChat?.id === chatId) {
      setCurrentChat(prev => prev ? { ...prev, tags } : null);
    }
    
    try {
      // Use the service function to update tags
      const { success, error } = await updateChatTags(chatId, tags);
      
      if (success) {
        console.log('Tags updated successfully in the backend');
        
        // Get latest chat data from the backend after successful update
        await loadChats();
        
        // For the current chat, make sure we have the latest data with updated tags
        if (currentChat?.id === chatId) {
          console.log('Refreshing current chat to get updated tags');
          try {
            const { chat: refreshedChat } = await getChat(chatId);
            if (refreshedChat) {
              console.log('Successfully refreshed chat with updated tags:', refreshedChat.tags);
              // Preserve any data not returned from getChat
              setCurrentChat((prev) => {
                if (!prev) return refreshedChat;
                return { ...prev, ...refreshedChat };
              });
            }
          } catch (refreshError) {
            console.error('Error refreshing chat after tag update:', refreshError);
          }
        }
        
        showNotification('Tags updated successfully', 'success');
        
        // Remove updating-tags class from the chat element
        setTimeout(() => {
          const chatItem = document.querySelector(`[data-chat-id="${chatId}"]`);
          if (chatItem) {
            chatItem.classList.remove('updating-tags');
          }
        }, 300);
      } else {
        console.error('Failed to update tags:', error);
        setError(`Failed to update tags: ${error}`);
        showNotification(`Failed to update tags: ${error}`, 'error');
        
        // If the API call failed, rollback the optimistic update
        loadChats(); // Reload chats from the server to get the correct state
      }
    } catch (err) {
      console.error('Error updating tags:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to update tags: ${errorMessage}`);
      showNotification(`Failed to update tags: ${errorMessage}`, 'error');
      
      // If an exception occurred, rollback the optimistic update
      loadChats(); // Reload chats from the server to get the correct state
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
  
  // Update title directly (used by the Layout component)
  const handleUpdateTitle = async (newTitle: string) => {
    if (!currentChat || !newTitle.trim() || newTitle === currentChat.title) {
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const { success, error } = await updateChat(currentChat.id, { title: newTitle });
      
      if (success) {
        // Update chat in state
        setCurrentChat(prev => prev ? { ...prev, title: newTitle } : null);
        setChats(prevChats => 
          prevChats.map(chat => 
            chat.id === currentChat.id ? { ...chat, title: newTitle } : chat
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
      }
    } catch (err) {
      console.error('Error updating chat title:', err);
      setError('An unexpected error occurred while updating the chat title.');
    } finally {
      setIsLoading(false);
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

  // Handle updating a message
  const handleUpdateMessage = async (messageId: string, newContent: string): Promise<boolean> => {
    if (!currentChat) return false;
    
    try {
      const { message: updatedMessage, error } = await updateMessage(
        currentChat.id,
        messageId,
        newContent
      );
      
      if (error) {
        throw new Error(error);
      }
      
      // Update the message in the UI
      if (updatedMessage) {
        setCurrentChat(prev => {
          if (!prev) return null;
          
          return {
            ...prev,
            messages: prev.messages?.map(msg =>
              String(msg.id) === messageId ? { ...msg, content: newContent } : msg
            )
          };
        });
        
        return true;
      }
      
      return false;
    } catch (err) {
      console.error('Error updating message:', err);
      setError('Failed to update message');
      return false;
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

  const handleSendMessage = async (messageContent: string, contextDocuments?: string[]) => {
    if (isStreaming) return;
    setError(null); // Clear any previous errors

    // Create new chat if none exists
    let chat = currentChat;
    if (!chat) {
      setIsLoading(true); // Show loading state
      
      // Start with default title "New Conversation"
      const { chat: newChat, error: createError } = await createChat("New Conversation");
      
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
      context_documents: contextDocuments // Add context documents if provided
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

      // Check if this is the first user message and update title if needed
      if (chat.title === "New Conversation") {
        // Create a new title from the message content
        const newTitle = messageContent.length > 30 
          ? `${messageContent.substring(0, 30)}...` 
          : messageContent;
        
        console.log('Updating chat title based on first message:', newTitle);
        const updateResult = await updateChat(chat.id, { title: newTitle });
        
        if (updateResult.success) {
          // Update the title in the current state
          setCurrentChat(prev => prev ? { ...prev, title: newTitle } : null);
        }
      }
      
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
      
      // Prepare query params including context documents if provided
      let streamUrl = `/chats/${chat.id}/stream?content=${encodeURIComponent(messageContent)}`;
      
      // Add context documents if available
      if (contextDocuments && contextDocuments.length > 0) {
        const contextParam = contextDocuments.join(',');
        streamUrl += `&context_documents=${encodeURIComponent(contextParam)}`;
      }
      
      // Set up EventSource
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      
      streamUrl += `&token=${encodeURIComponent(token)}&_=${Date.now()}`;
      
      const eventSource = new EventSource(getApiUrl(streamUrl, false));
      eventSourceRef.current = eventSource;
      
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
      <div className="flex flex-col h-full min-h-0">
        {/* We're removing the extra title and divider as per requirements */}
        {/* The title is already shown in the Layout component */}



        {/* Chat Messages */}
        <div className="flex-grow overflow-y-auto p-4 min-h-0" aria-live="polite">
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
                    
                    {/* Removed thumbs up/down buttons from the top of messages */}
                  </div>
                  
                  <ImprovedMessageContent content={message.content} message={message} onUpdateMessage={handleUpdateMessage} />
                  
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
        <ImprovedChatInput
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
        message={`Are you sure you want to edit the title "${originalTitle}"?`}
        confirmLabel="Edit"
        cancelLabel="Cancel"
        variant="info"
      />
    </Layout>
  );
};

export default CleanChatPage;