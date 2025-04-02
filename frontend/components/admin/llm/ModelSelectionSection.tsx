import React, { useState } from 'react';
import { Button } from '../../ui/Button';
import { Card } from '../../ui/Card';
import { ModelSelectionComponent } from './ModelSelectionComponent';
import { ProviderConfig, ChatConfig, EmbeddingConfig, RerankingConfig } from './types';
import { createLLMConfig, updateLLMConfig, activateLLMConfig, createEmbeddingConfig, updateEmbeddingConfig, activateEmbeddingConfig, createRerankingConfig, updateRerankingConfig, activateRerankingConfig } from '../../../services/llm';

interface ModelSelectionSectionProps {
  // Chat model state
  selectedChatProvider: string;
  setSelectedChatProvider: (provider: string) => void;
  selectedChatModel: string;
  setSelectedChatModel: (model: string) => void;
  availableChatModels: string[];
  setAvailableChatModels: (models: string[]) => void;
  filteredChatModels: string[];
  setFilteredChatModels: (models: string[]) => void;
  isPollingChatModels: boolean;
  setIsPollingChatModels: (isPolling: boolean) => void;
  
  // Embedding model state
  selectedEmbeddingProvider: string;
  setSelectedEmbeddingProvider: (provider: string) => void;
  selectedEmbeddingModel: string;
  setSelectedEmbeddingModel: (model: string) => void;
  availableEmbeddingModels: string[];
  setAvailableEmbeddingModels: (models: string[]) => void;
  filteredEmbeddingModels: string[];
  setFilteredEmbeddingModels: (models: string[]) => void;
  isPollingEmbeddingModels: boolean;
  setIsPollingEmbeddingModels: (isPolling: boolean) => void;
  
  // Reranking model state
  selectedRerankingProvider: string;
  setSelectedRerankingProvider: (provider: string) => void;
  selectedRerankingModel: string;
  setSelectedRerankingModel: (model: string) => void;
  availableRerankingModels: string[];
  setAvailableRerankingModels: (models: string[]) => void;
  filteredRerankingModels: string[];
  setFilteredRerankingModels: (models: string[]) => void;
  isPollingRerankingModels: boolean;
  setIsPollingRerankingModels: (isPolling: boolean) => void;
  
  // Shared state
  systemPrompt: string;
  providerConfigs: ProviderConfig[];
  providers: Record<string, any>;
  activeChatConfig: ChatConfig | null;
  activeEmbeddingConfig: EmbeddingConfig | null;
  activeRerankingConfig: RerankingConfig | null;
  temperature: number; // Added temperature prop
  setTemperature: (temp: number) => void; // Added temperature setter prop
  
  // Callbacks
  onUpdate: () => Promise<void>;
  setError: (error: string | null) => void;
}

