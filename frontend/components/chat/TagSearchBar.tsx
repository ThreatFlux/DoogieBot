import React, { useState, useEffect, useCallback } from 'react';
import { Tag } from '@/types';
import { searchTags, TagSearchParams } from '@/services/chat';
import { Input } from '@/components/ui/Input';
// Create our own debounce implementation to avoid dependency issues
const debounce = <F extends (...args: any[]) => any>(
  func: F,
  waitFor: number
) => {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  // Extended type with cancel method
  type DebouncedFunction<T extends (...args: any[]) => any> = {
    (...args: Parameters<T>): ReturnType<T>;
    cancel: () => void;
  };

  const debounced = ((...args: Parameters<F>) => {
    if (timeout !== null) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => func(...args), waitFor);
  }) as DebouncedFunction<F>;

  // Add cancel method
  debounced.cancel = () => {
    if (timeout !== null) {
      clearTimeout(timeout);
      timeout = null;
    }
  };

  return debounced;
};

export interface TagSearchBarProps {
  onTagsLoaded: (tags: Tag[], totalPages: number) => void;
  onSearchChange?: (term: string) => void;
  searchTerm?: string;
  className?: string;
}

const TagSearchBar: React.FC<TagSearchBarProps> = ({
  onTagsLoaded,
  onSearchChange,
  searchTerm: externalSearchTerm,
  className = '',
}) => {
  const [innerSearchTerm, setInnerSearchTerm] = useState(externalSearchTerm || '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  // Handle controlled vs uncontrolled search term
  const searchTerm = externalSearchTerm !== undefined ? externalSearchTerm : innerSearchTerm;

  // Create a proper debounced search function
  const debouncedLoadTags = useCallback(
    debounce((term: string, page: number) => {
      loadTags(term, page);
    }, 300),
    []
  );

  // Function to trigger the debounced search
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const triggerSearch = useCallback((term: string, page: number) => {
    debouncedLoadTags(term, page);
  }, [debouncedLoadTags]);

  const loadTags = async (term: string, page: number) => {
    setIsLoading(true);
    setError(null);

    try {
      const params: TagSearchParams = {
        search: term,
        page,
        pageSize: 20,
        sortBy: 'name',
        sortOrder: 'asc',
      };

      const { data, error } = await searchTags(params);

      if (error) {
        console.warn('Tag search returned error:', error);
        // Don't throw error, just show empty state
        onTagsLoaded([], 0);
        // Set a user-friendly error message for 404 errors only
        if (error.includes('404')) {
          setError('No tags found. Create a new tag to get started.');
        } else {
          setError(error);
        }
        return;
      }

      if (data) {
        onTagsLoaded(data.items, data.total_pages);
      } else {
        // If no data but also no error, use empty state
        onTagsLoaded([], 0);
      }
    } catch (err) {
      console.error('Error searching tags:', err);
      // Don't fail hard - just show empty results with error
      onTagsLoaded([], 0);
      setError(err instanceof Error ? err.message : 'An error occurred while searching tags');
    } finally {
      setIsLoading(false);
    }
  };

  // Load tags on mount and when search term or page changes
  useEffect(() => {
    triggerSearch(searchTerm, currentPage);
    
    // Cleanup on unmount
    return () => {
      debouncedLoadTags.cancel();
    };
  }, [searchTerm, currentPage, triggerSearch, debouncedLoadTags]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTerm = e.target.value;
    setInnerSearchTerm(newTerm);
    
    // If we're in controlled mode, call the parent's handler
    if (onSearchChange) {
      onSearchChange(newTerm);
    }
    
    // Reset to first page on new search
    setCurrentPage(1);
  };

  const handleNextPage = () => {
    setCurrentPage((prev) => prev + 1);
  };

  const handlePrevPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  };

  return (
    <div className={`tag-search-bar ${className}`}>
      <div className="flex items-center">
        <Input
          type="text"
          value={searchTerm}
          onChange={handleSearchChange}
          placeholder="Search tags..."
          className="w-full"
          disabled={isLoading}
        />
        {isLoading && (
          <div className="ml-2">
            <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
          </div>
        )}
      </div>

      {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
    </div>
  );
};

export default TagSearchBar;
