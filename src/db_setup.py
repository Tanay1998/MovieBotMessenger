from app import TodoItem, User, db

db.drop_all()
db.create_all()

admin = User(sender_id='admin')
todo1 = TodoItem(text='Eat cookie', user=admin, dateAdded=datetime.utcnow(), dateCompleted=datetime.utcnow())
todo2 = TodoItem(text='Wash clothes', user=admin, dateAdded=datetime.utcnow(), dateCompleted=None)

db.session.add(admin)
db.session.add(todo1)
db.session.add(todo2)

db.session.commit()

print User.query.all()
print TodoItem.query.all()
