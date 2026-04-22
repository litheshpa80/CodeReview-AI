from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import hmac
import hashlib
import json
import os
import requests
from dotenv import load_dotenv

from core.database import SessionLocal, PullRequest, Review, Metric, init_db
from core.llm_engine import LLMEngine
from core.github_client import GitHubClient
from fastapi import BackgroundTasks

load_dotenv()

app = FastAPI(title="CodeReview AI - Webhook Listener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For local dev, we can allow all or specific port 5000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "CodeReview AI webhook listener",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "supersecret")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
llm_engine = LLMEngine(provider=os.getenv("LLM_PROVIDER", "openai"))

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_signature(payload: bytes, signature: str):
    if not signature:
        return False
    sha_name, signature = signature.split('=')
    if sha_name != 'sha256':
        return False
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    db: Session = Depends(get_db)
):
    payload = await request.body()
    
    if not verify_signature(payload, x_hub_signature_256 or ""):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event_data = json.loads(payload)
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "pull_request":
        action = event_data.get("action")
        if action in ["opened", "reopened", "synchronize"]:
            pr_data = event_data["pull_request"]
            repo_full_name = event_data["repository"]["full_name"]
            pr_number = pr_data["number"]
            diff_url = pr_data["diff_url"]

            # Store or Update PR in DB
            pr = db.query(PullRequest).filter(PullRequest.github_id == pr_data["id"]).first()
            if not pr:
                pr = PullRequest(
                    github_id=pr_data["id"],
                    repo_name=repo_full_name,
                    pr_number=pr_number,
                    title=pr_data["title"],
                    author=pr_data["user"]["login"],
                    state=pr_data["state"]
                )
                db.add(pr)
                db.commit()
                db.refresh(pr)

            # 1. Fetch Diff
            headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
            mock_diff = event_data.get("mock_diff")
            if mock_diff:
                diff_text = mock_diff
            else:
                diff_response = requests.get(diff_url, headers=headers)
                if diff_response.status_code != 200:
                    return {"status": "error", "message": "Failed to fetch diff"}
                diff_text = diff_response.text

            # 2. Analyze Diff
            feedback = llm_engine.analyze_diff(diff_text)

            # 3. Store Review
            review = Review(
                pr_id=pr.id,
                review_status="completed",
                feedback=feedback
            )
            db.add(review)
            
            # 4. Update Metrics (Simplified)
            bug_count = sum(1 for f in feedback if f.get("severity") in ["MEDIUM", "CRITICAL"])
            critical_count = sum(1 for f in feedback if f.get("severity") == "CRITICAL")
            
            metric = Metric(
                repo_name=repo_full_name,
                bug_count=bug_count,
                critical_count=critical_count,
                avg_review_time=30 # Placeholder
            )
            db.add(metric)
            db.commit()

            # 5. Post Comments to GitHub (Inline or Single Comment)
            if GITHUB_TOKEN:
                comment_url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
                comment_body = "### CodeReview AI Feedback\n\n"
                for item in feedback:
                    comment_body += f"- **{item['severity']}**: {item['comment']}\n  - *Suggestion*: `{item['fix_suggestion']}`\n"
                
                requests.post(comment_url, headers=headers, json={"body": comment_body})

            return {"status": "success", "review_id": review.id}

    return {"status": "ignored"}

async def perform_bulk_scan(token: str, db: Session):
    client = GitHubClient(token)
    repos = client.list_repositories()
    
    for repo in repos:
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        full_name = repo["full_name"]
        
        # Check if we already have a PullRequest entry for this repo-scan
        pr_title = f"Bulk Scan: {repo_name}"
        pr = db.query(PullRequest).filter(PullRequest.title == pr_title).first()
        if not pr:
            pr = PullRequest(
                github_id=repo["id"], # Using repo ID as github_id for bulk scans
                repo_name=full_name,
                pr_number=0, # 0 indicates bulk scan
                title=pr_title,
                author=owner,
                state="completed"
            )
            db.add(pr)
            db.commit()
            db.refresh(pr)
        
        # Scan root files
        contents = client.get_repo_contents(owner, repo_name)
        all_feedback = []
        for item in contents:
            if item["type"] == "file" and item["name"].endswith((".py", ".js", ".ts")):
                content = client.get_file_content(owner, repo_name, item["path"])
                if content:
                    feedback = llm_engine.analyze_code(content, item["name"])
                    all_feedback.extend(feedback)
        
        if all_feedback:
            review = Review(
                pr_id=pr.id,
                review_status="completed",
                feedback=all_feedback
            )
            db.add(review)
            
            # Update metrics
            bug_count = sum(1 for f in all_feedback if f.get("severity") in ["MEDIUM", "CRITICAL"])
            critical_count = sum(1 for f in all_feedback if f.get("severity") == "CRITICAL")
            
            metric = Metric(
                repo_name=full_name,
                bug_count=bug_count,
                critical_count=critical_count,
                avg_review_time=60
            )
            db.add(metric)
            db.commit()

@app.post("/api/bulk-scan")
async def start_bulk_scan(
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    body = await request.json()
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
    
    background_tasks.add_task(perform_bulk_scan, token, db)
    return {"status": "started", "message": "Bulk scan initiated in background"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
