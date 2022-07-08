import os
from dotenv import load_dotenv

class Proxy:
    def __init__(self):
        load_dotenv()
        self.proxy = os.getenv("PROXY")
    
    def getProxy(self):
        return self.proxy