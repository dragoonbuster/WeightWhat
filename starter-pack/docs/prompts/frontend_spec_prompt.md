# Frontend Specification Prompt Template

You are a senior frontend architect tasked with creating a comprehensive specification for [PROJECT NAME]'s user interface. Write a detailed specification document titled "FRONTEND_SPEC.md" in the docs/specs/ directory.

## Context
[PROJECT NAME] requires a [DESCRIPTION: e.g., modern web application with responsive design]. The specification should cover component architecture, state management, and UI patterns while supporting [FRAMEWORK: React/Vue/Vanilla JS/Angular] approach and accessibility standards.

## Critical Integration Requirements
This frontend specification MUST ensure exact alignment with backend contracts:
1. **Error Response Format**: Must reference BACKEND_CORE_SPEC section 5.3 ErrorResponse format exactly
2. **API Contracts**: All request/response models must match BACKEND_CORE_SPEC section 5.2 precisely
3. **Environment Variables**: Must reference CONFIG_SYSTEM_SPEC for SIZECOMPARATOR_* prefixed variables
4. **Error Codes**: Must align with ERROR_MONITORING_SPEC error taxonomy (4xx client errors, 5xx server errors, integration errors, business logic errors)

## Document Requirements
- **Target Length**: 10-12 pages
- **Focus**: Component architecture, state management, and design patterns
- **Code Examples**: Minimal, pattern-focused only
- **Style**: Use tables, bullet points, and cross-references

## Core Sections (with page allocations)

### 1. Executive Summary (1 page)
- Project overview and business objectives
- Technical approach and framework choice rationale
- Success metrics and user experience goals
- Integration with backend services and APIs

### 2. Component Architecture (2-3 pages)

#### 2.1 Design Pattern
Show the base component pattern once:
```javascript
// For React
const Component = ({ props }) => {
    const [state, setState] = useState(initialState);
    // Component logic
};

// For Vue
export default {
    name: 'Component',
    props: [],
    data() { return {}; },
    // Component logic
};

// For Vanilla JS
class Component {
    constructor(container, options = {}) {
        this.container = container;
        this.options = options;
        this.state = {};
        this.init();
    }
    // Standard lifecycle methods
}
```

