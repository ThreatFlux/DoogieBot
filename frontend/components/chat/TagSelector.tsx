import React, { useState, useEffect } from 'react';
import { Tag } from '@/types';
import TagSearchBar from './TagSearchBar';

export interface TagSelectorProps {
  availableTags: Tag[];
  selectedTags: string[];
  onChange: (tags: string[]) => void;
  label: string;
  size?: 'small' | 'normal';
  showSearch?: boolean;
  maxHeight?: number;
  isLoading?: boolean;
  errorMessage?: string;
}

const TagSelector: React.FC<TagSelectorProps> = ({
  availableTags,
  selectedTags,
  onChange,
  label,
  size = 'normal',
  showSearch = true,
  maxHeight = 200,
  isLoading = false,
  errorMessage
}) => {
  const [filteredTags, setFilteredTags] = useState<Tag[]>(availableTags);
  const [searchTerm, setSearchTerm] = useState('');
  const [totalPages, setTotalPages] = useState(1);

  // Update filtered tags when available tags change
  useEffect(() => {
    if (!searchTerm) {
      setFilteredTags(availableTags);
    }
  }, [availableTags, searchTerm]);

  const toggleTag = (tagId: string) => {
    if (selectedTags.includes(tagId)) {
      onChange(selectedTags.filter(id => id !== tagId));
    } else {
      onChange([...selectedTags, tagId]);
    }
  };

  const handleTagsLoaded = (tags: Tag[], pages: number) => {
    setFilteredTags(tags);
    setTotalPages(pages);
  };

  // Add loading indicator
  if (isLoading) {
    return (
      <div className="enhanced-tag-selector">
        {label && <div className="text-sm font-medium mb-1">{label}</div>}
        <div className="tag-selector-loading p-2 flex items-center">
          <svg className="animate-spin h-4 w-4 mr-2 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <div className="text-sm text-gray-500">Loading tags...</div>
        </div>
      </div>
    );
  }

  // Display error message if present
  if (errorMessage) {
    return (
      <div className="enhanced-tag-selector">
        {label && <div className="text-sm font-medium mb-1">{label}</div>}
        <div className="tag-selector-error p-2 text-red-500 text-sm">
          <div className="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {errorMessage}
          </div>
        </div>
      </div>
    );
  }

  // Add empty state handling
  if (!filteredTags || filteredTags.length === 0) {
    return (
      <div className="enhanced-tag-selector">
        {label && <div className="text-sm font-medium mb-1">{label}</div>}
        <div className="tag-selector-empty p-2">
          <div className="text-sm text-gray-500">
            {searchTerm ? 'No matching tags found' : 'No tags available'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="enhanced-tag-selector">
      {label && <div className="text-sm font-medium mb-1">{label}</div>}
      
      {/* Tag search for larger collections */}
      {showSearch && (
        <div className="mb-2">
          <TagSearchBar
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            onTagsLoaded={handleTagsLoaded}
          />
        </div>
      )}

      {/* Simple list view without virtualization */}
      <div 
        className="flex flex-wrap gap-1"
        style={{ 
          maxHeight: `${maxHeight}px`,
          overflowY: 'auto'
        }}
      >
        {filteredTags.map(tag => (
          <button
            key={tag.id}
            onClick={() => toggleTag(tag.id)}
            className={`
              tag-item inline-flex items-center rounded transition-colors
              ${selectedTags.includes(tag.id) ? 'ring-1' : 'opacity-70 hover:opacity-100'}
              ${size === 'small' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-sm'}
            `}
            style={{
              backgroundColor: `${tag.color}10`,
              color: tag.color,
              borderColor: selectedTags.includes(tag.id) ? tag.color : 'transparent',
            }}
            type="button"
          >
            <span>{tag.name}</span>
            {selectedTags.includes(tag.id) && (
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                className={`${size === 'small' ? 'h-3 w-3 ml-1' : 'h-4 w-4 ml-1'}`}
                viewBox="0 0 20 20" 
                fill="currentColor"
              >
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            )}
          </button>
        ))}
      </div>

      {/* Pagination for large collections */}
      {totalPages > 1 && (
        <div className="flex justify-center mt-2 text-xs text-gray-500">
          <span>Additional tags available</span>
        </div>
      )}
    </div>
  );
};

export default TagSelector;
