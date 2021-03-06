import json
import sys
import os
import email
from email.header import decode_header
import collections
from analyse import extract_address, extract_date, extract_domain, address_uids_mapping


def extract_subject(email_string):
    email_msg = email.message_from_string(email_string)
    subject = email_msg['Subject'].strip()
    dh = decode_header(subject)
    default_charset = 'ASCII'
    ascii_subject = ''.join([unicode(t[0], t[1] or default_charset) for t in dh])  # converts to ascii
    return ''.join(s for s in ascii_subject if ord(s)>31 and ord(s)<126)  # removes formatting characters


def existing_instructions_file_exists():
    data_directory = os.path.dirname(DATA_PATH)
    return os.path.isfile(data_directory + '/instructions')


def load_existing_instructions_file():
    data_directory = os.path.dirname(DATA_PATH)
    instructions = open(data_directory + '/instructions', "r").readlines()

    existing_instructions_dict = {}

    for i in range(len(instructions)):
        instruction = instructions[i].strip()
        if instruction[:4] == 'done':
            continue
        c, address = instruction.split(' ')
        existing_instructions_dict[address] = c

    return existing_instructions_dict


def count_emails_for_existing_instructions():
    count = 0
    for domain in existing_instructions:
        matching_addresses = [y for y in set(addresses) if extract_domain(y) == domain]
        for address in matching_addresses:
            uids = address_to_uids[address]
            count += len(uids)
    return count


def write_instructions_file():
    data_directory = os.path.dirname(DATA_PATH)
    out = open(data_directory + '/instructions', "a")
    for instruction in instructions:
        if instruction:
            out.write(instruction + '\n')
    out.close()


def print_help():
    print('Actions List:\nr = mark as read\nd = delete\ns = skip\nu = undo\nf = finish\nh = help\n')


if __name__ == "__main__":

    args = len(sys.argv)

    if (args < 2):
        print ('Usage: python build_instructions.py <data_path>')
        exit()
    else:
        DATA_PATH = sys.argv[1]

    existing_instructions = {}

    if existing_instructions_file_exists():
        response = None
        while response not in ['y', 'n']:
            response = raw_input("Existing instructions file found, would you like to load the rules in there? y or n: ")
        if response == 'y':
            existing_instructions = load_existing_instructions_file()

    store = json.load(open(DATA_PATH))

    addresses = map(extract_address, store.values())
    domains = map(extract_domain, addresses)

    address_to_uids = address_uids_mapping(store)

    total_email_count = 0
    if len(existing_instructions) > 0:
        total_email_count = count_emails_for_existing_instructions()
        for d in existing_instructions:
            while d in domains:
                domains.remove(d)

    domain_occurences = collections.Counter(domains).most_common()

    format_str = '{:35}\t{:15}\t{:50}'

    print_help()

    print((format_str+'\n').format('Address', 'Date', 'Subject'))

    instructions = []
    answer = ''
    i = 0

    while (i < len(domain_occurences)):
        domain = domain_occurences[i][0]

        matching_addresses = [y for y in set(addresses) if extract_domain(y) == domain]

        email_count = 0

        for address in matching_addresses:
            uids = address_to_uids[address]
            email_count += len(uids)
            recent_uids = sorted(uids)[:10]
            for uid in recent_uids:
                email_string = store[uid]
                date = extract_date(email_string)
                subject = extract_subject(email_string)
                print(format_str.format(address, date, '\"'+subject[:100]+'\"'))
        
        if answer != 'u':
            total_email_count += email_count

        answer = None

        while answer not in ['r', 'd', 's', 'u', 'f', 'h']:
            answer = raw_input('\n[{}/{} emails] You have {} unread from @{}. What action would you like to perform on them?\n'.format(total_email_count, len(store), email_count, domain))

            # r = mark as read
            # d = delete
            # s = skip
            # u = undo
            # f = finish
            # h = help

            if answer == 'f':
                write_instructions_file()
                exit()
            elif answer == 'u':
                if i > 0:
                    total_email_count -= email_count
                    instructions.pop()
                    i -= 1
            elif (answer in ['r', 'd']):
                instructions.append(answer + ' ' + domain)
            elif answer == 's':
                instructions.append('')  # so that instructions.pop() above works correctly
            else:
                print_help()

        if answer == 'u':
            continue

        print('')

        i += 1

    write_instructions_file()
