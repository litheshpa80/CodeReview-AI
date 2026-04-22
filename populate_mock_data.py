import datetime
import random
from core.database import SessionLocal, PullRequest, Review, Metric, init_db

def populate():
    db = SessionLocal()
    init_db()

    repos = ["google/guava", "facebook/react", "tensorflow/tensorflow"]
    authors = ["dev_alice", "dev_bob", "dev_charlie"]

    for i in range(10):
        repo = random.choice(repos)
        author = random.choice(authors)
        
        pr = PullRequest(
            github_id=random.randint(100000, 999999),
            repo_name=repo,
            pr_number=i + 1,
            title=f"Feature/Bugfix {i+1}",
            author=author,
            state="closed"
        )
        db.add(pr)
        db.commit()
        db.refresh(pr)

        # Add Review
        feedback = [
            {"severity": "LOW", "comment": "Style issue", "fix_suggestion": "Use camelCase"},
            {"severity": "MEDIUM", "comment": "Potential bug", "fix_suggestion": "Check for null"},
        ]
        if random.random() > 0.7:
            feedback.append({"severity": "CRITICAL", "comment": "Security vulnerability", "fix_suggestion": "Use parameterized query"})

        review = Review(
            pr_id=pr.id,
            review_status="completed",
            feedback=feedback,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=10-i)
        )
        db.add(review)

        # Add Metric
        metric = Metric(
            repo_name=repo,
            bug_count=len(feedback),
            critical_count=sum(1 for f in feedback if f["severity"] == "CRITICAL"),
            avg_review_time=random.randint(20, 120),
            timestamp=datetime.datetime.utcnow() - datetime.timedelta(days=10-i)
        )
        db.add(metric)

    db.commit()
    db.close()
    print("Mock data populated.")

if __name__ == "__main__":
    populate()
