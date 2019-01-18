from flask import Flask, render_template, request, make_response, url_for, flash, redirect, session, abort, jsonify, g, current_app
from flask_moment import Moment
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from Forms import LoginForm, RegistrationForm, commuityRegistraion, ArticleForm , EditForm, EditArticleForm, CommentForm, ChatForm, ExternalMessageForm, commuityUpdateForm, commuityUpdateFormForModerator
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
import json
import psycopg2
import os
import sys
import datetime
from index import app, db, mongo,logger
from models import Community, User, UserCommunity, UserModerator, UserRequestedCommunity
import  myexception
from flask_httpauth import HTTPBasicAuth
from awsServices import sendEmail, sendMessage, sendDeclineMessage
from flask_mail import Mail,Message
from threading import Thread
from flask_pagedown import PageDown
import boto3
import redis
from bson.objectid import ObjectId
from markdown import markdown
from decorator import admin_required
import bleach

auth = HTTPBasicAuth()
import pprint

pagedown = PageDown()
app = Flask(__name__)
moment = Moment(app)
Bootstrap(app)
app.config['SECRET_KEY'] = os.urandom(32)
app.config['WTF_CSRF_ENABLED'] = False
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = "You should be logged in to view this page"
login_manager.login_view = 'login'

# Flask Mail settings
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'socialnetwork281@gmail.com'
app.config['MAIL_PASSWORD'] = 'Cmpe@281'
app.config['MAIL_DEBUG'] = True

app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[SocialNetwork]'
app.config['FLASKY_MAIL_SENDER'] = 'Admin <socialnetwork281@gmail.com>'
app.config['SOCIALNETWORK_ADMIN'] = 'socialnetwork281@gmail.com'
pagedown.init_app(app)
mail = Mail(app)
# Create SQS client
sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/507614993775/mails-queue'

# redis_cache = redis.StrictRedis(host='localhost',port=6379,db=0)
redis_cache = redis.StrictRedis(host='redis-community.nm0e1t.0001.use1.cache.amazonaws.com',port=6379,db=0)


def initializeRedis():
    redis_cache.flushall()
    communities = Community.query.filter_by(status='Approved').all()
    for community in communities:
        redis_cache.sadd('communities',community.ID)
        moderator = UserModerator.query.filter_by(communityID = community.ID).first().moderator
        redis_cache.set(community.ID,moderator)
        # print redis_cache.get(community.ID)
    # print redis_cache.smembers('communities')
    users = User.query.all()
    for user in users:
        redis_cache.sadd('listusers',user.username)
        if user.username != 'admin':
            usercommunities = UserCommunity.query.filter_by(userID = user.username).all()
            for _comm in usercommunities:
                redis_cache.sadd(user.username,_comm.communityID)
            print redis_cache.smembers(user.username)

initializeRedis()

def author_images():
    mongo.author_images.remove({})
    userObjs = User.query.all()
    for user in userObjs:
        if user.imageUrl:
            imagePath = user.imageUrl
        else:
            url = 'http://www.gravatar.com/avatar'
            hash = user.gravatar_hash()
            imagePath = '{url}/{hash}?s=100&d=identicon&r=g'.format(
                url=url, hash=hash)
        # print user.username + imagePath
        mongo.author_images.insert_one({
            'username': user.username,
            'imagePath': imagePath
        })
        key = 'img_'+user.username
        redis_cache.set(key,imagePath)
        # print redis_cache.get(key)
author_images()

listOfAuthAPIs = ['login','unconfirmed','logout','sign_up','confirm','resend_confirmation']

allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']

def convertIntoHTML(value):
    return bleach.linkify(bleach.clean(markdown(value, output_format='html'),tags=allowed_tags, strip=True))

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + subject,
                  sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    # msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
# Flask Mail settings

#Confirmation Email
@app.route('/confirm/<token>')
@login_required
def confirm(token):
    print token
    if current_user.status == 'approved':
        flash('Your account has been verified..')
        return redirect(url_for('home'))
    if current_user.confirm(token):
        db.session.commit()
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('home'))

@app.before_request
def before_request():
    if current_user.is_authenticated \
            and current_user.status != 'approved'\
            and request.endpoint not in listOfAuthAPIs \
            and request.endpoint != 'static':
        return redirect(url_for('unconfirmed'))

@app.route('/unconfirmed')
def unconfirmed():
    if current_user.status == 'approved' or current_user.is_anonymous:
        return redirect(url_for('home'))
    return render_template('_unconfirmed.html')

@app.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               '_confirmemail', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('home'))

@login_manager.user_loader
def load_user(username):
    # print username
    return User.query.get(username)

#Test Route
@app.route('/test', methods = ['GET','POST'])
def test():
    return render_template('admin.html')

@app.route('/',methods = ['GET'])
def index():
    return render_template('index.html')

@app.route('/admin', methods = ['GET'])
@login_required
@admin_required
def admin():
    adminData = getStats()
    listOfRequestedCommunitites = getRequestedCommunity()
    return render_template('admin.html', adminData=adminData , listOfRequestedCommunitites=listOfRequestedCommunitites)

@app.route('/admin_users', methods = ['GET','POST'])
@login_required
@admin_required
def admin_users():
    adminData = getStats()
    users = User.query.order_by((User.joining_date)).all()
    listUsers =[]
    for user in users:
        if user.username != 'admin':
            listUsers.append(user)
    return render_template('admin_users.html',users=listUsers , adminData=adminData )

@app.route('/admin_community', methods = ['GET','POST'])
@login_required
@admin_required
def admin_community():
   adminData = getStats()
   # categories = getUserCommunities()
   communityDetails = adminCommunityData()
   return render_template('admin_community.html',communityDetails=communityDetails, adminData=adminData )

@app.route('/admin_post', methods = ['GET','POST'])
@login_required
@admin_required
def admin_post():
    adminData = getStats()
    listOfPost =[]
    listOfPost.extend(mongo.posts.find({}))
    listOfPost.sort(key=lambda r: r['posted_date'], reverse=True)
    usersImage = getAllProfilePictures()
    return render_template('admin_post.html',adminData=adminData,listOfPost=listOfPost, usersPic=usersImage)

