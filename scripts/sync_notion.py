import os
import requests
import json
from pathlib import Path

# Load environment variables
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

# Base output directory
OUTPUT_DIR = Path("notes")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def query_database():
    """Fetch pages from the Notion database that are Published."""
    url = f"{BASE_URL}/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    body = {
        "filter": {
            "property": "Status",
            "select": {"equals": "Published"}
        }
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    return response.json()["results"]


def get_page_content(page_id):
    """Fetch the page's full content (rich text blocks)."""
    url = f"{BASE_URL}/blocks/{page_id}/children?page_size=100"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["results"]


def rich_text_to_plaintext(rich_text_array):
    """Convert Notion rich_text objects to plain text."""
    text = ""
    for part in rich_text_array:
        if "text" in part and part["text"] is not None:
            text += part["text"]["content"]
    return text


def blocks_to_markdown(blocks):
    """Convert block elements to Markdown."""
    md = ""
    for block in blocks:
        block_type = block["type"]

        if block_type == "paragraph":
            md += rich_text_to_plaintext(block["paragraph"]["rich_text"]) + "\n\n"

        elif block_type == "heading_1":
            md += "# " + rich_text_to_plaintext(block["heading_1"]["rich_text"]) + "\n\n"

        elif block_type == "heading_2":
            md += "## " + rich_text_to_plaintext(block["heading_2"]["rich_text"]) + "\n\n"

        elif block_type == "heading_3":
            md += "### " + rich_text_to_plaintext(block["heading_3"]["rich_text"]) + "\n\n"

        elif block_type == "bulleted_list_item":
            md += "- " + rich_text_to_plaintext(block["bulleted_list_item"]["rich_text"]) + "\n"

        elif block_type == "numbered_list_item":
            md += "1. " + rich_text_to_plaintext(block["numbered_list_item"]["rich_text"]) + "\n"

        elif block_type == "code":
            language = block["code"]["language"]
            code_text = rich_text_to_plaintext(block["code"]["rich_text"])
            md += f"```{language}\n{code_text}\n```\n\n"

        # More block types can be added here if needed.

    return md


def save_markdown(page, markdown_body):
    """Save one page as a Markdown file inside notes/category/title.md."""
    props = page["properties"]

    title = props["Title"]["title"][0]["plain_text"]

    category = props["Category"]["select"]["name"]
    tags = [t["name"] for t in props["Tags"]["multi_select"]]
    last_edited = page["last_edited_time"]
    summary = props["Summary"]["rich_text"][0]["plain_text"] if props["Summary"]["rich_text"] else ""

    # Create category folder inside notes/
    category_folder = OUTPUT_DIR / category.replace(" ", "-").lower()
    category_folder.mkdir(parents=True, exist_ok=True)

    # File path
    filename = f"{title.replace(' ', '_').lower()}.md"
    filepath = category_folder / filename

    # Frontmatter
    frontmatter = f"""---
title: "{title}"
category: "{category}"
tags: {tags}
last_updated: "{last_edited}"
summary: "{summary}"
---

"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter)
        f.write(markdown_body)

    print(f"Saved: {filepath}")


def main():
    print("Fetching Published pages from Notion...")
    pages = query_database()

    for page in pages:
        page_id = page["id"]
        print(f"Processing: {page_id}")

        blocks = get_page_content(page_id)
        markdown_body = blocks_to_markdown(blocks)
        save_markdown(page, markdown_body)

    print("\nSync completed successfully!")


if __name__ == "__main__":
    main()
