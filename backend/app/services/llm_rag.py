import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# Assuming LLMClient is the base class or protocol for clients
from app.llm.base import LLMClient
from app.llm.factory import LLMFactory
from app.rag.hybrid_retriever import HybridRetriever
from app.services.llm_config import LLMConfigService
from app.services.reranking_config import RerankingConfigService

logger = logging.getLogger(__name__)

from app.schemas.reranking import RerankingConfig # Import the schema
from sentence_transformers import CrossEncoder # Import CrossEncoder

# Cache for loaded CrossEncoder models
_cross_encoder_cache: Dict[str, CrossEncoder] = {}

async def _rerank_documents(reranking_config: RerankingConfig, query: str, documents: List[str]) -> List[float]:
    """
    Rerank documents based on their relevance to the query using a configured reranker.
    Currently supports local CrossEncoder models loaded via sentence-transformers.

    Args:
        reranking_config: The active reranking configuration object.
        query: User query.
        documents: List of document contents to rerank.

    Returns:
        List of relevance scores for each document, or empty list if reranking fails or is not supported.
    """
    if not documents:
        return []

    # --- Local Cross-Encoder Reranking ---
    # Check if the model name suggests a cross-encoder/reranker model
    # This is a heuristic; ideally, the config would have a 'type' field.
    model_name = reranking_config.model
    if "rerank" in model_name.lower():
        logger.info(f"Attempting local cross-encoder reranking using model: {model_name}")
        try:
            # Load model (with caching)
            if model_name not in _cross_encoder_cache:
                logger.info(f"Loading CrossEncoder model '{model_name}' into cache...")
                # You might need to specify device='cuda' if GPU is available and configured
                _cross_encoder_cache[model_name] = CrossEncoder(model_name, max_length=512) # max_length might need tuning
                logger.info(f"Successfully loaded '{model_name}'.")
            model = _cross_encoder_cache[model_name]

            # Prepare pairs for the cross-encoder
            pairs: List[List[str]] = [[query, doc] for doc in documents]
            logger.info(f"Predicting scores for {len(pairs)} query-document pairs...")

            # Predict scores - This is CPU/GPU intensive
            # Consider running in a separate thread/process for async environments if it blocks
            # For simplicity, running synchronously here.
            # Use asyncio.to_thread in Python 3.9+ if blocking becomes an issue:
            # scores = await asyncio.to_thread(model.predict, pairs, show_progress_bar=False) # show_progress_bar optional
            scores = model.predict(pairs, show_progress_bar=False) # show_progress_bar optional

            logger.info(f"Successfully predicted {len(scores)} scores using local cross-encoder.")
            # Ensure scores are float
            scores_float = [float(score) for score in scores]
            return scores_float

        except ImportError:
             logger.error("`sentence-transformers` library not found. Cannot perform local cross-encoder reranking. Please install it.")
             return []
        except Exception as e:
            logger.error(f"Error during local cross-encoder reranking with model '{model_name}': {str(e)}", exc_info=True)
            # If the model failed (e.g., not found locally, download error), remove from cache
            if model_name in _cross_encoder_cache:
                 del _cross_encoder_cache[model_name]
            return []
    else:
        # --- Fallback / Other Reranker Types (Placeholder) ---
        logger.warning(f"Model '{model_name}' doesn't appear to be a known local cross-encoder format.")
        logger.warning("Attempting fallback: Checking for dedicated client rerank method (e.g., Cohere)...")

        # Placeholder: If we add other clients (like Cohere) with a .rerank method,
        # we would instantiate the client here using reranking_config details
        # and call its .rerank method.
        # Example (if CohereClient existed):
        # try:
        #     client = LLMFactory._create_single_client(
        #         provider=reranking_config.provider,
        #         model=reranking_config.model,
        #         api_key=reranking_config.api_key,
        #         base_url=reranking_config.base_url
        #     )
        #     if hasattr(client, 'rerank'):
        #          logger.info(f"Using dedicated rerank method for provider {reranking_config.provider}...")
        #          scores = await client.rerank(query, documents)
        #          return [float(s) for s in scores]
        #     else:
        #          logger.warning(f"Provider {reranking_config.provider} client has no dedicated rerank method.")
        # except Exception as client_err:
        #     logger.error(f"Failed to create or use client for provider {reranking_config.provider}: {client_err}")

        logger.warning("No dedicated rerank method found or implemented for this configuration. Reranking skipped.")
        return []