@app.route('/edit_community/<community_id>', methods = ['GET','POST'])
@login_required
def edit_community_moderator(community_id):
    communityID = int(community_id)
    print "Printing Comuity"
    communityDetails = Community.query.filter_by(ID=communityID).first()
    # implementing redis caching for faster response
    if redis_cache.get(communityID):
        moderator = redis_cache.get(communityID)
    moderator = UserModerator.query.filter_by(communityID=communityID).first().moderator
    userObj = UserCommunity.query.filter_by(communityID=communityID).all()
    form = commuityUpdateFormForModerator()
    if form.validate_on_submit():
        communityDetails.description = form.desc.data
        communityDetails.address = form.address.data
        communityDetails.city = form.city.data
        communityDetails.zip_code = form.zip_code.data
        db.session.commit()
        return redirect(url_for('community',community_id=community_id))
    else:
        communityDetails = Community.query.filter_by(ID=communityID).first()
        form.desc.data = communityDetails.description
        form.address.data = communityDetails.address
        form.city.data = communityDetails.city
        form.zip_code.data = communityDetails.zip_code
        return render_template('_edit_community_moderator.html',form=form ,column = communityID, name = communityDetails.name)

#edit community
@app.route('/admin/edit_community/<community_id>', methods = ['GET','POST'])
@login_required
@admin_required
def edit_community(community_id):
    communityID = int(community_id)
    print "Printing Comuity"
    communityDetails = Community.query.filter_by(ID=communityID).first()
    # implementing redis caching for faster response
    if redis_cache.get(communityID):
        moderator = redis_cache.get(communityID)
    moderator = UserModerator.query.filter_by(communityID=communityID).first().moderator
    userObj = UserCommunity.query.filter_by(communityID=communityID).all()
    members = []
    for user in userObj:
        members.append(user.userID)
    members = [(k,v) for k,v in enumerate(members)]
    print members
    current_moderator = [member for member in members if member[1] == moderator]
    print moderator
    form = commuityUpdateForm(members,moderator=current_moderator[0][0])
    if form.validate_on_submit():
        communityDetails.description = form.desc.data
        communityDetails.address = form.address.data
        communityDetails.city = form.city.data
        communityDetails.zip_code = form.zip_code.data
        db.session.commit()
        new_moderator = dict(members).get(form.moderator.data)
        print new_moderator
        if moderator != new_moderator:
            UserModerator.query.filter_by(communityID=communityID).first().moderator = new_moderator
            if not checkAsModeratorForOtherCommunity(new_moderator):
                User.query.filter_by(username=new_moderator).first().role = 'moderator'
            if not checkAsModeratorForOtherCommunity(moderator):
                User.query.filter_by(username=moderator).first().role = 'user'
            db.session.commit()
            redis_cache.set(communityID,new_moderator)
        return redirect(url_for('admin_community'))
    else:
        communityDetails = Community.query.filter_by(ID=communityID).first()
        form.desc.data = communityDetails.description
        form.address.data = communityDetails.address
        form.city.data = communityDetails.city
        form.zip_code.data = communityDetails.zip_code
        # form.creation_date.data = communityDetails.creation_date
        # form.created_by.data = communityDetails.created_by
        return render_template('_edit_community.html',form=form ,column = communityID, name = communityDetails.name)

def checkAsModeratorForOtherCommunity(moderatorUserName):
    moderatorObj = UserModerator.query.filter_by(moderator = moderatorUserName).first()
    if moderatorObj:
        return True
    else:
        return False

#create new community
@app.route('/new_community', methods = ['GET','POST'])
@login_required
def new_community():
    form = commuityRegistraion()
    if form.validate_on_submit():
        name = form.name.data.lower()
        desc = form.desc.data
        address = form.address.data
        city = form.city.data
        zip_code = form.zip_code.data
        creation_date = datetime.datetime.now()
        created_by = current_user.username
        com = Community(name=name,
                        description=desc,
                        address=address,
                        city=city,
                        zip_code=zip_code,
                        creation_date=creation_date,
                        created_by = created_by)
        if Community.query.filter_by(name=name).first() is not None:
            flash("Community name already exists")
            form = commuityRegistraion()
            return render_template('_newCommunity.html',form=form)
        db.session.add(com)
        db.session.commit()
        message = 'Hi Admin, This is to inform that '+current_user.username+' has created a new commmunity named as '+name+'. User email is '+ current_user.email +' . Please Approve it.'
        subject = 'New Community '+ name + ' acceptance mail.'
        sendEmail(message, subject)
        sendMessage(current_user.contact_number,current_user.username, name)
        flash('Community ' + name + ' has been created. Waiting for admin approval.' )
        return redirect(url_for('home'))
    return render_template('_newCommunity.html',form=form)

#create new user
@app.route('/sign_up', methods = ['GET','POST'])
def new_user():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.lower()
        firstName = form.firstname.data
        lastName = form.lastname.data
        email = form.email.data
        hashed_password = generate_password_hash(form.password.data,method='sha256')
        password = hashed_password
        contact_number = form.contact.data
        joining_date = datetime.datetime.now()
        new_user = User(username = username,
                        firstName = firstName,
                        lastName=lastName,
                        email = email,
                        password=password,
                        contact_number = contact_number,
                        joining_date=joining_date,
                        role = 'user')
        if User.query.filter_by(username=username).first() is not None:
            flash("Username already exists")
            form = RegistrationForm()
            return render_template('_signup.html', form=form)
        elif User.query.filter_by(email=email).first() is not None:
            flash("Email already registered")
            form = RegistrationForm()
            return render_template('_signup.html', form=form)
        db.session.add(new_user)
        db.session.commit()
        url = 'http://www.gravatar.com/avatar'
        hash = new_user.gravatar_hash()
        imagePath = '{url}/{hash}?s=100&d=identicon&r=g'.format(
            url=url, hash=hash)
        # print user.username + imagePath
        mongo.author_images.insert_one({
            'username': new_user.username,
            'imagePath': imagePath
        })
        key = 'img_'+new_user.username
        redis_cache.set(key,imagePath)
        redis_cache.sadd('listusers',new_user.username)
        if app.config['SOCIALNETWORK_ADMIN']:
            send_email(app.config['SOCIALNETWORK_ADMIN'], ' New User',
                       '_newuser', user=new_user)
            token = new_user.generate_confirmation_token()
            send_email(new_user.email, 'Confirm Your Account',
                       '_confirmemail', user=new_user, token=token)
            flash('A confirmation email has been sent to you by email.')
        flash('Registration has been done successfully. Please login.')
        return redirect(url_for('login'))
    return render_template('_signup.html', form=form)

