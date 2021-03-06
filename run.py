import re
from paa import Google
from mongoconnect import get_database
import string

db = get_database()
articlestruct = db["articlestruct"]
tag_priority = { "h1": 3, "h2": 2, "h3": 1 }

def to_url(string):
    remove_punc = re.sub('[^A-Za-z0-9\s-]+', '', string.strip())
    return re.sub('[\s]+', '-', remove_punc).lower()

def should_search(question, article_structure, tag):
    id = to_url(string.capwords(question))
    if id in article_structure["structure"]:
        inline = tag_priority[article_structure["structure"][id]["tag"]]
        toadd = tag_priority[tag]
        if inline < toadd:
            return True
        return False
    else:
        return True

def get_info(question, article_structure=None, tag=None):
    printed = False
    tries = 0
    if article_structure == None or should_search(question, article_structure, tag):
        while not printed:
            try:
                google = Google()
                result = google.get_answer(question)
                if result['related_questions'] or result['has_answer']:
                    if result['has_answer']:
                        return {
                            "question": string.capwords(question),
                            "answer": result['response'],
                            "related": result['related_questions'],
                            "youtube": result['youtube'],
                            "sourcetitle": result['title'],
                            "sourcelink": result['link']
                        }
                    else:
                        return {
                            "question": string.capwords(question),
                            "answer": "",
                            "related": result['related_questions'],
                            "youtube": result['youtube'],
                            "sourcetitle": "",
                            "sourcelink": ""
                        }

                elif tries == 5:
                    printed = True
                else:
                    tries += 1
            except Exception as e:
                e
    return {}

def duplicate_check(to_check, toadd, tag_priority, article_structure, duplicates, answer, content, youtube, id, question, tag, answer_id, youtube_id, sourcetitle, sourcelink):
    if to_check == "id":
        inline = tag_priority[article_structure["structure"][id]["tag"]]
    elif to_check == "content":
        inline = tag_priority[article_structure["structure"][duplicates["content"][content]]["tag"]]
    elif to_check == "youtube":
        inline = tag_priority[article_structure["structure"][duplicates["youtube"][youtube]]["tag"]]

    if inline < toadd:
        if to_check == "id":
            content_delete = to_url(article_structure["structure"][id]["answer"])
            youtube_delete = article_structure["structure"][id]["youtube"]
            del article_structure["structure"][id]
            if content_delete:
                del duplicates["content"][content_delete]
            if youtube_delete:
                del duplicates["youtube"][youtube_delete]
        if to_check == "content":
            youtube_delete = article_structure["structure"][answer_id]["youtube"]
            if answer_id:
                del article_structure["structure"][answer_id]
            if content:
                del duplicates["content"][content]
            if youtube_delete:
                del duplicates["youtube"][youtube_delete]
        if to_check == "youtube":
            article_structure["structure"][youtube_id]["youtube"] = ""
            duplicates["youtube"][youtube] = id
        
        if content:
            duplicates["content"][content] = id
        if youtube:
            duplicates["youtube"][youtube] = id
        article_structure["structure"].update(
            {id: {
                "question": question,
                "answer": answer,
                "youtube": youtube,
                "tag": tag,
                "sourcetitle": sourcetitle,
                "sourcelink": sourcelink
            }}
        )
    else:
        if to_check == "youtube" and not id in article_structure["structure"] and not content in duplicates["content"]:
            if content and not ("https://www.youtube.com/watch?" in content):
                duplicates["content"][content] = id
                article_structure["structure"].update(
                    {id: {
                        "question": question,
                        "answer": answer,
                        "youtube": "",
                        "tag": tag,
                        "sourcetitle": sourcetitle,
                        "sourcelink": sourcelink
                    }}
                )

def add_structure(article_structure, duplicates, question, tag, answer, youtube, sourcetitle, sourcelink):
    id, content = to_url(question), to_url(answer)
    duplicate_id, duplicate_answer, duplicate_youtube = id in article_structure["structure"], content in duplicates["content"], youtube in duplicates["youtube"]
    if duplicate_id or duplicate_answer or duplicate_youtube:
        toadd, answer_id, youtube_id = tag_priority[tag], None, None
        if duplicate_answer and content:
            answer_id = duplicates["content"][content]
        if duplicate_youtube and youtube:
            youtube_id = duplicates["youtube"][youtube]
        if duplicate_id:
            duplicate_check("id", toadd, tag_priority, article_structure, duplicates, answer, content, youtube, id, question, tag, answer_id, youtube_id, sourcetitle, sourcelink)
        if id != answer_id and duplicate_answer:
            duplicate_check("content", toadd, tag_priority, article_structure, duplicates, answer, content, youtube, id, question, tag, answer_id, youtube_id, sourcetitle, sourcelink)
        if id != youtube_id and duplicate_youtube:
            duplicate_check("youtube", toadd, tag_priority, article_structure, duplicates, answer, content, youtube, id, question, tag, answer_id, youtube_id, sourcetitle, sourcelink)
    else:
        if content:
            duplicates["content"][content] = id
        if youtube:
            duplicates["youtube"][youtube] = id
        article_structure["structure"].update(
            {id: {
                "question": question,
                "answer": answer,
                "youtube": youtube,
                "tag": tag,
                "sourcetitle": sourcetitle,
                "sourcelink": sourcelink
            }}
        )

def make_article(header):
    info = get_info(header)
    if not info:
        return
    duplicates = { "content": {}, "youtube": {} }
    article_structure = { "_id": to_url(info["question"]), "structure": {} }
    add_structure(article_structure, duplicates, info["question"], "h1", info["answer"], info["youtube"], info["sourcetitle"], info["sourcelink"])
    for h2 in info["related"]:
        info_h2 = get_info(h2, article_structure, "h2")
        if not info_h2:
            continue
        add_structure(article_structure, duplicates, info_h2["question"], "h2", info_h2["answer"], info_h2["youtube"], info_h2["sourcetitle"], info_h2["sourcelink"])
        for h3 in info_h2["related"]:
            info_h3 = get_info(h3, article_structure, "h3")
            if not info_h3:
                continue
            add_structure(article_structure, duplicates, info_h3["question"], "h3", info_h3["answer"], info_h3["youtube"], info_h3["sourcetitle"], info_h3["sourcelink"])
    article_structure["structure"] = list(article_structure["structure"].values())
    articlestruct.replace_one( {'_id' : to_url(info["question"])}, article_structure, upsert = True )


articles_scraped = [
    "how do arenas switch from hockey to basketball",
    "how to clean a dirty basketball",
    "who won by 97 points in college basketball",
    "who was the first national college basketball champion",
    "who is michael jordan's favorite basketball player",
    "who played wvu men's basketball on tonight",
    "why are basketball numbers retired",
    "why a backspin on a basketball",
    "why is lego basketball so expensive",
    "what time is the men's basketball game on tonight",
    "what time is the wichita state basketball game",
    "what time is the basketball championship tonight",
]

to_scrape = [
    "what is a jelly layup in basketball",
    "who did michael jordan play college basketball for",
    "how much does hong kong mens basketball player make",
    "how do you become a good basketball player for beginners",
    "what does a professional basketball player do",
    "what nba basketball player wrote a best-selling book",
    "should i play basketball because im tall",
    "should i play basketball with a jammed finger",
    "is it good to chew gum while playing basketball",
    "how much does a portable basketball hoop cost"
]



from multiprocessing import Pool
if __name__ == "__main__":
    pool = Pool(processes=3)
    print(pool.map(make_article, to_scrape))
    pool.close()
    pool.join()