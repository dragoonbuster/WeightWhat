#!/bin/bash

# TickerTape Parallel Specification Generator
# Demonstrates the power of parallel execution with claude-code

set -euo pipefail

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
readonly SPECS_DIR="$PROJECT_ROOT/docs/specs"
readonly PROMPTS_DIR="$PROJECT_ROOT/docs/prompts"
readonly LOG_DIR="$PROJECT_ROOT/logs/spec-generation"
readonly MAX_PARALLEL_JOBS=4
readonly TIMEOUT_SECONDS=600  # 10 minutes per spec

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Available specification types
declare -A SPEC_TYPES=(
    ["api"]="API Contracts Specification"
    ["database"]="Database Schema Specification"
    ["core"]="Core Services Specification"
    ["content"]="Content Pipeline Specification"
    ["background"]="Background Processing Specification"
    ["frontend"]="Frontend Enhancement Specification"
    ["testing"]="Integration Testing Specification"
    ["manager"]="Manager Agents Specification"
)

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] <spec_type> [spec_type ...]

Generate TickerTape specifications in parallel using claude-code.

Available spec types:
EOF
    for key in "${!SPEC_TYPES[@]}"; do
        printf "  %-12s - %s\n" "$key" "${SPEC_TYPES[$key]}"
    done
    
    cat << EOF

Options:
  -h, --help       Show this help message
  -a, --all        Generate all available specifications
  -j, --jobs NUM   Maximum parallel jobs (default: $MAX_PARALLEL_JOBS)
  -t, --timeout    Timeout in seconds per spec (default: $TIMEOUT_SECONDS)
  -d, --dry-run    Show what would be generated without executing
  -v, --verbose    Enable verbose output

Examples:
  # Generate a single specification
  $0 api

  # Generate multiple specifications in parallel
  $0 api database core

  # Generate all specifications with 6 parallel jobs
  $0 --all --jobs 6

  # Dry run to see what would be generated
  $0 --dry-run --all

EOF
    exit 1
}

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

# Function to create necessary directories
setup_directories() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$SPECS_DIR"
    mkdir -p "$PROMPTS_DIR"
}

# Function to generate a single specification
generate_spec() {
    local spec_type=$1
    local spec_name="${SPEC_TYPES[$spec_type]}"
    local output_file="$SPECS_DIR/${spec_type^^}_SPEC.md"
    local log_file="$LOG_DIR/${spec_type}_$(date +%Y%m%d_%H%M%S).log"
    local prompt_file="$PROMPTS_DIR/${spec_type}_spec_prompt.md"
    
    print_color "$BLUE" "[$(date +%H:%M:%S)] Starting: $spec_name"
    
    # Create a prompt for this specification
    cat > "$prompt_file" << EOF
Generate a comprehensive specification for the TickerTape ${spec_name}.

Context:
- TickerTape is an AI-driven media tracking application
- Users describe what they want to track in plain English
- The system uses AI to understand intent and monitor multiple sources

Requirements for this specification:
1. Define clear interfaces and contracts
2. Include error handling strategies
3. Provide implementation examples
4. Consider scalability and performance
5. Include testing strategies

Output the specification to: $output_file

Make the specification detailed, actionable, and ready for implementation.
EOF
    
    # Run claude-code with timeout
    if timeout "$TIMEOUT_SECONDS" claude-code "$prompt_file" > "$log_file" 2>&1; then
        if [[ -f "$output_file" ]]; then
            local line_count=$(wc -l < "$output_file")
            print_color "$GREEN" "[$(date +%H:%M:%S)] ✓ Completed: $spec_name ($line_count lines)"
            return 0
        else
            print_color "$RED" "[$(date +%H:%M:%S)] ✗ Failed: $spec_name - No output file created"
            return 1
        fi
    else
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            print_color "$RED" "[$(date +%H:%M:%S)] ✗ Timeout: $spec_name (exceeded ${TIMEOUT_SECONDS}s)"
        else
            print_color "$RED" "[$(date +%H:%M:%S)] ✗ Failed: $spec_name (exit code: $exit_code)"
        fi
        return 1
    fi
}