#add new post
@app.route('/add_post', methods = ['POST'])
def add_post(category,title,content,content_html):
    posts = mongo.posts
    # impagePath = None
    # if not current_user.imageUrl:
    #     impagePath = current_user.gravatar()
    # else:
    #     impagePath = current_user.imageUrl
    post_data = {
        'category':category.lower(),
        'title': title,
        'content': content,
        'contentHTML': content_html,
        'author': current_user.username,
        'posted_date': datetime.datetime.utcnow(),
        'comments': []
    }
    # post_data = {
    #     'category':category.lower(),
    #     'title': title,
    #     'content': content,
    #     'contentHTML': content_html,
    #     'author': current_user.username,
    #     # 'authorImage': impagePath,
    #     'posted_date': datetime.datetime.utcnow(),
    #     'comments': []
    # }
    result = posts.insert_one(post_data)
    print 'One post: {0}'.format(result.inserted_id)

@app.route('/messages',methods=['GET'])
def messages():
    friends = getUserFriends()
    for friend in friends:
        print friend
    return render_template('messages.html', members = friends, selectedUser = None)

@app.route('/messageToOtherModerator',methods=['GET'])
def messageModerator():
    # communities = Community.query.all()
    # communityId = [community.ID for community in communities]
    communityId = redis_cache.smembers('communities')
    response = []
    for _id in communityId:
        _moderator = UserModerator.query.filter_by(communityID=_id).first()
        print _moderator
        user = User.query.filter_by(username=_moderator.moderator).first()
        detailObj = {
            'CommunityID': _id,
            'CommunityName': Community.query.filter_by(ID=_id).first().name,
            'Moderator': user
        }
        response.append(detailObj)
    return render_template('_externalCommunities.html', resp = response, selectedUser = None)

@app.route('/messageToOtherCommunity/<communityID>', methods=['GET','POST'])
@login_required
def externalCommunityMessage(communityID):
    if current_user.role == 'user' :
        flash('You are not an moderator..Only moderator can view this page..')
        return redirect(url_for('home'))
    moderator = UserModerator.query.filter_by(communityID=communityID).first().moderator
    communityName = Community.query.filter_by(ID=communityID).first().name
    form = ExternalMessageForm()
    if form.validate_on_submit():
        print form.subject.data
        print form.message.data
        messages = mongo.mod_messages
        message_data = {
            'sender': current_user.username,
            'subject':form.subject.data,
            'msg': form.message.data,
            'recipient': moderator,
            'community': communityName,
            'timestamp': datetime.datetime.utcnow()
        }
        # result = messages.insert_one(message_data)
        send_to_queue(message_data)
        form.subject.data = ''
        form.message.data = ''
        flash('your message has been sent')
    # communities = Community.query.all()
    # communityId = [community.ID for community in communities]
    communityId = redis_cache.smembers('communities')
    response = []
    for _id in  communityId:
        _moderator = UserModerator.query.filter_by(communityID = _id).first()
        user = User.query.filter_by(username = _moderator.moderator).first()
        detailObj = {
            'CommunityID': _id,
            'CommunityName': Community.query.filter_by(ID=_id).first().name,
            'Moderator': user
        }
        response.append(detailObj)
    return render_template('_externalCommunities.html', form = form, resp = response, selectedUser = moderator, selectedCommunity = communityID)

@app.route('/messages/<username>',methods=['GET', 'POST'])
def retrieveMessagesOfUser(username):
    print username
    form = ChatForm()
    if form.validate_on_submit():
        print form.msg.data
        msg = form.msg.data
        add_message(username,msg)
        form.msg.data = ''
    friends = getUserFriends()
    convos = get_messages(current_user.username,username)
    for friend in friends:
        print friend
    return render_template('messages.html', members=friends, form = form, selectedUser = username, conversations = convos )

@app.route('/mails', methods=['GET'])
def mails():
    mails = []
    messages = mongo.mod_messages.find({'recipient': current_user.username})
    for msg in messages:
        mails.append(msg)
    mails.sort(key=lambda r: r['timestamp'], reverse=True)
    usersPic = getAllProfilePictures()
    return render_template('mails.html',mails = mails,usersPic= usersPic)

@app.route('/reply/<mailid>',methods=['GET','POST'])
def getMail(mailid):
    mail = mongo.mod_messages.find_one({'_id': ObjectId(str(mailid))})
    form = ExternalMessageForm()
    if form.validate_on_submit():
        subject = form.subject.data
        msg = form.message.data
        message_data = {
            'sender': current_user.username,
            'subject':form.subject.data,
            'msg': form.message.data,
            'recipient': mail['sender'],
            'community': mail['community'],
            'timestamp': datetime.datetime.utcnow()
        }
        result = mongo.mod_messages.insert_one(message_data)
        mongo.mod_messages.update_one(
        {"_id": ObjectId(str(mailid))},
        {"$push": {
            'repliesRef': {
                        'id': result.inserted_id
                    }
                }
            }
        )
        flash('Your reply has been sent')
        return redirect(url_for('mails'))
    usersPic = getAllProfilePictures()
    return render_template('reply.html',form = form, mail = mail, usersPic=usersPic)

@app.route('/sendmessages', methods=['POST'])
def saveMessage():
    print "here"
    msg = request.form['msg']
    print msg
    return render_template('messages.html', message = msg, timestamp = datetime.datetime.utcnow())

@app.route('/joincommunity',methods=['GET'])
def listOfCommunitites():
    joinedCommunities = getCommunityDetailsJoined()
    unjoinedCommunities = getCommunityDetailsUnjoined()
    requestedCommunities = getCommunityDetailsRequested()
    return render_template('_joincommunity.html',joined = joinedCommunities, unjoined = unjoinedCommunities, requested = requestedCommunities)

#add comment to a post
@app.route('/add_post_comment', methods = ['POST'])
def add_post_comment():
    mongo.posts.update_one(
    {"_id": request.json['_id']},
    {"$push": {
        'comments': {
                    'posted': datetime.datetime.now(),
                    'text': request.json['text']
                }
            }
        }
    )
    return ("Comment Added to post " + str(request.json['_id']))

def msg_to_json(recipient, msg):
    message_data = {
        'fromUserId': recipient,
        'msg': msg,
        'toUserId': current_user.username,
        'message_date': datetime.datetime.utcnow()
    }
    return message_data
#add message
# @app.route('/add_message', methods = ['POST'])
def add_message(recipient, msg):
    messages = mongo.messages
    message_data = {
        'fromUserId':current_user.username,
        'msg': msg,
        'toUserId': recipient,
        'message_date': datetime.datetime.utcnow()
    }
    result = messages.insert_one(message_data)
    print 'One message: {0}'.format(result.inserted_id)

