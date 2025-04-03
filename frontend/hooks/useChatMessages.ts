import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/router';
import { Chat, Message } from '@/types';
import { submitFeedback, updateMessage, createChat, updateChat, getChat } from '@/services/chat';
import { getApiUrl } from '@/services/api';
import { useAuth } from '@/contexts/AuthContext';
import { useNotification } from '@/contexts/NotificationContext';
import { announce } from '@/utils/accessibilityUtils';
import { FeedbackType } from '@/components/chat/FeedbackButton'; // Assuming FeedbackType is defined here

export interface UseChatMessagesReturn {
  isStreaming: boolean;
  isWaitingForResponse: boolean; // Expose new state
  error: string | null; // Error specific to messaging
  messagesEndRef: React.RefObject<HTMLDivElement>;
  handleSendMessage: (messageContent: string, contextDocuments?: string[]) => Promise<void>;
  handleFeedback: (messageId: string, feedback: FeedbackType, feedbackText?: string) => Promise<void>;
  handleUpdateMessage: (messageId: string, newContent: string) => Promise<boolean>;
  closeEventSource: () => void; // Expose close function if needed externally
}

export const useChatMessages = (
  currentChat: Chat | null,
  setCurrentChat: React.Dispatch<React.SetStateAction<Chat | null>>,
  // Pass setChats to update list when title changes on first message
  setChats: React.Dispatch<React.SetStateAction<Chat[]>>,
  // Pass loadChats to refresh list after streaming completes or new chat created
  loadChats: () => Promise<void>
): UseChatMessagesReturn => {
  const { isAuthenticated } = useAuth();
  const { showNotification } = useNotification();
  const router = useRouter();

  
    const [isStreaming, setIsStreaming] = useState(false);
    const [isWaitingForResponse, setIsWaitingForResponse] = useState(false); // New state for initial wait
    const [error, setError] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const eventSourceRef = useRef<EventSource | null>(null);
  
  const closeEventSource = useCallback(() => {
    if (eventSourceRef.current) {
      console.log('Closing existing EventSource connection');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  // Clean up EventSource on unmount or when chat changes significantly
  useEffect(() => {
    return () => {
      closeEventSource();
    };
  }, [closeEventSource, currentChat?.id]); // Close if chat ID changes

  // Scroll to bottom when messages change or during streaming
  useEffect(() => {
    const scrollTimeout = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({
        behavior: isStreaming ? 'auto' : 'smooth',
        block: 'end'
      });
    }, 100); // Increased timeout slightly

    return () => clearTimeout(scrollTimeout);
  }, [currentChat?.messages, isStreaming]);


  const handleFeedback = async (messageId: string, feedback: FeedbackType, feedbackText?: string) => {
    if (!currentChat) return;
    setError(null);
    try {
      const { message: updatedMessage, error: feedbackError } = await submitFeedback(
        String(currentChat.id),
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
      announce({ message: 'Feedback submitted successfully', politeness: 'polite' });
    } catch (err) {
      console.error('Error submitting feedback:', err);
      const errorMsg = err instanceof Error ? err.message : 'Failed to submit feedback';
      setError(errorMsg);
      showNotification(errorMsg, 'error');
    }
  };

  const handleUpdateMessage = async (messageId: string, newContent: string): Promise<boolean> => {
    if (!currentChat) return false;
    setError(null);
    try {
      const { message: updatedMessage, error: updateError } = await updateMessage(
        currentChat.id,
        messageId,
        newContent
      );

      if (updateError) {
        throw new Error(updateError);
      }

      // Update the message in the UI
      if (updatedMessage) {
        setCurrentChat(prev => {
          if (!prev) return null;
          return {
            ...prev,
            messages: prev.messages?.map(msg =>
              String(msg.id) === messageId ? { ...updatedMessage } : msg // Use the full updated message from backend
            )
          };
        });
        showNotification('Message updated successfully', 'success');
        return true;
      }
      return false;
    } catch (err) {
      console.error('Error updating message:', err);
      const errorMsg = err instanceof Error ? err.message : 'Failed to update message';
      setError(errorMsg);
      showNotification(errorMsg, 'error');
      return false;
    }
  };

  // Set up EventSource for streaming
  const setupEventSource = (chatId: string, content: string, contextDocuments?: string[]) => {
    closeEventSource(); // Ensure previous connection is closed

    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('No authentication token found');
    }

    let streamUrl = `/chats/${chatId}/stream?content=${encodeURIComponent(content)}`;
    if (contextDocuments && contextDocuments.length > 0) {
        const contextParam = contextDocuments.join(',');
        streamUrl += `&context_documents=${encodeURIComponent(contextParam)}`;
    }
    streamUrl += `&token=${encodeURIComponent(token)}&_=${Date.now()}`; // Cache buster

    const fullUrl = getApiUrl(streamUrl, false); // useBaseUrl = false for EventSource
    console.log('Setting up EventSource connection to:', fullUrl);

    const eventSource = new EventSource(fullUrl);
    eventSourceRef.current = eventSource;
    return eventSource;
  };

  // Handle incoming EventSource messages
  const handleEventMessage = (event: MessageEvent) => {
    try {
      // console.log('Received event data:', event.data.substring(0, 100) + '...'); // Log less verbosely
      const data = JSON.parse(event.data);

      // Clear waiting state on first received chunk
      if (isWaitingForResponse) {
        setIsWaitingForResponse(false);
      }

      if (data.error) {
        setError(data.content || 'An error occurred during streaming');
        closeEventSource();
        setIsStreaming(false);
        return;
      }

      // Update the last assistant message content
      setCurrentChat((prev) => {
        if (!prev || !prev.messages) return prev;

        const updatedMessages = [...prev.messages];
        const lastAssistantIndex = updatedMessages.findLastIndex(msg => msg.role === 'assistant');

        if (lastAssistantIndex !== -1) {
          // Update the existing placeholder or last assistant message
          updatedMessages[lastAssistantIndex] = {
            ...updatedMessages[lastAssistantIndex],
            content: data.content, // Backend sends full content
            tokens: data.tokens,
            tokens_per_second: data.tokens_per_second,
            model: data.model,
            provider: data.provider,
            // Update document_ids if they arrive during streaming
            document_ids: data.document_ids || updatedMessages[lastAssistantIndex].document_ids,
            // Update id if it wasn't set before (e.g., placeholder) or if backend provides it
            id: data.id || updatedMessages[lastAssistantIndex].id,
            // Update created_at if backend provides it
            created_at: data.created_at || updatedMessages[lastAssistantIndex].created_at,
          };
        } else {
          // Should not happen if placeholder was added, but handle defensively
          console.error("Streaming update: Couldn't find last assistant message to update.");
        }

        return { ...prev, messages: updatedMessages };
      });

      if (data.done) {
        console.log('Received final chunk.');
        closeEventSource();
        setIsStreaming(false);
        // Refresh the chat list to ensure title/timestamp updates are reflected
        loadChats();
        // Refresh the current chat to get final message IDs and potentially other updates
        if (currentChat?.id) {
          const chatIdToRefresh = currentChat.id; // Capture ID before potential state changes
          getChat(chatIdToRefresh).then(result => {
            const fetchedChat = result.chat; // Assign to a constant first
            if (fetchedChat) { // Check the constant
              console.log('Refreshed current chat data from backend:', fetchedChat.id);
              setCurrentChat((prevChat): Chat | null => { // Explicitly define return type
                // If there's no previous chat, or the ID doesn't match the fetched chat,
                // use the newly fetched chat directly. fetchedChat is guaranteed non-null here.
                if (!prevChat || prevChat.id !== fetchedChat.id) { // Use the constant
                  return fetchedChat; // Use the constant
                }

                // --- If we are here, prevChat exists and IDs match. Merge messages. ---

                // Create a map of previous messages for efficient lookup
                const prevMessagesMap = new Map(prevChat.messages?.map(msg => [msg.id, msg]));

                // Ensure fetched messages is an array
                const fetchedMessages = fetchedChat.messages || []; // Use the constant

                // Map over fetched messages and merge with previous ones if necessary
                const finalMessages = fetchedMessages.map(fetchedMsg => {
                  const prevMsg = prevMessagesMap.get(fetchedMsg.id);

                  // If a previous message exists and it's an assistant message, merge token data
                  if (prevMsg && prevMsg.role === 'assistant') {
                    return {
                      ...fetchedMsg, // Start with the fetched message data
                      // Keep token info from prev state ONLY if missing in fetched state
                      tokens: fetchedMsg.tokens ?? prevMsg.tokens,
                      tokens_per_second: fetchedMsg.tokens_per_second ?? prevMsg.tokens_per_second,
                    };
                  }

                  // Otherwise (no previous message, or not an assistant message), use the fetched message as is
                  return fetchedMsg;
                });

                // Construct the final state: Start with prevChat, overlay fetched data (like updated_at),
                // and use the merged messages array. This ensures we return a valid Chat object.
                const updatedChat: Chat = {
                    ...prevChat,      // Base is the previous state
                    ...fetchedChat,   // Use the constant to overlay fields (e.g., updated_at)
                    messages: finalMessages, // Use the carefully merged messages
                };
                return updatedChat; // Return the correctly typed Chat object
              });
            } else {
              console.error('Failed to refresh chat after streaming:', result.error);
              showNotification(`Failed to refresh chat details: ${result.error}`, 'error');
            }
          });
        }
        showNotification('Response completed successfully', 'success');
        announce({ message: 'Response completed successfully', politeness: 'polite' });
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
    const eventSource = eventSourceRef.current;
    let errorMessage = 'Connection error during streaming.';
    if (eventSource && eventSource.readyState === EventSource.CLOSED) {
      errorMessage = 'Connection closed unexpectedly. Please try again.';
    }
    setError(errorMessage);
    showNotification(errorMessage, 'error');
    closeEventSource();
    setIsStreaming(false);
  };


  const handleSendMessage = async (messageContent: string, contextDocuments?: string[]) => {
    if (isStreaming || !isAuthenticated) return;
    setError(null);

    let chatId = currentChat?.id;
    let chatToUpdate = currentChat;

    // 1. Create new chat if necessary
    if (!chatToUpdate) {
      try {
        // Start with default title, will be updated later
        const { chat: newChat, error: createError } = await createChat("New Conversation");
        if (!newChat) {
          const errorMsg = createError || 'Failed to create chat';
          setError(errorMsg);
          showNotification(errorMsg, 'error');
          return;
        }
        chatToUpdate = newChat;
        chatId = newChat.id;
        setCurrentChat(chatToUpdate); // Set the newly created chat as current
        router.push(`/chat?id=${chatId}`, undefined, { shallow: true });
        await loadChats(); // Refresh list to show the new chat
        // Wait a moment for state/router updates
        await new Promise(resolve => setTimeout(resolve, 50));
      } catch (err) {
        console.error('Error creating new chat during send:', err);
        setError('Failed to initiate chat.');
        showNotification('Failed to initiate chat.', 'error');
        return;
      }
    }

    if (!chatId || !chatToUpdate) {
        setError('Chat session not available.');
        return;
    }

    // 2. Add user message optimistically
    const userMessage: Message = {
      id: -Date.now(), // Temporary ID (negative number)
      chat_id: typeof chatId === 'string' ? parseInt(chatId, 10) : chatId,
      role: 'user' as const,
      content: messageContent,
      created_at: new Date().toISOString(),
      context_documents: contextDocuments
    };

    // 3. Add assistant placeholder message optimistically
    const assistantMessage: Message = {
      id: -(Date.now() + 1), // Temporary ID (negative number, ensure different from user)
      chat_id: typeof chatId === 'string' ? parseInt(chatId, 10) : chatId,
      role: 'assistant' as const,
      content: '', // Placeholder
      created_at: new Date().toISOString(),
    };

    setCurrentChat(prev => ({
      ...(prev || chatToUpdate!), // Use chatToUpdate if prev is null
      messages: [...(prev?.messages || chatToUpdate!.messages || []), userMessage, assistantMessage],
    }));

    // 4. Set streaming state and scroll
    setIsStreaming(true);
    setError(null);
    setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' }), 10);

    try {
      // 5. Update title if it's the first message
      if (chatToUpdate.title === "New Conversation") {
        const newTitle = messageContent.length > 30
          ? `${messageContent.substring(0, 30)}...`
          : messageContent;
        console.log('Updating chat title based on first message:', newTitle);
        const updateResult = await updateChat(chatId, { title: newTitle });
        if (updateResult.success) {
          setCurrentChat(prev => prev ? { ...prev, title: newTitle } : null);
          setChats(prevChats => // Update title in the main list as well
            prevChats.map(c => c.id === chatId ? { ...c, title: newTitle } : c)
          );
          console.log('Successfully updated chat title in backend');
        } else {
          console.error('Failed to update chat title in backend:', updateResult.error);
          // Continue anyway, title update failure isn't critical for the stream
        }
      }

      // Set waiting state before starting stream
      setIsWaitingForResponse(true);

      // 6. Setup and start EventSource
      const eventSource = setupEventSource(chatId, messageContent, contextDocuments);
      eventSource.onmessage = handleEventMessage;
      eventSource.onerror = handleEventError;

      announce({ message: 'Message sent, waiting for response', politeness: 'polite' });

    } catch (err) {
      console.error('Error sending message:', err);
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred.';
      setError(`Failed to send message: ${errorMessage}`);
      showNotification(`Failed to send message: ${errorMessage}`, 'error');
      // Rollback optimistic UI updates? Remove placeholder messages?
      setCurrentChat(prev => {
          if (!prev) return null;
          // Remove the last two messages (user + assistant placeholder)
          const messages = prev.messages?.slice(0, -2) || [];
          return {...prev, messages };
      });
      setIsStreaming(false);
      closeEventSource();
    }
  };


  return {
    isStreaming,
    isWaitingForResponse, // Add new state to return object
    error,
    messagesEndRef,
    handleSendMessage,
    handleFeedback,
    handleUpdateMessage,
    closeEventSource,
  };
};