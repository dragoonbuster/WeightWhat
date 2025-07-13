# SizeComparator Frontend Specification

## 1. Executive Summary

### Project Overview
SizeComparator's frontend provides a lightweight, responsive web interface for weight comparison functionality. Built with vanilla HTML, CSS, and JavaScript, the frontend emphasizes zero dependencies, fast loading times, and universal browser compatibility while delivering a modern user experience.

### Technical Approach
The frontend architecture follows a single-page application pattern without frameworks, leveraging native browser APIs and modern CSS features. This approach ensures minimal bundle size (<50KB total), sub-100ms initial paint times, and compatibility with all modern browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+).

### Success Metrics
- **Performance**: Initial paint < 100ms, Time to Interactive < 500ms
- **Accessibility**: WCAG 2.1 AA compliance
- **Reliability**: Zero-flicker theme switching, graceful error handling
- **Compatibility**: Works on all modern browsers without polyfills

### Integration Points
The frontend integrates with the SizeComparator backend API as defined in BACKEND_CORE_SPEC.md, implementing exact request/response contracts, error handling aligned with ERROR_MONITORING_SPEC.md taxonomy, and configuration management following CONFIG_SYSTEM_SPEC.md patterns.

## 2. Component Architecture

### 2.1 Design Pattern
The frontend uses a modular vanilla JavaScript architecture with clear separation of concerns:

```javascript
// Base Component Pattern
class Component {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
        this.options = options;
        this.state = {};
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.render();
    }
    
    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.render();
    }
    
    render() {
        // Component-specific rendering logic
    }
    
    destroy() {
        // Cleanup event listeners and resources
    }
}
```

### 2.2 Component Hierarchy

| Component | Purpose | Parent | Communication |
|-----------|---------|--------|---------------|
| App | Application root and orchestration | - | Global state manager |
| Header | Navigation and theme toggle | App | Event dispatch |
| WeightForm | Input form and validation | App | Submit events |
| ResultsDisplay | Comparison results rendering | App | State updates |
| ErrorDisplay | Error message handling | App | Error events |
| LoadingIndicator | Loading state visualization | App | State changes |
| ThemeToggle | Light/dark mode switching | Header | Theme events |

### 2.3 Communication Patterns

**Event-Driven Architecture**:
- Custom events for decoupled communication
- Event delegation for dynamic content
- Centralized event bus for cross-component messaging

```javascript
// Event Bus Implementation
class EventBus {
    constructor() {
        this.events = {};
    }
    
    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
    }
    
    emit(event, data) {
        if (this.events[event]) {
            this.events[event].forEach(callback => callback(data));
        }
    }
    
    off(event, callback) {
        if (this.events[event]) {
            this.events[event] = this.events[event].filter(cb => cb !== callback);
        }
    }
}

const eventBus = new EventBus();
```

**State Management**:
- Centralized state store for application data
- Immutable state updates
- Subscription-based reactivity

## 3. API Client Implementation

### 3.1 Type-Safe API Client

The API client implements exact TypeScript interfaces matching BACKEND_CORE_SPEC.md Pydantic models:

```typescript
// Must match BACKEND_CORE_SPEC section 4.1 exactly
interface WeightComparisonRequest {
    item1_name: string;
    item1_weight: string;
    item2_name: string;
    item2_weight: string;
    output_unit?: WeightUnit;
}

// Must match BACKEND_CORE_SPEC section 4.2 exactly
interface WeightComparisonResponse {
    item1: WeightItem;
    item2: WeightItem;
    comparison: ComparisonResult;
    visualization_prompt: string;
    metadata: ResponseMetadata;
}

// Must match BACKEND_CORE_SPEC section 5.3 exactly
interface ErrorResponse {
    error: string;
    message: string;
    details?: Record<string, any>;
    request_id: string;
    timestamp: string; // ISO 8601 format
}

interface WeightItem {
    name: string;
    original_input: string;
    weight_kg: number;
    weight_display: string;
    unit_used: WeightUnit;
    confidence: number;
}

interface ComparisonResult {
    ratio: number;
    description: string;
    visualization_suggestions: string[];
}

interface ResponseMetadata {
    request_id: string;
    processing_time_ms: number;
    ai_provider_used: string;
    cache_hit: boolean;
}
```

