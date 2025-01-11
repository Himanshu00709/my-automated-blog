import threading
from openai import OpenAI
import os
import re
import subprocess
from datetime import datetime
from collections import defaultdict
import xml.etree.ElementTree as ET

# Initialize the OpenAI client with DeepSeek API
api_key = "sk-fe730eb5b82c40478fa6411e9f09bf1c"  # Replace with your DeepSeek API key
base_url = "https://api.deepseek.com"  # DeepSeek base URL
client = OpenAI(api_key=api_key, base_url=base_url)

# Function to sanitize filenames and replace spaces with hyphens
def sanitize_filename(filename):
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Replace invalid characters
    sanitized = sanitized.replace(' ', '-')  # Replace spaces with hyphens
    sanitized = re.sub(r'[-_]+$', '', sanitized)  # Remove trailing hyphens/underscores
    return sanitized.lower()[:50]  # Truncate to 50 characters to avoid long paths

# Function to generate fully formatted HTML content using DeepSeek API
def generate_formatted_html(prompt):
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates fully formatted HTML content for blog posts, including headlines, paragraphs, and basic styling. Return only the HTML code, nothing else. Make sure to add as many tables as you can and write 1000-word articles minimum. Write like a niche expert and doctor. write long paragraphs not fluffy content"},
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
            # Sanitize category and subcategory names
            category = sanitize_filename(category.strip())
            subcategory = sanitize_filename(subcategory.strip())
            return category, subcategory
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
                background: hsl(210, 29%, 24%);
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
            <a href="/" class="back-link">Back to Home</a>
        </div>
    </body>
    </html>
    """
    # Sanitize category and subcategory names
    category = sanitize_filename(category)
    subcategory = sanitize_filename(subcategory)
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
        <a class="navbar-brand" href="/">GFreeLife</a>
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

# Function to generate index.html with updated card content
def generate_index_html(blog_posts, output_dir, categories):
    index_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gluten Free Life</title>
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
            .body-content p {{
                font-size: 16px;
                color: #ddd;
                margin-bottom: 20px;
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
        <h1>Welcome to GFreeLife</h1>
        <div class="grid-container">
    """
    for post in blog_posts:
        url = f"/{post['category']}/{post['subcategory']}/{post['filename']}"
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
            <p>&copy; 2025 GFreeLife. All rights reserved. | <a href="/">Home</a> | <a href="/categories">Categories</a></p>
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
        # Sanitize category name
        category = sanitize_filename(category)
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
                <a class="navbar-brand" href="/">GFreeLife</a>
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
            # Sanitize subcategory name
            subcategory = sanitize_filename(subcategory)
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
            # Sanitize category and subcategory names
            category = sanitize_filename(category)
            subcategory = sanitize_filename(subcategory)
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
                </style>
            </head>
            <body>
                <nav class="navbar">
                    <a class="navbar-brand" href="/">GFreeLife</a>
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
                url = f"/{post['category']}/{post['subcategory']}/{post['filename']}"
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

# Function to generate sitemap.xml
def generate_sitemap(output_dir, blog_posts):
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    base_url = "https://gfreelife.com"

    # Add homepage
    url = ET.SubElement(urlset, "url")
    ET.SubElement(url, "loc").text = base_url
    ET.SubElement(url, "lastmod").text = datetime.now().strftime("%Y-%m-%d")

    # Add blog posts
    for post in blog_posts:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = f"{base_url}/{post['category']}/{post['subcategory']}/{post['filename']}"
        ET.SubElement(url, "lastmod").text = datetime.now().strftime("%Y-%m-%d")

    # Write to file
    tree = ET.ElementTree(urlset)
    sitemap_path = os.path.join(output_dir, "sitemap.xml")
    tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)
    print(f"Generated: {sitemap_path}")

# Function to generate robots.txt
def generate_robots_txt(output_dir):
    robots_content = """
User-agent: *
Allow: /
Sitemap: https://gfreelife.com/sitemap.xml
    """
    robots_path = os.path.join(output_dir, "robots.txt")
    with open(robots_path, "w", encoding="utf-8") as file:
        file.write(robots_content)
    print(f"Generated: {robots_path}")

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
      "gluten free dairy free pierogi",
