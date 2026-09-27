import json

from harness.reviewer import review_requirement
from harness.judge import judge_review


requirement = (
    "The system shall lock the account after five consecutive "
    "failed login attempts within 10 minutes."
)

print("\n" + "=" * 70)
print("ORIGINAL REQUIREMENT")
print("=" * 70)
print(requirement)


# Step 1: Reviewer
review = review_requirement(requirement)

print("\n" + "=" * 70)
print("REVIEWER OUTPUT")
print("=" * 70)

print("\nDetected Issues:")

if review.issues:
    for i, issue in enumerate(review.issues, start=1):
        print(f"\n{i}. Criterion: {issue.criterion.upper()}")
        print(f"   Explanation: {issue.explanation}")
else:
    print("No issues detected.")

print("\nImproved Requirement:")
print(review.improved_requirement)


# Step 2: Judge
judgment = judge_review(requirement, review)

print("\n" + "=" * 70)
print("JUDGE OUTPUT")
print("=" * 70)

print(f"\nVerdict: {judgment['verdict']}")
print(f"Explanation: {judgment['explanation']}")

print("\n" + "=" * 70)