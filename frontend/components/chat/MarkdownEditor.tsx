import React, { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/Button';

// Simple Markdown toolbar options
interface ToolbarButton {
  name: string;
  icon: React.ReactNode;
  action: (selectedText: string, textBefore: string, textAfter: string) => {
    replacement: string;
    cursorOffset: number;
  };
  shortcut?: string;
}

interface MarkdownEditorProps {
  initialValue: string;
  onSave: (content: string) => void;
  onCancel: () => void;
  height?: string;
}

const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  initialValue,
  onSave,
  onCancel,
  height = 'auto',
}) => {
  const [content, setContent] = useState(initialValue);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Focus the editor and place cursor at the end
    if (textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.setSelectionRange(
        textareaRef.current.value.length,
        textareaRef.current.value.length
      );
    }
  }, []);

  const getSelection = useCallback(() => {
    if (!textareaRef.current) return { start: 0, end: 0, text: '', before: '', after: '' };
    
    const start = textareaRef.current.selectionStart;
    const end = textareaRef.current.selectionEnd;
    const text = textareaRef.current.value.substring(start, end);
    const before = textareaRef.current.value.substring(0, start);
    const after = textareaRef.current.value.substring(end);
    
    return { start, end, text, before, after };
  }, []);

  const updateTextWithSelection = useCallback((
    newText: string,
    selectionStart: number,
    selectionEnd: number
  ) => {
    if (!textareaRef.current) return;
    
    setContent(newText);
    
    // We need to wait for the state update to be reflected in the DOM
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(selectionStart, selectionEnd);
      }
    }, 0);
  }, []);

  const toolbarButtons: ToolbarButton[] = [
    {
      name: 'Bold',
      icon: <span className="font-bold">B</span>,
      action: (text, before, after) => {
        const marker = '**';
        const replacement = `${marker}${text}${marker}`;
        return {
          replacement,
          cursorOffset: marker.length,
        };
      },
      shortcut: 'Ctrl+B',
    },
    {
      name: 'Italic',
      icon: <span className="italic">I</span>,
      action: (text, before, after) => {
        const marker = '*';
        const replacement = `${marker}${text}${marker}`;
        return {
          replacement,
          cursorOffset: marker.length,
        };
      },
      shortcut: 'Ctrl+I',
    },
    {
      name: 'Heading',
      icon: <span className="font-bold">H</span>,
      action: (text, before, after) => {
        // Check if we're at the start of a line
        const isStartOfLine = before.length === 0 || before.endsWith('\n');
        const prefix = isStartOfLine ? '' : '\n';
        const replacement = `${prefix}### ${text}`;
        return {
          replacement,
          cursorOffset: prefix.length + 4, // '### ' is 4 characters
        };
      },
    },
    {
      name: 'Link',
      icon: <span>🔗</span>,
      action: (text, before, after) => {
        const isUrl = text.match(/^(https?:\/\/|www\.)/i);
        const replacement = isUrl 
          ? `[](${text})` 
          : `[${text}](url)`;
        
        return {
          replacement,
          cursorOffset: isUrl ? 1 : text.length + 3, // position cursor in appropriate place
        };
      },
    },
    {
      name: 'Code',
      icon: <span className="font-mono">{"<>"}</span>,
      action: (text, before, after) => {
        // Check if this is a code block or inline code
        const hasNewlines = text.includes('\n');
        
        if (hasNewlines) {
          const replacement = `\`\`\`\n${text}\n\`\`\``;
          return {
            replacement,
            cursorOffset: 4, // Position after the first ```\n
          };
        } else {
          const marker = '`';
          const replacement = `${marker}${text}${marker}`;
          return {
            replacement,
            cursorOffset: marker.length,
          };
        }
      },
    },
    {
      name: 'List',
      icon: <span>•</span>,
      action: (text, before, after) => {
        // Check if we're at the start of a line
        const isStartOfLine = before.length === 0 || before.endsWith('\n');
        const prefix = isStartOfLine ? '' : '\n';
        
        // If multiple lines, make each a list item
        if (text.includes('\n')) {
          const lines = text.split('\n');
          const listItems = lines.map(line => `- ${line}`).join('\n');
          return {
            replacement: `${prefix}${listItems}`,
            cursorOffset: prefix.length + 2, // Position after the first '- '
          };
        } else {
          const replacement = `${prefix}- ${text}`;
          return {
            replacement,
            cursorOffset: prefix.length + 2, // '- ' is 2 characters
          };
        }
      },
    },
  ];

  const handleToolbarAction = (button: ToolbarButton) => {
    const { start, end, text, before, after } = getSelection();
    
    const selectedText = text || '';
    const { replacement, cursorOffset } = button.action(selectedText, before, after);
    
    const newContent = before + replacement + after;
    setContent(newContent);
    
    // Calculate new cursor position
    const newCursorPos = start + (
      selectedText.length === 0 
        ? cursorOffset // If no selection, place cursor at specified offset
        : replacement.length // If there was a selection, place cursor at end of replacement
    );
    
    // Set cursor position after the state update
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
      }
    }, 0);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Keyboard shortcuts
    if (e.ctrlKey || e.metaKey) {
      const key = e.key.toLowerCase();
      
      // Find matching toolbar button shortcut
      const button = toolbarButtons.find(
        btn => btn.shortcut?.toLowerCase().endsWith(key)
      );
      
      if (button) {
        e.preventDefault();
        handleToolbarAction(button);
      }
    }
    
    // Handle tab key for indentation
    if (e.key === 'Tab') {
      e.preventDefault();
      const { start, end, before, after } = getSelection();
      
      // Insert tab character (or spaces)
      const indentation = '  '; // 2 spaces
      const newContent = before + indentation + after;
      
      setContent(newContent);
      
      // Set cursor position after indentation
      setTimeout(() => {
        if (textareaRef.current) {
          const newCursorPos = start + indentation.length;
          textareaRef.current.focus();
          textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
        }
      }, 0);
    }
  };

  // Auto-resize logic
  useEffect(() => {
    if (!textareaRef.current) return;
    
    // Reset the height momentarily to get the correct scrollHeight value
    textareaRef.current.style.height = 'auto';
    
    // Get the scrollHeight and set the height
    const scrollHeight = textareaRef.current.scrollHeight;
    textareaRef.current.style.height = height === 'auto' 
      ? `${scrollHeight}px` 
      : height;
  }, [content, height]);

  return (
    <div className="flex flex-col rounded-md border border-gray-300 dark:border-gray-700">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-1 p-2 border-b border-gray-300 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 rounded-t-md">
        {toolbarButtons.map((button) => (
          <button
            key={button.name}
            className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded cursor-pointer transition-colors"
            title={button.shortcut ? `${button.name} (${button.shortcut})` : button.name}
            onClick={() => handleToolbarAction(button)}
            type="button"
          >
            {button.icon}
          </button>
        ))}
      </div>

      {/* Editor */}
      <textarea
        ref={textareaRef}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onKeyDown={handleKeyDown}
        className="w-full p-3 min-h-[150px] outline-none resize-none bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-b-md"
        placeholder="Write your markdown here..."
      />

      {/* Actions */}
      <div className="flex justify-end mt-2 space-x-2">
        <Button 
          variant="outline" 
          onClick={onCancel}
          className="px-4 py-2"
        >
          Cancel
        </Button>
        <Button
          onClick={() => onSave(content)}
          className="px-4 py-2"
        >
          Save
        </Button>
      </div>
    </div>
  );
};

export default MarkdownEditor;