import React, { useState, useRef, useCallback } from 'react';
import { Button } from '../ui/Button';

interface DragDropZoneProps {
  onFilesDrop: (files: File[]) => void;
  maxFiles?: number;
  acceptedFileTypes?: string;
  maxSizeInMB?: number;
  className?: string;
  isLoading?: boolean;
}

const DragDropZone: React.FC<DragDropZoneProps> = ({
  onFilesDrop,
  maxFiles = 10,
  acceptedFileTypes = '.pdf,.doc,.docx,.txt,.md,.rtf,.csv,.json',
  maxSizeInMB = 10,
  className = '',
  isLoading = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const maxSizeInBytes = maxSizeInMB * 1024 * 1024;

  const handleDragEnter = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) {
      setIsDragging(true);
    }
  }, [isDragging]);

  const validateFiles = useCallback((fileList: FileList | File[]): File[] => {
    setError(null);
    const files = Array.from(fileList);
    
    // Validate number of files
    if (files.length > maxFiles) {
      setError(`You can upload a maximum of ${maxFiles} files at once.`);
      return [];
    }
    
    // Validate file types and size
    const validFiles = files.filter(file => {
      const fileExtension = `.${file.name.split('.').pop()?.toLowerCase()}`;
      const isValidType = acceptedFileTypes.includes('*') || 
                          acceptedFileTypes.includes(fileExtension);
      
      const isValidSize = file.size <= maxSizeInBytes;
      
      if (!isValidType) {
        setError(`File type not supported. Allowed types: ${acceptedFileTypes}`);
        return false;
      }
      
      if (!isValidSize) {
        setError(`File size exceeds the maximum allowed size (${maxSizeInMB}MB).`);
        return false;
      }
      
      return true;
    });
    
    return validFiles;
  }, [acceptedFileTypes, maxFiles, maxSizeInBytes, maxSizeInMB]);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (isLoading) return;
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const validFiles = validateFiles(e.dataTransfer.files);
      if (validFiles.length > 0) {
        onFilesDrop(validFiles);
      }
    }
  }, [onFilesDrop, validateFiles, isLoading]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const validFiles = validateFiles(e.target.files);
      if (validFiles.length > 0) {
        onFilesDrop(validFiles);
      }
    }
    
    // Reset the input value so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [onFilesDrop, validateFiles]);

  const handleButtonClick = useCallback(() => {
    if (fileInputRef.current && !isLoading) {
      fileInputRef.current.click();
    }
  }, [isLoading]);

  return (
    <div className={`w-full ${className}`}>
      <div
        className={`
          border-2 border-dashed rounded-lg p-6 
          transition-colors duration-200 ease-in-out
          text-center cursor-pointer
          ${isDragging 
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' 
            : 'border-gray-300 dark:border-gray-600 hover:border-primary-400 dark:hover:border-primary-700'}
          ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleButtonClick}
      >
        <div className="flex flex-col items-center justify-center space-y-3">
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            className={`h-12 w-12 ${isDragging ? 'text-primary-500' : 'text-gray-400 dark:text-gray-500'}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={1.5} 
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" 
            />
          </svg>
          
          <div className="space-y-1">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {isDragging ? 'Drop your files here' : 'Drag and drop your files here'}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              or
            </p>
            <Button
              type="button"
              size="sm"
              isLoading={isLoading}
              disabled={isLoading}
              onClick={(e) => {
                e.stopPropagation();
                handleButtonClick();
              }}
            >
              Browse files
            </Button>
            
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Supports {acceptedFileTypes.replace(/\./g, '')} files up to {maxSizeInMB}MB
            </p>
          </div>
        </div>
      </div>
      
      {error && (
        <div className="mt-2 text-sm text-red-500 dark:text-red-400">
          {error}
        </div>
      )}
      
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={acceptedFileTypes}
        className="hidden"
        onChange={handleFileInputChange}
        disabled={isLoading}
      />
    </div>
  );
};

export default DragDropZone;
