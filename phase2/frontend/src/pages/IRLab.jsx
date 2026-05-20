import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Database, Calculator, GitMerge, Search as SearchIcon } from 'lucide-react';

const IRLab = () => {
  const [activeTab, setActiveTab] = useState('index');
  
  // Tab 1: Index Browser
  const [indexTerm, setIndexTerm] = useState('');
  const [indexData, setIndexData] = useState(null);
  
  // Tab 2: TF-IDF
  const [tfidfTerm, setTfidfTerm] = useState('');
  const [tfidfDocId, setTfidfDocId] = useState('');
  const [tfidfData, setTfidfData] = useState(null);
  
  // Tab 3: VSM
  const [vsmQuery, setVsmQuery] = useState('');
  const [vsmData, setVsmData] = useState(null);

  const fetchIndex = async (e) => {
    e.preventDefault();
    if (!indexTerm) return;
    const res = await fetch(`http://localhost:8000/api/ir/index?term=${encodeURIComponent(indexTerm)}`);
    setIndexData(await res.json());
  };

  const fetchTfidf = async (e) => {
    e.preventDefault();
    if (!tfidfTerm || !tfidfDocId) return;
    const res = await fetch(`http://localhost:8000/api/ir/tfidf?term=${encodeURIComponent(tfidfTerm)}&doc_id=${tfidfDocId}`);
    setTfidfData(await res.json());
  };

  const fetchVsm = async (e) => {
    e.preventDefault();
    if (!vsmQuery) return;
    const res = await fetch(`http://localhost:8000/api/ir/vsm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: vsmQuery })
    });
    setVsmData(await res.json());
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8 border-b border-border pb-4">
        <h1 className="text-3xl font-display font-bold flex items-center gap-3">
          <Terminal className="text-primary" size={32} />
          <span>IR Lab <span className="text-textMuted text-lg font-mono">/ Engine Explorer</span></span>
        </h1>
        <p className="text-textMuted mt-2">CS313x Presentation Interface. Inspect the in-memory data structures and algorithms.</p>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        
        {/* Sidebar Nav */}
        <div className="w-full md:w-64 space-y-2">
          <button 
            onClick={() => setActiveTab('index')}
            className={`w-full text-left px-4 py-3 rounded-lg flex items-center gap-3 transition-colors ${activeTab === 'index' ? 'bg-primary/10 text-primary border border-primary/30' : 'hover:bg-surface text-textMuted'}`}
          >
            <Database size={18} /> Inverted Index
          </button>
          <button 
            onClick={() => setActiveTab('tfidf')}
            className={`w-full text-left px-4 py-3 rounded-lg flex items-center gap-3 transition-colors ${activeTab === 'tfidf' ? 'bg-secondary/10 text-secondary border border-secondary/30' : 'hover:bg-surface text-textMuted'}`}
          >
            <Calculator size={18} /> TF-IDF Calculator
          </button>
          <button 
            onClick={() => setActiveTab('vsm')}
            className={`w-full text-left px-4 py-3 rounded-lg flex items-center gap-3 transition-colors ${activeTab === 'vsm' ? 'bg-highlight/10 text-highlight border border-highlight/30' : 'hover:bg-surface text-textMuted'}`}
          >
            <GitMerge size={18} /> Vector Space Model
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 glass-card p-6 min-h-[500px] font-mono bg-[#020408]">
          
          <AnimatePresence mode="wait">
            
            {/* INDEX TAB */}
            {activeTab === 'index' && (
              <motion.div key="index" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <h3 className="text-xl text-primary mb-6 flex items-center gap-2"><Database /> Inverted Index Browser</h3>
                <form onSubmit={fetchIndex} className="flex gap-4 mb-8">
                  <input 
                    type="text" 
                    placeholder="Enter a term (e.g., 'react')" 
                    className="bg-transparent border border-border rounded px-4 py-2 text-textPrimary focus:border-primary outline-none flex-1"
                    value={indexTerm}
                    onChange={(e) => setIndexTerm(e.target.value)}
                  />
                  <button type="submit" className="border border-primary text-primary px-4 rounded hover:bg-primary/20 transition-colors">Lookup</button>
                </form>

                {indexData && (
                  <div className="space-y-4 text-sm">
                    <div className="flex gap-8 text-textMuted border-b border-border pb-2">
                      <span>Term: <span className="text-primary">'{indexData.term}'</span></span>
                      <span>Document Frequency (DF): <span className="text-primary">{indexData.df}</span></span>
                      <span>Inverse Document Frequency (IDF): <span className="text-primary">{indexData.idf}</span></span>
                    </div>
                    
                    <div className="text-textMuted mt-4 mb-2">Postings List:</div>
                    <div className="max-h-96 overflow-y-auto pr-2 custom-scrollbar">
                      {indexData.postings.length === 0 ? (
                        <div className="text-red-400">Term not found in vocabulary.</div>
                      ) : (
                        indexData.postings.map(p => (
                          <div key={p.doc_id} className="flex items-start gap-4 py-2 border-b border-border/30">
                            <span className="text-secondary w-24">Doc {p.doc_id}</span>
                            <span className="text-textMuted w-20">TF: {p.tf}</span>
                            <span className="text-green-400 break-words flex-1">Positions: [{p.positions.join(', ')}]</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </motion.div>
            )}

            {/* TF-IDF TAB */}
            {activeTab === 'tfidf' && (
              <motion.div key="tfidf" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <h3 className="text-xl text-secondary mb-6 flex items-center gap-2"><Calculator /> TF-IDF Step-by-Step</h3>
                <form onSubmit={fetchTfidf} className="flex gap-4 mb-8">
                  <input 
                    type="text" 
                    placeholder="Term" 
                    className="bg-transparent border border-border rounded px-4 py-2 text-textPrimary focus:border-secondary outline-none w-1/3"
                    value={tfidfTerm}
                    onChange={(e) => setTfidfTerm(e.target.value)}
                  />
                  <input 
                    type="number" 
                    placeholder="Doc ID" 
                    className="bg-transparent border border-border rounded px-4 py-2 text-textPrimary focus:border-secondary outline-none w-1/3"
                    value={tfidfDocId}
                    onChange={(e) => setTfidfDocId(e.target.value)}
                  />
                  <button type="submit" className="border border-secondary text-secondary px-4 rounded hover:bg-secondary/20 transition-colors flex-1">Calculate</button>
                </form>

                {tfidfData && (
                  <div className="space-y-6 text-sm bg-[#0a0f1e] p-6 rounded-lg border border-border">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-textMuted mb-1">Term Frequency (Raw)</div>
                        <div className="text-2xl text-textPrimary">{tfidfData.tf_raw}</div>
                      </div>
                      <div>
                        <div className="text-textMuted mb-1">Term Frequency (Normalized)</div>
                        <div className="text-2xl text-textPrimary">{tfidfData.tf_normalized}</div>
                      </div>
                      <div>
                        <div className="text-textMuted mb-1">Document Frequency (DF)</div>
                        <div className="text-2xl text-textPrimary">{tfidfData.df} / {tfidfData.N}</div>
                      </div>
                      <div>
                        <div className="text-textMuted mb-1">Inverse Document Frequency (IDF)</div>
                        <div className="text-2xl text-textPrimary">{tfidfData.idf}</div>
                      </div>
                    </div>
                    
                    <div className="mt-6 pt-6 border-t border-border">
                      <div className="text-textMuted mb-2">Final Calculation:</div>
                      <div className="text-xl text-secondary font-bold font-sans">
                        {tfidfData.formula}
                      </div>
                    </div>
                  </div>
                )}
              </motion.div>
            )}

            {/* VSM TAB */}
            {activeTab === 'vsm' && (
              <motion.div key="vsm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <h3 className="text-xl text-highlight mb-6 flex items-center gap-2"><GitMerge /> Vector Space Model</h3>
                <form onSubmit={fetchVsm} className="flex gap-4 mb-8">
                  <input 
                    type="text" 
                    placeholder="Enter query to vectorize..." 
                    className="bg-transparent border border-border rounded px-4 py-2 text-textPrimary focus:border-highlight outline-none flex-1"
                    value={vsmQuery}
                    onChange={(e) => setVsmQuery(e.target.value)}
                  />
                  <button type="submit" className="border border-highlight text-highlight px-4 rounded hover:bg-highlight/20 transition-colors">Vectorize & Search</button>
                </form>

                {vsmData && (
                  <div className="space-y-6 text-sm">
                    <div className="bg-surface p-4 rounded border border-border">
                      <div className="text-highlight mb-2">Query Vector:</div>
                      <div className="text-green-400 break-words">
                        {JSON.stringify(vsmData.query_vector)}
                      </div>
                    </div>
                    
                    <div className="text-textMuted">Top 5 Document Vectors (Cosine Similarity):</div>
                    <div className="space-y-4">
                      {vsmData.top_documents.map((doc, idx) => (
                        <div key={idx} className="bg-[#0a0f1e] p-4 rounded border border-border/50">
                          <div className="flex justify-between mb-2">
                            <span className="text-secondary font-bold">Doc {doc.doc_id}</span>
                            <span className="text-highlight font-bold">Score: {doc.cosine_similarity}</span>
                          </div>
                          <div className="text-textMuted mb-1 line-clamp-1">{doc.title}</div>
                          <div className="text-blue-400 break-words text-xs">
                            {JSON.stringify(doc.document_vector)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default IRLab;
