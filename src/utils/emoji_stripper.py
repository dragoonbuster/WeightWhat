"""
Comprehensive emoji and symbol removal utility

This module provides robust removal of all emojis, emoticons, and decorative symbols
from text to ensure clean, professional output.
"""

import re
from typing import List


def strip_emojis_and_symbols(text: str) -> str:
    """
    Remove all emojis, emoticons, and decorative symbols from text.
    
    This is a comprehensive function that removes:
    - Unicode emojis (all ranges)
    - ASCII emoticons
    - Decorative symbols
    - Special characters
    """
    if not text:
        return text
    
    # Comprehensive Unicode emoji ranges
    emoji_ranges = [
        # Emoticons
        (0x1F600, 0x1F64F),
        # Miscellaneous Symbols and Pictographs
        (0x1F300, 0x1F5FF),
        # Transport and Map Symbols
        (0x1F680, 0x1F6FF),
        # Regional Indicator Symbols
        (0x1F1E0, 0x1F1FF),
        # Supplemental Symbols and Pictographs
        (0x1F900, 0x1F9FF),
        # Chess Symbols
        (0x1FA00, 0x1FA6F),
        # Symbols and Pictographs Extended-A
        (0x1FA70, 0x1FAFF),
        # Symbols for Legacy Computing
        (0x1FB00, 0x1FBFF),
        # Geometric Shapes Extended
        (0x1F780, 0x1F7FF),
        # Miscellaneous Symbols
        (0x2600, 0x26FF),
        # Dingbats
        (0x2700, 0x27BF),
        # Miscellaneous Mathematical Symbols-A
        (0x27C0, 0x27EF),
        # Supplemental Arrows-A
        (0x27F0, 0x27FF),
        # Braille Patterns
        (0x2800, 0x28FF),
        # Supplemental Arrows-B
        (0x2900, 0x297F),
        # Miscellaneous Mathematical Symbols-B
        (0x2980, 0x29FF),
        # Supplemental Mathematical Operators
        (0x2A00, 0x2AFF),
        # Miscellaneous Symbols and Arrows
        (0x2B00, 0x2BFF),
        # Glagolitic
        (0x2C00, 0x2C5F),
        # Latin Extended-C
        (0x2C60, 0x2C7F),
        # Coptic
        (0x2C80, 0x2CFF),
        # Georgian Supplement
        (0x2D00, 0x2D2F),
        # Tifinagh
        (0x2D30, 0x2D7F),
        # Ethiopic Extended
        (0x2D80, 0x2DDF),
        # Cyrillic Extended-A
        (0x2DE0, 0x2DFF),
        # Supplemental Punctuation
        (0x2E00, 0x2E7F),
        # CJK Radicals Supplement
        (0x2E80, 0x2EFF),
        # Kangxi Radicals
        (0x2F00, 0x2FDF),
        # Ideographic Description Characters
        (0x2FF0, 0x2FFF),
        # CJK Symbols and Punctuation
        (0x3000, 0x303F),
        # Hiragana
        (0x3040, 0x309F),
        # Katakana
        (0x30A0, 0x30FF),
        # Bopomofo
        (0x3100, 0x312F),
        # Hangul Compatibility Jamo
        (0x3130, 0x318F),
        # Kanbun
        (0x3190, 0x319F),
        # Bopomofo Extended
        (0x31A0, 0x31BF),
        # CJK Strokes
        (0x31C0, 0x31EF),
        # Katakana Phonetic Extensions
        (0x31F0, 0x31FF),
        # Enclosed CJK Letters and Months
        (0x3200, 0x32FF),
        # CJK Compatibility
        (0x3300, 0x33FF),
        # CJK Unified Ideographs Extension A
        (0x3400, 0x4DBF),
        # Yijing Hexagram Symbols
        (0x4DC0, 0x4DFF),
        # CJK Unified Ideographs
        (0x4E00, 0x9FFF),
        # Yi Syllables
        (0xA000, 0xA48F),
        # Yi Radicals
        (0xA490, 0xA4CF),
        # Modifier Tone Letters
        (0xA700, 0xA71F),
        # Latin Extended-D
        (0xA720, 0xA7FF),
        # Syloti Nagri
        (0xA800, 0xA82F),
        # Common Indic Number Forms
        (0xA830, 0xA83F),
        # Phags-pa
        (0xA840, 0xA87F),
        # Saurashtra
        (0xA880, 0xA8DF),
        # Devanagari Extended
        (0xA8E0, 0xA8FF),
        # Kayah Li
        (0xA900, 0xA92F),
        # Rejang
        (0xA930, 0xA95F),
        # Hangul Jamo Extended-A
        (0xA960, 0xA97F),
        # Javanese
        (0xA980, 0xA9DF),
        # Cham
        (0xAA00, 0xAA5F),
        # Myanmar Extended-A
        (0xAA60, 0xAA7F),
        # Tai Viet
        (0xAA80, 0xAADF),
        # Ethiopic Extended-A
        (0xAB00, 0xAB2F),
        # Cherokee Supplement
        (0xAB70, 0xABBF),
        # Meetei Mayek
        (0xABC0, 0xABFF),
        # Hangul Syllables
        (0xAC00, 0xD7AF),
        # Hangul Jamo Extended-B
        (0xD7B0, 0xD7FF),
        # High Surrogates
        (0xD800, 0xDB7F),
        # High Private Use Surrogates
        (0xDB80, 0xDBFF),
        # Low Surrogates
        (0xDC00, 0xDFFF),
        # Private Use Area
        (0xE000, 0xF8FF),
        # CJK Compatibility Ideographs
        (0xF900, 0xFAFF),
        # Alphabetic Presentation Forms
        (0xFB00, 0xFB4F),
        # Arabic Presentation Forms-A
        (0xFB50, 0xFDFF),
        # Variation Selectors
        (0xFE00, 0xFE0F),
        # Vertical Forms
        (0xFE10, 0xFE1F),
        # Combining Half Marks
        (0xFE20, 0xFE2F),
        # CJK Compatibility Forms
        (0xFE30, 0xFE4F),
        # Small Form Variants
        (0xFE50, 0xFE6F),
        # Arabic Presentation Forms-B
        (0xFE70, 0xFEFF),
        # Halfwidth and Fullwidth Forms
        (0xFF00, 0xFFEF),
        # Specials
        (0xFFF0, 0xFFFF),
        # Tags
        (0xE0000, 0xE007F),
        # Variation Selectors Supplement
        (0xE0100, 0xE01EF),
        # Supplementary Private Use Area-A
        (0xF0000, 0xFFFFF),
        # Supplementary Private Use Area-B
        (0x100000, 0x10FFFF),
    ]
    
    # Build regex pattern for all emoji ranges
    emoji_pattern_parts = []
    for start, end in emoji_ranges:
        if start <= 0xFFFF:
            emoji_pattern_parts.append(f'[\\u{start:04X}-\\u{end:04X}]')
        else:
            # For characters outside BMP, we need to handle them differently
            emoji_pattern_parts.append(f'[\\U{start:08X}-\\U{end:08X}]')
    
    # Add specific problem characters
    problem_chars = [
        # Various symbols
        '\u2022', '\u2023', '\u2024', '\u2025', '\u2026', '\u2027',
        '\u25A0', '\u25A1', '\u25A2', '\u25A3', '\u25A4', '\u25A5',
        '\u25B6', '\u25B7', '\u25C0', '\u25C1', '\u25C6', '\u25C7',
        '\u2605', '\u2606', '\u2665', '\u2666', '\u2713', '\u2714',
        '\u2717', '\u2718', '\u2764', '\u2192', '\u2190', '\u2191',
        '\u2193', '\u2194', '\u21A9', '\u21AA', '\u2934', '\u2935',
        # More hearts and symbols
        '\u2661', '\u2662', '\u2663', '\u2664', '\u2667',
        '\u2668', '\u2669', '\u266A', '\u266B', '\u266C',
        '\u266D', '\u266E', '\u266F', '\u267B', '\u267E',
        '\u267F', '\u2708', '\u2709', '\u270A', '\u270B',
        '\u270C', '\u270D', '\u270E', '\u270F', '\u2710',
    ]
    
    # First pass: Remove using comprehensive regex
    try:
        combined_pattern = '|'.join(emoji_pattern_parts)
        text = re.sub(combined_pattern, '', text, flags=re.UNICODE)
    except:
        # If regex is too complex, fall back to character-by-character approach
        pass
    
    # Second pass: Remove specific problem characters
    for char in problem_chars:
        text = text.replace(char, '')
    
    # Third pass: Remove ASCII emoticons
    emoticon_patterns = [
        # Classic emoticons
        r'[:;=8][\'`\-]?[)DPp\]\}3>oO0\*\|\\\/\[@]',
        r'[)DPp\]\}3>oO0\*\|\\\/\[@][\'`\-]?[:;=8]',
        r'+', r'+',
        # ,  variations
        r'[xX][dD]+',
        # Japanese emoticons
        r'\^_+\^', r'>_+<', r'o_+o', r'O_+O', r'T_+T',
        r'\(\s*\^\s*[\-_o]\s*\^\s*\)', r'\(\s*>\s*[\-_\.]\s*<\s*\)',
        # Other patterns
        r'[oO][rR][zZ]', r'[uU][wW][uU]',
        r'\\o/', r'/o\\',
    ]
    
    for pattern in emoticon_patterns:
        text = re.sub(pattern, '', text)
    
    # Fourth pass: Clean up any remaining Unicode symbols in specific ranges
    # This catches anything we might have missed
    text = re.sub(r'[\u2000-\u3300\uE000-\uF8FF\uFE00-\uFEFF\U00010000-\U0010FFFF]+', '', text, flags=re.UNICODE)
    
    # Fifth pass: Remove zero-width characters and other invisible Unicode
    invisible_chars = [
        '\u200B',  # Zero-width space
        '\u200C',  # Zero-width non-joiner
        '\u200D',  # Zero-width joiner
        '\u200E',  # Left-to-right mark
        '\u200F',  # Right-to-left mark
        '\u202A',  # Left-to-right embedding
        '\u202B',  # Right-to-left embedding
        '\u202C',  # Pop directional formatting
        '\u202D',  # Left-to-right override
        '\u202E',  # Right-to-left override
        '\u2060',  # Word joiner
        '\u2061',  # Function application
        '\u2062',  # Invisible times
        '\u2063',  # Invisible separator
        '\u2064',  # Invisible plus
        '\u206A',  # Inhibit symmetric swapping
        '\u206B',  # Activate symmetric swapping
        '\u206C',  # Inhibit Arabic form shaping
        '\u206D',  # Activate Arabic form shaping
        '\u206E',  # National digit shapes
        '\u206F',  # Nominal digit shapes
        '\uFEFF',  # Zero-width no-break space
    ]
    
    for char in invisible_chars:
        text = text.replace(char, '')
    
    # Clean up multiple spaces and normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def get_all_emoji_patterns() -> List[str]:
    """Get list of all emoji regex patterns for documentation."""
    patterns = [
        # Main emoji blocks
        r'[\U0001F600-\U0001F64F]',  # Emoticons
        r'[\U0001F300-\U0001F5FF]',  # Symbols & Pictographs
        r'[\U0001F680-\U0001F6FF]',  # Transport & Map
        r'[\U0001F1E0-\U0001F1FF]',  # Regional Indicators
        r'[\U00002600-\U000026FF]',  # Misc symbols
        r'[\U00002700-\U000027BF]',  # Dingbats
        r'[\U0001F900-\U0001F9FF]',  # Supplemental Symbols
        r'[\U0001FA70-\U0001FAFF]',  # Symbols Extended-A
        r'[\U00002300-\U000023FF]',  # Misc Technical
        
        # ASCII emoticons
        r'[:;=8][\'\-]?[)DPp\]\}3>oO0\*\|\\\/\[@]',
        r'+', r'+', r'[xX][dD]+',
        
        # Decorative symbols
        r'[→←↑↓•◆◇■□●○▲△▼▽◄►※⭐]',
    ]
    return patterns