def get_messages(person1, person2):
    listOfConversations = []
    messages = mongo.messages.find({'fromUserId':person1, 'toUserId':person2})
    for message in messages:
        listOfConversations.append(message)
    replies = mongo.messages.find({'fromUserId': person2, 'toUserId': person1})
    for reply in replies:
        listOfConversations.append(reply)
    listOfConversations.sort(key=lambda r: r['message_date'], reverse=True)
    return listOfConversations

#get all the distict communities
@app.route('/get_all_community', methods = ['GET'])
def get_all_community():
    communities = Community.query.all()
    communities_name = [community.name for community in communities]
    return json.dumps(communities_name)

@app.route('/home',methods = ['GET','POST'])
@login_required
def home():
    _categories = getUserCommunities()
    categories = [(int(_cat[0]),_cat[1])for _cat in _categories]
    categories.append((0,'general'))
    print categories
    form = ArticleForm(categories, category=0)
    # moderatorCommunityList = userModeratorCommunityList()
    if form.validate_on_submit():
        print 'inside add post'
        title = form.title.data
        # body = form.body.data.split('<p>')[1].split('</p>')[0]
        body = form.body.data
        content_html = convertIntoHTML(body)
        print body
        print form.category.data
        category = dict(categories).get(form.category.data)
        add_post(category,title,body,content_html)
        form.title.data = ""
        form.body.data = ""
        form.category.data = 0
    display_posts = getPostsByUser()
    communities = getUserCommunities()
    moderatorCommunityList = userModeratorCommunityList()
    usersImage = getAllProfilePictures()
    return render_template('_userdashboard.html',form=form, posts = display_posts, communities = communities, moderatorCommunityList = moderatorCommunityList, usersPic = usersImage)

def getAllProfilePictures():
    members = redis_cache.smembers('listusers')
    usersImage = {}
    for member in members:
        key = 'img_'+member
        usersImage[member] = redis_cache.get(key)
    print usersImage
    return usersImage
getAllProfilePictures()

@app.before_request
def before_request():
    g.user = current_user

@app.route('/profile/<username>', methods=['GET', 'POST'])
@login_required
def profilefrnd(username):
    temp = mongo.posts.find({ "author": username })
    userposts=[]
    for post in temp:
        userposts.append(post)
    userposts.sort(key=lambda r: r['posted_date'], reverse=True)
    userFriends = getUserFriends(username)
    user = User.query.filter_by(username=username).first()
    form = EditForm()
    usersImage = getAllProfilePictures()
    print "Outside gorm validate"
    if form.validate_on_submit():
        print ("Inside User Updated")
        user.email = form.email.data
        user.contact_number = form.contact.data
        user.firstName = form.firstname.data
        user.lastName = form.lastname.data
        print "Outside form Photo"
        if form.photo.data:
            f = form.photo.data
            filename = secure_filename(f.filename)
            res = upload_to_s3(f)
            print "S3 Bucket URL "
            print res
            if res != 'error':
                user.imageUrl = res
                print user.imageUrl
                user_image = mongo.author_images.find_one({'username': username})
                mongo.author_images.update_one({
                '_id': user_image['_id']
                },{
                '$set': {
                    'imagePath': res
                    }
                }, upsert=False)
                key = 'img_'+username
                redis_cache.set(key,res)
            print 'checking'
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('profile'))
    else:
        form.email.data = user.email
        form.contact.data = user.contact_number
        form.firstname.data = user.firstName
        form.lastname.data = user.lastName
        print ("Inside else User Updated")
    return render_template('profile.html', user = user , posts = userposts , userFriends = userFriends,form=form, usersPic=usersImage)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    username = current_user.username
    userposts = mongo.posts.find({ "author": username })
    userFriends = getUserFriends()
    user = User.query.filter_by(username=username).first()
    for friends in userFriends:
        print friends
    form = EditForm()
    usersImage = getAllProfilePictures()
    if form.validate_on_submit():
        print ("Inside User Updated")
        user.email = form.email.data
        user.contact_number = form.contact.data
        user.firstName = form.firstname.data
        user.lastName = form.lastname.data
        if form.photo.data:
            f = form.photo.data
            filename = secure_filename(f.filename)
            res = upload_to_s3(f)
            if res != 'error':
                user.imageUrl = res
                user_image = mongo.author_images.find({'username': username})
                mongo.author_images.update_one({
                '_id': user_image['_id']
                },{
                '$set': {
                    'imagePath': res
                    }
                }, upsert=False)
                key = 'img_'+username
                redis_cache.set(key,res)
        db.session.commit()
        print ("User Updated")
        flash('Your changes have been saved.')
        return redirect(url_for('profile'))
    else:
        form.email.data = user.email
        form.contact.data = user.contact_number
        form.firstname.data = user.firstName
        form.lastname.data = user.lastName
        print ("Inside else User Updated")
    return render_template('profile.html', form=form , posts = userposts , userFriends = userFriends ,user = user, usersPic=usersImage)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.rememberMe.data)
                session['loggedIn'] = True
                session['username'] = user.username
                flash('You have successfully logged In')
                print user.status
                print current_user.status
                print ("role")
                print (current_user.role)
                if current_user.role == 'admin':
                    print 'inside admin'
                    return redirect(url_for('admin'))
                return redirect(url_for('home'))
            else:
                flash('password is incorrect')
        else:
            flash('User is not registered')
    return render_template('_login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have successfully been logged out.')
    session['loggedIn'] = False
    return redirect(url_for('login'))

#get users in a community
@app.route('/get_community_users', methods = ['POST'])
@login_required
def getCommunityUsers():
    communityName = request.json['communityName'].lower()
    communityObj = Community.query.filter_by(name = communityName).first()
    communityUsers = UserCommunity.query.filter_by(communityID=communityObj.ID)
    users_list = []
    for item in communityUsers.all():
        users_list.append(item.userID)
    return json.dumps(users_list)

#get list of approved communities
@app.route('/get_community_list', methods = ['GET'])
@login_required
def getCommunityList():
    communities = Community.query.filter_by(status = 'Approved').all()
    communities_name = [community.name for community in communities]
    return json.dumps(communities_name)

#get list of requested communitites
@app.route('/get_requested_community', methods = ['GET'])
def getRequestedCommunity():
    communityObj = Community.query.filter_by(status = 'requested').all()
    communityList = []
    for item in communityObj:
        communityList.append(item)
    return communityList

