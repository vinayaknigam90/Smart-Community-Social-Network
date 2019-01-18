from index import db
from models import User, Community, UserModerator, UserCommunity, UserRequestedCommunity

# db.drop_all()
db.create_all()

print("DB created.")
