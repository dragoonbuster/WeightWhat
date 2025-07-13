#!/bin/bash

# Example usage of the parallel specification generator

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== TickerTape Parallel Specification Generator Examples ==="
echo

echo "1. Show help and available options:"
echo "   $SCRIPT_DIR/generate_specs.sh --help"
echo

echo "2. Generate a single specification:"
echo "   $SCRIPT_DIR/generate_specs.sh api"
echo

echo "3. Generate multiple specifications in parallel:"
echo "   $SCRIPT_DIR/generate_specs.sh api database core"
echo

echo "4. Generate all specifications with custom settings:"
echo "   $SCRIPT_DIR/generate_specs.sh --all --jobs 6 --timeout 900"
echo

echo "5. Dry run to see what would be generated:"
echo "   $SCRIPT_DIR/generate_specs.sh --dry-run --all"
echo

echo "6. Generate with verbose output:"
echo "   $SCRIPT_DIR/generate_specs.sh --verbose api database"
echo

echo "=== Demonstrating a dry run ==="
echo
$SCRIPT_DIR/generate_specs.sh --dry-run api database core

echo
echo "=== To run actual generation, remove --dry-run flag ==="