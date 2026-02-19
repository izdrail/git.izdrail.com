from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import httpx
import base64
from typing import Optional
import json
import os

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

class IssueRequest(BaseModel):
    owner: str
    repo: str
    title: str
    body: Optional[str] = None
    labels: Optional[list[str]] = None
    assignees: Optional[list[str]] = None

class FixSuggestionRequest(BaseModel):
    owner: str
    repo: str
    issue_number: int
    model: str = "mistral:7b"

class IssueUpdate(BaseModel):
    owner: str
    repo: str
    issue_number: int
    state: Optional[str] = None  # 'open' or 'closed'
    title: Optional[str] = None
    body: Optional[str] = None
    labels: Optional[list[str]] = None
    assignees: Optional[list[str]] = None

class RepoCreate(BaseModel):
    name: str
    description: Optional[str] = None
    private: bool = False
    auto_init: bool = True

class RepositoryRequest(BaseModel):
    owner: str
    repo: str

class CommentRequest(BaseModel):
    owner: str
    repo: str
    issue_number: int
    body: str

class BranchRequest(BaseModel):
    owner: str
    repo: str
    branch: str
    source_branch: str = "main"

class GitHubAPI:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise HTTPException(status_code=401, detail="GitHub token must be provided in header or environment")
            
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FastAPI-GitHub-API"
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

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def create_comment(self, owner: str, repo: str, issue_number: int, body: str) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                    headers=self.headers,
                    json={"body": body}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[list[str]] = None,
        assignees: Optional[list[str]] = None
    ) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                issue_data = {
                    "title": title,
                    "body": body,
                    "labels": labels or [],
                    "assignees": assignees or []
                }
                
                # Remove None values
                issue_data = {k: v for k, v in issue_data.items() if v is not None}
                
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/issues",
                    headers=self.headers,
                    json=issue_data
                )
                response.raise_for_status()
                return response.json()

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

    async def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        state: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        labels: Optional[list[str]] = None,
        assignees: Optional[list[str]] = None
    ) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                update_data = {}
                if state: update_data["state"] = state
                if title: update_data["title"] = title
                if body is not None: update_data["body"] = body
                if labels is not None: update_data["labels"] = labels
                if assignees is not None: update_data["assignees"] = assignees

                response = await client.patch(
                    f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                    headers=self.headers,
                    json=update_data
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def list_issues(self, owner: str, repo: str, state: str = "open") -> list:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/issues",
                    headers=self.headers,
                    params={"state": state}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def create_repository(self, name: str, description: str, private: bool, auto_init: bool) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/user/repos",
                    headers=self.headers,
                    json={
                        "name": name,
                        "description": description,
                        "private": private,
                        "auto_init": auto_init
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def delete_repository(self, owner: str, repo: str) -> bool:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/repos/{owner}/{repo}",
                    headers=self.headers
                )
                response.raise_for_status()
                return True
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def create_branch(self, owner: str, repo: str, branch: str, source_branch: str) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                # Get SHA of source branch
                ref_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/git/refs/heads/{source_branch}",
                    headers=self.headers
                )
                ref_response.raise_for_status()
                sha = ref_response.json()["object"]["sha"]

                # Create new branch
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/git/refs",
                    headers=self.headers,
                    json={
                        "ref": f"refs/heads/{branch}",
                        "sha": sha
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def list_repositories(self, username: Optional[str] = None) -> list:
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/user/repos" if not username else f"{self.base_url}/users/{username}/repos"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def list_branches(self, owner: str, repo: str) -> list:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/branches",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def list_pull_requests(self, owner: str, repo: str, state: str = "open") -> list:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls",
                    headers=self.headers,
                    params={"state": state}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def list_commits(self, owner: str, repo: str, sha: Optional[str] = None) -> list:
        async with httpx.AsyncClient() as client:
            try:
                params = {}
                if sha: params["sha"] = sha
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/commits",
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def get_contents(self, owner: str, repo: str, path: str = "", ref: Optional[str] = None) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                params = {}
                if ref: params["ref"] = ref
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def get_pull_request(self, owner: str, repo: str, pull_number: int) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    async def get_repository(self, owner: str, repo: str) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

class OllamaClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "https://ai.izdrail.com")

    async def generate_fix_suggestion(self, issue_title: str, issue_body: str, model: str) -> str:
        prompt = f"""As an expert software engineer, please provide a concise and practical fix suggestion for the following GitHub issue.
Title: {issue_title}
Description: {issue_body}

Provide your suggestion in markdown format. If possible, include a code snippet.
"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()
                return response.json().get("response", "No suggestion generated.")
            except Exception as e:
                return f"Error generating suggestion: {str(e)}"

@app.post("/create-pull-request")
async def create_pull_request(
    request: PullRequestRequest,
    authorization: Optional[str] = Header(None, description="GitHub token (format: 'token YOUR_TOKEN')")
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
    token = None
    if authorization:
        if not authorization.startswith("token "):
            raise HTTPException(status_code=401, detail="Authorization header must start with 'token '")
        token = authorization.replace("token ", "")
    
    api = GitHubAPI(token)
    
    result = await api.create_pull_request(
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

@app.post("/create-issue")
async def create_issue(
    request: IssueRequest,
    authorization: Optional[str] = Header(None, description="GitHub token (format: 'token YOUR_TOKEN')")
):
    """
    Create a GitHub issue in a specified repository.
    
    - **authorization**: GitHub token in header (format: 'token YOUR_TOKEN')
    - **owner**: Repository owner/organization
    - **repo**: Repository name
    - **title**: Issue title
    - **body**: Issue description (optional)
    - **labels**: List of labels to apply (optional)
    - **assignees**: List of GitHub usernames to assign (optional)
    """
    token = None
    if authorization:
        if not authorization.startswith("token "):
            raise HTTPException(status_code=401, detail="Authorization header must start with 'token '")
        token = authorization.replace("token ", "")
    
    api = GitHubAPI(token)
    
    result = await api.create_issue(
        owner=request.owner,
        repo=request.repo,
        title=request.title,
        body=request.body,
        labels=request.labels,
        assignees=request.assignees
    )
    
    return {
        "message": "Issue created successfully",
        "issue": {
            "id": result["id"],
            "number": result["number"],
            "title": result["title"],
            "html_url": result["html_url"],
            "state": result["state"],
            "labels": [label["name"] for label in result.get("labels", [])],
            "assignees": [assignee["login"] for assignee in result.get("assignees", [])]
        }
    }

@app.post("/suggest-fix")
async def suggest_fix(
    request: FixSuggestionRequest,
    authorization: Optional[str] = Header(None, description="GitHub token (format: 'token YOUR_TOKEN')")
):
    """
    Generate a fix suggestion for an issue using Ollama and post it as a comment.
    
    - **authorization**: GitHub token in header (format: 'token YOUR_TOKEN')
    - **owner**: Repository owner
    - **repo**: Repository name
    - **issue_number**: The number of the issue to comment on
    - **model**: Ollama model to use (default: mistral:7b)
    """
    token = None
    if authorization:
        if not authorization.startswith("token "):
            raise HTTPException(status_code=401, detail="Authorization header must start with 'token '")
        token = authorization.replace("token ", "")
    
    github_api = GitHubAPI(token)
    ollama = OllamaClient()
    
    # 1) Get issue details
    issue = await github_api.get_issue(request.owner, request.repo, request.issue_number)
    
    # 2) Generate suggestion
    suggestion = await ollama.generate_fix_suggestion(
        issue["title"],
        issue.get("body") or "No description provided.",
        request.model
    )
    
    # 3) Post comment
    comment_body = f"### 🤖 AI-Generated Fix Suggestion (Model: {request.model})\n\n{suggestion}"
    result = await github_api.create_comment(request.owner, request.repo, request.issue_number, comment_body)
    
    return {
        "message": "Fix suggestion posted successfully",
        "comment_url": result["html_url"],
        "suggestion": suggestion
    }

@app.patch("/issues/update")
async def update_issue_endpoint(
    request: IssueUpdate,
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.update_issue(**request.dict())

@app.get("/issues/list")
async def list_issues_endpoint(
    owner: str,
    repo: str,
    state: str = "open",
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.list_issues(owner, repo, state)

@app.post("/repos/create")
async def create_repo_endpoint(
    request: RepoCreate,
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.create_repository(**request.dict())

@app.delete("/repos/delete")
async def delete_repo_endpoint(
    request: RepositoryRequest,
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    success = await api.delete_repository(request.owner, request.repo)
    return {"message": "Repository deleted successfully"} if success else {"message": "Failed to delete repository"}

@app.post("/branches/create")
async def create_branch_endpoint(
    request: BranchRequest,
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.create_branch(**request.dict())

@app.get("/repos/list")
async def list_repos_endpoint(
    username: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.list_repositories(username)

@app.get("/branches/list")
async def list_branches_endpoint(
    owner: str,
    repo: str,
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.list_branches(owner, repo)

@app.get("/pulls/list")
async def list_pulls_endpoint(
    owner: str,
    repo: str,
    state: str = "open",
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.list_pull_requests(owner, repo, state)

@app.get("/repos/commits")
async def list_commits_endpoint(
    owner: str,
    repo: str,
    sha: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.list_commits(owner, repo, sha)

@app.get("/repos/contents")
async def get_contents_endpoint(
    owner: str,
    repo: str,
    path: str = "",
    ref: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.get_contents(owner, repo, path, ref)

@app.get("/repos/get")
async def get_repo_endpoint(
    owner: str,
    repo: str,
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.get_repository(owner, repo)

@app.get("/pulls/get")
async def get_pull_endpoint(
    owner: str,
    repo: str,
    pull_number: int,
    authorization: Optional[str] = Header(None)
):
    token = None
    if authorization:
        token = authorization.replace("token ", "") if authorization.startswith("token ") else authorization
    api = GitHubAPI(token)
    return await api.get_pull_request(owner, repo, pull_number)

@app.get("/")
async def root():
    """Welcome endpoint with API information."""
    return {
        "message": "GitHub API Extension Service",
        "version": "1.4.0",
        "endpoints": {
            "POST /create-pull-request": "Create a new pull request with file addition",
            "POST /create-issue": "Create a new GitHub issue",
            "PATCH /issues/update": "Update or close an existing issue",
            "GET /issues/list": "List issues in a repository",
            "POST /suggest-fix": "Generate and post an AI fix suggestion for an issue",
            "POST /repos/create": "Create a new repository",
            "GET /repos/list": "List repositories for a user or the authenticated user",
            "GET /repos/get": "Get repository metadata",
            "DELETE /repos/delete": "Delete a repository",
            "GET /repos/commits": "List commits in a repository",
            "GET /repos/contents": "Get repository contents or file metadata",
            "POST /branches/create": "Create a new branch",
            "GET /branches/list": "List branches in a repository",
            "GET /pulls/list": "List pull requests in a repository",
            "GET /pulls/get": "Get pull request details",
            "GET /docs": "Interactive API documentation",
            "GET /redoc": "Alternative API documentation"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000