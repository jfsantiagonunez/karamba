import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Database, FileText, Trash2, MessageSquare } from 'lucide-react';
import { deleteDocument, listDocuments } from '../../services/api';

export default function DocumentLibrary() {
  const queryClient = useQueryClient();
  
  const { data, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold mb-4 text-gray-900">Document Library</h2>
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Document Library</h2>
        {data?.stats && (
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <Database size={16} />
            <span>{data.stats.total_chunks} chunks indexed</span>
          </div>
        )}
      </div>
      
      {data?.documents && data.documents.length > 0 ? (
        <div className="space-y-2">
          {data.documents.map((doc) => (
            <div
              key={doc.filename}
              className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center space-x-3 flex-1">
                <FileText size={20} className="text-gray-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {doc.filename}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(doc.size)} • {formatDate(doc.modified)}
                  </p>
                  {doc.linked_sessions && doc.linked_sessions.length > 0 && (
                    <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                      <MessageSquare size={12} className="text-blue-500" />
                      <span className="text-xs text-blue-600">
                        Linked to:{' '}
                        {doc.linked_sessions.map((session, idx) => (
                          <span key={session.session_id}>
                            {session.title}
                            {idx < doc.linked_sessions.length - 1 ? ', ' : ''}
                          </span>
                        ))}
                      </span>
                    </div>
                  )}
                  {(!doc.linked_sessions || doc.linked_sessions.length === 0) && (
                    <p className="text-xs text-gray-400 mt-1">
                      Not linked to any chat
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={() => deleteMutation.mutate(doc.filename)}
                disabled={deleteMutation.isPending}
                className="ml-2 p-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                title="Delete document"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8">
          <FileText size={48} className="mx-auto text-gray-300 mb-2" />
          <p className="text-gray-500">No documents uploaded yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Upload a document to get started
          </p>
        </div>
      )}
    </div>
  );
}