# SizeComparator Theme System Specification

## 1. Executive Summary

### Overview
The SizeComparator theme system provides a robust, performant light/dark mode implementation with zero-flicker loading, smooth transitions, and comprehensive browser support. Built entirely with vanilla HTML/CSS/JavaScript, it integrates seamlessly with the existing frontend architecture while maintaining sub-16ms theme switching performance.

### Key Features
- **Zero-Flicker Loading**: Inline script prevents theme flash on page load
- **Smooth Transitions**: Hardware-accelerated animations under 200ms
- **System Integration**: Automatic detection and syncing with OS preferences
- **Persistent State**: LocalStorage with validation and fallbacks
- **Full Accessibility**: WCAG 2.1 AA compliant with proper ARIA support
- **Progressive Enhancement**: Graceful degradation for older browsers

### Architecture Overview
The theme system uses CSS custom properties as its foundation, with JavaScript managing state persistence and user interactions. All components inherit theme values through semantic tokens, ensuring consistent visual updates across the application.

## 2. CSS Custom Properties Architecture

### 2.1 Core Color System

```css
:root {
    /* === LIGHT THEME (DEFAULT) === */
    
    /* Primary Surfaces */
    --color-bg-primary: #ffffff;
    --color-bg-secondary: #f8fafc;
    --color-bg-tertiary: #f1f5f9;
    --color-bg-elevated: #ffffff;
    --color-bg-overlay: rgba(0, 0, 0, 0.5);
    
    /* Text Hierarchy */
    --color-text-primary: #0f172a;
    --color-text-secondary: #475569;
    --color-text-tertiary: #64748b;
    --color-text-disabled: #94a3b8;
    --color-text-inverse: #ffffff;
    
    /* Interactive Elements */
    --color-interactive-primary: #3b82f6;
    --color-interactive-primary-hover: #2563eb;
    --color-interactive-primary-active: #1d4ed8;
    --color-interactive-secondary: #6b7280;
    --color-interactive-secondary-hover: #4b5563;
    
    /* Borders */
    --color-border-primary: #e2e8f0;
    --color-border-secondary: #cbd5e1;
    --color-border-interactive: #d1d5db;
    --color-border-focus: #3b82f6;
    
    /* Status Colors */
    --color-status-error: #ef4444;
    --color-status-error-bg: #fef2f2;
    --color-status-success: #10b981;
    --color-status-success-bg: #f0fdf4;
    --color-status-warning: #f59e0b;
    --color-status-warning-bg: #fffbeb;
    
    /* Shadows */
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    
    /* Transitions */
    --transition-theme-fast: 150ms ease-out;
    --transition-theme-standard: 200ms ease-out;
    --transition-theme-slow: 300ms ease-out;
}

[data-theme="dark"] {
    /* === DARK THEME OVERRIDES === */
    
    /* Primary Surfaces */
    --color-bg-primary: #0f172a;
    --color-bg-secondary: #1e293b;
    --color-bg-tertiary: #334155;
    --color-bg-elevated: #1e293b;
    --color-bg-overlay: rgba(0, 0, 0, 0.7);
    
    /* Text Hierarchy */
    --color-text-primary: #f8fafc;
    --color-text-secondary: #cbd5e1;
    --color-text-tertiary: #94a3b8;
    --color-text-disabled: #64748b;
    --color-text-inverse: #0f172a;
    
    /* Interactive Elements */
    --color-interactive-primary: #60a5fa;
    --color-interactive-primary-hover: #3b82f6;
    --color-interactive-primary-active: #2563eb;
    --color-interactive-secondary: #94a3b8;
    --color-interactive-secondary-hover: #cbd5e1;
    
    /* Borders */
    --color-border-primary: #334155;
    --color-border-secondary: #475569;
    --color-border-interactive: #64748b;
    --color-border-focus: #60a5fa;
    
    /* Status Colors (adjusted for dark backgrounds) */
    --color-status-error: #f87171;
    --color-status-error-bg: rgba(239, 68, 68, 0.1);
    --color-status-success: #34d399;
    --color-status-success-bg: rgba(16, 185, 129, 0.1);
    --color-status-warning: #fbbf24;
    --color-status-warning-bg: rgba(245, 158, 11, 0.1);
    
    /* Enhanced shadows for dark mode */
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3);
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
}
```

### 2.2 Semantic Component Tokens

