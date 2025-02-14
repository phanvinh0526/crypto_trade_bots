import os
import requests
from dotenv import load_dotenv
from datetime import datetime
import pytz

# Load variables from .env file
load_dotenv()

# Env variables
LUNA_CRUSH_API_TOKEN = os.environ['LUNA_CRUSH_API_TOKEN']
LUNA_BASE_URL = "https://lunarcrush.com/api4"

class LunarCrushTopicPosts:
    # #############################
    # Input Param: search term
    # Desc: Get the top posts for a social topic. If start time is provided the result will be the top posts by interactions for the time range. If start is not provided it will be the most recent top posts by interactions from the last 24 hours.
    # #############################
    BASE_URL = LUNA_BASE_URL + "/public/topic/{}/posts/v1"

    def __init__(self):
        self.api_key = LUNA_CRUSH_API_TOKEN

    def fetch_topic_posts(self, topic):
        url = self.BASE_URL.format(topic)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None

    def analyze_topic(self, topic):
        """ Get total interactions, total followers, and sentiment analysis """
        data = self.fetch_topic_posts(topic)
        if not data or "data" not in data:
            return None
        
        posts = data["data"][:50]  # First 50 posts

        total_interactions = sum(post.get("interactions_24h", 0) for post in posts)
        total_followers = sum(post.get("creator_followers", 0) for post in posts)
        
        sentiment_scores = [post.get("post_sentiment", 3) for post in posts]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 3
        sentiment_label = "Positive" if avg_sentiment > 3 else "Neutral/Negative"

        return {
            "topic": topic,
            "total_interactions_24h": total_interactions,
            "total_creator_followers": total_followers,
            "average_post_sentiment": round(avg_sentiment, 2),
            "sentiment_label": sentiment_label
        }


class LunarCrushSearch:
    BASE_URL = LUNA_BASE_URL

    def __init__(self):
        self.api_key = LUNA_CRUSH_API_TOKEN
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def search_post(self, keyword):
        """ Search for the first and earliest post matching the keyword """
        url = f"{self.BASE_URL}/public/searches/search"
        params = {"term": keyword}  # Fetch up to 50 posts for sorting
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200 and "data" in response.json():
            posts = response.json()["data"]
            if not posts:
                return None
            
            first_post = posts[0]  # First post from the response
            
            # Find the earliest post by sorting based on 'post_created'
            earliest_post = min(posts, key=lambda p: p["post_created"])
            
            return {
                "first_post": {"id": first_post["id"], "text": first_post["text"], "post_link": first_post["post_link"], "post_created": first_post["post_created"]},
                "earliest_post": {"id": earliest_post["id"], "text": earliest_post["text"], "post_link": earliest_post["post_link"], "post_created": earliest_post["post_created"]}
            }
        else:
            print(f"Error in search_post: {response.status_code} - {response.text}")
            return None

    def get_post_details(self, post_type, post_id, post_created):
        """ Fetch details of a post (views, retweets, replies, creator) """
        url = f"{self.BASE_URL}/public/posts/{post_type}/{post_id}/v1"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            post = response.json()
            return {
                "views": post["metrics"].get("views", 0),
                "retweets": post["metrics"].get("retweets", 0),
                "replies": post["metrics"].get("replies", 0),
                "creator_name": post.get("creator_name", "Unknown"),
                "post_created": str(self.convert_unix_to_melbourne(post_created))
            }
        else:
            print(f"Error in get_post_details: {response.status_code} - {response.text}")
            return None

    def get_creator_details(self, creator_name, network="twitter"):

        """ Fetch creator details (followers, top 3 influence topics) """
        url = f"{self.BASE_URL}/public/creator/{network}/{creator_name}/v1"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200 and "data" in response.json():
            creator = response.json()["data"]
            top_3_topics = creator["topic_influence"][:3]
            topic_list = ', '.join([topic["topic"] for topic in top_3_topics])
            
            return {
                "creator_followers": creator.get("creator_followers", 0),
                "top_3_topics": topic_list
            }
        else:
            print(f"Error in get_creator_details: {response.status_code} - {response.text}")
            return None

    def convert_unix_to_melbourne(self, unix_timestamp):
        # Define GMT and Melbourne timezones
        gmt_timezone = pytz.utc
        melbourne_timezone = pytz.timezone("Australia/Melbourne")
        # Convert Unix timestamp (GMT) to datetime object
        gmt_datetime = datetime.utcfromtimestamp(unix_timestamp).replace(tzinfo=gmt_timezone)
        # Convert to Melbourne timezone
        melbourne_datetime = gmt_datetime.astimezone(melbourne_timezone)
        return melbourne_datetime

    def search_post_data(self, keyword, network="tweet"):
        """ Main function to fetch all data for a keyword search """
        posts = self.search_post(keyword)
        if not posts:
            return None
        
        first_post_details = self.get_post_details("tweet", posts["first_post"]["id"], posts["first_post"]["post_created"])
        earliest_post_details = self.get_post_details("tweet", posts["earliest_post"]["id"], posts["earliest_post"]["post_created"])
        
        if not first_post_details or not earliest_post_details:
            return None
        
        creator_detail_first_post = self.get_creator_details(first_post_details["creator_name"], "twitter")
        creator_details_earliest_post = self.get_creator_details(earliest_post_details["creator_name"], "twitter")
        if not creator_detail_first_post or not creator_details_earliest_post:
            return None
        
        return {
            "ca": keyword,
            "first_post": {
                "post_created": first_post_details["post_created"],
                "post_link": posts["first_post"]["post_link"],
                "views": first_post_details["views"],
                "retweets": first_post_details["retweets"],
                "replies": first_post_details["replies"],
                "creator_name": first_post_details["creator_name"],
                "creator_followers": creator_detail_first_post["creator_followers"],
                "top_3_topics": creator_detail_first_post["top_3_topics"]
            },
            "earliest_post": {
                "post_created": earliest_post_details["post_created"],
                "post_link": posts["earliest_post"]["post_link"],
                "views": earliest_post_details["views"],
                "retweets": earliest_post_details["retweets"],
                "replies": earliest_post_details["replies"],
                "creator_name": earliest_post_details["creator_name"],
                "creator_followers": creator_details_earliest_post["creator_followers"],
                "top_3_topics": creator_details_earliest_post["top_3_topics"]
            }
        }
    

