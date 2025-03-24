import React, { useState, useEffect } from 'react';
import { getChunkInfo } from '@/services/rag';

// Cache for document information to avoid redundant API calls
const chunkInfoCache: { [key: string]: {
  documentId: string,
  documentTitle: string,
  loading: boolean,
  error: boolean
} } = {};

interface DocumentReferencesProps {
  documentIds: string[];
}

const DocumentReferences: React.FC<DocumentReferencesProps> = ({ documentIds }) => {
  const [chunkInfo, setChunkInfo] = useState<{
    [key: string]: {
      documentId: string,
      documentTitle: string,
      loading: boolean,
      error: boolean
    }
  }>({});
  
  useEffect(() => {
    // Initialize state with cached values or defaults
    const initialState: {
      [key: string]: {
        documentId: string,
        documentTitle: string,
        loading: boolean,
        error: boolean
      }
    } = {};
    
    documentIds.forEach(chunkId => {
      if (chunkInfoCache[chunkId]) {
        // Use cached value if available
        initialState[chunkId] = chunkInfoCache[chunkId];
      } else {
        // Initialize with loading state
        initialState[chunkId] = {
          documentId: '',
          documentTitle: '',
          loading: true,
          error: false
        };
        
        // Fetch chunk information
        getChunkInfo(chunkId)
          .then(({ info, error }) => {
            // Log the response for debugging
            console.log(`Chunk info for ${chunkId}:`, { info, error });
            
            if (info) {
              // Update cache and state with document info
              const chunkData = {
                documentId: info.document_id,
                documentTitle: info.document_title,
                loading: false,
                error: false
              };
              console.log(`Setting chunk data for ${chunkId}:`, chunkData);
              chunkInfoCache[chunkId] = chunkData;
              setChunkInfo(prev => ({ ...prev, [chunkId]: chunkData }));
            } else {
              // Handle error
              console.error(`Error getting chunk info for ${chunkId}:`, error);
              const chunkData = {
                documentId: '',
                documentTitle: '',
                loading: false,
                error: true
              };
              chunkInfoCache[chunkId] = chunkData;
              setChunkInfo(prev => ({ ...prev, [chunkId]: chunkData }));
            }
          })
          .catch((err) => {
            // Handle fetch error
            console.error(`Exception getting chunk info for ${chunkId}:`, err);
            const chunkData = {
              documentId: '',
              documentTitle: '',
              loading: false,
              error: true
            };
            chunkInfoCache[chunkId] = chunkData;
            setChunkInfo(prev => ({ ...prev, [chunkId]: chunkData }));
          });
      }
    });
    
    setChunkInfo(initialState);
  }, [documentIds]);
  
  return (
    <div>
      <ul className="list-disc list-inside mb-2">
        {documentIds.map((chunkId, i) => {
          // Format the chunk ID for display
          const shortId = chunkId.length > 12 ? `${chunkId.substring(0, 8)}...` : chunkId;
          const info = chunkInfo[chunkId] || { documentId: '', documentTitle: '', loading: true, error: false };
          
          return (
            <li key={chunkId} className="text-gray-600 dark:text-gray-400 truncate mb-1">
              <span className="font-medium">Document {i + 1}:</span>{' '}
              {info.loading ? (
                <span className="text-gray-400">Loading...</span>
              ) : info.error || !info.documentTitle ? (
                // Fallback to just showing the chunk ID with a search link
                <>
                  <span>{shortId}</span>
                  <a
                    href={`/admin/documents?search=${chunkId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-xs"
                    title="Search for this document in admin"
                  >
                    Search in admin
                  </a>
                </>
              ) : (
                // Show document title and link when available
                <>
                  <span className="font-medium">{info.documentTitle}</span>
                  <a
                    href={`/admin/documents?search=${info.documentId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-xs"
                    title="View document in admin"
                  >
                    View document
                  </a>
                  <span className="text-gray-400 text-xs ml-1">({shortId})</span>
                </>
              )}
            </li>
          );
        })}
      </ul>
      <p className="text-xs text-gray-500 dark:text-gray-500 italic">
        Note: These IDs refer to document chunks used by the RAG system. The system will attempt to retrieve the original document titles, but some chunks may no longer exist in the database.
      </p>
    </div>
  );
};

export default DocumentReferences;
