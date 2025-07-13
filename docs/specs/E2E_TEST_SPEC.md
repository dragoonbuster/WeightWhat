# SizeComparator End-to-End Testing Specification

## Overview

This document specifies comprehensive end-to-end (E2E) testing strategies for SizeComparator, validating complete user workflows from frontend form submission to AI comparison results. The specification covers browser automation, performance testing, error scenario validation, and cross-browser compatibility testing to ensure production-ready system reliability.

## Key Integration Requirements

This specification validates the complete system integration:
- **FRONTEND_SPEC**: Theme system, responsive design, API client functionality
- **API_ENDPOINTS_SPEC**: Complete request/response cycles with error handling
- **BACKEND_CORE_SPEC**: Pydantic model validation through real API calls
- **AI_PROVIDER_SPEC**: Circuit breaker behavior and provider failover scenarios
- **ERROR_MONITORING_SPEC**: Error propagation from backend to frontend display
- **DEPLOYMENT_OPS_SPEC**: Health endpoint monitoring during E2E workflows

## 1. User Journey Testing Framework (1 page)

### 1.1 Core User Journey Scenarios

The E2E testing framework validates complete user workflows from initial page load through comparison result display:

#### 1.1.1 Happy Path Weight Comparison Journey

```javascript
// Primary user journey: Successful weight comparison
describe('Weight Comparison Happy Path', () => {
  it('should complete full comparison workflow', async () => {
    // Step 1: Navigate to application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Step 2: Verify page loads with correct theme
    const themeAttribute = await page.getAttribute('html', 'data-theme');
    expect(themeAttribute).toBe('light'); // Default theme
    
    // Step 3: Fill weight comparison form
    await page.fill('#item1-name', 'African Elephant');
    await page.fill('#item1-weight', '5000 kg');
    await page.fill('#item2-name', 'Honda Civic');
    await page.fill('#item2-weight', '1300 kg');
    
    // Step 4: Submit comparison request
    await page.click('#compare-btn');
    
    // Step 5: Verify loading state appears
    await page.waitForSelector('#loading-spinner', { state: 'visible' });
    
    // Step 6: Wait for results to load
    await page.waitForSelector('.comparison-result', { 
      state: 'visible', 
      timeout: 10000 
    });
    
    // Step 7: Validate result structure
    const resultText = await page.textContent('.comparison-explanation');
    expect(resultText).toContain('elephant');
    expect(resultText).toContain('car');
    
    // Step 8: Verify ratio calculation display
    const ratioDisplay = await page.textContent('.weight-ratio');
    expect(ratioDisplay).toMatch(/\d+\.\d+/); // Numeric ratio format
    
    // Step 9: Check visualization prompt generation
    const visualPrompt = await page.textContent('.visualization-prompt');
    expect(visualPrompt.length).toBeGreaterThan(50);
  });
});
```

#### 1.1.2 Multi-Step User Journey Validation

```javascript
// Complex user journey with multiple interactions
describe('Complete User Interaction Flow', () => {
  it('should handle multiple comparisons with theme switching', async () => {
    await page.goto('http://localhost:3000');
    
    // First comparison
    await performWeightComparison({
      item1: { name: 'Blue Whale', weight: '150 tons' },
      item2: { name: 'School Bus', weight: '8 tons' }
    });
    
    // Switch to dark theme
    await page.click('#theme-toggle');
    await page.waitForTimeout(300); // Theme transition
    
    // Verify theme change persisted
    const darkTheme = await page.getAttribute('html', 'data-theme');
    expect(darkTheme).toBe('dark');
    
    // Second comparison in dark theme
    await performWeightComparison({
      item1: { name: 'Butterfly', weight: '0.5 grams' },
      item2: { name: 'Paperclip', weight: '1 gram' }
    });
    
    // Verify results history (if implemented)
    const resultCards = await page.$$('.comparison-card');
    expect(resultCards.length).toBe(2);
    
    // Refresh page and verify theme persistence
    await page.reload();
    const persistedTheme = await page.getAttribute('html', 'data-theme');
    expect(persistedTheme).toBe('dark');
  });
});

async function performWeightComparison(comparison) {
  await page.fill('#item1-name', comparison.item1.name);
  await page.fill('#item1-weight', comparison.item1.weight);
  await page.fill('#item2-name', comparison.item2.name);
  await page.fill('#item2-weight', comparison.item2.weight);
  
  await page.click('#compare-btn');
  await page.waitForSelector('.comparison-result', { 
    state: 'visible', 
    timeout: 15000 
  });
}
```

