import { useQuery } from '@tanstack/react-query';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import { getSessionDocuments } from '../../services/api';

interface LinkedDocumentsProps {
  sessionId: string;
}

export default function LinkedDocuments({ sessionId }: LinkedDocumentsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const { data: documentsData } = useQuery({
    queryKey: ['session-documents', sessionId],
    queryFn: () => getSessionDocuments(sessionId),
    enabled: !!sessionId,
    retry: false,
  });

  if (!documentsData || documentsData.document_count === 0) {
    return null;
  }

  return (
    <div className="border-b border-gray-200 bg-gray-50 px-4 py-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between w-full text-sm text-gray-700 hover:text-gray-900"
      >
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-blue-600" />
          <span className="font-medium">
            {documentsData.document_count} document{documentsData.document_count !== 1 ? 's' : ''}{' '}
            linked to this chat
          </span>
        </div>
        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {isExpanded && (
        <div className="mt-2 space-y-1">
          {documentsData.documents.map((doc, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 px-2 py-1 text-xs text-gray-600 bg-white rounded border border-gray-200"
            >
              <FileText size={14} className="text-gray-400" />
              <span className="flex-1 truncate">{doc.filename}</span>
              <span className="text-gray-400">
                {(doc.size / 1024).toFixed(1)} KB
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
