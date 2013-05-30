# -*- coding: utf-8 -*-

import os
import hashlib
import uuid

from sqlalchemy import Column
from sqlalchemy import Unicode
from sqlalchemy import Enum
from sqlalchemy import String
from sqlalchemy.orm import validates

try:
    algorithms = hashlib.algorithms
except AttributeError:
    # Simple tuple for Python 2.6
    algorithms = ('md5', 'sha1')


class PasswordMixin(object):

    '''
        Authentication field definition along with appropriate methods
    '''

    #: password field
    password = Column(Unicode(40), nullable=False)

    #: hash_algorithm field
    _hash_algorithm = Column('hash_algorithm',
                             Enum(*hashlib.algorithms, name="hash_algorithms_enum"),
                             default=u'sha1', nullable=False)

    #: salt field
    _salt = Column('salt', Unicode(50), nullable=False)

    #: reset key field
    reset_key = Column(String(255), unique=True)

    def check_password(self, password):
        '''
            Checks to see whether passwords are the same

            :param str password: password to compare
            :returns: True, if password is same, False if not
            :rtype: bool
        '''
        if password and self.hash_password(password, self._salt, self._hash_algorithm.encode('utf-8')) == self.password:
                return True

        return False

    def set_reset(self):
        '''
            Generates password reset key
        '''
        self.reset_key = str(uuid.uuid4())

    @classmethod
    def hash_password(cls, password, salt, hash_method):
        '''
            Produces hash out of a password

            :param str password: password string, not hashed
            :param str salt: salt
            :param callable hash_method: a hash method which will be used to generate hash
            :returns: hashed password
            :rtype: str
        '''

        # let's allow passing just method name

        if not callable(hash_method):
            hash_method = getattr(hashlib, hash_method)

        # let's convert password to string from unicode
        if isinstance(password, unicode):
            password = password.encode('utf-8')

        # generating salted hash
        return hash_method(password + salt).hexdigest()

    @validates('password')
    def password_validator(self, key, password):
        '''
            Password validator keeps new password hashed.
            Rises Value error on empty password

            :param User user: object instance that triggered event
            :param str password: new password
            :param str oldvalue: old password value
            :param initiatior: the attribute implementation object which initiated this event.
            :returns: hashed and salted password
            :rtype: str

            .. note::

                If you using this Mixin on your own User object, don't forget to add a listener as well, like that:

                .. code-block:: python

                    from sqlalchemy.event import listen

                    listen(User.password, 'set', User.password_listener, retval=True)

            .. note::

                For more information on Attribute Events in sqlalchemy see:

                http://docs.sqlalchemy.org/en/rel_0_7/orm/events.html#sqlalchemy.orm.events.AttributeEvents.set

        '''

        if not password:
            raise ValueError('Password cannot be empty')

        # reading default hash_algorithm
        hash_algorithm = self.__class__._hash_algorithm.property.columns[0].default.arg

        # getting currently used hash method
        hash_method = getattr(hashlib, hash_algorithm)

        # generating salt
        salt = hash_method()
        salt.update(os.urandom(60))
        salt_value = salt.hexdigest()

        # storing used hash algorithm
        self._hash_algorithm = hash_algorithm
        self._salt = unicode(salt_value)
        return unicode(self.__class__.hash_password(password, salt_value, hash_method))