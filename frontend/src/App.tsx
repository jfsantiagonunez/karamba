import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FileText, MessageSquare } from 'lucide-react';
import { useState } from 'react';
import ChatLayout from './components/Chat/ChatLayout';
import DocumentLibrary from './components/Documents/DocumentLibrary';
import DocumentUpload from './components/Documents/DocumentUpload';

const queryClient = new QueryClient();

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'documents'>('chat');

  return (
    <QueryClientProvider client={queryClient}>
      <div className="h-screen flex flex-col bg-gray-50">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">K</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Karamba</h1>
                <p className="text-sm text-gray-600">Personal Research Assistant</p>
              </div>
            </div>
            
            {/* Tab Navigation */}
            <div className="flex space-x-2 bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setActiveTab('chat')}
                className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
                  activeTab === 'chat'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <MessageSquare size={18} />
                <span>Chat</span>
              </button>
              <button
                onClick={() => setActiveTab('documents')}
                className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
                  activeTab === 'documents'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <FileText size={18} />
                <span>Documents</span>
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-hidden">
          {activeTab === 'chat' ? (
            <ChatLayout />
          ) : (
            <div className="h-full p-6 overflow-auto">
              <div className="max-w-6xl mx-auto space-y-6">
                <DocumentUpload />
                <DocumentLibrary />
              </div>
            </div>
          )}
        </main>
      </div>
    </QueryClientProvider>
  );
}

export default App;