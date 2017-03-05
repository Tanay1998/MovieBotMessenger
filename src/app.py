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

            #Get user 
            curUser = User.query.filter_by(sender_id=sender_id).first()
            if curUser == None:
                curUser = User(sender_id=sender_id)
                db.session.add(curUser)
                db.session.commit()
                tutorial_send = get_tutorial()
                request_url = FACEBOOK_API_MESSAGE_SEND_URL % (app.config['FACEBOOK_PAGE_ACCESS_TOKEN'])
                requests.post(request_url, headers={'Content-Type': 'application/json'},
                          json={'recipient': {'id': sender_id}, 'message': {'text': tutorial_send}})

            message_text = (message['text']).strip()
            print "Got: " + message_text

            '''
                Process message_text & Get message to send 
            '''

            message_send = "Invalid command. To view all commands, type 'help'"

            # Display help
            if word_has(message_text.split()[0], ["help"]):
                message_send = get_tutorial()

            # To view list of completed tasks
            elif word_has(message_text.split()[0], ["list", "ls", "display"]) and word_has(message_text, ["done", "complete"]):       
                message_send = "Completed Tasks:"

                completeTodos = get_todo_tasks(curUser, True)
                for i in range(len(completeTodos)):
                    todo = completeTodos[i]
                    message_send += "\n#%d: %s" % (i + 1, todo.text)
                if len(completeTodos) == 0:
                    message_send = "No tasks completed yet!"

            #To view list of tasks todo
            elif word_has(message_text.split()[0], ["list", "ls", "display"]):              
                message_send = "Tasks Todo:"
                incompleteTodos = get_todo_tasks(curUser, False)
                for i in range(len(incompleteTodos)):
                    todo = incompleteTodos[i]
                    message_send += "\n#%d: %s" % (i + 1, todo.text)
                if len(incompleteTodos) == 0:
                    message_send = "No tasks todo!"   

            #Clear tasks
            elif word_has(message_text.split()[0], ["clear", "delete", "remove", "erase"]) and word_has(message_text, ["all", "complete", "finish", "todo"]):
                deleteIncomplete = False 
                deleteComplete = False 
                if word_has(message_text, [" complete", " finish"]):
                    deleteComplete = True
                if word_has(message_text, [" incomplete", " todo"]):
                    deleteIncomplete = True
                if not deleteIncomplete and not deleteComplete:
                    deleteIncomplete, deleteComplete = True, True

                message_send = "Clearing tasks:"
                if deleteComplete:
                    TodoItem.query.filter_by(user=curUser).filter(TodoItem.dateCompleted != None).delete(synchronize_session=False)
                    message_send += "\n\tCleared completed tasks"
                if deleteIncomplete:
                    TodoItem.query.filter_by(user=curUser).filter_by(dateCompleted = None).delete(synchronize_session=False)
                    message_send += "\n\tCleared todo tasks"
                db.session.commit()

            elif len(message_text) > 0:
                query = message_text.split()

                #Search for tasks
                if len(query) > 1 and word_has(query[0], ["search"]):
                    searchQuery = ' '.join(query[1:])
                    todoList = TodoItem.query.filter_by(user=curUser).order_by(TodoItem.dateAdded).all()
                    matches = []
                    for i in range(len(todoList)):
                        todo = todoList[i]
                        if searchQuery in todo.text:
                            matches.append(todo.text + (" (Incomplete)" if todo.dateCompleted == None else " (Finished)"))
                    if len(matches) == 0:
                        message_send = "No matches found for search"
                    else:
                        message_send = "Found %d results: " % (len(matches))
                        for match in matches:
                            message_send += "\n\t" + match

                #Add a new task
                elif len(query) > 1 and word_has(query[0], ["add", "insert", "input"]):   # For adding a new todo
                    text = ' '.join(query[1:])
                    newTodo = TodoItem(text=text, user=curUser, dateAdded=datetime.utcnow(), dateCompleted=None)
                    db.session.add(newTodo)
                    db.session.commit()
                    message_send = "To-do item '" + text + "' added to list."

                elif len(query) > 1 and query[0][0] == '$':            # For Marking as complete, editing deleting
                    index = int(query[0][1:])

                    # Mark as finished
                    if word_has(query[1], ["finish", "done", "complete"]):
                        todoList = get_todo_tasks(curUser, False)
                        if index > len(todoList):
                            message_send = "A task with this index does not exist"
                        else: 
                            curTodo = todoList[index - 1]
                            curTodo.dateCompleted = datetime.utcnow()
                            db.session.commit()
                            message_send = "Finished " + query[0] + ": " + curTodo.text

                    # Edit task
                    elif len(query) > 2 and word_has(query[1], ["edit", "modify", "change"]):
                        todoList = get_todo_tasks(curUser, False)
                        if index > len(todoList):
                            message_send = "A task with this index does not exist"
                        else: 
                            curTodo = todoList[index - 1]
                            curTodo.text = ' '.join(query[2:])
                            db.session.commit()
                            message_send = "Updated " + query[0] + ": " + curTodo.text

                    #Delete task
                    elif word_has(query[1], ["remove", "delete", "clear", "erase"]):
                        todoList = get_todo_tasks(curUser, False)
                        if index > len(todoList):
                            message_send = "A task with this index does not exist"
                        else: 
                            curTodo = todoList[index - 1]
                            db.session.delete(curTodo)
                            db.session.commit()
                            message_send = "Deleted " + query[0] + ": " + curTodo.text


            request_url = FACEBOOK_API_MESSAGE_SEND_URL % (app.config['FACEBOOK_PAGE_ACCESS_TOKEN'])
            requests.post(request_url, headers={'Content-Type': 'application/json'},
                          json={'recipient': {'id': sender_id}, 'message': {'text': message_send}})

    # Return an empty response.
    return ''

if __name__ == '__main__':
    app.run(debug=True)