### 3.2 HTTP Client Configuration

```javascript
class SizeComparatorAPI {
    constructor(config = {}) {
        // Configuration from SIZECOMPARATOR_* environment variables
        this.baseURL = config.apiEndpoint || process.env.SIZECOMPARATOR_API_ENDPOINT || '/api';
        this.timeout = parseInt(config.apiTimeout || process.env.SIZECOMPARATOR_API_TIMEOUT || '30000');
        this.retryConfig = {
            maxRetries: 2,
            retryDelay: 1000,
            backoffMultiplier: 2
        };
    }
    
    async compareWeights(request) {
        const requestId = this.generateRequestId();
        
        return this.makeRequest('/compare', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Request-ID': requestId
            },
            body: JSON.stringify(request)
        });
    }
    
    async makeRequest(endpoint, options, retryCount = 0) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                ...options,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const errorBody = await response.json();
                throw new APIError(response.status, errorBody);
            }
            
            return await response.json();
            
        } catch (error) {
            clearTimeout(timeoutId);
            
            // Handle retry logic based on error type
            if (this.shouldRetry(error, retryCount)) {
                const delay = this.retryConfig.retryDelay * Math.pow(this.retryConfig.backoffMultiplier, retryCount);
                await this.delay(delay);
                return this.makeRequest(endpoint, options, retryCount + 1);
            }
            
            throw this.transformError(error);
        }
    }
    
    shouldRetry(error, retryCount) {
        if (retryCount >= this.retryConfig.maxRetries) return false;
        
        // Retry on network errors and 5xx responses
        return error.name === 'AbortError' || 
               (error instanceof APIError && error.status >= 500);
    }
    
    generateRequestId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
}
```

### 3.3 Error Response Processing

Error handling aligned with ERROR_MONITORING_SPEC.md taxonomy:

```javascript
class ErrorHandler {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.errorStrategies = {
            // Client errors (4xx) - No retry
            400: { message: 'Invalid input. Please check your values.', retry: false },
            401: { message: 'Authentication required.', retry: false },
            403: { message: 'Access denied.', retry: false },
            404: { message: 'Service not found.', retry: false },
            429: { message: 'Too many requests. Please wait a moment.', retry: false, delay: 30000 },
            
            // Server errors (5xx) - Enable retry
            500: { message: 'Server error. Please try again.', retry: true },
            502: { message: 'Service temporarily unavailable.', retry: true },
            503: { message: 'Service under maintenance.', retry: true },
            504: { message: 'Request timeout. Please try again.', retry: true },
            
            // Network errors
            'NetworkError': { message: 'Unable to connect. Check your internet connection.', retry: true },
            'TimeoutError': { message: 'Request taking too long. Please try again.', retry: true }
        };
    }
    
    handleError(error) {
        const strategy = this.getErrorStrategy(error);
        
        this.eventBus.emit('error', {
            message: strategy.message,
            details: error.details,
            requestId: error.request_id,
            retry: strategy.retry,
            retryDelay: strategy.delay
        });
        
        // Log to console for debugging
        console.error(`[${error.request_id}] ${error.message}`, error.details);
    }
    
    getErrorStrategy(error) {
        if (error instanceof APIError) {
            return this.errorStrategies[error.status] || 
                   { message: error.message, retry: error.status >= 500 };
        }
        
        return this.errorStrategies[error.name] || 
               { message: 'An unexpected error occurred.', retry: false };
    }
}
```

## 4. State Management

### 4.1 State Architecture Overview

The application uses a lightweight custom state management solution with unidirectional data flow:

