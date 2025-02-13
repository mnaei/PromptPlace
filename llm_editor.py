#!/usr/bin/env python3
import os
import sys
import json
import logging
import subprocess
from bs4 import BeautifulSoup
from google import genai


# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        logging.info("LLM Editor script started.")

        # Get event payload from GitHub Actions
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            logging.error("GITHUB_EVENT_PATH environment variable not set.")
            sys.exit(1)
        with open(event_path, "r") as fp:
            event = json.load(fp)

        # Check for the issue and ensure the label is "prompt"
        issue = event.get("issue")
        label = event.get("label", {})  # for "labeled" events the label is in a separate key
        if not issue:
            logging.error("No issue found in the event payload.")
            sys.exit(1)
        if label.get("name") != "prompt":
            logging.info("This issue does not have the 'prompt' label; exiting.")
            sys.exit(0)

        issue_number = issue.get("number")
        issue_body = issue.get("body")
        if not issue_body:
            logging.error("Issue body is empty; nothing to process.")
            sys.exit(1)
        logging.info(f"Processing issue #{issue_number}")

        # Read the current index.html file
        index_path = "index.html"
        if not os.path.exists(index_path):
            logging.error(f"{index_path} not found in the repository.")
            sys.exit(1)
        with open(index_path, "r", encoding="utf-8") as f:
            current_html = f.read()

        # Build the prompt for the Gemini API
        prompt = (
            "Below is the current HTML of the page:\n"
            "---------------------\n"
            f"{current_html}\n"
            "---------------------\n\n"
            "Apply the following modifications as specified by the user. "
            "Return only the modified HTML code (including any necessary CSS/JS) and nothing else.\n\n"
            "User instructions:\n"
            f"{issue_body}"
        )
        logging.info("Constructed prompt for Gemini API.")

        # Create the Gemini client using your GEMINI_API_KEY
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            logging.error("GEMINI_API_KEY environment variable not set.")
            sys.exit(1)
        client = genai.Client(api_key=gemini_api_key)
        logging.info("Created Gemini API client.")

        # Start a chat session with the Gemini API and send the prompt
        chat = client.chats.create(model='gemini-2.0-flash')
        logging.info("Starting chat session with Gemini API.")

        try:
            response = chat.send_message(message=prompt)
        except Exception as e:
            logging.error(f"Gemini API Error {e}") 
            post_issue_comment(issue_number, error_msg)
            sys.exit(1)
            
        logging.info("Received response from Gemini API.")

        llm_output = response.text

        # Use BeautifulSoup to parse and pretty-print any HTML in the response.
        soup = BeautifulSoup(llm_output, "html.parser")
        html_tag = soup.find("html")
        if not html_tag:
            error_msg = "No <html> tag found in the Gemini API response."
            logging.error(error_msg)
            post_issue_comment(issue_number, error_msg)
            sys.exit(1)
        new_html = html_tag.prettify()

        # Write the new HTML back to index.html.
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(new_html)
        logging.info(f"{index_path} updated with new content.")

        # Configure Git to use a generic commit user
        subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)

        # Stage and commit the changes
        subprocess.run(["git", "add", index_path], check=True)
        commit_message = f"LLM updated index.html based on issue #{issue_number}"
        try:
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
        except subprocess.CalledProcessError:
            # If there is nothing to commit, exit gracefully.
            logging.info("No changes to commit. Exiting.")
            post_issue_comment(issue_number, "No changes were necessary for index.html.")
            sys.exit(0)

        # Push the commit to the main branch
        subprocess.run(["git", "push", "origin", "main"], check=True)
        logging.info("Changes pushed to main branch.")

        # Retrieve the new commit hash.
        result = subprocess.run(["git", "rev-parse", "HEAD"], check=True, stdout=subprocess.PIPE, universal_newlines=True)
        commit_hash = result.stdout.strip()

        # Construct a commit URL using GITHUB_REPOSITORY environment variable.
        repo_full = os.environ.get("GITHUB_REPOSITORY", "")
        commit_url = f"https://github.com/{repo_full}/commit/{commit_hash}"

        # Prepare and post a comment on the issue with the commit link and diff.
        comment_body = (
            "**index.html updated!**\n\n"
            f"Commit: [{commit_hash}]({commit_url})\n\n"
        )
        post_issue_comment(issue_number, comment_body)
        logging.info(f"Comment posted on issue #{issue_number}.")
    except Exception as e:
        logging.exception("An error occurred in the LLM Editor script: %s", str(e))
        try:
            # Attempt to notify the issue about the error.
            if "issue" in locals() and issue.get("number"):
                post_issue_comment(issue.get("number"), f"Error in LLM Editor script: {str(e)}")
        except Exception as e2:
            logging.error("Failed to post error comment: %s", str(e2))
        sys.exit(1)

def post_issue_comment(issue_number, body):
    """
    Post a comment on the GitHub issue using the GitHub API.
    Requires the GITHUB_TOKEN and GITHUB_REPOSITORY environment variables.
    """
    import requests  # Imported here to limit its scope if needed
    github_token = os.environ.get("GITHUB_TOKEN")
    repo_full = os.environ.get("GITHUB_REPOSITORY")
    if not github_token or not repo_full:
        logging.error("GITHUB_TOKEN or GITHUB_REPOSITORY environment variables not set. Cannot post comment.")
        return

    url = f"https://api.github.com/repos/{repo_full}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"body": body}
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code not in (200, 201):
            logging.error("Failed to post comment (status %s): %s", response.status_code, response.text)
        else:
            logging.info("Successfully posted comment to issue #%s.", issue_number)
    except Exception as err:
        logging.error("Exception posting comment: %s", str(err))

if __name__ == "__main__":
    main()
