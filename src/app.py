"""
Flask Documentation:     http://flask.pocoo.org/docs/
Flask-SQLAlchemy Documentation: http://flask-sqlalchemy.pocoo.org/
SQLAlchemy Documentation: http://docs.sqlalchemy.org/
FB Messenger Platform docs: https://developers.facebook.com/docs/messenger-platform.

This file creates your application.
"""

import os
import flask
import requests
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from chatbot import Chatbot

FACEBOOK_API_MESSAGE_SEND_URL = (
    'https://graph.facebook.com/v2.6/me/messages?access_token=%s')

app = flask.Flask(__name__)

# TODO: Set environment variables appropriately.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['FACEBOOK_PAGE_ACCESS_TOKEN'] = os.environ[
    'FACEBOOK_PAGE_ACCESS_TOKEN']
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mysecretkey')
app.config['FACEBOOK_WEBHOOK_VERIFY_TOKEN'] = 'mysecretverifytoken'


db = SQLAlchemy(app)
chatbot = Chatbot()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(80), unique=True)


class TodoItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    text = db.Column(db.String, nullable=False)
    dateAdded = db.Column(db.Date, nullable=False)
    dateCompleted = db.Column(db.Date, nullable=True) #None if event not completed

    # Connect each address to exactly one user.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # This adds an attribute 'user' to each address, and an attribute
    # 'addresses' (containing a list of addresses) to each user.
    user = db.relationship('User', backref='todos')


@app.route('/')
def index():
    """Simple example handler.

    This is just an example handler that demonstrates the basics of SQLAlchemy,
    relationships, and template rendering in Flask.

    """
    # Just for demonstration purposes
    for user in User.query:  #
        print 'User %d, username %s' % (user.id, user.sender_id)
        for todo in user.todos:
            print 'Todo %d: %s at' % (todo.id, todo.text)

    # Render all of this into an HTML template and return it. We use
    # User.query.all() to obtain a list of all users, rather than an
    # iterator. This isn't strictly necessary, but just to illustrate that both
    # User.query and User.query.all() are both possible options to iterate over
    # query results.
    return flask.render_template('index.html', users=User.query.all())

def get_todo_tasks(user, isComplete = False):
    if isComplete:
        return TodoItem.query.filter_by(user=user).filter(TodoItem.dateCompleted != None).order_by(TodoItem.dateAdded).all()
    else:
        return TodoItem.query.filter_by(user=user).filter_by(dateCompleted=None).order_by(TodoItem.dateAdded).all()

def word_has(word, matches):
    for match in matches: 
        if match in word.lower():
            return True
    return False

def get_tutorial():
    tutorial_send = "TUTORIAL FOR Todo-TK. Here is a list of basic commands you can use: "
    tutorial_send += "\n- 'help' will display this tutorial"
    tutorial_send += "\n- 'list' will print out your current todo list"
    tutorial_send += "\n- 'list complete' will print out your list of completed tasks"
    tutorial_send += "\n- 'add str' will create a new todo item with the label str"
    tutorial_send += "\n- 'search str' will give you a list of all completed and incomplete todos which contain str"
    tutorial_send += "\n- '$n finish' will mark the todo item with index n as complete"
    tutorial_send += "\n- '$n edit str' will change the todo item with index n to have a new label str"
    tutorial_send += "\n- '$n delete' will delete the todo item with index n"
    #tutorial_send += "\n- 'clear all', 'clear completed', 'clear todo' will respectively, clear all lists, clear the list of completed tasks, and clear the current todo list"
    return tutorial_send

@app.route('/fb_webhook', methods=['GET', 'POST'])
def fb_webhook():
    # Handle the initial handshake request.
    if flask.request.method == 'GET':
        if (flask.request.args.get('hub.mode') == 'subscribe' and
            flask.request.args.get('hub.verify_token') ==
            app.config['FACEBOOK_WEBHOOK_VERIFY_TOKEN']):
            challenge = flask.request.args.get('hub.challenge')
            return challenge
        else:
            print 'Received invalid GET request'
            return ''  # Still return a 200, otherwise FB gets upset.

    # Get the request body as a dict, parsed from JSON.
    payload = flask.request.json

    # TODO: Validate app ID and other parts of the payload to make sure we're
    # not accidentally processing data that wasn't intended for us.

    # Handle an incoming message.
    # TODO: Improve error handling in case of unexpected payloads.
    for entry in payload['entry']:
        for event in entry['messaging']:
            if 'message' not in event:
                continue
            message = event['message']
            # Ignore messages sent by us.
            if message.get('is_echo', False):
                continue
            # Ignore messages with non-text content.
            if 'text' not in message:
                continue
            sender_id = event['sender']['id']

            message_send = chatbot.process(message)

            request_url = FACEBOOK_API_MESSAGE_SEND_URL % (app.config['FACEBOOK_PAGE_ACCESS_TOKEN'])
            requests.post(request_url, headers={'Content-Type': 'application/json'},
                          json={'recipient': {'id': sender_id}, 'message': {'text': message_send}})

    # Return an empty response.
    return ''

if __name__ == '__main__':
    app.run(debug=True)