```css
:root {
    /* Component-specific semantic tokens */
    --input-bg: var(--color-bg-primary);
    --input-border: var(--color-border-interactive);
    --input-focus-border: var(--color-border-focus);
    --input-text: var(--color-text-primary);
    --input-placeholder: var(--color-text-tertiary);
    
    --card-bg: var(--color-bg-elevated);
    --card-border: var(--color-border-primary);
    --card-shadow: var(--shadow-md);
    --card-hover-shadow: var(--shadow-lg);
    
    --button-primary-bg: var(--color-interactive-primary);
    --button-primary-hover: var(--color-interactive-primary-hover);
    --button-primary-text: var(--color-text-inverse);
    --button-secondary-bg: var(--color-bg-secondary);
    --button-secondary-hover: var(--color-bg-tertiary);
    --button-secondary-text: var(--color-text-primary);
    
    --header-bg: var(--color-bg-primary);
    --header-border: var(--color-border-primary);
    --header-shadow: var(--shadow-sm);
}
```

### 2.3 Accessibility Enhancements

```css
/* High contrast mode adjustments */
@media (prefers-contrast: high) {
    :root {
        --color-border-primary: #000000;
        --color-border-focus: #0066ff;
        --color-text-secondary: var(--color-text-primary);
        --shadow-md: 0 0 0 1px #000000;
    }
    
    [data-theme="dark"] {
        --color-border-primary: #ffffff;
        --color-border-focus: #66b3ff;
        --shadow-md: 0 0 0 1px #ffffff;
    }
}

/* Reduced motion preferences */
@media (prefers-reduced-motion: reduce) {
    :root {
        --transition-theme-fast: 0ms;
        --transition-theme-standard: 0ms;
        --transition-theme-slow: 0ms;
    }
}
```

## 3. Theme Toggle Component

### 3.1 HTML Structure

```html
<button 
    id="theme-toggle" 
    class="theme-toggle"
    type="button"
    aria-label="Toggle dark mode"
    aria-pressed="false"
    data-theme-toggle
>
    <svg class="theme-icon theme-icon--light" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="5" fill="none" stroke="currentColor" stroke-width="2"/>
        <path d="M12 1v6m0 6v6m-9-9h6m6 0h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M20.5 7.5L16 12l4.5 4.5M3.5 7.5L8 12l-4.5 4.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <svg class="theme-icon theme-icon--dark" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" 
              fill="none" 
              stroke="currentColor" 
              stroke-width="2" 
              stroke-linecap="round" 
              stroke-linejoin="round"/>
    </svg>
    <span class="theme-toggle__label">Dark mode</span>
</button>
```

### 3.2 CSS Implementation

```css
.theme-toggle {
    /* Layout */
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    
    /* Appearance */
    background-color: var(--button-secondary-bg);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border-interactive);
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 500;
    
    /* Transitions */
    transition: 
        background-color var(--transition-theme-standard),
        border-color var(--transition-theme-standard),
        color var(--transition-theme-standard),
        transform var(--transition-theme-fast),
        box-shadow var(--transition-theme-fast);
    
    /* Interaction */
    cursor: pointer;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
}

.theme-toggle:hover {
    background-color: var(--button-secondary-hover);
    border-color: var(--color-border-focus);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

.theme-toggle:focus-visible {
    outline: 2px solid var(--color-border-focus);
    outline-offset: 2px;
}

.theme-toggle:active {
    transform: translateY(0);
}

/* Icon animations */
.theme-icon {
    width: 1.25rem;
    height: 1.25rem;
    flex-shrink: 0;
    transition: 
        opacity var(--transition-theme-standard),
        transform var(--transition-theme-standard);
}

.theme-icon--light {
    opacity: 1;
    transform: rotate(0deg);
}

.theme-icon--dark {
    position: absolute;
    left: 0.5rem;
    opacity: 0;
    transform: rotate(-90deg);
}

[data-theme="dark"] .theme-icon--light {
    opacity: 0;
    transform: rotate(90deg);
}

[data-theme="dark"] .theme-icon--dark {
    opacity: 1;
    transform: rotate(0deg);
}

/* Mobile optimization */
@media (max-width: 768px) {
    .theme-toggle {
        padding: 0.625rem;
        border-radius: 50%;
        aspect-ratio: 1;
    }
    
    .theme-toggle__label {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
}
```

### 3.3 JavaScript Implementation

