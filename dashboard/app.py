from flask import Flask, render_template, jsonify
from sqlalchemy.orm import Session
from core.database import SessionLocal, Metric, PullRequest, Review
import json

app = Flask(__name__)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/metrics")
def get_metrics():
    db = SessionLocal()
    metrics = db.query(Metric).order_by(Metric.timestamp.desc()).limit(20).all()
    metrics.reverse()
    
    def format_ts(ts):
        if isinstance(ts, str):
            from datetime import datetime
            try:
                return datetime.fromisoformat(ts.split('.')[0]).strftime("%Y-%m-%d %H:%M")
            except:
                return ts
        return ts.strftime("%Y-%m-%d %H:%M")

    data = {
        "labels": [format_ts(m.timestamp) for m in metrics],
        "bugs": [m.bug_count for m in metrics],
        "critical": [m.critical_count for m in metrics]
    }
    db.close()
    return jsonify(data)

@app.route("/api/stats")
def get_stats():
    db = SessionLocal()
    total_prs = db.query(PullRequest).count()
    total_reviews = db.query(Review).count()
    
    # Calculate severity distribution
    reviews = db.query(Review).all()
    severity_dist = {"LOW": 0, "MEDIUM": 0, "CRITICAL": 0}
    for r in reviews:
        if isinstance(r.feedback, list):
            for item in r.feedback:
                sev = item.get("severity", "LOW")
                severity_dist[sev] = severity_dist.get(sev, 0) + 1
    
    db.close()
    return jsonify({
        "total_prs": total_prs,
        "total_reviews": total_reviews,
        "severity_dist": severity_dist
    })

@app.route("/api/prs")
def get_prs():
    db = SessionLocal()
    prs = db.query(PullRequest).order_by(PullRequest.created_at.desc()).all()
    data = []
    for pr in prs:
        # Get the latest review for this PR
        latest_review = db.query(Review).filter(Review.pr_id == pr.id).order_by(Review.created_at.desc()).first()
        data.append({
            "id": pr.id,
            "title": pr.title,
            "author": pr.author,
            "repo": pr.repo_name,
            "status": pr.state,
            "feedback_count": len(latest_review.feedback) if latest_review and latest_review.feedback else 0,
            "feedback": latest_review.feedback if latest_review else []
        })
    db.close()
    return jsonify(data)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
