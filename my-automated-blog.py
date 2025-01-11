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

# Function to generate index.html with updated card content
def generate_index_html(blog_posts, output_dir):
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
            <p>&copy; 2025 GFreeLife. All rights reserved. | <a href="/">Home</a></p>
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
"light gluten free beer", "lipton soup mix gluten free", "low sodium gluten free recipes", "lulu's gluten free menu", "mama's gluten free flour", "massimo zero gluten free pasta", "mellow mushroom gluten free crust ingredients", "mississippi pot roast gluten free", "molino flour gluten free", "molino gluten free flour", "mountain farm gluten free bread", "natamycin gluten free", "nautilus glute drive bar weight", "new gluten free", "new gluten free products 2024", "oatmeal chocolate chip bars gluten free", "oggi gluten free pizza crust", "orecchiette gluten free", "organic gluten free sourdough", "pan integral gluten free", "peptones for glutes", "premade gluten free cinnamon rolls", "price gun gluten free", "private label gluten free food manufacturers", "quesos sin lactosa y sin gluten", "raglan road gluten free menu", "red bowl gluten free menu", "ristoranti gluten free vicino a me", "sakura gluta brightening underarm cream", "san angel inn gluten free menu", "scotland gluten free", "serranos gluten free menu", "shiro gluta", "smallcakes gluten free", "soft glute bench", "soju gluten free", "soup mix gluten free", "spaghetti warehouse gluten free", "spicy gluten free ramen", "spinach gluten free pasta", "spinach noodles gluten free", "store bought gluten free cinnamon rolls", "sugar free gluten free wine", "surfside vodka gluten free", "sweet fa gluten free", "ta'amti gluten free", "thanksgiving recipes gluten free dairy free", "the fine cheese company gluten free crackers", "the hub gluten free menu", "trader joe's gluten free beer", "trader joe's gluten free pumpkin pancake mix recipes", "tsingtao beer gluten free", "vegan chocolate gluten free", "vegan gluten free gifts", "venezia gluten free pasta", "where can i buy gluten free cinnamon rolls", "where can i buy gluten free soda bread", "where to buy gluten free cannoli shells", "where to buy gluten free challah", "wow cookies gluten free", "yoyo biscuits gluten free", "abs and glute machine", "alcohol free gluten free beer", "almond bark gluten free", "angel hair gluten free pasta", "animal kingdom gluten free", "are almond roca gluten free", "are applebee's riblets gluten free", "are candy cigarettes gluten free", "are carnitas gluten free", "are charms sweet pops gluten free", "are coffee creamers gluten free", "are cookout fries gluten free", "are gumballs gluten free", "are kirkland semi sweet chocolate chips gluten free", "are lip smackers gluten free", "are malibu splash gluten free", "are oatmeal cream pies gluten free", "are potato donuts gluten free", "are snow cones gluten free", "are starburst swirlers gluten free", "are sunkist fruit gems gluten free", "are turtles chocolates gluten free", "asafetida gluten free", "asafoetida powder gluten free", "avoine gluten", "be our guest gluten free", "bear creek soup gluten free", "belvedere vodka gluten free", "best gluten free subscription box", "black eyed pea gluten free", "blonde gluten free beer", "borghetti espresso liqueur gluten free", "bouncer high gluten flour", "buca gluten free", "buckeyes gluten free", "bulk gluten free", "bulk gluten free oats", "bulk gluten free soy sauce", "buy gluten free biscuits", "buy gluten free sugar free birthday cake", "cajun seasoning gluten free", "candid white milf glutes", "canned gluten free cinnamon rolls", "caramel shortbread gluten free", "charms sweet pops gluten free", "chicken francese gluten free", "chili crisp gluten free", "chipotle sauce gluten free", "christmas food gifts for gluten free", "churrascos gluten free menu", "communion bread gluten free", "cookie crisp gluten free", "corn flake crumbs gluten free", "cottage cheese gluten free bread", "dairy free gluten free pancake mix", "demi glace gluten free", "does horchata have gluten", "does pho noodles have gluten", "does trader joe's have gluten free pizza dough", "doves farm free gluten free flour", "dream oat milk gluten free", "dumle gluten free", "el sillao tiene gluten", "emsculpt glutes before and after", "estrella damm beer gluten free", "estrella damm daura gluten free", "estrella galicia gluten free", "fettuccine pasta gluten free", "filipino food gluten free", "freee gluten free bread flour", "frothy monkey gluten free", "frozen gluten free cookie dough", "galletas maria gluten free", "glicks high gluten flour", "gluta c", "gluta c kojic plus", "gluta c with kojic plus", "gluta drip near me", "gluta milky cream", "gluta shots near me", "gluta-c soap intense whitening", "glute and ab machine", "glute leg machine", "gluten and dairy free food delivery", "gluten and dairy free party food", "gluten and dairy free potluck recipes", "gluten and dairy free recipes for thanksgiving", "gluten and dairy free super bowl recipes", "gluten food test strips", "gluten free almond extract", "gluten free alphabet pasta", "gluten free apple kugel", "gluten free assorted chocolates", "gluten free b and b", "gluten free bacon recipes", "gluten free bakery charlestown", "gluten free bakery gig harbor", "gluten free banana bread with sour cream", "gluten free beer and cider", "gluten free beer greens", "gluten free beer sampler", "gluten free big island", "gluten free blini recipe", "gluten free blonde beer", "gluten free blt", "gluten free bread box", "gluten free buckeyes", "gluten free business for sale", "gluten free butterfly shrimp", "gluten free butternut squash ravioli", "gluten free buñuelos recipe", "gluten free cacio e pepe", "gluten free cake shipped", "gluten free challah los angeles", "gluten free cheese straw recipe", "gluten free chicken marsala", "gluten free chili crisp", "gluten free chinese almond cookies", "gluten free chocolate box", "gluten free chocolate covered strawberries", "gluten free chocolate croissant", "gluten free chocolate gift box", "gluten free chocolate gifts", "gluten free chocolate mousse pie", "gluten free chocolate peppermint cake", "gluten free christmas cookies to order", "gluten free christmas ornaments", "gluten free christmas tree cakes", "gluten free cinnamon raisin muffins", "gluten free cinnamon roll pancakes", "gluten free cinnamon toast crunch", "gluten free cocktail sausages", "gluten free colonoscopy prep", "gluten free communion bread", "gluten free corn meal mix", "gluten free cranberry oatmeal cookies", "gluten free crock pot lasagna", "gluten free cupcakes grand rapids mi", "gluten free custard pie", "gluten free dairy free subscription box", "gluten free dairy free sugar free cookbook", "gluten free dairy free super bowl snacks", "gluten free dairy free thanksgiving", "gluten free deep fried oreos", "gluten free donuts delivery", "gluten free downtown disney", "gluten free dutch oven peach cobbler", "gluten free eclair cake", "gluten free eclair recipe", "gluten free elephant ears", "gluten free estrella galicia", "gluten free fall baking", "gluten free farmers market englewood", "gluten free festival", "gluten free finger sandwiches", "gluten free fish patties", "gluten free flour 25 lbs", "gluten free food in china", "gluten free food samples", "gluten free food tour london", "gluten free food tour paris", "gluten free fortune cookie recipe", "gluten free fried ravioli", "gluten free gouda mac and cheese", "gluten free gourmet chocolate", "gluten free grasshopper pie", "gluten free greens", "gluten free hefeweizen", "gluten free hot cocoa bombs", "gluten free hot water pastry", "gluten free hotel new york", "gluten free hula hoops", "gluten free in china", "gluten free in korea", "gluten free in scotland", "gluten free indian snacks to buy", "gluten free individually wrapped snacks", "gluten free instant pot", "gluten free international snack box", "gluten free japanese beer", "gluten free king cake baton rouge", "gluten free king cake shipping", "gluten free lasagna crock pot", "gluten free lemon blueberry scones", "gluten free licorice canada", "gluten free liege waffles", "gluten free little debbie christmas tree cakes", "gluten free low sodium bread", "gluten free m&m cookies", "gluten free mango cake", "gluten free maple bars", "gluten free meat sticks", "gluten free memorial day recipes", "gluten free mexico city", "gluten free mississippi pot roast", "gluten free mithai", "gluten free mojito", "gluten free mooncake", "gluten free mooncake recipe", "gluten free mother's day brunch", "gluten free mother's day gift", "gluten free mother's day gifts", "gluten free movie snacks", "gluten free muffaletta", "gluten free oat rolls", "gluten free oats bulk", "gluten free oreo cookie crust", "gluten free oreo cupcakes", "gluten free oreo pie crust", "gluten free pappardelle pasta", "gluten free pasta rings", "gluten free pecan pie brownies", "gluten free pesto pizza", "gluten free pizza bagels", "gluten free platters", "gluten free pork rub", "gluten free puffed rice", "gluten free pumpernickel bagels", "gluten free pumpernickel recipe", "gluten free rainbow cake", "gluten free salisbury steak recipe", "gluten free salmon marinade", "gluten free sand tarts", "gluten free sandwich platters", "gluten free slow cooker lasagna", "gluten free souffle cheese", "gluten free sour beer", "gluten free sourdough bagels", "gluten free sourdough bread online", "gluten free sourdough waffles", "gluten free soy free bread", "gluten free soy free crackers", "gluten free spaghetti carbonara", "gluten free spinach pasta", "gluten free spring rolls frozen", "gluten free square pretzels", "gluten free strawberry ice cream", "gluten free strawberry rhubarb muffins", "gluten free stromboli", "gluten free sugar free cake mix", "gluten free sweet and sour chicken", "gluten free tarte tatin", "gluten free tequila brands", "gluten free teriyaki chicken recipe", "gluten free thanksgiving meals to order", "gluten free thanksgiving order", "gluten free tinted moisturizer", "gluten free tortellini soup", "gluten free tours of italy", "gluten free tres leches near me", "gluten free twice baked potatoes", "gluten free twisted tea", "gluten free ube cookies", "gluten free vegetarian products", "gluten free wasabi peas", "gluten free water crackers", "gluten free wedding catering", "gluten free welsh cakes", "gluten free whipped shortbread", "gluten free wholesalers", "gluten pork", "gluten-free bread pudding with bourbon sauce", "gluten-free school lunch ideas for picky eaters", "gluten-free side dishes for bbq", "glutes workout bench", "gooey butter cake gluten free", "harina p.a.n. gluten free", "harina pan gluten free", "heartland gluten free pasta", "heritage high gluten flour", "immaculate gluten free cookies", "is asahi beer gluten free", "is bear creek soup gluten free", "is blackened seasoning gluten free", "is chicken francese gluten free", "is crown royal whiskey lemonade gluten free", "is good and gather chicken broth gluten free", "is green goddess dressing gluten free", "is idli gluten free", "is kettle corn gluten free", "is kinky gluten free", "is kirin beer gluten free", "is lipton beefy onion soup mix gluten free", "is malai kofta gluten free", "is mango sticky rice gluten free", "is marsala sauce gluten free", "is ratatouille gluten free", "is salisbury steak gluten free", "is screwball whisky gluten free", "is smirnoff vanilla vodka gluten free", "is swedish candy gluten free", "is taco dip gluten free", "is tattoo ink gluten free", "is tecate gluten free", "is the kraken rum gluten free", "is tonic water gluten free", "is tony's creole seasoning gluten free", "is tony's gluten free", "italian rainbow cookies gluten free", "jl beers gluten free", "jordan almonds gluten free", "kim's gluten free flour blend", "knish gluten free", "kosher gluten free", "kyrol high gluten flour", "las almendras contienen gluten", "luxxe white gluta", "malt loaf gluten free", "metabolic maintenance l-methylfolate 10mg - gluten-free", "michelob ultra gold gluten free", "michelob ultra pure gold gluten free", "namaste gluten free flour recipes", "new amsterdam gluten free", "new gluten free products", "outback.gluten free menu", "outer banks gluten free", "pappardelle gluten free pasta", "pcos gluten and dairy free", "peanut brittle gluten free", "peanut butter balls gluten free", "popeyes blackened chicken gluten free", "pozole gluten free", "pre made gluten free pizza dough", "premade gluten free cookie dough", "prodynorphin in gluten", "pumpkin beer gluten free", "reverse glute ham machine", "rochester ny gluten free bakery", "salisbury steak recipe gluten free", "sarasota gluten free bakery", "schär gluten free online shop", "scrapple gluten free", "shawarma gluten free", "sheetz gluten free menu", "shumai gluten free", "sope gluten free", "spanish beer gluten free", "spanish gluten free beer", "sticky fingers gluten free scone mix"]
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
    
    # Generate index.html
    generate_index_html(all_posts, output_dir)
    
    # Generate sitemap.xml and robots.txt using threading
    sitemap_thread = threading.Thread(target=generate_sitemap, args=(output_dir, all_posts))
    robots_thread = threading.Thread(target=generate_robots_txt, args=(output_dir,))
    sitemap_thread.start()
    robots_thread.start()
    sitemap_thread.join()
    robots_thread.join()
    
    # Push changes to GitHub
    push_to_github()