### 1.2 User Journey Test Data Matrix

| Scenario | Item 1 | Item 2 | Expected Behavior | Validation Points |
|----------|--------|--------|------------------|-------------------|
| Large vs Small | Blue Whale (150t) | Car (1.5t) | Clear ratio display | Ratio > 50, visualization generated |
| Similar weights | Basketball (600g) | Soccer ball (450g) | Close comparison | Ratio 1-2, detailed explanation |
| Tiny objects | Grain of rice (25mg) | Ant (2mg) | Micro comparison | Scientific notation handling |
| Mixed units | Elephant (5000kg) | Person (150 pounds) | Unit conversion | Normalized display units |
| Edge cases | Feather (0.1g) | Mountain (1000 tons) | Extreme ratio | Error boundaries tested |

## 2. Browser Automation with Playwright (1 page)

### 2.1 Playwright Test Configuration

```javascript
// playwright.config.js
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // Sequential for API consistency
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : 2,
  reporter: [
    ['html'],
    ['junit', { outputFile: 'test-results/e2e-results.xml' }],
    ['allure-playwright']
  ],
  
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: process.env.CI ? true : false,
  },

  projects: [
    // Desktop browsers
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    
    // Mobile browsers
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
    
    // Tablet testing
    {
      name: 'iPad',
      use: { ...devices['iPad Pro'] },
    }
  ],

  webServer: {
    command: 'npm run start:e2e',
    url: 'http://localhost:3000/health',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
```

### 2.2 Advanced Browser Automation Patterns

```javascript
// e2e/utils/browser-helpers.js
export class BrowserTestHelpers {
  constructor(page) {
    this.page = page;
  }

  // Wait for AI response with intelligent timeout
  async waitForAIResponse(timeout = 15000) {
    // Wait for loading state to start
    await this.page.waitForSelector('#loading-spinner', { 
      state: 'visible', 
      timeout: 2000 
    });
    
    // Wait for loading to complete
    await this.page.waitForSelector('#loading-spinner', { 
      state: 'hidden', 
      timeout 
    });
    
    // Verify result is present
    await this.page.waitForSelector('.comparison-result', { 
      state: 'visible' 
    });
  }

  // Verify form validation states
  async verifyFormValidation(fieldSelector, expectedState) {
    const field = this.page.locator(fieldSelector);
    const validationState = await field.getAttribute('aria-invalid');
    
    switch (expectedState) {
      case 'invalid':
        expect(validationState).toBe('true');
        break;
      case 'valid':
        expect(validationState).toBe('false');
        break;
    }
  }

  // Check responsive design breakpoints
  async testResponsiveBreakpoint(width, height) {
    await this.page.setViewportSize({ width, height });
    await this.page.waitForTimeout(300); // CSS transition
    
    // Verify layout adjustments
    const container = this.page.locator('.container');
    const containerWidth = await container.evaluate(el => 
      window.getComputedStyle(el).width
    );
    
    return { width, height, containerWidth };
  }

  // Theme switching with validation
  async switchTheme(targetTheme) {
    const currentTheme = await this.page.getAttribute('html', 'data-theme');
    
    if (currentTheme !== targetTheme) {
      await this.page.click('#theme-toggle');
      await this.page.waitForTimeout(200); // Theme transition
      
      const newTheme = await this.page.getAttribute('html', 'data-theme');
      expect(newTheme).toBe(targetTheme);
    }
    
    return targetTheme;
  }

  // Network condition simulation
  async simulateNetworkConditions(condition) {
    const conditions = {
      slow3g: { downloadThroughput: 500 * 1024, uploadThroughput: 500 * 1024, latency: 400 },
      fast3g: { downloadThroughput: 1.6 * 1024 * 1024, uploadThroughput: 750 * 1024, latency: 150 },
      offline: { offline: true }
    };
    
    if (conditions[condition]) {
      await this.page.context().setExtraHTTPHeaders({
        'X-Test-Network-Condition': condition
      });
    }
  }
}
```

### 2.3 Page Object Model Implementation

