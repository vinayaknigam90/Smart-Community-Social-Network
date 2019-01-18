from pymongo import MongoClient
import datetime
import pprint

client = MongoClient("mongodb://admin:admin@ds251845.mlab.com:51845/socialcommunity")
db = client['socialcommunity']

# posts = db.posts
# post_data = {
#     'title': 'Python and MongoDB',
#     'content': 'PyMongo is fun, you guys',
#     'author': 'Scott',
#     'attachment': "",
#     'posted_date': datetime.datetime.now(),
#     'comments': [{
#         'author': { 'name': 'Anonymous'},
#         'posted': datetime.datetime.now(),
#         'text': 'This is still ugly'
#     },
#     {
#         'author': { 'name': 'Rahil'},
#         'posted': datetime.datetime.now(),
#         'text': 'This is still cute'
#     }]
# }
#
# result = posts.insert_one(post_data)
# print('One post: {0}'.format(result.inserted_id))

# for doc in db.posts.find({}):
#     pprint.pprint (str(doc['_id']))

# db.posts.update_one(
# {"_id": 1},
# {"$push": {
#     'comments': {
#         'author': { 'name': 'Manika'},
#                 'posted': datetime.datetime.now(),
#                 'text': 'I like this'
#             }
#         }
#     }
# )
# complaints = db.complaints
#
# complaint_data = {
#     'communityID': 1,
#     'category': 'Maintenance',
#     'title': 'Plumbing',
#     'content': 'Tap broken in washroom',
#     'complainee': 'rahil15',
#     'posted_date': datetime.datetime.now(),
#     'status':'open'
# }
#
# result = complaints.insert_one(complaint_data)
# print('One compalint: {0}'.format(result.inserted_id))

messages = db.messages

message_data = {
    'fromCommunityID': 1,
    'fromUserId':'rahil15',
    'subject': 'Inquiry',
    'content': 'What is there?',
    'toUserId': 'manika',
    'toCommunityId': 2,
    'message_date': datetime.datetime.now()
}

result = messages.insert_one(message_data)
print('One message: {0}'.format(result.inserted_id))
