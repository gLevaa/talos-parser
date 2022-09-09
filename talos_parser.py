import sys
import json
from pprint import pprint
class SourceParser:
    def __init__(self, data, sort_by, count):
        self.data = data
        self.sort_by = sort_by
        self.count = count

        self.post_table = None
        self.next_id = None

        self.parsed = {"urls": [], "next": None, "status": "success"}
    
    def parse(self):
        try:
            if not self.sort_by_is_valid():
                raise ValueError("The 'sort_by' parameter is invalid.")

            self.set_fields_after_validation() # self.data, self.post_table

            for post in self.post_table:
                post = post["data"]
                self.parsed["urls"].append(self.gen_url(post))
            self.parsed["next"] = self.gen_next_url(post["subreddit_name_prefixed"])
        except Exception as e:
            self.parsed = {"status": "failure", "error": f"{str(e)}"}

    def gen_url(self, post):
        url_suffix = post["permalink"] # /r/subreddit/comments/id/words_in_title/
        return f"https://old.reddit.com{url_suffix}"

    def gen_next_url(self, subreddit_name_prefixed):
        next_id = self.data["after"]
        if self.sort_by != "":
            next = f"https://old.reddit.com/{subreddit_name_prefixed}/{self.sort_by}/?count={self.count + 25}&after={next_id}"
        else:
            next = f"https://old.reddit.com/{subreddit_name_prefixed}/?count={self.count + 25}&after={next_id}"

        return next

    def set_fields_after_validation(self):
        # these can cause errors, any of which will be handled by try/except
        self.data = self.data["data"]
        self.post_table = self.data["children"]
        self.count = int(self.count)

    def sort_by_is_valid(self):
        if self.sort_by in ["new", "rising", "controversial", "top", None]:
            if self.sort_by == None: self.sort_by = ""

            return True
        return False

def is_source(data):
    if "kind" in data:
        return True
    return False

def main():
    try:
        f = open('page.json')
        data = json.load(f)
    except:
        print("page.json not found, or invalid JSON structure.")

    if is_source(data):
        parser = SourceParser(data=data, sort_by=None, count=sys.argv[1])
        parser.parse()
        print(parser.parsed)
    else:
        pass

if __name__ == "__main__":
    main()