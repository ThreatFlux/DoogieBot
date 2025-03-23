"""
Search functionality for the GraphRAG implementation.
"""

from typing import List, Dict, Any, Optional
import logging
import time
import gc
import random

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_graph(
    graph,
    query: str,
    node_types: Optional[List[str]] = None,
    relation_types: Optional[List[str]] = None,
    max_results: int = 5,
    fast_mode: bool = True
) -> List[Dict[str, Any]]:
    """
    Search the graph for nodes matching the query.
    
    Args:
        graph: GraphRAG graph
        query: Search query
        node_types: Optional list of node types to filter by
        relation_types: Optional list of relation types to filter by
        max_results: Maximum number of results to return
        fast_mode: Whether to use fast mode (limited semantic search)
        
    Returns:
        List of matching nodes
    """
    # Force garbage collection before starting search to free memory
    gc.collect()
    
    start_time = time.time()
    logger.info(f"Searching graph for: {query}")
    
    try:
        # Check if we're using the actual GraphRAG library
        if hasattr(graph, 'search'):
            # GraphRAG library method
            results = graph.search(
                query=query,
                node_types=node_types,
                relation_types=relation_types,
                max_results=max_results,
                fast_mode=fast_mode
            )
            
            total_time = time.time() - start_time
            logger.info(f"GraphRAG search completed in {total_time:.2f}s. Found {len(results)} matches")
            
            return results
        else:
            # Fallback implementation
            return _fallback_search(
                graph, 
                query, 
                node_types, 
                relation_types, 
                max_results, 
                fast_mode
            )
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        # Return empty list on error
        return []

def _fallback_search(
    graph,
    query: str,
    node_types: Optional[List[str]] = None,
    relation_types: Optional[List[str]] = None,
    max_results: int = 5,
    fast_mode: bool = True
) -> List[Dict[str, Any]]:
    """
    Fallback search implementation when GraphRAG library is not available.
    """
    query_lower = query.lower()
    
    # Step 1: Initial keyword matching
    direct_matches = _perform_keyword_matching(
        graph, query_lower, node_types, max_results
    )
    
    keyword_time = time.time()
    logger.info(f"Keyword matching completed, found {len(direct_matches)} matches")
    
    # If we have enough direct matches, skip semantic search to save memory
    if len(direct_matches) >= max_results:
        logger.info(f"Found {len(direct_matches)} direct matches, skipping semantic search")
        direct_matches.sort(key=lambda x: x['score'], reverse=True)
        return direct_matches[:max_results]
    
    # Step 2: Add semantic matches if we have few direct matches
    semantic_matches = []
    if len(direct_matches) < max_results and not fast_mode:
        semantic_matches = _perform_semantic_matching(
            graph, query, direct_matches, node_types
        )
        
        logger.info(f"Semantic matching completed, found {len(semantic_matches)} matches")
    
    # Combine direct and semantic matches
    all_matches = direct_matches + semantic_matches
    
    # Skip connected nodes search if we have enough matches
    if len(all_matches) >= max_results:
        all_matches.sort(key=lambda x: x['score'], reverse=True)
        return all_matches[:max_results]
    
    # Step 3: Add connected nodes to high-scoring matches
    connected_matches = []
    if all_matches:
        connected_matches = _find_connected_nodes(
            graph, all_matches, node_types, relation_types
        )
        
        logger.info(f"Connected node matching completed, found {len(connected_matches)} matches")
    
    # Combine all results, sort by score, and limit
    results = all_matches + connected_matches
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Force garbage collection again
    gc.collect()
    
    total_time = time.time() - start_time
    logger.info(f"Total search completed in {total_time:.2f}s. Found {len(results)} matches")
    
    return results[:max_results]

def _perform_keyword_matching(graph, query_lower, node_types, max_results):
    """Perform keyword matching on the graph."""
    direct_matches = []
    query_terms = query_lower.split()
    
    # Sample nodes for search if there are many
    nodes = graph["nodes"]
    if len(nodes) > 500:
        sample_size = 500
        sampled_node_ids = random.sample(list(nodes.keys()), sample_size)
        nodes_to_search = {node_id: nodes[node_id] for node_id in sampled_node_ids}
    else:
        nodes_to_search = nodes
    
    # Perform keyword matching
    for node_id, node_data in nodes_to_search.items():
        # Skip if we already have enough direct matches
        if len(direct_matches) >= max_results * 2:
            break
            
        content = node_data.get('content', '').lower()
        node_type = node_data.get('type')
        
        # Filter by node type if specified
        if node_types and node_type not in node_types:
            continue
        
        # Quick check if any query term is in content
        if any(term in content for term in query_terms):
            # Check if full query is in content
            if query_lower in content:
                # Calculate a simple relevance score based on position and frequency
                position = content.find(query_lower)
                frequency = content.count(query_lower)
                # Better scoring formula that considers both position and frequency
                score = (frequency * 0.5) + (1.0 / (position + 1) * 0.5)
                
                direct_matches.append({
                    'id': node_id,
                    'content': node_data.get('content'),
                    'type': node_type,
                    'score': score,
                    'metadata': node_data.get('metadata', {}),
                    'match_type': 'direct'
                })
    
    return direct_matches

