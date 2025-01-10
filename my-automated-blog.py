from openai import OpenAI
import os
import re
import subprocess
from datetime import datetime

# Initialize the OpenAI client with DeepSeek API
api_key = "sk-fe730eb5b82c40478fa6411e9f09bf1c"  # Replace with your DeepSeek API key
base_url = "https://api.deepseek.com"  # DeepSeek base URL

client = OpenAI(api_key=api_key, base_url=base_url)

# Function to sanitize filenames
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

# Function to generate fully formatted HTML content using DeepSeek API
def generate_formatted_html(prompt):
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",  # Specify the model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates fully formatted HTML content for blog posts, including headlines, paragraphs, and basic styling. Return only the HTML code, nothing else."},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

# Function to generate a blog post with fully formatted HTML
def generate_blog_post(keyword):
    prompt = f"""
    Write a detailed and engaging blog post about {keyword}. Include an introduction, body with subheadings, and conclusion.
    Format the entire content in HTML with proper headings (<h1>, <h2>), paragraphs (<p>), and basic styling.
    Return only the HTML code, nothing else. Use tables also and include FAQs and conclusion.
    """
    print(f"Generating blog post for: {keyword}")
    html_content = generate_formatted_html(prompt)
    if html_content:
        print(f"Successfully generated content for: {keyword}")
        return {
            "title": keyword,  # Use the keyword as the title (removed "Blog Post:" prefix)
            "content": html_content
        }
    else:
        print(f"Failed to generate content for: {keyword}")
        return None

# Function to save the formatted HTML content to a file
def save_formatted_html(post, output_dir):
    # Wrap the generated HTML in a full HTML template
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{post['title']}</title>
        <link href="https://fonts.googleapis.com/css2?family=Figtree:ital,wght@0,300..900;1,300..900&display=swap" rel="stylesheet">
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: hsl(47, 88%, 63%);
                font-family: "Figtree", sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }}
            .container {{
                background: hsl(0, 0%, 100%);
                max-width: 800px;
                margin: 20px;
                padding: 20px;
                border: solid 1px hsl(0, 0%, 7%);
                border-radius: 20px;
                box-shadow: 12px 12px 10px -6px rgba(0,0,0,1);
            }}
            h1 {{
                color: #2c3e50;
                text-align: center;
                margin-bottom: 20px;
            }}
            h2 {{
                color: #34495e;
                margin-top: 30px;
                margin-bottom: 15px;
            }}
            p {{
                color: #666;
                margin-bottom: 20px;
            }}
            a {{
                color: #3498db;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .back-link {{
                display: inline-block;
                margin-top: 20px;
                font-size: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {post['content']}
            <a href="index.html" class="back-link">Back to Home</a>
        </div>
    </body>
    </html>
    """

    # Sanitize the filename (removed "blog_post__" prefix)
    filename = sanitize_filename(f"{post['title'].lower().replace(' ', '_')}.html")
    filepath = os.path.join(output_dir, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(full_html)
        print(f"Generated: {filepath}")
    except Exception as e:
        print(f"Error saving file {filename}: {e}")

# Function to extract the first few lines of meaningful text from HTML content
def extract_preview(html_content):
    # Remove HTML tags and extract plain text
    plain_text = re.sub(r'<[^>]+>', '', html_content)
    # Remove extra whitespace and newlines
    plain_text = re.sub(r'\s+', ' ', plain_text).strip()
    # Return the first 200 characters (or less) as a preview
    return plain_text[:200] + "..."

# Function to generate index.html with a grid layout
def generate_index_html(blog_posts, output_dir):
    index_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My Automated Blog</title>
        <link href="https://fonts.googleapis.com/css2?family=Figtree:ital,wght@0,300..900;1,300..900&display=swap" rel="stylesheet">
        <style>
            body {
                margin: 0;
                padding: 0;
                background: hsl(47, 88%, 63%);
                font-family: "Figtree", sans-serif;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                color: #2c3e50;
                text-align: center;
                margin-bottom: 40px;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
            }
            .card {
                background: hsl(0, 0%, 100%);
                padding: 1.2em;
                border: solid 1px hsl(0, 0%, 7%);
                border-radius: 20px;
                box-shadow: 12px 12px 10px -6px rgba(0,0,0,1);
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 15px 15px 10px -6px rgba(0,0,0,1);
            }
            .img-head img {
                width: 100%;
                border-radius: 10px;
            }
            .card button {
                background: hsl(47, 88%, 63%);
                border: 0px solid;
                font-weight: 800;
                padding: 0.5em 1em 0.5em 1em;
                border-radius: 5px;
                margin-top: 1.5em;
                cursor: pointer;
            }
            .published {
                font-weight: 500;
                font-size: 0.8em;
                margin-top: 1em;
            }
            .card h1 {
                font-size: 1.5em;
                font-weight: 800;
                margin-top: 1em;
            }
            .descr {
                color: hsl(0, 0%, 42%);
                font-weight: 500;
                margin-top: 1em;
            }
            .author {
                display: flex;
                align-items: center;
                margin-top: 1.5em;
            }
            .author img {
                width: 3em;
                border-radius: 50%;
            }
            .author h6 {
                margin-left: 1em;
                font-size: 1em;
                font-weight: 800;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome to My Automated Blog</h1>
            <div class="grid">
    """

    for post in blog_posts:
        # Sanitize the filename (removed "blog_post__" prefix)
        filename = sanitize_filename(f"{post['title'].lower().replace(' ', '_')}.html")
        # Extract the first few lines of meaningful text
        preview = extract_preview(post['content'])
        index_content += f"""
                <div class="card" onclick="window.location.href='{filename}'">
                    <div class="img-head">
                        <img src="https://natyari.com/frontendmentor/blog-preview-card/assets/images/illustration-article.svg" alt="Header Image">
                    </div>
                    <button>Learning</button>
                    <p class="published">Published 21 Dec 2023</p>
                    <h1>{post['title']}</h1>
                    <p class="descr">{preview}</p>
                    <div class="author">
                        <img src="https://natyari.com/frontendmentor/blog-preview-card/assets/images/image-avatar.webp" alt="Author">
                        <h6>Greg Hooper</h6>
                    </div>
                </div>
        """

    index_content += """
            </div>
        </div>
    </body>
    </html>
    """

    # Save index.html with UTF-8 encoding
    filepath = os.path.join(output_dir, "index.html")
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(index_content)
        print(f"Generated: {filepath}")
    except Exception as e:
        print(f"Error saving index.html: {e}")

# Function to push changes to GitHub
def push_to_github():
    try:
        # Add all files to Git
        subprocess.run(["git", "add", "."], check=True)
        # Commit with a timestamp
        commit_message = f"Automated update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        # Push to the main branch
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Changes pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"Error pushing to GitHub: {e}")

# Main script
if __name__ == "__main__":
    # List of keywords or topics
    keywords = [
        "How to Defrost a Burger Patty?"
    ]

    # Generate blog posts for each keyword
    blog_posts = []
    for keyword in keywords:
        post = generate_blog_post(keyword)
        if post:
            blog_posts.append(post)
            print(f"Generated post: {post['title']}")
            print(f"Content preview: {post['content'][:100]}...")  # Debug: Print a preview of the content
        else:
            print(f"Failed to generate post for: {keyword}")

    # Save blog posts to files
    output_dir = "docs"
    os.makedirs(output_dir, exist_ok=True)

    # Generate individual HTML files for each post
    for post in blog_posts:
        save_formatted_html(post, output_dir)

    # Generate index.html
    generate_index_html(blog_posts, output_dir)

    # Push changes to GitHub
    push_to_github()