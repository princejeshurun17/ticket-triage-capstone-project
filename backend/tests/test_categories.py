from shared.categories import suggest_category


def test_it_support_keywords():
    category, confidence = suggest_category("Cannot access campus Wi-Fi", "My laptop won't connect from the dorm.")
    assert category == "IT Support"
    assert confidence > 0.3


def test_library_beats_generic_loan_word():
    category, _ = suggest_category("Book loan overdue", "I need to renew a library book loan before the fine grows.")
    assert category == "Library Services"


def test_student_finance_beats_generic_loan_word():
    category, _ = suggest_category("Student loan question", "My student loan disbursement has not arrived.")
    assert category == "Student Finance"


def test_no_match_falls_back_to_general_enquiry():
    category, confidence = suggest_category("Hello", "Just saying hi, no real issue.")
    assert category == "General Enquiry"
    assert confidence == 0.3