```javascript
// e2e/pages/comparison-page.js
export class ComparisonPage {
  constructor(page) {
    this.page = page;
    this.helpers = new BrowserTestHelpers(page);
    
    // Selectors
    this.selectors = {
      item1Name: '#item1-name',
      item1Weight: '#item1-weight',
      item2Name: '#item2-name', 
      item2Weight: '#item2-weight',
      compareButton: '#compare-btn',
      loadingSpinner: '#loading-spinner',
      results: '.comparison-result',
      errorDisplay: '#error-display',
      themeToggle: '#theme-toggle'
    };
  }

  async fillComparisonForm(data) {
    await this.page.fill(this.selectors.item1Name, data.item1.name);
    await this.page.fill(this.selectors.item1Weight, data.item1.weight);
    await this.page.fill(this.selectors.item2Name, data.item2.name);
    await this.page.fill(this.selectors.item2Weight, data.item2.weight);
  }

  async submitComparison() {
    await this.page.click(this.selectors.compareButton);
  }

  async waitForResults() {
    await this.helpers.waitForAIResponse();
  }

  async getComparisonResults() {
    const resultText = await this.page.textContent(this.selectors.results);
    const ratio = await this.page.textContent('.weight-ratio');
    const visualization = await this.page.textContent('.visualization-prompt');
    
    return { resultText, ratio, visualization };
  }

  async getErrorMessage() {
    return await this.page.textContent(this.selectors.errorDisplay);
  }
}
```

## 3. Performance Testing & Load Simulation (1 page)

### 3.1 Frontend Performance Metrics

```javascript
// e2e/performance/frontend-metrics.spec.js
describe('Frontend Performance Metrics', () => {
  it('should meet Core Web Vitals thresholds', async () => {
    await page.goto('/');
    
    // Measure First Contentful Paint (FCP)
    const fcp = await page.evaluate(() => {
      return new Promise((resolve) => {
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.name === 'first-contentful-paint') {
              resolve(entry.startTime);
            }
          }
        }).observe({ entryTypes: ['paint'] });
      });
    });
    
    expect(fcp).toBeLessThan(1800); // 1.8s threshold
    
    // Measure Largest Contentful Paint (LCP)
    const lcp = await page.evaluate(() => {
      return new Promise((resolve) => {
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const lastEntry = entries[entries.length - 1];
          resolve(lastEntry.startTime);
        }).observe({ entryTypes: ['largest-contentful-paint'] });
        
        setTimeout(() => resolve(0), 5000); // Fallback
      });
    });
    
    expect(lcp).toBeLessThan(2500); // 2.5s threshold
    
    // Measure Cumulative Layout Shift (CLS)
    const cls = await page.evaluate(() => {
      return new Promise((resolve) => {
        let cumulativeScore = 0;
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) {
              cumulativeScore += entry.value;
            }
          }
          resolve(cumulativeScore);
        }).observe({ entryTypes: ['layout-shift'] });
        
        setTimeout(() => resolve(cumulativeScore), 3000);
      });
    });
    
    expect(cls).toBeLessThan(0.1); // 0.1 threshold
  });

  it('should handle form submission performance', async () => {
    await page.goto('/');
    
    const performanceData = await page.evaluate(async () => {
      const startTime = performance.now();
      
      // Fill form
      document.querySelector('#item1-name').value = 'Test Item 1';
      document.querySelector('#item1-weight').value = '100 kg';
      document.querySelector('#item2-name').value = 'Test Item 2';
      document.querySelector('#item2-weight').value = '50 kg';
      
      // Submit form
      document.querySelector('#compare-btn').click();
      
      // Wait for loading spinner
      await new Promise(resolve => {
        const observer = new MutationObserver(() => {
          if (document.querySelector('#loading-spinner').style.display !== 'none') {
            observer.disconnect();
            resolve();
          }
        });
        observer.observe(document.body, { childList: true, subtree: true });
      });
      
      return performance.now() - startTime;
    });
    
    expect(performanceData).toBeLessThan(500); // 500ms for form processing
  });
});
```

### 3.2 API Response Time Validation

