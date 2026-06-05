"""
Utility functions for text formatting and Unicode conversion.
Used to simulate bold/italic on LinkedIn.
"""

def text_to_unicode_bold(text: str) -> str:
    """
    Convert ASCII text to Unicode Mathematical Sans-Serif Bold.
    A-Z: U+1D5D4 - U+1D5ED
    a-z: U+1D5EE - U+1D607
    
    NOTE: Digits (0-9) are intentionally LEFT as plain ASCII.
    LinkedIn does NOT render Mathematical Sans-Serif Bold digits
    (U+1D7EC-U+1D7F5) — they appear as empty boxes or invisible
    characters, which breaks CVE numbers (e.g., CVE-2025-5042)
    and other critical numeric data.
    """
    if not text:
        return text
        
    result = ""
    for char in text:
        codepoint = ord(char)
        if 65 <= codepoint <= 90:  # A-Z
            result += chr(codepoint + 120211)
        elif 97 <= codepoint <= 122:  # a-z
            result += chr(codepoint + 120205)
        else:
            # Digits, hyphens, punctuation — keep as-is for LinkedIn compatibility
            result = result + char
    return result

def text_to_unicode_italic(text: str) -> str:
    """
    Convert ASCII text to Unicode Mathematical Sans-Serif Italic.
    A-Z: U+1D608 - U+1D621
    a-z: U+1D622 - U+1D63B
    """
    if not text:
        return text
        
    result = ""
    for char in text:
        codepoint = ord(char)
        if 65 <= codepoint <= 90:  # A-Z
            result += chr(codepoint + 120263)
        elif 97 <= codepoint <= 122:  # a-z
            result += chr(codepoint + 120257)
        else:
            result = result + char
    return result

if __name__ == "__main__":
    test_text = "Hello 123 World!"
    print(f"Original: {test_text}")
    print(f"Bold:     {text_to_unicode_bold(test_text)}")
    print(f"Italic:   {text_to_unicode_italic(test_text)}")