```javascript
class StateManager {
    constructor() {
        this.state = {
            ui: {
                loading: false,
                error: null,
                theme: 'light'
            },
            form: {
                item1_name: '',
                item1_weight: '',
                item2_name: '',
                item2_weight: '',
                output_unit: 'kg'
            },
            results: {
                comparisons: null,
                lastUpdated: null
            },
            config: {
                apiEndpoint: this.getConfig('SIZECOMPARATOR_API_ENDPOINT', '/api'),
                apiTimeout: parseInt(this.getConfig('SIZECOMPARATOR_API_TIMEOUT', '30000')),
                environment: this.getConfig('SIZECOMPARATOR_ENVIRONMENT', 'production'),
                logLevel: this.getConfig('SIZECOMPARATOR_LOG_LEVEL', 'info'),
                cacheTtl: parseInt(this.getConfig('SIZECOMPARATOR_CACHE_TTL', '3600'))
            }
        };
        
        this.subscribers = [];
    }
    
    getConfig(key, defaultValue) {
        // In production, these would be injected during build
        return window.__ENV__?.[key] || defaultValue;
    }
    
    subscribe(callback) {
        this.subscribers.push(callback);
        return () => {
            this.subscribers = this.subscribers.filter(sub => sub !== callback);
        };
    }
    
    setState(updates) {
        this.state = this.deepMerge(this.state, updates);
        this.notify();
    }
    
    notify() {
        this.subscribers.forEach(callback => callback(this.state));
    }
}
```

### 4.2 State Structure

| State Key | Type | Persistence | Update Triggers |
|-----------|------|-------------|-----------------|
| ui.loading | boolean | None | API request lifecycle |
| ui.error | Object | None | Error responses |
| ui.theme | string | localStorage | Theme toggle |
| form.* | string | sessionStorage | User input |
| results.comparisons | Object | None | API responses |
| results.lastUpdated | Date | None | Successful comparisons |
| config.* | Various | None | Application initialization |

### 4.3 Persistence Strategy

```javascript
class PersistenceManager {
    constructor(stateManager) {
        this.stateManager = stateManager;
        this.storageKeys = {
            theme: 'sizecomparator-theme',
            formData: 'sizecomparator-form-data'
        };
        
        this.loadPersistedState();
        this.setupPersistenceListeners();
    }
    
    loadPersistedState() {
        // Load theme from localStorage
        const theme = localStorage.getItem(this.storageKeys.theme);
        if (theme) {
            this.stateManager.setState({ ui: { theme } });
        }
        
        // Load form data from sessionStorage
        const formData = sessionStorage.getItem(this.storageKeys.formData);
        if (formData) {
            try {
                const parsed = JSON.parse(formData);
                this.stateManager.setState({ form: parsed });
            } catch (e) {
                console.error('Failed to parse form data:', e);
            }
        }
    }
    
    setupPersistenceListeners() {
        this.stateManager.subscribe((state) => {
            // Persist theme changes
            localStorage.setItem(this.storageKeys.theme, state.ui.theme);
            
            // Persist form data
            sessionStorage.setItem(this.storageKeys.formData, JSON.stringify(state.form));
        });
    }
}
```

## 5. Design System & UI Patterns

### 5.1 Visual Hierarchy

**Typography Scale**:
```css
:root {
    --font-family-base: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-size-xs: 0.75rem;    /* 12px */
    --font-size-sm: 0.875rem;   /* 14px */
    --font-size-base: 1rem;     /* 16px */
    --font-size-lg: 1.125rem;   /* 18px */
    --font-size-xl: 1.5rem;     /* 24px */
    --font-size-2xl: 2rem;      /* 32px */
    
    --line-height-tight: 1.25;
    --line-height-base: 1.5;
    --line-height-relaxed: 1.75;
}
```

**Color System**:
```css
:root {
    /* Light theme colors */
    --color-primary: #3b82f6;
    --color-primary-hover: #2563eb;
    --color-secondary: #64748b;
    --color-success: #10b981;
    --color-warning: #f59e0b;
    --color-error: #ef4444;
    
    --color-bg-base: #ffffff;
    --color-bg-surface: #f8fafc;
    --color-bg-overlay: rgba(0, 0, 0, 0.5);
    
    --color-text-primary: #1e293b;
    --color-text-secondary: #64748b;
    --color-text-muted: #94a3b8;
    
    --color-border: #e2e8f0;
    --color-border-focus: var(--color-primary);
}

[data-theme="dark"] {
    --color-bg-base: #0f172a;
    --color-bg-surface: #1e293b;
    --color-text-primary: #f1f5f9;
    --color-text-secondary: #cbd5e1;
    --color-border: #334155;
}
```