#api to approve a requested community
@app.route('/approve_community/<communityId>', methods = ['GET'])
def approveCommunity(communityId):
    # communityName = request.json['name'].lower()
    # communityDetails = Community.query.filter_by(name = communityName).first()
    communityDetails = Community.query.filter_by(ID=communityId).first()
    created_by = communityDetails.created_by
    reqUser = User.query.filter_by(username=created_by).first()
    user_comm = UserCommunity(userID=created_by,
                        communityID=communityId)
    user_mod = UserModerator(communityID=communityId,
    moderator=created_by)
    communityDetails.status = 'Approved'
    reqUser.role = 'moderator'
    user = User.query.filter_by(username=created_by).first()
    user.role = 'moderator'
    db.session.add(user)
    db.session.add(user_comm)
    db.session.add(user_mod)
    db.session.commit()
    redis_cache.set(communityId,reqUser.username)
    redis_cache.sadd('communities',communityId)
    redis_cache.sadd(reqUser.username,communityId)
    message = 'Hi '+reqUser.username+', This is to inform that admin has approved a commmunity named as '+communityDetails.name+'. Now you are the moderator of the community.'
    sendDeclineMessage(reqUser.contact_number,message)
    return redirect(url_for('admin'))

# Decline Community
@app.route('/decline_community/<communityId>', methods = ['GET'])
def declineCommunity(communityId):
    # communityName = request.json['name'].lower()
    communityDetails = Community.query.filter_by(ID=communityId).first()
    Community.query.filter_by(ID=communityId).delete()
    created_by = communityDetails.created_by
    reqUser = User.query.filter_by(username=created_by).first()
    message = 'Hi '+reqUser.username+', This is to inform that admin has declined a new commmunity named as '+communityDetails.name+'. Sorry...'
    sendDeclineMessage(reqUser.contact_number,message)
    db.session.commit()
    return redirect(url_for('admin'))

#api to join a community
@app.route('/join_community', methods = ['POST'])
def joinCommunity():
    userID = request.form['username']
    communityID = request.form['id']
    print userID
    print communityID
    user_comm = UserCommunity(userID=userID,
                        communityID=communityID)
    UserRequestedCommunity.query.filter_by(communityID=communityID, userID=userID).delete()
    db.session.add(user_comm)
    db.session.commit()
    redis_cache.sadd(userID,communityID)
    communityName = (Community.query.filter_by(ID=communityID).first()).name
    message = 'Hi Moderator, This is to inform that '+current_user.username+' has joined '+communityName+' community. User email is '+ current_user.email +' .'
    subject = 'New Member Joined to '+ communityName + ' community.'
    data = {
        'status':200
    }
    return json.dumps(data)


# Delete Community modified Akhilesh
@app.route('/delete_community', methods = ['POST'])
def deleteCommunity():
    communityID = request.form['id']
    deleteCommunity(communityID)
    data = {
            'status':200
        }
    return json.dumps(data)

@app.route('/delete_post', methods = ['POST'])
def deletePost():
    postId = request.form['id']
    print postId
    mongo.posts.remove( {"_id" : ObjectId(str(postId)) } )
    data = {
            'status':200
        }
    return json.dumps(data)

@app.route('/delete_user', methods = ['POST'])
def deleteUser():
    userName = request.form['id']

    deleteUser(userName)
    data = {
            'status':200
        }
    return json.dumps(data)


# Code End
@app.route('/join_request', methods = ['POST'])
def joiningRequest():
    userID = current_user.username
    communityID = request.form['id']
    user_comm = UserRequestedCommunity(userID=userID,
                        communityID=communityID)
    db.session.add(user_comm)
    db.session.commit()
    communityName = (Community.query.filter_by(ID=communityID).first()).name
    message = 'Hi Moderator, This is to inform that '+current_user.username+' has requested to joined '+communityName+ "community."
    subject = 'New Member Requested to Join '+ communityName + ' community.'
    data = {
        'status':200
    }
    return json.dumps(data)

@app.route('/decline_request_user', methods = ['POST'])
def declineRequestByUser():
    userID = current_user.username
    communityID = request.form['id']
    UserRequestedCommunity.query.filter_by(communityID=communityID, userID=userID).delete()
    db.session.commit()
    data = {
        'status':200
    }
    return json.dumps(data)

#api route to
@app.route('/reject_request', methods = ['POST'])
def rejectRequestModerator():
    userID = request.form['username']
    communityID = request.form['id']
    print userID
    print communityID
    UserRequestedCommunity.query.filter_by(communityID=communityID, userID=userID).delete()
    db.session.commit()
    data = {
        'status': 200
    }
    return json.dumps(data)

#api to join a community
@app.route('/leave_community', methods = ['POST'])
def leaveCommunity():
    userID = current_user.username
    communityID = request.form['id']
    obj = UserModerator.query.filter_by(communityID=communityID).first().moderator
    if obj == userID:
        flash("User cannot be removed", "alert")
        data = {
            'status':200
        }
        return json.dumps(data)
    else:
        UserCommunity.query.filter_by(communityID=communityID, userID=userID).delete()
        db.session.commit()
        redis_cache.srem(userID,communityID)
        communityName = (Community.query.filter_by(ID=communityID).first()).name
        message = 'Hi Moderator, This is to inform that '+current_user.username+' has left '+communityName+' community. User email is '+ current_user.email +' .'
        subject = 'Member left '+ communityName + ' community.'
        sendEmail(message, subject)
        data = {
            'status':200
        }
        return json.dumps(data)

#api to get communities a user is member of
def getUserCommunities():
    communities = redis_cache.smembers(current_user.username)
    #redis
    # communities = UserCommunity.query.filter_by(userID=current_user.username).all()
    communityNames = []
    ids = []
    for item in communities:
        print item
        communityNames.append((Community.query.filter_by(ID=item).first()).name)
        ids.append(item)
        #redis
        # communityNames.append((Community.query.filter_by(ID=item.communityID).first()).name)
        # ids.append((Community.query.filter_by(ID=item.communityID).first()).ID)
    return [(k,v) for k,v in zip(ids, communityNames)]

