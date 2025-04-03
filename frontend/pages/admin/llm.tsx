import React, { useState, useEffect } from 'react';
import AdminLayout from '../../components/layout/AdminLayout';
import { withAdmin } from '../../utils/withAdmin';
import {
  SystemPromptSection,
  RAGConfigSection,
  ModelSelectionSection,
  APIKeysSection,
  ProviderConfig,
  ChatConfig // Import ChatConfig type
} from '../../components/admin/llm';
import {
  getLLMProviders,
  getAllLLMConfigs,
  getAllEmbeddingConfigs,
  getAllRerankingConfigs
} from '../../services/llm';

const LLMConfiguration: React.FC = () => {
  // State for providers and configs
  const [providers, setProviders] = useState<Record<string, any>>({});
  const [providerConfigs, setProviderConfigs] = useState<ProviderConfig[]>([]);
  const [chatConfigs, setChatConfigs] = useState<any[]>([]);
  const [embeddingConfigs, setEmbeddingConfigs] = useState<any[]>([]);
  const [rerankingConfigs, setRerankingConfigs] = useState<any[]>([]);
  
  // State for active configs
  const [activeChatConfig, setActiveChatConfig] = useState<ChatConfig | null>(null); // Use ChatConfig type
  const [activeEmbeddingConfig, setActiveEmbeddingConfig] = useState<any | null>(null);
  const [activeRerankingConfig, setActiveRerankingConfig] = useState<any | null>(null);
  
  // State for system prompt
  const [systemPrompt, setSystemPrompt] = useState<string>('You are Doogie, a helpful AI assistant.');
  
  // State for chat model selection
  const [selectedChatProvider, setSelectedChatProvider] = useState<string>('');
  const [selectedChatModel, setSelectedChatModel] = useState<string>('');
  const [availableChatModels, setAvailableChatModels] = useState<string[]>([]);
  const [filteredChatModels, setFilteredChatModels] = useState<string[]>([]);
  const [isPollingChatModels, setIsPollingChatModels] = useState<boolean>(false);
  
  // State for embedding model selection
  const [selectedEmbeddingProvider, setSelectedEmbeddingProvider] = useState<string>('');
  const [selectedEmbeddingModel, setSelectedEmbeddingModel] = useState<string>('');
  const [availableEmbeddingModels, setAvailableEmbeddingModels] = useState<string[]>([]);
  const [filteredEmbeddingModels, setFilteredEmbeddingModels] = useState<string[]>([]);
  const [isPollingEmbeddingModels, setIsPollingEmbeddingModels] = useState<boolean>(false);
  
  // State for reranking model selection
  const [selectedRerankingProvider, setSelectedRerankingProvider] = useState<string>('');
  const [selectedRerankingModel, setSelectedRerankingModel] = useState<string>('');
  const [availableRerankingModels, setAvailableRerankingModels] = useState<string[]>([]);
  const [filteredRerankingModels, setFilteredRerankingModels] = useState<string[]>([]);
  const [isPollingRerankingModels, setIsPollingRerankingModels] = useState<boolean>(false);
  
  // State for temperature
  const [temperature, setTemperature] = useState<number>(0.7); // Added temperature state
  
  // UI state
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load data on component mount
  useEffect(() => {
    loadData();
  }, []);

  // Function to load all data
  const loadData = async () => {
    setLoading(true);
    setError(null);
    // Load providers
    const providersResponse = await getLLMProviders();
    if (providersResponse.error) {
      console.error('API Error loading providers:', providersResponse.error);
      setError(`Failed to load providers: ${providersResponse.error}`);
      setLoading(false);
      return;
    }
    const providersData = providersResponse.providers || {};
    setProviders(providersData);

    // Load chat configurations
    const chatConfigsResponse = await getAllLLMConfigs();
    if (chatConfigsResponse.error) {
      console.error('API Error loading chat configs:', chatConfigsResponse.error);
      setError(`Failed to load chat configurations: ${chatConfigsResponse.error}`);
      setLoading(false);
      return;
    }
    const chatConfigsData = chatConfigsResponse.configs || [];
    setChatConfigs(chatConfigsData);

    // Load embedding configurations
    const embeddingConfigsResponse = await getAllEmbeddingConfigs();
    if (embeddingConfigsResponse.error) {
      console.error('API Error loading embedding configs:', embeddingConfigsResponse.error);
      setError(`Failed to load embedding configurations: ${embeddingConfigsResponse.error}`);
      setLoading(false);
      return;
    }
    const embeddingConfigsData = embeddingConfigsResponse.configs || [];
    setEmbeddingConfigs(embeddingConfigsData);

    // Load reranking configurations
    const rerankingConfigsResponse = await getAllRerankingConfigs();
    if (rerankingConfigsResponse.error) {
      console.error('API Error loading reranking configs:', rerankingConfigsResponse.error);
      setError(`Failed to load reranking configurations: ${rerankingConfigsResponse.error}`);
      setLoading(false);
      return;
    }
    const rerankingConfigsData = rerankingConfigsResponse.configs || [];
    setRerankingConfigs(rerankingConfigsData);

    // Set active configs
    const activeChatConfig = chatConfigsData.find((c: any) => c.is_active);
    setActiveChatConfig(activeChatConfig || null);

    const activeEmbeddingConfig = embeddingConfigsData.find((c: any) => c.is_active);
    setActiveEmbeddingConfig(activeEmbeddingConfig || null);

    const activeRerankingConfig = rerankingConfigsData.find((c: any) => c.is_active);
    setActiveRerankingConfig(activeRerankingConfig || null);

    // Initialize provider configs
    const initialProviderConfigs = Object.entries(providersData).map(([id, info]: [string, any]) => {
      // Find matching chat config
      const chatConfig = chatConfigsData.find((c: any) => c.chat_provider === id);
      // Find matching embedding config
      const embeddingConfig = embeddingConfigsData.find((c: any) => c.provider === id);

      // Only set base URL for providers that need it
      let baseUrl = '';
      if (id === 'ollama') {
        // Ollama requires a base URL
        baseUrl = chatConfig?.base_url || embeddingConfig?.base_url || 'http://localhost:11434';
      } else if (id === 'openrouter') {
        // OpenRouter has a fixed base URL that should not be changed
        baseUrl = 'https://openrouter.ai/api';
      } else {
        // Other providers like OpenAI don't need a base URL
        baseUrl = '';
      }

      return {
        id,
        chatConfig: chatConfig || null,
        embeddingConfig: embeddingConfig || null,
        enabled: (chatConfig?.is_active || embeddingConfig?.is_active) || false,
        api_key: chatConfig?.api_key || embeddingConfig?.api_key || '',
        base_url: baseUrl,
        model: chatConfig?.model || info.default_model || '',
        embedding_model: embeddingConfig?.model || '',
        embedding_provider: embeddingConfig?.provider || id,
        system_prompt: chatConfig?.system_prompt || 'You are Doogie, a helpful AI assistant.',
        available_models: [],
        embedding_models: [],
        isPolling: false
      };
    });

    setProviderConfigs(initialProviderConfigs);

    // Update systemPrompt state with the active chat configuration's system prompt
    if (activeChatConfig) {
      if (activeChatConfig.system_prompt) {
        setSystemPrompt(activeChatConfig.system_prompt);
      }

      // Set the selected chat provider and model based on active config
      setSelectedChatProvider(activeChatConfig.chat_provider);
      setSelectedChatModel(activeChatConfig.model);

      // Get reranking info from config
      const rerankingProvider = activeChatConfig.config?.reranking_provider || '';
      const rerankingModel = activeChatConfig.config?.reranking_model || '';
      setSelectedRerankingProvider(rerankingProvider);
      setSelectedRerankingModel(rerankingModel);
    }

    // Set the selected embedding provider and model based on active embedding config
    if (activeEmbeddingConfig) {
      setSelectedEmbeddingProvider(activeEmbeddingConfig.provider);
      setSelectedEmbeddingModel(activeEmbeddingConfig.model);
    }

    // If all loads succeed, set loading to false
    setLoading(false);
  };

  return (
    <AdminLayout title="LLM Configuration" description="Configure LLM providers and models">
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">LLM Configuration</h1>
        </div>
        
        {error && (
          <div className="p-4 bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-800 text-red-700 dark:text-red-400 rounded-md flex justify-between items-center">
            <div>{error}</div>
            <button
              onClick={() => setError(null)}
              className="text-red-700 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300"
            >
              ✕
            </button>
          </div>
        )}
        
        {loading ? (
          <div className="text-center py-8">Loading...</div>
        ) : (
          <>
            {/* System Prompt Section */}
            <SystemPromptSection
              systemPrompt={systemPrompt}
              setSystemPrompt={setSystemPrompt}
              activeChatConfig={activeChatConfig}
              onUpdate={loadData}
            />
            
            {/* RAG Configuration Section */}
            <RAGConfigSection
              activeChatConfig={activeChatConfig}
              selectedRerankingProvider={selectedRerankingProvider}
              selectedRerankingModel={selectedRerankingModel}
              onUpdate={loadData}
            />
            
            {/* Model Selection Section */}
            <ModelSelectionSection
              // Chat model props
              selectedChatProvider={selectedChatProvider}
              setSelectedChatProvider={setSelectedChatProvider}
              selectedChatModel={selectedChatModel}
              setSelectedChatModel={setSelectedChatModel}
              availableChatModels={availableChatModels}
              setAvailableChatModels={setAvailableChatModels}
              filteredChatModels={filteredChatModels}
              setFilteredChatModels={setFilteredChatModels}
              isPollingChatModels={isPollingChatModels}
              setIsPollingChatModels={setIsPollingChatModels}
              
              // Embedding model props
              selectedEmbeddingProvider={selectedEmbeddingProvider}
              setSelectedEmbeddingProvider={setSelectedEmbeddingProvider}
              selectedEmbeddingModel={selectedEmbeddingModel}
              setSelectedEmbeddingModel={setSelectedEmbeddingModel}
              availableEmbeddingModels={availableEmbeddingModels}
              setAvailableEmbeddingModels={setAvailableEmbeddingModels}
              filteredEmbeddingModels={filteredEmbeddingModels}
              setFilteredEmbeddingModels={setFilteredEmbeddingModels}
              isPollingEmbeddingModels={isPollingEmbeddingModels}
              setIsPollingEmbeddingModels={setIsPollingEmbeddingModels}
              
              // Reranking model props
              selectedRerankingProvider={selectedRerankingProvider}
              setSelectedRerankingProvider={setSelectedRerankingProvider}
              selectedRerankingModel={selectedRerankingModel}
              setSelectedRerankingModel={setSelectedRerankingModel}
              availableRerankingModels={availableRerankingModels}
              setAvailableRerankingModels={setAvailableRerankingModels}
              filteredRerankingModels={filteredRerankingModels}
              setFilteredRerankingModels={setFilteredRerankingModels}
              isPollingRerankingModels={isPollingRerankingModels}
              setIsPollingRerankingModels={setIsPollingRerankingModels}
              
              // Shared props
              systemPrompt={systemPrompt}
              providerConfigs={providerConfigs}
              providers={providers}
              activeChatConfig={activeChatConfig}
              activeEmbeddingConfig={activeEmbeddingConfig}
              activeRerankingConfig={activeRerankingConfig}
              temperature={temperature} // Pass temperature state
              setTemperature={setTemperature} // Pass temperature setter
              
              // Callbacks
              onUpdate={loadData}
              setError={setError}
            />
            
            {/* API Keys Section */}
            <APIKeysSection
              providerConfigs={providerConfigs}
              setProviderConfigs={setProviderConfigs}
              providers={providers}
              chatConfigs={chatConfigs}
              embeddingConfigs={embeddingConfigs}
              rerankingConfigs={rerankingConfigs}
              onUpdate={loadData}
              setError={setError}
            />
          </>
        )}
      </div>
    </AdminLayout>
  );
};

export default withAdmin(LLMConfiguration, "LLM Configuration");