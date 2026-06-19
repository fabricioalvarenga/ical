import email
import imaplib
import json
import os
import subprocess
from email import policy
from pathlib import Path

# TODO: Encriptar dados do servidor e usuário
IMAP_SERVER = os.environ["IMAP_SERVER"]
EMAIL = os.environ["EMAIL"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

OUTPUT_DIR = Path("/tmp/meetings")
MEETING_FILE = OUTPUT_DIR / "meeting.ics"
STATE_FILE = OUTPUT_DIR / "state.json"

OUTPUT_DIR.mkdir(parents = True, exist_ok = True)

def main():

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)

    try:
        account_login(mail, EMAIL, EMAIL_PASSWORD)

        select_mail_box(mail, "INBOX")

        state = load_state()

        saved_mail_box_uid = state["mail_box_uid"]

        current_mail_box_uid = get_mail_box_uid(mail)

        if saved_mail_box_uid is not None and current_mail_box_uid != saved_mail_box_uid:
            state["last_uid"] = 0

        new_uids = search_new_uids(mail, int(state["last_uid"]))

        if  not new_uids:
            save_state(current_mail_box_uid, int(state["last_uid"]))
            return

        for uid in sorted(new_uids):
            if not body_structure_contains_calendar(mail, uid):
                continue

            message = fetch_message(mail, uid)

            if message is None:
                continue

            calendar_data = extract_calendar_data(message)

            if calendar_data is None:
                continue

            save_ics_file(calendar_data)

            highest_uid = uid

            save_state(current_mail_box_uid, highest_uid)

            open_ics_file()

            break
    finally:
        try:
            mail.logout()
        except Exception:
            pass

def account_login(mail, email, password):
    status, _ = mail.login(email, password)

    if status != "OK":
        raise RuntimeError("Não foi possível realizar login no servidor")

def select_mail_box(mail, box):
    status, _ = mail.select(box)

    if status != "OK":
        raise RuntimeError("Não foi possível abrir a Caixa de Entada")
    
def load_state():
    if not STATE_FILE.exists():
        return { "mail_box_uid" : None, "last_uid": 0 }

    with STATE_FILE.open() as f:
        return json.load(f)

def save_state(mail_box_uid, last_uid):
    with STATE_FILE.open("w") as f:
        json.dump({ "mail_box_uid": mail_box_uid, "last_uid": last_uid },f, indent = 2)

def get_mail_box_uid(mail):
    response = mail.response("UIDVALIDITY")

    if response is None:
        raise RuntimeError("Servidor não retornou o UID da Caixa de Entrada")

    _, values = response

    return int(values[0])

def search_new_uids(mail, last_uid):
    status, data = mail.uid("SEARCH", None, "ALL")

    if status != "OK":
        raise RuntimeError("Erro ao buscar as mensagens na Caixa de Entrada")

    all_uids = [int(uid) for uid in data[0].split()]

    return [
        uid
        for uid in all_uids
        if uid > last_uid
    ]

def body_structure_contains_calendar(mail, uid):
    status, data = mail.uid("FETCH", str(uid), "(BODYSTRUCTURE)")

    if status != "OK":
        return False

    if not data:
        return False

    body_structure = data[0]

    if not isinstance(body_structure, bytes):
        return False

    text = body_structure.decode("utf-8", errors = "replace").upper()

    if ('"CALENDAR"' in text or '.ICS' in text or 'ICS' in text):
        return True

    return False

def fetch_message(mail, uid):
    status, message_data = mail.uid("FETCH", str(uid), "(BODY.PEEK[])")

    if status != "OK":
        return None

    raw_message = None

    for item in message_data:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            raw_message = item[1]
            break

    if raw_message is None:
        return None

    return email.message_from_bytes(raw_message, policy = policy.default)

def extract_calendar_data(message):
    for part in message.walk():
        if part.get_content_type() == "text/calendar":
            calendar_data = part.get_payload(decode = True)

            if isinstance(calendar_data, bytes):
                return calendar_data

    return None
 
def save_ics_file(calendar_data):
    with MEETING_FILE.open("wb") as f:
        f.write(calendar_data)

def open_ics_file():
    subprocess.run(["open", MEETING_FILE])

if __name__ == "__main__":
    main()
