"""
Utility functions for text formatting and Unicode conversion.
Used to simulate bold/italic on LinkedIn.
"""

def text_to_unicode_bold(text: str) -> str:
    """
    Convert ASCII text to Unicode Mathematical Sans-Serif Bold.
    A-Z: U+1D5D4 - U+1D5ED
    a-z: U+1D5EE - U+1D607
    0-9: U+1D7EC - U+1D7F5
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
        elif 48 <= codepoint <= 57:  # 0-9
            result += chr(codepoint + 120796)
        else:
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
