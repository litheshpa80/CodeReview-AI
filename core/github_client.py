import requests
import base64

class GitHubClient:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"

    def list_repositories(self):
        """Lists all repositories for the authenticated user."""
        url = f"{self.base_url}/user/repos?sort=updated&per_page=10"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []

    def get_repo_contents(self, owner, repo, path=""):
        """Gets the contents of a directory in a repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []

    def get_file_content(self, owner, repo, path):
        """Gets the content of a specific file."""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8")
        return None