```javascript
// e2e/performance/api-performance.spec.js
describe('API Performance Testing', () => {
  it('should meet response time SLA requirements', async () => {
    const responseMetrics = [];
    
    // Test multiple comparison requests
    for (let i = 0; i < 10; i++) {
      const startTime = Date.now();
      
      await page.goto('/');
      await page.fill('#item1-name', `Item ${i}A`);
      await page.fill('#item1-weight', `${100 + i} kg`);
      await page.fill('#item2-name', `Item ${i}B`);
      await page.fill('#item2-weight', `${50 + i} kg`);
      
      await page.click('#compare-btn');
      await page.waitForSelector('.comparison-result', { timeout: 10000 });
      
      const responseTime = Date.now() - startTime;
      responseMetrics.push(responseTime);
    }
    
    // Calculate performance statistics
    const avgResponseTime = responseMetrics.reduce((a, b) => a + b, 0) / responseMetrics.length;
    const p95ResponseTime = responseMetrics.sort((a, b) => a - b)[Math.floor(0.95 * responseMetrics.length)];
    const maxResponseTime = Math.max(...responseMetrics);
    
    // Validate SLA requirements
    expect(avgResponseTime).toBeLessThan(3000); // 3s average
    expect(p95ResponseTime).toBeLessThan(5000); // 5s P95
    expect(maxResponseTime).toBeLessThan(10000); // 10s max
    
    console.log(`Performance Metrics:
      Average: ${avgResponseTime}ms
      P95: ${p95ResponseTime}ms
      Max: ${maxResponseTime}ms`);
  });

  it('should handle concurrent user load simulation', async () => {
    const concurrentUsers = 5;
    const userSessions = [];
    
    for (let i = 0; i < concurrentUsers; i++) {
      userSessions.push(simulateUserSession(i));
    }
    
    const results = await Promise.all(userSessions);
    
    // Verify all sessions completed successfully
    const successfulSessions = results.filter(result => result.success);
    const successRate = successfulSessions.length / results.length;
    
    expect(successRate).toBeGreaterThan(0.9); // 90% success rate
    
    // Verify response times under load
    const responseTimes = results.map(r => r.responseTime);
    const avgUnderLoad = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
    
    expect(avgUnderLoad).toBeLessThan(6000); // 6s average under load
  });
});

async function simulateUserSession(sessionId) {
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    const startTime = Date.now();
    
    await page.goto('/');
    await page.fill('#item1-name', `Session ${sessionId} Item A`);
    await page.fill('#item1-weight', `${sessionId * 10 + 100} kg`);
    await page.fill('#item2-name', `Session ${sessionId} Item B`);
    await page.fill('#item2-weight', `${sessionId * 5 + 50} kg`);
    
    await page.click('#compare-btn');
    await page.waitForSelector('.comparison-result', { timeout: 15000 });
    
    const responseTime = Date.now() - startTime;
    
    return { success: true, responseTime, sessionId };
  } catch (error) {
    return { success: false, error: error.message, sessionId };
  } finally {
    await context.close();
  }
}
```

## 4. Error Scenario Testing (1.5 pages)

### 4.1 AI Provider Failure Scenarios