**Spacing System (8px Grid)**:
```css
:root {
    --space-1: 0.25rem;  /* 4px */
    --space-2: 0.5rem;   /* 8px */
    --space-3: 0.75rem;  /* 12px */
    --space-4: 1rem;     /* 16px */
    --space-6: 1.5rem;   /* 24px */
    --space-8: 2rem;     /* 32px */
    --space-12: 3rem;    /* 48px */
    --space-16: 4rem;    /* 64px */
}
```

### 5.2 Common UI Patterns

| Pattern | Usage | Components | Interaction |
|---------|-------|------------|-------------|
| Cards | Comparison results | .comparison-card | Hover for details |
| Forms | Weight input | .form-group, .input-field | Real-time validation |
| Buttons | Actions | .btn-primary, .btn-secondary | Loading states |
| Messages | Errors/success | .alert, .toast | Auto-dismiss option |
| Loading | Async operations | .spinner, .skeleton | Accessibility labels |

**Component CSS Example**:
```css
/* Card Pattern */
.comparison-card {
    background: var(--color-bg-surface);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    padding: var(--space-6);
    transition: transform 0.2s, box-shadow 0.2s;
}

.comparison-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* Form Pattern */
.form-group {
    margin-bottom: var(--space-4);
}

.input-field {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    font-size: var(--font-size-base);
    transition: border-color 0.2s;
}

.input-field:focus {
    outline: none;
    border-color: var(--color-border-focus);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}
```

## 6. Core Feature Specifications

### 6.1 Feature Summary

| Feature | Components | Data Sources | Key Actions |
|---------|------------|--------------|-------------|
| Weight Comparison | WeightForm, ResultsDisplay | API /compare endpoint | Submit, validate, display |
| Theme Switching | ThemeToggle, ThemeManager | localStorage | Toggle, persist, apply |
| Error Handling | ErrorDisplay, ErrorHandler | API errors, validation | Display, retry, clear |
| Loading States | LoadingIndicator | State manager | Show, hide, animate |

### 6.2 API Integration Contracts

All API client implementations must match BACKEND_CORE_SPEC.md contracts exactly:

**Request Format**:
```javascript
// Weight comparison request matching BACKEND_CORE_SPEC
const request = {
    item1_name: "Elephant",
    item1_weight: "5000 kg",
    item2_name: "Car", 
    item2_weight: "3000 pounds",
    output_unit: "kg" // Optional, defaults to input unit
};
```

**Response Handling**:
```javascript
// Success response handler
function handleComparisonResponse(response) {
    // Validate response structure matches WeightComparisonResponse
    if (!response.item1 || !response.item2 || !response.comparison) {
        throw new Error('Invalid response structure');
    }
    
    // Update state with results
    stateManager.setState({
        results: {
            comparisons: response,
            lastUpdated: new Date()
        },
        ui: { loading: false }
    });
}

// Error response handler matching ErrorResponse format
function handleErrorResponse(error) {
    // Error must contain required fields from BACKEND_CORE_SPEC
    const { error: errorCode, message, details, request_id, timestamp } = error;
    
    errorHandler.handleError({
        code: errorCode,
        message: message,
        details: details,
        request_id: request_id,
        timestamp: new Date(timestamp)
    });
}
```

### 6.3 Error Handling Framework

Error handling aligned with ERROR_MONITORING_SPEC.md taxonomy:

