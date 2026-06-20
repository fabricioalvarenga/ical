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

OUTPUT_DIR = Path.home() / "Documents" / "Downloads" / ".meetings"
STATE_FILE = OUTPUT_DIR / "state.json"

OUTPUT_DIR.mkdir(parents = True, exist_ok = True)

def main():
    clear_meetings_directory()

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
            highest_uid = uid

            if not body_structure_contains_calendar(mail, uid):
                continue

            message = fetch_message(mail, uid)

            if message is None:
                continue

            for part in message.walk():
                calendar_data = extract_calendar_data(part)

                if calendar_data is None:
                    continue

                file_path = define_meeting_file_path()

                save_ics_file(calendar_data, file_path)

                open_ics_file(file_path)

#            break

        save_state(current_mail_box_uid, highest_uid)
    finally:
        try:
            mail.logout()
        except Exception:
            pass

def clear_meetings_directory():
    for file_path in OUTPUT_DIR.glob("*.ics"):
        if file_path.is_file():
            file_path.unlink()

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

    text = body_structure.decode("utf-8", errors = "replace").lower()

    if ('"calendar"' in text or '.ics' in text or 'ics' in text):
        print(f"{uid} cotains calendar")
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

def define_meeting_file_path():
    count = 1

    while True:
        file_path = OUTPUT_DIR / f"meeting[{count}].ics"

        if not file_path.exists():
            return file_path
    
        count += 1

def extract_calendar_data(part):
    content_type = part.get_content_type()
    filename = part.get_filename()

    is_calendar = (content_type == "text/calendar") or (filename is not None and filename.lower().endswith(".ics"))

    if is_calendar:
        calendar_data = part.get_payload(decode = True)

        if isinstance(calendar_data, bytes):
            return calendar_data

    return None
 
def save_ics_file(calendar_data, file_path):
    with file_path.open("wb") as f:
        f.write(calendar_data)

def open_ics_file(file_path):
    subprocess.run(["open", file_path])

if __name__ == "__main__":
    main()
