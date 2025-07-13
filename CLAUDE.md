# SizeComparator - AI Assistant Context

Last Updated: 2025-07-13

## Project Overview

SizeComparator is a lightweight web application that converts weight inputs (lbs/kg) into relatable object comparisons using AI providers (OpenAI, Anthropic, X.ai). The system transforms abstract weight values into concrete, understandable comparisons like "24 lbs = four chickens (6 lbs each)" to help users visualize and understand weight measurements.

### Core Value Proposition
- **Instant Understanding** - Convert any weight into familiar object comparisons
- **AI-Powered Accuracy** - Multiple AI providers ensure quality and reliability
- **Zero Dependencies** - Vanilla frontend with minimal backend for easy deployment
- **Robust Fallbacks** - Graceful degradation when AI providers fail

## Current Implementation Status (2025-07-13)

### Completed Features
- **System Architecture Design**
  - Lightweight FastAPI backend with async AI provider management
  - Vanilla HTML/CSS/JS frontend with no build dependencies
  - Provider abstraction pattern for pluggable AI services
  - Configuration-driven prompt templates and validation rules

- **Specification Documents**
  - Complete 10-page system specification with implementation details
  - Optimized prompt template for specification generation
  - Development workflow documentation for parallel implementation
  - Error handling and fallback strategies documented

- **AI Integration Framework**
  - Abstract provider interface supporting OpenAI, Anthropic, X.ai
  - Circuit breaker pattern for provider health management
  - Retry logic with exponential backoff and automatic failover
  - Response validation ensuring exactly 2 quality comparisons

- **Frontend Design**
  - Responsive single-page design with CSS Grid layout
  - Light/dark theme system with localStorage persistence
  - Progressive enhancement for optimal user experience
  - Mobile-first responsive design approach

- **Backend API Architecture**
  - RESTful API with comprehensive error handling
  - Input validation and unit conversion (lbs/kg)
  - Structured logging with request ID tracking
  - Health check endpoints for monitoring

### In Progress
- Core backend implementation (FastAPI application)
- AI provider implementations (OpenAI, Anthropic, X.ai)
- Frontend UI components and theme system
- Configuration management system (75% complete)

### Planned (Not Started)
- Integration testing with mock AI providers
- Production deployment configuration and Docker setup

### Known Issues
- AI provider rate limiting needs exponential backoff refinement
- Response validation rules require real-world testing with AI outputs
- Theme toggle animation could be smoother
- Error message localization not yet implemented

## Recent Changes (2025-07-13)

1. **Architecture Specification**
   - Created comprehensive 10-page system specification
   - Defined provider abstraction pattern for AI integration
   - Documented fallback strategies for AI provider failures
   - Established parallel development workflow

2. **Development Framework**
   - Implemented specification generation prompt optimization
   - Created development guidelines following senior dev + PM methodology
   - Established parallel task execution patterns
   - Defined code quality standards and security requirements

3. **AI Integration Design**
   - Designed provider interface with health monitoring
   - Created circuit breaker pattern for reliability
   - Established prompt template system for configuration-driven behavior
   - Defined response validation framework

4. **Bug Prevention Strategy**
   - Comprehensive error handling across all system layers
   - Input validation with specific error messages
   - Graceful degradation for AI service failures
   - Type hints throughout codebase for early error detection

5. **Development Optimization (100% Complete)**
   - Parallel development strategy for efficient team coordination
   - Template-driven specification generation
   - Minimal dependency approach for maintainability
   - Configuration-driven behavior for easy updates

## Development Guidelines

### Code Style
- No emojis or symbols in code, comments, or commit messages
- Professional, clear, and consistent naming conventions
- Follow PEP 8 for Python code and standard conventions for HTML/CSS/JS
- Use type hints throughout the Python codebase
- Write self-documenting code with minimal comments

### Git Commit Standards
- Use clear, descriptive commit messages
- Present tense, imperative mood ("Add feature" not "Added feature")
- First line: 50 characters max, capitalize, no period
- Blank line between subject and body
- Body: Wrap at 72 characters, explain what and why

### Testing Commands
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Type checking
mypy src/

# Linting
ruff check src/

