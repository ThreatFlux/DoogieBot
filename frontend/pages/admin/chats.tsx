import { useEffect, useState, useCallback } from 'react'; // Added useCallback
import AdminLayout from '@/components/layout/AdminLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
// Removed RadioGroup and Label imports as they don't exist
import { getAdminFeedbackMessages, markMessageAsReviewed } from '@/services/chat'; // Updated service functions
import withAdmin from '@/utils/withAdmin';
import { Message, PaginatedResponse } from '@/types'; // Use Message and PaginatedResponse
import { useNotification } from '@/contexts/NotificationContext'; // For showing success/error messages

const ChatReview = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10); // Smaller page size
  const [totalPages, setTotalPages] = useState(1);
  const [totalMessages, setTotalMessages] = useState(0);
  const [filterReviewed, setFilterReviewed] = useState<boolean | undefined>(false); // Default to Not Reviewed
  const { showNotification } = useNotification();

  // Fetch messages when page or filter changes
  const loadMessages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data, error } = await getAdminFeedbackMessages({
        page: currentPage,
        pageSize: pageSize,
        reviewed: filterReviewed
      });
      
      if (data) {
        setMessages(data.items || []);
        setTotalMessages(data.total);
        setTotalPages(data.pages);
      } else if (error) {
        setError(error);
        showNotification(`Error loading messages: ${error}`, 'error');
      }
    } catch (err) {
      console.error('Failed to load messages:', err);
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to load messages: ${errorMsg}`);
      showNotification(`Failed to load messages: ${errorMsg}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, filterReviewed, showNotification]); // Dependencies for useCallback

  useEffect(() => {
    loadMessages();
  }, [loadMessages]); // useEffect depends on the memoized loadMessages

  // Handler for marking a message as reviewed
  const handleMarkAsReviewed = async (messageId: string) => {
    setError(null); // Clear previous errors
    try {
      const { message, error } = await markMessageAsReviewed(messageId);
      if (message) {
        showNotification('Message marked as reviewed', 'success');
        // Option 1: Optimistic update (faster UI)
        // setMessages(prevMessages =>
        //   prevMessages.map(msg =>
        //     msg.id === messageId ? { ...msg, reviewed: true } : msg
        //   )
        // );
        // Option 2: Refetch (simpler, ensures data consistency)
        loadMessages();
      } else if (error) {
        setError(error);
        showNotification(`Failed to mark as reviewed: ${error}`, 'error');
      }
    } catch (err) {
      console.error('Failed to mark message as reviewed:', err);
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to mark as reviewed: ${errorMsg}`);
      showNotification(`Failed to mark as reviewed: ${errorMsg}`, 'error');
    }
    // Removed incorrect catch block and else if from old handleDeleteChat
  };

  // --- Handlers for Pagination ---
  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  // --- Handler for Filter Change ---
  const handleFilterChange = (value: string) => {
    setCurrentPage(1); // Reset to first page on filter change
    if (value === 'all') {
      setFilterReviewed(undefined);
    } else if (value === 'reviewed') {
      setFilterReviewed(true);
    } else {
      setFilterReviewed(false); // 'not_reviewed'
    }
  };

  return (
    <AdminLayout title="Feedback Review" description="Review messages with feedback">
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Feedback Review</h1>
          
          {/* Filter Controls */}
          <div className="flex items-center space-x-4">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter by status:</span>
            <div className="flex items-center space-x-3">
              {/* Using standard HTML radio buttons */}
              <label className="flex items-center space-x-1 cursor-pointer">
                <input
                  type="radio"
                  name="reviewFilter"
                  value="not_reviewed"
                  checked={filterReviewed === false}
                  onChange={() => handleFilterChange('not_reviewed')}
                  className="form-radio h-4 w-4 text-primary-600 border-gray-300 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:focus:ring-offset-gray-800"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Not Reviewed</span>
              </label>
              <label className="flex items-center space-x-1 cursor-pointer">
                <input
                  type="radio"
                  name="reviewFilter"
                  value="reviewed"
                  checked={filterReviewed === true}
                  onChange={() => handleFilterChange('reviewed')}
                  className="form-radio h-4 w-4 text-primary-600 border-gray-300 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:focus:ring-offset-gray-800"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Reviewed</span>
              </label>
              <label className="flex items-center space-x-1 cursor-pointer">
                <input
                  type="radio"
                  name="reviewFilter"
                  value="all"
                  checked={filterReviewed === undefined}
                  onChange={() => handleFilterChange('all')}
                  className="form-radio h-4 w-4 text-primary-600 border-gray-300 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700 dark:focus:ring-offset-gray-800"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">All</span>
              </label>
            </div>
          </div>
        </div>
        
        {error && (
          <div className="p-4 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-md">
            {error}
          </div>
        )}
        
        {loading ? (
          <div className="text-center py-10">Loading messages...</div>
        ) : (
          <>
            {/* Messages List */}
            <div className="space-y-4">
              {messages.map((message) => ( // Use 'messages' state
                <Card key={message.id}>
                  <div className="p-4 space-y-3">
                    {/* Message Header */}
                    <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span>Chat ID: {message.chat_id}</span>
                      <span>Message ID: {message.id}</span>
                      <span>{new Date(message.created_at).toLocaleString()}</span>
                    </div>

                    {/* Message Content */}
                    <div className="border-t border-b border-gray-200 dark:border-gray-700 py-3">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        {message.role === 'user' ? 'User' : 'Assistant'} says:
                      </h4>
                      <p className="text-gray-900 dark:text-white whitespace-pre-wrap text-sm">
                        {message.content}
                      </p>
                    </div>

                    {/* Feedback Section */}
                    {message.feedback && (
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            message.feedback === 'positive' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                            'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                          }`}>
                            {message.feedback === 'positive' ? 'Positive' : 'Negative'} Feedback
                          </span>
                          {message.feedback_text && (
                            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 italic">
                              Comment: "{message.feedback_text}"
                            </p>
                          )}
                        </div>
                        
                        {/* Action Button */}
                        <div className="flex-shrink-0">
                          {message.reviewed ? (
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                              Reviewed
                            </span>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleMarkAsReviewed(String(message.id))} // Convert ID to string
                            >
                              Mark as Reviewed
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
              {messages.length === 0 && !loading && ( // Use 'messages' state
                <div className="text-center text-gray-500 dark:text-gray-400 py-10">
                  No messages found with the selected filter.
                </div>
              )}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6">
                <Button
                  variant="outline"
                  onClick={handlePreviousPage}
                  disabled={currentPage === 1 || loading}
                >
                  Previous
                </Button>
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Page {currentPage} of {totalPages} (Total: {totalMessages})
                </span>
                <Button
                  variant="outline"
                  onClick={handleNextPage}
                  disabled={currentPage === totalPages || loading}
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </AdminLayout>
  );
};

export default withAdmin(ChatReview, "Feedback Review"); // Updated title for HOC