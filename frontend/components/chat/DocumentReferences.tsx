import React, { useState, useEffect } from 'react';
import { getChunkInfo } from '@/services/rag'; // Keeps fetching doc title for context
import { getChunkDetail } from '@/services/document'; // For fetching chunk content
import { DocumentChunkDetail } from '@/types'; // Type for chunk detail
import ChunkContentDialog from '@/components/document/ChunkContentDialog'; // Import the dialog
import { Button } from '@/components/ui/Button'; // Import Button

// Cache for document information to avoid redundant API calls for titles
const chunkInfoCache: { [key: string]: {
  documentId: string,
  documentTitle: string,
  loading: boolean,
  error: boolean
} } = {};

interface DocumentReferencesProps {
  documentIds: string[]; // These are actually chunk IDs
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

  // State for chunk detail dialog
  const [showChunkDialog, setShowChunkDialog] = useState(false);
  const [selectedChunkDetail, setSelectedChunkDetail] = useState<DocumentChunkDetail | null>(null);
  const [isLoadingChunkDetail, setIsLoadingChunkDetail] = useState(false);
  const [chunkDetailError, setChunkDetailError] = useState<string | null>(null);


  useEffect(() => {
    // Initialize state with cached values or defaults for document titles
    const initialState: typeof chunkInfo = {};

    documentIds.forEach(chunkId => {
      if (chunkInfoCache[chunkId]) {
        initialState[chunkId] = chunkInfoCache[chunkId];
      } else {
        initialState[chunkId] = {
          documentId: '',
          documentTitle: '',
          loading: true,
          error: false
        };

        // Fetch chunk information (document title)
        getChunkInfo(chunkId)
          .then(({ info, error }) => {
            if (info) {
              const chunkData = {
                documentId: info.document_id,
                documentTitle: info.document_title,
                loading: false,
                error: false
              };
              chunkInfoCache[chunkId] = chunkData;
              // Use functional update to avoid race conditions if multiple fetches resolve closely
              setChunkInfo(prev => ({ ...prev, [chunkId]: chunkData }));
            } else {
              console.error(`Error getting chunk info for ${chunkId}:`, error);
              const chunkData = { documentId: '', documentTitle: '', loading: false, error: true };
              chunkInfoCache[chunkId] = chunkData;
              setChunkInfo(prev => ({ ...prev, [chunkId]: chunkData }));
            }
          })
          .catch((err) => {
            console.error(`Exception getting chunk info for ${chunkId}:`, err);
            const chunkData = { documentId: '', documentTitle: '', loading: false, error: true };
            chunkInfoCache[chunkId] = chunkData;
            setChunkInfo(prev => ({ ...prev, [chunkId]: chunkData }));
          });
      }
    });

    setChunkInfo(initialState);
  }, [documentIds]);

  // Handler to fetch and show chunk content
  const handleViewChunkContent = async (chunkId: string) => {
    setSelectedChunkDetail(null);
    setIsLoadingChunkDetail(true);
    setChunkDetailError(null); // Clear previous errors
    setShowChunkDialog(true);
    try {
      const { chunk, error } = await getChunkDetail(chunkId);
      if (error) {
        setChunkDetailError(`Failed to load chunk content: ${error}`);
        console.error(`Error fetching chunk detail for ${chunkId}:`, error);
      } else {
        setSelectedChunkDetail(chunk || null);
        if (!chunk) {
           setChunkDetailError('Chunk content not found.');
        }
      }
    } catch (err) {
      setChunkDetailError('An unexpected error occurred while loading chunk content.');
      console.error(`Exception fetching chunk detail for ${chunkId}:`, err);
    } finally {
      setIsLoadingChunkDetail(false);
    }
  };


  return (
    <div>
      <ul className="list-disc list-inside mb-2">
        {documentIds.map((chunkId, i) => {
          const shortId = chunkId.length > 12 ? `${chunkId.substring(0, 8)}...` : chunkId;
          const info = chunkInfo[chunkId] || { documentId: '', documentTitle: '', loading: true, error: false };

          return (
            <li key={chunkId} className="text-gray-600 dark:text-gray-400 truncate mb-1 flex items-center justify-between">
              <div> {/* Wrap text content */}
                <span className="font-medium">Context Chunk {i + 1}:</span>{' '}
                {info.loading ? (
                  <span className="text-gray-400">Loading title...</span>
                ) : info.error || !info.documentTitle ? (
                  // Fallback to just showing the chunk ID
                  <span title={`Chunk ID: ${chunkId}`}>{shortId}</span>
                ) : (
                  // Show document title and chunk ID when available
                  <>
                    <span className="font-medium" title={`From document: ${info.documentTitle} (ID: ${info.documentId})`}>
                      {info.documentTitle}
                    </span>
                    <span className="text-gray-400 text-xs ml-1" title={`Chunk ID: ${chunkId}`}>({shortId})</span>
                  </>
                )}
              </div>
              {/* Add View Chunk Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleViewChunkContent(chunkId)}
                className="ml-2 text-xs"
                title={`View content of chunk ${shortId}`}
              >
                View Chunk
              </Button>
            </li>
          );
        })}
      </ul>
      <p className="text-xs text-gray-500 dark:text-gray-500 italic">
        Note: These IDs refer to document chunks used by the RAG system. Click "View Chunk" to see the specific content used.
      </p>

      {/* Render the Chunk Content Dialog */}
      <ChunkContentDialog
        isOpen={showChunkDialog}
        onClose={() => setShowChunkDialog(false)}
        chunk={selectedChunkDetail}
        isLoading={isLoadingChunkDetail}
      />
      {/* Display error fetching chunk detail if any */}
      {chunkDetailError && (
         <p className="text-xs text-red-500 mt-1">{chunkDetailError}</p>
      )}
    </div>
  );
};

export default DocumentReferences;
