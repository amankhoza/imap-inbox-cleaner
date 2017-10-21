import json
import sys
import collections
import imaplib
import time
import logging
import re
from analyse import extract_address, extract_domain
from fetch import create_directory, init_logger, exception, init_imap


def run_command(attempt_no, create_new_instance, command, uid):
    global mail
    if attempt_no > TIMOUT_LIMIT:
        logger.error('Time out limit reached, deleted {} emails, read {} emails'.format(count['d'], count['r']))
        exit()
    if attempt_no > 0:
        logger.info('Timeout {}...'.format(attempt_no))
        time.sleep(TIMEOUT_WAIT)
        if create_new_instance:
            logger.info('Creating new imap instance')
            _, mail = init_imap(IMAP_HOST, USERNAME, PASSWORD)
        logger.info('Reattempting to run command {} for email_uid {}'.format(commands[command], uid))
    try:
        status, response = mail.uid('STORE', uid, '+FLAGS', command_flags[command])
        if status != 'OK':
            logger.info('Encountered problem whilst running command {} on email_uid {}\nResponse received:\n{}'.format(commands[command], uid, response))
            return run_command(attempt_no + 1, False, uid)
        elif attempt_no > 0:
            logger.info('Successfully ran command {} on email_uid {}'.format(commands[command], uid))
            logger.info('Progress report: {} emails deleted, {} emails read'.format(count['d'], count['r']))
        if status == 'OK':
            count[command] += 1
    except imaplib.IMAP4.abort:
        logger.error('Connection closed by server whilst running command {} on email_uid {}\n{}'.format(commands[command], uid, exception()))
        return run_command(attempt_no + 1, True, uid)
    except Exception:
        logger.error('Unexpected error whilst running command {} on email_uid {}, deleted {} emails, read {} emails\n{}'.format(commands[command], uid, count['d'], count['r'], exception()))
        exit()


def process_address(c, address):
    log('Info', 'Preparing to {} {} emails from address {}'.format(commands[c], len(address_to_uids[address]), address))
    if not TEST:
        uids = address_to_uids[address]
        for uid in uids:
            run_command(0, False, c, uid)
        mail.expunge()
        mark_line_as_done(INSTRUCTIONS_PATH, i)
    else:
        count[c] += len(address_to_uids[address])
    log('Info', 'Successfully {} {} emails from address {}'.format(commands[c], len(address_to_uids[address]), address))


def mark_line_as_done(file_name, line_num):
    lines = open(file_name, 'r').readlines()
    lines[line_num] = 'done ' + lines[line_num]
    out = open(file_name, 'w')
    out.writelines(lines)
    out.close()


def address_uids_mapping(store):
    uid_to_address = {uid: extract_address(email_string) for uid, email_string in store.items()}

    address_to_uids = collections.defaultdict(list)

    for k, v in uid_to_address.items():
        address_to_uids[v].append(k)

    return address_to_uids


def log(log_type, log_msg):
    if TEST:
        print(log_type + ': ' + log_msg)
    elif log_type == 'Error':
        logger.error(log_msg)
    elif log_type == 'Info':
        logger.info(log_msg)


logger = logging.getLogger()

if __name__ == "__main__":

    args = len(sys.argv)

    if (args == 7):
        DATA_PATH = sys.argv[1]
        INSTRUCTIONS_PATH = sys.argv[2]
        UID_VALIDITY = sys.argv[3]
        IMAP_HOST = sys.argv[4]
        USERNAME = sys.argv[5]
        PASSWORD = sys.argv[6]
        TEST = False
    elif (args == 3):
        DATA_PATH = sys.argv[1]
        INSTRUCTIONS_PATH = sys.argv[2]
        TEST = True
    else:
        print('Usage: python clean.py <data_path> <instructions_path> <uid_validity> <imap_host> <username> <password>')
        print('OR if you would like to test your command list (without making changes) then')
        print('Usage: python clean.py <data_path> <instructions_path>')
        exit()

    if not TEST:
        LOG_PATH = USERNAME + '/clean.log'
        TIMEOUT_WAIT = 30
        TIMOUT_LIMIT = 3

        create_directory(USERNAME)
        init_logger(LOG_PATH)

    count = {'d': 0, 'r': 0}

    store = json.load(open(DATA_PATH))

    addresses = map(extract_address, store.values())

    address_to_uids = address_uids_mapping(store)

    commands = {'d': 'DELETE', 'r': 'READ'}
    command_flags = {'d': '(\\Deleted)', 'r': '(\\Seen)'}

    instructions = open(INSTRUCTIONS_PATH, 'r').readlines()

    start = time.time()

    for i in range(len(instructions)):
        instruction = instructions[i].strip()
        if instruction[:4] == 'done':
            continue
        if not TEST:
            uidvalidity, mail = init_imap(IMAP_HOST, USERNAME, PASSWORD)
            if uidvalidity != UID_VALIDITY:
                logger.error('UID_VALIDITY {} does not match expected UID_VALIDITY of {} please refetch emails and try again'.format(uidvalidity, UID_VALIDITY))
                mail.close()
                mail.logout()
                exit()
        c, address = instruction.split(' ')
        if c not in commands:
            log('error', 'Whilst trying to process instruction "{}" on line {}. Command not found. Try "d" or "r" instead'.format(instruction, i))
        elif address.startswith('"') and address.endswith('"'):  # regex case
            pattern = address.strip('"')
            matching_addresses = [x for x in set(addresses) if re.match(pattern, x)]
            log('Info', 'Found {} addresses matching regex pattern "{}" {}'.format(len(matching_addresses), pattern, str(matching_addresses)))
            for addr in matching_addresses:
                process_address(c, addr)
        elif '@' not in address:  # domain case
            # log error for case where domain not in domains
            domain = address
            matching_addresses = [x for x in set(addresses) if extract_domain(x) == domain]
            log('Info', 'Found {} addresses matching domain {} {}'.format(len(matching_addresses), domain, str(matching_addresses)))
            for addr in matching_addresses:
                process_address(c, addr)
        elif address in address_to_uids:  # single address case
            process_address(c, address)
        else:
            log('Error', 'Whilst trying to process instruction "{}" on line {}. Address not found in unread emails.'.format(instruction, i))

    if not TEST:
        mail.close()
        mail.logout()

    end = time.time()
    log('Info', 'Completed, deleted {} emails, read {} emails, time elapsed: {:.1f}s'.format(count['d'], count['r'], end - start))
