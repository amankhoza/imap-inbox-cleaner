import json
import sys
import email
import collections
import time


def extract_address(email_string):
    email_msg = email.message_from_string(email_string)
    from_field = email_msg['From'].strip()
    if '<' not in from_field:
        return from_field
    else:
        return from_field.split('<')[1].strip('>')


def extract_domain(address):
    if '@' not in address:
        return address
    else:
        return address.split('@')[1]


def address_uids_mapping(store):
    uid_to_address = {uid: extract_address(email_string) for uid, email_string in store.items()}

    address_to_uids = collections.defaultdict(list)

    for k, v in uid_to_address.items():
        address_to_uids[v].append(k)

    return address_to_uids


if __name__ == "__main__":

    args = len(sys.argv)

    if (args < 2):
        print ('Usage: python analyse.py <data_path>')
        exit()
    else:
        DATA_PATH = sys.argv[1]

    store = json.load(open(DATA_PATH))

    addresses = map(extract_address, store.values())
    domains = map(extract_domain, addresses)

    address_occurences = collections.Counter(addresses).most_common()
    domain_occurences = collections.Counter(domains).most_common()

    address_to_uids = address_uids_mapping(store)

    print('\nYou have {} unread emails from {} unique senders:\n'.format(len(store), len(address_occurences)))

    print('Last received\tUnread\tAddress')

    for x in address_occurences:
        occurences = str(x[1])
        address = x[0]
        uids = address_to_uids[address]
        latest_uid = max(uids)
        latest_email = email.message_from_string(store[latest_uid])
        date_tuple = email.utils.parsedate(latest_email['Date'])
        if date_tuple:
            date = time.strftime('%d %b %Y', date_tuple)
        else:
            date = '-- --- ----'
        print(date + '\t' + occurences + '\t' + address)

    print('\nYou have {} unread emails from {} unique domains:\n'.format(len(store), len(domain_occurences)))

    print('Unread\tDomain')

    for x in domain_occurences:
        occurences = str(x[1])
        domain = x[0]
        matching_addresses = [y for y in set(addresses) if extract_domain(y) == domain]
        if (len(matching_addresses)) > 1:
            address_spelling = 'addresses'
        else:
            address_spelling = 'address'
        print('{}\t{} ({} {})'.format(occurences, domain, len(matching_addresses), address_spelling))
