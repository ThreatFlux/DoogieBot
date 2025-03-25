import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import SearchBar from '@/components/chat/SearchBar';
import TagSelector from '@/components/chat/TagSelector';
import { Tag, Chat } from '@/types';
import { getUserTags, createTag, updateTag, deleteTag, searchTags, TagSearchParams } from '@/services/chat';
import { useNotification } from '@/contexts/NotificationContext';
import { showSuccess } from '@/utils/notificationUtils';

interface ChatSidebarProps {
  chats: Chat[];
  filteredChats: Chat[];
  searchTerm: string;
  selectedFilterTags: string[];
  onSearchChange: (value: string) => void;
  onSelectedTagsChange: (tags: string[]) => void;
  onSelectChat: (chat: Chat) => void;
  onNewChat: () => void;
  onDeleteChat: (chatId: string, e?: React.MouseEvent) => void;
  onUpdateTags: (chatId: string, tags: string[]) => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  chats,
  filteredChats,
  searchTerm,
  selectedFilterTags,
  onSearchChange,
  onSelectedTagsChange,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  onUpdateTags
}) => {
  const [tags, setTags] = useState<Tag[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tag management state
  const [showNewTagForm, setShowNewTagForm] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [newTagColor, setNewTagColor] = useState('#3b82f6'); // Default blue
  const [isCreatingTag, setIsCreatingTag] = useState(false);
  
  // Tag editing state
  const [editingTagId, setEditingTagId] = useState<string | null>(null);
  const [editTagName, setEditTagName] = useState('');
  const [editTagColor, setEditTagColor] = useState('');
  
  // Get notification context
  const { showNotification } = useNotification();
  const [isEditingTag, setIsEditingTag] = useState(false);
  
  // Tag deletion state
  const [tagToDelete, setTagToDelete] = useState<string | null>(null);
  const [showDeleteTagConfirm, setShowDeleteTagConfirm] = useState(false);

  // Tag search state
  const [tagSearchTerm, setTagSearchTerm] = useState('');
  const [showTagFilters, setShowTagFilters] = useState(false);
  const [showTagManagement, setShowTagManagement] = useState(false);
  const [tagPage, setTagPage] = useState(1);
  const [totalTagPages, setTotalTagPages] = useState(1);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  // Load tags from backend with search capabilities
  useEffect(() => {
    const loadTags = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Use either search or basic API based on whether search term exists
        if (tagSearchTerm) {
          const params: TagSearchParams = {
            search: tagSearchTerm,
            page: tagPage,
            pageSize: 20,
            sortBy: 'name',
            sortOrder: 'asc'
          };
          
          const { data, error: searchError } = await searchTags(params);
          
          if (data) {
            // If loading more, append to existing tags; otherwise replace
            if (tagPage > 1 && isLoadingMore) {
              setTags(prevTags => [...prevTags, ...data.items]);
            } else {
              setTags(data.items);
            }
            setTotalTagPages(data.total_pages);
          } else if (searchError) {
            setError(`Failed to search tags: ${searchError}`);
            // Keep existing tags
          }
        } else {
          // No search term, use standard API
          const { tags: userTags, error: tagsError } = await getUserTags();
          
          if (userTags) {
            setTags(userTags);
          } else if (tagsError) {
            setError(`Failed to load tags: ${tagsError}`);
            // Set empty array to avoid undefined
            setTags([]);
          }
        }
      } catch (err) {
        console.error('Error loading tags:', err);
        setError('An unexpected error occurred while loading tags');
        if (tagPage === 1) {
          setTags([]);
        }
      } finally {
        setIsLoading(false);
        setIsLoadingMore(false);
      }
    };
    
    loadTags();
  }, [tagSearchTerm, tagPage]);
  
  // Handle tag search with debouncing
  const handleTagSearch = (term: string) => {
    setTagSearchTerm(term);
    setTagPage(1); // Reset to first page when search changes
  };
  
  // Handle loading more tags
  const handleLoadMoreTags = () => {
    if (tagPage < totalTagPages && !isLoadingMore) {
      setIsLoadingMore(true);
      setTagPage(prevPage => prevPage + 1);
    }
  };

  // Handle tags loaded from search
  const handleTagsLoaded = (tags: Tag[], pages: number) => {
    // If loading more, append to existing tags; otherwise replace
    if (isLoadingMore) {
      setTags(prevTags => {
        // Filter out duplicates
        const newTags = tags.filter(tag => !prevTags.some(t => t.id === tag.id));
        return [...prevTags, ...newTags];
      });
    } else {
      setTags(tags);
    }
    
    setTotalTagPages(pages);
    setIsLoadingMore(false);
  };

  // Handle tag creation
  const handleCreateTag = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newTagName.trim()) return;
    
    setIsCreatingTag(true);
    setError(null);
    
    try {
      console.log('Attempting to create tag:', newTagName.trim(), newTagColor);
      const { tag, error: createError } = await createTag(newTagName.trim(), newTagColor);
      
      if (tag) {
        // Add the new tag to the list
        setTags(prevTags => [...prevTags, tag]);
        
        // Reset form
        setNewTagName('');
        setShowNewTagForm(false);
        
        // Show success notification
        showSuccess(showNotification, 'Tag created successfully');
      } else if (createError) {
        console.error('Error from createTag:', createError);
        setError(`${createError}`);
        
        // Check for auth errors and try to refresh
        if (createError.includes('401') || createError.includes('authentication')) {
          // Force refresh the page to trigger re-authentication
          setError('Authentication error. Please try again.');
          setTimeout(() => {
            window.location.reload();
          }, 2000);
        }
      }
    } catch (err) {
      console.error('Exception in createTag:', err);
      setError('An unexpected error occurred while creating the tag. Please try again.');
    } finally {
      setIsCreatingTag(false);
    }
  };
  
  // Start editing a tag
  const handleStartEditTag = (tag: Tag) => {
    setEditingTagId(tag.id);
    setEditTagName(tag.name);
    setEditTagColor(tag.color);
    // Hide the new tag form if it's open
    setShowNewTagForm(false);
  };
  
  // Cancel tag editing
  const handleCancelEditTag = () => {
    setEditingTagId(null);
    setEditTagName('');
    setEditTagColor('');
  };
  
  // Save tag edits
  const handleSaveTagEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!editingTagId || !editTagName.trim()) return;
    
    setIsEditingTag(true);
    setError(null);
    
    try {
      const { tag, error: updateError } = await updateTag(editingTagId, {
        name: editTagName.trim(),
        color: editTagColor
      });
      
      if (tag) {
        // Update the tag in the list
        setTags(prevTags => 
          prevTags.map(t => t.id === editingTagId ? tag : t)
        );
        
        // Reset form
        handleCancelEditTag();
      } else if (updateError) {
        setError(`Failed to update tag: ${updateError}`);
      }
    } catch (err) {
      console.error('Error updating tag:', err);
      setError('An unexpected error occurred while updating the tag');
    } finally {
      setIsEditingTag(false);
    }
  };
  
  // Prepare for tag deletion
  const handleConfirmDeleteTag = (tagId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent event bubbling
    setTagToDelete(tagId);
    setShowDeleteTagConfirm(true);
  };
  
  // Cancel tag deletion
  const handleCancelDeleteTag = () => {
    setTagToDelete(null);
    setShowDeleteTagConfirm(false);
  };
  
  // Perform tag deletion
  const handleDeleteTag = async () => {
    if (!tagToDelete) return;
    
    setError(null);
    
    try {
      const { success, error: deleteError } = await deleteTag(tagToDelete);
      
      if (success) {
        // Remove the tag from the list
        setTags(prevTags => prevTags.filter(t => t.id !== tagToDelete));
        
        // Remove the tag from selected filter tags if present
        if (selectedFilterTags.includes(tagToDelete)) {
          onSelectedTagsChange(selectedFilterTags.filter(id => id !== tagToDelete));
        }
        
        // Reset state
        handleCancelDeleteTag();
      } else if (deleteError) {
        setError(`Failed to delete tag: ${deleteError}`);
      }
    } catch (err) {
      console.error('Error deleting tag:', err);
      setError('An unexpected error occurred while deleting the tag');
    }
  };
  // Find the tag being deleted (for confirmation message)
  const tagToDeleteName = tagToDelete 
    ? tags.find(t => t.id === tagToDelete)?.name || 'this tag' 
    : '';
    
  return (
    <div className="p-1.5 w-full flex flex-col h-full overflow-hidden">
      <Button
        onClick={(e) => {
          e.preventDefault();
          onNewChat();
        }}
        className="w-full mb-2 flex items-center justify-center text-xs py-1.5 sidebar-button"
        aria-label="Create new chat"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
        </svg>
        New Chat
      </Button>

      <div className="mb-2 w-full flex-shrink-0">
        <SearchBar
          onSearch={onSearchChange}
          initialValue={searchTerm}
          placeholder="Search conversations..."
          className="mb-1 w-full text-xs"
        />

        {/* Tag filtering - Collapsible */}
        <div className="mb-1">
          <div className="flex justify-between items-center mb-0.5">
            <button
              type="button"
              onClick={() => setShowTagFilters(!showTagFilters)}
              className="text-xs font-medium flex items-center w-full justify-between"
            >
              <span>Filter by tags</span>
              <svg xmlns="http://www.w3.org/2000/svg" className={`h-4 w-4 transition-transform ${showTagFilters ? 'transform rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>

          {showTagFilters && (
            <>
              <div className="flex justify-end mb-0.5">
                <button
                  type="button"
                  onClick={() => setShowNewTagForm(!showNewTagForm)}
                  className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
                >
                  {showNewTagForm ? 'Cancel' : '+ New Tag'}
                </button>
              </div>
              
              {showNewTagForm && (
                <form onSubmit={handleCreateTag} className="mb-1 p-1.5 bg-gray-50 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600">
                  <div className="mb-1">
                    <Input
                      type="text"
                      placeholder="Tag name"
                      value={newTagName}
                      onChange={(e) => setNewTagName(e.target.value)}
                      className="text-xs mb-1"
                    />
                    <div className="flex space-x-2 items-center">
                      <label className="text-xs text-gray-600 dark:text-gray-400">Color:</label>
                      <input
                        type="color"
                        value={newTagColor}
                        onChange={(e) => setNewTagColor(e.target.value)}
                        className="p-0 h-6 w-6 border-0"
                      />
                    </div>
                  </div>
                  <Button
                    type="submit"
                    className="w-full py-0.5 text-xs"
                    isLoading={isCreatingTag}
                    disabled={!newTagName.trim() || isCreatingTag}
                  >
                    Create Tag
                  </Button>
                </form>
              )}
              
              {error && (
                <div className="text-xs text-red-500 dark:text-red-400 mb-1">
                  {error}
                </div>
              )}

              <TagSelector
                availableTags={tags}
                selectedTags={selectedFilterTags}
                onChange={onSelectedTagsChange}
                label=""
                showSearch={false}
                maxHeight={120}
                size="small"
                compact={true}
              />
              
              {totalTagPages > 1 && tagPage < totalTagPages && (
                <button
                  onClick={handleLoadMoreTags}
                  className="w-full text-xs text-center py-0.5 mt-0.5 text-primary-600 dark:text-primary-400 hover:underline"
                  disabled={isLoadingMore}
                >
                  {isLoadingMore ? 'Loading more tags...' : 'Load more tags'}
                </button>
              )}
            </>
          )}

          {/* Tag Management - Collapsible */}
          {tags.length > 0 && (
            <div className="mt-1">
              <div className="flex justify-between items-center mb-0.5">
                <button
                  type="button"
                  onClick={() => setShowTagManagement(!showTagManagement)}
                  className="text-xs font-medium flex items-center w-full justify-between text-gray-700 dark:text-gray-300"
                >
                  <span>Manage Tags</span>
                  <svg xmlns="http://www.w3.org/2000/svg" className={`h-4 w-4 transition-transform ${showTagManagement ? 'transform rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
              
              {showTagManagement && (
                <div className="space-y-0.5 max-h-24 overflow-y-auto pr-1">
                  {tags.map(tag => (
                  <div 
                    key={tag.id} 
                    className="flex items-center justify-between p-1 bg-gray-50 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600"
                  >
                    {editingTagId === tag.id ? (
                      <form 
                        onSubmit={handleSaveTagEdit} 
                        className="w-full flex flex-col space-y-2"
                      >
                        <div className="flex space-x-2">
                          <Input
                            type="text"
                            value={editTagName}
                            onChange={(e) => setEditTagName(e.target.value)}
                            className="text-xs flex-grow"
                            placeholder="Tag name"
                          />
                          <input
                            type="color"
                            value={editTagColor}
                            onChange={(e) => setEditTagColor(e.target.value)}
                            className="p-0 h-6 w-6 border-0"
                          />
                        </div>
                        <div className="flex space-x-1">
                          <Button
                            type="submit"
                            className="py-0.5 px-2 text-xs flex-1"
                            size="sm" 
                            isLoading={isEditingTag}
                            disabled={!editTagName.trim() || isEditingTag}
                          >
                            Save
                          </Button>
                          <Button
                            type="button"
                            className="py-0.5 px-2 text-xs flex-1"
                            size="sm"
                            variant="secondary"
                            onClick={handleCancelEditTag}
                          >
                            Cancel
                          </Button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <div className="flex items-center space-x-2">
                          <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: tag.color }}
                          />
                          <span className="text-sm">{tag.name}</span>
                        </div>
                        <div className="flex space-x-1">
                          <button
                            onClick={() => handleStartEditTag(tag)}
                            className="text-gray-500 hover:text-blue-500 p-1"
                            title="Edit tag"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                            </svg>
                          </button>
                          <button
                            onClick={(e) => handleConfirmDeleteTag(tag.id, e)}
                            className="text-gray-500 hover:text-red-500 p-1"
                            title="Delete tag"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="chat-list space-y-1 flex-grow overflow-y-auto w-full pr-1 pb-2 mt-1">
        {filteredChats.length === 0 ? (
          <div className="text-center text-gray-500 dark:text-gray-400 p-4">
            {chats.length > 0 ? (
              <p>No chats match your filters</p>
            ) : (
              <p>No conversations yet</p>
            )}
          </div>
        ) : (
          filteredChats.map((chat) => (
            <div
              key={chat.id}
              data-chat-id={chat.id}
              className="chat-item p-1.5 rounded-lg bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-shadow cursor-pointer border border-gray-200 dark:border-gray-700 w-full"
              onClick={() => onSelectChat(chat)}
            >
              <div className="flex justify-between items-start">
                <h3 className="font-medium text-xs text-gray-900 dark:text-gray-100 truncate">
                  {chat.title || 'Untitled Chat'}
                </h3>
                <button
                  className="text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400 ml-1"
                  onClick={(e) => onDeleteChat(chat.id, e)}
                  title="Delete chat"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>

              {chat.tags && chat.tags.length > 0 && (
                <div className="flex flex-wrap mt-1 gap-0.5">
                  {chat.tags.map(tagId => {
                    const tag = tags.find((t: Tag) => t.id === tagId);
                    return tag ? (
                      <span
                        key={tag.id}
                        className="inline-flex items-center px-1 py-0 rounded text-xs font-medium"
                        style={{
                          backgroundColor: `${tag.color}30`,
                          color: tag.color,
                          borderColor: `${tag.color}60`,
                          boxShadow: `0 0 0 1px ${tag.color}20`,
                        }}
                      >
                        {tag.name}
                      </span>
                    ) : null;
                  })}
                </div>
              )}

              <div className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {chat.messages?.length || 0} message{chat.messages?.length !== 1 ? 's' : ''}
              </div>

              <div className="mt-1">
                <TagSelector
                availableTags={tags}
                selectedTags={chat.tags || []}
                onChange={(tags) => {
                console.log('Tag selector onChange called with tags:', tags, 'for chat ID:', chat.id);
                // Optimistically update the UI first for a responsive feel
                  const updatedTags = [...tags];
                  const chatItem = document.querySelector(`[data-chat-id="${chat.id}"]`);
                  if (chatItem) {
                      // Mark this chat as being updated
                    chatItem.classList.add('updating-tags');
                  }
                  
                  // Call the parent component's update function
                  onUpdateTags(chat.id, updatedTags);
                  
                  // Show a success notification
                  showSuccess(showNotification, 'Chat tags updated');
                  
                  // Remove the updating class after a delay
                  setTimeout(() => {
                    if (chatItem) {
                      chatItem.classList.remove('updating-tags');
                    }
                  }, 1500);
                }}
                label=""
                size="small"
                compact={true}
              />
              </div>
            </div>
          ))
        )}
      </div>
      
      {/* Confirm Delete Tag Dialog */}
      <ConfirmDialog
        isOpen={showDeleteTagConfirm}
        onClose={handleCancelDeleteTag}
        onConfirm={handleDeleteTag}
        title="Delete Tag"
        message={`Are you sure you want to delete "${tagToDeleteName}"? This will also remove the tag from all conversations that use it.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />
    </div>
  );
};

export default ChatSidebar;
