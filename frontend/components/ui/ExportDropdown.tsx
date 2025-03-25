import React, { useState, useRef, useEffect } from 'react';
import { Chat } from '@/types';
import { announce } from '@/utils/accessibilityUtils';
import { getChat } from '@/services/chat';

export type ExportFormat = 'markdown' | 'text' | 'json' | 'html';

interface ExportDropdownProps {
  chat: Chat | { id: string };
  onExport?: (format: ExportFormat) => void;
}

const ExportDropdown: React.FC<ExportDropdownProps> = ({ chat, onExport }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  
  // Ensure we have a full chat object
  const [fullChat, setFullChat] = useState<Chat | null>(null);

  // Fetch full chat data if needed
  useEffect(() => {
    const fetchFullChat = async () => {
      // If we already have a full chat object, use it
      if ('messages' in chat && chat.messages) {
        setFullChat(chat as Chat);
        return;
      }
      
      // Otherwise, fetch the chat data
      try {
        if ('id' in chat && chat.id) {
          const { chat: fetchedChat } = await getChat(chat.id);
          if (fetchedChat) {
            setFullChat(fetchedChat);
          }
        }
      } catch (error) {
        console.error('Failed to fetch full chat data:', error);
      }
    };
    
    fetchFullChat();
  }, [chat]);
  
  // Handle clicking outside of the dropdown to close it
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  // Handle ESC key to close the dropdown
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Handle export function that works with blobs directly
  const exportChatData = (format: ExportFormat) => {
    if (!fullChat) return;
    
    let content = '';
    let mimeType = '';
    let filename = `chat-${fullChat.id}-${new Date().toISOString().slice(0, 10)}`;
    
    const formatDate = (dateString: string): string => {
      const date = new Date(dateString);
      return date.toLocaleString();
    };
    
    const formatMessageForText = (message: any): string => {
      const roleLabel = message.role === 'user' ? 'User' : 'Assistant';
      const timestamp = message.created_at ? formatDate(message.created_at) : '';
      const tokens = message.tokens ? `(Tokens: ${message.tokens})` : '';
      
      return `### ${roleLabel} - ${timestamp} ${tokens}\n\n${message.content}\n\n`;
    };
    
    const formatMessageForMarkdown = (message: any): string => {
      const roleLabel = message.role === 'user' ? 'User' : 'Assistant';
      const timestamp = message.created_at ? formatDate(message.created_at) : '';
      const tokens = message.tokens ? `(Tokens: ${message.tokens})` : '';
      
      return `## ${roleLabel} - ${timestamp} ${tokens}\n\n${message.content}\n\n`;
    };
    
    switch (format) {
      case 'json':
        content = JSON.stringify(fullChat, null, 2);
        mimeType = 'application/json';
        filename += '.json';
        break;
        
      case 'text':
        content = `# Chat: ${fullChat.title || 'Untitled Chat'}\n\n`;
        content += `# Created: ${formatDate(fullChat.created_at || new Date().toISOString())}\n\n`;
        content += `# Messages: ${fullChat.messages?.length || 0}\n\n`;
        
        if (fullChat.messages && fullChat.messages.length > 0) {
          fullChat.messages.forEach(message => {
            content += formatMessageForText(message);
          });
        }
        
        mimeType = 'text/plain';
        filename += '.txt';
        break;
        
      case 'markdown':
        content = `# ${fullChat.title || 'Untitled Chat'}\n\n`;
        content += `*Created: ${formatDate(fullChat.created_at || new Date().toISOString())}*\n\n`;
        
        if (fullChat.messages && fullChat.messages.length > 0) {
          fullChat.messages.forEach(message => {
            content += formatMessageForMarkdown(message);
          });
        }
        
        mimeType = 'text/markdown';
        filename += '.md';
        break;
        
      case 'html':
        content = `<!DOCTYPE html>\n<html>\n<head>\n<title>${fullChat.title || 'Untitled Chat'}</title>\n`;
        content += `<style>\n`;
        content += `body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }\n`;
        content += `.header { text-align: center; margin-bottom: 30px; }\n`;
        content += `.message { margin-bottom: 20px; padding: 15px; border-radius: 8px; }\n`;
        content += `.user { background-color: #f0f0f0; }\n`;
        content += `.assistant { background-color: #e6f7ff; }\n`;
        content += `.message-header { font-weight: bold; margin-bottom: 10px; }\n`;
        content += `.message-content { white-space: pre-wrap; }\n`;
        content += `</style>\n</head>\n<body>\n`;
        content += `<div class="header">\n`;
        content += `<h1>${fullChat.title || 'Untitled Chat'}</h1>\n`;
        content += `<p>Created: ${formatDate(fullChat.created_at || new Date().toISOString())}</p>\n`;
        content += `</div>\n`;
        
        if (fullChat.messages && fullChat.messages.length > 0) {
          fullChat.messages.forEach(message => {
            const roleClass = message.role === 'user' ? 'user' : 'assistant';
            const roleLabel = message.role === 'user' ? 'User' : 'Assistant';
            const timestamp = message.created_at ? formatDate(message.created_at) : '';
            const tokens = message.tokens ? `(Tokens: ${message.tokens})` : '';
            
            content += `<div class="message ${roleClass}">\n`;
            content += `<div class="message-header">${roleLabel} - ${timestamp} ${tokens}</div>\n`;
            content += `<div class="message-content">${message.content}</div>\n`;
            content += `</div>\n`;
          });
        }
        
        content += `</body>\n</html>`;
        
        mimeType = 'text/html';
        filename += '.html';
        break;
    }
    
    // Create a blob and download the file
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
  };

  // Handle export
  const handleExport = (format: ExportFormat) => {
    if (!fullChat) return;
    
    if (onExport) {
      onExport(format);
    } else {
      exportChatData(format);
    }
    
    setIsOpen(false);
    
    // Announce for screen readers
    announce({ 
      message: `Chat exported successfully as ${format}`, 
      politeness: 'polite' 
    });
  };
  
  return (
    <div ref={dropdownRef} className="relative">
      {/* Dropdown Trigger Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)} 
        className="flex items-center px-3 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full"
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label="Export chat menu"
        disabled={!chat}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <span className="ml-2 hidden md:inline">Export</span>
      </button>
      
      {/* Dropdown Menu */}
      {isOpen && (
        <div 
          className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg py-1 z-50 border border-gray-200 dark:border-gray-700"
          role="menu"
          aria-orientation="vertical"
          aria-labelledby="export-menu"
        >
          <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">Export Format</p>
          </div>
          
          <button 
            className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            onClick={() => handleExport('markdown')}
            role="menuitem"
            disabled={!fullChat}
          >
            <div className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              Markdown (.md)
            </div>
          </button>
          
          <button 
            className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            onClick={() => handleExport('text')}
            role="menuitem"
            disabled={!fullChat}
          >
            <div className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Text (.txt)
            </div>
          </button>
          
          <button 
            className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            onClick={() => handleExport('json')}
            role="menuitem"
            disabled={!fullChat}
          >
            <div className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              JSON (.json)
            </div>
          </button>
          
          <button 
            className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            onClick={() => handleExport('html')}
            role="menuitem"
            disabled={!fullChat}
          >
            <div className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              HTML (.html)
            </div>
          </button>
        </div>
      )}
    </div>
  );
};

export default ExportDropdown;