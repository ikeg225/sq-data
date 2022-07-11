import re
from paa import Google
from mongoconnect import get_database

db = get_database()
articlestruct = db["articlestruct"]

def to_url(string):
    remove_punc = re.sub('[^A-Za-z0-9\s-]+', '', string.strip())
    return re.sub('[\s]+', '-', remove_punc).lower()

def get_info(question):
    printed = False
    tries = 0
    while not printed:
        try:
            google = Google()
            result = google.get_answer(question)
            if not result['related_questions'] or result['has_answer']:
                return {
                    "question": question,
                    "answer": re.sub(r"[a-zA-Z]{3} \d{1,2}, \d{4}[\s]*$", "", result['response']),
                    "related": result['related_questions'],
                    "youtube": result['youtube'],
                    "sourcetitle": result['title'],
                    "sourcelink": result['link']
                }
            elif tries == 2:
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
    tag_priority = { "h1": 3, "h2": 2, "h3": 1 }
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
        info_h2 = get_info(h2)
        if not info_h2:
            continue
        add_structure(article_structure, duplicates, info_h2["question"], "h2", info_h2["answer"], info_h2["youtube"], info_h2["sourcetitle"], info_h2["sourcelink"])
        for h3 in info_h2["related"]:
            info_h3 = get_info(h3)
            if not info_h3:
                continue
            add_structure(article_structure, duplicates, info_h3["question"], "h3", info_h3["answer"], info_h3["youtube"], info_h3["sourcetitle"], info_h3["sourcelink"])
    article_structure["structure"] = list(article_structure["structure"].values())
    articlestruct.replace_one( {'_id' : to_url(info["question"])}, article_structure, upsert = True )


#for header in ["how do arenas switch from hockey to basketball"]:

#google = Google()
#google.get_answer_to_related_questions("how do arenas switch from hockey to basketball")

print(make_article("how do arenas switch from hockey to basketball"))
print(make_article("how to clean a dirty basketball"))

#collection_name.insert_many([item_1,item_2])