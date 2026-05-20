import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, ScatterChart, Scatter, ZAxis
} from 'recharts';

const fetchAnalytics = async (platform = 'all') => {
  const res = await fetch(`http://localhost:8000/api/analytics?platform=${platform}`);
  return await res.json();
};

const COLORS = ['#00D4FF', '#7B61FF', '#FFD166', '#FF6B6B', '#4ECDC4'];

const Analytics = () => {
  const [data, setData] = useState(null);
  const [platform, setPlatform] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [platform]);

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await fetchAnalytics(platform);
      setData(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return <div className="p-20 text-center text-primary animate-pulse">Loading Intelligence...</div>;
  }

  // Format data for charts
  const platformData = Object.entries(data.platform_dist).map(([name, value]) => ({ name, value }));
  const currencyData = Object.entries(data.currency_dist).map(([name, value]) => ({ name, value }));

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-display font-bold gradient-text">Market Intelligence</h1>
        
        <select 
          value={platform} 
          onChange={(e) => setPlatform(e.target.value)}
          className="bg-surface border border-border rounded-lg px-4 py-2 text-textPrimary focus:outline-none focus:border-primary"
        >
          <option value="all">All Platforms</option>
          <option value="Freelancer.com">Freelancer.com</option>
          <option value="Fiverr.com">Fiverr.com</option>
        </select>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="glass-card p-6">
          <div className="text-sm text-textMuted mb-1">Average Budget</div>
          <div className="text-3xl font-display font-bold text-primary">${data.budget_stats.mean}</div>
        </div>
        <div className="glass-card p-6">
          <div className="text-sm text-textMuted mb-1">Median Budget</div>
          <div className="text-3xl font-display font-bold text-secondary">${data.budget_stats.median}</div>
        </div>
        <div className="glass-card p-6">
          <div className="text-sm text-textMuted mb-1">Max Budget Recorded</div>
          <div className="text-3xl font-display font-bold text-highlight">${data.budget_stats.max}</div>
        </div>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Top Skills */}
        <div className="glass-card p-6 md:col-span-2 h-96">
          <h3 className="text-lg font-display font-semibold mb-4">Top 20 In-Demand Skills</h3>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.top_skills} layout="vertical" margin={{ top: 0, right: 0, left: 40, bottom: 0 }}>
              <XAxis type="number" stroke="#5A6490" />
              <YAxis dataKey="skill" type="category" stroke="#5A6490" fontSize={12} width={100} />
              <Tooltip cursor={{fill: '#1a2340'}} contentStyle={{backgroundColor: '#0d1428', border: '1px solid #1a2340'}} />
              <Bar dataKey="count" fill="#00D4FF" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Platform Dist */}
        <div className="glass-card p-6 h-96">
          <h3 className="text-lg font-display font-semibold mb-4">Platform Distribution</h3>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={platformData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                {platformData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{backgroundColor: '#0d1428', border: '1px solid #1a2340'}} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 text-sm mt-4">
            {platformData.map((entry, index) => (
              <div key={entry.name} className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{backgroundColor: COLORS[index % COLORS.length]}}></span>
                {entry.name}
              </div>
            ))}
          </div>
        </div>

        {/* Budget Histogram */}
        <div className="glass-card p-6 md:col-span-1 h-80">
          <h3 className="text-lg font-display font-semibold mb-4">Budget Distribution</h3>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.budget_histogram}>
              <XAxis dataKey="range" stroke="#5A6490" fontSize={10} />
              <YAxis stroke="#5A6490" />
              <Tooltip cursor={{fill: '#1a2340'}} contentStyle={{backgroundColor: '#0d1428', border: '1px solid #1a2340'}} />
              <Bar dataKey="count" fill="#7B61FF" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Skills by Avg Budget (Bubble) */}
        <div className="glass-card p-6 md:col-span-2 h-80">
          <h3 className="text-lg font-display font-semibold mb-4">Skills Value vs Frequency</h3>
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <XAxis dataKey="frequency" type="number" name="Frequency" stroke="#5A6490" />
              <YAxis dataKey="avg_budget" type="number" name="Avg Budget ($)" stroke="#5A6490" />
              <ZAxis dataKey="frequency" range={[50, 400]} name="Volume" />
              <Tooltip cursor={{strokeDasharray: '3 3'}} contentStyle={{backgroundColor: '#0d1428', border: '1px solid #1a2340'}} />
              <Scatter name="Skills" data={data.skills_by_budget} fill="#FFD166" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

      </div>
    </div>
  );
};

export default Analytics;
