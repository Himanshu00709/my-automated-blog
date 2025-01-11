from openai import OpenAI
import os
import re
import subprocess
from datetime import datetime
from collections import defaultdict

# Initialize the OpenAI client with DeepSeek API
api_key = "sk-fe730eb5b82c40478fa6411e9f09bf1c"  # Replace with your DeepSeek API key
base_url = "https://api.deepseek.com"  # DeepSeek base URL
client = OpenAI(api_key=api_key, base_url=base_url)

# Function to sanitize filenames and replace spaces with hyphens
def sanitize_filename(filename):
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    sanitized = sanitized.replace(' ', '-')
    sanitized = re.sub(r'[-_]+$', '', sanitized)
    return sanitized.lower()

# Function to generate fully formatted HTML content using DeepSeek API
def generate_formatted_html(prompt):
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates fully formatted HTML content for blog posts, including headlines, paragraphs, and basic styling. Return only the HTML code, nothing else. Make sure to add as many tables as you can and write 1000-word articles minimum."},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

# Function to determine category and subcategory using DeepSeek API
def determine_category(keyword):
    prompt = f"""
    Determine the most appropriate category and subcategory for the following keyword: "{keyword}".
    Return the result in the format: "category/subcategory".
    For example, for "how to buy a skateboard?", return "buying-guide/skateboard".
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that determines the category and subcategory for a given keyword."},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        result = response.choices[0].message.content.strip()
        if "/" in result:
            category, subcategory = result.split("/", 1)
            return category.strip(), subcategory.strip()
        else:
            return "uncategorized", "uncategorized"
    except Exception as e:
        print(f"Error determining category: {e}")
        return "uncategorized", "uncategorized"

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
            "title": keyword,
            "content": html_content
        }
    else:
        print(f"Failed to generate content for: {keyword}")
        return None

# Function to save the formatted HTML content to a file
def save_formatted_html(post, output_dir, category, subcategory):
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
            footer {{
                background: #2c3e50;
                color: #fff;
                padding: 20px;
                text-align: center;
                margin-top: 40px;
            }}
            footer a {{
                color: #3498db;
                text-decoration: none;
            }}
            footer a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {post['content']}
            <a href="https://gfreelife.com" class="back-link">Back to Home</a>
        </div>
        <footer>
            <p>&copy; {datetime.now().year} GFreeLife. All rights reserved. | <a href="/">Home</a> | <a href="/categories">Categories</a></p>
        </footer>
    </body>
    </html>
    """
    category_dir = os.path.join(output_dir, category)
    subcategory_dir = os.path.join(category_dir, subcategory)
    os.makedirs(subcategory_dir, exist_ok=True)
    filename = sanitize_filename(f"{post['title']}.html")
    filepath = os.path.join(subcategory_dir, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(full_html)
        print(f"Generated: {filepath}")
    except Exception as e:
        print(f"Error saving file {filename}: {e}")

# Function to extract the first few lines of meaningful text from HTML content
def extract_preview(html_content):
    plain_text = re.sub(r'<[^>]+>', '', html_content)
    plain_text = re.sub(r'\{.*?\}', '', plain_text)
    plain_text = re.sub(r'/\*.*?\*/', '', plain_text)
    plain_text = re.sub(r'\s+', ' ', plain_text).strip()
    return plain_text[:200] + "..."

# Function to scan the docs folder for existing posts
def scan_existing_posts(output_dir):
    existing_posts = []
    for root, _, files in os.walk(output_dir):
        for filename in files:
            if filename.endswith(".html") and filename != "index.html":
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as file:
                        content = file.read()
                        title_match = re.search(r'<title>(.*?)</title>', content)
                        if title_match:
                            title = title_match.group(1)
                            relative_path = os.path.relpath(filepath, output_dir)
                            category, subcategory = os.path.split(os.path.dirname(relative_path))
                            existing_posts.append({
                                "title": title,
                                "content": content,
                                "filename": filename,
                                "category": category,
                                "subcategory": subcategory
                            })
                except Exception as e:
                    print(f"Error reading file {filename}: {e}")
    return existing_posts

# Function to generate a navigation menu based on categories and subcategories
def generate_navigation_menu(categories):
    menu_items = []
    for category, subcategories in categories.items():
        menu_items.append(f'<li class="nav-item dropdown">')
        menu_items.append(f'<a class="nav-link dropdown-toggle" href="/{category}" id="{category}-dropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">{category.capitalize()}</a>')
        menu_items.append('<div class="dropdown-menu" aria-labelledby="{category}-dropdown">')
        for subcategory in subcategories:
            menu_items.append(f'<a class="dropdown-item" href="/{category}/{subcategory}">{subcategory.capitalize()}</a>')
        menu_items.append('</div>')
        menu_items.append('</li>')
    return f"""
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <a class="navbar-brand" href="https://gfreelife.com">GFreeLife</a>
        <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav">
                {"".join(menu_items)}
            </ul>
        </div>
    </nav>
    """

# Function to generate index.html with the new design
def generate_index_html(blog_posts, output_dir, categories):
    index_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My Automated Blog</title>
        <link href="https://fonts.googleapis.com/css?family=Roboto:400,500,700,900" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
        <style>
            body {{
                width: 100%;
                height: 100vh;
                font-family: 'Roboto';
                background: #fff;
                margin: 0;
                padding: 0;
            }}
            h1 {{
                font-size: 42px;
                font-weight: 900;
                margin: 50px 5%;
                text-transform: capitalize;
                position: relative;
            }}
            h1:after {{
                position: absolute;
                content: '';
                top: -10px;
                left: 0;
                width: 80px;
                height: 4px;
                background: #2c3e50;
            }}
            .grid-container {{
                width: 90%;
                margin: 0 auto;
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
            }}
            .grid-col {{
                flex: 1 1 calc(33.3% - 20px);
                min-width: 300px;
                box-sizing: border-box;
                margin-bottom: 20px;
            }}
            .grid-col .icon {{
                font-size: 48px;
                text-align: center;
                margin-bottom: 20px;
                color: #2c3e50;
            }}
            .body-content {{
                background: #2c3e50;
                padding: 20px;
                position: relative;
                border: 1px solid #2c3e50;
                border-top: none;
                z-index: 1;
                line-height: 23px;
                color: #fff;
                border-radius: 5px;
            }}
            .body-content h3 {{
                margin-bottom: 15px;
                font-family: 'Roboto';
                font-weight: 900;
                font-size: 22px;
            }}
            .round-btn {{
                position: absolute;
                bottom: 25px;
                left: 20px;
                width: 60px;
                height: 60px;
                font-size: 22px;
                line-height: 60px;
                text-align: center;
                background: #fff;
                color: #2c3e50;
                border-radius: 50%;
                z-index: 1;
                transition: all .2s ease-in-out;
                box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.2), 0 0 0 0 rgba(255, 255, 255, 0.0);
            }}
            .round-btn:hover {{
                box-shadow: 0 0 0 10px rgba(255, 255, 255, 0.2), 0 0 0 20px rgba(255, 255, 255, 0.12);
            }}
            .navbar {{
                background: #2c3e50;
                padding: 10px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .navbar-brand {{
                color: #fff;
                font-size: 24px;
                font-weight: 700;
                text-decoration: none;
            }}
            .navbar-nav {{
                display: flex;
                gap: 20px;
                list-style: none;
                margin: 0;
                padding: 0;
            }}
            .nav-item {{
                position: relative;
            }}
            .nav-link {{
                color: #fff;
                text-decoration: none;
                font-size: 16px;
                font-weight: 500;
            }}
            .dropdown-menu {{
                display: none;
                position: absolute;
                top: 100%;
                left: 0;
                background: #fff;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                border-radius: 5px;
                padding: 10px 0;
                z-index: 1000;
            }}
            .dropdown-item {{
                color: #2c3e50;
                text-decoration: none;
                padding: 10px 20px;
                display: block;
            }}
            .dropdown-item:hover {{
                background: #f8f9fa;
            }}
            .nav-item:hover .dropdown-menu {{
                display: block;
            }}
            footer {{
                background: #2c3e50;
                color: #fff;
                padding: 20px;
                text-align: center;
                margin-top: 40px;
            }}
            footer a {{
                color: #3498db;
                text-decoration: none;
            }}
            footer a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        {generate_navigation_menu(categories)}
        <h1>Latest News</h1>
        <div class="grid-container">
    """
    for post in blog_posts:
        url = f"{post['category']}/{post['subcategory']}/{post['filename']}"
        preview = extract_preview(post['content'])
        index_content += f"""
            <div class="grid-col">
                <div class="icon">
                    <i class="fa fa-file-text-o"></i>
                </div>
                <div class="body-content">
                    <h3>{post['title']}</h3>
                    <p>{preview}</p>
                    <a href="{url}" class="round-btn"><i class="fa fa-long-arrow-right"></i></a>
                </div>
            </div>
        """
    index_content += """
        </div>
        <footer>
            <p>&copy; {datetime.now().year} GFreeLife. All rights reserved. | <a href="/">Home</a> | <a href="/categories">Categories</a></p>
        </footer>
    </body>
    </html>
    """
    filepath = os.path.join(output_dir, "index.html")
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(index_content)
        print(f"Generated: {filepath}")
    except Exception as e:
        print(f"Error saving index.html: {e}")

# Function to generate category pages
def generate_category_pages(categories, output_dir):
    for category, subcategories in categories.items():
        category_dir = os.path.join(output_dir, category)
        os.makedirs(category_dir, exist_ok=True)
        category_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{category.capitalize()} - GFreeLife</title>
            <link href="https://fonts.googleapis.com/css?family=Roboto:400,500,700,900" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
            <style>
                body {{
                    width: 100%;
                    height: 100vh;
                    font-family: 'Roboto';
                    background: #fff;
                    margin: 0;
                    padding: 0;
                }}
                h1 {{
                    font-size: 42px;
                    font-weight: 900;
                    margin: 50px 5%;
                    text-transform: capitalize;
                    position: relative;
                }}
                h1:after {{
                    position: absolute;
                    content: '';
                    top: -10px;
                    left: 0;
                    width: 80px;
                    height: 4px;
                    background: #2c3e50;
                }}
                .grid-container {{
                    width: 90%;
                    margin: 0 auto;
                    display: flex;
                    flex-wrap: wrap;
                    gap: 20px;
                }}
                .grid-col {{
                    flex: 1 1 calc(33.3% - 20px);
                    min-width: 300px;
                    box-sizing: border-box;
                    margin-bottom: 20px;
                }}
                .grid-col .icon {{
                    font-size: 48px;
                    text-align: center;
                    margin-bottom: 20px;
                    color: #2c3e50;
                }}
                .body-content {{
                    background: #2c3e50;
                    padding: 20px;
                    position: relative;
                    border: 1px solid #2c3e50;
                    border-top: none;
                    z-index: 1;
                    line-height: 23px;
                    color: #fff;
                    border-radius: 5px;
                }}
                .body-content h3 {{
                    margin-bottom: 15px;
                    font-family: 'Roboto';
                    font-weight: 900;
                    font-size: 22px;
                }}
                .round-btn {{
                    position: absolute;
                    bottom: 25px;
                    left: 20px;
                    width: 60px;
                    height: 60px;
                    font-size: 22px;
                    line-height: 60px;
                    text-align: center;
                    background: #fff;
                    color: #2c3e50;
                    border-radius: 50%;
                    z-index: 1;
                    transition: all .2s ease-in-out;
                    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.2), 0 0 0 0 rgba(255, 255, 255, 0.0);
                }}
                .round-btn:hover {{
                    box-shadow: 0 0 0 10px rgba(255, 255, 255, 0.2), 0 0 0 20px rgba(255, 255, 255, 0.12);
                }}
                .navbar {{
                    background: #2c3e50;
                    padding: 10px 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .navbar-brand {{
                    color: #fff;
                    font-size: 24px;
                    font-weight: 700;
                    text-decoration: none;
                }}
                .navbar-nav {{
                    display: flex;
                    gap: 20px;
                    list-style: none;
                    margin: 0;
                    padding: 0;
                }}
                .nav-item {{
                    position: relative;
                }}
                .nav-link {{
                    color: #fff;
                    text-decoration: none;
                    font-size: 16px;
                    font-weight: 500;
                }}
                .dropdown-menu {{
                    display: none;
                    position: absolute;
                    top: 100%;
                    left: 0;
                    background: #fff;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    border-radius: 5px;
                    padding: 10px 0;
                    z-index: 1000;
                }}
                .dropdown-item {{
                    color: #2c3e50;
                    text-decoration: none;
                    padding: 10px 20px;
                    display: block;
                }}
                .dropdown-item:hover {{
                    background: #f8f9fa;
                }}
                .nav-item:hover .dropdown-menu {{
                    display: block;
                }}
                footer {{
                    background: #2c3e50;
                    color: #fff;
                    padding: 20px;
                    text-align: center;
                    margin-top: 40px;
                }}
                footer a {{
                    color: #3498db;
                    text-decoration: none;
                }}
                footer a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <nav class="navbar">
                <a class="navbar-brand" href="https://gfreelife.com">GFreeLife</a>
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/categories">Categories</a>
                    </li>
                </ul>
            </nav>
            <h1>{category.capitalize()}</h1>
            <div class="grid-container">
        """
        for subcategory in subcategories:
            category_content += f"""
                <div class="grid-col">
                    <div class="icon">
                        <i class="fa fa-folder-open-o"></i>
                    </div>
                    <div class="body-content">
                        <h3>{subcategory.capitalize()}</h3>
                        <a href="/{category}/{subcategory}" class="round-btn"><i class="fa fa-long-arrow-right"></i></a>
                    </div>
                </div>
            """
        category_content += """
            </div>
            <footer>
                <p>&copy; {datetime.now().year} GFreeLife. All rights reserved. | <a href="/">Home</a> | <a href="/categories">Categories</a></p>
            </footer>
        </body>
        </html>
        """
        filepath = os.path.join(category_dir, "index.html")
        try:
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(category_content)
            print(f"Generated: {filepath}")
        except Exception as e:
            print(f"Error saving category page {filepath}: {e}")

# Function to generate subcategory pages
def generate_subcategory_pages(categories, output_dir, blog_posts):
    for category, subcategories in categories.items():
        for subcategory in subcategories:
            subcategory_dir = os.path.join(output_dir, category, subcategory)
            os.makedirs(subcategory_dir, exist_ok=True)
            subcategory_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subcategory.capitalize()} - {category.capitalize()} - GFreeLife</title>
                <link href="https://fonts.googleapis.com/css?family=Roboto:400,500,700,900" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
                <style>
                    body {{
                        width: 100%;
                        height: 100vh;
                        font-family: 'Roboto';
                        background: #fff;
                        margin: 0;
                        padding: 0;
                    }}
                    h1 {{
                        font-size: 42px;
                        font-weight: 900;
                        margin: 50px 5%;
                        text-transform: capitalize;
                        position: relative;
                    }}
                    h1:after {{
                        position: absolute;
                        content: '';
                        top: -10px;
                        left: 0;
                        width: 80px;
                        height: 4px;
                        background: #2c3e50;
                    }}
                    .grid-container {{
                        width: 90%;
                        margin: 0 auto;
                        display: flex;
                        flex-wrap: wrap;
                        gap: 20px;
                    }}
                    .grid-col {{
                        flex: 1 1 calc(33.3% - 20px);
                        min-width: 300px;
                        box-sizing: border-box;
                        margin-bottom: 20px;
                    }}
                    .grid-col .icon {{
                        font-size: 48px;
                        text-align: center;
                        margin-bottom: 20px;
                        color: #2c3e50;
                    }}
                    .body-content {{
                        background: #2c3e50;
                        padding: 20px;
                        position: relative;
                        border: 1px solid #2c3e50;
                        border-top: none;
                        z-index: 1;
                        line-height: 23px;
                        color: #fff;
                        border-radius: 5px;
                    }}
                    .body-content h3 {{
                        margin-bottom: 15px;
                        font-family: 'Roboto';
                        font-weight: 900;
                        font-size: 22px;
                    }}
                    .round-btn {{
                        position: absolute;
                        bottom: 25px;
                        left: 20px;
                        width: 60px;
                        height: 60px;
                        font-size: 22px;
                        line-height: 60px;
                        text-align: center;
                        background: #fff;
                        color: #2c3e50;
                        border-radius: 50%;
                        z-index: 1;
                        transition: all .2s ease-in-out;
                        box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.2), 0 0 0 0 rgba(255, 255, 255, 0.0);
                    }}
                    .round-btn:hover {{
                        box-shadow: 0 0 0 10px rgba(255, 255, 255, 0.2), 0 0 0 20px rgba(255, 255, 255, 0.12);
                    }}
                    .navbar {{
                        background: #2c3e50;
                        padding: 10px 20px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}
                    .navbar-brand {{
                        color: #fff;
                        font-size: 24px;
                        font-weight: 700;
                        text-decoration: none;
                    }}
                    .navbar-nav {{
                        display: flex;
                        gap: 20px;
                        list-style: none;
                        margin: 0;
                        padding: 0;
                    }}
                    .nav-item {{
                        position: relative;
                    }}
                    .nav-link {{
                        color: #fff;
                        text-decoration: none;
                        font-size: 16px;
                        font-weight: 500;
                    }}
                    .dropdown-menu {{
                        display: none;
                        position: absolute;
                        top: 100%;
                        left: 0;
                        background: #fff;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                        border-radius: 5px;
                        padding: 10px 0;
                        z-index: 1000;
                    }}
                    .dropdown-item {{
                        color: #2c3e50;
                        text-decoration: none;
                        padding: 10px 20px;
                        display: block;
                    }}
                    .dropdown-item:hover {{
                        background: #f8f9fa;
                    }}
                    .nav-item:hover .dropdown-menu {{
                        display: block;
                    }}
                    footer {{
                        background: #2c3e50;
                        color: #fff;
                        padding: 20px;
                        text-align: center;
                        margin-top: 40px;
                    }}
                    footer a {{
                        color: #3498db;
                        text-decoration: none;
                    }}
                    footer a:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
                <nav class="navbar">
                    <a class="navbar-brand" href="https://gfreelife.com">GFreeLife</a>
                    <ul class="navbar-nav">
                        <li class="nav-item">
                            <a class="nav-link" href="/">Home</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/categories">Categories</a>
                        </li>
                    </ul>
                </nav>
                <h1>{subcategory.capitalize()}</h1>
                <div class="grid-container">
            """
            subcategory_posts = [post for post in blog_posts if post['category'] == category and post['subcategory'] == subcategory]
            for post in subcategory_posts:
                url = f"{post['category']}/{post['subcategory']}/{post['filename']}"
                preview = extract_preview(post['content'])
                subcategory_content += f"""
                    <div class="grid-col">
                        <div class="icon">
                            <i class="fa fa-file-text-o"></i>
                        </div>
                        <div class="body-content">
                            <h3>{post['title']}</h3>
                            <p>{preview}</p>
                            <a href="{url}" class="round-btn"><i class="fa fa-long-arrow-right"></i></a>
                        </div>
                    </div>
                """
            subcategory_content += """
                </div>
                <footer>
                    <p>&copy; {datetime.now().year} GFreeLife. All rights reserved. | <a href="/">Home</a> | <a href="/categories">Categories</a></p>
                </footer>
            </body>
            </html>
            """
            filepath = os.path.join(subcategory_dir, "index.html")
            try:
                with open(filepath, "w", encoding="utf-8") as file:
                    file.write(subcategory_content)
                print(f"Generated: {filepath}")
            except Exception as e:
                print(f"Error saving subcategory page {filepath}: {e}")

# Function to push changes to GitHub
def push_to_github():
    try:
        subprocess.run(["git", "add", "."], check=True)
        commit_message = f"Automated update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "pull", "origin", "main"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Changes pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"Error pushing to GitHub: {e}")

# Main script
if __name__ == "__main__":
    keywords = [
        "how to play a fighting game?"
    ]
    output_dir = "docs"
    os.makedirs(output_dir, exist_ok=True)
    cname_filepath = os.path.join(output_dir, "CNAME")
    with open(cname_filepath, "w") as cname_file:
        cname_file.write("gfreelife.com")
    
    # Initialize categories with existing posts
    categories = defaultdict(set)
    existing_posts = scan_existing_posts(output_dir)
    
    # Populate categories with existing posts' categories and subcategories
    for post in existing_posts:
        categories[post['category']].add(post['subcategory'])
    
    blog_posts = []
    for keyword in keywords:
        # Skip exact match keywords if they already exist
        post_exists = any(post["title"] == keyword for post in existing_posts)
        if not post_exists:
            post = generate_blog_post(keyword)
            if post:
                category, subcategory = determine_category(keyword)
                categories[category].add(subcategory)  # Add new category/subcategory if not already present
                blog_posts.append({
                    **post,
                    "category": category,
                    "subcategory": subcategory,
                    "filename": sanitize_filename(f"{post['title']}.html")
                })
                print(f"Generated post: {post['title']} (Category: {category}/{subcategory})")
            else:
                print(f"Failed to generate post for: {keyword}")
        else:
            print(f"Post already exists: {keyword}")
    
    # Combine existing posts and new posts
    all_posts = existing_posts + blog_posts
    
    # Save new posts
    for post in blog_posts:
        save_formatted_html(post, output_dir, post['category'], post['subcategory'])
    
    # Generate index.html, category pages, and subcategory pages
    generate_index_html(all_posts, output_dir, categories)
    generate_category_pages(categories, output_dir)
    generate_subcategory_pages(categories, output_dir, all_posts)
    
    # Push changes to GitHub
    push_to_github()