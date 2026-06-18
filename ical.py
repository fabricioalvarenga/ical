import os
import sys
import imaplib
import email
from email import policy

# TODO: Encriptar dados do servidor e usuário
IMAP_SERVER = os.environ["IMAP_SERVER"] 
EMAIL = os.environ["EMAIL"]
PASSWORD = os.environ["EMAIL_PASSWORD"]

def main():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)

    try:
        login(mail, EMAIL, PASSWORD)

        select(mail, "INBOX")

        uids = get_all_messages(mail)

        for uid in reversed(uids):
            if not is_calendar_message(mail, uid):
                continue

            message = fetch(mail, uid)

            if message is None:
                continue

            for part in message.walk():
                if part.get_content_type() == "text/calendar":
                    calendar_data = part.get_payload(decode = True)

                    if not isinstance(calendar_data, bytes):
                        continue

                    # TODO: Buscar o caminho da pasta Documents automaticamente
                    with open("/Users/fabricioalvarenga/Documents/Downloads/reuniao.ics", "wb") as f:
                        f.write(calendar_data)
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def login(client, email, password):
    status, _ = client.login(email, password)

    if status != "OK":
        raise RuntimeError("Não foi possível realizar login no servidor")

def select(client, box):
    status, _ = client.select(box)

    if status != "OK":
        raise RuntimeError("Não foi possível abrir a Caixa de Entada")

def get_all_messages(client):
    status, data = client.uid("SEARCH", "", "ALL")

    if status != "OK":
        raise RuntimeError("Erro ao buscar as mensagens na Caixa de Entada")

    uids = data[0].split()

    if not uids:
        print("Nenhuma mensagem encontrada na Caixa de Entrada")
        sys.exit()

    return uids

def fetch(client, uid):
    status, message_data = client.uid("FETCH", uid, "(BODY.PEEK[])")

    if status != "OK":
        return None

    raw_message = None

    for item in message_data:
        if isinstance(item, tuple):
            raw_message = item[1]
            break

    if raw_message is None:
        return None

    return email.message_from_bytes(raw_message, policy = policy.default)

def is_calendar_message(client, uid):
    status, data = client.uid("FETCH", uid, "(BODYSTRUCTURE)")

    if status != "OK":
        return False

    body_structure = data[0]

    if not isinstance(body_structure, bytes):
        return False

    text = body_structure.decode("utf-8", errors = "replace").upper()

    if ('"CALENDAR"' in text or '.ICS' in text or 'ICS' in text):
        return True

    return False
    
if __name__ == "__main__":
    main()
