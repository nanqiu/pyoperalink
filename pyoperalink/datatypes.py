import datetime

rfc3339_format = "%Y-%m-%dT%H:%M:%SZ"


def datetime_from_rfc3339(date_string):
    if isinstance(date_string, basestring):
        try:
            return datetime.datetime.strptime(date_string, rfc3339_format)
        except ValueError:
            pass


def datetime_to_rfc3339(date):
    if date:
        return date.strftime(rfc3339_format)


class LinkEntry(object):
    """
    Abstract, base class for objects of all datatypes stored at server
    """

    def __init__(self, conn=None, id=None, **kwargs):
        """
        Initializes Link datatype instances,
        populating their fields from kwargs.

        "conn" and "id" are used internally and are
        not required for creating new items.
        """

        self._conn = conn

        # Initialize all fields of the object
        for field in self.fields:
            if not hasattr(self, field):
                setattr(self, field, None)
        self.id = id
        self._set_fields(kwargs)

    def _to_python(self):
        """
        Returns dict representing object fields
        """
        return dict((key, val)
                        for key, val in vars(self).iteritems()
                            if key in self.fields and val is not None)


    def _set_fields(self, params):
        """
        Set the object"s fields using passed params dictionary
        """
        for key in params:
            if key in self.fields:
                setattr(self, key, params[key])

    def delete(self):
        """
        Invoke method for element deletion from the server
        """
        method = getattr(self._conn, "delete_%s" % self.datatype)
        method(self.id)

    def update(self):
        """
        Sends the item to the Opera Link server.
        If there are any concurrent changes on the server, it"ll update too
        """
        method = getattr(self._conn, "update_%s" % self.datatype)
        resp = method(self.id, self._to_python())

        self._set_fields(resp[0]["properties"])

    def _add(self, parent_id=None):
        """
        Adds a new item to the Opera Link storage.
        If parent_id is provided, it'll attempt to create it inside that folder.
        Otherwise, the item will be appended to the root folder.
        """
        method = getattr(self._conn, "create_%s" % self.datatype)
        params = self._to_python()
        params["item_type"] = self.item_type
        resp = method(parent_id, params)

        self.id = resp[0]["id"]
        self._set_fields(resp[0]["properties"])

    def __str__(self):
        fields = "\n".join("%s:%s" % (field, value.encode("utf-8"))
                    for field, value in self._to_python().iteritems()
                        if value is not None)
        return "%s\n%s" % (self.__class__.__name__, fields)


class TreeEntry(LinkEntry):
    """
    Abstract class for all elements that are folder content
    """

    @property
    def is_folder(self):
        return False

    def trash(self):
        method = getattr(self._conn, "trash_%s" % self.datatype)
        method(item_id=self.id)

    def move(self, reference_item, relative_position):
        """
        Moves the item to location relative to the reference_item;
        relative_position can have one of 3 values: into, before, after;
        conn is LinkClient object
        """
        method = getattr(self._conn, "move_%s" % self.datatype)
        if reference_item:
            resp = method(self.id, relative_position, reference_item.id)
        else:
            resp = method(self.id, {"reference_item": ""})

        self._set_fields(resp[0]["properties"])

    def get_trash_folder(self):
        root = self.get_root_folder()
        if root:
            return root.trash_folder


class BookmarkEntry(TreeEntry):
    """ Common class for elements that can be inside Opera bookmarks """
    datatype = "bookmark"

    def __init__(self, *args, **kwargs):
        super(BookmarkEntry, self).__init__(*args, **kwargs)


class BookmarkFolder(BookmarkEntry):
    fields = ("title", "nickname", "description",
              "type", "target")
    item_type = "bookmark_folder"

    @property
    def is_folder(self):
        return True

    @property
    def children(self):
        if not self._conn:
            raise ValueError("Cannot fetch children for locally created items")
        return self._conn._get_resource_children(self.datatype, self.id, False)


class BookmarkSeparator(BookmarkEntry):
    fields = ()
    item_type = "bookmark_separator"


class Bookmark(BookmarkEntry):
    fields = ("title", "nickname", "description", "uri",
              "icon", "created", "visited");
    item_type = "bookmark"

    def __init__(self, *args, **kwargs):
        super(Bookmark, self).__init__(*args, **kwargs)
        self.created = datetime_from_rfc3339(self.created)
        self.visited = datetime_from_rfc3339(self.visited)

    def update(self):
        super(Bookmark, self).update()
        self.created = datetime_from_rfc3339(self.created)
        self.visited = datetime_from_rfc3339(self.visited)

    def _add(self, item_id=None):
        super(Bookmark, self)._add(item_id)
        self.created = datetime_from_rfc3339(self.created)
        self.visited = datetime_from_rfc3339(self.visited)

    def _to_python(self):
        d = super(Bookmark, self)._to_python()
        d["created"] = datetime_to_rfc3339(self.created)
        d["visited"] = datetime_to_rfc3339(self.visited)
        return d


class NoteEntry(TreeEntry):
    datatype = "note"


class NoteFolder(NoteEntry):
    fields = ("title", "type", "target")
    item_type = "note_folder"

    @property
    def is_folder(self):
        return True

    @property
    def children(self):
        if not self._conn:
            raise ValueError("Cannot fetch children for locally created items")
        return self._conn._get_resource_children(self.datatype, self.id, False)


class NoteSeparator(NoteEntry):
    fields = ()
    item_type = "note_separator"


class Note(NoteEntry):
    item_type = "note"
    fields = ("content", "created", "uri");

    def __init__(self, *args, **kwargs):
        super(Note, self).__init__(*args, **kwargs)
        self.created = datetime_from_rfc3339(self.created)

    def _to_python(self):
        d = super(Note, self)._to_python()
        d["created"] = datetime_to_rfc3339(self.created)
        return d

    def _add(self, item_id=None):
        super(Note, self)._add(item_id)
        self.created = datetime_from_rfc3339(self.created)

    def update(self):
        super(Note, self).update()
        self.created = datetime_from_rfc3339(self.created)


class SpeedDial(LinkEntry):
    fields = ("title", "uri", "icon", "thumbnail")
    datatype = "speeddial"
    item_type = "speeddial"

    def __init__(self, *args, **kwargs):
        super(SpeedDial, self).__init__(*args, **kwargs)
        self.position = None
        if self.id is not None:
            self.position = int(self.id)

    def _add(self):
        super(SpeedDial,self)._add(self.position)

class SearchEngine(LinkEntry):
    fields = ("title", "uri", "encoding", "is_post",
              "key", "post_query", "icon")
    datatype = "search_engine"
    item_type = "search_engine"


registry = {
    "bookmark": Bookmark,
    "bookmark_folder": BookmarkFolder,
    "bookmark_separator": BookmarkSeparator,
    "note": Note,
    "note_folder": NoteFolder,
    "note_separator": NoteSeparator,
    "speeddial": SpeedDial,
    "search_engine": SearchEngine,
}
