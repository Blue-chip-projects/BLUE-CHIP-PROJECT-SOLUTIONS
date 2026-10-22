"""Wait for Cloudflare's successful deployment check for this exact commit."""
import json
import os
import time
import urllib.request

repository = os.environ["GITHUB_REPOSITORY"]
sha = os.environ["GITHUB_SHA"]
token = os.environ["GH_TOKEN"]
url = f"https://api.github.com/repos/{repository}/commits/{sha}/check-runs?per_page=100"
deadline = time.monotonic() + 600
while time.monotonic() < deadline:
    request = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Jenasaro-Search-Check",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        runs = json.load(response)["check_runs"]
    deployment = next((run for run in runs if run["name"] == "Cloudflare Pages"
                       and run.get("app", {}).get("slug") == "cloudflare-workers-and-pages"), None)
    if deployment and deployment["status"] == "completed":
        if deployment["conclusion"] != "success":
            raise SystemExit(f"Cloudflare deployment failed: {deployment['conclusion']}; search engines were not notified")
        print(f"Cloudflare deployment succeeded for {sha}")
        break
    print("Waiting for Cloudflare to publish this commit", flush=True)
    time.sleep(10)
else:
    raise SystemExit("Timed out waiting for deployment; search engines were not notified")
