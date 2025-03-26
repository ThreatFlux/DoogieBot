import React, { useState } from 'react';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { ProviderConfig } from './types';
import { createLLMConfig, updateLLMConfig, createEmbeddingConfig, updateEmbeddingConfig, createRerankingConfig, updateRerankingConfig } from '../../../services/llm';

interface APIKeysSectionProps {
  providerConfigs: ProviderConfig[];
  setProviderConfigs: React.Dispatch<React.SetStateAction<ProviderConfig[]>>;
  providers: Record<string, any>;
  chatConfigs: any[];
  embeddingConfigs: any[];
  rerankingConfigs: any[];
  onUpdate: () => Promise<void>;
  setError: (error: string | null) => void;
}

export const APIKeysSection: React.FC<APIKeysSectionProps> = ({
  providerConfigs,
  setProviderConfigs,
  providers,
  chatConfigs,
  embeddingConfigs,
  rerankingConfigs,
  onUpdate,
  setError
}) => {
  const [savingProvider, setSavingProvider] = useState<string | null>(null);

  // Function to update API key
  const updateApiKey = (providerId: string, apiKey: string): void => {
    setProviderConfigs((prevConfigs: ProviderConfig[]) =>
      prevConfigs.map((pc: ProviderConfig) =>
        pc.id === providerId ? { ...pc, api_key: apiKey } : pc
      )
    );
  };

  // Function to update base URL
  const updateBaseUrl = (providerId: string, baseUrl: string): void => {
    setProviderConfigs((prevConfigs: ProviderConfig[]) =>
      prevConfigs.map((pc: ProviderConfig) =>
        pc.id === providerId ? { ...pc, base_url: baseUrl } : pc
      )
    );
  };

  // Function to save API keys for a provider
  const saveProviderApiKey = async (providerId: string): Promise<void> => {
    const providerConfig = providerConfigs.find((pc: ProviderConfig) => pc.id === providerId);
    if (!providerConfig) return;
    
    setSavingProvider(providerId);
    try {
      // Only use server URL for Ollama
      let serverUrl: string | undefined = undefined;
      if (providerId === 'ollama') {
        // Ollama requires a server URL
        serverUrl = providerConfig.base_url || 'http://localhost:11434';
      }
      // For other providers, don't set a server URL
      
      // Find if there's an existing chat config for this provider
      const existingChatConfig = chatConfigs.find((c: any) => c.chat_provider === providerId);
      // Find if there's an existing embedding config for this provider
      const existingEmbeddingConfig = embeddingConfigs.find((c: any) => c.provider === providerId);
      
      // Update chat config if it exists
      if (existingChatConfig) {
        const chatResponse = await updateLLMConfig(existingChatConfig.id, {
          api_key: providerConfig.api_key,
          base_url: serverUrl
        });
        
        if (chatResponse.error) {
          throw new Error(chatResponse.error);
        }
      } else {
        // If no existing chat config, create a new one
        const provider = providers[providerId];
        const newChatConfig = {
          chat_provider: providerId,
          embedding_provider: providerId,
          model: provider.default_model,
          embedding_model: provider.default_model,
          system_prompt: 'You are Doogie, a helpful AI assistant.',
          api_key: providerConfig.api_key,
          base_url: serverUrl
        };
        
        const chatResponse = await createLLMConfig(newChatConfig);
        if (chatResponse.error) {
          throw new Error(chatResponse.error);
        }
      }
      
      // Update embedding config if it exists
      if (existingEmbeddingConfig) {
        const embeddingResponse = await updateEmbeddingConfig(existingEmbeddingConfig.id, {
          api_key: providerConfig.api_key,
          base_url: serverUrl
        });
        
        if (embeddingResponse.error) {
          throw new Error(embeddingResponse.error);
        }
      } else {
        // If no existing embedding config, create a new one
        const provider = providers[providerId];
        const newEmbeddingConfig = {
          provider: providerId,
          model: provider.default_model,
          api_key: providerConfig.api_key,
          base_url: serverUrl
        };
        
        const embeddingResponse = await createEmbeddingConfig(newEmbeddingConfig);
        if (embeddingResponse.error) {
          throw new Error(embeddingResponse.error);
        }
      }
      
      // Find if there's an existing reranking config for this provider
      const existingRerankingConfig = rerankingConfigs.find((c: any) => c.provider === providerId);
      
      // Update reranking config if it exists
      if (existingRerankingConfig) {
        const rerankingResponse = await updateRerankingConfig(existingRerankingConfig.id, {
          api_key: providerConfig.api_key,
          base_url: serverUrl
        });
        
        if (rerankingResponse.error) {
          throw new Error(rerankingResponse.error);
        }
      } else {
        // If no existing reranking config, create a new one
        const provider = providers[providerId];
        const newRerankingConfig = {
          provider: providerId,
          model: provider.default_model,
          api_key: providerConfig.api_key,
          base_url: serverUrl
        };
        
        const rerankingResponse = await createRerankingConfig(newRerankingConfig);
        if (rerankingResponse.error) {
          throw new Error(rerankingResponse.error);
        }
      }
      
      setError(null);
      // Reload data to reflect changes
      await onUpdate();
      // Show success message after data is reloaded
      alert(`Configuration for ${providerId} saved successfully!`);
    } catch (err) {
      console.error('Failed to save configuration:', err);
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSavingProvider(null);
    }
  };

  return (
    <Card>
      <div className="p-4">
        <h3 className="text-lg font-semibold mb-4">API Keys</h3>
        
        <div className="space-y-6">
          {Object.entries(providers).map(([id, provider]: [string, any]) => (
            <div key={id} className="p-4 border rounded dark:border-gray-700">
              <h4 className="text-md font-semibold mb-3">{id.charAt(0).toUpperCase() + id.slice(1)}</h4>
              
              <div className="space-y-4">
                {provider.requires_api_key && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      API Key
                    </label>
                    <div className="mt-1 flex">
                      <input
                        type="password"
                        className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600"
                        value={providerConfigs.find(pc => pc.id === id)?.api_key || ''}
                        onChange={(e) => updateApiKey(id, e.target.value)}
                        placeholder="Enter API key"
                      />
                    </div>
                  </div>
                )}
                
                {provider.requires_base_url && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Ollama Server URL <span className="text-red-500">*</span>
                    </label>
                    <div className="mt-1 flex">
                      <input
                        type="text"
                        className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600"
                        value={providerConfigs.find(pc => pc.id === id)?.base_url || ''}
                        onChange={(e) => updateBaseUrl(id, e.target.value)}
                        placeholder="http://localhost:11434 (required)"
                      />
                    </div>
                    {id === 'ollama' && (
                      <p className="mt-1 text-sm text-gray-500">
                        Ollama requires a Server URL to connect to your Ollama instance. Default is http://localhost:11434
                      </p>
                    )}
                  </div>
                )}
                
                {(provider.requires_api_key || provider.requires_base_url) && (
                  <div>
                    <Button 
                      onClick={() => saveProviderApiKey(id)}
                      disabled={savingProvider === id}
                    >
                      {savingProvider === id 
                        ? `Saving ${id.charAt(0).toUpperCase() + id.slice(1)} Configuration...` 
                        : `Save ${id.charAt(0).toUpperCase() + id.slice(1)} Configuration`}
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};