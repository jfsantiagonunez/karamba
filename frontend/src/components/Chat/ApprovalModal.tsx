import { AlertCircle, CheckCircle, XCircle } from 'lucide-react';

interface ApprovalModalProps {
  actionId: string;
  query: string;
  reason: string;
  agentName?: string;
  onApprove: () => void;
  onDeny: () => void;
  isProcessing: boolean;
}

export default function ApprovalModal({
  actionId,
  query,
  reason,
  agentName,
  onApprove,
  onDeny,
  isProcessing,
}: ApprovalModalProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full">
        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-200 bg-yellow-50">
          <AlertCircle className="text-yellow-600" size={24} />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Approval Required</h3>
            {agentName && (
              <p className="text-sm text-gray-600">{agentName}</p>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">
              Query:
            </label>
            <div className="bg-gray-50 rounded p-3 text-sm text-gray-900">
              "{query}"
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">
              Reason:
            </label>
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm text-gray-900">
              {reason}
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-gray-700">
            <p className="font-medium mb-1">⚠️ Important:</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>This query requires human approval before execution</li>
              <li>Review the query and reason carefully</li>
              <li>Click "Approve" to allow execution or "Deny" to cancel</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onDeny}
            disabled={isProcessing}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <XCircle size={18} />
            <span>Deny</span>
          </button>
          <button
            onClick={onApprove}
            disabled={isProcessing}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <CheckCircle size={18} />
            <span>{isProcessing ? 'Approving...' : 'Approve & Execute'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
