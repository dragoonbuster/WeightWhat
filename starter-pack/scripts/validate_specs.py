#!/usr/bin/env python3
"""
Specification Validation Script

This script validates generated specification documents by checking:
- File sizes (warns if over 50KB)
- Document structure (required sections)
- Table and visual element counts
- Unfilled placeholders
- Overall document quality

Exit codes:
- 0: All validations passed
- 1: Validation failures found
- 2: Script execution error
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ValidationResult:
    """Stores validation results for a single specification file"""
    filename: str
    file_size: int
    size_warning: bool = False
    missing_sections: List[str] = field(default_factory=list)
    table_count: int = 0
    visual_count: int = 0
    placeholders: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if the specification passed all validations"""
        return len(self.errors) == 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0 or self.size_warning


class SpecificationValidator:
    """Validates specification documents against defined criteria"""
    
    # Default configuration
    DEFAULT_CONFIG = {
        "max_file_size_kb": 50,
        "required_sections": [
            "Overview",
            "Requirements",
            "Technical Details",
            "Implementation",
            "Testing"
        ],
        "placeholder_patterns": [
            r"\[TODO\]",
            r"\[PLACEHOLDER\]",
            r"\[INSERT.*?\]",
            r"\[FILL.*?\]",
            r"XXX",
            r"TBD",
            r"<placeholder>",
            r"\{\{.*?\}\}"
        ],
        "table_patterns": [
            r"\|.*\|.*\|",  # Markdown tables
            r"<table>.*?</table>"  # HTML tables
        ],
        "visual_patterns": [
            r"```mermaid",  # Mermaid diagrams
            r"```plantuml",  # PlantUML diagrams
            r"```dot",  # Graphviz
            r"!\[.*?\]\(.*?\)",  # Images
            r"<img.*?>",  # HTML images
            r"```diagram"  # Generic diagram blocks
        ]
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize validator with optional custom configuration"""
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # Compile regex patterns for efficiency
        self.placeholder_regex = [re.compile(p, re.IGNORECASE) 
                                 for p in self.config["placeholder_patterns"]]
        self.table_regex = [re.compile(p, re.MULTILINE | re.DOTALL) 
                           for p in self.config["table_patterns"]]
        self.visual_regex = [re.compile(p, re.MULTILINE | re.DOTALL) 
                            for p in self.config["visual_patterns"]]
    
    def validate_file(self, filepath: Path) -> ValidationResult:
        """Validate a single specification file"""
        result = ValidationResult(filename=str(filepath))
        
        try:
            # Check file existence
            if not filepath.exists():
                result.errors.append(f"File not found: {filepath}")
                return result
            
            # Check file size
            file_size_kb = filepath.stat().st_size / 1024
            result.file_size = int(file_size_kb)
            
            if file_size_kb > self.config["max_file_size_kb"]:
                result.size_warning = True
                result.warnings.append(
                    f"File size ({file_size_kb:.1f}KB) exceeds recommended "
                    f"limit of {self.config['max_file_size_kb']}KB"
                )
            
            # Read file content
            try:
                content = filepath.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                result.errors.append("File is not valid UTF-8 encoded text")
                return result
            
            # Validate structure
            missing_sections = self._check_required_sections(content)
            if missing_sections:
                result.missing_sections = missing_sections
                result.errors.append(
                    f"Missing required sections: {', '.join(missing_sections)}"
                )
            
            # Count tables and visuals
            result.table_count = self._count_elements(content, self.table_regex)
            result.visual_count = self._count_elements(content, self.visual_regex)
            
            # Check for placeholders
            placeholders = self._find_placeholders(content)
            if placeholders:
                result.placeholders = placeholders
                result.warnings.append(
                    f"Found {len(placeholders)} unfilled placeholder(s)"
                )
            
            # Additional quality checks
            self._perform_quality_checks(content, result)
            
        except Exception as e:
            result.errors.append(f"Validation error: {str(e)}")
        
        return result
    
    def _check_required_sections(self, content: str) -> List[str]:
        """Check for required sections in the document"""
        missing = []
        content_lower = content.lower()
        
        for section in self.config["required_sections"]:
            # Check for various heading formats
            patterns = [
                f"# {section}",  # H1
                f"## {section}",  # H2
                f"### {section}",  # H3
                f"**{section}**",  # Bold
                f"__{section}__",  # Bold alt
                f"{section}:",  # Colon format
                f"{section}\n---",  # Underlined
                f"{section}\n==="  # Underlined alt
            ]
            
            found = any(
                re.search(pattern, content, re.IGNORECASE | re.MULTILINE) 
                for pattern in patterns
            )
            
            if not found:
                missing.append(section)
        
        return missing
    
    def _count_elements(self, content: str, patterns: List[re.Pattern]) -> int:
        """Count occurrences of elements matching given patterns"""
        count = 0
        for pattern in patterns:
            matches = pattern.findall(content)
            count += len(matches)
        return count
    
    def _find_placeholders(self, content: str) -> List[str]:
        """Find all unfilled placeholders in the content"""
        placeholders = []
        found_positions = set()  # Track positions to avoid duplicates
        
        for pattern in self.placeholder_regex:
            for match in pattern.finditer(content):
                position = match.start()
                if position not in found_positions:
                    found_positions.add(position)
                    # Extract context around placeholder
                    start = max(0, position - 20)
                    end = min(len(content), position + len(match.group()) + 20)
                    context = content[start:end].strip()
                    placeholders.append(f"{match.group()} (context: ...{context}...)")
        
        return placeholders
    
    def _perform_quality_checks(self, content: str, result: ValidationResult):
        """Perform additional quality checks on the document"""
        lines = content.split('\n')
        
        # Check for very short documents
        if len(lines) < 50:
            result.warnings.append(
                f"Document seems too short ({len(lines)} lines). "
                "Consider adding more detail."
            )
        
        # Check for sections with minimal content
        section_pattern = re.compile(r'^#+\s+(.+)$', re.MULTILINE)
        sections = section_pattern.findall(content)
        
        for i, section in enumerate(sections[:-1]):
            # Find content between this section and the next
            section_start = content.find(f"# {section}")
            if section_start == -1:
                section_start = content.find(f"## {section}")
            if section_start == -1:
                section_start = content.find(f"### {section}")
            
            if i + 1 < len(sections):
                next_section = sections[i + 1]
                section_end = content.find(f"# {next_section}", section_start + 1)
                if section_end == -1:
                    section_end = content.find(f"## {next_section}", section_start + 1)
                if section_end == -1:
                    section_end = content.find(f"### {next_section}", section_start + 1)
            else:
                section_end = len(content)
            
            if section_start != -1 and section_end != -1:
                section_content = content[section_start:section_end].strip()
                # Count non-empty lines
                content_lines = [l for l in section_content.split('\n')[1:] 
                               if l.strip() and not l.strip().startswith('#')]
                
                if len(content_lines) < 3:
                    result.warnings.append(
                        f"Section '{section}' has minimal content "
                        f"({len(content_lines)} lines)"
                    )
        
        # Check for broken links
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
        for match in link_pattern.finditer(content):
            link_text, link_url = match.groups()
            if link_url.startswith('#'):
                # Internal link - check if anchor exists
                anchor = link_url[1:].lower().replace(' ', '-')
                if anchor not in content.lower():
                    result.warnings.append(
                        f"Possible broken internal link: [{link_text}]({link_url})"
                    )
        
        # Check for consistent formatting
        if content.count('```') % 2 != 0:
            result.warnings.append("Unclosed code block detected")
        
        # Check for tables without headers
        table_lines = [l for l in lines if '|' in l and l.strip().startswith('|')]
        for i, line in enumerate(table_lines):
            if i + 1 < len(lines) and '---' not in lines[i + 1]:
                result.warnings.append(
                    f"Possible table without header separator at line {i + 1}"
                )


def validate_directory(directory: Path, validator: SpecificationValidator,
                      pattern: str = "*.md") -> List[ValidationResult]:
    """Validate all specification files in a directory"""
    results = []
    
    for filepath in sorted(directory.glob(pattern)):
        if filepath.is_file():
            print(f"Validating: {filepath.name}")
            result = validator.validate_file(filepath)
            results.append(result)
    
    return results


def generate_report(results: List[ValidationResult], output_format: str = "text") -> str:
    """Generate a validation report from results"""
    if output_format == "json":
        return generate_json_report(results)
    else:
        return generate_text_report(results)


def generate_text_report(results: List[ValidationResult]) -> str:
    """Generate a human-readable text report"""
    report = []
    report.append("=" * 80)
    report.append("SPECIFICATION VALIDATION REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")
    
    # Summary statistics
    total_files = len(results)
    valid_files = sum(1 for r in results if r.is_valid)
    files_with_warnings = sum(1 for r in results if r.has_warnings)
    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) + (1 if r.size_warning else 0) 
                        for r in results)
    
    report.append("SUMMARY")
    report.append("-" * 40)
    report.append(f"Total files validated: {total_files}")
    report.append(f"Valid files: {valid_files}")
    report.append(f"Files with errors: {total_files - valid_files}")
    report.append(f"Files with warnings: {files_with_warnings}")
    report.append(f"Total errors: {total_errors}")
    report.append(f"Total warnings: {total_warnings}")
    report.append("")
    
    # Detailed results
    report.append("DETAILED RESULTS")
    report.append("-" * 40)
    
    for result in results:
        report.append(f"\nFile: {result.filename}")
        report.append(f"Size: {result.file_size}KB")
        report.append(f"Tables: {result.table_count}")
        report.append(f"Visuals: {result.visual_count}")
        
        if result.is_valid and not result.has_warnings:
            report.append("Status: PASSED ✓")
        elif result.is_valid:
            report.append("Status: PASSED WITH WARNINGS")
        else:
            report.append("Status: FAILED ✗")
        
        if result.errors:
            report.append("\n  Errors:")
            for error in result.errors:
                report.append(f"    - {error}")
        
        if result.warnings or result.size_warning:
            report.append("\n  Warnings:")
            for warning in result.warnings:
                report.append(f"    - {warning}")
        
        if result.placeholders:
            report.append(f"\n  Placeholders found ({len(result.placeholders)}):")
            for i, placeholder in enumerate(result.placeholders[:5]):  # Show first 5
                report.append(f"    - {placeholder}")
            if len(result.placeholders) > 5:
                report.append(f"    ... and {len(result.placeholders) - 5} more")
        
        report.append("-" * 40)
    
    return "\n".join(report)


def generate_json_report(results: List[ValidationResult]) -> str:
    """Generate a JSON report for programmatic consumption"""
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_files": len(results),
            "valid_files": sum(1 for r in results if r.is_valid),
            "files_with_warnings": sum(1 for r in results if r.has_warnings),
            "total_errors": sum(len(r.errors) for r in results),
            "total_warnings": sum(len(r.warnings) + (1 if r.size_warning else 0) 
                                for r in results)
        },
        "results": []
    }
    
    for result in results:
        report_data["results"].append({
            "filename": result.filename,
            "file_size_kb": result.file_size,
            "is_valid": result.is_valid,
            "has_warnings": result.has_warnings,
            "table_count": result.table_count,
            "visual_count": result.visual_count,
            "errors": result.errors,
            "warnings": result.warnings,
            "missing_sections": result.missing_sections,
            "placeholder_count": len(result.placeholders),
            "placeholders": result.placeholders[:10]  # Limit to first 10
        })
    
    return json.dumps(report_data, indent=2)


def main():
    """Main entry point for the validation script"""
    parser = argparse.ArgumentParser(
        description="Validate specification documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
  0 - All validations passed
  1 - Validation failures found
  2 - Script execution error

Examples:
  %(prog)s specs/
  %(prog)s specs/ --output-format json
  %(prog)s specs/API_SPEC.md --config custom_config.json
  %(prog)s specs/ --pattern "*_SPEC.md" --report validation_report.txt
        """
    )
    
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a specification file or directory to validate"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to custom configuration JSON file"
    )
    
    parser.add_argument(
        "--pattern",
        default="*.md",
        help="File pattern to match (default: *.md)"
    )
    
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format for the report (default: text)"
    )
    
    parser.add_argument(
        "--report",
        type=Path,
        help="Save report to file (prints to stdout if not specified)"
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code 1 if any warnings are found"
    )
    
    args = parser.parse_args()
    
    try:
        # Load custom configuration if provided
        config = None
        if args.config:
            if not args.config.exists():
                print(f"Error: Configuration file not found: {args.config}")
                sys.exit(2)
            
            try:
                with open(args.config) as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in configuration file: {e}")
                sys.exit(2)
        
        # Create validator
        validator = SpecificationValidator(config)
        
        # Validate files
        if args.path.is_file():
            results = [validator.validate_file(args.path)]
        elif args.path.is_dir():
            results = validate_directory(args.path, validator, args.pattern)
        else:
            print(f"Error: Path not found: {args.path}")
            sys.exit(2)
        
        if not results:
            print(f"No files found matching pattern: {args.pattern}")
            sys.exit(2)
        
        # Generate report
        report = generate_report(results, args.output_format)
        
        # Output report
        if args.report:
            args.report.write_text(report)
            print(f"Report saved to: {args.report}")
        else:
            print(report)
        
        # Determine exit code
        has_errors = any(not r.is_valid for r in results)
        has_warnings = any(r.has_warnings for r in results)
        
        if has_errors:
            sys.exit(1)
        elif has_warnings and args.strict:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()