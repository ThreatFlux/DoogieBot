import { LLMConfig, LLMModel, LLMProvider, EmbeddingConfig, RerankingConfig, RerankingProvider } from '@/types'; // Add RerankingProvider
import { get, post, put, del } from './api';

// ======================
// System Prompt Section
// ======================

export const getSystemPrompt = async (): Promise<{ prompt?: string; error?: string }> => {
  const response = await get<LLMConfig>('/llm/admin/config/active');
  if (response.error || !response.data) {
    return { error: response.error || 'No active config found' };
  }
  return { prompt: response.data.system_prompt };
};

export const updateSystemPrompt = async (prompt: string): Promise<{ success?: boolean; error?: string }> => {
  const activeConfig = await get<LLMConfig>('/llm/admin/config/active');
  if (activeConfig.error || !activeConfig.data) {
    return { error: activeConfig.error || 'No active config found' };
  }
  
  const response = await put<LLMConfig>(`/llm/admin/config/${activeConfig.data.id}`, { system_prompt: prompt });
  if (response.error) {
    return { error: response.error };
  }
  return { success: true };
};

// ======================
// RAG Configuration
// ======================

export const getRAGConfig = async (): Promise<{ config?: any; error?: string }> => {
  const response = await get<LLMConfig>('/llm/admin/config/active');
  if (response.error || !response.data) {
    return { error: response.error || 'No active config found' };
  }
  return { config: response.data.config?.rag_config };
};

export const updateRAGConfig = async (config: any): Promise<{ success?: boolean; error?: string }> => {
  const activeConfig = await get<LLMConfig>('/llm/admin/config/active');
  if (activeConfig.error || !activeConfig.data) {
    return { error: activeConfig.error || 'No active config found' };
  }
  
  const response = await put<LLMConfig>(`/llm/admin/config/${activeConfig.data.id}`, { 
    config: {
      ...(activeConfig.data.config || {}),
      rag_config: config
    }
  });
  if (response.error) {
    return { error: response.error };
  }
  return { success: true };
};

// ======================
// Model Selection
// ======================

// Get all available LLM providers
export const getLLMProviders = async (): Promise<{ providers?: LLMProvider[]; error?: string }> => {
  const response = await get<LLMProvider[]>('/llm/providers');
  if (response.error) {
    return { error: response.error };
  }
  return { providers: response.data };
};

// Get available models for a provider (backward compatibility)
export const getProviderModels = async (
  providerId: string,
  apiKey?: string,
  baseUrl?: string
): Promise<{ chatModels?: string[]; embeddingModels?: string[]; error?: string }> => {
  const params = new URLSearchParams();
  if (apiKey) params.append('api_key', apiKey);
  if (baseUrl) params.append('base_url', baseUrl);
  
  const queryString = params.toString() ? `?${params.toString()}` : '';
  const response = await get<{ chat_models: string[]; embedding_models: string[] }>(
    `/llm/providers/${providerId}/models${queryString}`
  );

  if (response.error) {
    return { error: response.error };
  }
  return {
    chatModels: response.data?.chat_models || [],
    embeddingModels: response.data?.embedding_models || []
  };
};

// Get available chat models for a provider
export const getChatModels = async (
  providerId: string,
  apiKey?: string,
  baseUrl?: string
): Promise<{ models?: string[]; error?: string }> => {
  const result = await getProviderModels(providerId, apiKey, baseUrl);
  if (result.error) {
    return { error: result.error };
  }
  return { models: result.chatModels };
};

// Get available embedding models for a provider
export const getEmbeddingModels = async (
  providerId: string,
  apiKey?: string,
  baseUrl?: string
): Promise<{ models?: string[]; error?: string }> => {
  const result = await getProviderModels(providerId, apiKey, baseUrl);
  if (result.error) {
    return { error: result.error };
  }
  return { models: result.embeddingModels };
};

// ======================
// API Keys Storage
// ======================

export const getAPIKeys = async (): Promise<{ keys?: {api_key?: string; base_url?: string}; error?: string }> => {
  const response = await get<LLMConfig>('/llm/admin/config/active');
  if (response.error || !response.data) {
    return { error: response.error || 'No active config found' };
  }
  return {
    keys: {
      api_key: response.data.api_key,
      base_url: response.data.base_url
    }
  };
};

