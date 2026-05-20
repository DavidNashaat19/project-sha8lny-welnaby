import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Target, Search as SearchIcon, ExternalLink, Plus, X, Upload } from 'lucide-react';

const fetchMatch = async (payload) => {
  const res = await fetch(`http://localhost:8000/api/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return await res.json();
};

const Match = () => {
  const [skills, setSkills] = useState(['react', 'javascript']);
  const [currentSkill, setCurrentSkill] = useState('');
  const [budget, setBudget] = useState(0);
  const [platform, setPlatform] = useState('all');
  
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleAddSkill = (e) => {
    e.preventDefault();
    if (currentSkill.trim() && !skills.includes(currentSkill.toLowerCase())) {
      setSkills([...skills, currentSkill.toLowerCase()]);
      setCurrentSkill('');
    }
  };

  const removeSkill = (s) => {
    setSkills(skills.filter(skill => skill !== s));
  };

  const handleMatch = async () => {
    if (skills.length === 0) return;
    setLoading(true);
    try {
      const data = await fetchMatch({
        skills,
        budget_expectation: budget > 0 ? budget : null,
        platform
      });
      setResults(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/api/parse-resume', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.skills && data.skills.length > 0) {
        // Merge unique skills
        const newSkills = [...new Set([...skills, ...data.skills.map(s => s.toLowerCase())])];
        setSkills(newSkills);
      }
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="grid md:grid-cols-12 gap-8">
        
        {/* Profile Builder */}
        <div className="md:col-span-4">
          <div className="glass-card p-6 sticky top-24">
            <div className="flex items-center gap-3 mb-6">
              <Target className="text-primary" />
              <h2 className="text-2xl font-display font-semibold">Profile Builder</h2>
            </div>
            
            <div 
              onClick={() => fileInputRef.current?.click()}
              className={`mb-8 p-4 border-2 border-dashed rounded-xl transition-colors group cursor-pointer ${uploading ? 'bg-primary/5 border-primary/10' : 'border-primary/20 bg-primary/5 hover:bg-primary/10'}`}
            >
              <div className="flex flex-col items-center gap-2">
                <div className={`w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary transition-transform ${uploading ? 'animate-pulse' : 'group-hover:scale-110'}`}>
                   {uploading ? <Upload size={20} className="animate-bounce" /> : <ExternalLink size={20} />}
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold">{uploading ? 'Analyzing PDF...' : 'Upload Resume (PDF)'}</p>
                  <p className="text-[11px] text-textMuted">AI will extract your skills automatically</p>
                </div>
                <input 
                  type="file" 
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden" 
                  accept=".pdf" 
                />
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-sm text-textMuted mb-2">Your Skills</label>
              <div className="flex flex-wrap gap-2 mb-3">
                {skills.map(s => (
                  <span key={s} className="bg-surface border border-border px-3 py-1 rounded-full text-sm flex items-center gap-2">
                    {s}
                    <button onClick={() => removeSkill(s)} className="text-textMuted hover:text-red-400">
                      <X size={14} />
                    </button>
                  </span>
                ))}
              </div>
              <form onSubmit={handleAddSkill} className="relative">
                <input 
                  type="text" 
                  className="input-field w-full pr-10" 
                  placeholder="Add a skill..."
                  value={currentSkill}
                  onChange={e => setCurrentSkill(e.target.value)}
                />
                <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 text-primary hover:text-secondary">
                  <Plus size={20} />
                </button>
              </form>
            </div>

            <div className="mb-6">
              <label className="block text-sm text-textMuted mb-2">Minimum Budget ($)</label>
              <input 
                type="number" 
                className="input-field w-full" 
                value={budget}
                onChange={e => setBudget(Number(e.target.value))}
              />
            </div>

            <div className="mb-8">
              <label className="block text-sm text-textMuted mb-2">Preferred Platform</label>
              <select 
                className="input-field w-full"
                value={platform}
                onChange={e => setPlatform(e.target.value)}
              >
                <option value="all">Any</option>
                <option value="Freelancer.com">Freelancer.com</option>
                <option value="Fiverr.com">Fiverr.com</option>
              </select>
            </div>

            <button 
              onClick={handleMatch} 
              className="primary-button w-full flex items-center justify-center gap-2"
              disabled={loading || skills.length === 0}
            >
              {loading ? 'Analyzing...' : 'Find My Matches'} <SearchIcon size={18} />
            </button>
          </div>
        </div>

        {/* Results Panel */}
        <div className="md:col-span-8">
          {results ? (
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-8"
            >
              {/* Score Header */}
              <div className="glass-card p-8 flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-display font-semibold mb-2">Market Fit Score</h3>
                  <p className="text-textMuted">Based on cosine similarity with current open jobs.</p>
                </div>
                <div className="relative w-32 h-32 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="64" cy="64" r="56" fill="transparent" stroke="#1a2340" strokeWidth="8" />
                    <circle 
                      cx="64" cy="64" r="56" fill="transparent" 
                      stroke="#00D4FF" strokeWidth="8" 
                      strokeDasharray="351.85" 
                      strokeDashoffset={351.85 - (351.85 * results.match_score)}
                      className="transition-all duration-1000 ease-out"
                    />
                  </svg>
                  <div className="absolute text-3xl font-display font-bold text-primary">
                    {(results.match_score * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* Gap Analysis */}
              <div className="grid md:grid-cols-2 gap-6">
                <div className="glass-card p-6">
                  <h4 className="font-semibold mb-4 text-green-400">Skills In Demand (You Have)</h4>
                  <div className="flex flex-wrap gap-2">
                    {results.matched_skills.map(s => (
                      <span key={s} className="bg-green-500/10 text-green-400 px-3 py-1 rounded text-sm">{s}</span>
                    ))}
                  </div>
                </div>
                
                <div className="glass-card p-6 border-orange-500/30">
                  <h4 className="font-semibold mb-4 text-orange-400">Missing Skills (Gap Analysis)</h4>
                  <div className="flex flex-wrap gap-2">
                    {results.gap_skills.map(s => (
                      <span key={s} className="bg-orange-500/10 text-orange-400 px-3 py-1 rounded text-sm">{s}</span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Suggested Learning */}
              {results.suggested_skills.length > 0 && (
                <div className="glass-card p-6 border-secondary/30">
                  <h4 className="font-semibold mb-4 text-secondary">Suggested to Learn Next</h4>
                  <p className="text-sm text-textMuted mb-4">These skills frequently co-occur with your existing skillset.</p>
                  <div className="flex flex-wrap gap-2">
                    {results.suggested_skills.map(s => (
                      <span key={s} className="bg-secondary/10 text-secondary px-3 py-1 rounded text-sm">{s}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Top Job Matches */}
              <div>
                <h3 className="text-2xl font-display font-semibold mb-6">Your Top Matching Jobs</h3>
                <div className="space-y-4">
                  {results.top_jobs.map(job => (
                    <div key={job.doc_id} className="glass-card p-6">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-sm text-textMuted">{job.platform}</span>
                        <span className="text-primary font-mono">Match: {(job.relevance_score * 100).toFixed(0)}%</span>
                      </div>
                      <h4 className="text-lg font-display font-semibold mb-2">{job.title}</h4>
                      <p className="text-textMuted text-sm mb-4 line-clamp-2">{job.description_snippet}</p>
                      <div className="flex justify-between items-center">
                        <div className="flex gap-2">
                          {job.skills.slice(0, 3).map(s => (
                            <span key={s} className="bg-surface px-2 py-1 rounded text-xs">{s}</span>
                          ))}
                        </div>
                        <a href={job.url} target="_blank" rel="noreferrer" className="text-primary text-sm flex items-center gap-1 hover:text-secondary">
                          Apply <ExternalLink size={14} />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-textMuted opacity-50 py-20">
              <Target size={64} className="mb-4" />
              <p className="text-lg">Enter your skills and click match to see your market fit.</p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};

export default Match;
