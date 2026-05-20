import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      "app_name": "Sha8lny Welnaby",
      "tagline": "Find Your Next Freelance Edge",
      "sub_tagline": "AI-powered search across Freelancer.com & Fiverr.com — built on real IR algorithms",
      "search_jobs": "Search Jobs",
      "explore_analytics": "Explore Analytics",
      "nav": {
        "search": "Search",
        "analytics": "Analytics",
        "match": "Match",
        "ir_lab": "IR Lab"
      },
      "stats": {
        "jobs": "Jobs Indexed",
        "platforms": "Platforms",
        "categories": "Skill Categories",
        "engine": "Real IR Engine"
      },
      "features": {
        "search_title": "Smart Search",
        "search_desc": "Find jobs matching your skills using TF-IDF, Vector Space Model, Boolean logic and positional indexing.",
        "analytics_title": "Market Analytics",
        "analytics_desc": "Interactive charts showing salary distributions, skill demand, and market trends.",
        "match_title": "Skill Match",
        "match_desc": "Discover how well your profile aligns with current market demand and identify gap skills."
      }
    }
  },
  ar: {
    translation: {
      "app_name": "شغلني ولنبي",
      "tagline": "اكتشف فرصتك القادمة في العمل الحر",
      "sub_tagline": "بحث ذكي عبر Fiverr وفريلانسر — مبني على خوارزميات استرجاع المعلومات",
      "search_jobs": "ابحث عن وظائف",
      "explore_analytics": "تصفح الإحصائيات",
      "nav": {
        "search": "بحث",
        "analytics": "إحصائيات",
        "match": "مطابقة",
        "ir_lab": "مختبر البحث"
      },
      "stats": {
        "jobs": "وظيفة مؤرشفة",
        "platforms": "منصات",
        "categories": "فئة مهارات",
        "engine": "محرك بحث حقيقي"
      },
      "features": {
        "search_title": "بحث ذكي",
        "search_desc": "ابحث عن وظائف تناسب مهاراتك باستخدام TF-IDF ونموذج الفضاء المتجهي والمنطق البوليني.",
        "analytics_title": "تحليل السوق",
        "analytics_desc": "رسوم بيانية تفاعلية توضح توزيع الرواتب، الطلب على المهارات، واتجاهات السوق.",
        "match_title": "مطابقة المهارات",
        "match_desc": "اكتشف مدى توافق ملفك الشخصي مع متطلبات السوق الحالية وتعرّف على المهارات الناقصة."
      }
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: "en", // default language
    fallbackLng: "en",
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
