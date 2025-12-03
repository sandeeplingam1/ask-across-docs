"""Test the improved question parser"""
from backend.app.routes.questions import _parse_questions_from_text

# Test Case 1: Document title should be ignored
test1 = """Sample Governance Questions

1. Has the Organization documented an AUP?
"""
print("═══ Test 1: Ignore Document Title ═══")
questions = _parse_questions_from_text(test1)
print(f"Found {len(questions)} questions:")
for i, q in enumerate(questions, 1):
    print(f"Q{i}: {q[:80]}...")
print()

# Test Case 2: Parent with colon + sub-bullets = ONE question
test2 = """1. Is the Board provided an annual report addressing:
    - Overall GLBA Program Status
    - Material Risk Issues
"""
print("═══ Test 2: Parent with Colon + Sub-bullets ═══")
questions = _parse_questions_from_text(test2)
print(f"Found {len(questions)} questions:")
for i, q in enumerate(questions, 1):
    print(f"Q{i}:\n{q}\n")
print()

# Test Case 3: Parent question with sub-bullets
test3 = """Has the Organization documented an AUP? Additionally consider:
    - Annual Employee Acknowledgement
    - Confidentiality Agreement
"""
print("═══ Test 3: Question with 'Additionally consider:' ═══")
questions = _parse_questions_from_text(test3)
print(f"Found {len(questions)} questions:")
for i, q in enumerate(questions, 1):
    print(f"Q{i}:\n{q}\n")
print()

# Test Case 4: Multiple ? in same line = ONE question
test4 = """1. Has the Org Chart been updated? Does it identify committees?

2. Is MFA enforced? Are exceptions documented?
"""
print("═══ Test 4: Multiple ? in Same Item ═══")
questions = _parse_questions_from_text(test4)
print(f"Found {len(questions)} questions:")
for i, q in enumerate(questions, 1):
    print(f"Q{i}: {q}")
print()

# Test Case 5: Short bullet labels should NOT become questions
test5 = """Does the organization have a privacy policy?
    • Confidentiality Agreement
    • Annual Acknowledgement
"""
print("═══ Test 5: Short Bullets Stay as Sub-points ═══")
questions = _parse_questions_from_text(test5)
print(f"Found {len(questions)} questions:")
for i, q in enumerate(questions, 1):
    print(f"Q{i}:\n{q}\n")
print()

# Test Case 6: Real-world governance document
test6 = """GLBA Compliance Questions

1. Has the Board approved the Information Security Program?

2. Is the Board provided an annual report addressing:
    - Overall GLBA Program Status
    - Material Risk Issues
    - Key Risk Indicators

3. Has the Org Chart been updated? Does it identify all committees?

4. Are vendor risk assessments conducted annually?
    • Third-party reviews
    • SOC 2 reports
"""
print("═══ Test 6: Real-world Document ═══")
questions = _parse_questions_from_text(test6)
print(f"Found {len(questions)} questions:")
for i, q in enumerate(questions, 1):
    print(f"Q{i}:\n{q}\n")