# Function to run specifications in parallel
run_parallel() {
    local -a specs=("$@")
    local -a pids=()
    local -a results=()
    local active_jobs=0
    local completed_jobs=0
    local failed_jobs=0
    
    print_color "$YELLOW" "Starting parallel generation of ${#specs[@]} specifications"
    print_color "$YELLOW" "Maximum parallel jobs: $MAX_PARALLEL_JOBS"
    echo
    
    # Start time for overall progress
    local start_time=$(date +%s)
    
    # Process all specifications
    for spec in "${specs[@]}"; do
        # Wait if we've reached the parallel job limit
        while [[ $active_jobs -ge $MAX_PARALLEL_JOBS ]]; do
            # Check for completed jobs
            for i in "${!pids[@]}"; do
                if [[ -n "${pids[$i]}" ]] && ! kill -0 "${pids[$i]}" 2>/dev/null; then
                    wait "${pids[$i]}"
                    local exit_code=$?
                    if [[ $exit_code -eq 0 ]]; then
                        ((completed_jobs++))
                    else
                        ((failed_jobs++))
                    fi
                    ((active_jobs--))
                    unset pids[$i]
                fi
            done
            sleep 0.1
        done
        
        # Start new job
        if [[ $DRY_RUN -eq 0 ]]; then
            generate_spec "$spec" &
            pids+=($!)
            ((active_jobs++))
        else
            print_color "$BLUE" "[DRY RUN] Would generate: ${SPEC_TYPES[$spec]}"
            ((completed_jobs++))
        fi
    done
    
    # Wait for remaining jobs
    print_color "$YELLOW" "\nWaiting for remaining jobs to complete..."
    for pid in "${pids[@]}"; do
        if [[ -n "$pid" ]]; then
            wait "$pid"
            if [[ $? -eq 0 ]]; then
                ((completed_jobs++))
            else
                ((failed_jobs++))
            fi
        fi
    done
    
    # Calculate duration
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    # Print summary
    echo
    print_color "$YELLOW" "=== Generation Summary ==="
    print_color "$GREEN" "Completed: $completed_jobs"
    print_color "$RED" "Failed: $failed_jobs"
    print_color "$BLUE" "Total time: ${minutes}m ${seconds}s"
    
    # Validate results
    if [[ $DRY_RUN -eq 0 ]]; then
        echo
        print_color "$YELLOW" "=== Validation Results ==="
        validate_results "${specs[@]}"
    fi
    
    return $failed_jobs
}

# Function to validate generated specifications
validate_results() {
    local -a specs=("$@")
    local valid_count=0
    local total_size=0
    
    for spec in "${specs[@]}"; do
        local output_file="$SPECS_DIR/${spec^^}_SPEC.md"
        if [[ -f "$output_file" ]]; then
            local file_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null || echo 0)
            local line_count=$(wc -l < "$output_file")
            
            if [[ $file_size -gt 1000 ]]; then  # At least 1KB
                ((valid_count++))
                ((total_size += file_size))
                printf "  %-20s: %6d lines (%d KB)\n" "${SPEC_TYPES[$spec]}" "$line_count" "$((file_size / 1024))"
            else
                print_color "$RED" "  ${SPEC_TYPES[$spec]}: Too small ($file_size bytes)"
            fi
        else
            print_color "$RED" "  ${SPEC_TYPES[$spec]}: Not found"
        fi
    done
    
    echo
    print_color "$GREEN" "Valid specifications: $valid_count/${#specs[@]}"
    print_color "$BLUE" "Total size: $((total_size / 1024)) KB"
}

# Function to check dependencies
check_dependencies() {
    local missing_deps=0
    
    if ! command -v claude-code &> /dev/null; then
        print_color "$RED" "Error: claude-code is not installed or not in PATH"
        ((missing_deps++))
    fi
    
    if ! command -v timeout &> /dev/null; then
        if command -v gtimeout &> /dev/null; then
            # macOS with coreutils
            alias timeout=gtimeout
        else
            print_color "$RED" "Error: timeout command not found (install coreutils)"
            ((missing_deps++))
        fi
    fi
    
    if [[ $missing_deps -gt 0 ]]; then
        exit 1
    fi
}

# Main function
main() {
    local -a specs_to_generate=()
    local max_jobs=$MAX_PARALLEL_JOBS
    local timeout=$TIMEOUT_SECONDS
    local verbose=0
    
    # Default values
    DRY_RUN=0
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                ;;
            -a|--all)
                specs_to_generate=("${!SPEC_TYPES[@]}")
                ;;
            -j|--jobs)
                max_jobs="$2"
                shift
                ;;
            -t|--timeout)
                timeout="$2"
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=1
                ;;
            -v|--verbose)
                verbose=1
                ;;
            *)
                if [[ -n "${SPEC_TYPES[$1]}" ]]; then
                    specs_to_generate+=("$1")
                else
                    print_color "$RED" "Error: Unknown spec type: $1"
                    echo "Available types: ${!SPEC_TYPES[*]}"
                    exit 1
                fi
                ;;
        esac
        shift
    done
    
    # Check if any specs were specified
    if [[ ${#specs_to_generate[@]} -eq 0 ]]; then
        print_color "$RED" "Error: No specification types specified"
        usage
    fi
    
    # Update global variables
    MAX_PARALLEL_JOBS=$max_jobs
    TIMEOUT_SECONDS=$timeout
    
    # Check dependencies
    check_dependencies
    
    # Setup directories
    setup_directories
    
    # Show configuration
    print_color "$YELLOW" "=== TickerTape Specification Generator ==="
    print_color "$BLUE" "Project root: $PROJECT_ROOT"
    print_color "$BLUE" "Output directory: $SPECS_DIR"
    print_color "$BLUE" "Log directory: $LOG_DIR"
    echo
    
    # Run parallel generation
    run_parallel "${specs_to_generate[@]}"
    
    exit $?
}

# Run main function
main "$@"