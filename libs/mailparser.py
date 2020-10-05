# Author: Zhang Huangbin <zhb@iredmail.org>

import email
from email.header import decode_header
from libs.logger import log_traceback


def __decode_headers(msg):
    """Decode message into list of {header: value}."""

    # List of {header: value} pairs.
    headers = []

    # header 'From: name <email>'
    header_from = []

    for (header, value) in list(msg.items()):
        for (text, encoding) in decode_header(value):
            if not encoding:
                encoding = 'utf-8'

            try:
                value = str(text, encoding=encoding, errors='replace')
            except:
                continue

            if header == 'From':
                header_from.append(value)
            else:
                headers += [{header: value}]

    if header_from:
        headers = [{'From': ' '.join(header_from)}] + headers

    return headers


def parse_raw_message(msg: bytes):
    """Read RAW message from string. Return tuple of:

    list of multiple mail headers: [[header: value], [header: value], ...]
    list of (multiple) body parts: [part1, part2, ...]
    list of attachment file names: [name1, name2, ...]
    """

    # Get all mail headers. Sample:
    # [{'From': 'sender@xx.com'}, {'To': 'recipient@xx.net'}]
    headers = []

    # Get decoded content parts of mail body.
    bodies = []

    # Get list of attachment names.
    attachments = []

    msg = email.message_from_bytes(msg)

    # Extract all headers.
    for i in __decode_headers(msg):
        for k in i:
            headers += [(k, i[k])]

    for part in msg.walk():
        _content_type = part.get_content_maintype()

        # multipart/* is just a container
        if _content_type == 'multipart':
            continue

        # either a string or None.
        _filename = part.get_filename()
        if _filename:
            attachments += [_filename]

        if _content_type == 'text':
            # Plain text, not an attachment.
            try:
                if part.get_content_charset():
                    encoding = part.get_content_charset()
                elif part.get_charset():
                    encoding = part.get_charset()
                else:
                    encoding = 'utf-8'

                text = str(part.get_payload(decode=True),
                           encoding=encoding,
                           errors='replace')

                text = text.strip()
                bodies.append(text)
            except:
                log_traceback()

    return (headers, bodies, attachments)