```javascript
class ThemeToggle {
    constructor() {
        this.button = document.querySelector('[data-theme-toggle]');
        if (!this.button) return;
        
        this.label = this.button.querySelector('.theme-toggle__label');
        this.init();
    }
    
    init() {
        // Set initial state
        this.updateButtonState();
        
        // Event listeners
        this.button.addEventListener('click', () => this.handleToggle());
        
        // Listen for theme changes from other sources
        document.addEventListener('themechange', (e) => {
            this.updateButtonState(e.detail.theme);
        });
    }
    
    handleToggle() {
        const currentTheme = ThemeManager.getCurrentTheme();
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        // Measure performance
        const measure = performance.mark('theme-switch-start');
        
        // Apply theme
        ThemeManager.setTheme(newTheme);
        
        // Log performance
        performance.mark('theme-switch-end');
        performance.measure('theme-switch', 'theme-switch-start', 'theme-switch-end');
        
        const duration = performance.getEntriesByName('theme-switch')[0].duration;
        if (duration > 50) {
            console.warn(`Theme switch took ${duration.toFixed(2)}ms (target: <50ms)`);
        }
    }
    
    updateButtonState(theme = ThemeManager.getCurrentTheme()) {
        const isDark = theme === 'dark';
        
        // Update ARIA
        this.button.setAttribute('aria-pressed', isDark.toString());
        this.button.setAttribute('aria-label', 
            isDark ? 'Switch to light mode' : 'Switch to dark mode'
        );
        
        // Update label
        if (this.label) {
            this.label.textContent = isDark ? 'Light mode' : 'Dark mode';
        }
    }
}
```

## 4. Theme Persistence & System Integration

### 4.1 Core Theme Manager

```javascript
const ThemeManager = (() => {
    const STORAGE_KEY = 'sizecomparator-theme-preference';
    const THEME_ATTRIBUTE = 'data-theme';
    const VALID_THEMES = ['light', 'dark', 'system'];
    
    let currentTheme = null;
    let systemPreference = null;
    let mediaQuery = null;
    
    const detectSystemPreference = () => {
        if (!window.matchMedia) return 'light';
        
        mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        return mediaQuery.matches ? 'dark' : 'light';
    };
    
    const getStoredPreference = () => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            return VALID_THEMES.includes(stored) ? stored : null;
        } catch {
            return null;
        }
    };
    
    const storePreference = (preference) => {
        try {
            localStorage.setItem(STORAGE_KEY, preference);
            return true;
        } catch {
            console.warn('Failed to store theme preference');
            return false;
        }
    };
    
    const applyTheme = (theme) => {
        if (theme !== 'light' && theme !== 'dark') return;
        
        document.documentElement.setAttribute(THEME_ATTRIBUTE, theme);
        currentTheme = theme;
        
        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('themechange', {
            detail: { theme, timestamp: Date.now() }
        }));
    };
    
    const init = () => {
        // Detect system preference
        systemPreference = detectSystemPreference();
        
        // Listen for system changes
        if (mediaQuery?.addEventListener) {
            mediaQuery.addEventListener('change', (e) => {
                systemPreference = e.matches ? 'dark' : 'light';
                
                // Auto-update if using system preference
                const stored = getStoredPreference();
                if (!stored || stored === 'system') {
                    applyTheme(systemPreference);
                }
            });
        }
        
        // Apply initial theme
        const preference = getStoredPreference();
        const theme = (!preference || preference === 'system') 
            ? systemPreference 
            : preference;
        
        applyTheme(theme);
    };
    
    // Public API
    return {
        init,
        
        getCurrentTheme() {
            return document.documentElement.getAttribute(THEME_ATTRIBUTE) || 'light';
        },
        
        setTheme(theme) {
            if (!VALID_THEMES.includes(theme)) {
                console.error(`Invalid theme: ${theme}`);
                return false;
            }
            
            // Store preference
            storePreference(theme);
            
            // Apply theme
            const actualTheme = theme === 'system' ? systemPreference : theme;
            applyTheme(actualTheme);
            
            return true;
        },
        
        getSystemPreference() {
            return systemPreference;
        }
    };
})();
```

### 4.2 Zero-Flicker Prevention Script

