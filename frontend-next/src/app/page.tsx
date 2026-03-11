"use client";

import { useEffect, useState } from 'react';
import { getPredictionsSummary, getFullForecast, RegionSummary, FullForecastResponse } from '@/lib/api';
import AQICard from '@/components/aqi-card';
import { TrendChart, ComparisonChart } from '@/components/charts';
import { RefreshCcw, LayoutGrid, BarChart3, List } from 'lucide-react';

export default function Dashboard() {
  const [summary, setSummary] = useState<RegionSummary[]>([]);
  const [forecast, setForecast] = useState<FullForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sumRes, foreRes] = await Promise.all([
        getPredictionsSummary(),
        getFullForecast()
      ]);
      setSummary(sumRes.data.regions || []);
      setForecast(foreRes.data || null);
    } catch (error) {
      console.error('Error fetching dashboard data', error);
      // Fallback dummy data for development visualization
      setSummary([
        { region: 'North Delhi', day_1_aqi: 245, day_1_category: 'Poor' },
        { region: 'South Delhi', day_1_aqi: 180, day_1_category: 'Moderate' },
        { region: 'East Delhi', day_1_aqi: 310, day_1_category: 'Very Poor' },
        { region: 'West Delhi', day_1_aqi: 210, day_1_category: 'Poor' },
        { region: 'Central Delhi', day_1_aqi: 195, day_1_category: 'Moderate' },
        { region: 'Dwarka', day_1_aqi: 150, day_1_category: 'Moderate' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Calculate average trend data from actual forecast
  const getTrendData = () => {
    if (!forecast || !forecast.regions) {
      return [
        { date: 'Today', aqi: 210 },
        { date: 'Tomorrow', aqi: 245 },
        { date: 'Day 3', aqi: 230 },
      ];
    }

    const regions = Object.values(forecast.regions);
    if (regions.length === 0) return [];

    const avgDay1 = regions.reduce((acc, r) => acc + r.day_1, 0) / regions.length;
    const avgDay2 = regions.reduce((acc, r) => acc + r.day_2, 0) / regions.length;
    const avgDay3 = regions.reduce((acc, r) => acc + r.day_3, 0) / regions.length;

    return [
      { date: 'Day 1', aqi: Math.round(avgDay1) },
      { date: 'Day 2', aqi: Math.round(avgDay2) },
      { date: 'Day 3', aqi: Math.round(avgDay3) },
    ];
  };

  const trendData = getTrendData();

  const comparisonData = summary.map(r => ({
    region: r.region,
    aqi: r.day_1_aqi
  }));

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col gap-2">
        <h2 className="text-3xl font-extrabold tracking-tight text-gray-900">Dashboard Overview</h2>
        <p className="text-gray-500 max-w-2xl">
          Real-time air quality metrics and 3-day forecasts across Delhi's major regions. 
          Monitor changes and plan your outdoor activities accordingly.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          Array(6).fill(0).map((_, i) => (
            <div key={i} className="h-32 bg-gray-100 rounded-2xl animate-pulse" />
          ))
        ) : (
          summary.map((region) => (
            <AQICard 
              key={region.region}
              region={region.region}
              aqi={region.day_1_aqi}
              category={region.day_1_category}
            />
          ))
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
        <div className="bg-white p-8 rounded-3xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                <BarChart3 size={20} />
              </div>
              <h3 className="text-xl font-bold text-gray-800">Regional Comparison</h3>
            </div>
            <button onClick={fetchData} className="text-gray-400 hover:text-blue-500 transition-colors">
              <RefreshCcw size={18} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
          <ComparisonChart data={comparisonData} />
        </div>

        <div className="bg-white p-8 rounded-3xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-50 text-green-600 rounded-lg">
                <LayoutGrid size={20} />
              </div>
              <h3 className="text-xl font-bold text-gray-800">3-Day Trend (Average)</h3>
            </div>
          </div>
          <TrendChart data={trendData} />
        </div>
      </div>

      <div className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="p-8 border-b border-gray-50 flex items-center gap-3">
          <div className="p-2 bg-purple-50 text-purple-600 rounded-lg">
            <List size={20} />
          </div>
          <h3 className="text-xl font-bold text-gray-800">Forecast Matrix</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50/50">
                <th className="px-8 py-4 text-xs font-bold uppercase tracking-wider text-gray-500">Region</th>
                <th className="px-8 py-4 text-xs font-bold uppercase tracking-wider text-gray-500 font-semibold text-blue-600">Day 1</th>
                <th className="px-8 py-4 text-xs font-bold uppercase tracking-wider text-gray-500 font-semibold text-blue-600">Day 2</th>
                <th className="px-8 py-4 text-xs font-bold uppercase tracking-wider text-gray-500 font-semibold text-blue-600">Day 3</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading ? (
                Array(5).fill(0).map((_, i) => (
                  <tr key={i}><td colSpan={4} className="px-8 py-4 animate-pulse"><div className="h-4 bg-gray-100 rounded w-full"></div></td></tr>
                ))
              ) : (
                summary.map((r, i) => {
                  const regForecast = forecast?.regions?.[r.region];
                  return (
                    <tr key={i} className="hover:bg-gray-50/30 transition-colors">
                      <td className="px-8 py-5 font-bold text-gray-900">{r.region}</td>
                      <td className="px-8 py-5">
                        <div className="flex flex-col">
                          <span className="font-bold text-lg">{regForecast?.day_1 || r.day_1_aqi}</span>
                          <span className="text-[10px] uppercase font-bold text-gray-400">{regForecast?.category?.[0] || r.day_1_category}</span>
                        </div>
                      </td>
                      <td className="px-8 py-5">
                        {regForecast ? (
                          <div className="flex flex-col">
                            <span className="font-bold text-lg">{regForecast.day_2}</span>
                            <span className="text-[10px] uppercase font-bold text-gray-400">{regForecast.category[1]}</span>
                          </div>
                        ) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-8 py-5">
                        {regForecast ? (
                          <div className="flex flex-col">
                            <span className="font-bold text-lg">{regForecast.day_3}</span>
                            <span className="text-[10px] uppercase font-bold text-gray-400">{regForecast.category[2]}</span>
                          </div>
                        ) : <span className="text-gray-300">—</span>}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
