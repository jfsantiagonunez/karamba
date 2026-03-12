import { useQuery } from '@tanstack/react-query';
import { listDocuments } from '../../services/api';
import { FileText } from 'lucide-react';

export default function DocumentLibrary() {
  const { data, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-4">Document Library</h2>
      {data?.documents && data.documents.length > 0 ? (
        <div className="space-y-2">
          {data.documents.map((doc) => (
            <div key={doc.filename} className="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg">
              <FileText size={20} className="text-gray-400" />
              <span className="flex-1">{doc.filename}</span>
              <span className="text-sm text-gray-500">
                {(doc.size / 1024).toFixed(1)} KB
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-500">No documents uploaded yet</p>
      )}
    </div>
  );
}