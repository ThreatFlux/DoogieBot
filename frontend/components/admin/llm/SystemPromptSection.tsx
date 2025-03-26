import React, { useState } from 'react';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { ChatConfig } from './types';
import { updateLLMConfig } from '../../../services/llm';

interface SystemPromptSectionProps {
  systemPrompt: string;
  setSystemPrompt: (prompt: string) => void;
  activeChatConfig: ChatConfig | null;
  onUpdate: () => Promise<void>;
}

export const SystemPromptSection: React.FC<SystemPromptSectionProps> = ({
  systemPrompt,
  setSystemPrompt,
  activeChatConfig,
  onUpdate
}) => {
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateSystemPrompt = async () => {
    if (!activeChatConfig) return;
    
    setIsUpdating(true);
    setError(null);
    
    try {
      // Update the config
      const response = await updateLLMConfig(activeChatConfig.id, { system_prompt: systemPrompt });
      if (response.error) {
        throw new Error(response.error);
      }
      
      // Reload data to reflect changes
      await onUpdate();
      
      // Show success message after data is reloaded
      alert("System prompt updated successfully!");
    } catch (err) {
      console.error('Failed to update system prompt:', err);
      setError(err instanceof Error ? err.message : 'Failed to update system prompt');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <Card>
      <div className="p-4">
        <h3 className="text-lg font-semibold mb-4">System Prompt</h3>
        
        {error && (
          <div className="p-4 mb-4 bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-800 text-red-700 dark:text-red-400 rounded-md">
            {error}
          </div>
        )}
        
        <div className="space-y-4">
          <div>
            <textarea
              className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={3}
            />
          </div>
          <div>
            <Button 
              onClick={updateSystemPrompt} 
              disabled={isUpdating || !activeChatConfig}
            >
              {isUpdating ? 'Updating...' : 'Update System Prompt'}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
};