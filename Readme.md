# GitHub Pull Request Creator API

A FastAPI-based REST API that automatically creates GitHub pull requests with file additions. This service simplifies the process of programmatically creating PRs by handling all the GitHub API interactions including branch creation, file commits, and pull request submission.

## 🚀 Features

- **Automated PR Creation**: Creates pull requests with new file additions in a single API call
- **AI Fix Suggestions**: Automatically generate and post fix suggestions using Ollama
- **Issue Management**: Programmatically create GitHub issues with labels and assignees
- **Branch Management**: Automatically creates and manages feature branches
- **File Operations**: Handles file creation and commits via GitHub's Git API
- **Async Operations**: Built with FastAPI for high performance async operations
- **Comprehensive Error Handling**: Detailed error responses with proper HTTP status codes
- **Auto Documentation**: Interactive API documentation with Swagger UI
- **Token Authentication**: Secure GitHub token-based authentication

## 📋 Prerequisites

- Python 3.8+
- GitHub Personal Access Token with repository permissions
- Target GitHub repository (public or private with proper access)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd github-pr-creator-api
   ```

2. **Install dependencies**
   ```bash
   pip install fastapi uvicorn httpx pydantic
   ```

   Or using requirements.txt:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create requirements.txt** (if needed)
   ```
   fastapi==0.104.1
   uvicorn==0.24.0
   httpx==0.25.2
   pydantic==2.5.0
   ```

## 🚀 Quick Start

1. **Start the server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. **Create your first pull request**
   ```bash
   curl -X POST "http://localhost:8000/create-pull-request" \
     -H "Authorization: token YOUR_GITHUB_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "owner": "your-username",
       "repo": "your-repository",
       "base": "main",
       "branch_name": "feature/add-new-file",
       "title": "Add new documentation file",
       "body": "This PR adds a new documentation file to improve project clarity.",
       "file_path": "docs/new-guide.md",
       "file_content": "# New Guide\n\nThis is a comprehensive guide for new users.\n\n## Getting Started\n\nFollow these steps..."
     }'
   ```

## 📖 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Welcome page with API information |
| `GET` | `/health` | Health check endpoint |
| `POST` | `/create-pull-request` | Create a new pull request with file addition |
| `POST` | `/create-issue` | Create a new GitHub issue |
| `PATCH` | `/issues/update` | Update or close an existing issue |
| `GET` | `/issues/list` | List issues in a repository |
| `POST` | `/suggest-fix` | Generate and post an AI fix suggestion |
| `POST` | `/repos/create` | Create a new repository |
| `DELETE` | `/repos/delete` | Delete a repository |
| `POST` | `/branches/create` | Create a new branch |
| `GET` | `/docs` | Interactive Swagger documentation |
| `GET` | `/redoc` | Alternative ReDoc documentation |

### Create Pull Request

**Endpoint:** `POST /create-pull-request`

**Headers:**
- `Authorization: token YOUR_GITHUB_TOKEN` (required)
- `Content-Type: application/json`

**Request Body:**
```json
{
  "owner": "string",           // Repository owner/organization (required)
  "repo": "string",            // Repository name (required)
  "base": "string",            // Base branch (default: "main")
  "branch_name": "string",     // New branch name (required)
  "title": "string",           // Pull request title (required)
  "body": "string",            // Pull request description (required)
  "file_path": "string",       // File path (e.g., "docs/readme.md") (required)
  "file_content": "string"     // File content (required)
}
```

**Response:**
```json
{
  "message": "Pull request created successfully",
  "pull_request": {
    "id": 123456,
    "number": 42,
    "title": "Add new documentation file",
    "html_url": "https://github.com/owner/repo/pull/42",
    "state": "open",
    "head": {
      "ref": "feature/add-new-file",
      "sha": "abc123..."
    },
    "base": {
      "ref": "main",
      "sha": "def456..."
    }
  }
}
```

### Create Issue

**Endpoint:** `POST /create-issue`

**Headers:**
- `Authorization: token YOUR_GITHUB_TOKEN` (required)
- `Content-Type: application/json`

**Request Body:**
```json
{
  "owner": "string",           // Repository owner (required)
  "repo": "string",            // Repository name (required)
  "title": "string",           // Issue title (required)
  "body": "string",            // Issue description (optional)
  "labels": ["string"],        // Array of label names (optional)
  "assignees": ["string"]      // Array of GitHub usernames (optional)
}
```

**Response:**
```json
{
  "message": "Issue created successfully",
  "issue": {
    "id": 987654,
    "number": 123,
    "title": "Found a bug in the API",
    "html_url": "https://github.com/owner/repo/issues/123",
    "state": "open",
    "labels": ["bug", "high-priority"],
    "assignees": ["developer1"]
  }
}
```

### Suggest Fix

**Endpoint:** `POST /suggest-fix`

**Headers:**
- `Authorization: token YOUR_GITHUB_TOKEN` (required)
- `Content-Type: application/json`

**Request Body:**
```json
{
  "owner": "string",           // Repository owner (required)
  "repo": "string",            // Repository name (required)
  "issue_number": 123,         // The issue number (required)
  "model": "string"            // Ollama model, e.g., "mistral:7b" (default: "mistral:7b")
}
```

**Response:**
```json
{
  "message": "Fix suggestion posted successfully",
  "comment_url": "https://github.com/owner/repo/issues/123#issuecomment-789",
  "suggestion": "Detailed fix suggestion in markdown..."
}
```

## 🔐 Authentication

This API uses GitHub Personal Access Tokens for authentication. 

### Creating a GitHub Token

1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Click "Generate new token"
3. Select the following scopes:
   - `repo` (Full control of private repositories)
   - `public_repo` (Access public repositories) - if working with public repos only
4. Copy the generated token

### Using the Token

Include the token in the Authorization header:
```
Authorization: token YOUR_GITHUB_TOKEN
```

## 🔧 Configuration

### Environment Variables

You can optionally use environment variables:

```bash
export GITHUB_TOKEN=your_token_here
export API_HOST=0.0.0.0
export API_PORT=8000
```

### Production Deployment

For production deployment, consider:

1. **Use environment variables** for sensitive data
2. **Enable HTTPS** with reverse proxy (nginx/traefik)
3. **Add rate limiting** to prevent abuse
4. **Implement logging** for monitoring
5. **Use Docker** for containerization

## 🐳 Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Docker Compose:**
```yaml
version: '3.8'
services:
  github-pr-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
