# Config Loader Specification Prompt

Create a focused CONFIG_LOADER_SPEC.md specification for SizeComparator's configuration loading system. Target 5 pages maximum.

## Context
This specification defines the configuration loading system that manages YAML/JSON files, environment variables, and hot-reload capabilities across all SizeComparator components.

## Document Requirements

### 1. File Loading Architecture (1 page)
- YAML and JSON file loading with hierarchical configuration support
- Configuration file discovery and loading order (base → environment → local)
- File watching system for hot-reload capability
- Atomic configuration updates with rollback on failure

### 2. Environment Variable Resolution (1 page)
- Template syntax: `${VAR_NAME:-default_value}` resolution
- Recursive variable expansion and circular dependency detection  
- Type conversion and validation during resolution
- SIZECOMPARATOR_* prefix enforcement and validation

### 3. Configuration Hierarchy Management (1 page)
- Base configuration (config/base.yaml)
- Environment-specific overrides (config/dev.yaml, config/prod.yaml)
- Local developer overrides (config/local.yaml) 
- Merge strategy and conflict resolution rules

### 4. JSON Schema Validation Framework (1 page)
- Schema definition for all configuration sections
- Runtime validation with detailed error reporting
- Custom validators for business logic (URL reachability, API key format)
- Validation caching and performance optimization

### 5. Hot-Reload and Error Handling (1 page)
- File system monitoring with debouncing
- Safe configuration updates without service restart
- Validation and rollback for invalid configuration changes
- Change event notification to dependent components

## Integration Requirements
- Reference CONFIG_SYSTEM_SPEC for overall architecture
- Integrate with all components for configuration access
- Support ENV_MANAGER_SPEC for environment variable processing
- Align with ERROR_MONITORING_SPEC for configuration error logging

## Focus Areas
- Atomic configuration updates
- Zero-downtime configuration changes
- Comprehensive validation and error handling
- Performance optimization for frequent reloads
- Development and production environment support