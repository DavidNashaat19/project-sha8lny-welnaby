import React from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Search, BarChart3, Target, Database } from 'lucide-react';

const Landing = () => {
  const { t } = useTranslation();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { 
      opacity: 1,
      transition: { staggerChildren: 0.2 }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1, transition: { duration: 0.6, ease: "easeOut" } }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[85vh] px-4 relative">
      {/* Abstract Background Elements */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[100px] -z-10" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/10 rounded-full blur-[100px] -z-10" />

      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="text-center max-w-4xl mx-auto mt-20"
      >
        <motion.h1 variants={itemVariants} className="text-6xl md:text-8xl font-display font-bold mb-6">
          <span className="gradient-text">{t('app_name')}</span>
        </motion.h1>
        
        <motion.p variants={itemVariants} className="text-xl md:text-2xl text-textPrimary mb-4 font-light">
          {t('tagline')}
        </motion.p>
        
        <motion.p variants={itemVariants} className="text-md text-textMuted mb-12 max-w-2xl mx-auto">
          {t('sub_tagline')}
        </motion.p>

        <motion.div variants={itemVariants} className="flex flex-col sm:flex-row gap-6 justify-center">
          <Link to="/search" className="primary-button flex items-center gap-2 justify-center py-4 text-lg">
            {t('search_jobs')} <Search size={20} />
          </Link>
          <Link to="/analytics" className="secondary-button flex items-center gap-2 justify-center py-4 text-lg">
            {t('explore_analytics')} <BarChart3 size={20} />
          </Link>
        </motion.div>
      </motion.div>

      {/* Stats Section */}
      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, delay: 0.4 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-8 w-full max-w-5xl mt-32 mb-20"
      >
        <div className="glass-card p-6 text-center">
          <div className="text-4xl font-display font-bold text-primary mb-2">300+</div>
          <div className="text-sm text-textMuted uppercase tracking-wider">{t('stats.jobs')}</div>
        </div>
        <div className="glass-card p-6 text-center">
          <div className="text-4xl font-display font-bold text-secondary mb-2">2</div>
          <div className="text-sm text-textMuted uppercase tracking-wider">{t('stats.platforms')}</div>
        </div>
        <div className="glass-card p-6 text-center">
          <div className="text-4xl font-display font-bold text-highlight mb-2">50+</div>
          <div className="text-sm text-textMuted uppercase tracking-wider">{t('stats.categories')}</div>
        </div>
        <div className="glass-card p-6 text-center">
          <div className="text-primary flex justify-center mb-2"><Database size={40} /></div>
          <div className="text-sm text-textMuted uppercase tracking-wider">{t('stats.engine')}</div>
        </div>
      </motion.div>

      {/* Features */}
      <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto w-full pb-20">
        <motion.div 
          whileHover={{ y: -5 }}
          className="glass-card p-8"
        >
          <Search className="text-primary mb-6" size={32} />
          <h3 className="text-2xl font-display font-semibold mb-4">{t('features.search_title')}</h3>
          <p className="text-textMuted leading-relaxed">{t('features.search_desc')}</p>
        </motion.div>

        <motion.div 
          whileHover={{ y: -5 }}
          className="glass-card p-8"
        >
          <BarChart3 className="text-secondary mb-6" size={32} />
          <h3 className="text-2xl font-display font-semibold mb-4">{t('features.analytics_title')}</h3>
          <p className="text-textMuted leading-relaxed">{t('features.analytics_desc')}</p>
        </motion.div>

        <motion.div 
          whileHover={{ y: -5 }}
          className="glass-card p-8"
        >
          <Target className="text-highlight mb-6" size={32} />
          <h3 className="text-2xl font-display font-semibold mb-4">{t('features.match_title')}</h3>
          <p className="text-textMuted leading-relaxed">{t('features.match_desc')}</p>
        </motion.div>
      </div>
    </div>
  );
};

export default Landing;