#### 2.2 Component Hierarchy Table
| Component | Purpose | Parent | Communication |
|-----------|---------|--------|---------------|
| AppRoot | Application shell | - | Global state |
| Header | Navigation/branding | AppRoot | Props/events |
| [MAIN_FEATURE_1] | [PURPOSE] | AppRoot | State updates |
| [MAIN_FEATURE_2] | [PURPOSE] | AppRoot | API calls |
| [MAIN_FEATURE_3] | [PURPOSE] | AppRoot | User events |
| Common/* | Shared UI elements | Various | Props only |

#### 2.3 Communication Patterns
- Props/emit for parent-child (Vue/React)
- Context/providers for cross-component
- Event bus/pub-sub for decoupled messaging
- State management for complex flows

### 3. API Client Implementation (1.5 pages)

#### 3.1 Type-Safe API Client
**CRITICAL**: Generate TypeScript interfaces directly from BACKEND_CORE_SPEC Pydantic models:

```typescript
// Must match BACKEND_CORE_SPEC section 4.1 WeightComparisonRequest exactly
interface WeightComparisonRequest {
  item1_name: string;
  item1_weight: string;
  item2_name: string;
  item2_weight: string;
  output_unit?: WeightUnit;
}

// Must match BACKEND_CORE_SPEC section 4.2 WeightComparisonResponse exactly
interface WeightComparisonResponse {
  item1: WeightItem;
  item2: WeightItem;
  comparison: ComparisonResult;
  visualization_prompt: string;
  metadata: ResponseMetadata;
}

// Must match BACKEND_CORE_SPEC section 5.3 ErrorResponse exactly
interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, any>;
  request_id: string;
  timestamp: string;
}
```

#### 3.2 HTTP Client Configuration
- Base URL from SIZECOMPARATOR_API_ENDPOINT
- Timeout from SIZECOMPARATOR_API_TIMEOUT
- Request/response interceptors for error handling
- Request ID generation and propagation for tracing

#### 3.3 Error Response Processing
Map ERROR_MONITORING_SPEC taxonomy to user actions:
- 4xx errors: Show validation messages, disable retry
- 5xx errors: Show generic error, enable retry with exponential backoff
- Network errors: Show connectivity message, enable manual retry
- Timeout errors: Show timeout message, suggest checking connection

### 4. State Management (2 pages)

#### 4.1 State Architecture Overview
- [STATE_SOLUTION: Redux/Vuex/Context/Custom] pattern
- Unidirectional data flow diagram
- Persistence strategy (localStorage/sessionStorage)
- State synchronization approach

#### 4.2 State Structure Table
| State Key | Type | Persistence | Update Triggers |
|-----------|------|-------------|-----------------|
| auth | Object | Session | Login/logout |
| user | Object | Session | Profile updates |
| api | Object | None | Request lifecycle |
| errors | Object | None | Error responses |
| [DOMAIN_1] | [TYPE] | [STORAGE] | [TRIGGERS] |
| [DOMAIN_2] | [TYPE] | [STORAGE] | [TRIGGERS] |
| ui | Object | None | User interactions |

### 5. Design System & UI Patterns (1-2 pages)

#### 5.1 Visual Hierarchy
- Typography scale and usage
- Color palette and semantic meanings
- Spacing system (8px grid recommended)
- Icon library and usage guidelines

#### 5.2 Common UI Patterns Table
| Pattern | Usage | Components | Interaction |
|---------|-------|------------|-------------|
| Cards | Content display | List items, previews | Click/hover |
| Modals | Detailed views | Forms, confirmations | Open/close |
| Forms | Data input | All user inputs | Validate/submit |
| Tables | Data grids | Reports, lists | Sort/filter |
| Navigation | Wayfinding | Menu, breadcrumbs | Route/scroll |

### 6. Core Feature Specifications (3 pages)

#### 6.1 Feature Summary Table
| Feature | Components | Data Sources | Key Actions |
|---------|------------|--------------|-------------|
| [FEATURE_1] | [COMPONENTS] | [API/STATE] | [ACTIONS] |
| [FEATURE_2] | [COMPONENTS] | [API/STATE] | [ACTIONS] |
| [FEATURE_3] | [COMPONENTS] | [API/STATE] | [ACTIONS] |

#### 6.2 API Integration Contracts
**CRITICAL**: All API client implementations must match BACKEND_CORE_SPEC section 5.2 exactly:
- Request models must match `WeightComparisonRequest` schema precisely
- Response handling must conform to `WeightComparisonResponse` structure
- Error responses must implement exact `ErrorResponse` format from BACKEND_CORE_SPEC section 5.3:
  ```typescript
  interface ErrorResponse {
    error: string;
    message: string;
    details?: Record<string, any>;
    request_id: string;
    timestamp: string; // ISO 8601 format
  }
  ```

#### 6.3 Error Handling Framework
Must align with ERROR_MONITORING_SPEC taxonomy:
- **Client Errors (4xx)**: Invalid requests, authentication failures, rate limiting
- **Server Errors (5xx)**: Service unavailable, internal errors, dependency failures  
- **Integration Errors**: External API failures, database timeouts, message queue issues
- **Business Logic Errors**: Invalid object comparisons, constraint violations

Error handling patterns:
- Display user-friendly messages based on error.message
- Log technical details from error.details for debugging
- Track request_id for issue correlation
- Implement retry logic based on error category

#### 6.4 User Flows
- Primary user journey diagram
- Alternative paths and edge cases
- Error handling and recovery flows
- Success states and feedback

#### 6.5 Interactive Elements
- Form validation patterns
- Loading and progress indicators
- Error states and messages
- Empty states and onboarding

### 7. Responsive Design & Accessibility (1-2 pages)

#### 7.1 Responsive Breakpoints
| Breakpoint | Width | Layout Changes | Priority Content |
|------------|-------|----------------|------------------|
| Mobile | 0-767px | Single column | Core actions |
| Tablet | 768-1023px | 2 columns | Primary features |
| Desktop | 1024-1439px | Multi-column | Full interface |
| Large | 1440px+ | Optimized | Enhanced views |

#### 7.2 Accessibility Requirements
- WCAG 2.1 AA compliance targets
- Keyboard navigation implementation
- Screen reader optimization
- Color contrast requirements (4.5:1 minimum)
- Focus management strategy
- ARIA patterns for complex widgets

### 8. Performance & Optimization (1 page)

#### 8.1 Performance Targets
| Metric | Target | Strategy |
|--------|--------|----------|
| Initial Load | < 3s | Code splitting, lazy loading |
| Time to Interactive | < 5s | Critical path optimization |
| Largest Contentful Paint | < 2.5s | Image optimization |
| First Input Delay | < 100ms | Main thread optimization |

#### 8.2 Optimization Strategies
- Bundle splitting approach
- Asset optimization (images, fonts)
- Caching strategy
- Progressive enhancement
- Virtualization for large lists

### 9. Implementation Roadmap (1 page)

#### Phase 1: Foundation (Week 1-2)
- Design system setup
- Component architecture
- State management implementation
- Development environment

#### Phase 2: Core Features (Week 3-4)
- [FEATURE_1] implementation
- [FEATURE_2] implementation
- API integration layer
- Basic responsive layouts

#### Phase 3: Enhanced Features (Week 5-6)
- [FEATURE_3] implementation
- Advanced interactions
- Performance optimization
- Accessibility features

#### Phase 4: Polish & Testing (Week 7-8)
- Cross-browser testing
- Performance audit
- Accessibility audit
- User acceptance testing

## Technical Considerations

### Technology Stack
- Framework: [React/Vue/Angular/Vanilla JS]
- State Management: [Redux/Vuex/MobX/Context]
- Styling: [CSS Modules/Styled Components/SCSS/Tailwind]
- Build Tools: [Webpack/Vite/Parcel]
- Testing: [Jest/Vitest/Cypress]

### Environment Configuration
**CRITICAL**: Must reference CONFIG_SYSTEM_SPEC for all environment variables:
- All configuration variables must use SIZECOMPARATOR_* prefix
- Environment variable template syntax: `${VAR_NAME:-default_value}`
- Required frontend configuration variables:
  - `SIZECOMPARATOR_API_ENDPOINT`: Backend API base URL
  - `SIZECOMPARATOR_API_TIMEOUT`: Request timeout in milliseconds
  - `SIZECOMPARATOR_ENVIRONMENT`: deployment environment (development/staging/production)
  - `SIZECOMPARATOR_LOG_LEVEL`: Frontend logging level
  - `SIZECOMPARATOR_CACHE_TTL`: Client-side cache time-to-live

Example configuration integration:
```typescript
const config = {
  apiEndpoint: process.env.SIZECOMPARATOR_API_ENDPOINT || 'http://localhost:8000',
  apiTimeout: parseInt(process.env.SIZECOMPARATOR_API_TIMEOUT || '30000'),
  environment: process.env.SIZECOMPARATOR_ENVIRONMENT || 'development',
  logLevel: process.env.SIZECOMPARATOR_LOG_LEVEL || 'info',
  cacheTtl: parseInt(process.env.SIZECOMPARATOR_CACHE_TTL || '3600')
};
```

### Browser Support
- Modern browsers (last 2 versions)
- Mobile browsers (iOS Safari, Chrome)
- Progressive enhancement strategy
- Polyfill requirements

### Code Organization
```
src/
├── components/       # UI components
│   ├── common/      # Shared components
│   ├── features/    # Feature-specific
│   └── layouts/     # Layout components
├── services/        # API and utilities
├── state/          # State management
├── styles/         # Global styles
├── assets/         # Static assets
└── [entry]         # Main entry point
```

## Mandatory Cross-References
**CRITICAL**: Frontend specification must explicitly reference and align with:

### Backend Integration (MANDATORY)
- **BACKEND_CORE_SPEC section 5.2**: Request/response contracts for all API endpoints
- **BACKEND_CORE_SPEC section 5.3**: Exact ErrorResponse format implementation
- **BACKEND_CORE_SPEC section 4**: Pydantic models for type-safe client generation

### Configuration Management (MANDATORY)  
- **CONFIG_SYSTEM_SPEC section 2.3**: Environment variable handling with SIZECOMPARATOR_* prefix
- **CONFIG_SYSTEM_SPEC section 4**: Validation framework for frontend configuration
- **CONFIG_SYSTEM_SPEC section 8**: Security requirements for sensitive data handling

### Error Handling (MANDATORY)
- **ERROR_MONITORING_SPEC section 2**: Error categorization taxonomy alignment
- **ERROR_MONITORING_SPEC section 1**: Structured logging with request ID propagation
- **ERROR_MONITORING_SPEC section 4**: Metrics collection requirements for frontend

### Supporting References
- See AUTHENTICATION_SPEC for auth flows
- See DATABASE_SPEC for data models  
- See TESTING_SPEC for test strategies
- See AI_PROVIDER_SPEC for visualization integration

## Key Deliverables
1. Component architecture documentation
2. State management implementation
3. Design system and style guide
4. Responsive layout system
5. Accessibility compliance report
6. Performance optimization plan
7. Interactive prototype/mockups

The specification should provide clear architectural guidance while remaining flexible for implementation details, maintaining a focused 10-12 page format that balances comprehensiveness with readability.

## Integration Validation Checklist
Before finalizing the frontend specification, verify:

### Backend Contract Compliance
- [ ] All TypeScript interfaces match BACKEND_CORE_SPEC Pydantic models exactly
- [ ] Error response handling implements BACKEND_CORE_SPEC section 5.3 ErrorResponse format
- [ ] API endpoints match BACKEND_CORE_SPEC section 5.2 contracts precisely
- [ ] HTTP status codes align with backend implementation

### Configuration System Integration
- [ ] All environment variables use SIZECOMPARATOR_* prefix per CONFIG_SYSTEM_SPEC
- [ ] Environment variable template syntax matches CONFIG_SYSTEM_SPEC section 2.3
- [ ] Security requirements from CONFIG_SYSTEM_SPEC section 8 are implemented
- [ ] Frontend configuration validation follows CONFIG_SYSTEM_SPEC patterns

### Error Monitoring Alignment
- [ ] Error categories match ERROR_MONITORING_SPEC taxonomy exactly
- [ ] Request ID propagation follows ERROR_MONITORING_SPEC section 1 requirements
- [ ] Frontend metrics collection aligns with ERROR_MONITORING_SPEC section 4
- [ ] Error logging structures match observability requirements

### Interface Consistency
- [ ] No custom error formats that deviate from backend specifications
- [ ] No environment variables outside CONFIG_SYSTEM_SPEC naming conventions
- [ ] No error codes that conflict with ERROR_MONITORING_SPEC taxonomy
- [ ] All request/response models maintain type safety with backend

## Customization Instructions
When using this template:
1. Replace all [PLACEHOLDERS] with project-specific details
2. Add/remove features based on project scope
3. Adjust timeline based on team size and complexity
4. Include relevant technology stack details
5. **MANDATORY**: Verify all backend specification references are current and accurate
6. **MANDATORY**: Validate environment variable naming against CONFIG_SYSTEM_SPEC
7. **MANDATORY**: Confirm error handling taxonomy matches ERROR_MONITORING_SPEC
8. Add domain-specific UI patterns as needed

## Critical Success Factors
The frontend specification is considered complete only when:
1. All API contracts are type-safe and match backend exactly
2. Error handling covers all ERROR_MONITORING_SPEC categories
3. Environment configuration follows CONFIG_SYSTEM_SPEC patterns
4. No interface mismatches exist between frontend and backend components