#!/usr/bin/python

import os
import sys
import getopt
import json
import yaml
import urllib2

API_ROOT = 'https://api.perma.cc'
MEDIA_ROOT = 'https://user-content.perma.cc/media'
USER_AGENT = 'Perma Export Script'

def main(argv):
    key, output_dir = parse_args(argv)

    ensure_dir_exists(output_dir)
    os.chdir(output_dir)

    download_user(key)
    download_archives(key)
    download_folders(key)
    download_vesting_orgs(key)

def parse_args(argv):
    key = ''
    output_dir = ''
    help_text = '{script} --key <perma_api_key> --output-dir <the/output/directory>'.format(script=os.path.basename(__file__))
 
    try:
        opts, args = getopt.getopt(argv,"hk:o:",["key=","output-dir="])
    except getopt.GetoptError:
        print help_text
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print help_text
            sys.exit()
        elif opt in ("-k", "--key"):
            key = arg
        elif opt in ("-o", "--output-dir"):
            output_dir = arg

    return (key, output_dir)

def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def query_api(key, url):
    headers = {'Authorization' : 'ApiKey {key}'.format(key=key),
               'User-Agent' : USER_AGENT}
    request = urllib2.Request(API_ROOT + url, headers=headers)
    contents = urllib2.urlopen(request).read()
    return json.loads(contents)

def query_paginated_api(key, url):
    # initial seed for the first iteration
    result = {'meta': {'next': url}}

    while result.get('meta', {}).get('next'):
        result = query_api(key, result['meta']['next'])
        yield result

def write_to_fixture(fixture, result):
    fixture.write(yaml.safe_dump(result['objects'], default_flow_style=False))

def download_list(key, name):
    print 'Downloading {0}...'.format(name.replace('_', ' '))
    with open(name + '.yaml', 'w') as yaml_file:
        # initial seed for the first iteration
        for result in query_paginated_api(key, '/v1/user/{0}/'.format(name)):
            write_to_fixture(yaml_file, result)
            total = result['meta']['total_count']
            if total:
                percent = float(result['meta']['offset'] + len(result['objects'])) / total
            else:
                percent = 1
            update_progress(round(percent, 3))

def download_user(key):
    print 'Downloading users...'
    with open('users.yaml', 'w') as yaml_file:
        # wrap this response so it's stored as an array
        # to match the other resources
        result = {'objects': [query_api(key, '/v1/user')]}
        write_to_fixture(yaml_file, result)
        update_progress(1)

def download_archives(key):
    print 'Downloading archives...'
    with open('archives.yaml', 'w') as yaml_file:
        # initial seed for the first iteration
        for result in query_paginated_api(key, '/v1/user/archives/'):
            write_to_fixture(yaml_file, result)

            total = result['meta']['total_count']
            if total == 0:
                update_progress(1)
            else:
                for i, archive in enumerate(result['objects']):
                    download_assets(archive)
                    percent = (result['meta']['offset'] + i + 1.0) / total
                    update_progress(round(percent, 3))

def download_assets(archive):
    asset = archive['assets'][0]
    path = asset['base_storage_path']

    for key, val in asset.iteritems():
        if key == 'base_storage_path' or not val or val == 'failed':
            continue

        ensure_dir_exists(path)

        with open('{0}/{1}'.format(path, val), 'wb') as cap_file:
            url = '{0}/{1}/{2}'.format(MEDIA_ROOT, path, val)
            # A user agent is required or else you'll get a 403
            req = urllib2.Request(url, headers={'User-Agent' : USER_AGENT})
            con = urllib2.urlopen(req)
            cap_file.write(con.read())

def download_folders(key):
    download_list(key, 'folders')

def download_vesting_orgs(key):
    download_list(key, 'vesting_orgs')

# via: http://stackoverflow.com/a/15860757/313561
def update_progress(progress):
    barLength = 10 # Modify this to change the length of the progress bar
    status = ""
    if progress < 0:
        progress = 0
        status = "Halt...\r\n"
    if progress >= 1:
        progress = 1
        status = "Done...\r\n"
    block = int(round(barLength*progress))
    text = "\rPercent: [{0}] {1}% {2}".format( "#"*block + "-"*(barLength-block), progress*100, status)
    sys.stdout.write(text)
    sys.stdout.flush()

if __name__ == "__main__":
    main(sys.argv[1:])
