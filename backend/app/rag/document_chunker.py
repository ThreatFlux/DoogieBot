import json # Add json import
from typing import List, Dict, Any, Optional
import re

class DocumentChunker:
    """
    Chunker for splitting documents into smaller pieces for indexing.
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the chunker with chunk size and overlap.
        
        Args:
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Split text into chunks with specified size and overlap.
        
        Args:
            text: The text to chunk
            metadata: Optional metadata to include with each chunk
            
        Returns:
            List of dictionaries containing chunk content and metadata
        """
        if not text:
            return []
        
        chunks = []
        
        # Split text into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = []
        current_size = 0
        
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            # If adding this paragraph would exceed chunk size and we already have content,
            # create a new chunk
            if current_size + para_size > self.chunk_size and current_chunk:
                # Join the current chunk and add it to the list
                chunk_text = "\n\n".join(current_chunk)
                chunk_meta = self._create_chunk_metadata(metadata, i, len(chunks))
                
                chunks.append({
                    "content": chunk_text,
                    "metadata": chunk_meta
                })
                
                # Start a new chunk with overlap
                overlap_size = max(0, len(current_chunk) - 1)
                current_chunk = current_chunk[-overlap_size:] if overlap_size > 0 else []
                current_size = sum(len(p) for p in current_chunk)
            
            # Add the paragraph to the current chunk
            current_chunk.append(para)
            current_size += para_size
        
        # Add the last chunk if there's anything left
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunk_meta = self._create_chunk_metadata(metadata, len(paragraphs), len(chunks))
            
            chunks.append({
                "content": chunk_text,
                "metadata": chunk_meta
            })
        
        return chunks
    
    def _create_chunk_metadata(self, metadata: Optional[Dict[str, Any]], position: int, chunk_index: int) -> Dict[str, Any]:
        """
        Create metadata for a chunk.
        
        Args:
            metadata: Original document metadata
            position: Position in the original document
            chunk_index: Index of the chunk
            
        Returns:
            Dictionary with chunk metadata
        """
        chunk_meta = {
            "chunk_index": chunk_index,
            "position": position
        }
        
        # Include original metadata if provided, excluding the large parsed_json object
        if metadata:
            # Create a copy to avoid modifying the original metadata dict
            meta_copy = metadata.copy()
            meta_copy.pop("parsed_json", None) # Remove parsed_json if it exists
            chunk_meta.update(meta_copy)
        
        return chunk_meta
    
    def _chunk_json_structure(self, parsed_data: Any, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk JSON data based on its structure.
        Currently handles lists of objects by creating a chunk per object.
        Handles single objects by creating one chunk for the whole object.
        Other JSON types (e.g., list of strings) are serialized as a single chunk.

        Args:
            parsed_data: The parsed JSON data (list or dict)
            metadata: Original document metadata

        Returns:
            List of chunks specific to JSON structure.
        """
        chunks = []
        chunk_index = 0

        if isinstance(parsed_data, list):
            # If it's a list, iterate through elements
            for i, item in enumerate(parsed_data):
                try:
                    # Convert item back to compact JSON string
                    chunk_content = json.dumps(item, separators=(',', ':'))

                    # TODO: Add optional check for chunk_content length > self.chunk_size
                    # and implement sub-chunking or warning/skipping logic if needed.

                    # Create metadata for this chunk
                    # Position 'i' represents the index in the original JSON list
                    chunk_meta = self._create_chunk_metadata(metadata, position=i, chunk_index=chunk_index)
                    # Optionally add JSON path: chunk_meta['json_path'] = f'[{i}]'

                    chunks.append({
                        "content": chunk_content,
                        "metadata": chunk_meta
                    })
                    chunk_index += 1
                except TypeError as e:
                    print(f"Warning: Could not serialize JSON item at index {i}: {e}. Skipping.")
                    continue

        elif isinstance(parsed_data, dict):
            # If it's a single dictionary object, treat it as one chunk
            try:
                chunk_content = json.dumps(parsed_data, separators=(',', ':'))
                # TODO: Add optional check for chunk_content length > self.chunk_size

                chunk_meta = self._create_chunk_metadata(metadata, position=0, chunk_index=chunk_index)
                # Optionally add JSON path: chunk_meta['json_path'] = '$'

                chunks.append({
                    "content": chunk_content,
                    "metadata": chunk_meta
                })
                chunk_index += 1
            except TypeError as e:
                print(f"Warning: Could not serialize JSON object: {e}. Skipping.")

        else:
            # Handle other valid JSON types (string, number, boolean, null) or fallback
            # Serialize the whole thing as one chunk
            try:
                chunk_content = json.dumps(parsed_data, separators=(',', ':'))
                chunk_meta = self._create_chunk_metadata(metadata, position=0, chunk_index=chunk_index)
                chunks.append({
                    "content": chunk_content,
                    "metadata": chunk_meta
                })
                chunk_index += 1
            except TypeError as e:
                 print(f"Warning: Could not serialize non-list/dict JSON data: {e}. Skipping.")

        if not chunks:
             print(f"Warning: No chunks created for JSON document with metadata: {metadata.get('document_id', 'N/A')}. Input type: {type(parsed_data)}")
             # Optionally fall back to text chunking on the original content string if needed

        return chunks

    def chunk_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk a document based on its content and metadata.
        Routes JSON documents to a specialized chunker.
        
        Args:
            content: Document content (string representation)
            metadata: Document metadata (may include parsed_json)
            
        Returns:
            List of chunks with content and metadata
        """
        # Check if it's JSON and we have the parsed data
        if metadata and metadata.get("format") == "json" and "parsed_json" in metadata:
            parsed_data = metadata.get("parsed_json")
            if parsed_data is not None:
                 # Pass the parsed data and original metadata (excluding parsed_json for chunk meta)
                return self._chunk_json_structure(parsed_data, metadata)
            else:
                # Fallback if parsed_json is None for some reason
                print(f"Warning: JSON format indicated but parsed_json is None. Falling back to text chunking for document: {metadata.get('document_id', 'N/A')}")
                return self.chunk_text(content, metadata)
        else:
            # For all other document types or if parsed_json is missing
            return self.chunk_text(content, metadata)