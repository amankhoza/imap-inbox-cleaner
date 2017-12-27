import imaplib
import time
import logging
import json
import sys
import os
from socket import gaierror


def exception():
    return logging.Formatter().formatException(sys.exc_info())


def init_imap(imap_host, username, password):
    logger.info('Attempting imap login')
    try:
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(username, password)
        logger.info('Successfully logged in')
        mail.select('Inbox')
        status = mail.status('Inbox', '(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)')
        logger.info('Inbox status\n{}'.format(status))
        _, response = mail.status('Inbox', '(UIDVALIDITY)')
        uidvalidity = response[0].split()[2].strip(').,]')
        return uidvalidity, mail
    except imaplib.IMAP4.error:
        logger.error('Failed to log in, please check user credentials\n{}'.format(exception()))
        exit()
    except gaierror:
        logger.error('Failed to log in, please check host name\n{}'.format(exception()))
        exit()


def fetched_count():
    return len(store) - prev_store_count


def fetch_header(attempt_no, create_new_instance, uid):
    global mail
    if attempt_no > TIMOUT_LIMIT:
        logger.error('Time out limit reached, only fetched {} emails'.format(fetched_count()))
        write_store()
        exit()
    if attempt_no > 0:
        logger.info('Timeout {}...'.format(attempt_no))
        time.sleep(TIMEOUT_WAIT)
        if create_new_instance:
            logger.info('Creating new imap instance')
            _, mail = init_imap(IMAP_HOST, USERNAME, PASSWORD)
        logger.info('Reattempting to download header for email_uid {}'.format(uid))
    try:
        status, response = mail.uid('FETCH', uid, '(BODY.PEEK[HEADER])')
        payload = response[0][1]
        if status != 'OK':
            logger.info('Encountered problem whilst downloading header for email_uid {}\nResponse received:\n{}'.format(uid, response))
            return fetch_header(attempt_no + 1, False, uid)
        elif attempt_no > 0:
            logger.info('Successfully downloaded header for email_uid {}'.format(uid))
            logger.info('Progress report: {} emails downloaded, {} remaining'.format(fetched_count(), len(uids_to_fetch) - fetched_count()))
        return payload
    except imaplib.IMAP4.abort:
        logger.error('Connection closed by server whilst processing email_uid {}\n{}'.format(uid, exception()))
        return fetch_header(attempt_no + 1, True, uid)
    except BaseException:
        logger.error('Unexpected error whilst processing email_uid {}, only fetched {} emails\n{}'.format(uid, fetched_count(), exception()))
        write_store()
        exit()


def write_store():
    with open(DATA_PATH, 'w') as fp:
        json.dump(store, fp, sort_keys=True)


def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def init_logger(log_path):
    logging.basicConfig(filename=log_path, level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s\n',
                        datefmt='%m/%d/%Y %H:%M:%S')


logger = logging.getLogger()

if __name__ == "__main__":

    args = len(sys.argv)

    if (args < 4):
        print ('Usage: python fetch.py <imap_host> <username> <password>')
        exit()
    else:
        IMAP_HOST = sys.argv[1]
        USERNAME = sys.argv[2]
        PASSWORD = sys.argv[3]

    DATA_PATH = USERNAME + '/data.json'
    LOG_PATH = USERNAME + '/fetch.log'
    TIMEOUT_WAIT = 30
    TIMOUT_LIMIT = 3

    create_directory(USERNAME)

    init_logger(LOG_PATH)

    prev_store_count = 0

    if (os.path.isfile(DATA_PATH)):
        store = json.load(open(DATA_PATH))
        prev_store_count = len(store)
        logger.info('Loaded {} emails from existing store'.format(prev_store_count))
    else:
        store = {}
        logger.info('Created new store')

    _, mail = init_imap(IMAP_HOST, USERNAME, PASSWORD)

    _, data = mail.uid('SEARCH', None, '(UNSEEN)')
    unread_msg_uids = data[0].split()
    uids_to_fetch = list(set(unread_msg_uids) ^ set(store.keys()))

    logger.info('{} unread emails on server'.format(len(unread_msg_uids)))
    logger.info('Attempting to fetch {} emails ({} in store)'.format(len(uids_to_fetch), len(store.keys())))

    start = time.time()

    for uid in uids_to_fetch:
        header = fetch_header(0, False, uid)
        store[uid] = unicode(header, errors='ignore')

    write_store()
    end = time.time()
    logger.info('Completed, fetched {} emails, time elapsed: {:.1f}s'.format(fetched_count(), end - start))
