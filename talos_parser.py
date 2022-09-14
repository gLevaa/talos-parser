from time import sleep, time
from enum import Enum
from html import unescape

from pprint import pprint

class PostType(Enum):
    TEXT = 0
    CROSSPOST = 1
    INTERNAL_IMAGE = 2
    INTERNAL_VIDEO = 3
    EXTERNAL_IMAGE = 4
    EXTERNAL_VIDEO = 5
    EXTERNAL_LINK = 6

class SourceParser:
    def __init__(self, data: dict, sort_by: str | None, count: int) -> None:
        self.data = data
        self.sort_by = sort_by
        self.count = count

        self.post_table = None
        self.next_id = None

        self.parsed = {"urls": [], "next": None, "status": "success"}

    def get_parsed(self) -> dict:
        return self.parsed
    
    def parse(self) -> None:
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

    def gen_url(self, post: dict) -> None:
        url_suffix = post["permalink"] # /r/subreddit/comments/id/words_in_title/
        return f"https://reddit.com{url_suffix}"

    def gen_next_url(self, subreddit_name_prefixed: str) -> str:
        next_id = self.data["after"]
        if self.sort_by != "":
            next = f"https://reddit.com/{subreddit_name_prefixed}/{self.sort_by}/.json?count={self.count + 25}&after={next_id}"
        else:
            next = f"https://reddit.com/{subreddit_name_prefixed}/.json?count={self.count + 25}&after={next_id}"

        return next

    def set_fields_after_validation(self) -> None:
        # these can cause errors, any of which will be handled by try/except
        self.data = self.data["data"]
        self.post_table = self.data["children"]
        self.count = int(self.count)

    def sort_by_is_valid(self) -> None:
        if self.sort_by in ["new", "rising", "controversial", "top", None]:
            if self.sort_by == None: self.sort_by = ""

            return True
        return False

class PostParser:
    def __init__(self, data: dict) -> None:
        self.data = data
        self.post_data = data[0]["data"]["children"][0]["data"]

        self.parsed = {"status": "success", "type": None}

    def get_parsed(self) -> dict:
        return self.parsed
    
    def parse(self) -> None:
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

    def parse_generalised_fields(self) -> None:
        try:
            self.parsed["author_id"] = self.post_data["author_fullname"]
            self.parsed["is_author_premium"] = self.post_data["author_premium"]
        except:
            # field DNE if deleted
            self.parsed["author_id"] = None
            self.parsed["is_author_premium"] = False

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
        

        self.parsed["published_at"] = int(self.post_data["created"])
        self.parsed["post_link"] = self.gen_link_from_suffix(self.post_data["permalink"])

        self.parsed["crawled_at"] = int(time())

        comment_parser = CommentParser(self.data)
        comment_parser.parse()
        self.parsed.update(comment_parser.get_parsed())

    def parse_text(self, is_internal: bool) -> None:
        self.parsed["type"] = "text"
        self.parsed["is_internal"] = is_internal

    def parse_crosspost(self, is_internal: bool) -> None:
        self.parsed["type"] = "crosspost"
        self.parsed["is_internal"] = is_internal
        self.parsed["content"] = self.gen_link_from_suffix(self.post_data["crosspost_parent_list"][0]["permalink"])

    def parse_image(self, is_internal: bool) -> None:
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

    def parse_video(self, is_internal: bool) -> None:
        self.parsed["type"] = "video"
        self.parsed["is_internal"] = is_internal

        if is_internal:
            self.parsed["content"] = [self.post_data["secure_media"]["reddit_video"]["fallback_url"]]
        else:
            self.parsed["content"] = [self.post_data["url_overridden_by_dest"]]

    def parse_link(self, is_internal: bool) -> None:
        self.parsed["type"] = "link"
        self.parsed["is_internal"] = is_internal
        self.parsed["content"] = [self.post_data["url"]]

    def determine_post_type(self) -> PostType:
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

    def gen_link_from_suffix(self, suffix: str) -> None:
        return f"https://reddit.com{suffix}"

