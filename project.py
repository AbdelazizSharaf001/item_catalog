#!/usr/bin/env python
# 
# imports	-----------------------
import random, re, string, httplib2, json, requests
# HTTP
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
# DataBase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dbsetup import Base, Catagory, Item
# Flask
from flask import (
	Flask,
	render_template,
	request,
	redirect,
	url_for,
	jsonify,
	session,
	make_response
)
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from flask_login import (
	LoginManager,
	current_user,
	login_required,
	login_user,
	logout_user,
)
from oauthlib.oauth2 import WebApplicationClient


# application start
app = Flask(__name__)
# Database
def dbx():
	# database engine
	engine				= create_engine('sqlite:///catalog.db')
	Base.metadata.bind	= engine
	dbsession			= sessionmaker(bind = engine)
	return dbsession()

CLINT_ID = json.loads(open('client_secrets.json', 'r').read())[u'client_id']
print CLINT_ID

@app.route('/')
@app.route('/Catagories/')
def hello():
	dbs			= dbx()
	Catagories	= dbs.query(Catagory).all()
	items		= dbs.query(Item).all()
	page		= ["Catalog"]
	out	= render_template('header.html',
							page=page,
							cats=Catagories)
	out += render_template('index.html',
							page=page,
							cats=Catagories,
							items=items)
	out += render_template('footer.html')
	return out

@app.route('/Catagories/<int:cid>/')
def Catagories(cid):
	dbs	= dbx()
	Catagories	= dbs.query(Catagory).all()
	cat			= dbs.query(Catagory).filter_by(id=cid).one()
	items		= dbs.query(Item).filter_by(catagory_id=cat.id).all()
	page 		= ["Catalog", cat.name]
	
	if len(items) == 0:
		items = [{
				'id'			: -1,
				'catagory_id'	: cat.id,
				'name'			: 'No items Found in this Catagory'
			}]

	out = render_template('header.html',
							page=page,
							cats=Catagories)
	out += render_template('index.html',
							page=page,
							items=items)
	out += render_template('footer.html')
	return out

@app.route('/Catagories/<int:cid>/<int:iid>/')
def desc(cid, iid):
	dbs	= dbx()
	Catagories	= dbs.query(Catagory).all()
	cat			= dbs.query(Catagory).filter_by(id=cid).one()
	item		= dbs.query(Item).filter_by(id=iid).one()
	page 		= ["Catalog", cat.name, item.name]
	
	out = render_template('header.html',
							page=page,
							cats=Catagories)
	out += render_template('desc.html',
							page=page,
							item=item)
	out += render_template('footer.html')
	return out

@app.route('/login/', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		# an attempt to cupture logged user data
		if request.args.get('state') != session['state']:
			response = make_response(json.dumb('Invalid state parameter'), 401)
			response.headers['Content-Type'] = 'application/json'
			return response
		code = request.data
		try:
			oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
			oauth_flow.redirect_uri = 'postmessage'
			credentials = oauth_flow.step2_exchange(code)
		except FlowExchangeError:
			response = make_response(json.dumb('Failed to upgrade the authorization code'), 401)
			response.headers['Content-Type'] = 'application/json'
			return response
		access_token = credentials.access_token

		url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
		h = httplib2.Http()
		result = json.loads(h.request(url, 'GET')[1])
		# If there was an error in the access token info, abort.
		if result.get('error') is not None:
			response = make_response(json.dumps(result.get('error')), 500)
			response.headers['Content-Type'] = 'application/json'
			return response

		# Verify that the access token is used for the intended user.
		gplus_id = credentials.id_token['sub']
		if result['user_id'] != gplus_id:
			response = make_response(
				json.dumps("Token's user ID doesn't match given user ID."), 401)
			response.headers['Content-Type'] = 'application/json'
			return response

		# Verify that the access token is valid for this app.
		if result['issued_to'] != CLIENT_ID:
			response = make_response(
				json.dumps("Token's client ID does not match app's."), 401)
			print "Token's client ID does not match app's."
			response.headers['Content-Type'] = 'application/json'
			return response

		stored_access_token = session.get('access_token')
		stored_gplus_id = session.get('gplus_id')
		if stored_access_token is not None and gplus_id == stored_gplus_id:
			response = make_response(json.dumps('Current user is already connected.'),
									 200)
			response.headers['Content-Type'] = 'application/json'
			return response

		# Store the access token in the session for later use.
		session['access_token'] = credentials.access_token
		session['gplus_id'] = gplus_id

		# Get user info
		userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
		params = {'access_token': credentials.access_token, 'alt': 'json'}
		answer = requests.get(userinfo_url, params=params)

		data = answer.json()

		session['username'] = data['name']
		session['picture'] = data['picture']
		session['email'] = data['email']
	else:
		dbs	= dbx()
		Catagories	= dbs.query(Catagory).all()
		state = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in xrange(32) )
		# session['state'] = state
		page 		= ["Login"]
		
		out = render_template('header.html',
								page=page,
								cats=Catagories)
		out += render_template('login.html',
								state=state)
		out += render_template('footer.html')
		return out

