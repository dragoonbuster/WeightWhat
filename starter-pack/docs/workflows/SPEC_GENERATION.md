# Specification Generation Workflow Guide

Last Updated: 2025-07-13

## Overview: The Prompt → Spec → Optimization Cycle

The specification generation workflow is a systematic approach to creating comprehensive technical documentation that balances detail with efficiency. This guide documents the proven process used in TickerTape, which achieved 40-50% compression in specification size while maintaining technical accuracy.

### The Core Cycle

```
1. Prompt Design → 2. Spec Generation → 3. Optimization Review → 4. Implementation
      ↑                                              |
      └──────────────── Refinement ←─────────────────┘
```

**Key Principles:**
- Start with focused, structured prompts
- Generate within token limits (8-12 pages optimal)
- Optimize for implementation utility, not documentation completeness
- Iterate based on actual usage patterns

## Writing Effective Prompts

### The Anatomy of a Specification Prompt

A well-structured prompt contains:

1. **Clear Objective Statement**
2. **Context and Constraints**
3. **Document Structure with Page Allocations**
4. **Technical Requirements**
5. **Quality Standards**

### Example: Optimized Content Pipeline Prompt

```markdown
# Content Pipeline Specification Prompt

Create a focused CONTENT_PIPELINE_SPEC.md specification for TickerTape's content fetching system. 
Target length: 12 pages maximum.

## Context
TickerTape needs a content pipeline to aggregate media information from multiple sources 
(TMDB, web scraping, RSS). This is Phase 1 of the project and critical for the matching system to work.

## Document Requirements

Write a 12-page specification covering:

### 1. Executive Summary (1 page)
- Purpose: Unified content aggregation system
- Key architectural decisions (3-4 main ones)
- Expected performance targets
- Integration with matching system

### 2. System Architecture (3 pages)
- High-level architecture diagram (text-based)
- ContentProvider abstract base class (core interface only)
- Plugin discovery and registration system
- Data flow: Fetch → Normalize → Store → Index
- Key design patterns (2-3 main ones)

### 3. Provider Framework (2 pages)
- Provider interface and lifecycle
- Configuration management
- Error handling strategy
- Rate limiting framework
- ONE complete provider example (TMDB)

[Continue with remaining sections...]

## Technical Requirements
1. **Focus on Architecture**: Emphasize design patterns and integration contracts
2. **Code Examples**: Include 2-3 key code examples only
3. **Integration Focus**: Show connections to existing systems
4. **Practical Guidance**: Sufficient detail for senior developers
5. **Performance Oriented**: Specific targets and bottleneck mitigation

## Quality Standards
- Every section must provide actionable technical guidance
- Avoid redundant explanations
- Focus on decision points and contracts
- Include error scenarios and handling
- Maintain professional technical depth
```

### Prompt Writing Best Practices

1. **Specify Exact Page Limits**: "Write a 12-page specification" not "Write a comprehensive specification"
2. **Break Down Section Allocations**: Assign specific page counts to each section
3. **Focus on Architecture Over Implementation**: Request patterns and contracts, not exhaustive code
4. **Include Integration Points**: Always specify how the component connects to the larger system
5. **Request Specific Examples**: "Include ONE complete provider example" not "Include provider examples"

## The 8-12 Page Limit: Why It Matters

### Context Window Economics

```
Token Usage Analysis:
- 1 page ≈ 500-700 tokens
- 12 pages ≈ 6,000-8,400 tokens
- Claude's context: ~100,000 tokens

Efficiency Gains:
- Single 25-page spec: 25% of context window
- Optimized 12-page spec: 12% of context window
- Parallel capacity: 2-3 specs → 8-10 specs
```

### Optimal Specification Sizes

| Spec Type | Target Pages | Use Case |
|-----------|-------------|----------|
| Core Architecture | 10-12 | Critical system components |
| Implementation Guide | 8-10 | Specific feature development |
| Integration Spec | 8-10 | System connections |
| Reference Documentation | 6-8 | Lookup information |
| Future Features | 8-10 | High-level planning |

### Benefits of Size Constraints

1. **Forced Prioritization**: Only essential information makes the cut
2. **Better Readability**: Developers find and absorb information faster
3. **Parallel Processing**: Load multiple specs simultaneously
4. **Iteration Speed**: Faster generation and review cycles
5. **Maintenance**: Easier to keep specifications current

## Optimization Strategies

### 1. Table-Driven Design

Replace verbose descriptions with structured tables:

