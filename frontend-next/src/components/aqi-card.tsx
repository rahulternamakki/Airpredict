import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface AQICardProps {
  region: string;
  aqi: number;
  category: string;
  className?: string;
}

const getAQIColor = (category: string) => {
  switch (category.toLowerCase()) {
    case 'good': return 'bg-green-500 text-white';
    case 'satisfactory': return 'bg-green-400 text-white';
    case 'moderate': return 'bg-yellow-400 text-gray-900';
    case 'poor': return 'bg-orange-500 text-white';
    case 'very poor': return 'bg-red-600 text-white';
    case 'severe': return 'bg-red-900 text-white';
    default: return 'bg-gray-400 text-white';
  }
};

const getAQIBG = (category: string) => {
  switch (category.toLowerCase()) {
    case 'good': return 'bg-green-50 border-green-100';
    case 'satisfactory': return 'bg-green-50 border-green-100';
    case 'moderate': return 'bg-yellow-50 border-yellow-100';
    case 'poor': return 'bg-orange-50 border-orange-100';
    case 'very poor': return 'bg-red-50 border-red-100';
    case 'severe': return 'bg-red-100 border-red-200';
    default: return 'bg-gray-50 border-gray-100';
  }
};

const AQICard: React.FC<AQICardProps> = ({ region, aqi, category, className }) => {
  return (
    <div className={cn(
      "p-6 rounded-2xl border transition-all hover:shadow-lg", 
      getAQIBG(category),
      className
    )}>
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-bold text-gray-800">{region}</h3>
        <span className={cn(
          "px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider",
          getAQIColor(category)
        )}>
          {category}
        </span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-extrabold text-gray-900">{aqi}</span>
        <span className="text-gray-500 font-medium">AQI</span>
      </div>
    </div>
  );
};

export default AQICard;