@app.route('/logout/')
def logout():
	# an attempt to sign in
	access_token = session.get('access_token')
	if access_token is None:
		print 'Access Token is None'
		response = make_response(json.dumps('Current user not connected.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	print 'In gdisconnect access token is %s', access_token
	print 'User name is: '
	print session['username']
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % session['access_token']
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]
	print 'result is '
	print result
	if result['status'] == '200':
		del session['access_token']
		del session['gplus_id']
		del session['username']
		del session['email']
		del session['picture']
		response = make_response(json.dumps('Successfully disconnected.'), 200)
		response.headers['Content-Type'] = 'application/json'
		return response
	else:
		response = make_response(json.dumps('Failed to revoke token for given user.', 400))
		response.headers['Content-Type'] = 'application/json'
		return response
	logout_user()

@app.route('/Catagories/new/', methods=['GET', 'POST'])
def newCat():
	dbs	= dbx()
	if request.method == 'POST':
		catx = Catagory(name = request.form['c_name'])
		dbs.add(catx)
		dbs.commit()
		return redirect(url_for('hello'))
	else:
		Catagories	= dbs.query(Catagory).all()
		page 		= ["New Catagory"]
		
		out = render_template('header.html',
								page=page,
								cats=Catagories)
		out += render_template('new.html',
								page=page)
		out += render_template('footer.html')
		return out

@app.route('/Catagories/edit/<int:cid>/', methods=['GET', 'POST'])
def editCat(cid):
	dbs	= dbx()
	if request.method == 'POST':
		catx = dbs.query(Catagory).filter_by(id=cid).one()
		catx.name = request.form['c_name']
		dbs.add(catx)
		dbs.commit()
		return redirect(url_for('hello'))
	else:
		Catagories	= dbs.query(Catagory).all()
		page 		= ["Edit Catagory"]
		
		out = render_template('header.html',
								page=page,
								cats=Catagories)
		out += render_template('new.html',
								page=page)
		out += render_template('footer.html')
		return out

@app.route('/Catagories/del/<int:cid>/', methods=['POST'])
def deleteCat(cid):
	dbs	= dbx()
	if request.method == 'POST':
		catx = dbs.query(Catagory).filter_by(id=cid).one()
		dbs.delete(catx)
		dbs.commit()
	return redirect(url_for('hello'))

@app.route('/Catagories/new/<int:cid>/', methods=['GET', 'POST'])
def newItem(cid):
	dbs	= dbx()
	if request.method == 'POST':
		cat = dbs.query(Catagory).filter_by(id=cid).one()
		itemx = Catagory(name		= request.form['c_name'],
						description	= request.form['descripe'],
						catagory	= request.form['catagory'])
		dbs.add(catx)
		dbs.commit()
		return redirect(url_for('hello'))
	else:
		Catagories	= dbs.query(Catagory).all()
		page 		= ["New Item"]
		
		out = render_template('header.html',
								page=page,
								cats=Catagories)
		out += render_template('inew.html',
								page=page,
								cats=Catagories)
		out += render_template('footer.html')
		return out

@app.route('/Catagories/edit/<int:cid>/<int:iid>/', methods=['GET', 'POST'])
def editItem(cid, iid):
	dbs	= dbx()
	if request.method == 'POST':
		cat = dbs.query(Catagory).filter_by(id=request.form['catagory']).one()
		itemx = dbs.query(Item).filter_by(id=iid, catagory_id=cid).one()
		itemx.name			= request.form['c_name']
		itemx.description	= request.form['descripe']
		itemx.catagory		= cat
		dbs.add(itemx)
		dbs.commit()
		return redirect(url_for('hello'))
	else:
		Catagories	= dbs.query(Catagory).all()
		page 		= ["Edit Item"]
		
		out = render_template('header.html',
								page=page,
								cats=Catagories)
		out += render_template('inew.html',
								page=page,
								cats=Catagories)
		out += render_template('footer.html')
		return out

@app.route('/Catagories/del/<int:cid>/<int:iid>/', methods=['POST'])
def deleteitem(cid, iid):
	dbs	= dbx()
	if request.method == 'POST':
		itemx = dbs.query(Item).filter_by(id=iid, catagory_id=cid).one()
		dbs.delete(itemx)
		dbs.commit()
	return redirect(url_for('hello'))


if __name__ == '__main__':
	app.secret_key	= 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=8000)