async def get_rag_context(
    db: Session,
    embedding_client: LLMClient,
    retriever: HybridRetriever,
    query: str,
    top_k: Optional[int] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Get relevant context for RAG, including optional reranking.

    Args:
        db: Database session.
        embedding_client: LLM client capable of generating embeddings.
        retriever: HybridRetriever instance.
        query: User query.
        top_k: Number of results to return (optional, uses config value if not provided).

    Returns:
        List of relevant documents (potentially reranked) or None.
    """
    # Get active LLM config for RAG settings
    active_llm_config = LLMConfigService.get_active_config(db)

    # Determine top_k
    if top_k is None:
        if active_llm_config and active_llm_config.config and 'rag_top_k' in active_llm_config.config:
            top_k = active_llm_config.config.get('rag_top_k')
        else:
            top_k = 3 # Default

    try:
        # Generate query embedding
        logger.info(f"Generating embedding for query: {query[:50]}...")
        query_embedding = None
        try:
            embeddings = await embedding_client.get_embeddings([query])
            if embeddings and len(embeddings) > 0:
                query_embedding = embeddings[0]
                logger.info(f"Successfully generated query embedding with dimension {len(query_embedding)}")
            else:
                logger.warning("Failed to generate query embedding: empty result")
        except Exception as embed_error:
            logger.error(f"Error generating query embedding: {str(embed_error)}")
            # Continue with keyword search even if embedding fails

        # Retrieve relevant documents
        results = await retriever.retrieve(
            query=query,
            query_embedding=query_embedding,
            top_k=top_k
        )

        if not results:
            return None

        # Format results for context
        context = []
        for result in results:
            context.append({
                "id": result.get("id"),
                "content": result.get("content"),
                "score": result.get("score", 0),
                "source": result.get("source")
            })

        # Apply reranking if enabled
        use_reranking = active_llm_config and active_llm_config.config and active_llm_config.config.get('use_reranking', False)
        if use_reranking and context:
            reranking_config = RerankingConfigService.get_active_config(db)

            if reranking_config:
                documents_content = [doc["content"] for doc in context]
                logger.info(f"--- Documents before reranking for query '{query[:50]}...' ---")
                for i, doc in enumerate(context):
                    logger.info(f"  {i+1}. ID: {doc.get('id')}, Source: {doc.get('source')}, Initial Score: {doc.get('score'):.4f}, Content: {doc.get('content', '')[:100]}...")
                logger.info("---------------------------------------------------------")

                # Pass the config object, not a client
                reranked_scores = await _rerank_documents(reranking_config, query, documents_content)

                if reranked_scores and len(reranked_scores) == len(context):
                    for i, score in enumerate(reranked_scores):
                        context[i]["score"] = score # Apply new scores
                    context.sort(key=lambda x: x["score"], reverse=True) # Sort by new scores
                    logger.info(f"Successfully reranked {len(context)} documents using '{reranking_config.model}'.")
                    logger.info(f"--- Documents after reranking for query '{query[:50]}...' ---")
                    for i, doc in enumerate(context):
                        logger.info(f"  {i+1}. ID: {doc.get('id')}, Source: {doc.get('source')}, Reranked Score: {doc.get('score'):.4f}, Content: {doc.get('content', '')[:100]}...")
                    logger.info("--------------------------------------------------------")
                else:
                    logger.warning(f"Reranking process with '{reranking_config.model}' returned {len(reranked_scores) if reranked_scores else 0} scores for {len(context)} documents. Using original ranking.")
            # If no dedicated reranking config is active, check the main LLM config flag
            elif active_llm_config and active_llm_config.config and active_llm_config.config.get('use_reranking', False):
                logger.warning("Reranking enabled in main LLM config, but no active dedicated reranking configuration found in the database. Skipping reranking.")

        # Apply reranked_top_n limit AFTER reranking attempt (success or failure)
        reranked_top_n = getattr(active_llm_config, 'reranked_top_n', None)
        if reranked_top_n is not None and reranked_top_n > 0:
            if len(context) > reranked_top_n:
                logger.info(f"Applying final reranked_top_n limit: {reranked_top_n} (truncated from {len(context)})")
                context = context[:reranked_top_n]
            else:
                logger.info(f"Final reranked_top_n limit ({reranked_top_n}) is >= number of documents ({len(context)}), keeping all.")
        else:
            # If no specific limit, default to rag_top_k or the number retrieved if rag_top_k is also missing
            final_limit = top_k # top_k was determined earlier from rag_top_k or default
            if len(context) > final_limit:
                logger.info(f"Applying default limit (rag_top_k): {final_limit} (truncated from {len(context)})")
                context = context[:final_limit]
            else:
                logger.info(f"No reranked_top_n limit set, keeping all {len(context)} documents (within rag_top_k limit of {final_limit}).")

        return context

    except Exception as e:
        logger.error(f"Error getting RAG context: {str(e)}")
        return None