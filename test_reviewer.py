from harness.reviewer import review_requirement


requirement = (
    "The system shall lock the account after five consecutive "
    "failed login attempts within 10 minutes."
)

result = review_requirement(requirement)

print(result.model_dump_json(indent=2))