```javascript
// e2e/error-scenarios/ai-provider-failures.spec.js
describe('AI Provider Failure Handling', () => {
  beforeEach(async () => {
    // Setup test to intercept API calls
    await page.route('/api/compare', route => {
      // Default: pass through to real API
      route.continue();
    });
  });

  it('should handle AI provider timeout gracefully', async () => {
    // Intercept API call and simulate timeout
    await page.route('/api/compare', async route => {
      await new Promise(resolve => setTimeout(resolve, 35000)); // Simulate timeout
      route.fulfill({
        status: 504,
        contentType: 'application/json',
        body: JSON.stringify({
          error_code: 'GATEWAY_TIMEOUT',
          error_category: 'INTEGRATION_ERROR',
          message: 'AI provider request timed out',
          request_id: 'test-request-123',
          timestamp: new Date().toISOString(),
          severity: 'CRITICAL'
        })
      });
    });

    await page.goto('/');
    await page.fill('#item1-name', 'Elephant');
    await page.fill('#item1-weight', '5000 kg');
    await page.fill('#item2-name', 'Car');
    await page.fill('#item2-weight', '1500 kg');
    
    await page.click('#compare-btn');
    
    // Verify loading state appears
    await page.waitForSelector('#loading-spinner', { state: 'visible' });
    
    // Wait for error to be displayed
    await page.waitForSelector('#error-display', { 
      state: 'visible', 
      timeout: 40000 
    });
    
    // Verify error message content
    const errorMessage = await page.textContent('#error-display');
    expect(errorMessage).toContain('timed out');
    expect(errorMessage).toContain('try again');
    
    // Verify loading spinner is hidden
    await page.waitForSelector('#loading-spinner', { state: 'hidden' });
    
    // Verify retry functionality
    await page.click('.retry-button');
    await page.waitForSelector('#loading-spinner', { state: 'visible' });
  });

  it('should handle AI provider circuit breaker open state', async () => {
    // Simulate circuit breaker open response
    await page.route('/api/compare', route => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          error_code: 'CIRCUIT_BREAKER_OPEN',
          error_category: 'INTEGRATION_ERROR',
          message: 'AI provider is temporarily unavailable due to repeated failures',
          request_id: 'test-request-456',
          timestamp: new Date().toISOString(),
          severity: 'CRITICAL',
          remediation_hint: 'Service will automatically retry in a few minutes'
        })
      });
    });

    await page.goto('/');
    
    // Fill and submit form
    const comparisonPage = new ComparisonPage(page);
    await comparisonPage.fillComparisonForm({
      item1: { name: 'Lion', weight: '200 kg' },
      item2: { name: 'Tiger', weight: '220 kg' }
    });
    
    await comparisonPage.submitComparison();
    
    // Verify circuit breaker error handling
    await page.waitForSelector('#error-display', { state: 'visible' });
    const errorMessage = await comparisonPage.getErrorMessage();
    
    expect(errorMessage).toContain('temporarily unavailable');
    expect(errorMessage).toContain('automatically retry');
    
    // Verify form is disabled during circuit breaker
    const compareButton = page.locator('#compare-btn');
    const isDisabled = await compareButton.isDisabled();
    expect(isDisabled).toBe(true);
  });

  it('should handle AI provider rate limiting', async () => {
    // Simulate rate limiting response
    await page.route('/api/compare', route => {
      route.fulfill({
        status: 429,
        contentType: 'application/json',
        headers: {
          'Retry-After': '30'
        },
        body: JSON.stringify({
          error_code: 'RATE_LIMIT_EXCEEDED',
          error_category: 'CLIENT_ERROR',
          message: 'Too many requests. Please wait 30 seconds before trying again.',
          request_id: 'test-request-789',
          timestamp: new Date().toISOString(),
          severity: 'WARNING'
        })
      });
    });

    await page.goto('/');
    
    // Submit multiple requests rapidly
    for (let i = 0; i < 3; i++) {
      await page.fill('#item1-name', `Item ${i}A`);
      await page.fill('#item1-weight', '100 kg');
      await page.fill('#item2-name', `Item ${i}B`);
      await page.fill('#item2-weight', '50 kg');
      await page.click('#compare-btn');
      
      if (i < 2) {
        await page.waitForSelector('#loading-spinner', { state: 'hidden' });
      }
    }
    
    // Verify rate limiting error display
    await page.waitForSelector('#error-display', { state: 'visible' });
    const errorMessage = await page.textContent('#error-display');
    expect(errorMessage).toContain('Too many requests');
    expect(errorMessage).toContain('30 seconds');
    
    // Verify countdown timer (if implemented)
    const countdownTimer = page.locator('.retry-countdown');
    if (await countdownTimer.isVisible()) {
      const initialTime = await countdownTimer.textContent();
      expect(initialTime).toMatch(/\d+/);
    }
  });
});
```

### 4.2 Network Error Scenarios

```javascript
// e2e/error-scenarios/network-errors.spec.js
describe('Network Error Handling', () => {
  it('should handle complete network failure', async () => {
    await page.goto('/');
    
    // Simulate network offline
    await page.context().setOffline(true);
    
    // Fill and submit form
    await page.fill('#item1-name', 'Whale');
    await page.fill('#item1-weight', '80 tons');
    await page.fill('#item2-name', 'Elephant');
    await page.fill('#item2-weight', '5 tons');
    
    await page.click('#compare-btn');
    
    // Verify offline error handling
    await page.waitForSelector('#error-display', { 
      state: 'visible', 
      timeout: 10000 
    });
    
    const errorMessage = await page.textContent('#error-display');
    expect(errorMessage).toContain('network');
    expect(errorMessage).toContain('internet connection');
    
    // Restore network and verify retry works
    await page.context().setOffline(false);
    await page.click('.retry-button');
    
    // Should eventually succeed
    await page.waitForSelector('.comparison-result', { 
      state: 'visible', 
      timeout: 15000 
    });
  });

  it('should handle intermittent network issues', async () => {
    await page.goto('/');
    
    let requestCount = 0;
    await page.route('/api/compare', route => {
      requestCount++;
      
      if (requestCount <= 2) {
        // First two requests fail
        route.abort('failed');
      } else {
        // Third request succeeds
        route.continue();
      }
    });
    
    // Fill and submit form
    await page.fill('#item1-name', 'Mountain');
    await page.fill('#item1-weight', '1000000 tons');
    await page.fill('#item2-name', 'Pebble');
    await page.fill('#item2-weight', '10 grams');
    
    await page.click('#compare-btn');
    
    // Should show error first
    await page.waitForSelector('#error-display', { state: 'visible' });
    
    // Auto-retry should eventually succeed (if implemented)
    // Or manual retry should work
    const retryButton = page.locator('.retry-button');
    if (await retryButton.isVisible()) {
      await retryButton.click();
      await page.waitForTimeout(1000);
      await retryButton.click(); // Second retry
    }
    
    // Should eventually show results
    await page.waitForSelector('.comparison-result', { 
      state: 'visible', 
      timeout: 20000 
    });
  });
});
```

