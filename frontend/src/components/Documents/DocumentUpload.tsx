import { useMutation, useQueryClient } from '@tanstack/react-query';
import { File, Upload, X } from 'lucide-react';
import { useState } from 'react';
import { uploadDocument } from '../../services/api';

export default function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setFile(null);
    },
  });

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (file) {
      uploadMutation.mutate(file);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold mb-4 text-gray-900">Upload Document</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <Upload className="mx-auto text-gray-400 mb-2" size={48} />
          
          {file ? (
            <div className="flex items-center justify-center space-x-2">
              <File size={20} className="text-blue-600" />
              <span className="text-sm text-gray-700">{file.name}</span>
              <button
                type="button"
                onClick={() => setFile(null)}
                className="text-red-500 hover:text-red-700"
              >
                <X size={16} />
              </button>
            </div>
          ) : (
            <>
              <input
                type="file"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                accept=".pdf,.docx,.csv,.xlsx,.txt,.md"
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer text-blue-600 hover:text-blue-700 font-medium"
              >
                Choose a file
              </label>
              <span className="text-gray-500"> or drag and drop</span>
              <p className="text-sm text-gray-500 mt-2">
                Supported: PDF, DOCX, CSV, XLSX, TXT, MD
              </p>
            </>
          )}
        </div>
        
        <button
          type="submit"
          disabled={!file || uploadMutation.isPending}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {uploadMutation.isPending ? 'Uploading...' : 'Upload Document'}
        </button>
        
        {uploadMutation.isError && (
          <p className="text-sm text-red-600">
            Error: {uploadMutation.error?.message || 'Upload failed'}
          </p>
        )}
        
        {uploadMutation.isSuccess && (
          <p className="text-sm text-green-600">Document uploaded successfully!</p>
        )}
      </form>
    </div>
  );
}