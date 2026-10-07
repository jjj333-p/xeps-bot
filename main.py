"""
A small little slixmpp bot to name mentioned XEPs and link to them.
Copyright (C) 2026 Joseph Winkie

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import asyncio
import json
import xml.etree.ElementTree as ET
import re
import logging
import subprocess
from collections.abc import Iterable

import aiohttp
import slixmpp
from slixmpp.types import PresenceArgs

XEP_PATTERN = re.compile(r'(?i)\bxep[- ]?(\d+)')

xeps_by_number: dict[int, ET.Element] = {}
xeps_by_title: dict[str, ET.Element] = {}

# lazy man's method to preventing port exhaustion
# they could still dos the bot but whatever
fetch_lock = asyncio.Lock()

async def fetch_xeps():
    async with fetch_lock:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://xmpp.org/extensions/xeplist.xml") as resp:
                xeplisttxt = await resp.text()
                xeplistxml = ET.fromstring(xeplisttxt)

                for xep in xeplistxml.findall("xep"):
                    number = xep.findtext("number")
                    title = xep.findtext("title")
                    short_name = xep.findtext("shortname")

                    if number is None or title is None:
                        continue

                    if number.isdigit():
                        xeps_by_number[int(number)] = xep

                    xeps_by_title[title] = xep
                    if short_name is not None:
                        xeps_by_title[short_name] = xep

def create_preview_txt(xep : ET.Element):
    # traverse xml
    number = int(xep.findtext("number") or "-1")
    title = xep.findtext("title")
    status = xep.findtext("status")
    last_rev = xep.find("last-revision")
    last_rev_date = last_rev.findtext("date") if last_rev is not None else None
    last_rev_version = last_rev.findtext("version") if last_rev is not None else None
    supersededby_el = xep.find("supersededby")
    supersededby_list = supersededby_el.findall("spec") if supersededby_el is not None else None

    # form nice text
    out = f"XEP-{number:04d}: *{title}* ({status}, last revised {last_rev_date}, v{last_rev_version}) https://xmpp.org/extensions/xep-{number:04d}.html"
    if supersededby_list is not None:
        out += f"superseded by {', '.join(spec.text or "?" for spec in supersededby_list)}"

    return out

def create_with_abstract(xep : ET.Element):
    out = create_preview_txt(xep)
    abstract = xep.findtext("abstract")
    if abstract:
        return f"{out}\n> {'\n> '.join(abstract.split("\n"))}"
    else:
        return out

def get_git_info() -> tuple[str, str]:
    """
    Attempts to fetch the current Git version and remote origin URL.
    Returns (version, url) with safe fallbacks if Git is unavailable.
    """
    version = "unknown version"
    url = "tbd"

    try:
        version = subprocess.check_output(
            ["git", "describe", "--tags", "--always", "--dirty"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()

        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()

        # Optional: If you want to convert SSH URLs (git@...) to HTTPS for clickability
        if url.startswith("git@"):
            url = url.replace(":", "/").replace("git@", "https://")

    except Exception:
        # Fails silently if git is not installed or it's not a git repository
        pass

    return version, url

git_version, repo_url = get_git_info()

status_msg = f"XEPsBot v{git_version} | Source: {repo_url}"

def remove_fallbacks(body: str, fallbacks: Iterable[str]) -> str:
    # get out fallback ranges for features we support
    ranges_to_remove = []
    for fallback in fallbacks:
        if fallback["for"] == "urn:xmpp:reply:0":
            start = int(fallback["body"]["start"])
            end = int(fallback["body"]["end"])
            ranges_to_remove.append((start, end))
    # Remove in reverse order so indices stay valid
    ranges_to_remove.sort(reverse=True)
    result = list(body)
    for start, end in ranges_to_remove:
        if end > len(result):
            continue
        if start < 0:
            continue
        del result[start:end]

    return "".join(result).strip()

with open("./login.json", encoding="utf-8") as lf:
    login = json.load(lf)

class MUCBot(slixmpp.ClientXMPP):

    def __init__(self, jid, password, rooms, nick):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        self.rooms = rooms
        self.nick = nick

        self.add_event_handler("session_start", self.start)

        # The groupchat_message event is triggered whenever a message
        # stanza is received from any chat room. If you also also
        # register a handler for the 'message' event, MUC messages
        # will be processed by both handlers.
        self.add_event_handler("message", self.message)

        self.add_event_handler("groupchat_direct_invite", self.invite)

        self.register_plugin('xep_0045')  # Multi-User Chat
        self.register_plugin('xep_0199')  # XMPP Ping
        self.register_plugin('xep_0461')  # Message Replies
        self.register_plugin('xep_0249')  # muc invites

    async def start(self, _):
        await self.get_roster()
        self.send_presence()

        # join configured rooms
        for room in self.rooms:
            await self.plugin['xep_0045'].join_muc_wait(
                room,
                self.nick,
                presence_options=PresenceArgs(
                    pstatus=status_msg
                ),
                maxchars=0,
            )

        while True:
            await asyncio.sleep(86_400)
            await fetch_xeps()

    async def invite(self, msg):
        """
                Handler triggered when a Direct MUC Invite (XEP-0249) is received.
                The plugin parses the XML and exposes it through message['xep_0249'].
                """
        # Extract the invite payload
        invite = msg['groupchat_invite']

        # The plugin gives you clean access to the underlying attributes
        room_jid = invite['jid']
        room_password = invite['password']
        # unsupported for now
        if room_password:
            return
        reason = invite['reason']

        sender = msg['from']
        print(f"Received a direct invite to {room_jid} from {sender}")

        if reason:
            print(f"Reason: {reason}")

        # Optional: Join the room immediately using XEP-0045
        try:
            await self.plugin['xep_0045'].join_muc_wait(
                room_jid,
                self.boundjid.user,  # Use your JID's user part as the nickname
                presence_options=PresenceArgs(
                    pstatus=status_msg
                ),
            )
            print(f"Successfully joined {room_jid}")
        except Exception as e:
            print(f"Failed to join {room_jid}: {e}")
            return


        # Add room to login.json and save
        try:
            with open("./login.json", "r", encoding="utf-8") as lf:
                login_data = json.load(lf)

            if room_jid not in login_data.get("rooms", []):
                login_data.setdefault("rooms", []).append(room_jid)
                self.rooms.append(room_jid)

                with open("./login.json", "w", encoding="utf-8") as lf:
                    json.dump(login_data, lf, indent=2, ensure_ascii=False)

                print(f"Added {room_jid} to login.json")
        except Exception as e:
            print(f"Failed to update login.json: {e}")

        self.send_message(
                mto=room_jid,
                mbody=f"Joined muc as I was invited by `{sender}` with reason `{reason}` .",
                mtype="groupchat"
            )

    async def message(self, msg):
        # dont respond to self
        if msg['mucnick'] == self.nick:
            return

        cleaned_body = remove_fallbacks(
                msg['body'],
                msg['fallbacks']
        )

        if cleaned_body.startswith("!refresh"):
            await fetch_xeps()
            self.send_message(
                mto=msg['from'].bare,
                mbody=f"Index has been refreshed, {msg['from'].resource}",
                mtype=msg['type']
            )
        elif cleaned_body.startswith("!xep"):
            xep_query = cleaned_body[4:].strip()

            if xep_query.isdigit():
                xep_num = int(xep_query)

                xep = xeps_by_number.get(int(xep_num))

            else:
                xep = xeps_by_title.get(xep_query)

            if xep is None:
                print("unknown xep", xep_query)
                preview_txt = f"Unknown xep {xep_query}"
            else:
                preview_txt = create_with_abstract(xep)

            self.send_message(
                mto=msg['from'].bare,
                mbody=preview_txt,
                mtype=msg['type']
            )
        else:
            xep_nums = XEP_PATTERN.findall(cleaned_body)

            for xep_num in xep_nums:
                xep = xeps_by_number.get(int(xep_num))

                if xep is None:
                    print("unknown xep", xep_num)
                    continue

                preview_txt = create_preview_txt(xep)

                self.send_message(
                    mto=msg['from'].bare,
                    mbody=preview_txt,
                    mtype=msg['type']
                )


if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')

    asyncio.run(fetch_xeps())

    xmpp = MUCBot(login["jid"], login["password"],
                  login["rooms"], login["displayname"])

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect()
    print("Connected and running forever...")
    asyncio.get_event_loop().run_forever()