### 4.3 Frontend Validation Error Scenarios

```javascript
// e2e/error-scenarios/validation-errors.spec.js
describe('Form Validation Error Handling', () => {
  beforeEach(async () => {
    await page.goto('/');
  });

  it('should validate required fields', async () => {
    // Try to submit with empty fields
    await page.click('#compare-btn');
    
    // Verify validation errors
    const nameField1 = page.locator('#item1-name');
    const weightField1 = page.locator('#item1-weight');
    
    expect(await nameField1.getAttribute('aria-invalid')).toBe('true');
    expect(await weightField1.getAttribute('aria-invalid')).toBe('true');
    
    // Check for validation messages
    const validationMessages = page.locator('.validation-error');
    expect(await validationMessages.count()).toBeGreaterThan(0);
  });

  it('should validate weight format', async () => {
    await page.fill('#item1-name', 'Test Item');
    await page.fill('#item1-weight', 'invalid weight'); // Invalid format
    await page.fill('#item2-name', 'Test Item 2');
    await page.fill('#item2-weight', '100 kg');
    
    await page.click('#compare-btn');
    
    // Should show weight format error
    const weightField = page.locator('#item1-weight');
    expect(await weightField.getAttribute('aria-invalid')).toBe('true');
    
    const errorMessage = await page.textContent('.field-error[for="item1-weight"]');
    expect(errorMessage).toContain('weight format');
  });

  it('should validate character limits', async () => {
    const longName = 'A'.repeat(101); // Exceeds 100 char limit
    
    await page.fill('#item1-name', longName);
    await page.fill('#item1-weight', '100 kg');
    await page.fill('#item2-name', 'Normal Name');
    await page.fill('#item2-weight', '50 kg');
    
    await page.blur('#item1-name'); // Trigger validation
    
    // Should show character limit error
    const nameField = page.locator('#item1-name');
    expect(await nameField.getAttribute('aria-invalid')).toBe('true');
    
    const errorMessage = await page.textContent('.field-error[for="item1-name"]');
    expect(errorMessage).toContain('100 characters');
  });
});
```

## 5. Cross-Browser Compatibility & Mobile Testing (1 page)

### 5.1 Cross-Browser Feature Testing

```javascript
// e2e/cross-browser/compatibility.spec.js
describe('Cross-Browser Compatibility', () => {
  const browsers = ['chromium', 'firefox', 'webkit'];
  
  browsers.forEach(browserName => {
    describe(`${browserName} compatibility`, () => {
      it('should handle theme switching correctly', async () => {
        // Test theme switching across browsers
        await page.goto('/');
        
        // Verify default theme
        let theme = await page.getAttribute('html', 'data-theme');
        expect(theme).toBe('light');
        
        // Switch to dark theme
        await page.click('#theme-toggle');
        await page.waitForTimeout(300);
        
        theme = await page.getAttribute('html', 'data-theme');
        expect(theme).toBe('dark');
        
        // Verify theme persistence after reload
        await page.reload();
        await page.waitForLoadState('networkidle');
        
        theme = await page.getAttribute('html', 'data-theme');
        expect(theme).toBe('dark');
      });

      it('should handle CSS animations and transitions', async () => {
        await page.goto('/');
        
        // Test loading spinner animation
        await page.fill('#item1-name', 'Test');
        await page.fill('#item1-weight', '100 kg');
        await page.fill('#item2-name', 'Test 2');
        await page.fill('#item2-weight', '50 kg');
        
        await page.click('#compare-btn');
        
        // Verify spinner is visible and animated
        const spinner = page.locator('#loading-spinner');
        await expect(spinner).toBeVisible();
        
        // Check animation properties (browser-specific)
        const animationName = await spinner.evaluate(el => 
          window.getComputedStyle(el).animationName
        );
        expect(animationName).not.toBe('none');
      });

      it('should handle form validation styling', async () => {
        await page.goto('/');
        
        // Trigger validation error
        await page.click('#compare-btn');
        
        // Check validation styling
        const invalidField = page.locator('#item1-name[aria-invalid="true"]');
        await expect(invalidField).toBeVisible();
        
        // Verify browser-specific validation styles
        const borderColor = await invalidField.evaluate(el =>
          window.getComputedStyle(el).borderColor
        );
        
        // Should have error styling (red-ish color)
        expect(borderColor).toMatch(/rgb\(.*,.*,.*\)/);
      });
    });
  });
});
```