```javascript
class ErrorManager {
    constructor() {
        this.errorCategories = {
            // Client Errors (4xx)
            CLIENT_ERROR: {
                codes: [400, 401, 403, 404, 429],
                retry: false,
                userMessage: 'Please check your input and try again.'
            },
            
            // Server Errors (5xx)
            SERVER_ERROR: {
                codes: [500, 502, 503, 504],
                retry: true,
                userMessage: 'Service temporarily unavailable. Please try again.'
            },
            
            // Integration Errors
            INTEGRATION_ERROR: {
                patterns: ['ECONNREFUSED', 'ETIMEDOUT', 'ENETUNREACH'],
                retry: true,
                userMessage: 'Connection error. Please check your network.'
            },
            
            // Business Logic Errors
            BUSINESS_LOGIC_ERROR: {
                patterns: ['INVALID_WEIGHT', 'COMPARISON_FAILED'],
                retry: false,
                userMessage: 'Unable to process comparison. Please verify your inputs.'
            }
        };
    }
    
    categorizeError(error) {
        // Categorize based on status code or error pattern
        if (error.status) {
            for (const [category, config] of Object.entries(this.errorCategories)) {
                if (config.codes?.includes(error.status)) {
                    return { category, ...config };
                }
            }
        }
        
        // Check error patterns
        const errorString = error.toString();
        for (const [category, config] of Object.entries(this.errorCategories)) {
            if (config.patterns?.some(pattern => errorString.includes(pattern))) {
                return { category, ...config };
            }
        }
        
        return {
            category: 'UNKNOWN_ERROR',
            retry: false,
            userMessage: 'An unexpected error occurred.'
        };
    }
}
```

### 6.4 User Flows

**Primary Flow: Weight Comparison**
1. User enters two items with weights
2. Form validates input in real-time
3. User submits comparison request
4. Loading state displays with spinner
5. API returns comparison results
6. Results display with visual cards
7. User can start new comparison

**Error Recovery Flow**
1. Error occurs during API call
2. Error categorized by type
3. User-friendly message displayed
4. Retry option shown if applicable
5. Form remains populated for correction
6. User retries or modifies input

### 6.5 Interactive Elements

**Form Validation**:
```javascript
const ValidationRules = {
    weight: {
        required: true,
        pattern: /^\d+\.?\d{0,2}(\s*(kg|lb|lbs|pounds?|kilograms?|g|grams?|oz|ounces?))?$/i,
        min: 0.001,
        max: 1000000,
        sanitize: (value) => value.trim().toLowerCase(),
        validate: (value) => {
            const num = parseFloat(value);
            if (isNaN(num)) return 'Please enter a valid number';
            if (num < 0.001) return 'Weight must be at least 0.001';
            if (num > 1000000) return 'Weight cannot exceed 1,000,000';
            return null;
        }
    },
    name: {
        required: true,
        maxLength: 100,
        sanitize: (value) => value.trim(),
        validate: (value) => {
            if (!value) return 'Please enter an item name';
            if (value.length > 100) return 'Name must be 100 characters or less';
            return null;
        }
    }
};
```

**Loading States**:
```javascript
class LoadingManager {
    showLoading() {
        // Disable form
        document.querySelectorAll('input, button').forEach(el => {
            el.disabled = true;
        });
        
        // Show spinner with accessibility
        const spinner = document.getElementById('loading-spinner');
        spinner.classList.add('active');
        spinner.setAttribute('aria-hidden', 'false');
        
        // Update button text
        const submitBtn = document.getElementById('submit-btn');
        submitBtn.textContent = 'Comparing...';
        submitBtn.setAttribute('aria-busy', 'true');
    }
    
    hideLoading() {
        // Re-enable form
        document.querySelectorAll('input, button').forEach(el => {
            el.disabled = false;
        });
        
        // Hide spinner
        const spinner = document.getElementById('loading-spinner');
        spinner.classList.remove('active');
        spinner.setAttribute('aria-hidden', 'true');
        
        // Reset button
        const submitBtn = document.getElementById('submit-btn');
        submitBtn.textContent = 'Compare';
        submitBtn.removeAttribute('aria-busy');
    }
}
```

## 7. Responsive Design & Accessibility

### 7.1 Responsive Breakpoints

| Breakpoint | Width | Layout Changes | Priority Content |
|------------|-------|----------------|------------------|
| Mobile | 0-767px | Single column, stacked inputs | Core form, results |
| Tablet | 768-1023px | 2-column results grid | Full form, enhanced results |
| Desktop | 1024-1439px | Side margins, optimal width | All features visible |
| Large | 1440px+ | Centered container, max-width | Enhanced spacing |

