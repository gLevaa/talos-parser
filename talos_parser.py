import sys
import json

from time import time
from enum import Enum
from html import unescape

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


class PostType(Enum):
    TEXT = 0
    CROSSPOST = 1
    INTERNAL_IMAGE = 2
    INTERNAL_VIDEO = 3
    EXTERNAL_IMAGE = 4
    EXTERNAL_VIDEO = 5
    EXTERNAL_LINK = 6

class PostParser:
    def __init__(self, data):
        self.post_data = data[0]["data"]["children"][0]["data"]
        #comment_data = data[1]["data"]

        self.parsed = {"status": "success", "type": None}
    
    def parse(self):
        try:
            if "[deleted]" in self.post_data["selftext"]:
                self.parsed["type"] = "deleted"
                return

            post_type = self.determine_post_type()
            self.parse_generalised_fields()

            parse_types = {
                PostType.TEXT: self.parse_text,
                PostType.CROSSPOST: self.parse_crosspost,
                PostType.INTERNAL_IMAGE: self.parse_image,
                PostType.EXTERNAL_IMAGE: self.parse_image,
                PostType.INTERNAL_VIDEO: self.parse_video,
                PostType.EXTERNAL_VIDEO: self.parse_video,
                PostType.EXTERNAL_LINK: self.parse_link,
            }

            is_internal = post_type not in {PostType.EXTERNAL_IMAGE, PostType.EXTERNAL_VIDEO, PostType.EXTERNAL_LINK}
            parse_types[post_type](is_internal)
        except Exception as e:
            self.parsed = {"status": "failure", "error": f"{str(e)}"}

    def parse_generalised_fields(self):
        self.parsed["id"] = self.post_data["id"]
        self.parsed["title"] = self.post_data["title"]
        self.parsed["subreddit"] = self.post_data["subreddit_name_prefixed"]
        self.parsed["text"] = self.post_data["selftext"]
        self.parsed["flair"] = self.post_data["link_flair_text"]
        self.parsed["upvotes"] = self.post_data["ups"]
        self.parsed["upvote_ratio"] = self.post_data["upvote_ratio"]
        self.parsed["num_rewards"] = self.post_data["total_awards_received"]
        self.parsed["num_crossposts"] = self.post_data["num_crossposts"]
        self.parsed["num_comments"] = self.post_data["num_comments"]
        
        self.parsed["is_over_18"] = self.post_data["over_18"]
        self.parsed["is_quarantined"] = self.post_data["quarantine"]
        self.parsed["is_locked"] = self.post_data["locked"]
        self.parsed["is_author_premium"] = self.post_data["author_premium"]

        self.parsed["published_at"] = int(self.post_data["created"])
        self.parsed["post_link"] = self.gen_link_from_suffix(self.post_data["permalink"])

        self.parsed["crawled_at"] = int(time())

    def parse_text(self, is_internal):
        self.parsed["type"] = "text"
        self.parsed["is_internal"] = is_internal

    def parse_crosspost(self, is_internal):
        self.parsed["type"] = "crosspost"
        self.parsed["is_internal"] = is_internal
        self.parsed["content"] = self.gen_link_from_suffix(self.post_data["crosspost_parent_list"][0]["permalink"])

    def parse_image(self, is_internal):
        self.parsed["type"] = "image"
        self.parsed["is_internal"] = is_internal

        if "gallery_data" in self.post_data:
            media = self.post_data["media_metadata"]
            content = []
            for image in media.keys():
                image_link = media[image]["s"]["u"]
                content.append(unescape(image_link))
                self.parsed["content"] = content
        else:
            self.parsed["content"] = [self.post_data["url_overridden_by_dest"]]

    def parse_video(self, is_internal):
        self.parsed["type"] = "video"
        self.parsed["is_internal"] = is_internal

        if is_internal:
            self.parsed["content"] = [self.post_data["secure_media"]["reddit_video"]["fallback_url"]]
        else:
            self.parsed["content"] = [self.post_data["url_overridden_by_dest"]]

    def parse_link(self, is_internal):
        self.parsed["type"] = "link"
        self.parsed["is_internal"] = is_internal
        self.parsed["content"] = [self.post_data["url"]]

    def determine_post_type(self):
        # https://developer.mozilla.org/en-US/docs/Web/Media/Formats/Image_types
        image_extensions = [".apng", ".avif", ".gif", ".gifv", ".jpg", ".jpeg", ".jfif", ".pjpeg",\
            ".pjp", ".png", ".svg", ".webp", ".bmp", ".ico", ".cur", ".tif", ".tiff"]
        
        url                 = self.post_data["url"]
        media               = self.post_data["media"]
        domain              = self.post_data["domain"]

        # domain can be null if post is deleted, causing en error. lazy evaluate domain_is_self
        # (i.e. if term 1 is true, term 2 wont be executed)
        domain_is_self      = self.post_data["is_self"] or f"self.{self.post_data['subreddit']}" in self.post_data["domain"]
        is_self             = self.post_data["is_self"]
        contains_crosspost  = "crosspost_parent_list" in self.post_data
        contains_gallery    = "gallery_data" in self.post_data
        
        if is_self or domain_is_self:   return PostType.TEXT
        elif contains_crosspost:        return PostType.CROSSPOST
        elif "i.redd.it" in domain:     return PostType.INTERNAL_IMAGE
        elif contains_gallery:          return PostType.INTERNAL_IMAGE
        elif "v.redd.it" in domain:     return PostType.INTERNAL_VIDEO
        
        if any(extension in url for extension in image_extensions) or ("gfycat" in url):
            return PostType.EXTERNAL_IMAGE
        elif media == None:
            return PostType.EXTERNAL_LINK
        else:
            return PostType.EXTERNAL_VIDEO

    def gen_link_from_suffix(self, link):
        return f"https://old.reddit.com{link}"


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
    
    f.close()

if __name__ == "__main__":
    main()

"""
import requests
def test():
    try:
        f = open('page.json')
        data = json.load(f)
    except:
        print("page.json not found, or invalid JSON structure.")
    
    # data = homepage
    s_parser = SourceParser(data, None, 0)
    s_parser.parse()
    pprint(s_parser.parsed)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'}
    for url in s_parser.parsed["urls"]:
        r = requests.get(url + ".json", headers=headers)
        open('page.json', 'wb').write(r.content)

        g = open('page.json')
        data = json.load(g)

        parser = PostParser(data)
        parser.parse()
        pprint(parser.parsed)

        g.close()

    f.close()
"""

