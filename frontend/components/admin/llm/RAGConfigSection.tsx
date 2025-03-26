import React, { useState } from 'react';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { Input } from '../../ui/Input';
import { ChatConfig } from './types';
import { updateLLMConfig } from '../../../services/llm';

interface RAGConfigSectionProps {
  activeChatConfig: ChatConfig | null;
  selectedRerankingProvider: string;
  selectedRerankingModel: string;
  onUpdate: () => Promise<void>;
}

export const RAGConfigSection: React.FC<RAGConfigSectionProps> = ({
  activeChatConfig,
  selectedRerankingProvider,
  selectedRerankingModel,
  onUpdate
}) => {
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [topK, setTopK] = useState<number>(activeChatConfig?.config?.rag_top_k || 3);
  const [useReranking, setUseReranking] = useState<boolean>(activeChatConfig?.config?.use_reranking || false);

  // Update when activeChatConfig changes
  React.useEffect(() => {
    if (activeChatConfig) {
      setTopK(activeChatConfig.config?.rag_top_k || 3);
      setUseReranking(activeChatConfig.config?.use_reranking || false);
    }
  }, [activeChatConfig]);

  const updateRAGConfig = async () => {
    if (!activeChatConfig) return;
    
    setIsUpdating(true);
    setError(null);
    
    try {
      // Include reranking model and provider if reranking is enabled
      const reranking_provider = useReranking ? selectedRerankingProvider : '';
      const reranking_model = useReranking ? selectedRerankingModel : '';
      
      console.log(`Updating RAG config with reranking: ${useReranking}, provider: ${reranking_provider}, model: ${reranking_model}`);
      
      // Update the config
      const response = await updateLLMConfig(activeChatConfig.id, {
        config: {
          ...activeChatConfig.config,
          rag_top_k: topK,
          use_reranking: useReranking,
          reranking_provider,
          reranking_model
        }
      } as any); // Type assertion to bypass TypeScript check
      
      if (response.error) {
        throw new Error(response.error);
      }
      
      // Reload data to reflect changes
      await onUpdate();
      
      // Show success message after data is reloaded
      alert("RAG configuration updated successfully!");
    } catch (err) {
      console.error('Failed to update RAG configuration:', err);
      setError(err instanceof Error ? err.message : 'Failed to update RAG configuration');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <Card>
      <div className="p-4">
        <h3 className="text-lg font-semibold mb-4">RAG Configuration</h3>
        
        {error && (
          <div className="p-4 mb-4 bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-800 text-red-700 dark:text-red-400 rounded-md">
            {error}
          </div>
        )}
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Number of RAG Results (top_k)
            </label>
            <div className="mt-1 flex">
              <Input
                type="number"
                min="1"
                max="20"
                className="flex-1"
                value={topK}
                onChange={(e) => {
                  const value = parseInt(e.target.value);
                  if (value >= 1 && value <= 20) {
                    setTopK(value);
                  }
                }}
              />
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Controls how many relevant documents are retrieved for RAG. Default: 3
            </p>
          </div>
          
          <div className="mt-4">
            <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 dark:text-gray-300">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-300 focus:ring focus:ring-primary-200 focus:ring-opacity-50 dark:border-gray-600 dark:bg-gray-700"
                checked={useReranking}
                onChange={(e) => setUseReranking(e.target.checked)}
              />
              <span>Enable Reranking</span>
            </label>
            <p className="mt-1 text-sm text-gray-500">
              When enabled, results will be reranked using the selected reranking model before being sent to the LLM.
            </p>
          </div>
          
          <div>
            <Button 
              onClick={updateRAGConfig} 
              disabled={isUpdating || !activeChatConfig}
            >
              {isUpdating ? 'Updating...' : 'Update RAG Configuration'}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
};