**Responsive CSS Implementation**:
```css
/* Mobile First Base Styles */
.container {
    width: 100%;
    padding: var(--space-4);
}

.results-grid {
    display: grid;
    gap: var(--space-4);
    grid-template-columns: 1fr;
}

/* Tablet and up */
@media (min-width: 768px) {
    .container {
        max-width: 768px;
        margin: 0 auto;
        padding: var(--space-8);
    }
    
    .results-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: var(--space-6);
    }
    
    .form-row {
        display: flex;
        gap: var(--space-4);
    }
    
    .form-row > * {
        flex: 1;
    }
}

/* Desktop */
@media (min-width: 1024px) {
    .container {
        max-width: 1024px;
    }
    
    .header {
        padding: var(--space-6) 0;
    }
}

/* Large screens */
@media (min-width: 1440px) {
    .container {
        max-width: 1200px;
    }
}
```

### 7.2 Accessibility Requirements

**WCAG 2.1 AA Compliance**:

```javascript
class AccessibilityManager {
    constructor() {
        this.announcer = this.createAnnouncer();
        this.setupKeyboardNavigation();
        this.ensureColorContrast();
    }
    
    createAnnouncer() {
        const announcer = document.createElement('div');
        announcer.setAttribute('role', 'status');
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        document.body.appendChild(announcer);
        return announcer;
    }
    
    announce(message) {
        this.announcer.textContent = message;
        // Clear after announcement
        setTimeout(() => {
            this.announcer.textContent = '';
        }, 1000);
    }
    
    setupKeyboardNavigation() {
        // Skip to main content link
        const skipLink = document.querySelector('.skip-link');
        skipLink.addEventListener('click', (e) => {
            e.preventDefault();
            const main = document.getElementById('main-content');
            main.tabIndex = -1;
            main.focus();
        });
        
        // Escape key to close modals/dismiss errors
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.dismissActiveModal();
            }
        });
        
        // Tab trap for modals
        this.setupModalTabTrap();
    }
    
    ensureColorContrast() {
        // Verify minimum contrast ratios
        const contrastRatios = {
            normalText: 4.5,  // WCAG AA for normal text
            largeText: 3,     // WCAG AA for large text
            ui: 3             // WCAG AA for UI components
        };
        
        // Add high contrast mode support
        if (window.matchMedia('(prefers-contrast: high)').matches) {
            document.documentElement.classList.add('high-contrast');
        }
    }
}
```

**Focus Management**:
```css
/* Focus visible for keyboard navigation */
:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
}

/* Remove outline for mouse users */
:focus:not(:focus-visible) {
    outline: none;
}

/* Skip link for screen readers */
.skip-link {
    position: absolute;
    left: -9999px;
    z-index: 999;
}

.skip-link:focus {
    left: 50%;
    transform: translateX(-50%);
    top: var(--space-4);
    padding: var(--space-3) var(--space-6);
    background: var(--color-primary);
    color: white;
    text-decoration: none;
    border-radius: 0.375rem;
}
```

**ARIA Implementation**:
```html
<!-- Form with proper ARIA labels -->
<form role="form" aria-labelledby="form-title">
    <h2 id="form-title">Compare Weights</h2>
    
    <div class="form-group">
        <label for="item1-name">First Item Name</label>
        <input 
            type="text" 
            id="item1-name" 
            name="item1_name"
            required
            aria-required="true"
            aria-describedby="item1-name-error"
        >
        <span id="item1-name-error" class="error-message" role="alert"></span>
    </div>
    
    <!-- Results with live region -->
    <section aria-live="polite" aria-label="Comparison Results">
        <h2>Results</h2>
        <div id="results-container"></div>
    </section>
</form>
```

## 8. Performance & Optimization

### 8.1 Performance Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| First Paint | < 100ms | Inline critical CSS |
| Time to Interactive | < 500ms | Defer non-critical JS |
| Largest Contentful Paint | < 1s | Optimize images, fonts |
| Total Bundle Size | < 50KB | No frameworks, minification |
| API Response (perceived) | < 2s | Optimistic UI updates |

### 8.2 Optimization Strategies

