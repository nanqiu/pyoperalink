========================================
 pyoperalink - Python Opera Link Client
========================================

:Version: 0.1.0

Introduction
------------

This is the Opera Link Public API client library for Python.  It
provides utilities to get and manipulate Opera Link datatypes. All
applications must provide the library with its application key
received from https://auth.opera.com/service/oauth/applications/.  The
library takes care of authorizing the user and giving easy access to
get and modify his Opera Link data.

Requirements
============
oauth2 module http://pypi.python.org/pypi/oauth2/


Installation
============

You can install ``pyoperalink`` either via the Python Package Index (PyPI)
or from source.

To install using ``pip``,::

    $ pip install pyoperalink


To install using ``easy_install``,::

    $ easy_install pyoperalink


If you have downloaded a source you can install it
by doing the following,::

    $ python setup.py build
    # python setup.py install # as root



Interface
=========

To receive data from server following get methods can be invoked on LinkClient
object:

To get a specific item:

get_bookmark(item_id)
get_note(item_id)
get_speeddial(item_id)

Or to get lists of items, either at root level, or for a specific
folder(where applicable):

get_bookmarks(item_id=None)
get_notes(item_id=None)
get_speeddials()

All of the above methods will return instances of the corresponding
Opera Link datatype class.

High level interface operates on instances of Opera Link dataype classes (listed
above in Classes section).

add(item)
add_to_folder(item, destination)
move_into(item, destination)
move_before(item, reference_item)
move_after(item, reference)

Low level interface operates on parameter item_id of element and objects
parameters passed as dictionary. Generally, you wouldn't need to
directly call those methods, use the methods of the client and the
dataype classes as specified above.

List of accepted parameters for every datatype can be found in
documentation for corresponding class.

Methods of LinkClient:
    create_bookmark(item_id, params)
    move_bookmark(item_id, relative_position, reference_item=None)
    delete_bookmark(item_id)
    trash_bookmark(item_id)
    update_bookmark(item_id, params)

    create_note(item_id, params)
    move_note(item_id, , relative_position, reference_item=None)
    delete_note(item_id)
    trash_note(item_id)
    update_note(item_id, params)

    create_speeddial(item_id, params)
    delete_speeddial(item_id)
    update_speeddial(item_id, params)

Except from the delete method, all calls will return server response
as a dictionary of the item's fields and their values.



Authorization
=============
To get access to the user's data OAuth 1.0a protocol based authization method is
preformed. To make it work for your application, it must be registered at
https://auth.opera.com/service/oauth/applications/ where you are going to receive
consumer key and consumer secret. It can be registered either as a Desktop or a
Web application. If you register the latter, then you must specify a callback URL
- the adress where the user and the generated token will be returned
  back into your web application, after autorization is complete.



Examples 
========

>>> import pyoperalink

AUTHORIZATION

Typical workflow to access Opera Link data of a new user:

    # Create a new OAuth handler with consumer key and consumer secret,
    # received when registering the application on. 
    # Pass the callback URL if you're making a web application
    # http://auth.opera.com/service/oauth/applications/
    >>> from pyoperalink.auth import OAuth
    >>> auth = OAuth('consumer_key',
    >>> ....'consumer_secret')

    # Get address to the authorization website where user can grant access to the
    # application, pass callback URL if any. 
    >>> auth.get_authorization_url()
    'https://auth.opera.com/service/oauth/authorize?callback=oob&oauth_token=ATfOL57RDJplURAtmC2VjQcphgsphCnX'

    # Now your application should redirect user on the address above

    # After the user has granted access to the application, complete
    # the autorization, using the verifer code you received.
    # Keep this token, using whatever means you want. You need it
    # every time you want to access the service. 
    >>> token = auth.get_access_token(verifier)


    # To access Opera Link data of a user who has already generated
    # access token:
    >>> auth = OAuth('consumer_key',
    >>> ....'consumer_secret')
    >>> auth.set_access_token("token", "token_secret")

    # Now you can use Opera Link Public API

    >>> from pyoperalink.client import LinkClient
    >>> client = LinkClient(auth)

ACCESSING THE USER DATA

Examples for bookmarks:

    >>> from pyoperalink import datatypes

    # get list of all bookmark elements from the server
    >>> bookmarks = client.get_bookmarks()
    >>> len(bookmarks)
    6
    >>> isinstance(bookmarks[0], Bookmark)
    True
    >>> bookmarks[0].uri
    'http://link.opera.com/'

    # move some element to a trash folder
    >>> bookmarks[-1].trash()

    # check if an element in the list is a folder
    >>> bookmarks[2].is_folder()
    True
    # Fetch the items contained in the folder
    >>> children = bookmarks[2].children
    >>> len(children)
    4

    # Directly fetch the items contained in a specific folder
    >>> children = client.get_bokmarks("4E1601F6F30511DB9CA51FD19A7AAECA")
    >>> len(children)
    4

    # Move one of the bookmarks into a folder
    >>> bookmarks[1].move(bookmarks[2], "into")
    # Or using the client shortcut method
    >>> client.move_into(bookmarks[1], bookmarks[2])

    # Greate a new bookmark and add it to the storage
    >>> sample_bookmark = datatypes.Bookmark(title='sample_title', uri='http://www.opera.com')
    >>> client.add(sample_bookmark)

    # Or add it straight into an existing folder:
    >>> sample_bookmark = datatypes.Bookmark(title='sample_title', uri='http://www.opera.com')
    >>> client.add_to_folder(sample_bookmark, bookmarks[2])

    # Modify bookmark properties
    >>> bookmarks[2].title = 'New folder title'
    # And save the changes to the server
    >>> bookmarks[2].update()


Examples for notes:
    # get list of notes from the server
    >>> notes = client.get_notes()
    >>> len(notes)
    6

    # check if element is a folder
    >>> notes[2].is_folder()
    True
    >>> children = notes[2].children
    >>> len(children)
    1

    # move one of the notes to another folder
    >>> client.move_into(notes[3], notes[2])
    >>> len(client.get_notes(notes[2].id))
    2

    >>> sample_note = datatypes.Note(content='sample note content')
    >>> client.add_to_folder(sample_note, notes[2])
    >>> len(notes[2].children)
    3

Examples for speed dials:
    # get list of speed dials from the server
    >>> dials = client.get_speeddials()
    >>> len(dials)
    8

    # delete one of the speed dials
    >>> dials[1].delete()
    >>> dials = client.get_speeddials()
    >>> len(dials)
    7

    # insert new dial at position 1
    >>> sample_dial = datatypes.SpeedDial(id=1, title='sample note content', uri='http://example.com')
    >>> client.add(sample_dial)
    >>> sample_dial.uri
    'http://example.com'
    >>> sample_dial.position
    1


License
=======

This software is licensed under the ``BSD License``. See the ``LICENSE``
file in the top distribution directory for the full license text.