**Before** (3 paragraphs):
```
The system supports multiple authentication providers. For OAuth2, we need to store 
client ID, client secret, redirect URI, and scopes. For API keys, we store the key 
and optional rate limits. For JWT, we need the signing key and algorithm...
```

**After** (1 table):
```
| Provider | Required Config | Optional Config | Notes |
|----------|----------------|-----------------|-------|
| OAuth2 | client_id, client_secret, redirect_uri | scopes, state | Standard flow |
| API Key | api_key | rate_limit, expires | Header/query param |
| JWT | signing_key, algorithm | issuer, audience | RS256 preferred |
```

### 2. Cross-Reference Architecture

Instead of duplicating information:

```markdown
### Caching Strategy
See CORE_SERVICES_SPEC.md Section 4.2 for cache architecture.
This component implements the standard cache interface with:
- TTL: 5 minutes for live data, 24 hours for static
- Keys: `pipeline:provider:{provider_id}:content:{content_id}`
```

### 3. Focused Content Patterns

**Include:**
- Architecture decisions and rationale
- Integration contracts and interfaces
- Key algorithms and patterns
- Critical configuration
- Error handling strategies

**Exclude:**
- Exhaustive implementation details
- Multiple similar examples
- Operational procedures (separate doc)
- Historical context or alternatives considered
- Verbose explanations of standard patterns

### 4. Code Example Optimization

Limit to 2-3 essential examples that demonstrate:
- Core interface/contract
- Primary implementation pattern
- Integration example

```python
# Example: ContentProvider Interface (keep this)
class ContentProvider(ABC):
    @abstractmethod
    async def fetch(self, query: SearchQuery) -> List[Content]:
        """Fetch content matching the query."""
        pass
    
    @abstractmethod
    def normalize(self, raw_data: Dict) -> Content:
        """Normalize provider-specific data to standard format."""
        pass

# Skip: Full implementations of every provider
# Skip: Detailed error handling for each method
# Skip: Complete test examples
```

## Generic Specification Prompt Template

```markdown
# [COMPONENT_NAME] Specification Prompt

Create a focused [COMPONENT_NAME]_SPEC.md specification for [brief description]. 
Target length: [8-12] pages maximum.

## Context
[2-3 sentences explaining why this component exists, what problem it solves, 
and where it fits in the system architecture]

## Document Requirements

Write a [N]-page specification covering:

### 1. Executive Summary (1 page)
- Purpose and scope
- Key architectural decisions (3-4 main ones)
- Success criteria
- Integration touchpoints

### 2. System Architecture ([2-3] pages)
- High-level design (text-based diagram)
- Core components and their responsibilities
- Data flow and lifecycle
- Key design patterns employed

### 3. [Primary Feature Area] ([2-3] pages)
- Detailed design of main functionality
- Core algorithms/logic
- API contracts
- One complete implementation example

### 4. [Secondary Feature Area] ([1-2] pages)
- Supporting functionality design
- Integration patterns
- Configuration approach

### 5. Integration Points ([1-2] pages)
- How this connects to existing components
- Database models used/created
- Event system integration
- API endpoints exposed

### 6. Operations (1 page)
- Key configuration parameters
- Monitoring/metrics
- Common troubleshooting
- Scaling considerations

## Technical Requirements

1. **Architecture Focus**: Emphasize design decisions and patterns
2. **Code Examples**: Include [2-3] key examples only
3. **Integration Clear**: Show all connection points
4. **Implementation Ready**: Sufficient for senior developers
5. **Performance**: Include specific targets where relevant

## Quality Standards

- Actionable technical guidance throughout
- No redundant explanations
- Focus on decisions and contracts
- Error scenarios included
- Professional technical depth

The specification should serve as a focused implementation guide covering essential 
architecture and integration points without excessive examples.
```

## Validation Checklist

### Pre-Generation
- [ ] Prompt specifies exact page limit (8-12 pages)
- [ ] Section breakdown with page allocations provided
- [ ] Context explains component's role in larger system
- [ ] Technical requirements focus on architecture over implementation
- [ ] Quality standards emphasize actionable guidance

### Post-Generation Review
- [ ] Total length within target range
- [ ] Each section provides implementable guidance
- [ ] Integration points clearly defined
- [ ] 2-3 code examples demonstrate core patterns
- [ ] No excessive implementation details
- [ ] Cross-references to related specs included
- [ ] Error handling strategies documented
- [ ] Performance targets specified where relevant