**Critical CSS Inlining**:
```html
<style>
/* Critical above-the-fold styles */
:root{--color-bg-base:#fff;--color-text-primary:#1e293b}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
.container{max-width:1024px;margin:0 auto;padding:1rem}
/* Theme flicker prevention */
[data-theme="dark"]{--color-bg-base:#0f172a;--color-text-primary:#f1f5f9}
</style>
```

**JavaScript Loading Strategy**:
```html
<!-- Inline theme script to prevent flicker -->
<script>
(function(){
    const theme = localStorage.getItem('sizecomparator-theme') || 
                  (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
})();
</script>

<!-- Deferred application scripts -->
<script src="/js/app.js" defer></script>
```

**Resource Optimization**:
```javascript
// Lazy load non-critical resources
class ResourceLoader {
    static loadCSS(href) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.media = 'print';
        link.onload = function() { this.media = 'all'; };
        document.head.appendChild(link);
    }
    
    static preconnect(origin) {
        const link = document.createElement('link');
        link.rel = 'preconnect';
        link.href = origin;
        document.head.appendChild(link);
    }
}

// Preconnect to API
ResourceLoader.preconnect(config.apiEndpoint);
```

**Memory Management**:
```javascript
class ComponentLifecycle {
    constructor() {
        this.components = new WeakMap();
        this.cleanupTasks = [];
    }
    
    register(component, cleanup) {
        this.components.set(component, cleanup);
    }
    
    destroy(component) {
        const cleanup = this.components.get(component);
        if (cleanup) {
            cleanup();
            this.components.delete(component);
        }
    }
    
    addCleanupTask(task) {
        this.cleanupTasks.push(task);
    }
    
    cleanup() {
        this.cleanupTasks.forEach(task => task());
        this.cleanupTasks = [];
    }
}
```

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- HTML structure and semantic markup
- CSS design system and theme variables
- Core JavaScript architecture
- Theme manager with persistence

### Phase 2: Core Features (Week 3-4)
- Weight comparison form
- API client with error handling
- Results display component
- Loading and error states

### Phase 3: Enhanced Features (Week 5-6)
- Advanced form validation
- Retry mechanisms
- Accessibility features
- Performance optimizations

### Phase 4: Polish & Testing (Week 7-8)
- Cross-browser testing
- Performance audit
- Accessibility audit
- Documentation

## Technical Considerations

### Browser Support
- Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- No polyfills required
- Progressive enhancement for older browsers
- Feature detection for optional enhancements

### File Structure
```
frontend/
├── index.html          # Single HTML file
├── css/
│   ├── critical.css    # Inlined critical styles
│   └── main.css        # Full stylesheet
├── js/
│   ├── api.js          # API client module
│   ├── theme.js        # Theme manager
│   ├── validator.js    # Form validation
│   ├── state.js        # State management
│   ├── components.js   # UI components
│   └── app.js          # Main application
└── assets/
    ├── icons/          # SVG icons
    └── fonts/          # Web fonts (optional)
```

### Environment Configuration
Following CONFIG_SYSTEM_SPEC.md patterns:
```javascript
// Configuration loaded from environment
const config = {
    apiEndpoint: '${SIZECOMPARATOR_API_ENDPOINT:-http://localhost:8000}',
    apiTimeout: ${SIZECOMPARATOR_API_TIMEOUT:-30000},
    environment: '${SIZECOMPARATOR_ENVIRONMENT:-production}',
    logLevel: '${SIZECOMPARATOR_LOG_LEVEL:-info}',
    cacheTtl: ${SIZECOMPARATOR_CACHE_TTL:-3600}
};
```

## Key Deliverables

1. **Semantic HTML structure** with ARIA attributes and accessibility features
2. **Modern CSS implementation** using custom properties and grid layout
3. **Vanilla JavaScript modules** with clean separation of concerns
4. **Zero-flicker theme system** with localStorage persistence
5. **Type-safe API client** matching BACKEND_CORE_SPEC contracts exactly
6. **Comprehensive error handling** aligned with ERROR_MONITORING_SPEC
7. **Responsive design** working across all device sizes
8. **Performance optimizations** meeting all target metrics
9. **Accessibility compliance** with WCAG 2.1 AA standards
10. **Complete documentation** for maintenance and deployment