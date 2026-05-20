import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import Landing from './pages/Landing';
import Search from './pages/Search';
import Analytics from './pages/Analytics';
import Match from './pages/Match';
import IRLab from './pages/IRLab';

const Navbar = () => {
  const { t, i18n } = useTranslation();

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language === 'en' ? 'ar' : 'en');
  };

  return (
    <nav className="sticky top-0 z-50 glass-card rounded-none border-t-0 border-l-0 border-r-0 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <Link to="/" className="text-2xl font-display font-bold gradient-text flex items-center gap-2">
          <span className="text-primary text-3xl">∿</span>
          {t('app_name')}
        </Link>
        
        <div className="hidden md:flex items-center gap-6 text-sm font-medium">
          <Link to="/search" className="hover:text-primary transition-colors">{t('nav.search')}</Link>
          <Link to="/analytics" className="hover:text-primary transition-colors">{t('nav.analytics')}</Link>
          <Link to="/match" className="hover:text-primary transition-colors">{t('nav.match')}</Link>
          <Link to="/ir-lab" className="hover:text-primary transition-colors">{t('nav.ir_lab')}</Link>
        </div>
      </div>
      
      <button 
        onClick={toggleLanguage}
        className="flex items-center gap-2 text-sm hover:text-primary transition-colors"
      >
        <Globe size={18} />
        {i18n.language === 'en' ? 'عربي' : 'English'}
      </button>
    </nav>
  );
};

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/search" element={<Search />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/match" element={<Match />} />
            <Route path="/ir-lab" element={<IRLab />} />
          </Routes>
        </main>
        <footer className="py-6 text-center text-textMuted text-sm border-t border-border mt-12">
          <p>Sha8lny Welnaby © 2026 — CS313x Information Retrieval</p>
        </footer>
      </div>
    </BrowserRouter>
  )
}

export default App;