### 5.2 Mobile Responsiveness Testing

```javascript
// e2e/mobile/responsive.spec.js
describe('Mobile Responsiveness', () => {
  const devices = [
    { name: 'iPhone 12', width: 390, height: 844 },
    { name: 'Pixel 5', width: 393, height: 851 },
    { name: 'iPad', width: 768, height: 1024 },
    { name: 'iPad Pro', width: 1024, height: 1366 }
  ];

  devices.forEach(device => {
    describe(`${device.name} responsiveness`, () => {
      beforeEach(async () => {
        await page.setViewportSize({ 
          width: device.width, 
          height: device.height 
        });
        await page.goto('/');
      });

      it('should display form elements appropriately', async () => {
        // Check form layout on mobile
        const form = page.locator('form');
        const formWidth = await form.evaluate(el => el.offsetWidth);
        
        // Form should not exceed viewport width
        expect(formWidth).toBeLessThanOrEqual(device.width);
        
        // Check input field sizes
        const inputs = page.locator('input[type="text"], input[type="number"]');
        const inputCount = await inputs.count();
        
        for (let i = 0; i < inputCount; i++) {
          const input = inputs.nth(i);
          const inputWidth = await input.evaluate(el => el.offsetWidth);
          expect(inputWidth).toBeLessThanOrEqual(device.width - 40); // Account for padding
        }
      });

      it('should handle mobile touch interactions', async () => {
        // Test theme toggle with touch
        await page.tap('#theme-toggle');
        await page.waitForTimeout(300);
        
        const theme = await page.getAttribute('html', 'data-theme');
        expect(theme).toBe('dark');
        
        // Test form submission with touch
        await page.tap('#item1-name');
        await page.fill('#item1-name', 'Mobile Test Item');
        
        await page.tap('#item1-weight');
        await page.fill('#item1-weight', '100 kg');
        
        await page.tap('#item2-name');
        await page.fill('#item2-name', 'Mobile Test Item 2');
        
        await page.tap('#item2-weight');
        await page.fill('#item2-weight', '50 kg');
        
        await page.tap('#compare-btn');
        
        // Should show loading state
        await page.waitForSelector('#loading-spinner', { state: 'visible' });
      });

      it('should scroll and display results properly', async () => {
        // Fill form and submit
        await page.fill('#item1-name', 'Very Long Item Name That Might Wrap');
        await page.fill('#item1-weight', '2500 kilograms');
        await page.fill('#item2-name', 'Another Very Long Item Name');
        await page.fill('#item2-weight', '1200 kg');
        
        await page.click('#compare-btn');
        await page.waitForSelector('.comparison-result', { 
          state: 'visible', 
          timeout: 15000 
        });
        
        // Check if results are visible without horizontal scroll
        const resultsContainer = page.locator('.results-container');
        const containerWidth = await resultsContainer.evaluate(el => el.scrollWidth);
        const viewportWidth = device.width;
        
        expect(containerWidth).toBeLessThanOrEqual(viewportWidth);
        
        // Scroll to results if necessary
        await resultsContainer.scrollIntoViewIfNeeded();
        
        // Verify text is readable (not too small)
        const resultText = page.locator('.comparison-explanation');
        const fontSize = await resultText.evaluate(el => 
          window.getComputedStyle(el).fontSize
        );
        
        const fontSizeNumber = parseInt(fontSize.replace('px', ''));
        expect(fontSizeNumber).toBeGreaterThan(14); // Minimum readable size
      });
    });
  });

  it('should handle orientation changes', async () => {
    // Start in portrait
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/');
    
    // Fill form in portrait
    await page.fill('#item1-name', 'Portrait Test');
    await page.fill('#item1-weight', '100 kg');
    
    // Switch to landscape
    await page.setViewportSize({ width: 844, height: 390 });
    await page.waitForTimeout(300); // CSS transition
    
    // Continue filling form in landscape
    await page.fill('#item2-name', 'Landscape Test');
    await page.fill('#item2-weight', '75 kg');
    
    // Submit and verify layout
    await page.click('#compare-btn');
    await page.waitForSelector('#loading-spinner', { state: 'visible' });
    
    // Form should still be functional and properly laid out
    const form = page.locator('form');
    const isVisible = await form.isVisible();
    expect(isVisible).toBe(true);
  });
});
```

