# Dictionary to cache chatbot data
chatbot_cache = {}

# Utility function to cache chatbot data
def cache_chatbot_data(chatbot_id, data):
    chatbot_cache[chatbot_id] = data

# Utility function to check if chatbot data is cached
def is_chatbot_cached(chatbot_id):
    return chatbot_id in chatbot_cache

# Utility function to get chatbot data from cache
def get_chatbot_data(chatbot_id):
    return chatbot_cache.get(chatbot_id)

# Utility function to delete chatbot data from cache
def delete_chatbot_data(chatbot_id):
    if chatbot_id in chatbot_cache:
        del chatbot_cache[chatbot_id]