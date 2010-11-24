from __future__ import absolute_import

from urllib import urlencode

import oauth2 as oauth

from pyoperalink.datatypes import registry

try:
    import json as simplejson
except ImportError:
    import simplejson

TREE_STRUCTURED_DATATYPES = [("bookmark", "BookmarkFolderEntry"),
                             ("note", "NoteFolderEntry")]
LIST_STRUCTURED_DATATYPES = [("speeddial", "SpeedDial"),
                             ("search_engine", "SearchEngine")]

# Opera Link Server address
OPERA_LINK_URL = "https://link.api.opera.com/rest"


class LinkError(Exception):
    """
    Link exception with status_code
    Thrown when communication with server fails
    """
    status_code = None
    reason = None

    def __init__(self, status_code=None, reason=None, content=None):
        self.status_code = status_code or self.status_code
        self.reason = reason or self.reason
        self.content = content
        Exception.__init__(self, self.status_code, self.reason, self.content)

    def __repr__(self):
        return "<%s: %s %s>" % (self.__class__.__name__,
                                self.status_code,
                                self.reason)


class BadRequestError(LinkError):
    """
    API data request lacks some obligatory or parameters are not valid
    """
    status_code = 400
    reason = "Bad request"


class NotFoundError(LinkError):
    """
    Item does not exist on the server
    """
    status_code = 404
    reason = "Not found"


class AccessDeniedError(LinkError):
    """
    Authentication failed
    """
    status_code = 401
    reason = "Unauthorized access"


class DatatypeMaster(type):
    """
    Metaclass which defines the behaviour of LinkClient.

    Generates some of the high-level API calls and associated metods
    for communicating with the Opera Link server.

    It uses the registered datatypes from datatypes.py
    """

    get_docstring = """
    Fetches an item of dataype %s from the server, provided an unique ID.
    """

    get_children_docstring = """
    Gets a list of items from datatype %s from the server, provided a folder ID.
    If item_id=None then all root-level items will be fetched.
    """

    update_docstring = """
    Saves local changes to the %s item"s fields to the server.
    Returns a dict with all the item"s fields and values, as saved on
    the server.
    """

    create_docstring = """
    Creates a new item of %(datatype)s.

    If item_id=None then the new item is appended at the end of the
    root folder.  If item_id is provided then the new item will be
    appended at the end of the folder, corresponding to that ID.

    Created object is of type deriving from %(class)s depending on
    "item_type" parameter passed.
    """

    delete_docstring = """
    Deletes an item of datatype %s from the server, given a unique ID
    """

    trash_docstring = """
    Moves and item of datatype %s on the server, directly to the trash folder
    """

    move_docstring = """
    Moves an item of datatype %s with unique ID "item_id" to a position relative
    to "reference_item".

    The position is determined by the value of
    "reference_position" - one of: ("before", "after", "into"}
    """

    def __new__(cls, name, bases, attrs):
        """
        This is where all datatype-dependant methods of the LinkClient
        class will be defined.
        """
        super_new = super(DatatypeMaster, cls).__new__

        # Add methods specific for tree structures
        for datatype, element_class in TREE_STRUCTURED_DATATYPES:

            trash_method = cls.gen_delete_datatype(datatype, "trash")
            trash_method.__doc__ = cls.trash_docstring % datatype
            attrs["%s_%s" % ("trash", datatype)] = trash_method

            move_method = cls.gen_move_datatype(datatype)
            move_method.__doc__ = cls.move_docstring % datatype
            attrs["%s_%s" % ("move", datatype)] = move_method

        # Add methods common for all datatype elements
        for datatype, element_class in (TREE_STRUCTURED_DATATYPES + 
                                        LIST_STRUCTURED_DATATYPES):
            # method to get list of items
            method = cls.gen_elements_getter(datatype,
                    ((datatype, element_class) in TREE_STRUCTURED_DATATYPES))
            method.__doc__ = cls.get_children_docstring % datatype
            attrs["get_%ss" % datatype] = method

            # method to get details of the item
            method = cls.gen_get_datatype(datatype)
            method.__doc__ = cls.get_docstring % datatype
            attrs["get_%s" % datatype] = method

            # method to delete an item
            method = cls.gen_delete_datatype(datatype, "delete")
            method.__doc__ = cls.delete_docstring % datatype
            attrs["delete_%s" % datatype] = method

            # method to create an item
            method = cls.gen_change_datatype(datatype, "create")
            method.__doc__ = cls.create_docstring % {
                                        "datatype": datatype,
                                        "class": element_class}
            attrs["create_%s" % datatype] = method

            # method to update an item
            method = cls.gen_change_datatype(datatype, "update")
            method.__doc__ = cls.update_docstring % datatype
            attrs["update_%s" % datatype] = method

        return super_new(cls, name, bases, attrs)

    @classmethod
    def gen_elements_getter(cls, datatype, tree_structure):
        """
        Closure generating general method to get
        list or tree of elements from server
        """
        def datatype_tree_getter(instance, item_id=None):
            return instance._get_resource_children(datatype, item_id,
                                                   tree_structure)
        def datatype_list_getter(instance):
            return instance._get_resource_children(datatype, None,
                                                   tree_structure)
        if tree_structure:
            return datatype_tree_getter
        return datatype_list_getter

    @classmethod
    def gen_get_datatype(cls, datatype):
        """
        Closure generating general method to get
        from server details of one element
        """
        def datatype_getter(instance, item_id):
            return instance._get_resource(datatype, False, item_id)
        return datatype_getter

    @classmethod
    def gen_change_datatype(cls, datatype, api_method):
        """
        Closure generating general method to change
        at server side details of element
        """
        def datatype_changer(instance, item_id, params):
            return instance._change_resource(datatype, api_method,
                                             params, item_id)
        return datatype_changer

    @classmethod
    def gen_move_datatype(cls, datatype):
        """
        Closure generating method to move an element at the server
        """
        def datatype_move(instance, item_id, relative_position,
                          reference_item=None):

            if reference_item is None:
                reference_item = ""
            return instance._change_resource(datatype, "move",
                    {"reference_item": reference_item,
                     "relative_position": relative_position},
                    item_id)
        return datatype_move

    @classmethod
    def gen_delete_datatype(cls, datatype, api_method):
        """
        Closure generating method to  an element at the server
        """
        def datatype_delete(instance, item_id):
            return instance._change_resource(datatype, api_method, {}, item_id)
        return datatype_delete


