import os
import sys
import imaplib
import email
from email import policy

# TODO: Encriptar dados do servidor e usuário
IMAP_SERVER = os.environ["IMAP_SERVER"] 
EMAIL = os.environ["EMAIL"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

mail = imaplib.IMAP4_SSL(IMAP_SERVER)

try:
    _, _ = mail.login(EMAIL, EMAIL_PASSWORD)

    status, _ = mail.select("INBOX")

    if status != "OK":
        raise RuntimeError("Não foi possível abrir a Caixa de Entada")

    status, data = mail.uid("SEARCH", "", "ALL")

    if status != "OK":
        raise RuntimeError("Erro ao buscar as mensagens na Caixa de Entada")

    uids = data[0].split()

    if not uids:
        print("Nenhuma mensagem encontrada na Caixa de Entrada")
        sys.exit()

    for uid in reversed(uids):
        print(uid)

        status, message_data = mail.uid("FETCH", uid, "(BODY.PEEK[])")

        if status != "OK":
            continue

        raw_message = None

        for item in message_data:
            if isinstance(item, tuple):
                raw_message = item[1]
                break

        if raw_message is None:
            continue

        message = email.message_from_bytes(raw_message, policy = policy.default)

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

