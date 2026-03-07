# agents/suggested_questions.py

PUBLIC_QUESTIONS = [
    "Is it safe to go outside tomorrow in South Delhi?",
    "Which area has the best air quality right now?",
    "What does AQI 250 mean for my child?",
    "Will the air get better in the next 3 days?",
    "Should I wear an N95 mask today?",
    "What time of day is safest to go for a walk?",
    "Why is North Delhi more polluted than South Delhi?",
    "What can I do at home to reduce my exposure?",
]

POLICY_QUESTIONS = [
    "Which region needs emergency intervention in the next 3 days?",
    "What is the most impactful single intervention right now?",
    "What GRAP stage is Delhi in based on today's forecast?",
    "Compare AQI reduction across all counterfactual scenarios.",
    "What are the top 3 emission drivers in East Delhi today?",
    "How much would odd-even vehicle restrictions improve AQI?",
    "Which region shows the worst 3-day deterioration trend?",
    "Quantify the benefit of reducing industrial emissions by 30%.",
]

def get_suggested_questions(agent_type: str) -> list:
    if agent_type == "public":
        return PUBLIC_QUESTIONS
    return POLICY_QUESTIONS
