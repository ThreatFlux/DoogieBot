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

async def _rerank_documents(reranking_client: LLMClient, query: str, documents: List[str]) -> List[float]:
    """
    Rerank documents based on their relevance to the query.

    Args:
        reranking_client: LLM client capable of reranking or embedding.
        query: User query.
        documents: List of document contents to rerank.

    Returns:
        List of relevance scores for each document.
    """
    if not documents:
        return []

    try:
        # If the reranking client has a specific rerank method, use it
        if hasattr(reranking_client, 'rerank'):
            logger.info(f"Using dedicated rerank method for query: {query[:50]}...")
            scores = await reranking_client.rerank(query, documents)
            logger.debug(f"Raw rerank scores: {scores}")
            return scores

        # Check if the client has embedding capabilities
        if hasattr(reranking_client, 'get_embeddings'):
            logger.info(f"Attempting reranking via embedding similarity for query: {query[:50]}...")
            # Use embeddings to calculate similarity
            try:
                query_embedding = await reranking_client.get_embeddings([query])
                if not query_embedding or len(query_embedding) == 0:
                    logger.warning("Failed to generate query embedding for reranking")
                    return []

                query_embedding = query_embedding[0]

                # Get embeddings for all documents
                doc_embeddings = await reranking_client.get_embeddings(documents)
                if not doc_embeddings or len(doc_embeddings) != len(documents):
                    logger.warning(f"Failed to generate document embeddings for reranking: got {len(doc_embeddings) if doc_embeddings else 0} for {len(documents)} documents")
                    return []

                # TODO: Implement cosine similarity calculation if needed, or assume client handles it.
                # For now, returning empty list if only embedding is available without explicit rerank.
                logger.warning("Reranking via embedding similarity not fully implemented, returning original order.")
                return []

            except Exception as e:
                logger.warning(f"Error using embeddings for reranking: {str(e)}")
                # Return empty scores, will fall back to original ranking
                return []
        else:
            logger.warning("Reranking client does not support embeddings, falling back to original ranking")
            return []

    except Exception as e:
        logger.error(f"Unexpected error during reranking: {str(e)}")
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
                # Use the dedicated reranking config directly
                logger.info(f"Reranking results using dedicated config: {reranking_config.provider}/{reranking_config.model}")
                try:
                    # Create reranking client using details from RerankingConfig
                    reranking_client = LLMFactory._create_single_client(
                        provider=reranking_config.provider,
                        model=reranking_config.model,
                        api_key=reranking_config.api_key, # Use key from reranking_config
                        base_url=reranking_config.base_url # Use URL from reranking_config
                    )

                    if not reranking_client:
                        logger.warning("Failed to create reranking client using _create_single_client")
                    else:
                        documents = [doc["content"] for doc in context]
                        logger.info(f"--- Documents before reranking for query '{query[:50]}...' ---")
                        for i, doc in enumerate(context):
                            logger.info(f"  {i+1}. ID: {doc.get('id')}, Source: {doc.get('source')}, Initial Score: {doc.get('score'):.4f}, Content: {doc.get('content', '')[:100]}...")
                        logger.info("---------------------------------------------------------")

                        reranked_scores = await _rerank_documents(reranking_client, query, documents)

                        if reranked_scores and len(reranked_scores) == len(context):
                            for i, score in enumerate(reranked_scores):
                                context[i]["score"] = score
                            context.sort(key=lambda x: x["score"], reverse=True)
                            logger.info(f"Successfully reranked {len(context)} documents.")
                            logger.info(f"--- Documents after reranking for query '{query[:50]}...' ---")
                            for i, doc in enumerate(context):
                                logger.info(f"  {i+1}. ID: {doc.get('id')}, Source: {doc.get('source')}, Reranked Score: {doc.get('score'):.4f}, Content: {doc.get('content', '')[:100]}...")
                            logger.info("--------------------------------------------------------")

                        else:
                            logger.warning(f"Reranking returned {len(reranked_scores) if reranked_scores else 0} scores for {len(context)} documents. Using original ranking.")
                except Exception as e:
                    logger.error(f"Error during reranking process: {str(e)}")
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