#api to get full community details for a joined user community
@app.route('/user_joined_community', methods = ['GET'])
def getCommunityDetailsJoined():
    communities = redis_cache.smembers(current_user.username)
    # communities = UserCommunity.query.filter_by(userID=current_user.username).all()
    communityObj = []
    moderators = []
    response = []
    users = []
    for community in communities:
        #redis
        x = UserCommunity.query.filter_by(communityID = community).all()
        users.append(len(x))
        communityObj.append(Community.query.filter_by(ID = community).first())
        nameOfModerator = redis_cache.get(community)
        moderators.append(nameOfModerator)
        # x = UserCommunity.query.filter_by(communityID = community.communityID).all()
        # users.append(len(x))
        # communityObj.append(Community.query.filter_by(ID = community.communityID).first())
        # moderators.append(UserModerator.query.filter_by(communityID = community.communityID).first().moderator)
    for obj in communityObj:
        data = {
        "id" : obj.ID,
        "name" : obj.name,
        "creation_date" : str(obj.creation_date).split(" ")[0],
                }
        response.append(data)
    for i in range(0,len(moderators)):
        response[i]['moderator'] = moderators[i]
        response[i]['users'] = users[i]
    return response

#api to get full community details for a unjoined user community
@app.route('/user_unjoined_community', methods = ['GET'])
def getCommunityDetailsUnjoined():
    communities = redis_cache.smembers(current_user.username)
    totalCommunities = redis_cache.smembers('communities')
    #redis
    # communities = UserCommunity.query.filter_by(userID=current_user.username).all()
    # totalCommunities = Community.query.filter_by(status = 'Approved').all()
    requestedCommunities = UserRequestedCommunity.query.filter_by(userID=current_user.username).all()
    # jid = set()
    # tid = set()
    rid = set()
    jid = communities
    tid = totalCommunities
    for community in requestedCommunities:
        rid.add(community.communityID)
    # for community in communities:
    #     jid.add(community.communityID)
    # for community in totalCommunities:
    #     tid.add(community.ID)
    unjoined_temp =  tid - jid
    unjoined = unjoined_temp - rid
    moderators = []
    response = []
    communityObj = []
    users = []
    for id in unjoined:
        x = UserCommunity.query.filter_by(communityID = id).all()
        users.append(len(x))
        communityObj.append(Community.query.filter_by(ID = id).first())
        name_moderator = redis_cache.get(id)
        moderators.append(name_moderator)
        # x = UserCommunity.query.filter_by(communityID = id).all()
        # users.append(len(x))
        # communityObj.append(Community.query.filter_by(ID = id).first())
        # moderators.append(UserModerator.query.filter_by(communityID = id).first().moderator)
    for obj in communityObj:
        data = {
        "id" : obj.ID,
        "name" : obj.name,
        "creation_date" : str(obj.creation_date).split(" ")[0],
                }
        response.append(data)
    for i in range(0,len(moderators)):
        response[i]['moderator'] = moderators[i]
        response[i]['users'] = users[i]
    return response

#api to get full community details for a unjoined user community
@app.route('/user_requested_community', methods = ['GET'])
def getCommunityDetailsRequested():
    requestedCommunities = UserRequestedCommunity.query.filter_by(userID=current_user.username).all()
    rid = set()
    for community in requestedCommunities:
        rid.add(community.communityID)

    moderators = []
    response = []
    communityObj = []
    users = []
    for id in rid:
        x = UserCommunity.query.filter_by(communityID = id).all()
        users.append(len(x))
        communityObj.append(Community.query.filter_by(ID = id).first())
        name_moderator = redis_cache.get(id)
        moderators.append(name_moderator)
        #redis
        # x = UserCommunity.query.filter_by(communityID = id).all()
        # users.append(len(x))
        # communityObj.append(Community.query.filter_by(ID = id).first())
        # moderators.append(UserModerator.query.filter_by(communityID = id).first().moderator)
    for obj in communityObj:
        data = {
        "id" : obj.ID,
        "name" : obj.name,
        "creation_date" : str(obj.creation_date).split(" ")[0],
                }
        response.append(data)
    for i in range(0,len(moderators)):
        response[i]['moderator'] = moderators[i]
        response[i]['users'] = users[i]
    return response

#method to delete a community
def deleteCommunity(communityID):
    UserRequestedCommunity.query.filter_by(communityID=communityID).delete() 
    mod_name = redis_cache.get(communityID)
    UserCommunity.query.filter_by(communityID = communityID).delete()
    UserModerator.query.filter_by(communityID=communityID).delete()
    obj = UserModerator.query.filter_by(moderator=mod_name).first()
    print "Inside Del Moderator "
    print obj
    if obj is  None:
        print "Inside If del moderator"
        temp = User.query.filter_by(username=mod_name).first()
        temp.role = 'user'
        db.session.commit()
    communityObj = Community.query.filter_by(ID=communityID).first()
    name = communityObj.name
    posts = mongo.posts
    mongo.get_collection('posts').delete_many({"category": name})
    Community.query.filter_by(ID=communityID).delete()     
    db.session.commit()
    redis_cache.delete(communityID)
    redis_cache.srem('communities',communityID)
    _users = redis_cache.smembers('listusers')
    for _user in _users:
         print redis_cache.smembers(_user)
         redis_cache.srem(_user ,communityID)
         print redis_cache.smembers(_user)

#api to get posts filter by user
@app.route('/get_user_posts', methods = ['GET'])
def getPostsByUser():
    userID = current_user.username
    # communities = UserCommunity.query.filter_by(userID=userID).all()
    communities = redis_cache.smembers(userID)
    posts = mongo.posts
    generalPosts = []
    communityPosts = []
    communityNames = []
    response = []
    for item in communities:
        communityNames.append((Community.query.filter_by(ID=item).first()).name)
        #redis
        # communityNames.append((Community.query.filter_by(ID=item.communityID).first()).name)
    for name in communityNames:
        communityPosts.extend(posts.find({ "category": name }))
    for post in communityPosts:
        response.append(post)
    generalPosts.append(posts.find({ "category": "general" }))
    for item in generalPosts:
        for doc in item:
            response.append(doc)
    response.sort(key=lambda r: r['posted_date'], reverse=True)
    for post in response:
        post['_id'] = str(post['_id'])
    return response

#api to get the statistics
#@app.route('/get_stats', methods = ['GET'])
def getStats():
    communities = len(Community.query.all())
    users = len(User.query.all()) - 1
    post = mongo.posts
    posts = post.find()
    count = 0
    for item in posts:
        count = count + 1
    response = {
    "users" : users,
    "communities" : communities,
    "posts" : count
    }
    return response

