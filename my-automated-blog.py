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
            "title": keyword,  # Use the keyword as the title
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
            <a href="https://gfreelife.com" class="back-link">Back to Home</a>
        </div>
    </body>
    </html>
    """

    # Sanitize the filename
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
    # Remove CSS blocks and comments
    plain_text = re.sub(r'\{.*?\}', '', plain_text)  # Remove CSS rules
    plain_text = re.sub(r'/\*.*?\*/', '', plain_text)  # Remove CSS comments
    # Remove extra whitespace and newlines
    plain_text = re.sub(r'\s+', ' ', plain_text).strip()
    # Return the first 200 characters (or less) as a preview
    return plain_text[:200] + "..."

# Function to scan the docs folder for existing posts
def scan_existing_posts(output_dir):
    existing_posts = []
    for filename in os.listdir(output_dir):
        if filename.endswith(".html") and filename != "index.html":
            filepath = os.path.join(output_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as file:
                    content = file.read()
                    # Extract the title from the <title> tag
                    title_match = re.search(r'<title>(.*?)</title>', content)
                    if title_match:
                        title = title_match.group(1)
                        existing_posts.append({
                            "title": title,
                            "content": content,
                            "filename": filename
                        })
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
    return existing_posts

# Function to generate index.html with the new design
def generate_index_html(blog_posts, output_dir):
    index_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My Automated Blog</title>
        <link href="https://fonts.googleapis.com/css?family=Roboto:400,500,700,900" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
        <style>
            body {
                width: 100%;
                height: 100vh;
                font-family: 'Roboto';
                background: #fff;
            }

            h1 {
                font-size: 42px;
                font-weight: 900;
                margin: 50px 5%;
                text-transform: capitalize;
                position: relative;
            }

            h1:after {
                position: absolute;
                content: '';
                top: -10px;
                left: 0;
                width: 80px;
                height: 4px;
                background: #2c3e50;
            }

            .grid-container {
                width: 90%;
                margin: 0 auto;
            }

            .grid-col {
                width: 33.3%;
                min-width: 300px;
                box-sizing: border-box;
                padding-right: 20px;
                margin-bottom: 20px;
                float: left;
            }

            .grid-col .icon {
                font-size: 48px;
                text-align: center;
                margin-bottom: 20px;
                color: #2c3e50;
            }

            .body-content {
                background: #2c3e50;
                padding: 0 30px 120px 40px;
                position: relative;
                border: 1px solid #2c3e50;
                border-top: none;
                z-index: 1;
                line-height: 23px;
                color: #fff;
                border-bottom-left-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            .body-content:before {
                content: '';
                position: absolute;
                top: -30px;
                left: -1px;
                width: 100%;
                height: 50px;
                background: #2c3e50;
                border-left: 1px solid #2c3e50;
                border-right: 1px solid #2c3e50;
                transform: skewY(5deg);
                z-index: -1;
                box-shadow: 0 -4px 5px rgba(0,0,0,0.4);
            }

            .body-content h3 {
                margin-bottom: 15px;
                font-family: 'Roboto';
                font-weight: 900;
                font-size: 22px;
            }

            .round-btn {
                position: absolute;
                bottom: 25px;
                left: 40px!important;
                width: 60px;
                height: 60px;
                font-size: 22px;
                line-height: 60px;
                text-align: center;
                background: #fff;
                color: #2c3e50;
                -webkit-border-radius: 50%;
                -moz-border-radius: 50%;
                border-radius: 50%;
                z-index: 1;
                -webkit-transition: all .2s ease-in-out;
                -o-transition: all .2s ease-in-out;
                -moz-transition: all .2s ease-in-out;
                transition: all .2s ease-in-out;
                -webkit-box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.2), 0 0 0 0 rgba(255, 255, 255, 0.0);
                -moz-box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.2), 0 0 0 0 rgba(255, 255, 255, 0.0);
                box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.2), 0 0 0 0 rgba(255, 255, 255, 0.0);
            }

            .round-btn:hover {
                -webkit-box-shadow: 0 0 0 10px rgba(255, 255, 255, 0.2), 0 0 0 20px rgba(255, 255, 255, 0.12);
                -moz-box-shadow: 0 0 0 10px rgba(255, 255, 255, 0.2), 0 0 0 20px rgba(255, 255, 255, 0.12);
                box-shadow: 0 0 0 10px rgba(255, 255, 255, 0.2), 0 0 0 20px rgba(255, 255, 255, 0.12);
            }
        </style>
    </head>
    <body>
        <h1>Latest news</h1>
        <div class="grid-container">
    """

    # Add all blog posts to the grid
    for post in blog_posts:
        # Sanitize the filename
        filename = post.get("filename", sanitize_filename(f"{post['title'].lower().replace(' ', '_')}.html"))
        # Extract the first few lines of meaningful text
        preview = extract_preview(post['content'])
        index_content += f"""
            <div class="grid-col">
                <div class="icon">
                    <i class="fa fa-file-text-o"></i>
                </div>
                <div class="body-content">
                    <h3>{post['title']}</h3>
                    <p>{preview}</p>
                    <a href="{filename}" class="round-btn"><i class="fa fa-long-arrow-right"></i></a>
                </div>
            </div>
        """

    index_content += """
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
        # Pull remote changes first to avoid conflicts
        subprocess.run(["git", "pull", "origin", "main"], check=True)
        # Push to the main branch
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Changes pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"Error pushing to GitHub: {e}")

# Main script
if __name__ == "__main__":
    # List of keywords or topics
    keywords = [
        "How to catch a ball?"
    ]

    # Output directory for blog posts
    output_dir = "docs"
    os.makedirs(output_dir, exist_ok=True)

    # Add CNAME file for custom domain
    cname_filepath = os.path.join(output_dir, "CNAME")
    with open(cname_filepath, "w") as cname_file:
        cname_file.write("gfreelife.com")

    # Scan existing posts in the docs folder
    existing_posts = scan_existing_posts(output_dir)

    # Generate blog posts for each keyword
    blog_posts = []
    for keyword in keywords:
        # Check if the post already exists
        post_exists = any(post["title"] == keyword for post in existing_posts)
        if not post_exists:
            post = generate_blog_post(keyword)
            if post:
                blog_posts.append(post)
                print(f"Generated post: {post['title']}")
                print(f"Content preview: {post['content'][:100]}...")  # Debug: Print a preview of the content
            else:
                print(f"Failed to generate post for: {keyword}")
        else:
            print(f"Post already exists: {keyword}")

    # Combine existing and new posts
    all_posts = existing_posts + blog_posts

    # Generate individual HTML files for new posts
    for post in blog_posts:
        save_formatted_html(post, output_dir)

    # Generate index.html
    generate_index_html(all_posts, output_dir)

    # Push changes to GitHub
    push_to_github()