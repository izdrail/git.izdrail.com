from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import httpx
import base64
from typing import Optional
import json

app = FastAPI(title="GitHub Pull Request Creator API", version="1.0.0")

class PullRequestRequest(BaseModel):
    owner: str
    repo: str
    base: str = "main"
    branch_name: str
    title: str
    body: str
    file_path: str
    file_content: str

class GitHubPullRequestCreator:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FastAPI-GitHub-PR-Creator"
        }
        self.base_url = "https://api.github.com"

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        base: str,
        branch_name: str,
        title: str,
        body: str,
        file_path: str,
        file_content: str
    ) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                # 1) Get the base ref and SHA
                base_ref_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/git/refs/heads/{base}",
                    headers=self.headers
                )
                base_ref_response.raise_for_status()
                base_ref = base_ref_response.json()
                base_sha = base_ref["object"]["sha"]

                # 2) Create the branch ref
                create_ref_response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/git/refs",
                    headers=self.headers,
                    json={
                        "ref": f"refs/heads/{branch_name}",
                        "sha": base_sha
                    }
                )
                create_ref_response.raise_for_status()

                # 3) Create blob for the file
                blob_response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/git/blobs",
                    headers=self.headers,
                    json={
                        "content": file_content,
                        "encoding": "utf-8"
                    }
                )
                blob_response.raise_for_status()
                blob = blob_response.json()
                blob_sha = blob["sha"]

                # 4) Get the tree of the base commit
                base_commit_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/git/commits/{base_sha}",
                    headers=self.headers
                )
                base_commit_response.raise_for_status()
                base_commit = base_commit_response.json()
                base_tree_sha = base_commit["tree"]["sha"]

                # 5) Create a new tree with our file
                new_tree_response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/git/trees",
                    headers=self.headers,
                    json={
                        "base_tree": base_tree_sha,
                        "tree": [
                            {
                                "path": file_path,
                                "mode": "100644",
                                "type": "blob",
                                "sha": blob_sha
                            }
                        ]
                    }
                )
                new_tree_response.raise_for_status()
                new_tree = new_tree_response.json()
                new_tree_sha = new_tree["sha"]

                # 6) Commit the new tree
                commit_response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/git/commits",
                    headers=self.headers,
                    json={
                        "message": f"Add {file_path}",
                        "tree": new_tree_sha,
                        "parents": [base_sha]
                    }
                )
                commit_response.raise_for_status()
                commit = commit_response.json()
                commit_sha = commit["sha"]

                # 7) Update branch ref to point to new commit
                update_ref_response = await client.patch(
                    f"{self.base_url}/repos/{owner}/{repo}/git/refs/heads/{branch_name}",
                    headers=self.headers,
                    json={
                        "sha": commit_sha,
                        "force": False
                    }
                )
                update_ref_response.raise_for_status()

                # 8) Finally create the PR
                pr_response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls",
                    headers=self.headers,
                    json={
                        "base": base,
                        "head": f"{owner}:{branch_name}",
                        "title": title,
                        "body": body
                    }
                )
                pr_response.raise_for_status()
                return pr_response.json()

            except httpx.HTTPStatusError as e:
                error_detail = f"GitHub API error: {e.response.status_code}"
                try:
                    error_body = e.response.json()
                    error_detail += f" - {error_body.get('message', 'Unknown error')}"
                except:
                    error_detail += f" - {e.response.text}"
                raise HTTPException(status_code=e.response.status_code, detail=error_detail)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.post("/create-pull-request")
async def create_pull_request(
    request: PullRequestRequest,
    authorization: str = Header(..., description="GitHub token (format: 'token YOUR_TOKEN')")
):
    """
    Create a GitHub pull request with a new file.
    
    - **authorization**: GitHub token in header (format: 'token YOUR_TOKEN')
    - **owner**: Repository owner/organization
    - **repo**: Repository name
    - **base**: Base branch (default: main)
    - **branch_name**: Name for the new branch
    - **title**: Pull request title
    - **body**: Pull request description
    - **file_path**: Path where the file should be created (e.g., 'articles/new-article.md')
    - **file_content**: Content of the file to be added
    """
    # Extract token from authorization header
    if not authorization.startswith("token "):
        raise HTTPException(status_code=401, detail="Authorization header must start with 'token '")
    
    token = authorization.replace("token ", "")
    
    creator = GitHubPullRequestCreator(token)
    
    result = await creator.create_pull_request(
        owner=request.owner,
        repo=request.repo,
        base=request.base,
        branch_name=request.branch_name,
        title=request.title,
        body=request.body,
        file_path=request.file_path,
        file_content=request.file_content
    )
    
    return {
        "message": "Pull request created successfully",
        "pull_request": {
            "id": result["id"],
            "number": result["number"],
            "title": result["title"],
            "html_url": result["html_url"],
            "state": result["state"],
            "head": {
                "ref": result["head"]["ref"],
                "sha": result["head"]["sha"]
            },
            "base": {
                "ref": result["base"]["ref"],
                "sha": result["base"]["sha"]
            }
        }
    }

@app.get("/")
async def root():
    """Welcome endpoint with API information."""
    return {
        "message": "GitHub Pull Request Creator API",
        "version": "1.0.0",
        "endpoints": {
            "POST /create-pull-request": "Create a new pull request with file addition",
            "GET /docs": "Interactive API documentation",
            "GET /redoc": "Alternative API documentation"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000