export const updateAPIKeys = async (keys: {
  api_key?: string;
  base_url?: string;
}): Promise<{ success?: boolean; error?: string }> => {
  const activeConfig = await get<LLMConfig>('/llm/admin/config/active');
  if (activeConfig.error || !activeConfig.data) {
    return { error: activeConfig.error || 'No active config found' };
  }
  
  const response = await put<LLMConfig>(`/llm/admin/config/${activeConfig.data.id}`, keys);
  if (response.error) {
    return { error: response.error };
  }
  return { success: true };
};

// ======================
// Configuration Management
// ======================

export const getActiveLLMConfig = async (): Promise<{ config?: LLMConfig; error?: string }> => {
  const response = await get<LLMConfig>('/llm/admin/config/active');
  if (response.error) {
    return { error: response.error };
  }
  return { config: response.data };
};

export const getAllLLMConfigs = async (): Promise<{ configs?: LLMConfig[]; error?: string }> => {
  const response = await get<LLMConfig[]>('/llm/admin/config');
  if (response.error) {
    return { error: response.error };
  }
  return { configs: response.data };
};

export const createLLMConfig = async (config: {
  chat_provider: string;
  embedding_provider: string;
  model: string;
  embedding_model: string;
  system_prompt: string;
  api_key?: string;
  base_url?: string;
  temperature?: number; // Added temperature
  reranked_top_n?: number | null;
  config?: any;
}): Promise<{ config?: LLMConfig; error?: string }> => {
  const response = await post<LLMConfig>('/llm/admin/config', config);
  if (response.error) {
    return { error: response.error };
  }
  return { config: response.data };
};

export const updateLLMConfig = async (
  configId: string,
  config: {
    chat_provider?: string;
    embedding_provider?: string;
    model?: string;
    embedding_model?: string;
    system_prompt?: string;
    api_key?: string;
    base_url?: string;
    is_active?: boolean;
    temperature?: number; // Added temperature
    reranked_top_n?: number | null;
    config?: any;
  }
): Promise<{ config?: LLMConfig; error?: string }> => {
  const response = await put<LLMConfig>(`/llm/admin/config/${configId}`, config);
  if (response.error) {
    return { error: response.error };
  }
  return { config: response.data };
};

export const activateLLMConfig = async (configId: string): Promise<{ config?: LLMConfig; error?: string }> => {
  const response = await post<LLMConfig>(`/llm/admin/config/${configId}/activate`, {});
  if (response.error) {
    return { error: response.error };
  }
  return { config: response.data };
};

export const deleteLLMConfig = async (configId: string): Promise<{ success?: boolean; error?: string }> => {
  const response = await del(`/llm/admin/config/${configId}`);
  if (response.error) {
    return { error: response.error };
  }
  return { success: true };
};

// ======================
// Embedding Configuration
// ======================

export const getActiveEmbeddingConfig = async (): Promise<{ config?: EmbeddingConfig; error?: string }> => {
  const response = await get<EmbeddingConfig>('/llm/admin/embedding/config/active');
  if (response.error) {
    return { error: response.error };
  }
  return { config: response.data };
};

export const getAllEmbeddingConfigs = async (): Promise<{ configs?: EmbeddingConfig[]; error?: string }> => {
  const response = await get<EmbeddingConfig[]>('/llm/admin/embedding/config');
  if (response.error) {
    return { error: response.error };
  }
  return { configs: response.data };
};

export const createEmbeddingConfig = async (config: {
  provider: string;
  model: string;
  api_key?: string;
  base_url?: string;
  config?: any;
}): Promise<{ config?: EmbeddingConfig; error?: string }> => {
  const response = await post<EmbeddingConfig>('/llm/admin/embedding/config', config);
  if (response.error) {
    return { error: response.error };
  }
  return { config: response.data };
};

export const updateEmbeddingConfig = async (
  configId: string,
  config: {
    provider?: string;
    model?: string;
    api_key?: string;
    base_url?: string;
    is_active?: boolean;
    config?: any;
  }
): Promise<{ config?: EmbeddingConfig; error?: string }> => {
  const response = await put<EmbeddingConfig>(`/llm/admin/embedding/config/${configId}`, config);
  if (response.error) {
    return { error: response.error };
  }
  return { config: response.data };
};

export const activateEmbeddingConfig = async (configId: string): Promise<{ config?: EmbeddingConfig; error?: string }> => {
  const response = await post<EmbeddingConfig>(`/llm/admin/embedding/config/${configId}/activate`, {});
  if (response.error) {
    return { error: response.error };
  }
  return { config: response.data };
};