def _perform_semantic_matching(graph, query, direct_matches, node_types):
    """Perform semantic matching using TF-IDF."""
    semantic_matches = []
    
    try:
        # Extract query terms (excluding common words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
        filtered_query_terms = [term.lower() for term in query.split() if term.lower() not in stop_words]
        
        # If we have meaningful query terms
        if filtered_query_terms:
            # Use a limited sample for semantic search
            max_nodes_for_tfidf = 200
            
            # Get node contents for TF-IDF
            node_contents = []
            node_ids = []
            
            # First, try to find nodes that contain at least one query term
            count = 0
            for node_id, node_data in graph["nodes"].items():
                # Skip nodes already in direct matches
                if any(match['id'] == node_id for match in direct_matches):
                    continue
                    
                # Filter by node type if specified
                node_type = node_data.get('type')
                if node_types and node_type not in node_types:
                    continue
                
                content = node_data.get('content', '').lower()
                
                # Check if any query term is in the content
                if any(term in content for term in filtered_query_terms):
                    node_contents.append(content)
                    node_ids.append(node_id)
                    count += 1
                    
                    if count >= max_nodes_for_tfidf:
                        break
            
            # If we don't have enough nodes, add some random ones
            if count < min(50, max_nodes_for_tfidf):
                remaining_nodes = list(set(graph["nodes"].keys()) - set(node_ids) - set(match['id'] for match in direct_matches))
                if remaining_nodes:
                    sample_size = min(max_nodes_for_tfidf - count, len(remaining_nodes))
                    sampled_nodes = random.sample(remaining_nodes, sample_size)
                    
                    for node_id in sampled_nodes:
                        node_data = graph["nodes"][node_id]
                        node_type = node_data.get('type')
                        
                        if node_types and node_type not in node_types:
                            continue
                            
                        node_contents.append(node_data.get('content', ''))
                        node_ids.append(node_id)
                        count += 1
            
            logger.info(f"Selected {len(node_contents)} nodes for semantic search")
            
            # If we have nodes to compare against
            if node_contents:
                # Import TF-IDF here to reduce memory usage when not needed
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                
                # Add query to the corpus
                all_texts = node_contents + [query]
                
                # Create TF-IDF vectorizer
                vectorizer = TfidfVectorizer(
                    min_df=1,
                    stop_words='english',
                    lowercase=True,
                    max_features=500
                )
                
                # Compute TF-IDF vectors
                tfidf_matrix = vectorizer.fit_transform(all_texts)
                
                # Get query vector (last one)
                query_vector = tfidf_matrix[-1]
                
                # Compute similarity between query and each node
                similarities = cosine_similarity(query_vector, tfidf_matrix[:-1])[0]
                
                # Add semantic matches
                similarity_threshold = 0.3
                for i, similarity in enumerate(similarities):
                    if similarity > similarity_threshold:
                        node_id = node_ids[i]
                        node_data = graph["nodes"][node_id]
                        node_type = node_data.get('type')
                        
                        semantic_matches.append({
                            'id': node_id,
                            'content': node_data.get('content'),
                            'type': node_type,
                            'score': float(similarity) * 0.8,  # Scale semantic matches slightly lower
                            'metadata': node_data.get('metadata', {}),
                            'match_type': 'semantic'
                        })
                
                # Clean up to free memory
                del tfidf_matrix
                del vectorizer
                del similarities
                gc.collect()
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")
    
    return semantic_matches

def _find_connected_nodes(graph, all_matches, node_types, relation_types):
    """Find connected nodes to the top matches."""
    connected_matches = []
    
    # Get top matches to expand
    top_matches = sorted(all_matches, key=lambda x: x['score'], reverse=True)[:min(2, len(all_matches))]
    
    # Limit the number of neighbors to check per match
    max_neighbors_to_check = 10
    
    for match in top_matches:
        # Get neighbors with high edge weights
        neighbors_checked = 0
        
        for neighbor_id in graph["neighbors"].get(match['id'], []):
            # Limit the number of neighbors we check
            neighbors_checked += 1
            if neighbors_checked > max_neighbors_to_check:
                break
                
            # Skip if already in results
            if any(r['id'] == neighbor_id for r in all_matches) or any(r['id'] == neighbor_id for r in connected_matches):
                continue
            
            # Get edge data
            edge_key = (match['id'], neighbor_id)
            edge_data = graph["edges"].get(edge_key, {})
            
            relation = edge_data.get('relation')
            weight = edge_data.get('weight', 0.5)
            
            # Filter by relation type if specified
            if relation_types and relation not in relation_types:
                continue
            
            # Only include high-weight connections
            if weight > 0.5:
                node_data = graph["nodes"].get(neighbor_id, {})
                node_type = node_data.get('type')
                
                # Filter by node type if specified
                if node_types and node_type not in node_types:
                    continue
                
                # Add connected node with score based on original match and edge weight
                connected_matches.append({
                    'id': neighbor_id,
                    'content': node_data.get('content'),
                    'type': node_type,
                    'score': match['score'] * weight * 0.7,  # Scale connected matches lower
                    'metadata': node_data.get('metadata', {}),
                    'match_type': 'connected',
                    'connected_to': match['id'],
                    'relation': relation
                })
    
    return connected_matches