#api to get the user messages
@app.route('/get_user_messages', methods = ['GET'])
@login_required
def getMessageByUser():
    userID = current_user.username
    messages = mongo.messages
    inbox = []
    sent = []
    inbox.extend(messages.find({ "toUserId": userID }))
    sent.extend(messages.find({"fromUserId": userID}))
    inbox.sort(key=lambda r: r['message_date'], reverse=True)
    sent.sort(key=lambda r: r['message_date'], reverse=True)
    for message in inbox:
        message['message_date'] = str(message['message_date'])
        message['_id'] = str(message['_id'])
    for message in sent:
        message['message_date'] = str(message['message_date'])
        message['_id'] = str(message['_id'])
    response = {
    "inbox": inbox,
    "sent": sent
    }
    return json.dumps(response)

@app.route('/community/<community_id>', methods=['GET', 'POST'])
def community(community_id):
    communityObj = Community.query.filter_by(ID=community_id).first()
    posts = mongo.posts
    communityPosts = posts.find({ "category": communityObj.name })
    users = []
    userObj = UserCommunity.query.filter_by(communityID = community_id).all()
    for obj in userObj:
        users.append(obj.userID)
    postFinal = []
    for post in communityPosts:
        postFinal.append(post)
    postFinal.sort(key=lambda r: r['posted_date'], reverse=True)
    for post in postFinal:
        post['_id'] = str(post['_id'])
    moderator = redis_cache.get(community_id)
    #redis
    # moderator = UserModerator.query.filter_by(communityID=community_id).first().moderator
    response = {
    "communityObj" : communityObj,
    "posts" : postFinal,
    "moderator" : moderator,
    "creation_date" : communityObj.creation_date,
    "users" : users
    }
    print response['users']
    usersImage = getAllProfilePictures()
    return render_template('_community.html',communityObj = response['communityObj'],posts = response['posts'], moderator = response['moderator'],
    date = response['creation_date'], members = response['users'], usersPic = usersImage)

#api to get user friends
@app.route('/get_user_friends', methods=['GET'])
def getUserFriends(username = None):
    if not username:
        userID = current_user.username
    else:
        userID = username
    userCommunity = redis_cache.smembers(userID)
    #redis
    # userCommunity = UserCommunity.query.filter_by(userID = userID).all()
    friends = set()
    for item in userCommunity:
        l = UserCommunity.query.filter_by(communityID = item).all()
        # l = UserCommunity.query.filter_by(communityID = item.communityID).all()
        for user in l:
            friends.add(user.userID)
    current = {userID}
    friendList = friends - current
    response = []
    obj = User.query.filter(User.username.in_(friendList)).all()
    # for item in obj:
    #     data = {
    #     "username" : item.username,
    #     "firstName" : item.firstName,
    #     "lastName" : item.lastName
    #     }
    #     response.append(data)
    # return response
    return obj

# Below Commented by Akhilesh - Didnot understand the functnality

#@app.route('/delete_user', methods = ['POST'])
def deleteUser(userID):
    #userID = request.json['userID']
    moderator = UserModerator.query.filter_by(moderator=userID).all()
    if len(moderator) != 0:
        flash("Delete user from moderator list")
    else:
        UserCommunity.query.filter_by(userID=userID).delete()
        User.query.filter_by(username=userID).delete()
        redis_cache.delete(userID)
        redis_cache.srem('listusers',userID)
        mongo.author_images.remove( {'username': userID} )
        mongo.posts.remove({'author':userID})
        key = 'img_'+userID
        redis_cache.delete(key)
        db.session.commit()


@app.route('/requestedCommunities')
def adminToApprove():
    listOfRequestedCommunitites = getRequestedCommunity()
    for item in listOfRequestedCommunitites:
        print item
    return render_template('_requestedCommunity.html', requestedCommunities = listOfRequestedCommunitites)

@app.route('/post/<id>', methods=['GET','POST'])
def post(id):
    form = CommentForm()
    if form.validate_on_submit():
        if form.comment.data:
            impagePath = None
            if not current_user.imageUrl:
                impagePath = current_user.gravatar()
            else:
                impagePath = current_user.imageUrl
            mongo.posts.update_one(
            {"_id": ObjectId(str(id))},
            {"$push": {
                'comments': {
                    'author': { 'name': current_user.username, 'imageUrl' : impagePath},
                    'posted': datetime.datetime.utcnow(),
                    'text': form.comment.data,
                    'disabled': False
                        }
                    }
                }
            )
            form.comment.data = ''
            flash('Your comment has been added')
    _id = str(id)
    post = mongo.posts.find_one({ "_id": ObjectId(_id) })
    usersImage = getAllProfilePictures()
    return render_template('_post.html', post=post, commentForm=form, usersPic = usersImage)


@app.route('/editpost/<id>', methods=['GET', 'POST'])
@login_required
def editPost(id):
    _id = str(id)
    post = mongo.posts.find_one({ "_id": ObjectId(_id) })
    _categories = getUserCommunities()
    categories = [(int(_cat[0]),_cat[1])for _cat in _categories]
    categories.append((0,'general'))
    name = post['category']
    category = Community.query.filter_by(name=name).first()
    if category:
        categoryId = category.ID
    else:
        categoryId = 0
    form = EditArticleForm(categories,category=categoryId)
    if form.validate_on_submit():
        title = form.title.data
        body = form.body.data
        content_html = convertIntoHTML(body)
        category = dict(categories).get(form.category.data)
        # print body
        post['title'] = title
        post['conntent'] = body
        post['contentHTML'] = content_html
        post['category'] = category
        # Below route need to be changed..
        mongo.posts.update_one({
              '_id': post['_id']
            },{
              '$set': {
                'title': title,
                'content': body,
                'contentHTML': content_html,
                'category':category,
                'posted_date':datetime.datetime.utcnow()
              }
            }, upsert=False)
        flash('Your post has been updated')
        return redirect(url_for('home'))
    form.title.data = post['title']
    form.body.data = post['content']
    return render_template('_editPost.html', form=form, id = id)

@app.route('/disable', methods=['POST'])
@login_required
def disable():
    _id = request.form['id']
    post = mongo.posts.find_one({ "_id": ObjectId(_id) })
    flash('The post has been disabled.')
    # Below route need to be changed..
    mongo.posts.update_one({
          '_id': post['_id']
        },{
          '$set': {
              'disabled': True,
            'posted_date':datetime.datetime.utcnow()
          }
        }, upsert=False)
    data = {
        'status': 200
    }
    return json.dumps(data)

@app.route('/enable', methods=['POST'])
@login_required
def enable():
    _id = request.form['id']
    post = mongo.posts.find_one({ "_id": ObjectId(_id) })
    flash('The post has been disabled.')
    # Below route need to be changed..
    mongo.posts.update_one({
          '_id': post['_id']
        },{
          '$set': {
              'disabled': False,
            'posted_date':datetime.datetime.utcnow()
          }
        }, upsert=False)
    data = {
        'status': 200
    }
    return json.dumps(data)

