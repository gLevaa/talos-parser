# talos-parser
This is the parser used for [talos](https://www.github.com/gLevaa/talos), a distributed Reddit web crawler.

It is designed to take Reddit JSON API data and extract a meaningful output, with an emphasis on data collection for analysis. 

- Extracts the 'next' page as well as post URLs from the homepage of a subreddit
- Extracts a collection of data from posts
    - General data, applying to all types of posts; title, text, upvotes, flair, creation time, etc.
    - Type-specific data
        - The post type
        - Internal image/video references
        - External image/video references
        - External link references
        - Crosspost references

<ins>Note</ins>: For this project, 'source' denotes a homepage, and 'post' denotes a specific post. 


# Usage
This section outlines quick usage. For more detail, see the documentation section.

## Using the `parser.py` interface 
Ensure that `page.json` exists.

### **Sources**
```py
"""
count: (int) -> the ?count= parameter of the source URL, e.g.
    - https://old.reddit.com/r/all -> count = 0
    - https://old.reddit.com/r/all/?count=25&... -> count = 25
"""
python ./parser.py (int)count

# Successful parse
python ./parser.py 0
{'status': 'success',
 'next': 'https://old.reddit.com/r/subreddit/?count=25&after=t3_id',
 'urls': ['https://old.reddit.com/r/subreddit/comments/id/title',
            ...,
          'https://old.reddit.com/r/subreddit/comments/id/title']
}

# Failed parse
python ./parser.py 0
{'status': 'failure', 'error': 'string form of exception'}
```
<ins>Note</ins>: `0` is an example argument. This should match the count parameter, as outlined in the docstring within the example.

### **Posts**
```py
python ./parser.py

# Successful parse
python ./parser.py
{'crawled_at': int, # Unix/Epoch time, used for talos crawler
 'flair': str | None,
 'id': str,
 'is_author_premium': bool,
 'is_internal': bool, # is content hosted on Reddit
 'is_locked': bool,
 'is_over_18': bool,
 'is_quarantined': bool,
 'num_comments': int,
 'num_crossposts': int,
 'num_rewards': int,
 'post_link': str,
 'published_at': int, # Unix/Epoch time
 'status': str,
 'subreddit': str, # r/sub
 'text': str,
 'title': str,
 'type': PostType (enum),
 'upvote_ratio': float,
 'upvotes': int 
 'errors': []
 'comments': [
    {
        "parent_id": str
        "author_id": str
        "is_author_premium": bool
        "id": str
        "text": str
        "subreddit": str # r/sub
        "upvotes": int,
        "depth": int, # comment depth, root = 0, child = 1
        "num_awards": 0,
        "published_at": int, # Epoch/Unix time
        "is_controversial": bool,
        "is_score_hidden": bool,
        "is_locked": bool,
        "permalink": str
        "num_children": int
    }, ...
 ]} 

# Failed parse
python ./parser.py
{'status': 'failure', 'error': 'string form of exception'}
```
<ins>Note</ins>: The dictionary arguments are in no specific order. Some sorting would need to be done for the sake of presentability.

<br>

## Using the `talos_parser.py` library
Again, ensure `page.json` exists.

`talos_parser.py` itself contains the following;
- ``SourceParser(data: dict, sort_by: str | None, count: int): class``
- ``PostParser(data: dict): class``
- ``CommentParser(data: dict): class``
- ``is_source(data: dict) -> bool``
- ``PostType(Enum)``

In all cases, ``data`` is the returned JSON API call.

For ``SourceParser``, `sort_by` is the Reddit URL sort, i.e. `"new", "rising", "controversial", "top", None`. It must match the source URL.

For ``PostParser``, ``CommentParser`` is called automatically.

```py
import talos_parser
from pprint import pprint # optional, JSON formatting

try:
    f = open('page.json')
    data = json.load(f)
except:
    print("page.json not found, or invalid JSON structure.")

if talos_parser.is_source(data):
    parser = talos_parser.SourceParser(data=data, sort_by=None, count=0)
    parser.parse()
else:
    parser = talos_parser.PostParser(data)
    parser.parse()

pprint(parser.get_parsed()) # print() works equally
```

## Use case: Python based Reddit scraper
Using the talos parser, a Python based Reddit scraper can be made relatively easily.
```py
from talos_parser import SourceParser, PostParser

import json
import requests
from time import sleep

ITERATIONS = 1 # crawl one source page of posts
SEED = "https://reddit.com/r/newzealand/new/.json"

headers = {'User-Agent': '...'}
def fetch_content(url=SEED):
    req = requests.get(url, headers=headers)
    open('page.json', 'wb').write(req.content)


def fetch_data():
    current_page = open('page.json')
    data = json.load(current_page)
    current_page.close()

    return data


def crawl(result, iteration=1, page_count=0):
    try:
        fetch_content(result["sources"][-1])
    except:
        fetch_content() # trigger SEED default param
    
    data = fetch_data()

    # At the start of crawl(), page.json will always be a source
    source_parser = SourceParser(data, "new", (iteration-1)*25)
    source_parser.parse()
    source = source_parser.get_parsed()

    result["sources"].append(source["next"])

    page_count += 1

    for post in source["urls"]:
        fetch_content(post)
        data = fetch_data()

        post_parser = PostParser(data)
        post_parser.parse()
        result[post] = post_parser.get_parsed()

        page_count += 1
        sleep(2)
    
    fetch_content(source["next"])

    if iteration == ITERATIONS:
        try:
            result = json.dumps(result)
            with open("output.json", "w") as output:
                output.write(result)
        except:
            print("Could not write to file")
            print(result)
        return
    
    crawl(result, iteration + 1, page_count)


result = {"sources":[]}
crawl(result)
```
The output for this crawl can be found [here](https://raw.githubusercontent.com/gLevaa/talos-parser/main/crawl_output.json). I recommend [this tool](http://json.parser.online.fr/) for formatting the JSON into a readable, interactive format.