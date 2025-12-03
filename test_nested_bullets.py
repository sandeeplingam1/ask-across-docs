#!/usr/bin/env python3
"""Test nested bullet parsing"""

import re

def _parse_questions_from_text(text: str) -> list[str]:
    """
    Parse audit questions from text with EXACT human auditor understanding.
    """
    import re
    
    lines = text.split('\n')
    questions = []
    current_question = None
    current_subpoints = []
    
    # Question word patterns (case-insensitive)
    question_words = r'\b(does|has|is|are|was|were|do|did|have|can|could|should|would|will|' \
                     r'provide|describe|explain|list|identify|document|what|when|where|who|why|how)\b'
    
    # Bullet patterns (comprehensive) - handle bullets with space OR tab OR multiple bullets
    bullet_pattern = r'^[-*•o◦○▪▫✓✔➢➣➤►▶]+[\s\t]+'
    
    # Number patterns: 1. 1) 1: 1- I. A.) a. etc.
    number_pattern = r'^(\d+[.):\-]|[A-Z][.):]|[a-z][.):]|[ivxIVX]+[.):])\s+'
    
    for line in lines:
        if not line.strip():
            continue
        
        stripped = line.strip()
        leading_spaces = len(line) - len(line.lstrip())
        
        # Clean line by removing numbering/bullets for content analysis
        cleaned = re.sub(number_pattern, '', stripped)
        cleaned = re.sub(bullet_pattern, '', cleaned)
        cleaned = cleaned.strip()
        
        # Word count for filtering
        word_count = len(cleaned.split())
        
        has_question_mark = '?' in stripped
        ends_with_colon = stripped.endswith(':')
        ends_with_question = stripped.endswith('?')
        starts_with_question_word = re.search(question_words, cleaned, re.IGNORECASE) is not None
        
        # Check if this could be a sub-point (nested bullet or heavy indent)
        could_be_subpoint = bool(re.match(r'^[o◦▪▫]+[\s\t]+', stripped)) or leading_spaces >= 8
        
        # Ignore if it's clearly a title/label AND not a potential sub-point
        is_title = (
            not has_question_mark 
            and not ends_with_colon 
            and not starts_with_question_word
            and word_count < 5
            and not (current_question and could_be_subpoint)  # Don't ignore potential sub-points!
        )
        
        # Also ignore very short fragments without structure (unless potential sub-point)
        if word_count < 3 and not ends_with_question and not ends_with_colon and not could_be_subpoint:
            is_title = True
        
        if is_title:
            continue
        
        is_subpoint = False
        
        if current_question:
            # Check for NESTED bullets (o, ◦) vs TOP-LEVEL bullets (•, -, *)
            is_nested_bullet = bool(re.match(r'^[o◦▪▫]+[\s\t]+', stripped))
            is_top_bullet = bool(re.match(r'^[•\-*]+[\s\t]+', stripped))
            
            # Check if parent ended with colon (expecting sub-list)
            parent_expects_sublist = current_question.rstrip().endswith(':')
            
            # Check 1: Heavily indented (8+ spaces = definitely a sub-point)
            if leading_spaces >= 8:
                is_subpoint = True
            
            # Check 2: Nested bullet (o, ◦)
            elif is_nested_bullet:
                is_subpoint = True
            
            # Check 3: Moderate indent (4+ spaces) 
            elif leading_spaces >= 4:
                if parent_expects_sublist:
                    is_subpoint = True  # Parent expects list, all indented lines are sub-points
                elif len(cleaned) < 40 and not ends_with_question:
                    is_subpoint = True
            
            # Check 4: Short fragment without question structure
            elif len(cleaned) < 30 and not ends_with_question and not starts_with_question_word:
                is_subpoint = True
        
        is_parent = False
        
        if not is_subpoint:
            if ends_with_question or ends_with_colon:
                is_parent = True
            elif starts_with_question_word and len(cleaned) > 20 and leading_spaces < 8:
                is_parent = True
            elif has_question_mark and len(cleaned) > 15:
                is_parent = True
        
        if is_parent:
            has_own_numbering = re.match(number_pattern, stripped)
            
            if current_question and not has_own_numbering and leading_spaces >= 4:
                current_question += ' ' + stripped
            else:
                if current_question:
                    question_text = current_question
                    if current_subpoints:
                        question_text += '\n' + '\n'.join([f"    - {sp}" for sp in current_subpoints])
                    questions.append(question_text)
                
                # Start new question - clean it
                new_question = stripped
                prev_q = ""
                while prev_q != new_question:
                    prev_q = new_question
                    new_question = re.sub(number_pattern, '', new_question)
                    new_question = re.sub(bullet_pattern, '', new_question)
                    new_question = new_question.strip()
                
                current_question = new_question
                current_subpoints = []
        
        elif is_subpoint and current_question:
            subpoint = stripped
            
            # Remove all leading bullets and numbers (handle nested: o • text)
            prev_subpoint = ""
            while prev_subpoint != subpoint:
                prev_subpoint = subpoint
                subpoint = re.sub(number_pattern, '', subpoint)
                subpoint = re.sub(bullet_pattern, '', subpoint)
                subpoint = subpoint.strip()
            
            if subpoint and len(subpoint) > 2:
                current_subpoints.append(subpoint)
    
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


# Test with the exact document content
test_text = """Sample Governance Questions
•	Does the Board of Directors approve the Information Security Program/Policy?
•	Does a documented IT Committee Charter (or related document) exist outlining the roles and responsibilities of the IT Committee and its members?
•	Has an individual been formally designated as the Information Technology/Security Officer?
•	Does the IT Committee document regular discussions related to cyber events?
•	Has an Organizational Chart been documented, and is it updated regularly (or since the most recent significant organizational change)? Does the Organizational Chart identify major committees (such as IT Committee, Board of Directors, Audit Committee, Management Committee, etc.)?
•	Has an IT Strategic Plan been documented? If so, does the Plan address short-term and long-term IT goals?
•	Is the Board of Directors provided an annual report of the overall status of the Information Security Program and all (GLBA) related activities, specifically addressing the following areas: 
o	• Overall GLBA Program Status 
o	• Material Risk Issues
o	• Risk Assessment 
o	• Risk Management and Control Decisions 
o	• Service Provider Oversight 
o	• Results of Testing 
o	• Security Breaches or Lack of Breaches
o	• Program Changes 
o	• Cybersecurity
o	• Patch Management (FIL 43-2003)
•	Has the Organization documented a formal Acceptable Use Policy, outlining what general practices are allowed and disallowed for employees? Additionally, has the Organization considered the following in regards to the AUP:
o	• Annual Employee Acknowledgement
o	• Confidentiality or Nondisclosure Agreement (could be included in handbook or code of ethics)
o	• Social Media Use (or separate policy) - should address use while at work and outside of work
o	• Clear Desk / Clear Screen Policy"""

questions = _parse_questions_from_text(test_text)

print(f"\n{'='*70}")
print(f"TOTAL QUESTIONS PARSED: {len(questions)}")
print(f"{'='*70}\n")

for i, q in enumerate(questions, 1):
    print(f"Q{i}: {q}")
    print(f"{'-'*70}\n")