export const deleteEmbeddingConfig = async (configId: string): Promise<{ success?: boolean; error?: string }> => {
  const response = await del(`/llm/admin/embedding/config/${configId}`);
  if (response.error) {
    return { error: response.error };
  }
  return { success: true };
};

// ======================
// Reranking Configuration
// ======================

export const getActiveRerankingConfig = async (): Promise<{ config?: RerankingConfig; error?: string }> => {
  // Try the new endpoint first
  const response = await get<RerankingConfig>('/llm/admin/reranking/config/active');
  if (!response.error) {
    return { config: response.data };
  }
  
  // Fall back to the old endpoint if the new one fails
  const fallbackResponse = await get<RerankingConfig>('/reranking/active');
  if (fallbackResponse.error) {
    return { error: fallbackResponse.error };
  }
  return { config: fallbackResponse.data };
};

export const getAllRerankingConfigs = async (): Promise<{ configs?: RerankingConfig[]; error?: string }> => {
  // Try the new endpoint first
  const response = await get<RerankingConfig[]>('/llm/admin/reranking/config');
  if (!response.error) {
    return { configs: response.data };
  }
  
  // Fall back to the old endpoint if the new one fails
  const fallbackResponse = await get<RerankingConfig[]>('/reranking');
  if (fallbackResponse.error) {
    return { error: fallbackResponse.error };
  }
  return { configs: fallbackResponse.data };
};

export const createRerankingConfig = async (config: {
  provider: string;
  model: string;
  api_key?: string;
  base_url?: string;
  config?: any;
}): Promise<{ config?: RerankingConfig; error?: string }> => {
  // Try the new endpoint first
  const response = await post<RerankingConfig>('/llm/admin/reranking/config', config);
  if (!response.error) {
    return { config: response.data };
  }
  
  // Fall back to the old endpoint if the new one fails
  const fallbackResponse = await post<RerankingConfig>('/reranking', config);
  if (fallbackResponse.error) {
    return { error: fallbackResponse.error };
  }
  return { config: fallbackResponse.data };
};

export const updateRerankingConfig = async (
  configId: string,
  config: {
    provider?: string;
    model?: string;
    api_key?: string;
    base_url?: string;
    is_active?: boolean;
    config?: any;
  }
): Promise<{ config?: RerankingConfig; error?: string }> => {
  // Try the new endpoint first
  const response = await put<RerankingConfig>(`/llm/admin/reranking/config/${configId}`, config);
  if (!response.error) {
    return { config: response.data };
  }
  
  // Fall back to the old endpoint if the new one fails
  const fallbackResponse = await put<RerankingConfig>(`/reranking/${configId}`, config);
  if (fallbackResponse.error) {
    return { error: fallbackResponse.error };
  }
  return { config: fallbackResponse.data };
};

export const activateRerankingConfig = async (configId: string): Promise<{ config?: RerankingConfig; error?: string }> => {
  // Try the new endpoint first
  const response = await post<RerankingConfig>(`/llm/admin/reranking/config/${configId}/activate`, {});
  if (!response.error) {
    return { config: response.data };
  }
  
  // Fall back to the old endpoint if the new one fails
  const fallbackResponse = await post<RerankingConfig>(`/reranking/${configId}/activate`, {});
  if (fallbackResponse.error) {
    return { error: fallbackResponse.error };
  }
  return { config: fallbackResponse.data };
};

export const deleteRerankingConfig = async (configId: string): Promise<{ success?: boolean; error?: string }> => {
  // Try the new endpoint first
  const response = await del(`/llm/admin/reranking/config/${configId}`);
  if (!response.error) {
    return { success: true };
  }
  
  // Fall back to the old endpoint if the new one fails
  const fallbackResponse = await del(`/reranking/${configId}`);
  if (fallbackResponse.error) {
    return { error: fallbackResponse.error };
  }
  return { success: true };
};

// Get available reranking providers
export const getRerankingProviders = async (): Promise<{ providers?: RerankingProvider[]; error?: string }> => {
  // Use the new dedicated endpoint
  const response = await get<{ providers: RerankingProvider[] }>('/reranking/providers');
  if (response.error) {
    return { error: response.error };
  }
  return { providers: response.data?.providers || [] };
};