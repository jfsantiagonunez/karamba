import { CheckCircle, Circle, Loader2 } from 'lucide-react';

interface Phase {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

interface Props {
  phases: Phase[];
}

export default function PhaseIndicator({ phases }: Props) {
  return (
    <div className="flex items-center justify-center space-x-4">
      {phases.map((phase, idx) => (
        <div key={phase.name} className="flex items-center">
          <div className="flex items-center space-x-2">
            {phase.status === 'completed' && (
              <CheckCircle className="text-green-500" size={20} />
            )}
            {phase.status === 'running' && (
              <Loader2 className="text-blue-500 animate-spin" size={20} />
            )}
            {phase.status === 'pending' && (
              <Circle className="text-gray-300" size={20} />
            )}
            {phase.status === 'failed' && (
              <Circle className="text-red-500" size={20} />
            )}
            <span
              className={`capitalize text-sm ${
                phase.status === 'running' ? 'font-semibold text-blue-600' : 'text-gray-600'
              }`}
            >
              {phase.name}
            </span>
          </div>
          {idx < phases.length - 1 && (
            <div className="w-8 h-0.5 bg-gray-300 mx-2" />
          )}
        </div>
      ))}
    </div>
  );
}