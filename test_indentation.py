#!/usr/bin/env python3
"""Test DOCX indentation preservation"""

# Simulate what the DOCX reader should produce with indentation levels
# Level 0 = top-level bullet (•)
# Level 1 = nested bullet (o)

test_text_with_indentation = """Does the Board of Directors approve the Information Security Program/Policy?
Does a documented IT Committee Charter (or related document) exist outlining the roles and responsibilities of the IT Committee and its members?
Has an individual been formally designated as the Information Technology/Security Officer?
Does the IT Committee document regular discussions related to cyber events?
Has an Organizational Chart been documented, and is it updated regularly (or since the most recent significant organizational change)? Does the Organizational Chart identify major committees (such as IT Committee, Board of Directors, Audit Committee, Management Committee, etc.)?
Has an IT Strategic Plan been documented? If so, does the Plan address short-term and long-term IT goals?
Is the Board of Directors provided an annual report of the overall status of the Information Security Program and all (GLBA) related activities, specifically addressing the following areas:
    Overall GLBA Program Status
    Material Risk Issues
    Risk Assessment
    Risk Management and Control Decisions
    Service Provider Oversight
    Results of Testing
    Security Breaches or Lack of Breaches
    Program Changes
    Cybersecurity
    Patch Management (FIL 43-2003)
Has the Organization documented a formal Acceptable Use Policy, outlining what general practices are allowed and disallowed for employees? Additionally, has the Organization considered the following in regards to the AUP:
    Annual Employee Acknowledgement
    Confidentiality or Nondisclosure Agreement (could be included in handbook or code of ethics)
    Social Media Use (or separate policy) - should address use while at work and outside of work
    Clear Desk / Clear Screen Policy"""

# Import the parser from test file
import sys
sys.path.insert(0, '/home/sandeep.lingam/app-project/Audit-App')

from test_nested_bullets import _parse_questions_from_text

questions = _parse_questions_from_text(test_text_with_indentation)

print(f"\n{'='*70}")
print(f"TOTAL QUESTIONS PARSED: {len(questions)}")
print(f"{'='*70}\n")

for i, q in enumerate(questions, 1):
    print(f"Q{i}: {q}")
    print(f"{'-'*70}\n")

print("\n✅ SUCCESS CRITERIA:")
print(f"{'='*70}")
print("Should parse 8 questions (not 10!)")
print("Q7 should have 10 sub-bullets")
print("Q8 should have 4 sub-bullets")
print("No Q9 or Q10 (they should be sub-bullets of Q8)")