```

## 📝 Examples

### Example 1: Add Documentation File
```bash
curl -X POST "http://localhost:8000/create-pull-request" \
  -H "Authorization: token ghp_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "myorg",
    "repo": "myproject",
    "branch_name": "docs/update-readme",
    "title": "Update project README",
    "body": "This PR updates the README with latest project information and usage examples.",
    "file_path": "README.md",
    "file_content": "# My Project\n\nUpdated documentation content..."
  }'
```

### Example 2: Add Configuration File
```bash
curl -X POST "http://localhost:8000/create-pull-request" \
  -H "Authorization: token ghp_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "myorg",
    "repo": "myproject",
    "base": "develop",
    "branch_name": "feature/add-config",
    "title": "Add application configuration",
    "body": "Adds new configuration file for application settings.",
    "file_path": "config/app.yaml",
    "file_content": "app:\n  name: MyApp\n  version: 1.0.0\n  debug: false"
  }'
```

### Example 3: Create Bug Issue
```bash
curl -X POST "http://localhost:8000/create-issue" \
  -H "Authorization: token ghp_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "myorg",
    "repo": "myproject",
    "title": "Critical bug in production",
    "body": "Users are reporting issues when logging in with social accounts.",
    "labels": ["bug", "p0"],
    "assignees": ["lead-dev"]
  }'
```

### Example 4: Suggest Fix for Issue
```bash
curl -X POST "http://localhost:8000/suggest-fix" \
  -H "Authorization: token ghp_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "myorg",
    "repo": "myproject",
    "issue_number": 42,
    "model": "mistral:7b"
  }'
```

## ❌ Error Handling

The API provides detailed error responses:

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input data |
| 401 | Unauthorized - Invalid or missing GitHub token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Repository or branch not found |
| 422 | Unprocessable Entity - Branch already exists or other Git conflicts |
| 500 | Internal Server Error - Unexpected server error |

**Example Error Response:**
```json
{
  "detail": "GitHub API error: 422 - Reference already exists"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure your GitHub token has the correct permissions
   - Check that the token is not expired
   - Verify the Authorization header format

2. **Branch Already Exists**
   - Use a unique branch name for each PR
   - Delete existing branches if needed

3. **File Path Issues**
   - Use forward slashes (`/`) in file paths
   - Ensure the path doesn't start with `/`

4. **Repository Access**
   - Verify you have write access to the repository
   - Check that the repository exists and is accessible

### Support

For issues and questions:
- Check the [API documentation](http://localhost:8000/docs)
- Review the error messages carefully
- Ensure all required fields are provided
- Verify GitHub token permissions

## 🔄 API Workflow

The API follows this workflow:

1. **Validate Input** - Checks request parameters and authentication
2. **Get Base Reference** - Retrieves the base branch SHA
3. **Create Branch** - Creates a new branch from the base
4. **Create Blob** - Uploads the file content as a Git blob
5. **Get Base Tree** - Retrieves the current repository tree
6. **Create New Tree** - Adds the new file to the tree
7. **Create Commit** - Commits the changes with a message
8. **Update Branch** - Points the branch to the new commit
9. **Create Pull Request** - Opens the PR with specified title and body

This ensures a clean, atomic operation that either succeeds completely or fails without partial changes.