class LinkClient(object):
    """
    Opera Link API client.

    This class handles all communication with the Opera Link server and provides
    high-level methods for accessing and manipulating Opera Link data.
    """

    __metaclass__ = DatatypeMaster

    def __init__(self, auth_handler=None, url_prefix=OPERA_LINK_URL):
        """
        auth_handler must be an auth.OAuth object, with a set access token.

        url_prefix defaults to the Opera Link API server address.
        It can be changed for testing purposes.
        """
        if auth_handler is not None:
            self.conn = oauth.Client(auth_handler._consumer,
                                     auth_handler.access_token)
        self.url_prefix = url_prefix

    def _build_query(self, api_method=None, **kwargs):
        query = dict(kwargs, api_output="json")
        if api_method:
          query["api_method"] = api_method
        return query

    def _get_url_suffix(self, datatype, item_id):
        """
        Returns the second part of the URL for a given datatype and item.

        The Opera Link URLs look have this form:
        <self.url>/<datatype>/<item_id>/
        """
        url = "%s/%s/" % (self.url_prefix, datatype)
        if item_id:
            url += "%s/" % str(item_id)
        return url

    def _get_resource_children(self, datatype, item_id,
            create_tree_structure):
        url_suffix = self._get_url_suffix(datatype, item_id)
        resource_location = "%s%s?%s" % (url_suffix, "children",
                                         urlencode(self._build_query()))
        json_list = self._get_request(resource_location)
        if not json_list:
            return []

        if create_tree_structure:
            children = []
            for data in json_list:
                item_type = data.pop("item_type")
                item_id = data.pop("id")
                new_item = registry[item_type](self, item_id,
                                               **data["properties"])
                children.append(new_item)
            return children
        else:
            l = []
            for data in json_list:
                item_type = data.pop("item_type")
                item_id = data.pop("id")
                new_child = registry[item_type](self,item_id,
                                                **data["properties"])
                l.append(new_child)
            return l

    def _get_resource(self, datatype, recursive, item_id):
        resource_location = self._get_url_suffix(datatype, item_id)
        resource_location += "?" + urlencode(self._build_query())
        data = self._get_request(resource_location)[0]
        item_type = data.pop("item_type")
        item_id = data.pop("id")
        new_item = registry[item_type](self, item_id, **data["properties"])
        return new_item

    def _change_resource(self, datatype, api_method, params, item_id=None):
        resource_location = self._get_url_suffix(datatype, item_id)
        data = self._build_query(api_method)
        data.update(params)
        return self._post_request(resource_location, data)

    @property
    def _http_headers(self):
        return {
            "Content-type": "application/x-www-form-urlencoded",
        }

    def _urlencode(self, data):
        return urlencode(dict((key, value.encode("utf-8"))
                            for key, value in data.iteritems()
                                if isinstance(value, basestring)))

    def _post_request(self, url, data):
        """
        Sends data manipulation requests to the server
        """
        # Encode all fields that have a value and send them to the server
        try:
            resp, content = self.conn.request(url, method="POST",
                                              body=self._urlencode(data),
                                              headers=self._http_headers)
        except Exception, ex:
            raise LinkError(503, "SERVICE UNAVAILABLE", ex)

        if resp.status not in [200, 204]:
            self._raise_link_exception(resp.status, resp.reason, content)

        # Link API requests return lists of items,
        # with the exception of the delete method.
        if not content:
            return

        return simplejson.loads(content)

    def _get_request(self, url):
        """
        Sends data access requests to the server
        """
        try:
            resp, content = self.conn.request(url, method="GET",
                                              headers=self._http_headers)
        except Exception, ex:
            raise LinkError(503, "SERVICE UNAVAILABLE", ex)

        api_status = resp.status
        if api_status != 200:
            self._raise_link_exception(resp.status, resp.reason, content)

        if not content:
            return
        return simplejson.loads(content)

    def _raise_link_exception(self, status, reason, content):
        if status == 400:
            raise BadRequestError()
        elif status == 401:
            raise AccessDeniedError()
        elif status == 404:
            raise NotFoundError()
        else:
            raise LinkError(status, reason, content)

    """ High level API methods """

    def add(self, element):
        """
        Adds newly created elements to Opera Link. For tree-structured datatypes,
        the item will be appended at the end of the root folder.
        """
        if element._conn != self:
            element._conn = self
            element._add()

    def add_to_folder(self, element, destination):
        """
        Adds newly created elements to Opera Link, appended at the end
        of to the spedified destination folder.
        """
        if element._conn != self:
            element._conn = self
            element._add(destination.id)

    def move_into(self, element, destination=None):
       """
       Relocates the item in the tree, appendig it at the end of destination.
       destination must be a folder item. If None, it imples the root folder.
       """
       element.move(destination, "into")

    def move_before(self, element, reference_item):
       """
       Relocates the item in the tree, placing it after reference_item.
       """
       element.move(reference_item, "before")

    def move_after(self, element, reference_item):
        """
        Relocates the item in the tree, placing it after reference_item.
        """
        element.move(reference_item, "after")
