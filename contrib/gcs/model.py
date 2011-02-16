# -*- coding: utf-8 -*-
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, \
    Sequence, Text, Boolean, Date, DateTime, Float
from sqlalchemy import create_engine, func
from sqlalchemy.orm import mapper, sessionmaker, relationship, backref, \
    joinedload
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
db_session = None


class UseInnoDB(object):
    __table_args__ = {'mysql_engine': 'InnoDB'}


class PluginInstances(Base, UseInnoDB):
    __tablename__ = 'plugin_instances'

    plugin = Column(Integer, ForeignKey('plugins.id'), primary_key=True)
    instance = Column(Integer, ForeignKey('instances.id'), primary_key=True)


class InstancesUser(Base, UseInnoDB):
    __tablename__ = 'instances_user'

    instance = Column(Integer, ForeignKey('instances.id'), primary_key=True)
    user = Column(Integer, ForeignKey('users.id'), primary_key=True)


class RoleMappings(Base, UseInnoDB):
    __tablename__ = 'role_mappings'

    user = Column(Integer, ForeignKey('users.id'), primary_key=True)
    role = Column(Integer, ForeignKey('roles.id'), primary_key=True)


class Statistics(Base, UseInnoDB):
    __tablename__ = 'statistics'

    id = Column(Integer, Sequence('statistic_id_seq'), primary_key=True)
    instance_id = Column(Integer, ForeignKey('instances.id'), primary_key=True)
    instance = relationship("Instance")

    act_type = Column(String(255))
    plugin = Column(String(255))
    category = Column(String(255))
    action = Column(String(255))
    uuid = Column(String(36))
    date = Column(DateTime)
    duration = Column(Float)
    render_time = Column(Float)
    amount = Column(Integer)
    mem_usage = Column(Integer)
    load = Column(Float)
    info = Column(Text(512))


class Instance(Base, UseInnoDB):
    __tablename__ = 'instances'

    id = Column(Integer, Sequence('instance_id_seq'), primary_key=True)
    uuid = Column(String(36), nullable=False, unique=True)
    password = Column(String(64))
    version = Column(String(64))
    created = Column(Date)
    last_seen = Column(Date)
    active = Column(Boolean)
    description = Column(Text(512))
    certificate = Column(Text(2048))
    test_instance = Column(Boolean)

    plugins = relationship("Plugin", secondary=PluginInstances.__table__)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    contact = relationship("Contact")

    def __repr__(self):
        return "<Instance('%s','%s')>" % (self.uuid, self.description)


class Contact(Base, UseInnoDB):
    __tablename__ = 'contacts'
    id = Column(Integer, Sequence('contact_id_seq'), primary_key=True)
    phone = Column(String(64))
    contact = Column(String(512))
    contact_mail = Column(String(512))
    company = Column(String(512))
    street = Column(String(512))
    postal_code = Column(String(512))
    city = Column(String(512))
    trade = Column(String(512))
    employees = Column(Integer)
    clients = Column(Integer)
    knownFrom=Column(String(512))
    sector=Column(String(512))

    description = Column(Text)

    def __repr__(self):
        return "<Contact('%s')>" % self.description


class User(Base, UseInnoDB):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    mail = Column(String(255), nullable=False)
    lang = Column(String(16), nullable=False)
    surname = Column(String(512), nullable=False)
    givenname = Column(String(512), nullable=False)
    uid = Column(String(512), nullable=False, unique=True)
    password = Column(String(512), nullable=False)
    restore_question = Column(String(512), nullable=False)
    restore_answer = Column(String(512), nullable=False)
    newsletter = Column(Boolean)
    active = Column(Boolean, default=False)

    instances = relationship("Instance", secondary=InstancesUser.__table__)
    roles = relationship("Role", secondary=RoleMappings.__table__)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    contact = relationship("Contact")

    def __repr__(self):
        return "<User('%s', '%s', '%s')>" % (self.mail,
            self.surname, self.givenname)

class Activation(Base, UseInnoDB):
    __tablename__ = 'activation'
    id = Column(Integer, Sequence('activation_id_seq'), primary_key=True)
    activation_code = Column(String(64), nullable=False)
    datetime = Column(DateTime, nullable=False, default=func.now())

    user_id = Column(Integer, ForeignKey('users.id')) 
    user = relationship("User")


class Plugin(Base, UseInnoDB):
    __tablename__ = 'plugins'
    id = Column(Integer, Sequence('plugin_id_seq'), primary_key=True)
    name = Column(String(64), nullable=False)
    version = Column(String(64))

    def __repr__(self):
        return "<Plugin('%s', '%s')>" % (self.name, self.version)


class Role(Base, UseInnoDB):
    __tablename__ = 'roles'
    id = Column(Integer, Sequence('role_id_seq'), primary_key=True)
    name = Column(String(64), nullable=False, unique=True)
    description = Column(Text(512))

    def __repr__(self):
        return "<Role('%s')>" % self.name


def get_session():
    #global db_session

    #if not db_session:
    engine = create_engine('mysql://root:tester@localhost/gcs', echo=False)
    metadata = Base.metadata
    metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    db_session = Session()

    return db_session