# Format code
ruff format src/
```

### Common Development Tasks

#### Start Development Server
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Run Frontend Development Server
```bash
python -m http.server 3000 --directory frontend/
```

#### Test AI Provider Integration
```bash
python scripts/test_providers.py --provider openai
```

## Technical Details

### AI Provider Integration
- **Issue**: Multiple AI providers with different response formats and reliability
- **Solution**: Provider abstraction with standardized interface and circuit breaker pattern
- See SIZECOMPARATOR_SYSTEM_SPEC.md Section 3 for detailed information

### Weight Conversion Logic
- Supports lbs and kg with automatic conversion
- Validates input ranges (0.1 to 1,000,000 units)
- Normalizes precision to 2 decimal places
- Handles edge cases like very small or very large weights

### Authentication Flow
1. No user authentication required (public API)
2. Rate limiting per client IP address
3. API key management for AI providers via environment variables
4. Secure configuration loading with validation
5. No sensitive data exposure in responses or logs

## Project Structure (Current)
```
SizeComparator/
├── src/
│   ├── api/                # FastAPI routes and middleware
│   ├── core/               # Business logic and weight processing
│   ├── providers/          # AI provider implementations
│   ├── models/             # Pydantic models and schemas
│   ├── services/           # AI orchestration and response validation
│   │   ├── ai_manager.py   # Provider coordination and fallback
│   │   └── validator.py    # Response quality validation
│   └── main.py             # FastAPI application entry point
├── frontend/               # Static HTML/CSS/JS files
│   ├── css/                # Stylesheets with theme system
│   ├── js/                 # JavaScript modules and API client
│   └── index.html          # Single page application
├── config/                 # Configuration files and templates
├── tests/                  # Test suite
├── docs/                   # Technical documentation
├── scripts/                # Utility scripts
└── requirements.txt        # Python dependencies
```

## Refactoring Plans

### Immediate Goals
1. Implement AI provider circuit breaker with configurable thresholds
2. Add comprehensive input validation with user-friendly error messages
3. Create response caching system for improved performance
4. Implement structured logging with request tracing

### AI Integration Strategy
- Standardize response format across all providers
- Implement A/B testing for prompt effectiveness
- Add response quality scoring and automatic improvement
- Create fallback to static comparison database

### File Organization
- Separate AI provider implementations into individual modules
- Create shared utilities for weight conversion and validation
- Organize frontend assets with clear separation of concerns
- Establish configuration hierarchy for different environments

## Important Context for AI Assistants

### When Working on This Project:
1. **Simplicity First**: Always choose the simplest solution that meets requirements
2. **AI Provider Reliability**: Assume AI providers will fail and design accordingly
3. **Configuration Over Code**: Prefer file-based configuration for behavior changes
4. **Performance Matters**: Target sub-2 second response times for user requests
5. **Commit Frequently**: User prefers incremental commits with clear messages

### Common Pitfalls:
- Assuming AI providers always return valid responses
- Hardcoding prompt templates instead of using configuration
- Adding complex dependencies when simple solutions exist
- Not handling edge cases in weight conversion
- Creating files without planning the overall structure

### Testing Credentials:
- OpenAI API key stored in OPENAI_API_KEY environment variable
- Anthropic API key stored in ANTHROPIC_API_KEY environment variable
- X.ai API key stored in XAI_API_KEY environment variable

## Next Major Milestones

1. **Core Implementation**: Complete FastAPI backend with AI provider integration
2. **Frontend Development**: Implement responsive UI with theme system
3. **Integration Testing**: Comprehensive testing with real AI providers
4. **Performance Optimization**: Achieve sub-2 second response time targets
5. **Production Deployment**: Containerized deployment with monitoring

## Remember
- **Keep It Simple** - Avoid over-engineering solutions
- **Plan thoroughly** before implementing complex AI integration logic
- **Test with Real Providers** - Mock testing only goes so far with AI services
- **Think like a PM** - consider the full user journey from input to comparison
- **Document decisions** for future developers and AI provider changes
- **Monitor Everything** - AI providers change behavior and reliability
- Commit after every completed change
- No emojis in any text
- Test thoroughly before committing

## AI Assistant Best Practices

### Parallel Execution
When multiple independent pieces of information are requested, use parallel tool calls for optimal performance:
- Run multiple file reads when exploring the codebase
- Execute independent bash commands simultaneously  
- Batch AI provider tests together
- Generate multiple specification sections in parallel

### TodoWrite Usage
Use the TodoWrite tool proactively when:
- Implementing AI provider integration (complex multi-step task)
- Building frontend components with theme system
- User provides multiple features or enhancements
- Working on error handling across multiple components
- After receiving new requirements to capture all tasks

Skip TodoWrite for:
- Single configuration changes
- Simple bug fixes or typos
- Adding single utility functions
- Updating documentation only

### File Operations
- ALWAYS prefer editing existing files over creating new ones
- NEVER create documentation files unless explicitly requested
- Read configuration files before attempting to edit them
- Use absolute paths for all file operations
- Plan AI provider integration before implementation

### Testing and Validation
- Test AI provider integration with actual API calls when possible
- Verify weight conversion logic with edge cases
- Check theme system across different browsers
- Ensure error handling covers all AI provider failure modes
- Document any breaking changes in AI provider interfaces