### Optimization Assessment
- [ ] Could any section be converted to a table?
- [ ] Are there redundant examples that could be removed?
- [ ] Can verbose explanations be simplified?
- [ ] Would diagrams/tables communicate better than text?
- [ ] Are all code examples essential?

## Running Multiple Spec Generations in Parallel

### Strategy 1: Independent Specifications

When specifications have minimal interdependencies:

```
Parallel Batch 1 (Foundation):
- DATABASE_SCHEMA_SPEC
- API_CONTRACTS_SPEC
- FRONTEND_ENHANCEMENT_SPEC

Parallel Batch 2 (Core Features):
- CONTENT_PIPELINE_SPEC
- CORE_SERVICES_SPEC
- BACKGROUND_PROCESSING_SPEC

Parallel Batch 3 (Advanced):
- MANAGER_AGENTS_SPEC
- INTEGRATION_TESTING
- PHASE_6_PRODUCTION
```

### Strategy 2: Multi-Part Generation

For specifications exceeding token limits:

```
CONTENT_PIPELINE_SPEC.md (Total: 20+ pages)
├── Part 1: Core Architecture (8 pages) → Agent 1
├── Part 2: Provider Implementations (8 pages) → Agent 2
└── Part 3: Operations & Monitoring (6 pages) → Agent 3

Assembly: Dedicated agent combines all parts
```

### Parallel Execution Tips

1. **Start with Independent Specs**: Minimize dependencies
2. **Use Clear Naming**: `SPEC_NAME_PART1.md`, `SPEC_NAME_PART2.md`
3. **Include Context**: Each part should reference overall structure
4. **Coordinate Terminology**: Ensure consistent naming across parts
5. **Plan Assembly**: Reserve an agent for combining multi-part specs

## Common Spec Types and Characteristics

### 1. Architecture Specifications
**Examples**: CORE_SERVICES_SPEC, CONTENT_PIPELINE_SPEC
**Characteristics**:
- Heavy on design patterns and decisions
- Multiple component interactions
- Performance considerations critical
- 10-12 pages optimal

### 2. Implementation Guides
**Examples**: DATABASE_CONSOLIDATION_SPEC, FRONTEND_ENHANCEMENT_SPEC
**Characteristics**:
- Step-by-step procedures
- Migration strategies
- Before/after comparisons
- 8-10 pages optimal

### 3. Integration Specifications
**Examples**: API_CONTRACTS_SPEC, BACKGROUND_PROCESSING_SPEC
**Characteristics**:
- Interface definitions
- Protocol specifications
- Event flows
- 8-10 pages optimal

### 4. Operational Specifications
**Examples**: PHASE_6_PRODUCTION, INTEGRATION_TESTING
**Characteristics**:
- Deployment procedures
- Monitoring strategies
- Troubleshooting guides
- 10-12 pages optimal

### 5. Feature Specifications
**Examples**: MANAGER_AGENTS_SPEC, Enhancement specs
**Characteristics**:
- User-facing functionality
- AI/ML components
- Privacy considerations
- 8-10 pages for future features

## Compression Achievement Examples

### TickerTape Optimization Results

| Specification | Original | Optimized | Reduction | Strategy Used |
|--------------|----------|-----------|-----------|---------------|
| CORE_SERVICES | 25+ pages | 15 pages | 40% | Removed redundant examples, tabled configurations |
| CONTENT_PIPELINE | 20+ pages | 12 pages | 40% | Focused on architecture, single provider example |
| DATABASE_CONSOLIDATION | 20 pages | 10 pages | 50% | Eliminated verbose migrations, kept key patterns |
| MANAGER_AGENTS | 20+ pages | 10 pages | 50% | High-level architecture only, deferred implementation |

### Key Compression Techniques

1. **Example Reduction**: From all providers to one representative
2. **Table Conversion**: Configuration options, error codes, API endpoints
3. **Cross-Referencing**: Instead of repeating shared patterns
4. **Focus Shift**: From implementation to architecture
5. **Appendix Removal**: Moved to separate implementation guides

## Conclusion

The specification generation workflow is about creating focused, actionable technical documentation that serves its purpose without excess. By following these guidelines:

- Specifications remain within context window limits
- Multiple specs can be processed in parallel
- Developers get the guidance they need
- Documentation stays maintainable

Remember: The goal is not comprehensive documentation but effective implementation guidance. Every page should earn its place by providing unique, actionable value to the development team.