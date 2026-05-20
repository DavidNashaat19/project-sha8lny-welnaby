import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../store/useAppStore';
import { Search as SearchIcon, Filter, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';

// API Hook Simulation (Real API call to FastAPI)
const fetchJobs = async (params) => {
  const queryParams = new URLSearchParams();
  if (params.q) queryParams.append('q', params.q);
  if (params.mode) queryParams.append('mode', params.mode);
  if (params.platform) params.platform.forEach(p => queryParams.append('platform', p));
  if (params.skills) params.skills.forEach(s => queryParams.append('skills', s));
  if (params.budgetMin) queryParams.append('budget_min', params.budgetMin);
  if (params.budgetMax) queryParams.append('budget_max', params.budgetMax);
  if (params.budgetType && params.budgetType !== 'all') queryParams.append('budget_type', params.budgetType);
  if (params.page) queryParams.append('page', params.page);
  
  const res = await fetch(`http://localhost:8000/api/search?${queryParams.toString()}`);
  return await res.json();
};

const JobCard = ({ job }) => {
  const [showIR, setShowIR] = useState(false);
  const platformColor = job.platform.includes('Freelancer') ? 'bg-blue-500' : 'bg-teal-500';

  // Determine which skills to show
  const showInferred = !job.has_explicit_skills || (job.inferred_skills && job.inferred_skills.length > 0);
  const explicitSkills = job.skills || [];
  const inferredSkills = job.inferred_skills || [];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2, borderColor: '#00D4FF', boxShadow: '0 4px 20px rgba(0, 212, 255, 0.1)' }}
      className="glass-card p-6 mb-4 relative overflow-hidden group cursor-pointer"
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <span className={`w-3 h-3 rounded-full ${platformColor}`} />
          <span className="text-sm text-textMuted font-medium">{job.platform}</span>
        </div>
        {job.budget_extracted && (
          <div className="bg-surface border border-border px-3 py-1 rounded-full text-xs text-textPrimary font-mono">
            {job.budget_currency} {job.budget_extracted} {job.budget_type === 'hourly' ? '/hr' : ''}
          </div>
        )}
      </div>
      
      <h3 className="text-xl font-display font-semibold mb-2 group-hover:text-primary transition-colors">
        {job.title}
      </h3>
      
      <p className="text-textMuted text-sm mb-4 line-clamp-2">
        {job.description_snippet}
      </p>
      
      <div className="flex flex-wrap gap-2 mb-4 items-center">
        {explicitSkills.slice(0, 5).map(skill => (
          <span key={skill} className="bg-primary/10 text-primary border border-primary/30 px-2 py-1 rounded text-xs">
            {skill}
          </span>
        ))}
        
        {showInferred && inferredSkills.length > 0 && (
          <>
            <span className="text-[10px] font-bold text-[#7B61FF] uppercase tracking-wider ml-1 mr-1">✦ AI</span>
            {inferredSkills.slice(0, 5).map(skill => (
              <span 
                key={skill} 
                title="Detected automatically from job description"
                className="bg-transparent text-[#7B61FF] border border-dashed border-[#7B61FF]/50 px-2 py-1 rounded text-xs"
              >
                {skill}
              </span>
            ))}
          </>
        )}

        {(explicitSkills.length + inferredSkills.length) > 10 && (
          <span className="bg-surface text-textMuted px-2 py-1 rounded text-xs">
            +{(explicitSkills.length + inferredSkills.length) - 10}
          </span>
        )}
      </div>
      
      <div className="flex items-center justify-between border-t border-border pt-4 mt-2">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs text-textMuted">
              {job.score_label || 'Relevance'}:
            </span>
            <div className="w-24 h-2 bg-surface rounded-full overflow-hidden">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(100, (job.relevance_score || 0) * 100)}%` }}
                className="h-full bg-gradient-to-r from-primary to-secondary"
              />
            </div>
            <span className="text-xs font-mono">{(job.relevance_score * 100).toFixed(0)}%</span>
          </div>
          
          {job.matched_tokens && (
             <button 
               onClick={(e) => { e.stopPropagation(); setShowIR(!showIR); }}
               className="text-xs text-textMuted hover:text-primary flex items-center gap-1"
             >
               IR Details {showIR ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
             </button>
          )}
        </div>
        
        <a 
          href={job.url} 
          target="_blank" 
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="flex items-center gap-1 text-sm text-primary hover:text-secondary transition-colors"
        >
          View <ExternalLink size={14} />
        </a>
      </div>

      <AnimatePresence>
        {showIR && job.tfidf_breakdown && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-4 p-4 bg-background/50 border border-border rounded-lg text-xs font-mono overflow-hidden"
          >
            <div className="text-textMuted mb-2">Matched Tokens:</div>
            <div className="flex flex-wrap gap-2 mb-3">
              {job.matched_tokens.map(t => (
                <span key={t} className="text-highlight bg-highlight/10 px-1 py-0.5 rounded">{t}</span>
              ))}
            </div>
            <div className="text-textMuted mb-2">TF-IDF Breakdown:</div>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(job.tfidf_breakdown).map(([term, score]) => (
                <div key={term} className="flex justify-between border-b border-border/50 pb-1">
                  <span>{term}</span>
                  <span className="text-primary">{score.toFixed(4)}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const Search = () => {
  const { t } = useTranslation();
  const { searchQuery, setSearchQuery, searchMode, setSearchMode } = useAppStore();
  
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ total: 0, time: 0 });
  const [insight, setInsight] = useState("");
  
  // Filters
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [platforms, setPlatforms] = useState(['all']);
  
  useEffect(() => {
    handleSearch();
  }, [searchMode]); // Auto search when mode changes
  
  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    setInsight(""); // Clear previous insight
    try {
      const data = await fetchJobs({
        q: searchQuery,
        mode: searchMode,
        platform: platforms.includes('all') ? null : platforms
      });
      setResults(data.results || []);
      setStats({ total: data.total, time: data.query_time_ms });
      if (data.insight) setInsight(data.insight);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Search Header */}
      <div className="sticky top-20 z-40 bg-background/90 backdrop-blur pb-6 border-b border-border">
        <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4 items-end md:items-center">
          <div className="flex-1 w-full relative">
            <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 text-textMuted" size={20} />
            <input 
              type="text" 
              placeholder="e.g. machine learning, تصميم جرافيك, React"
              className="w-full bg-surface border border-border rounded-xl py-4 pl-12 pr-4 text-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all font-sans"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          
          <div className="flex gap-4 w-full md:w-auto">
            <select 
              value={searchMode} 
              onChange={(e) => setSearchMode(e.target.value)}
              className="bg-surface border border-border rounded-xl px-4 py-4 text-textPrimary focus:outline-none focus:border-primary"
            >
              <option value="tfidf">TF-IDF (Relevance)</option>
              <option value="hybrid">Hybrid (Lexical + AI) ✨</option>
              <option value="semantic">Semantic (AI Meaning) 🧠</option>

              <option value="boolean">Boolean (AND/OR/NOT)</option>
              <option value="vsm">Vector Space Model</option>
              <option value="phrase">Phrase Match ("...")</option>
            </select>
            
            <button 
              type="submit"
              className="primary-button py-4 px-8 rounded-xl"
            >
              {t('nav.search')}
            </button>
            
            <button 
              type="button"
              onClick={() => setFilterDrawerOpen(!filterDrawerOpen)}
              className="secondary-button py-4 px-4 rounded-xl flex items-center justify-center"
            >
              <Filter size={20} />
            </button>
          </div>
        </form>
      </div>

      <div className="flex mt-8 gap-8">
        {/* Main Content */}
        <div className="flex-1">
          <div className="flex justify-between items-center mb-6">
            <div className="text-textMuted text-sm">
              {loading ? 'Searching...' : `Found ${stats.total} results in ${stats.time}ms`}
              {searchMode === 'semantic' && <span className="ml-2 text-cyan-400 font-bold">🧠 AI MODE</span>}
            </div>
          </div>

          {/* Market Insight Strip */}
          <AnimatePresence>
            {insight && (
              <motion.div 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6 overflow-hidden"
                style={{
                  background: 'rgba(123, 97, 255, 0.06)',
                  border: '1px solid rgba(123, 97, 255, 0.25)',
                  borderLeft: '4px solid #7B61FF',
                  borderRadius: '12px',
                  padding: '16px 20px'
                }}
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="text-[11px] font-bold text-[#7B61FF] uppercase tracking-[0.1em]">✦ Market Insight</span>
                  <span className="bg-[#7B61FF]/20 text-[#7B61FF] text-[10px] px-2 py-0.5 rounded font-medium">AI-powered</span>
                </div>
                <p className="text-[#D0D8FF] text-sm leading-relaxed">
                  {insight}
                </p>
              </motion.div>
            )}
            
            {loading && !insight && searchQuery && (
               <motion.div 
                 className="mb-6 h-24 w-full animate-pulse rounded-xl bg-[#7B61FF]/5 border border-[#7B61FF]/10"
               />
            )}
          </AnimatePresence>
          
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="glass-card p-6 h-40 animate-pulse bg-surface/50" />
              ))}
            </div>
          ) : results.length > 0 ? (
            <div className="space-y-4">
              {results.map(job => (
                <JobCard key={job.doc_id} job={job} />
              ))}
            </div>
          ) : (
            <div className="text-center py-20 text-textMuted">
              <SearchIcon size={48} className="mx-auto mb-4 opacity-20" />
              <p>No matches found. Try broader terms or a different search mode.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Search;
