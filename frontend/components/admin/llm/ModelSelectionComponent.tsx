import React, { useState, useEffect } from 'react';
import { Button } from '../../ui/Button';
import { filterModels, groupModelsByProvider } from './utils';
import { ProviderConfig } from './types';
import { getProviderModels } from '../../../services/llm';

interface ModelSelectionComponentProps {
  modelType: 'chat' | 'embedding' | 'reranking';
  selectedProvider: string;
  setSelectedProvider: (provider: string) => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  availableModels: string[];
  setAvailableModels: (models: string[]) => void;
  filteredModels: string[];
  setFilteredModels: (models: string[]) => void;
  isPolling: boolean;
  setIsPolling: (isPolling: boolean) => void;
  providerConfigs: ProviderConfig[];
  providers: Record<string, any>;
  setError: (error: string | null) => void;
}

export const ModelSelectionComponent: React.FC<ModelSelectionComponentProps> = ({
  modelType,
  selectedProvider,
  setSelectedProvider,
  selectedModel,
  setSelectedModel,
  availableModels,
  setAvailableModels,
  filteredModels,
  setFilteredModels,
  isPolling,
  setIsPolling,
  providerConfigs,
  providers,
  setError
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  // Poll for available models for a provider
  const pollModelsForProvider = async (providerId: string) => {
    const providerConfig = providerConfigs.find(pc => pc.id === providerId);
    if (!providerConfig) {
      setError(`Provider configuration not found for ${providerId}`);
      return;
    }
    
    // For Ollama, ensure base URL is set
    if (providerId === 'ollama' && !providerConfig.base_url) {
      setError("Ollama requires a Base URL (e.g., http://localhost:11434)");
      return;
    }
    
    setIsPolling(true);
    
    try {
      // Only use server URL for Ollama
      let serverUrl = undefined;
      if (providerId === 'ollama') {
        // Ollama requires a server URL
        serverUrl = providerConfig.base_url || 'http://localhost:11434';
        console.log(`Polling models for ${providerId} with server URL: ${serverUrl}`);
      } else {
        console.log(`Polling models for ${providerId}`);
      }
      
      const response = await getProviderModels(
        providerId,
        providerConfig.api_key,
        serverUrl // Only pass serverUrl for Ollama
      );
      
      if (response.error) {
        throw new Error(response.error);
      }
      
      console.log(`Received models for ${providerId}:`, response);
      
      // Special handling for Ollama - use all models for all types
      if (providerId === 'ollama') {
        // Combine chat and embedding models for Ollama
        const ollamaModels = Array.from(new Set([...(response.chatModels || []), ...(response.embeddingModels || [])]));
        console.log(`Combined Ollama models:`, ollamaModels);
        
        if (ollamaModels.length === 0) {
          setError(`No models found for Ollama. Please check your configuration and ensure Ollama is running.`);
          setIsPolling(false);
          return;
        }
        
        setAvailableModels(ollamaModels);
        setFilteredModels(ollamaModels);
        
        if (ollamaModels.length > 0 && !selectedModel) {
          setSelectedModel(ollamaModels[0]);
        }
      } else {
        // Standard handling for other providers
        if (modelType === 'chat') {
          if (providerId === 'openrouter') {
            // For OpenRouter, use chat models directly to preserve provider prefixes
            const chatModels = response.chatModels || [];
            
            // Force to array if needed
            const modelsArray = Array.isArray(chatModels) ? chatModels : [];
            
            // Add some default models if empty
            const finalModels = modelsArray.length > 0 ? modelsArray : [
              "openai/gpt-3.5-turbo",
              "openai/gpt-4",
              "anthropic/claude-2"
            ];
            
            setAvailableModels(finalModels);
            setFilteredModels(finalModels);
            
            if (finalModels.length > 0 && !selectedModel) {
              setSelectedModel(finalModels[0]);
            }
            
            if (modelsArray.length === 0) {
              console.warn(`No chat models found for OpenRouter, using defaults`);
            }
          } else {
            // For other providers
            const chatModels = response.chatModels || [];
            setAvailableModels(chatModels);
            setFilteredModels(chatModels);
            
            if (chatModels.length > 0 && !selectedModel) {
              setSelectedModel(chatModels[0]);
            }
            
            if (chatModels.length === 0) {
              setError(`No chat models found for ${providerId}. Please check your configuration.`);
            }
          }
        } else if (modelType === 'embedding') {
          if (providerId === 'openrouter') {
            const embeddingModels = response.embeddingModels || [];
            setAvailableModels(embeddingModels);
            setFilteredModels(embeddingModels);
            
            if (embeddingModels.length > 0 && !selectedModel) {
              setSelectedModel(embeddingModels[0]);
            }
            
            if (embeddingModels.length === 0) {
              setError(`No embedding models found for OpenRouter. Please check your configuration.`);
            }
          } else {
            const embeddingModels = response.embeddingModels || [];
            setAvailableModels(embeddingModels);
            setFilteredModels(embeddingModels);
            
            if (embeddingModels.length > 0 && !selectedModel) {
              setSelectedModel(embeddingModels[0]);
            }
            
            if (embeddingModels.length === 0) {
              setError(`No embedding models found for ${providerId}. Please check your configuration.`);
            }
          }
        } else if (modelType === 'reranking') {
          if (providerId === 'openrouter') {
            const rerankingModels = response.embeddingModels || [];
            setAvailableModels(rerankingModels);
            setFilteredModels(rerankingModels);
            
            if (rerankingModels.length > 0 && !selectedModel) {
              setSelectedModel(rerankingModels[0]);
            }
            
            if (rerankingModels.length === 0) {
              setError(`No embedding models found for OpenRouter. Please check your configuration.`);
            }
          } else {
            // For other providers, we can use embedding models or fall back to chat models
            let rerankingModels = response.embeddingModels || [];
            
            // If no embedding models are available, use chat models as a fallback
            if (rerankingModels.length === 0) {
              rerankingModels = response.chatModels || [];
              console.log(`No embedding models found for ${providerId}, using chat models for reranking:`, rerankingModels);
            }
            
            setAvailableModels(rerankingModels);
            setFilteredModels(rerankingModels);
            
            if (rerankingModels.length > 0 && !selectedModel) {
              setSelectedModel(rerankingModels[0]);
            }
            
            if (rerankingModels.length === 0) {
              setError(`No models found for reranking with ${providerId}. Please check your configuration.`);
            }
          }
        }
      }
    } catch (err) {
      console.error('Failed to poll available models:', err);
      setError(err instanceof Error ? err.message : 'Failed to poll available models');
    } finally {
      setIsPolling(false);
    }
  };

  // Update filtered models when search term changes
  useEffect(() => {
    if (searchTerm.trim() === '') {
      setFilteredModels(availableModels);
    } else {
      const filtered = availableModels.filter(model =>
        model.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredModels(filtered);
    }
  }, [searchTerm, availableModels, setFilteredModels]);

  const modelTypeLabel = modelType.charAt(0).toUpperCase() + modelType.slice(1);

  return (
    <div className="mb-6">
      <h4 className="text-md font-semibold mb-3">{modelTypeLabel} Model</h4>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            {modelTypeLabel} Provider
          </label>
          <div className="mt-1">
            <select
              className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
              value={selectedProvider}
              onChange={(e) => {
                setSelectedProvider(e.target.value);
                setSelectedModel('');
                setAvailableModels([]);
                if (e.target.value) {
                  pollModelsForProvider(e.target.value);
                }
              }}
            >
              <option value="">Select a provider</option>
              {Object.entries(providers).map(([id, provider]) => (
                <option key={id} value={id}>{id.charAt(0).toUpperCase() + id.slice(1)}</option>
              ))}
            </select>
          </div>
        </div>
        
        {selectedProvider && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              {modelTypeLabel} Model
            </label>
            <div className="mt-1">
              {isPolling ? (
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Polling for available models...
                </div>
              ) : availableModels.length > 0 ? (
                // Use the advanced UI for OpenRouter or any provider with more than 10 models
                (selectedProvider === 'openrouter' || availableModels.length > 10) ? (
                  <div className="relative">
                    <div className="mb-2">
                      {selectedModel && (
                        <div className="mb-2 p-2 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded flex justify-between items-center">
                          <span className="font-medium">Selected: {selectedModel}</span>
                          <button
                            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                            onClick={() => setSelectedModel('')}
                          >
                            ✕
                          </button>
                        </div>
                      )}
                      <div className="flex items-center">
                        <input
                          type="text"
                          placeholder="Search models..."
                          className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                        {searchTerm && (
                          <button
                            className="ml-2 p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                            onClick={() => setSearchTerm('')}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="max-h-60 overflow-y-auto border rounded dark:bg-gray-700 dark:border-gray-600">
                      {filteredModels.length === 0 ? (
                        <div className="p-3 text-gray-500 dark:text-gray-400 text-center">
                          No models found matching "{searchTerm}"
                        </div>
                      ) : (
                        Object.entries(
                          groupModelsByProvider(filteredModels)
                        ).map(([provider, models]: [string, string[]]) => (
                          <div key={provider} className="border-b dark:border-gray-600">
                            <div className="px-3 py-1 text-sm font-medium bg-gray-100 dark:bg-gray-800">
                              {provider}
                            </div>
                            {models.map(model => (
                              <div
                                key={model}
                                className={`px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 ${
                                  selectedModel === model ? 'bg-blue-50 dark:bg-blue-900/30' : ''
                                }`}
                                onClick={() => setSelectedModel(model)}
                              >
                                {model.split('/')[1] || model}
                              </div>
                            ))}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ) : (
                  <select
                    className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                  >
                    <option value="">Select a model</option>
                    {availableModels.map((model) => (
                      <option key={model} value={model}>{model}</option>
                    ))}
                  </select>
                )
              ) : (
                <div className="flex">
                  <input
                    type="text"
                    className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600"
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    placeholder="Enter model name"
                  />
                  <Button
                    variant="outline"
                    className="ml-2"
                    onClick={() => pollModelsForProvider(selectedProvider)}
                    disabled={isPolling}
                  >
                    {isPolling ? 'Polling...' : 'Poll Models'}
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};