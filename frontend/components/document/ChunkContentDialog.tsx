import React from 'react';
import { Dialog } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Scrollbar } from 'react-scrollbars-custom';
import { DocumentChunkDetail } from '@/types';

interface ChunkContentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  chunk: DocumentChunkDetail | null;
  isLoading: boolean;
}

const ChunkContentDialog: React.FC<ChunkContentDialogProps> = ({ isOpen, onClose, chunk, isLoading }) => {
  return (
    <Dialog isOpen={isOpen} onClose={onClose} title={`Chunk Detail: ${chunk?.id?.substring(0, 8) ?? ''}...`}>
      {isLoading ? (
        <div className="text-center p-4">Loading chunk content...</div>
      ) : chunk ? (
        <div className="space-y-4 max-h-[70vh]">
          <div>
            <h3 className="font-semibold text-gray-800 dark:text-gray-200">Chunk ID:</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 break-all">{chunk.id}</p>
          </div>
          <div>
            <h3 className="font-semibold text-gray-800 dark:text-gray-200">Document ID:</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 break-all">{chunk.document_id}</p>
          </div>
          <div>
            <h3 className="font-semibold text-gray-800 dark:text-gray-200">Chunk Index:</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">{chunk.chunk_index}</p>
          </div>
          <div>
            <h3 className="font-semibold text-gray-800 dark:text-gray-200">Content:</h3>
            <Scrollbar style={{ height: '40vh' }} className="w-full rounded-md border p-4 bg-gray-50 dark:bg-gray-900">
              <pre className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words">
                {chunk.content}
              </pre>
            </Scrollbar>
          </div>
          {chunk.meta_data && Object.keys(chunk.meta_data).length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-800 dark:text-gray-200">Metadata:</h3>
              <pre className="text-sm text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 p-2 rounded">
                {JSON.stringify(chunk.meta_data, null, 2)}
              </pre>
            </div>
          )}
          <div className="flex justify-end">
            <Button variant="outline" onClick={onClose}>Close</Button>
          </div>
        </div>
      ) : (
        <div className="text-center p-4 text-red-600">Could not load chunk content.</div>
      )}
    </Dialog>
  );
};

export default ChunkContentDialog;