```html
<!-- This script MUST be placed in <head> before any CSS -->
<script>
(function() {
    // Constants matching ThemeManager
    const STORAGE_KEY = 'sizecomparator-theme-preference';
    const THEME_ATTRIBUTE = 'data-theme';
    
    // Get stored preference
    let theme = 'light';
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored === 'dark' || stored === 'light') {
            theme = stored;
        } else if (!stored || stored === 'system') {
            // Check system preference
            if (window.matchMedia && 
                window.matchMedia('(prefers-color-scheme: dark)').matches) {
                theme = 'dark';
            }
        }
    } catch (e) {
        // localStorage not available
    }
    
    // Apply theme immediately
    document.documentElement.setAttribute(THEME_ATTRIBUTE, theme);
    
    // Add loading class to prevent transitions
    document.documentElement.classList.add('theme-loading');
})();
</script>

<!-- Remove loading class after DOM ready -->
<script>
document.addEventListener('DOMContentLoaded', function() {
    requestAnimationFrame(function() {
        document.documentElement.classList.remove('theme-loading');
    });
});
</script>
```

### 4.3 CSS Loading State

```css
/* Prevent all transitions during initial load */
.theme-loading * {
    transition: none !important;
}

/* Ensure smooth transitions after load */
html:not(.theme-loading) {
    transition: none;
}

html:not(.theme-loading) *,
html:not(.theme-loading) *::before,
html:not(.theme-loading) *::after {
    transition-duration: inherit;
    transition-timing-function: inherit;
}
```

## 5. Component Integration Patterns

### 5.1 Form Components

```css
/* Weight input fields */
.weight-input {
    /* Base styles */
    width: 100%;
    padding: 0.75rem 1rem;
    font-size: 1rem;
    line-height: 1.5;
    
    /* Theme-aware colors */
    background-color: var(--input-bg);
    color: var(--input-text);
    border: 1px solid var(--input-border);
    border-radius: 0.375rem;
    
    /* Transitions */
    transition: 
        background-color var(--transition-theme-standard),
        border-color var(--transition-theme-standard),
        color var(--transition-theme-standard),
        box-shadow var(--transition-theme-fast);
}

.weight-input:hover:not(:disabled) {
    border-color: var(--color-border-secondary);
}

.weight-input:focus {
    outline: none;
    border-color: var(--input-focus-border);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

[data-theme="dark"] .weight-input:focus {
    box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1);
}

.weight-input::placeholder {
    color: var(--input-placeholder);
    opacity: 1;
}

.weight-input:disabled {
    background-color: var(--color-bg-secondary);
    color: var(--color-text-disabled);
    cursor: not-allowed;
}
```

### 5.2 Results Display Components

```css
/* Comparison cards */
.comparison-card {
    /* Layout */
    padding: 1.5rem;
    border-radius: 0.5rem;
    
    /* Theme colors */
    background-color: var(--card-bg);
    border: 1px solid var(--card-border);
    box-shadow: var(--card-shadow);
    
    /* Transitions */
    transition: 
        background-color var(--transition-theme-standard),
        border-color var(--transition-theme-standard),
        box-shadow var(--transition-theme-standard),
        transform var(--transition-theme-fast);
}

.comparison-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--card-hover-shadow);
}

/* Result values */
.comparison-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--color-text-primary);
    transition: color var(--transition-theme-standard);
}

.comparison-label {
    font-size: 0.875rem;
    color: var(--color-text-secondary);
    transition: color var(--transition-theme-standard);
}

/* Ratio indicator */
.ratio-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
    background-color: var(--color-interactive-primary);
    color: var(--color-text-inverse);
    transition: 
        background-color var(--transition-theme-standard),
        color var(--transition-theme-standard);
}
```

### 5.3 Loading & Error States

```css
/* Loading spinner */
.loading-spinner {
    width: 2.5rem;
    height: 2.5rem;
    border: 3px solid var(--color-border-primary);
    border-top-color: var(--color-interactive-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    transition: border-color var(--transition-theme-standard);
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Error messages */
.error-message {
    padding: 1rem;
    border-radius: 0.375rem;
    background-color: var(--color-status-error-bg);
    color: var(--color-status-error);
    border: 1px solid var(--color-status-error);
    transition: all var(--transition-theme-standard);
}

.error-message__icon {
    display: inline-block;
    width: 1.25rem;
    height: 1.25rem;
    margin-right: 0.5rem;
    vertical-align: middle;
}

/* Success messages */
.success-message {
    padding: 1rem;
    border-radius: 0.375rem;
    background-color: var(--color-status-success-bg);
    color: var(--color-status-success);
    border: 1px solid var(--color-status-success);
    transition: all var(--transition-theme-standard);
}
```

