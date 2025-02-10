# llm_editor.py
import os
import requests
import git
import google.generativeai as genai
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
ISSUE_NUMBER = os.environ["ISSUE_NUMBER"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GITHUB_ISSUE_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{ISSUE_NUMBER}"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_REPOSITORY}"
RAW_GITHUB_REPO_URL = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main"
INDEX_HTML_PATH = "index.html"
COMMIT_MESSAGE_PREFIX = f"Update index.html from issue #{ISSUE_NUMBER}: "

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def get_current_index_html():
    """Fetches the current index.html file from the GitHub repository."""
    try:
        response = requests.get(f"{RAW_GITHUB_REPO_URL}/{INDEX_HTML_PATH}")
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching index.html: {e}")
        raise

def create_prompt(current_html, instructions):
    """Creates a prompt for the Gemini API."""
    prompt_parts = [
        "You are an expert web developer. Modify the following HTML code based on the user instructions. ",
        "Ensure the response is only valid HTML, CSS, and Javascript code within the <html>, <head>, and <body> tags. ",
        "Do not include any explanations or surrounding text. ",
        "Current index.html:\n",
        current_html,
        "\nUser instructions:\n",
        instructions,
        "\n\nPlease provide the complete modified index.html code:"
    ]
    return "".join(prompt_parts)

def generate_code_with_llm(prompt):
    """Generates HTML code using the Gemini API."""
    try:
        response = model.generate_content(prompt)
        response.raise_for_block_error()
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.error(f"Gemini API error: {e}")
        raise

def extract_html_from_llm_response(llm_response):
    """Extracts HTML, CSS, and JS code from the LLM response using regex."""
    html_match = re.search(r'(?s)<html>(.*?)</html>', llm_response, re.IGNORECASE)
    if html_match:
        return html_match.group(0) # Return the whole <html></html> block
    else:
        logging.warning("Could not find <html> tags in LLM response. Returning the full response as is.")
        return llm_response

def commit_changes_to_github(repo_path, new_html, commit_message):
    """Commits the changes to the GitHub repository."""
    try:
        repo = git.Repo(repo_path)
        with open(os.path.join(repo_path, INDEX_HTML_PATH), "w") as f:
            f.write(new_html)
        repo.index.add([INDEX_HTML_PATH])
        repo.index.commit(commit_message)
        origin = repo.remote(name='origin')
        origin.push()
        commit_hash = repo.head.commit.hexsha
        return commit_hash
    except git.GitError as e:
        logging.error(f"Git commit error: {e}")
        raise

def comment_on_github_issue(commit_url, diff_url):
    """Comments on the GitHub Issue with a link to the commit and diff."""
    comment_body = f"✅ index.html updated!\n\nCommit: [{commit_url}]({commit_url})\nDiff: [{diff_url}]({diff_url})"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"body": comment_body}
    try:
        response = requests.post(GITHUB_ISSUE_URL + "/comments", headers=headers, json=data)
        response.raise_for_status()
        logging.info(f"Commented on issue: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error commenting on issue: {e}")
        raise

def get_diff_url(repo_url, base_commit, head_commit):
    """Constructs the diff URL between two commits on GitHub."""
    return f"{repo_url}/compare/{base_commit}...{head_commit}"

def main():
    """Main function to orchestrate the script."""
    issue_body = os.environ["ISSUE_BODY"]
    repo_path = "."  # Assuming the script runs from the root of the repository

    logging.info("Starting script execution.")

    try:
        current_html = get_current_index_html()
        logging.info("Successfully fetched current index.html.")
    except Exception as e:
        error_message = f"Failed to fetch current index.html. Please check the repository and network connectivity. Error: {e}"
        logging.error(error_message)
        comment_on_github_issue(f"Error: {error_message}", "") # Comment with error, no commit/diff URL
        return 1

    prompt = create_prompt(current_html, issue_body)
    logging.info("Prompt created for Gemini API.")

    try:
        llm_generated_code = generate_code_with_llm(prompt)
        logging.info("Code generated by Gemini API.")
        extracted_html = extract_html_from_llm_response(llm_generated_code)
        logging.info("HTML extracted from LLM response.")
    except Exception as e:
        error_message = f"Failed to generate or process code with Gemini API. Error: {e}"
        logging.error(error_message)
        comment_on_github_issue(f"Error: {error_message}", "") # Comment with error, no commit/diff URL
        return 1

    commit_message = COMMIT_MESSAGE_PREFIX + issue_body[:50] + "..." # Truncate issue body for commit message
    base_commit_sha = git.Repo(repo_path).head.commit.hexsha # Get SHA before commit
    try:
        commit_hash = commit_changes_to_github(repo_path, extracted_html, commit_message)
        logging.info(f"Changes committed to GitHub. Commit hash: {commit_hash}")
        commit_url = f"{GITHUB_REPO_URL}/commit/{commit_hash}"
        head_commit_sha = commit_hash # SHA after commit
        diff_url = get_diff_url(GITHUB_REPO_URL, base_commit_sha, head_commit_sha)
        comment_on_github_issue(commit_url, diff_url)
    except Exception as e:
        error_message = f"Failed to commit changes to GitHub. Error: {e}"
        logging.error(error_message)
        comment_on_github_issue(f"Error: {error_message}", "") # Comment with error, no commit/diff URL
        return 1

    logging.info("Script execution completed successfully.")
    return 0

if __name__ == "__main__":
    exit(main())
