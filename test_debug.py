#!/usr/bin/env python3
"""Debug nested bullet parsing"""

import re

def _parse_questions_from_text_debug(text: str) -> list[str]:
    """Parse with debug output"""
    import re
    
    lines = text.split('\n')
    questions = []
    current_question = None
    current_subpoints = []
    
    question_words = r'\b(does|has|is|are|was|were|do|did|have|can|could|should|would|will|' \
                     r'provide|describe|explain|list|identify|document|what|when|where|who|why|how)\b'
    
    bullet_pattern = r'^[-*•o◦○▪▫✓✔➢➣➤►▶]+[\s\t]+'
    number_pattern = r'^(\d+[.):\-]|[A-Z][.):]|[a-z][.):]|[ivxIVX]+[.):])\s+'
    
    print("\n" + "="*70)
    print("LINE-BY-LINE ANALYSIS")
    print("="*70)
    
    for line_num, line in enumerate(lines, 1):
        if not line.strip():
            continue
        
        stripped = line.strip()
        leading_spaces = len(line) - len(line.lstrip())
        
        cleaned = re.sub(number_pattern, '', stripped)
        cleaned = re.sub(bullet_pattern, '', cleaned)
        cleaned = cleaned.strip()
        
        word_count = len(cleaned.split())
        
        has_question_mark = '?' in stripped
        ends_with_colon = stripped.endswith(':')
        ends_with_question = stripped.endswith('?')
        starts_with_question_word = re.search(question_words, cleaned, re.IGNORECASE) is not None
        
        print(f"\nLine {line_num}: {stripped[:60]}...")
        print(f"  Leading spaces: {leading_spaces}")
        print(f"  Cleaned: {cleaned[:50]}...")
        print(f"  Word count: {word_count}")
        
        is_title = (
            not has_question_mark 
            and not ends_with_colon 
            and not starts_with_question_word
            and word_count < 5
        )
        
        if word_count < 3 and not ends_with_question and not ends_with_colon:
            is_title = True
        
        if is_title:
            print(f"  → IGNORED (title)")
            continue
        
        is_subpoint = False
        
        if current_question:
            is_nested_bullet = bool(re.match(r'^[o◦▪▫]+[\s\t]+', stripped))
            is_top_bullet = bool(re.match(r'^[•\-*]+[\s\t]+', stripped))
            
            print(f"  Nested bullet: {is_nested_bullet}, Top bullet: {is_top_bullet}")
            
            if leading_spaces >= 8:
                is_subpoint = True
                print(f"  → SUBPOINT (heavy indent)")
            elif is_nested_bullet:
                is_subpoint = True
                print(f"  → SUBPOINT (nested bullet)")
            elif leading_spaces >= 4 and len(cleaned) < 40 and not ends_with_question:
                is_subpoint = True
                print(f"  → SUBPOINT (moderate indent + fragment)")
            elif len(cleaned) < 30 and not ends_with_question and not starts_with_question_word:
                is_subpoint = True
                print(f"  → SUBPOINT (short fragment)")
        
        is_parent = False
        
        if not is_subpoint:
            if ends_with_question or ends_with_colon:
                is_parent = True
                print(f"  → PARENT (ends with ? or :)")
            elif starts_with_question_word and len(cleaned) > 20 and leading_spaces < 8:
                is_parent = True
                print(f"  → PARENT (question word + substance)")
            elif has_question_mark and len(cleaned) > 15:
                is_parent = True
                print(f"  → PARENT (has ?)")
        
        if is_parent:
            has_own_numbering = bool(re.match(number_pattern, stripped))
            
            if current_question and not has_own_numbering and leading_spaces >= 4:
                current_question += ' ' + stripped
                print(f"  → CONTINUATION of current question")
            else:
                if current_question:
                    question_text = current_question
                    if current_subpoints:
                        question_text += '\n' + '\n'.join([f"    - {sp}" for sp in current_subpoints])
                    questions.append(question_text)
                    print(f"  → SAVED previous question with {len(current_subpoints)} subpoints")
                
                current_question = stripped
                current_subpoints = []
                print(f"  → NEW PARENT QUESTION")
        
        elif is_subpoint and current_question:
            subpoint = stripped
            
            prev_subpoint = ""
            while prev_subpoint != subpoint:
                prev_subpoint = subpoint
                subpoint = re.sub(number_pattern, '', subpoint)
                subpoint = re.sub(bullet_pattern, '', subpoint)
                subpoint = subpoint.strip()
            
            if subpoint and len(subpoint) > 2:
                current_subpoints.append(subpoint)
                print(f"  → ADDED subpoint: {subpoint[:40]}...")
            else:
                print(f"  → SKIPPED (too short after cleaning)")
    
    if current_question:
        question_text = current_question
        if current_subpoints:
            question_text += '\n' + '\n'.join([f"    - {sp}" for sp in current_subpoints])
        questions.append(question_text)
    
    cleaned_questions = []
    for q in questions:
        q = q.strip()
        if len(q) > 10:
            cleaned_questions.append(q)
    
    return cleaned_questions


# Test with Q7 specifically
test_text = """•	Is the Board of Directors provided an annual report of the overall status of the Information Security Program and all (GLBA) related activities, specifically addressing the following areas: 
o	• Overall GLBA Program Status 
o	• Material Risk Issues
o	• Risk Assessment 
o	• Risk Management and Control Decisions 
o	• Service Provider Oversight 
o	• Results of Testing 
o	• Security Breaches or Lack of Breaches
o	• Program Changes 
o	• Cybersecurity
o	• Patch Management (FIL 43-2003)"""

questions = _parse_questions_from_text_debug(test_text)

print(f"\n{'='*70}")
print(f"FINAL RESULT:")
print(f"{'='*70}\n")

for i, q in enumerate(questions, 1):
    print(f"Q{i}: {q}\n")
