#!/usr/bin/env python
# 
# imports	-----------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
 
from dbsetup import Base, Catagory, Item
from random import seed, randint


# DB engine
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
session = DBSession()

# seed random number generator
seed(1)


# catagories [from description]
cats = [
		'Soccer',
		'Basketball',
		'Bsaeball',
		'Frisbee',
		'Snowboarding',
		'Rock Climbing',
		'Foosball',
		'Skiating',
		'Hockey'
	]

for cat in cats:
	catx = Catagory(name = cat)
	session.add(catx)
	session.commit()

	# fill items automatically
	for i in range(randint(0, 50)):
		# item id
		i += 1
		# generate item no. x on the fly
		itemx = Item(name = str(catx.name)+' | Item.'+str(i),
						description = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum",
						catagory = catx
						)
		# commit to database
		session.add(itemx)
		session.commit()