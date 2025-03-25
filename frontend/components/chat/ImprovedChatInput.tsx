import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { TextArea } from '@/components/ui/TextArea';
import DragDropZone from '@/components/document/DragDropZone';
import FilePreview from '@/components/document/FilePreview';
import { uploadDocument } from '@/services/document';

interface ChatInputProps {
  onSendMessage: (message: string, contextDocuments?: string[]) => void;
  isStreaming: boolean;
  disabled?: boolean;
}

const ImprovedChatInput: React.FC<ChatInputProps> = ({ 
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
  const [contextDocuments, setContextDocuments] = useState<string[]>([]);
  
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-focus the input when the component mounts
  useEffect(() => {
    if (textAreaRef.current) {
      textAreaRef.current.focus();
    }
  }, []);

  const handleSend = async () => {
    const trimmedMessage = message.trim();
    
    // If there are files, upload them first
    if (files.length > 0) {
      await handleUploadFiles();
    }
    
    // Send the message if there is one
    if (trimmedMessage && !isStreaming && !disabled) {
      onSendMessage(trimmedMessage, contextDocuments.length > 0 ? contextDocuments : undefined);
      setMessage('');
      setContextDocuments([]);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
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
    
    // Collect document IDs from all uploaded files
    const uploadedDocIds: string[] = [];
    
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
          
          // If the file was uploaded successfully, add its ID to our context documents
          if (document && document.id) {
            uploadedDocIds.push(document.id);
            
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
      
      // Update context documents with all successfully uploaded document IDs
      if (uploadedDocIds.length > 0) {
        setContextDocuments(prev => [...prev, ...uploadedDocIds]);
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
      
      {/* Context Documents Info */}
      {contextDocuments.length > 0 && (
        <div className="mb-2 p-2 text-sm text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 rounded-md">
          <span className="font-medium">Using {contextDocuments.length} document(s) as context</span>
        </div>
      )}
      
      {/* Chat Input */}
      <div className="flex items-start space-x-2">
        {/* Attachments button */}
        <Button
          type="button"
          variant="outline"
          onClick={toggleFileUploader}
          title={showFileUploader ? "Hide file uploader" : "Attach files"}
          className="p-2 mt-1"
          disabled={isStreaming || disabled || isUploading}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8 4a3 3 0 00-3 3v4a5 5 0 0010 0V7a1 1 0 112 0v4a7 7 0 11-14 0V7a5 5 0 0110 0v4a3 3 0 11-6 0V7a1 1 0 012 0v4a1 1 0 102 0V7a3 3 0 00-3-3z" clipRule="evenodd" />
          </svg>
        </Button>
        
        {/* Multi-line text input */}
        <div className="flex-grow">
          <TextArea
            ref={textAreaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message or drag files here... (Shift+Enter for new line)"
            className="flex-grow min-h-[60px] resize-none"
            rows={1}
            autoResize={true}
            disabled={isStreaming || disabled || isUploading}
          />
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-1">
            Press Shift+Enter for a new line, Enter to send
          </div>
        </div>
        
        {/* Send button */}
        <Button 
          onClick={handleSend} 
          disabled={((!message.trim() && files.length === 0) || isStreaming || disabled) && !isUploading}
          isLoading={isStreaming || isUploading}
          loadingText={isUploading ? "Uploading..." : "Sending..."}
          className="mt-1"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>
        </Button>
      </div>
    </div>
  );
};

export default ImprovedChatInput;