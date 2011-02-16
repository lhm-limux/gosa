#!/usr/bin/env python

from sqlalchemy import create_engine
engine = create_engine('sqlite:///test.db', echo=True)

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

Base = declarative_base()
metadata = Base.metadata
class Address(Base):
	__tablename__ = 'addresses'
	id = Column(Integer, primary_key=True)
	email_address = Column(String, nullable=False)
	user_id = Column(Integer, ForeignKey('users.id'))

	def __init__(self, email_address):
		self.email_address = email_address

	def __repr__(self):
		return "<Address('%s')>" % self.email_address

class User(Base):
	__tablename__ = 'users'
	
	id = Column(Integer, primary_key=True)
	username = Column(String)
	fullname = Column(String)
	password = Column(String)
	addresses = relationship(Address, order_by=Address.id, backref=("user"))
	
	def __init__(self, username, fullname, password):
		self.username = username
	        self.fullname = fullname
	        self.password = password
	
	def __repr__(self):
	        return "<User('%s','%s', '%s')>" % (self.username, self.fullname, self.password)

metadata.create_all(engine)
session = Session()
user1 = User('hsenkblei', 'Hubert Senkblei', 'tester123')
user1.addresses = [Address(email_address='user@domain.com')]
session.add(user1)
our_user = session.query(User).filter_by(username='hsenkblei').first()
print our_user, "ID", our_user.id
session.commit()
