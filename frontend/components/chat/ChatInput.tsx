import React, { useState, KeyboardEvent, useRef } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import DragDropZone from '@/components/document/DragDropZone';
import FilePreview from '@/components/document/FilePreview';
import { uploadDocument } from '@/services/document';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isStreaming: boolean;
  disabled?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage, 
  isStreaming,
  disabled = false
}) => {
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number[]>([]);
  const [showFileUploader, setShowFileUploader] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = async () => {
    const trimmedMessage = message.trim();
    
    // If there are files, upload them first
    if (files.length > 0) {
      await handleUploadFiles();
    }
    
    // Send the message if there is one
    if (trimmedMessage && !isStreaming && !disabled) {
      onSendMessage(trimmedMessage);
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const handleFilesDrop = (droppedFiles: File[]) => {
    setFiles(prevFiles => [...prevFiles, ...droppedFiles]);
    setShowFileUploader(false); // Hide the uploader after files are dropped
  };
  
  const handleRemoveFile = (index: number) => {
    setFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
  };
  
  const handleUploadFiles = async () => {
    if (files.length === 0) return;
    
    setIsUploading(true);
    setError(null);
    
    // Initialize progress array
    setUploadProgress(Array(files.length).fill(0));
    
    try {
      // For each file, upload it
      for (let i = 0; i < files.length; i++) {
        // Simulate progress (in a real app, this would come from the upload API)
        const progressInterval = setInterval(() => {
          setUploadProgress(prev => {
            const newProgress = [...prev];
            newProgress[i] = Math.min(newProgress[i] + 10, 90); // Go up to 90% for simulation
            return newProgress;
          });
        }, 200);
        
        try {
          // Upload the file
          const { document, error: uploadError } = await uploadDocument(files[i]);
          
          // Clear the progress interval
          clearInterval(progressInterval);
          
          if (uploadError) {
            throw new Error(uploadError);
          }
          
          // Set progress to 100% when done
          setUploadProgress(prev => {
            const newProgress = [...prev];
            newProgress[i] = 100;
            return newProgress;
          });
          
          // If the file was uploaded successfully, append a message with the document ID
          if (document) {
            // Add file reference to the message
            const fileReference = `[Document: ${document.title}]`;
            
            if (message.trim()) {
              setMessage(prev => `${prev} ${fileReference}`);
            } else {
              setMessage(fileReference);
            }
          }
        } catch (err) {
          clearInterval(progressInterval);
          console.error(`Error uploading file ${i}:`, err);
          setError(`Error uploading ${files[i].name}. Please try again.`);
          
          // Set progress to indicate error
          setUploadProgress(prev => {
            const newProgress = [...prev];
            newProgress[i] = -1; // Use negative value to indicate error
            return newProgress;
          });
        }
      }
    } finally {
      // Clean up after all uploads
      // Wait a bit to let the user see the 100% completion
      setTimeout(() => {
        setIsUploading(false);
        setFiles([]);
        setUploadProgress([]);
      }, 1000);
    }
  };
  
  const toggleFileUploader = () => {
    setShowFileUploader(prev => !prev);
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3">
      {/* File Uploader UI */}
      {showFileUploader && (
        <div className="mb-3">
          <DragDropZone
            onFilesDrop={handleFilesDrop}
            maxFiles={5}
            maxSizeInMB={50}
            className="mb-2"
          />
        </div>
      )}
      
      {/* File Preview */}
      {files.length > 0 && (
        <FilePreview
          files={files}
          onRemove={handleRemoveFile}
          isUploading={isUploading}
          uploadProgress={uploadProgress}
        />
      )}
      
      {/* Error Message */}
      {error && (
        <div className="mb-2 p-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-md">
          {error}
        </div>
      )}
      
      {/* Chat Input */}
      <div className="flex items-center space-x-2">
        <Button
          type="button"
          variant="outline"
          onClick={toggleFileUploader}
          title={showFileUploader ? "Hide file uploader" : "Attach files"}
          className="p-2"
          disabled={isStreaming || disabled || isUploading}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8 4a3 3 0 00-3 3v4a5 5 0 0010 0V7a1 1 0 112 0v4a7 7 0 11-14 0V7a5 5 0 0110 0v4a3 3 0 11-6 0V7a1 1 0 012 0v4a1 1 0 102 0V7a3 3 0 00-3-3z" clipRule="evenodd" />
          </svg>
        </Button>
        
        <Input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message or drag files here..."
          className="flex-grow"
          disabled={isStreaming || disabled || isUploading}
        />
        
        <Button 
          onClick={handleSend} 
          disabled={((!message.trim() && files.length === 0) || isStreaming || disabled) && !isUploading}
          isLoading={isStreaming || isUploading}
          loadingText={isUploading ? "Uploading..." : "Sending..."}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>
        </Button>
      </div>
    </div>
  );
};

export default ChatInput;
