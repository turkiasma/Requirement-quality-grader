from harness.judge import judge_review


requirement = (
    "The system shall lock the account after five consecutive "
    "failed login attempts within 10 minutes."
)


review = {
    "issues": [
        {
            "criterion": "completeness",
            "explanation": "The requirement does not specify the duration of the account lockout."
        },
        {
            "criterion": "clarity",
            "explanation": "The phrase 'within 10 minutes' may be ambiguous."
        }
    ],
    "improved_requirement": (
        "The system shall lock the account for 30 minutes "
        "after five consecutive failed login attempts occurring "
        "within any 10-minute time window."
    )
}


result = judge_review(requirement, review)

print(result)