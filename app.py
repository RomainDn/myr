from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myr.db'
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    prenom = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    nom = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    
    # Relation avec les groupes où l'utilisateur est membre
    member_of_groups = db.relationship('Group', secondary='user_groups', backref='members')

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relation avec les messages du groupe
    messages = db.relationship('Message', backref='group', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='messages')


    def __repr__(self):
        return f"Message('{self.user_id}', '{self.content}', '{self.timestamp}')"

class UserGroups(db.Model):
    __tablename__ = 'user_groups'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)

@app.route("/")
def home():
    if 'username' in session:
        username = session['username']
        return render_template("index.html", username=username)
    return render_template("index.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['Username']
        password = request.form['Password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['username'] = user.username
            user.online = True
            db.session.commit()
            return redirect(url_for('chat'))
        return render_template('login.html', error='Invalid Credentials')
    return render_template("login.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        prenom = request.form['Prenom']
        nom = request.form['Nom']
        age = request.form['Age']
        username = request.form['Username']
        password = request.form['Password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error='Username already exists')
        new_user = User(username=username, password=password, prenom=prenom, age=age, nom=nom)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = new_user.username
        new_user.online = True
        db.session.commit()
        return redirect(url_for('chat'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            db.session.commit()
        session.pop('username', None)
    return redirect(url_for('login'))

@app.route("/chat", methods=["POST", "GET"])
def chat():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            groups = user.member_of_groups
            return render_template("chat.html", username=user.username, groups=groups)
    return render_template("chat.html")

@app.route("/create-group", methods=['GET', 'POST'])
def create_group():
    if 'username' in session:
        if request.method == 'POST':
            group_name = request.form['Nom_du_groupe']
            participant_ids = request.form.getlist('Participant[]')

            current_user = User.query.filter_by(username=session['username']).first()
            new_group = Group(name=group_name, created_by=current_user.id)
            db.session.add(new_group)
            db.session.commit()

            if str(current_user.id) not in participant_ids:
                participant_ids.append(str(current_user.id))

            for user_id in participant_ids:
                user = User.query.get(user_id)
                if user:
                    new_group.members.append(user)

            db.session.commit()
            return redirect(url_for('chat'))

        users = User.query.all()
        username = session['username']
        return render_template("create_group.html", username=username, users=users)

    return redirect(url_for('login'))

@app.route("/group/<int:group_id>", methods=['GET'])
def group(group_id):
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        group = Group.query.get(group_id)
        if group and user in group.members:
            messages = Message.query.filter_by(group_id=group_id).order_by(Message.timestamp.asc()).all()
            print(messages)
            return render_template("group.html", username=user.username, group=group, messages=messages)
    return redirect(url_for('login'))

@app.route("/send_message/<int:group_id>", methods=['POST'])
def send_message(group_id):
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        group = Group.query.get(group_id)
        if group and user in group.members:
            content = request.form['message']
            new_message = Message(content=content, group_id=group_id, user_id=user.id)
            db.session.add(new_message)
            db.session.commit()
            return redirect(url_for('group', group_id=group_id))
    return redirect(url_for('login'))

@app.route("/account")
def account():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        username = session['username']
        return render_template("account.html", username=username, user=user)
    return render_template("account.html")

@app.route('/update_account', methods=['POST'])
def update_account():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user.prenom = request.form['prenom']
            user.nom = request.form['nom']
            user.age = request.form['age']
            db.session.commit()
            return redirect(url_for('account'))
    return redirect(url_for('login'))

@app.route('/delete_account')
def delete_account():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            session.pop('username', None)
    return redirect(url_for('login'))

@app.route("/apropos")
def apropos():
    if 'username' in session:
        username = session['username']
        return render_template("apropos.html", username=username)
    return render_template("apropos.html")

if __name__ == '__main__':
    app.run(host='10.101.14.46', debug=True)