class CommentParser:
    def __init__(self, data: dict) -> None:
        self.comment_data = data[1]["data"]["children"]
        self.parsed = {"errors":[], "comments":[]}

    def get_parsed(self) -> dict:
        return self.parsed

    def parse(self) -> None:
        for root_comment in self.comment_data:
            self.recursive_parse(root_comment)

    def recursive_parse(self, root: dict) -> None:
        if root["kind"] != "t1": # comment identifier
            return
        
        self.parse_comment(root["data"])
        
        try:
            children = root["data"]["replies"]["data"]["children"]
            for child in children:
                self.recursive_parse(child)
        except TypeError:
            # in the case of no child comments
            pass
        except Exception as e:
            self.parsed["errors"].append(str(e))
    
    
    def parse_comment(self, comment_data: dict) -> None:
        parsed_comment = {}
        try:
            if "t3" in comment_data["parent_id"]:
                # parent is the post
                parsed_comment["parent_id"] = None
            else:
                parsed_comment["parent_id"] = comment_data["parent_id"]

            if "author_fullname" not in comment_data:
                # deleted comment
                parsed_comment["author_id"]         = None
                parsed_comment["is_author_premium"] = False
            else:
                parsed_comment["author_id"]         = comment_data["author_fullname"]
                parsed_comment["is_author_premium"] = comment_data["author_premium"]

            parsed_comment["id"]                = comment_data["name"]
            parsed_comment["text"]              = comment_data["body"]
            parsed_comment["subreddit"]         = comment_data["subreddit_name_prefixed"]
            parsed_comment["upvotes"]           = comment_data["ups"]
            parsed_comment["depth"]             = comment_data["depth"]
            parsed_comment["num_awards"]        = comment_data["total_awards_received"]
            parsed_comment["published_at"]      = int(comment_data["created"])
            parsed_comment["is_controversial"]  = bool(comment_data["controversiality"])
            parsed_comment["is_score_hidden"]   = comment_data["score_hidden"] # upvotes = -1 if hidden?
            parsed_comment["is_locked"]         = comment_data["locked"]
            parsed_comment["permalink"]         = comment_data["permalink"] # convert to link

            if len(comment_data["replies"]) == 0:
                parsed_comment["num_children"] = 0
            else:
                parsed_comment["num_children"] = len(comment_data["replies"]["data"]["children"])

            self.parsed["comments"].append(parsed_comment)
        except Exception as e:
            self.parsed["errors"].append(str(e))

def is_source(data: dict) -> bool:
    if "kind" in data:
        return True

    return False


"""
import json
import requests
result = {"sources":[]}
def test(iter=0, count=0):
    try:
        f = open('page.json')
        data = json.load(f)
    except:
        print("page.json not found, or invalid JSON structure.")
        exit()
    
    # data = homepage
    s_parser = SourceParser(data, None, 25*iter)
    s_parser.parse()
    count += 1
    print(count)
    result["sources"].append(s_parser.get_parsed())

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'}
    for url in s_parser.parsed["urls"]:
        r = requests.get(url + ".json", headers=headers)
        open('page.json', 'wb').write(r.content)

        g = open('page.json')
        data = json.load(g)

        parser = PostParser(data)
        parser.parse()
        result[url] = parser.get_parsed()

        count +=1
        print(count)

        g.close()

        sleep(2)
    
    r = requests.get(s_parser.parsed["next"], headers=headers)
    open('page.json', 'wb').write(r.content)

    f.close()

    if iter == 2:
        return
    
    test(iter + 1, count)
try:
    test()
except Exception as e:
    result = json.dumps(result)
    with open("output.json", "w") as o:
        o.write(result)
    raise(e)

result = json.dumps(result)
with open("output.json", "w") as o:
    o.write(result)

import json
try:
    f = open('page.json')
    data = json.load(f)
except:
    print("page.json not found, or invalid JSON structure.")

p = PostParser(data)
p.parse()

result = json.dumps(p.get_parsed())
with open("output.json", "w") as o:
    o.write(result)

print("done")
"""