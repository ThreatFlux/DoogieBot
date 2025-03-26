// Utility functions for LLM configuration components
import { ProviderConfig } from './types';

/**
 * Filters models based on a search term
 */
export const filterModels = (models: string[], searchTerm: string): string[] => {
  if (!searchTerm.trim()) {
    return models;
  }
  
  return models.filter(model => 
    model.toLowerCase().includes(searchTerm.toLowerCase())
  );
};

/**
 * Groups models by provider (for OpenRouter and other providers with provider prefixes)
 */
export const groupModelsByProvider = (models: string[]): Record<string, string[]> => {
  return models.reduce((acc: Record<string, string[]>, model: string) => {
    const [provider] = model.split('/');
    if (!acc[provider]) acc[provider] = [];
    acc[provider].push(model);
    return acc;
  }, {} as Record<string, string[]>);
};

/**
 * Determines if a server URL is needed for a provider
 */
export const getServerUrl = (providerId: string, providerConfig?: ProviderConfig): string | undefined => {
  if (!providerConfig) return undefined;
  
  if (providerId === 'ollama') {
    // Ollama requires a server URL
    return providerConfig.base_url || 'http://localhost:11434';
  } else if (providerId === 'openrouter') {
    // OpenRouter has a fixed base URL
    return 'https://openrouter.ai/api';
  }
  
  // Other providers don't need a base URL
  return undefined;
};

/**
 * Combines models for Ollama (which uses the same models for chat and embedding)
 */
export const combineOllamaModels = (chatModels: string[], embeddingModels: string[]): string[] => {
  return Array.from(new Set([...chatModels, ...embeddingModels]));
};