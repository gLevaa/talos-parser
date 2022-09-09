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

## Usage
`talos_parser.py` takes command line arguments, and relies on the existence of `page.json`, the file with the JSON API data.

### **Sources**
Simply run `talos_parser.py (int)count`, where count denotes the count of the source page (found in the URL, /?count=25, or just reddit.com/ where count = 0).

In the case of a successful parse, the output will be; <br>
`{'status': 'success', 'next': 'link_to_next', 'urls': ['url1', ..., 'url25']}`

In the case of a failed parsed, the output will be;<br>
`{'status': 'failure', 'error': "exception"}`

### **Posts**
TODO