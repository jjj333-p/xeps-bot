# XEPs Bot

A small little [slixmpp](https://slixmpp.readthedocs.io/) bot to name mentioned XEPs and link to them.
Feel free to invite my instance, [xepsbot@pain.agency](xmpp:xepsbot@pain.agency)

What it does:

- `!xep <number | name | shortname>`
Outputs the xep number, name, and abstract of the mentioned XEP if found.
```md
Wed 07 Oct 2026 03:04:38 AM  - jjj333_p :
!xep oob
Wed 07 Oct 2026 03:04:38 AM  - XEPs Bot:
XEP-0066: *Out of Band Data* (Draft, last revised 2026-07-08, v1.6) https://xmpp.org/extensions/xep-0066.html
> This specification defines two XMPP protocol extensions for communicating URIs, one for use in XMPP message stanzas and the other for use in a structured request-response interaction via XMPP IQ stanzas. Among other things, this enables one entity to inform another entity about a file that is available at an HTTP URL.
```

- Mention a xep in your message, and the xep number, name and abstract will be output
```md
Wed 07 Oct 2026 03:04:32 AM  - jjj333_p :
xep6 xep-66 xep 45 XEP0359
Wed 07 Oct 2026 03:04:33 AM  - XEPs Bot:
XEP-0006: *Profiles* (Obsolete, last revised 2002-05-08, v1.1) https://xmpp.org/extensions/xep-0006.html
Wed 07 Oct 2026 03:04:33 AM  - XEPs Bot:
XEP-0066: *Out of Band Data* (Draft, last revised 2026-07-08, v1.6) https://xmpp.org/extensions/xep-0066.html
Wed 07 Oct 2026 03:04:33 AM  - XEPs Bot:
XEP-0045: *Multi-User Chat* (Draft, last revised 2026-05-03, v1.35.5) https://xmpp.org/extensions/xep-0045.html
Wed 07 Oct 2026 03:04:33 AM  - XEPs Bot:
XEP-0359: *Unique and Stable Stanza IDs* (Experimental, last revised 2023-02-20, v0.7.0) https://xmpp.org/extensions/xep-0359.html
```

- `!refresh` refreshes the index. The index is refreshed daily automatically.