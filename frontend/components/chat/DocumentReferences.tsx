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
  const [selectedDocumentTitle, setSelectedDocumentTitle] = useState<string | null>(null); // Add state for title
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
    setSelectedDocumentTitle(null); // Clear previous title
    setIsLoadingChunkDetail(true);
    setChunkDetailError(null); // Clear previous errors
    setShowChunkDialog(true);

    // Get the title from the already fetched chunkInfo state
    const title = chunkInfo[chunkId]?.documentTitle;
    setSelectedDocumentTitle(title || null); // Set the title state

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
            <li key={chunkId} className="text-gray-600 dark:text-gray-400 mb-1 flex items-center justify-between text-sm">
              <div className="flex-grow truncate mr-2"> {/* Wrap text content and allow truncation */}
                {info.loading ? (
                  <span className="text-gray-400 italic">Loading title...</span>
                ) : info.error || !info.documentTitle ? (
                  // Fallback to just showing the chunk ID if title fails
                  <span title={`Chunk ID: ${chunkId}`} className="font-mono text-xs">{shortId}</span>
                ) : (
                  // Show document title - chunk ID
                  <>
                    <span className="font-medium" title={`Document: ${info.documentTitle} (ID: ${info.documentId})`}>
                      {info.documentTitle}
                    </span>
                    <span className="text-gray-400 mx-1">-</span>
                    <span className="font-mono text-xs" title={`Chunk ID: ${chunkId}`}>{shortId}</span>
                  </>
                )}
              </div>
              {/* View Chunk Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleViewChunkContent(chunkId)}
                className="text-xs flex-shrink-0" // Prevent button from shrinking text
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
        documentTitle={selectedDocumentTitle} // Pass title to dialog
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