# def admin():
#     userModObj = UserModerator.query.all()
#     communityNames = []
#     for obj in userModObj:

def userModeratorCommunityList():
    moderatorCommunityListObj = UserModerator.query.filter_by(moderator = current_user.username).all()
    communityList = []
    for item in moderatorCommunityListObj:
        communityList.append(Community.query.filter_by(ID=item.communityID).first().name)
    return communityList

def adminCommunityData():
    userMod = UserModerator.query.all()
    response = []
    for obj in userMod:
        username = obj.moderator
        communityID = obj.communityID
        userObj = User.query.filter_by(username = username).first()
        firstName = userObj.firstName
        lastName = userObj.lastName
        communityObj = Community.query.filter_by(ID = communityID).first()
        membersCount = len(UserCommunity.query.filter_by(communityID = communityID).all())

        communityName = communityObj.name
        creation_date = communityObj.creation_date
        data = {
        "username" : username,
        "communityID" : communityID,
        "firstName" : firstName,
        "lastName" : lastName,
        "communityName" : communityName,
        "creation_date" : creation_date,
        "count": membersCount
        }
        response.append(data)
    return response

@app.route('/requestedtojoincommunitites', methods=['GET'])
def moderatorUserData():
    current_moderator = current_user.username
    print current_moderator
    moderatorCommObj = UserModerator.query.filter_by(moderator=current_moderator).all()
    communityName = []
    moderator_communities = []
    requested = []
    response = []
    for obj in moderatorCommObj:
        moderator_communities.append(obj.communityID)
    for id in moderator_communities:
        name = Community.query.filter_by(ID=id).first().name
        print name
        userReqObj = UserRequestedCommunity.query.filter_by(communityID=id).all()
        if userReqObj is not None:
            for obj in userReqObj:
                user = User.query.filter_by(username=obj.userID).first()
                print user.username
                data = {
                "community_id" : id,
                "community_name" : name,
                "username" : user.username
                }
                response.append(data)
    return render_template('_requestedCommunities.html', response=response)

@app.route('/network', methods=['GET'])
def getNetwork():
    communityObj = Community.query.all()
    userCommunity = UserCommunity.query.all()
    communities = []
    users = []
    for obj in communityObj:
        communities.append([obj.ID, obj.name])
    start = 999
    for obj in userCommunity:
        data = {
        "id" : start,
        "name" : obj.userID,
        "com" : obj.communityID
        }
        users.append(data)
        start = start - 1

    response = {
    "community" : communities,
    "user" : users
    }

    return json.dumps(response)

@app.route('/admin/graph', methods=['GET'])
def render_graph():
    adminData = getStats()
    return render_template("test.html",adminData=adminData)


@app.route('/admin/billing', methods=['GET'])
def render_billing():
    adminData = getStats()
    billDetails = billing()

    return render_template("billing.html",adminData=adminData , billDetails= billDetails)


def billing():
    print('check1')
    client = boto3.client('budgets')
    response = client.describe_budget(
    AccountId='507614993775',
    BudgetName='MonthlyAWSBudget'
    )
    return response


def upload_to_s3(file):
    # bucket_name = 'image-cmpe281-social-network'
    bucket_name = 'cmpe281smartcommunity'
    ext = file.filename.split('.')[1]
    file.filename = current_user.username + '.'+ ext
    s3 = boto3.client('s3')
    try:
        s3.upload_fileobj(
            file,
            bucket_name,
            file.filename,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": file.content_type
            }
        )
    except Exception as e:
        # This is a catch all exception, edit this part to fit your needs.
        print("Something Happened: ", e)
        return 'error'
    return 'https://s3.amazonaws.com/{}/{}'.format(bucket_name,file.filename)

@app.route("/msgtomoderator/<communityID>",methods = ['GET','POST'])
def msgToModerator(communityID):
    moderator = UserModerator.query.filter_by(communityID=communityID).first().moderator
    communityName = Community.query.filter_by(ID=communityID).first().name
    form = ExternalMessageForm()
    if form.validate_on_submit():
        print form.message.data
        print form.subject.data
        message = {
            'subject': form.subject.data,
            'msg': form.message.data,
            'sender': current_user.username,
            'community': communityName,
            'recipient': moderator,
        }
        send_to_queue(message)
        # mongo.mod_messages.insert_one(message)
        flash('Your Message has been delievered to the moderator')
        return redirect(url_for('community',community_id=communityID))
    return render_template('_messageTemplate.html',form=form, moderator=moderator, community=communityID)

@app.route("/msgtoadmin", methods=['GET','POST'])
def msgToAdmin():
    form = ExternalMessageForm()
    if form.validate_on_submit():
        print form.message.data
        print form.subject.data
        messageToAdmin = {
            'subject': form.subject.data,
            'msg': form.message.data,
            'sender': current_user.username,
            'community': 'NA',
            'recipient': 'admin'
        }
        # mongo.mod_messages.insert_one(messageToAdmin)
        send_to_queue(messageToAdmin)
        flash('Your Message has been delievered to the Admin')
        return redirect(url_for('home'))
    return render_template('_messageTemplate.html',form=form, moderator='admin')

def send_to_queue(message):
    # Send message to SQS queue
    print message
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageAttributes={
            'Subject': {
                'DataType': 'String',
                'StringValue': message['subject']
            },
            'Msg': {
                'DataType': 'String',
                'StringValue': message['msg']
            },
            'Sender': {
                'DataType': 'String',
                'StringValue': message['sender']
            },
            'Community': {
                'DataType': 'String',
                'StringValue': message['community']
            },
            'Recipient': {
                'DataType': 'String',
                'StringValue': message['recipient']
            }
        },
        MessageBody=(
            'New message to {0} from {1}'.format(message['recipient'],message['sender'])
        )
    )

# def createAdmin():
#     admin = User(username='admin',
#                     firstName='admin',
#                     lastName='admin',
#                     email='socialnetwork281@gmail.com',
#                     password=generate_password_hash('Cmpe@281',method='sha256'),
#                     contact_number=9999999999,
#                     joining_date=datetime.datetime.utcnow(),
#                     status = 'approved',
#                     role='admin')
#     db.session.add(admin)
#     db.session.commit()

# createAdmin()

if __name__ == '__main__':
    app.run(debug = False,threaded=True,host='0.0.0.0',port=3000)