### 5.3 Accessibility Testing Across Devices

```javascript
// e2e/accessibility/cross-device-a11y.spec.js
describe('Cross-Device Accessibility', () => {
  it('should maintain keyboard navigation on all devices', async () => {
    await page.goto('/');
    
    // Test tab navigation
    await page.keyboard.press('Tab'); // Should focus first input
    let focused = await page.evaluate(() => document.activeElement.id);
    expect(focused).toBe('item1-name');
    
    await page.keyboard.press('Tab'); // Next input
    focused = await page.evaluate(() => document.activeElement.id);
    expect(focused).toBe('item1-weight');
    
    await page.keyboard.press('Tab'); // Next input
    focused = await page.evaluate(() => document.activeElement.id);
    expect(focused).toBe('item2-name');
    
    await page.keyboard.press('Tab'); // Next input
    focused = await page.evaluate(() => document.activeElement.id);
    expect(focused).toBe('item2-weight');
    
    await page.keyboard.press('Tab'); // Submit button
    focused = await page.evaluate(() => document.activeElement.id);
    expect(focused).toBe('compare-btn');
  });

  it('should announce loading states to screen readers', async () => {
    await page.goto('/');
    
    // Fill form
    await page.fill('#item1-name', 'Accessibility Test');
    await page.fill('#item1-weight', '100 kg');
    await page.fill('#item2-name', 'Screen Reader Test');
    await page.fill('#item2-weight', '50 kg');
    
    // Submit form
    await page.click('#compare-btn');
    
    // Check ARIA live region announcements
    const liveRegion = page.locator('[aria-live="polite"]');
    await expect(liveRegion).toBeVisible();
    
    const announcement = await liveRegion.textContent();
    expect(announcement).toContain('Processing comparison');
    
    // Wait for results and check final announcement
    await page.waitForSelector('.comparison-result', { 
      state: 'visible', 
      timeout: 15000 
    });
    
    const finalAnnouncement = await liveRegion.textContent();
    expect(finalAnnouncement).toContain('Comparison complete');
  });

  it('should handle high contrast mode', async () => {
    await page.goto('/');
    
    // Simulate high contrast mode
    await page.addStyleTag({
      content: `
        @media (prefers-contrast: high) {
          * {
            filter: contrast(2) !important;
          }
        }
      `
    });
    
    // Verify elements are still visible and functional
    const themeToggle = page.locator('#theme-toggle');
    await expect(themeToggle).toBeVisible();
    
    const compareButton = page.locator('#compare-btn');
    await expect(compareButton).toBeVisible();
    
    // Test functionality still works
    await page.click('#theme-toggle');
    await page.waitForTimeout(300);
    
    const theme = await page.getAttribute('html', 'data-theme');
    expect(theme).toBe('dark');
  });
});
```

## Summary

This comprehensive E2E testing specification provides:

1. **Complete User Journey Validation** - Tests entire workflows from form submission to AI comparison results with theme switching and multiple user scenarios

2. **Advanced Browser Automation** - Playwright-based automation with Page Object Model, performance monitoring, and cross-browser compatibility testing

3. **Performance & Load Testing** - Core Web Vitals validation, API response time SLA verification, and concurrent user load simulation

4. **Comprehensive Error Scenarios** - AI provider failures, network issues, circuit breaker states, rate limiting, and form validation errors

5. **Cross-Browser & Mobile Testing** - Full compatibility testing across Chrome, Firefox, Safari, and mobile devices with responsive design validation

6. **Accessibility Integration** - Screen reader compatibility, keyboard navigation, and high contrast mode testing across all scenarios

The framework ensures production-ready reliability by validating complete system integration from frontend user interactions through backend AI processing, providing confidence in deployment readiness and user experience quality.
