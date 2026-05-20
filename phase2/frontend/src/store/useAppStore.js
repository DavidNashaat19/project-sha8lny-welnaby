import { create } from 'zustand';

export const useAppStore = create((set) => ({
  searchQuery: '',
  searchMode: 'tfidf',
  platformFilter: [],
  skillsFilter: [],
  budgetMin: null,
  budgetMax: null,
  
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSearchMode: (mode) => set({ searchMode: mode }),
  setPlatformFilter: (platforms) => set({ platformFilter: platforms }),
  setSkillsFilter: (skills) => set({ skillsFilter: skills }),
  setBudgetRange: (min, max) => set({ budgetMin: min, budgetMax: max }),
  
  // App state
  isDrawerOpen: false,
  selectedJob: null,
  openDrawer: (job) => set({ isDrawerOpen: true, selectedJob: job }),
  closeDrawer: () => set({ isDrawerOpen: false, selectedJob: null }),
}));
