import pymongo
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room
from database import get_user, user_info, get_password

app = Flask(__name__)
socketio = SocketIO(app)


my_client = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = my_client["chatapp"]
my_rooms = mydb["all_rooms"]
my_users = mydb["all_users"]
my_chat = mydb['all_chat']
my_broadcastedmsgs = mydb["broadcastedmsgs"]


@app.route('/index')
def home():
    return render_template("index.html")


rooms = []
usernames = []
for x in my_chat.find({}, {"_id": 0, "room": 1}):
    rooms.append(x['room'])


for x in my_users.find({}, {"_id": 0, "user": 1}):
    usernames.append(x['user'])


@app.route('/chat')
def chat():
    print('inside chat function')
    username = request.args.get('username')
    room = request.args.get('room')

    room_cnt = rooms.count(room)
    uname_cnt = usernames.count(username)

    if room_cnt > 0 and uname_cnt > 0:
        return render_template('chat.html', username=username, room=room)

    elif room_cnt == 0 and uname_cnt > 0:
        rooms.append(room)
        add_room_query = {"room": room}
        xk = my_rooms.insert_one(add_room_query)
        print("new room created:", xk)
        return render_template('chat.html', username=username, room=room)

    elif uname_cnt == 0 and room_cnt > 0:
        usernames.append(username)
        add_user_query = {"user": username}
        xk = my_users.insert_one(add_user_query)
        print("new user created:", xk)
        return render_template('chat.html', username=username, room=room)
    elif uname_cnt == 0 and room_cnt == 0:
        # user_add
        usernames.append(username)
        add_user_query = {"user": username}
        y = my_users.insert_one(add_user_query)
        print("new user created:", y)

        # room_add
        rooms.append(room)
        add_room_query = {"room": room}
        xk = my_rooms.insert_one(add_room_query)
        print("new room created:", xk)
        return render_template('chat.html', username=username, room=room)
    else:
        print("inside else of chat function")
        return render_template("index.html")


@socketio.on('join_room')
def handle_join_room_event(data):
    app.logger.info("{} has joined the room {}".format(data['username'], data['room']))
    join_room(data['room'])
    socketio.emit('join_room_announcement', data, room=data['room'])


@socketio.on('send_message')
def handle_send_message_event(data):
    app.logger.info("{} has sent message to the room {}: {}".format(data['username'], data['room'], data['message']))

    # dev's code
    add_chat_query = {"room": data['room'], "username": data['username'], "message": data['message']}
    z = my_chat.insert_one(add_chat_query)
    print("new chat added:", z)

    socketio.emit('receive_message', data, room=data['room'])


@socketio.on('leave_room')
def handle_leave_room_event(data):
    app.logger.info("{} has left the room {}".format(data['username'], data['room']))
    leave_room(data['room'])
    socketio.emit('leave_room_announcement', data, room=data['room'])


@socketio.on('broadcasting')
def broadcasting(data):
    print("inside broadcasting or broad function")
    # dev's code
    add_chat_query = {"message": data}
    z = my_broadcastedmsgs.insert_one(add_chat_query)
    print("new msg broadcasted:", z)
    print("going to emit", data)
    data = "broadcasted msg:"+str(data)
    
    socketio.emit('rb', data)
    print("emitted broadcast")


@app.route('/login', methods=['POST', 'GET'])
def login():
    note = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if get_user(username) != None and get_password(password) != None:
            return redirect(url_for('home'))
        else:
            note = 'username or password should be wrong'

    return render_template('login.html', note=note)


@app.route('/')
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    messages = ''
    if request.method == 'POST':
        username1 = request.form.get('username')
        password = request.form.get('password')

        if get_user(username1) == None:
            user_info(username1, password)
            return redirect(url_for('login'))
        else:
            messages = 'user already exist'
    return render_template('signup.html', messages=messages)


if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0", port=8000)
