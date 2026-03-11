"use client";

import { useEffect, useState } from 'react';
import { getRegionalShap, getPredictionsSummary, RegionSummary, RegionShap } from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Info, Activity, Filter, ArrowRight } from 'lucide-react';

export default function InsightsPage() {
  const [regions, setRegions] = useState<RegionSummary[]>([]);
  const [selectedRegion, setSelectedRegion] = useState('');
  const [shapData, setShapData] = useState<RegionShap | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getPredictionsSummary().then(res => {
      const regionList = res.data.regions || [];
      setRegions(regionList);
      if (regionList.length > 0) setSelectedRegion(regionList[0].region);
    });
  }, []);

  useEffect(() => {
    if (selectedRegion) {
      setLoading(true);
      getRegionalShap(selectedRegion)
        .then(res => {
          // The API returns an array of daily SHAP data, we take Day 1
          const data = Array.isArray(res.data) 
            ? res.data.find(d => d.prediction_day === 1) || res.data[0]
            : res.data;
          setShapData(data);
        })
        .catch(() => {
          // Fallback dummy SHAP data
          setShapData({
            region: selectedRegion,
            prediction_day: 1,
            base_value: 150,
            predicted_value: 245,
            top_features: [
              { feature: 'NO2', shap_value: 45, actual_value: 0 },
              { feature: 'PM2.5_Observed', shap_value: 40, actual_value: 0 },
              { feature: 'Temperature', shap_value: -15, actual_value: 0 },
              { feature: 'Humidity', shap_value: 10, actual_value: 0 },
              { feature: 'WindSpeed', shap_value: -5, actual_value: 0 },
            ]
          });
        })
        .finally(() => setLoading(false));
    }
  }, [selectedRegion]);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-gray-900">Model Insights</h2>
          <p className="text-gray-500 mt-1">Understanding the 'Why' behind the predictions using SHAP values.</p>
        </div>
        
        <div className="flex items-center gap-3 bg-white p-2 rounded-2xl border border-gray-100 shadow-sm">
          <Filter size={18} className="text-gray-400 ml-2" />
          <select 
            value={selectedRegion}
            onChange={(e) => setSelectedRegion(e.target.value)}
            className="bg-transparent border-none focus:ring-0 text-gray-900 font-bold pr-8"
          >
            {regions.map(r => (
              <option key={r.region} value={r.region}>{r.region}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-white p-8 rounded-3xl border border-gray-100 shadow-sm">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                <Activity size={20} />
              </div>
              <h3 className="text-xl font-bold text-gray-800">Feature Impact (SHAP)</h3>
            </div>
            
            <div className="h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={shapData?.top_features || []}
                  margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#f1f5f9" />
                  <XAxis type="number" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8' }} />
                  <YAxis 
                    dataKey="feature" 
                    type="category" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fill: '#475569', fontWeight: 600, fontSize: 13 }} 
                  />
                  <Tooltip 
                    cursor={{ fill: '#f8fafc' }}
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                  />
                  <Bar dataKey="shap_value" radius={[0, 4, 4, 0]}>
                    {shapData?.top_features?.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.shap_value > 0 ? '#ef4444' : '#22c55e'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-gradient-to-br from-gray-900 to-gray-800 p-8 rounded-3xl text-white shadow-xl">
            <h4 className="text-gray-400 font-bold uppercase tracking-wider text-xs mb-4">Prediction Logic</h4>
            <div className="space-y-6">
              <div className="flex justify-between items-end border-b border-gray-700 pb-4">
                <span className="text-gray-400 font-medium text-sm text-gray-200">Base Value</span>
                <span className="text-2xl font-bold">{shapData?.base_value ?? 0}</span>
              </div>
              <div className="flex justify-between items-end border-b border-gray-700 pb-4">
                <span className="text-gray-400 font-medium text-sm text-gray-200">Total Shifts</span>
                <span className={`text-2xl font-bold ${((shapData?.predicted_value ?? 0) - (shapData?.base_value ?? 0)) > 0 ? 'text-red-400' : 'text-green-400'}`}>
                  {shapData ? (shapData.predicted_value - shapData.base_value > 0 ? '+' : '') : ''}
                  {shapData ? shapData.predicted_value - shapData.base_value : 0}
                </span>
              </div>
              <div className="flex justify-between items-center bg-white/10 p-4 rounded-2xl">
                <span className="text-gray-200 font-bold">Predicted AQI</span>
                <span className="text-3xl font-black text-blue-400">{shapData?.predicted_value ?? 0}</span>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 p-6 rounded-3xl border border-blue-100">
            <div className="flex gap-4">
              <div className="bg-blue-600 p-2 h-fit rounded-lg text-white">
                <Info size={16} />
              </div>
              <div className="space-y-2">
                <h5 className="font-bold text-blue-900">How to read this?</h5>
                <p className="text-sm text-blue-800 leading-relaxed">
                  Positive values (Red) indicate features that are increasing the AQI, while negative values (Green) show features helping to improve air quality.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
