from paa import Google
from useragent import UserAgent
"""
Methods:
get_answer ->
generate_answer ->
get_simple_answer ->
get_related_questions -> 
generate_related_questions ->
"""

valid = []
for i in UserAgent.getUserAgents():
    printed = False
    tries = 0
    while not printed:
        try:
            google = Google(header=i)
            result = google.get_related_questions("who did kansas basketball lose to")
            if not result:
                valid.append(i)
                print(i)
                printed = True
            elif tries == 2:
                printed = True
            else:
                tries += 1
        except Exception as e:
            e

print(valid)

"""
print(search.generate_answer("who did kansas basketball lose to"))

print(search.get_simple_answer("who did kansas basketball lose to"))
print(search.get_related_questions("who did kansas basketball lose to"))

for question in search.generate_related_questions("who did kansas basketball lose to"):
    print(question)
    break
"""