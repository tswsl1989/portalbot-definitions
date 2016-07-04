###
# Copyright (c) 2013, Thomas Lake
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import sqlite3
import datetime

class DefinitionError(Exception):
    pass

class Definitions(callbacks.Plugin):
    """This plugin allows users to provide definitions for words, abbreviations
    and phrases, which the bot will then repeat on demand. Definitions can be
    added using the 'define' command, and checked using the 'meanings' command.
    More help is probably available via the bot's owner."""

    def __init__(self, irc):
        self.__parent = super(Definitions, self)
        self.__parent.__init__(irc)
        self._db = self.registryValue("database")
        self._delimiter = self.registryValue("delimiter")
        #self.definitions = {"test": "This was a static test definition", "foo": "bar", "quux": "baz"}
        try:
            self._conn = sqlite3.connect(self._db)

        except Exception as E:
            raise DefinitionError("Is fire!: %s" % E)

        self._cur = self._conn.cursor()
        self._cur.execute("SELECT name FROM sqlite_master WHERE type='table' and name='definitions'")
        if self._cur.fetchone() is None:
            self._cur.execute("CREATE TABLE definitions (term, meaning, addedby, updated)")
            self._cur.execute("INSERT INTO definitions VALUES (:term, :meaning, :addedby, :updated);",
            {"term": "Test", "meaning": "Database test item", "addedby": "System", "updated": datetime.datetime.now()})
            self._conn.commit()

    def meanings(self, irc, msg, args, term):
        """<term>

        List any and all definitions for the term $term.
        """
        self._cur.execute("SELECT rowid, term, meaning FROM definitions WHERE term LIKE :term",
                {"term": term})
        results = self._cur.fetchall()
        if len(results) and len(results) <= 3:
            for i in results:
                irc.reply("[%s] %s: %s" % (hex(i[0])[2:], i[1], i[2]))
        elif len(results) and len(results) > 3:
            irc.reply("There are %d meanings for %s. The first one is:" %
                    (len(results), term))
            irc.reply("Message me 'ids %s' to get the IDs for other definitions" % term)
            i = results[0]
            irc.reply("[%s] %s: %s" % (hex(i[0])[2:], i[1], i[2]))
        else:
            irc.reply("No definitions found for %s" % term)

    m = wrap(meanings, [rest('something')])
    whatis = wrap(meanings, [rest('something')])
    meanings = wrap(meanings, [rest('something')])

    def ids(self, irc, msg, args, term):
        """<term>

        List definition IDs for term
        """
        self._cur.execute("SELECT rowid, term, meaning FROM definitions WHERE term LIKE :term",
                {"term": term})
        results = self._cur.fetchall()
        if results and len(results) >= 1:
            irc.reply("There are %d definitions for %s, with the following IDs:" % (len(results), term))
            irc.reply("Use 'detail id' to get details for each one.")
            idlist = ",".join([hex(r[0])[2:] for r in results])
            irc.reply(idlist)
        else:
            irc.reply("I wasn't able to find any definitions for '%s'" % term)

    ids = wrap(ids, [rest('something')])

    def detail(self, irc, msg, args, defID):
        """<definition ID>

        Return information about a definition. IDs are given in square brackets
        at the start of the output from meanings
        """
        defIDstr = defID
        try:
            defID=int(defID, 16)
        except ValueError as e:
            irc.reply("'%s' is not a valid definition ID" % defIDstr)
            return

        self._cur.execute("SELECT rowid, term, meaning, addedby, updated FROM definitions WHERE rowid=:id", {"id": defID})

        res = self._cur.fetchone()
        if res is None:
            irc.reply("No match found for ID %s" % defID)
        else:
            irc.reply("[%s] %s: %s (added by %s on %s)" % (hex(defID)[2:], res[1],
                res[2], res[3], res[4]))

    detail = wrap(detail, ['somethingWithoutSpaces'])

    def delete(self, irc, msg, args, defID):
        """<definition ID>

        Delete definition from database
        """
        defIDstr = defID
        try:
            defID=int(defID, 16)
        except ValueError as e:
            irc.reply("'%s' is not a valid definition ID" % defIDstr)
            return False

        if self._cur.execute("DELETE FROM definitions WHERE rowid=:id", {"id":
            defID}).rowcount == 1:
            try:
                self._conn.commit()
            except Exception as e:
                irc.replyError()
                return False

            irc.replySuccess()
        else:
            irc.replyError()


    forget = wrap(delete, ['somethingWithoutSpaces'])
    delete = wrap(delete, ['somethingWithoutSpaces'])

    def define(self, irc, msg, args, term, meaning):
        """<term> <meaning>

        Add a definition to the database
        """
        user=irc.msg.nick
        self._conn.execute("INSERT INTO definitions VALUES (:term, :meaning, :user, :dt)",
                {"term": term, "meaning": meaning, "user": user, "dt": datetime.datetime.now()})
        irc.replySuccess()
        self._conn.commit()

    define = wrap(define, ['something', rest('something')])
Class = Definitions


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
