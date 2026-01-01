// Theme, font size, and motion utilities
export const applyReducedMotion = (reduceMotion) => {
  const root = window.document.documentElement;
  
  if (reduceMotion) {
    root.classList.add('reduce-motion');
  } else {
    root.classList.remove('reduce-motion');
  }
  
  // Save to localStorage
  localStorage.setItem('tovplay-reduce-motion', reduceMotion ? 'true' : 'false');};

export const applyTheme = (theme) => {
  const root = window.document.documentElement;
  
  // For Tailwind, we only need to add/remove the 'dark' class
  if (theme === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
  
  // Save to localStorage
  localStorage.setItem('tovplay-theme', theme);
  
  // Update the data-theme attribute for other potential theme systems
  root.setAttribute('data-theme', theme);
  
  // Dispatch a custom event to notify about theme change
  window.dispatchEvent(new CustomEvent('theme-changed', { detail: { theme } }));
};

export const applyFontSize = (size) => {
  const root = window.document.documentElement;
  
  // Remove all font size classes
  root.classList.remove('font-size-small', 'font-size-medium', 'font-size-large');
  
  // Apply the selected font size
  if (['small', 'medium', 'large'].includes(size)) {
    root.classList.add(`font-size-${size}`);
  }
  
  // Save to localStorage
  localStorage.setItem('tovplay-font-size', size);
  
  // Dispatch a custom event to notify about font size change
  window.dispatchEvent(new CustomEvent('font-size-changed', { detail: { size } }));
};