export const ModelSelectionSection: React.FC<ModelSelectionSectionProps> = ({
  // Chat model props
  selectedChatProvider,
  setSelectedChatProvider,
  selectedChatModel,
  setSelectedChatModel,
  availableChatModels,
  setAvailableChatModels,
  filteredChatModels,
  setFilteredChatModels,
  isPollingChatModels,
  setIsPollingChatModels,
  
  // Embedding model props
  selectedEmbeddingProvider,
  setSelectedEmbeddingProvider,
  selectedEmbeddingModel,
  setSelectedEmbeddingModel,
  availableEmbeddingModels,
  setAvailableEmbeddingModels,
  filteredEmbeddingModels,
  setFilteredEmbeddingModels,
  isPollingEmbeddingModels,
  setIsPollingEmbeddingModels,
  
  // Reranking model props
  selectedRerankingProvider,
  setSelectedRerankingProvider,
  selectedRerankingModel,
  setSelectedRerankingModel,
  availableRerankingModels,
  setAvailableRerankingModels,
  filteredRerankingModels,
  setFilteredRerankingModels,
  isPollingRerankingModels,
  setIsPollingRerankingModels,
  
  // Shared props
  systemPrompt,
  providerConfigs,
  providers,
  activeChatConfig,
  activeEmbeddingConfig,
  activeRerankingConfig,
  
  // Callbacks
  onUpdate,
  setError,
  temperature, // Destructure temperature
  setTemperature // Destructure setTemperature
}) => {
  const [isSaving, setIsSaving] = useState(false);

  const saveConfiguration = async () => {
    setIsSaving(true);
    try {
      // Prepare chat configuration
      const chatConfigData = {
        reranking_provider: selectedRerankingProvider || null,
        reranking_model: selectedRerankingModel || null,
        use_reranking: activeChatConfig?.config?.use_reranking || false,
        rag_top_k: activeChatConfig?.config?.rag_top_k || 3
      };
      
      // Update or create chat config
      if (activeChatConfig) {
        // Only use server URL for Ollama
        let serverUrl = undefined;
        if (selectedChatProvider === 'ollama') {
          // Ollama requires a server URL
          serverUrl = providerConfigs.find(pc => pc.id === selectedChatProvider)?.base_url || 'http://localhost:11434';
        }
        
        // Update existing chat config
        const response = await updateLLMConfig(activeChatConfig.id, {
          chat_provider: selectedChatProvider,
          model: selectedChatModel,
          system_prompt: systemPrompt,
          api_key: providerConfigs.find(pc => pc.id === selectedChatProvider)?.api_key,
          base_url: serverUrl,
          temperature: temperature, // Include temperature in update
          config: chatConfigData
        });
        
        if (response.error) {
          throw new Error(response.error);
        }
      } else {
        // Only use server URL for Ollama
        let serverUrl = undefined;
        if (selectedChatProvider === 'ollama') {
          // Ollama requires a server URL
          serverUrl = providerConfigs.find(pc => pc.id === selectedChatProvider)?.base_url || 'http://localhost:11434';
        }
        
        // Create new chat config
        const chatResponse = await createLLMConfig({
          chat_provider: selectedChatProvider,
          embedding_provider: selectedEmbeddingProvider, // Required field
          model: selectedChatModel,
          embedding_model: selectedEmbeddingModel, // Required field
          system_prompt: systemPrompt,
          api_key: providerConfigs.find(pc => pc.id === selectedChatProvider)?.api_key,
          base_url: serverUrl,
          temperature: temperature, // Include temperature in create
          config: chatConfigData
        });
        
        if (chatResponse.error) {
          throw new Error(chatResponse.error);
        }
        
        // Activate the new chat config
        if (chatResponse.config) {
          await activateLLMConfig(chatResponse.config.id);
        }
      }
      
      // Handle embedding configuration
      if (selectedEmbeddingProvider) {
        if (activeEmbeddingConfig) {
          // Only use server URL for Ollama
          let embeddingServerUrl = undefined;
          if (selectedEmbeddingProvider === 'ollama') {
            // Ollama requires a server URL
            embeddingServerUrl = providerConfigs.find(pc => pc.id === selectedEmbeddingProvider)?.base_url || 'http://localhost:11434';
          }
          
          // Update existing embedding config
          const embeddingResponse = await updateEmbeddingConfig(activeEmbeddingConfig.id, {
            provider: selectedEmbeddingProvider,
            model: selectedEmbeddingModel,
            api_key: providerConfigs.find(pc => pc.id === selectedEmbeddingProvider)?.api_key,
            base_url: embeddingServerUrl
          });
          
          if (embeddingResponse.error) {
            throw new Error(embeddingResponse.error);
          }
        } else {
          // Only use server URL for Ollama
          let embeddingServerUrl = undefined;
          if (selectedEmbeddingProvider === 'ollama') {
            // Ollama requires a server URL
            embeddingServerUrl = providerConfigs.find(pc => pc.id === selectedEmbeddingProvider)?.base_url || 'http://localhost:11434';
          }
          
          // Create new embedding config
          const embeddingResponse = await createEmbeddingConfig({
            provider: selectedEmbeddingProvider,
            model: selectedEmbeddingModel,
            api_key: providerConfigs.find(pc => pc.id === selectedEmbeddingProvider)?.api_key,
            base_url: embeddingServerUrl
          });
          
          if (embeddingResponse.error) {
            throw new Error(embeddingResponse.error);
          }
          
          // Activate the new embedding config
          if (embeddingResponse.config) {
            await activateEmbeddingConfig(embeddingResponse.config.id);
          }
        }
      }
      
      // Handle reranking configuration
      if (selectedRerankingProvider) {
        if (activeRerankingConfig) {
          // Only use server URL for Ollama
          let rerankingServerUrl = undefined;
          if (selectedRerankingProvider === 'ollama') {
            // Ollama requires a server URL
            rerankingServerUrl = providerConfigs.find(pc => pc.id === selectedRerankingProvider)?.base_url || 'http://localhost:11434';
          }
          
          // Update existing reranking config
          const rerankingResponse = await updateRerankingConfig(activeRerankingConfig.id, {
            provider: selectedRerankingProvider,
            model: selectedRerankingModel,
            api_key: providerConfigs.find(pc => pc.id === selectedRerankingProvider)?.api_key,
            base_url: rerankingServerUrl
          });
          
          if (rerankingResponse.error) {
            throw new Error(rerankingResponse.error);
          }
        } else {
          // Only use server URL for Ollama
          let rerankingServerUrl = undefined;
          if (selectedRerankingProvider === 'ollama') {
            // Ollama requires a server URL
            rerankingServerUrl = providerConfigs.find(pc => pc.id === selectedRerankingProvider)?.base_url || 'http://localhost:11434';
          }
          
          // Create new reranking config
          const rerankingResponse = await createRerankingConfig({
            provider: selectedRerankingProvider,
            model: selectedRerankingModel,
            api_key: providerConfigs.find(pc => pc.id === selectedRerankingProvider)?.api_key,
            base_url: rerankingServerUrl
          });
          
          if (rerankingResponse.error) {
            throw new Error(rerankingResponse.error);
          }
          
          // Activate the new reranking config
          if (rerankingResponse.config) {
            await activateRerankingConfig(rerankingResponse.config.id);
          }
        }
      }
      
      setError(null);
      // Reload data to reflect changes
      await onUpdate();
      // Show success message after data is reloaded
      alert("Configuration saved successfully!");
    } catch (err) {
      console.error('Failed to save configuration:', err);
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card>
      <div className="p-4">
        <h3 className="text-lg font-semibold mb-4">Model Selection</h3>
        
        {/* Chat Model Selection */}
        <ModelSelectionComponent
          modelType="chat"
          selectedProvider={selectedChatProvider}
          setSelectedProvider={setSelectedChatProvider}
          selectedModel={selectedChatModel}
          setSelectedModel={setSelectedChatModel}
          availableModels={availableChatModels}
          setAvailableModels={setAvailableChatModels}
          filteredModels={filteredChatModels}
          setFilteredModels={setFilteredChatModels}
          isPolling={isPollingChatModels}
          setIsPolling={setIsPollingChatModels}
          providerConfigs={providerConfigs}
          providers={providers}
          setError={setError}
        />
        
        {/* Temperature Slider */}
        <div className="mt-4 mb-6 border-t pt-4">
          <label htmlFor="temperature" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Chat Temperature: <span className="font-semibold">{temperature.toFixed(2)}</span>
          </label>
          <input
            type="range"
            id="temperature"
            name="temperature"
            min="0"
            max="2"
            step="0.01"
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
            <span>Deterministic (0.0)</span>
            <span>Creative (2.0)</span>
          </div>
        </div>
        
        {/* Embedding Model Selection */}
        <ModelSelectionComponent
          modelType="embedding"
          selectedProvider={selectedEmbeddingProvider}
          setSelectedProvider={setSelectedEmbeddingProvider}
          selectedModel={selectedEmbeddingModel}
          setSelectedModel={setSelectedEmbeddingModel}
          availableModels={availableEmbeddingModels}
          setAvailableModels={setAvailableEmbeddingModels}
          filteredModels={filteredEmbeddingModels}
          setFilteredModels={setFilteredEmbeddingModels}
          isPolling={isPollingEmbeddingModels}
          setIsPolling={setIsPollingEmbeddingModels}
          providerConfigs={providerConfigs}
          providers={providers}
          setError={setError}
        />
        
        {/* Reranking Model Selection */}
        <ModelSelectionComponent
          modelType="reranking"
          selectedProvider={selectedRerankingProvider}
          setSelectedProvider={setSelectedRerankingProvider}
          selectedModel={selectedRerankingModel}
          setSelectedModel={setSelectedRerankingModel}
          availableModels={availableRerankingModels}
          setAvailableModels={setAvailableRerankingModels}
          filteredModels={filteredRerankingModels}
          setFilteredModels={setFilteredRerankingModels}
          isPolling={isPollingRerankingModels}
          setIsPolling={setIsPollingRerankingModels}
          providerConfigs={providerConfigs}
          providers={providers}
          setError={setError}
        />
        
        <div className="mt-4">
          <Button 
            onClick={saveConfiguration}
            disabled={isSaving || !selectedChatProvider || !selectedChatModel || !selectedEmbeddingProvider || !selectedEmbeddingModel}
          >
            {isSaving ? 'Saving...' : 'Save Model Configuration'}
          </Button>
        </div>
      </div>
    </Card>
  );
};