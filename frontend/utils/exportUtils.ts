import { Chat, Message } from '@/types';

export enum ExportFormat {
  JSON = 'json',
  TXT = 'txt',
  MD = 'md'
}

/**
 * Format a date string in a readable format
 */
const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleString();
};

/**
 * Format a message for export to plain text format
 */
const formatMessageForText = (message: Message): string => {
  const roleLabel = message.role === 'user' ? 'User' : 'Assistant';
  const timestamp = message.created_at ? formatDate(message.created_at) : '';
  const tokens = message.tokens ? `(Tokens: ${message.tokens})` : '';
  
  return `### ${roleLabel} - ${timestamp} ${tokens}\n\n${message.content}\n\n`;
};

/**
 * Format a message for export to markdown format
 */
const formatMessageForMarkdown = (message: Message): string => {
  const roleLabel = message.role === 'user' ? 'User' : 'Assistant';
  const timestamp = message.created_at ? formatDate(message.created_at) : '';
  const tokens = message.tokens ? `(Tokens: ${message.tokens})` : '';
  
  return `## ${roleLabel} - ${timestamp} ${tokens}\n\n${message.content}\n\n`;
};

/**
 * Export chat data in the specified format
 */
export const exportChat = (chat: Chat, format: ExportFormat): void => {
  if (!chat) return;
  
  let content = '';
  let mimeType = '';
  let filename = `chat-${chat.id}-${new Date().toISOString().slice(0, 10)}`;
  
  switch (format) {
    case ExportFormat.JSON:
      content = JSON.stringify(chat, null, 2);
      mimeType = 'application/json';
      filename += '.json';
      break;
      
    case ExportFormat.TXT:
      content = `# Chat: ${chat.title || 'Untitled Chat'}\n\n`;
      content += `# Created: ${formatDate(chat.created_at || new Date().toISOString())}\n\n`;
      content += `# Messages: ${chat.messages?.length || 0}\n\n`;
      
      if (chat.messages && chat.messages.length > 0) {
        chat.messages.forEach(message => {
          content += formatMessageForText(message);
        });
      }
      
      mimeType = 'text/plain';
      filename += '.txt';
      break;
      
    case ExportFormat.MD:
      content = `# ${chat.title || 'Untitled Chat'}\n\n`;
      content += `*Created: ${formatDate(chat.created_at || new Date().toISOString())}*\n\n`;
      
      if (chat.messages && chat.messages.length > 0) {
        chat.messages.forEach(message => {
          content += formatMessageForMarkdown(message);
        });
      }
      
      mimeType = 'text/markdown';
      filename += '.md';
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
