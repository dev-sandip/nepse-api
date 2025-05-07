import time

class TokenBucket:
    def __init__(self, capacity, refill_rate):
        
        self.capacity = capacity  
        self.refill_rate = refill_rate  
        self.tokens = capacity  
        self.last_refill = time.time()  

    def add_tokens(self):
        
        now = time.time()
        if self.tokens < self.capacity:
            
            tokens_to_add = (now - self.last_refill) * self.refill_rate
            
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now  

    def take_token(self):
        
        self.add_tokens()  
        if self.tokens >= 1:
            self.tokens -= 1  
            return True  
        return False  