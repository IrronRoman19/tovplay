import { createContext, useContext, useState, useEffect } from 'react';
import { applyTheme, applyFontSize, applyReducedMotion } from '@/utils/themeUtils';

const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  const [fontSize, setFontSize] = useState('medium');
  const [reduceMotion, setReduceMotion] = useState(false);

  // Initialize theme from localStorage on mount
  useEffect(() => {
    // Get saved preferences with defaults
    const savedTheme = localStorage.getItem('tovplay-theme') || 'light';
    const savedFontSize = localStorage.getItem('tovplay-font-size') || 'medium';
    const savedReduceMotion = localStorage.getItem('tovplay-reduce-motion') === 'true';
    
    // Update state
    setTheme(savedTheme);
    setFontSize(savedFontSize);
    setReduceMotion(savedReduceMotion);
    
    // Apply the saved settings
    applyTheme(savedTheme);
    applyFontSize(savedFontSize);
    applyReducedMotion(savedReduceMotion);
    
    // Add a class to the body to indicate theme is loaded (for FOUC prevention)
    document.body.classList.add('theme-loaded');
    
    // Cleanup
    return () => {
      document.body.classList.remove('theme-loaded');
    };
  }, []);

  const updateTheme = (newTheme) => {
    // Ensure the theme is valid
    const theme = ['light', 'dark', 'system'].includes(newTheme) ? newTheme : 'light';
    setTheme(theme);
    applyTheme(theme);
    
    // Dispatch a storage event to sync across tabs
    window.dispatchEvent(
      new StorageEvent('storage', {
        key: 'tovplay-theme',
        newValue: theme,
        storageArea: localStorage
      })
    );
  };

  const updateFontSize = (newSize) => {
    setFontSize(newSize);
    applyFontSize(newSize);
  };

  const updateReduceMotion = (newValue) => {
    setReduceMotion(newValue);
    applyReducedMotion(newValue);
  };

  return (
    <ThemeContext.Provider
      value={{
        theme,
        fontSize,
        reduceMotion,
        updateTheme,
        updateFontSize,
        updateReduceMotion,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