def format_json_for_telegram(topic_data, post_data):
    # Extract and escape topic data
    topic = topic_data.get("topic", "N/A")
    total_interactions = topic_data.get("total_interactions_24h", 0)
    total_followers = topic_data.get("total_creator_followers", 0)
    avg_sentiment = topic_data.get("average_post_sentiment", "N/A")
    sentiment_label = topic_data.get("sentiment_label", "N/A")

    # Extract and escape first post data
    first_post = post_data.get("first_post", {})
    first_post_created = first_post.get("post_created", "N/A")
    first_post_link = first_post.get("post_link", "N/A")
    first_post_views = first_post.get("views", 0)
    first_post_retweets = first_post.get("retweets", 0)
    first_post_replies = first_post.get("replies", 0)
    first_creator_name = first_post.get("creator_name", "N/A")
    first_creator_followers = first_post.get("creator_followers", 0)
    first_top_3_topics = first_post.get("top_3_topics", "N/A")

    # Extract and escape earliest post data
    earliest_post = post_data.get("earliest_post", {})
    earliest_post_created = earliest_post.get("post_created", "N/A")
    earliest_post_link = earliest_post.get("post_link", "N/A")
    earliest_post_views = earliest_post.get("views", 0)
    earliest_post_retweets = earliest_post.get("retweets", 0)
    earliest_post_replies = earliest_post.get("replies", 0)
    earliest_creator_name = earliest_post.get("creator_name", "N/A")
    earliest_creator_followers = earliest_post.get("creator_followers", 0)
    earliest_top_3_topics = earliest_post.get("top_3_topics", "N/A")

    # Format the message for Telegram display
    formatted_message = (
        f"📌 <b>Topic Data:</b>\n"
        f"💬 <b><u>Topic:</u></b> {topic}\n"
        f"🔄 <b><u>Total Interactions (24h):</u></b> {total_interactions}\n"
        f"👥 <b><u>Total Creator Followers:</u></b> {total_followers}\n"
        f"📊 <b><u>Average Sentiment:</u></b> {avg_sentiment} ({sentiment_label})\n\n"
        
        f"📌 <b>First Post:</b>\n"
        f"📅 <b><u>Created:</u></b> {first_post_created}\n"
        f"🔗 <b><u>[Post Link]({first_post_link})</u></b>\n"
        f"👁️ <b><u>Views:</u></b> {first_post_views}\n"
        f"🔄 <b><u>Retweets:</u></b> {first_post_retweets}\n"
        f"💬 <b><u>Replies:</u></b> {first_post_replies}\n"
        f"👤 <b><u>Creator:</u></b> {first_creator_name} ({first_creator_followers} followers)\n"
        f"📚 <b><u>Top 3 Topics:</u></b> {first_top_3_topics}\n\n"
        
        f"📌 <b>Earliest Post:</b>\n"
        f"📅 <b><u>Created:</u></b> {earliest_post_created}\n"
        f"🔗 <b><u>[Post Link]({earliest_post_link})</u></b>\n"
        f"👁️ <b><u>Views:</u></b> {earliest_post_views}\n"
        f"🔄 <b><u>Retweets:</u></b> {earliest_post_retweets}\n"
        f"💬 <b><u>Replies:</u></b> {earliest_post_replies}\n"
        f"👤 <b><u>Creator:</u></b> {earliest_creator_name} ({earliest_creator_followers} followers)\n"
        f"📚 <b><u>Top 3 Topics:</u></b> {earliest_top_3_topics}\n"
    )
    print(formatted_message)
    return formatted_message




### Example Usage ###
# if __name__ == "__main__":
#     keyword = "7oBYdEhV4GkXC19ZfgAvXpJWp2Rn9pm1Bx2cVNxFpump"

#     lunarcrush = LunarCrushTopicPosts()
#     topic_data = lunarcrush.analyze_topic(keyword)  # Replace with your topic
#     print(topic_data)

#     lunarcrush = LunarCrushSearch()
#     keyword_data = lunarcrush.search_post_data(keyword)
#     print(keyword_data)

### Example Results ###
# {'topic': '7oBYdEhV4GkXC19ZfgAvXpJWp2Rn9pm1Bx2cVNxFpump', 'total_interactions_24h': 671489, 'total_creator_followers': 10479024, 'average_post_sentiment': 3.15, 'sentiment_label': 'Positive'}
# {
#    "keyword":"7oBYdEhV4GkXC19ZfgAvXpJWp2Rn9pm1Bx2cVNxFpump",
#    "first_post":{
#       "post_link":"https://x.com/anyuser/status/1888722674265764017",
#       "views":4762998,
#       "retweets":1355,
#       "replies":1636,
#       "creator_name":"FA_Touadera"
#    },
#    "earliest_post":{
#       "post_link":"https://x.com/anyuser/status/1888716729095688374",
#       "views":2137,
#       "retweets":1,
#       "replies":0
#    },
#    "creator_followers":52239,
#    "top_3_topics":"bitcoin, experiment designed, central african"
# }
