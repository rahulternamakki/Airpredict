"use client";

import { useEffect, useState } from 'react';
import { getPipelineStatus } from '@/lib/api';
import { AlertCircle, Clock } from 'lucide-react';

const Header = () => {
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    getPipelineStatus()
      .then((res) => setStatus(res.data))
      .catch((err) => console.error('Failed to fetch pipeline status', err));
  }, []);

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8 sticky top-0 z-10">
      <div className="flex items-center gap-4">
        {status ? (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Clock size={16} className="text-blue-500" />
            <span>Last Pipeline Run: <span className="font-medium text-gray-900">{status.pipeline_ran_at}</span></span>
            <span className="mx-2 text-gray-300">|</span>
            <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-100">
              Model: {status.gemini_model_used}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-gray-400 animate-pulse">
            <div className="h-4 w-4 bg-gray-200 rounded-full" />
            <div className="h-4 w-48 bg-gray-200 rounded" />
          </div>
        )}
      </div>

      <div className="flex items-center gap-4 text-xs font-semibold uppercase tracking-wider text-green-600 bg-green-50 px-3 py-1 rounded-full border border-green-100">
        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
        System Live
      </div>
    </header>
  );
};

export default Header;
