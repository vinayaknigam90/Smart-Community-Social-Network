from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, IntegerField, SelectField, ValidationError, TextAreaField, SubmitField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import InputRequired, Email, Length, NumberRange, DataRequired, Regexp
from flask_pagedown.fields import PageDownField

class LoginForm(FlaskForm):
    """User Login Form"""
    username = StringField('Username',validators=[DataRequired(),Length(4,15,'UserName must be between 4 to 15 characters')])
    password = PasswordField('Password',validators=[DataRequired(),Length(8,80,'Password must be of atleast 8 characters')])
    rememberMe = BooleanField('Remember Me',default=False)
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    """User Registration Form"""

    email = StringField('Email:',validators=[DataRequired(),Email(message='Invalid email'),Length(5,50,'Email must be of atleast more than 5 characters')])
    username = StringField('Username:', validators=[DataRequired(), Length(4,15,'UserName must be between 4 to 15 characters'),Regexp('^[A-Za-z][A-Za-z0-9_]*$', 0,
               'Usernames must have only letters, numbers or underscores')])
    firstname = StringField('Firstname:', validators=[DataRequired(), Length(1,30,'Firstname must be between 1 to 30 characters')])
    lastname = StringField('Lastname:', validators=[DataRequired(), Length(1,30,'Lastname must be between 1 to 30 characters')])
    contact = IntegerField('Mobile:', validators=[DataRequired()])
    password = PasswordField('Password:',validators=[DataRequired(),Length(8, 80,'Password must be of atleast 8 characters')])
    submit = SubmitField('Register')

class EditForm(FlaskForm):
    """User Edit Form"""
    photo = FileField('Change ProfilePic',validators=[FileAllowed(['jpg', 'png'], 'Images only!')])
    email = StringField('Email:',validators=[DataRequired(),Email(message='Invalid email'),Length(5,50,'Email must be of atleast more than 5 characters')])
    firstname = StringField('Firstname:', validators=[DataRequired(), Length(1,30,'Firstname must be between 1 to 30 characters')])
    lastname = StringField('Lastname:', validators=[DataRequired(), Length(1,30,'Lastname must be between 1 to 30 characters')])
    contact = IntegerField('Mobile:', validators=[DataRequired()])
    submit = SubmitField('Update')

    # def validateEmail(self,_email):
    #     if User.query.filter_by(email=_email).first():
    #         raise ValidationError('Email is already in use.')
    #
    # def validateUserName(self,_username):
    #     if User.query.filter_by(username=_username).first():
    #         raise ValidationError('Username is already in use.')

class commuityRegistraion(FlaskForm):
    """User Registration Form"""
    name = StringField('Name:', validators=[DataRequired(), Length(4,50,'Community Name must be between 4 to 50 characters')])
    desc = StringField('Description:',validators=[Length(max=256,message='Description should be less than of 256 letters.')])
    address = StringField('Address:', validators=[DataRequired(), Length(4,50)])
    city = StringField('City:', validators=[DataRequired(), Length(max=30)])
    zip_code = IntegerField('ZipCode:', validators=[DataRequired()])

class commuityUpdateForm(FlaskForm):
    """User Registration Form"""
    def __init__(self, members, *args,**kwargs):
        super(commuityUpdateForm, self).__init__(*args, **kwargs)
        self.moderator.choices = members

    desc = StringField('Description:',validators=[Length(max=256,message='Description should be less than of 256 letters.')])
    address = StringField('Address:', validators=[DataRequired(), Length(4,50)])
    city = StringField('City:', validators=[DataRequired(), Length(max=30)])
    zip_code = IntegerField('ZipCode:', validators=[DataRequired()])
    moderator = SelectField('Moderator:', coerce=int)

class commuityUpdateFormForModerator(FlaskForm):
    """Community Update Form"""

    desc = StringField('Description:',validators=[Length(max=256,message='Description should be less than of 256 letters.')])
    address = StringField('Address:', validators=[DataRequired(), Length(4,50)])
    city = StringField('City:', validators=[DataRequired(), Length(max=30)])
    zip_code = IntegerField('ZipCode:', validators=[DataRequired()])

# Post Form Class
class ArticleForm(FlaskForm):
    def __init__(self, categories, *args,**kwargs):
        super(ArticleForm, self).__init__(*args, **kwargs)
        self.category.choices = categories

    title = StringField('Title', validators=[DataRequired(),Length(min=1, max=256)])
    body = PageDownField("What's on your mind?", validators=[DataRequired()])
    # body = TextAreaField('Content', validators=[DataRequired(),Length(max=256)])
    category = SelectField('Category:',coerce=int)
    submit = SubmitField('Post')


# Post Form Class
class EditArticleForm(FlaskForm):
    def __init__(self, categories, *args, **kwargs):
        super(EditArticleForm, self).__init__(*args, **kwargs)
        self.category.choices = categories

    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=256)])
    body = PageDownField("What's on your mind?", validators=[DataRequired()])
    # body = TextAreaField('Content', validators=[DataRequired(),Length(max=256)])
    category = SelectField('Category:', coerce=int)
    submit = SubmitField('Edit Post')

class CommentForm(FlaskForm):
    comment = StringField('', validators=[DataRequired()])
    submit = SubmitField('Add Comment')

class ChatForm(FlaskForm):
    msg = StringField('', validators=[DataRequired()])
    submit = SubmitField('Send Message')

class ExternalMessageForm(FlaskForm):
    subject = StringField('Subject',validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=1, max=256)])
    submit = SubmitField('Send Message')