### 5.4 Theme-Aware Component Factory

```javascript
class ThemeAwareComponent {
    constructor(element, options = {}) {
        this.element = element;
        this.options = options;
        this.themeListeners = new Map();
        
        this.init();
    }
    
    init() {
        // Listen for theme changes
        this.themeChangeHandler = (e) => this.onThemeChange(e.detail.theme);
        document.addEventListener('themechange', this.themeChangeHandler);
        
        // Apply initial theme-specific setup
        this.onThemeChange(ThemeManager.getCurrentTheme());
    }
    
    onThemeChange(theme) {
        // Execute theme-specific callbacks
        const callbacks = this.themeListeners.get(theme) || [];
        callbacks.forEach(callback => callback.call(this, theme));
        
        // Update component classes
        this.element.className = this.element.className
            .replace(/theme-\w+/g, '')
            .trim() + ` theme-${theme}`;
    }
    
    whenTheme(theme, callback) {
        if (!this.themeListeners.has(theme)) {
            this.themeListeners.set(theme, []);
        }
        this.themeListeners.get(theme).push(callback);
        
        // Execute immediately if current theme matches
        if (ThemeManager.getCurrentTheme() === theme) {
            callback.call(this, theme);
        }
        
        return this;
    }
    
    destroy() {
        document.removeEventListener('themechange', this.themeChangeHandler);
        this.themeListeners.clear();
    }
}

// Usage example
const card = new ThemeAwareComponent(document.querySelector('.comparison-card'))
    .whenTheme('dark', function() {
        // Dark theme specific behavior
        this.element.style.setProperty('--card-glow', '0 0 20px rgba(96, 165, 250, 0.1)');
    })
    .whenTheme('light', function() {
        // Light theme specific behavior
        this.element.style.removeProperty('--card-glow');
    });
```

## 6. Performance Optimization

### 6.1 Critical Performance Metrics

| Metric | Target | Strategy |
|--------|--------|----------|
| Initial theme application | < 16ms | Inline script execution |
| Theme switch animation | < 200ms | CSS transitions only |
| Memory usage | < 50KB | Efficient data structures |
| Paint operations | 1 per switch | Batched DOM updates |
| Layout shifts | 0 | Fixed dimensions |

### 6.2 Optimization Techniques

```javascript
// Performance-optimized theme switching
const OptimizedThemeSwitch = {
    scheduleThemeChange(newTheme) {
        // Use RAF to batch DOM operations
        requestAnimationFrame(() => {
            // Mark paint boundary
            document.documentElement.style.contain = 'paint';
            
            // Apply theme
            ThemeManager.setTheme(newTheme);
            
            // Schedule cleanup
            requestAnimationFrame(() => {
                document.documentElement.style.contain = '';
            });
        });
    },
    
    // Debounced system preference listener
    createDebouncedListener(callback, delay = 100) {
        let timeoutId;
        return (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => callback(...args), delay);
        };
    }
};
```

### 6.3 CSS Performance Optimizations

```css
/* Use CSS containment for performance */
.theme-toggle,
.comparison-card,
.weight-input {
    contain: layout style paint;
}

/* Optimize repaints with will-change */
.theme-transition-active * {
    will-change: background-color, color, border-color;
}

/* Remove will-change after transition */
.theme-transition-complete * {
    will-change: auto;
}

/* Use transform for animations instead of position */
.comparison-card {
    transform: translateY(0);
    transition: transform var(--transition-theme-fast);
}

.comparison-card:hover {
    transform: translateY(-2px);
}
```

## 7. Browser Compatibility

### 7.1 Support Matrix

| Feature | Chrome 90+ | Firefox 88+ | Safari 14+ | Edge 90+ |
|---------|------------|-------------|------------|----------|
| CSS Custom Properties | ✅ | ✅ | ✅ | ✅ |
| data-* attributes | ✅ | ✅ | ✅ | ✅ |
| matchMedia | ✅ | ✅ | ✅ | ✅ |
| localStorage | ✅ | ✅ | ✅ | ✅ |
| CSS transitions | ✅ | ✅ | ✅ | ✅ |
| contain property | ✅ | ✅ | Partial | ✅ |

### 7.2 Progressive Enhancement