"gluten free dairy free popcorn",
"gluten free dairy free potluck ideas",
"gluten free dairy free potluck recipes",
"gluten free dairy free thanksgiving sides",
"gluten free dairy free trail mix",
"gluten free demi glace",
"gluten free dessert dips",
"gluten free dining at disney springs",
"gluten free donut mix",
"gluten free donuts online",
"gluten free donuts order online",
"gluten free donuts shipped",
"gluten free dubai chocolate bar",
"gluten free duck sauce",
"gluten free dutch oven cobbler",
"gluten free everything bagel",
"gluten free falafel frozen",
"gluten free flatbread crackers",
"gluten free florida keys",
"gluten free food in croatia",
"gluten free franchise",
"gluten free french bread pizza",
"gluten free french fries recipe",
"gluten free french recipes",
"gluten free french toast sticks frozen",
"gluten free fried oreos",
"gluten free fried oysters",
"gluten free frozen pizza dough",
"gluten free gefilte fish",
"gluten free gender reveal cake",
"gluten free gift cards",
"gluten free gingerbread house kit",
"gluten free gingerbread house kits",
"gluten free gingerbread kit",
"gluten free gooey butter cake",
"gluten free gourmet chocolates",
"gluten free graduation cookies",
"gluten free gravy granules",
"gluten free gravy mixes",
"gluten free greek cookies",
"gluten free greek recipes",
"gluten free hampers uk",
"gluten free hanukkah cookies",
"gluten free harvest bread",
"gluten free heart shaped pizza",
"gluten free hello dolly bars",
"gluten free hobnobs",
"gluten free homebrew beer kits",
"gluten free honey bun",
"gluten free hot water crust",
"gluten free hot water crust pastry",
"gluten free hotels italy",
"gluten free hungarian cookies",
"gluten free instapot recipes",
"gluten free invisible apple cake",
"gluten free islands of adventure",
"gluten free italian anise cookies",
"gluten free italian anisette cookies",
"gluten free italian cream cake",
"gluten free italian rainbow cookies",
"gluten free jalapeno cheddar bread",
"gluten free joe joe's",
"gluten free key lime cookies",
"gluten free kibbeh",
"gluten free king cake shipped",
"gluten free knish",
"gluten free koulourakia",
"gluten free kourabiedes",
"gluten free kreplach",
"gluten free kugel",
"gluten free lefse for sale",
"gluten free lefse with instant potatoes",
"gluten free lussekatter",
"gluten free m and m cookies",
"gluten free m&m cookie recipe",
"gluten free mac and cheese trader joe's",
"gluten free main dish for potluck",
"gluten free main dishes for potluck",
"gluten free mama flour",
"gluten free mandel bread",
"gluten free mango muffins",
"gluten free matzo ball soup mix",
"gluten free meat rubs",
"gluten free merch",
"gluten free mini cookies",
"gluten free mississippi mud pie",
"gluten free monkey bread with pizza dough",
"gluten free mooncakes",
"gluten free moravian cookies",
"gluten free moscow mule",
"gluten free mother's day",
"gluten free mr kipling",
"gluten free mystery box",
"gluten free new products",
"gluten free new york bagels shipped",
"gluten free non alcoholic drinks",
"gluten free noodle kugel",
"gluten free north shore",
"gluten free oat matzo",
"gluten free oatmeal butterscotch cookies"
"gluten free oatmeal scotchies"
"gluten free orecchiette pasta"
"gluten free oreo crust recipe"
"gluten free oreo ice cream"
"gluten free organic bagels"
"gluten free ornament"
"gluten free palmiers"
"gluten free pandoro"
"gluten free pasta gift baskets"
"gluten free pasta making class"
"gluten free pasta shells for stuffing"
"gluten free pasta suppliers"
"gluten free peach galette"
"gluten free peach rings"
"gluten free peanut butter balls recipe"
"gluten free peanut butter chocolate balls"
"gluten free pepparkakor"
"gluten free peppermint brownies"
"gluten free pepperoni bread"
"gluten free persimmon muffins"
"gluten free persimmon pudding"
"gluten free picnic hamper"
"gluten free pigs in a blanket frozen"
"gluten free pizza dough doves farm"
"gluten free pizza dough frozen"
"gluten free polish cookies"
"gluten free popcorn tins"
"gluten free pork recipes"
"gluten free porter"
"gluten free porter beer"
"gluten free premade cinnamon rolls"
"gluten free pretzel rings"
"gluten free protein pumpkin bread"
"gluten free pumpkin bread chocolate chip"
"gluten free pumpkin chocolate chip bread"
"gluten free pumpkin dip"
"gluten free pumpkin ice cream"
"gluten free pumpkin ravioli"
"gluten free pumpkin trifle"
"gluten free rainbow cookies"
"gluten free ramen packets"
"gluten free raspberry muffins"
"gluten free recipes ireland"
"gluten free red velvet brownies"
"gluten free resort costa rica"
"gluten free rhubarb tart"
"gluten free rice vinegar"
"gluten free riesling wine"
"gluten free rigatoni noodles"
"gluten free ring pasta"
"gluten free rosh hashanah recipes"
"gluten free rusks"
"gluten free russian dressing"
"gluten free saffron buns"
"gluten free sake"
"gluten free salisbury steak"
"gluten free salt dough"
"gluten free scones delivered"
"gluten free scones delivery"
"gluten free scones to buy"
"gluten free scones without xanthan gum"
"gluten free scotch eggs"
"gluten free scotland"
"gluten free seafood boil"
"gluten free seafood breader"
"gluten free semla"
"gluten free seoul"
"gluten free shampoo bar"
"gluten free sides for cookout"
"gluten free slider buns to buy"
"gluten free slow cooker potato soup"
"gluten free slutty brownies"
"gluten free snack box gift"
"gluten free snack packages"
"gluten free snickerdoodle bars"
"gluten free snow cone syrup"
"gluten free soju"
"gluten free soup mix"
"gluten free soup mixes"
"gluten free sour cream pound cake"
"gluten free sourdough bagel recipe"
"gluten free sourdough bread delivery"
"gluten free sourdough bread for sale"
"gluten free sourdough bread to buy"
"gluten free sourdough focaccia"
"gluten free sourdough kit"
"gluten free sourdough san francisco"
"gluten free sourdough starter for sale"
"gluten free spicy ramen"
"gluten free spicy ramen noodles"
"gluten free spinach bread"
"gluten free spinach casserole"
"gluten free ssamjang"
"gluten free st joseph zeppole"
"gluten free starter kit"
"gluten free sticker"
"gluten free stocking stuffers"
"gluten free stollen buy"
"gluten free stollen to buy"
"gluten free stromboli dough recipe"
"gluten free stromboli recipe"
"gluten free stuffed cabbage"
"gluten free stuffed cookies"
"gluten free stuffed pork chops"
"gluten free stuffed shells recipe"
"gluten free sugar cookie bars"
"gluten free sugar free cheesecake"
"gluten free sugar free pancakes"
"gluten free summer side dishes"
"gluten free super bowl"
"gluten free super bowl desserts"
"gluten free super bowl foods"
"gluten free superbowl snacks"
"gluten free swaps"
"gluten free swedish candy"
"gluten free sweet and sour sauce for meatballs"
"gluten free swiss roll to buy"
"gluten free t shirt"
"gluten free taralli"
"gluten free tea sandwiches"
"gluten free tequeños"
"gluten free thanksgiving dinner near me"
"gluten free toilet paper"
"gluten free tonic"
"gluten free turkey and dumplings"
"gluten free turkey recipes"
"gluten free vanilla vodka"
"gluten free vasilopita"
"gluten free vegan cupcakes delivery"
"gluten free vegan latkes"
"gluten free vegan perogies"
"gluten free vegan pierogi"
"gluten free vodka belvedere"
"gluten free wedding cake sampler"
"gluten free wedding cake samples"
"gluten free wedding cake tasting"
"gluten free wedding cakes"
"gluten free whipped shortbread cookies"
"gluten free white chocolate and cranberry cookies"
"gluten free white chocolate cranberry cookies"
"gluten free wiener schnitzel"
"gluten free wonton chips"
"gluten freedom sweet potato bread"
"gluten off bakery"
"gluten popcorn"
"gluten replacer"
"gluten revolution"
"gluten sugar free pumpkin bread"
"gluten test kit for beer"
"gluten-free communion bread recipe"
"gluten-free super bowl snacks"
"glutenberg beer gluten free"
"glúten de trigo"
"goat cheese cheesecake gluten free"
"good times gluten free"
"granoro gluten free pasta"
"great harvest bread company gluten free"
"great harvest bread gluten free"
"great harvest gluten free bread"
"greek gluten free card"
"haldiram gluten free chapati"
"hanukkah recipes gluten free"
"harina de avena integral sin gluten"
"harina de avena sin gluten"
"harvest bread company gluten free"
"hello dolly bars gluten free"
"hikari gluta"
"hoist glute master weight chart"
"hot water crust pastry gluten free"
"how much gluten is in guinness"
"how to engage glutes when running"
"individually wrapped gluten free communion wafers"
"individually wrapped gluten free cookies"
"is arroz con leche gluten free"
"is asahi gluten free"
"is beer cheese gluten free"
"is belvedere gluten free"
"is captain morgan sliced variety pack gluten free"
"is dashi gluten free"
"is dream oat milk gluten free"
"is dulce de leche gluten free"
"is fregola gluten free"
"is furikake gluten free"
"is garage beer gluten free"
"is gekkeikan sake gluten free"
"is korean fried chicken gluten free"
"is masago gluten free"
"is mich ultra gold gluten free"
"is mich ultra pure gold gluten free"
"is miller high life gluten free"
"is natamycin gluten free"
"is old dutch puffcorn gluten free"
"is parrot bay gluten free"
"is popeyes grilled chicken gluten-free"
"is popeyes red beans and rice gluten free"
"is shrimp fried rice gluten free"
"is truffle oil gluten free"
"ishin gluta"
"jack's bbq gluten free"
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
    threads = []
    for keyword in keywords:
        # Skip exact match keywords if they already exist
        post_exists = any(post["title"] == keyword for post in existing_posts)
        if not post_exists:
            # Create a thread for each blog post generation
            thread = threading.Thread(target=lambda k=keyword: blog_posts.append(generate_blog_post(k)))
            threads.append(thread)
            thread.start()
        else:
            print(f"Post already exists: {keyword}")
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Determine categories for new posts
    for post in blog_posts:
        if post:
            category, subcategory = determine_category(post['title'])
            categories[category].add(subcategory)
            post.update({
                "category": category,
                "subcategory": subcategory,
                "filename": sanitize_filename(f"{post['title']}.html")
            })
            print(f"Generated post: {post['title']} (Category: {category}/{subcategory})")
    
    # Combine existing posts and new posts
    all_posts = existing_posts + blog_posts
    
    # Save new posts using threading
    save_threads = []
    for post in blog_posts:
        if post:
            thread = threading.Thread(target=save_formatted_html, args=(post, output_dir, post['category'], post['subcategory']))
            save_threads.append(thread)
            thread.start()
    
    # Wait for all save threads to complete
    for thread in save_threads:
        thread.join()
    
    # Generate index.html, category pages, and subcategory pages
    generate_index_html(all_posts, output_dir, categories)
    generate_category_pages(categories, output_dir)
    generate_subcategory_pages(categories, output_dir, all_posts)
    
    # Generate sitemap.xml and robots.txt
    generate_sitemap(output_dir, all_posts)
    generate_robots_txt(output_dir)
    
    # Push changes to GitHub
    push_to_github()