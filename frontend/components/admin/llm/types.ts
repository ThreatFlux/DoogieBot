// Types for LLM configuration components

export interface ProviderConfig {
  id: string;
  chatConfig: any | null;
  embeddingConfig: any | null;
  enabled: boolean;
  api_key: string;
  base_url: string;
  model: string;
  embedding_model: string;
  embedding_provider: string;
  system_prompt: string;
  available_models: string[];
  embedding_models: string[];
  isPolling: boolean;
}

export interface Provider {
  default_model: string;
  requires_api_key: boolean;
  requires_base_url: boolean;
}

export interface ChatConfig {
  id: string;
  chat_provider: string;
  model: string;
  system_prompt: string;
  is_active: boolean;
  config?: {
    rag_top_k?: number;
    use_reranking?: boolean;
    reranking_provider?: string;
    reranking_model?: string;
  };
}

export interface EmbeddingConfig {
  id: string;
  provider: string;
  model: string;
  is_active: boolean;
  base_url?: string;
}

export interface RerankingConfig {
  id: string;
  provider: string;
  model: string;
  is_active: boolean;
  base_url?: string;
}