```javascript
// Feature detection and fallbacks
const FeatureSupport = {
    hasCustomProperties: CSS && CSS.supports && CSS.supports('(--test: 0)'),
    hasMatchMedia: 'matchMedia' in window,
    hasLocalStorage: (() => {
        try {
            localStorage.setItem('test', '1');
            localStorage.removeItem('test');
            return true;
        } catch {
            return false;
        }
    })(),
    
    // Fallback theme system for older browsers
    fallbackTheme: {
        current: 'light',
        
        apply(theme) {
            document.body.className = document.body.className
                .replace(/\btheme-\w+\b/g, '')
                .trim() + ` theme-${theme}`;
            this.current = theme;
        },
        
        toggle() {
            this.apply(this.current === 'light' ? 'dark' : 'light');
        }
    }
};

// Initialize appropriate system
if (FeatureSupport.hasCustomProperties) {
    ThemeManager.init();
} else {
    // Use class-based fallback
    FeatureSupport.fallbackTheme.apply('light');
}
```

### 7.3 Fallback CSS

```css
/* Class-based theme fallback for older browsers */
body.theme-light {
    background-color: #ffffff;
    color: #0f172a;
}

body.theme-dark {
    background-color: #0f172a;
    color: #f8fafc;
}

/* Component fallbacks */
.theme-light .comparison-card {
    background-color: #ffffff;
    border-color: #e2e8f0;
}

.theme-dark .comparison-card {
    background-color: #1e293b;
    border-color: #334155;
}

/* Feature queries for progressive enhancement */
@supports (color: var(--test)) {
    /* Modern theme system styles */
}

@supports not (color: var(--test)) {
    /* Fallback styles */
}
```

## 8. Implementation Checklist

### Phase 1: Foundation
- [ ] Implement CSS custom properties system
- [ ] Create zero-flicker prevention script
- [ ] Set up theme manager core functionality
- [ ] Add system preference detection

### Phase 2: Components
- [ ] Build theme toggle component
- [ ] Implement smooth transitions
- [ ] Add keyboard accessibility
- [ ] Create mobile-optimized version

### Phase 3: Integration
- [ ] Update all UI components with theme tokens
- [ ] Add theme-aware component patterns
- [ ] Implement performance optimizations
- [ ] Set up browser compatibility fallbacks

### Phase 4: Polish
- [ ] Performance testing and optimization
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Cross-browser testing
- [ ] Documentation and examples

## 9. Testing Guidelines

### 9.1 Manual Testing Checklist
- [ ] No theme flicker on page load
- [ ] Smooth transitions under 200ms
- [ ] Theme persists across page reloads
- [ ] System preference changes are detected
- [ ] All UI elements update correctly
- [ ] Keyboard navigation works properly
- [ ] Mobile touch interactions are smooth

### 9.2 Automated Testing
```javascript
// Example theme system tests
describe('ThemeManager', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute('data-theme');
    });
    
    test('applies default theme on init', () => {
        ThemeManager.init();
        expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    });
    
    test('persists theme preference', () => {
        ThemeManager.setTheme('dark');
        expect(localStorage.getItem('sizecomparator-theme-preference')).toBe('dark');
    });
    
    test('respects system preference when set to system', () => {
        window.matchMedia = jest.fn().mockImplementation(query => ({
            matches: query === '(prefers-color-scheme: dark)',
            addEventListener: jest.fn()
        }));
        
        ThemeManager.setTheme('system');
        expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    });
});
```

## 10. Maintenance Guidelines

### 10.1 Adding New Theme Colors
1. Add color to both light and dark theme in `:root` and `[data-theme="dark"]`
2. Create semantic token if needed
3. Update high contrast mode overrides
4. Test color contrast ratios (WCAG AA: 4.5:1 for normal text, 3:1 for large text)

### 10.2 Performance Monitoring
- Use Performance Observer API to track theme switch duration
- Monitor reflow/repaint operations with Chrome DevTools
- Keep theme system under 50KB total (CSS + JS)
- Ensure no layout shifts during theme changes

### 10.3 Browser Updates
- Test new browser versions quarterly
- Update feature detection as needed
- Maintain fallbacks until browser usage < 1%
- Document any browser-specific workarounds

This theme system provides a robust, performant, and accessible foundation for SizeComparator's UI, ensuring users have a seamless experience regardless of their theme preference or system configuration.