#!/usr/bin/python

import os
import sys
import getopt
import json
import yaml
import urllib2

API_ROOT = 'http://api.perma.dev:8000'
MEDIA_ROOT = 'http://perma.dev:8000/media'

def main(argv):
    key, output_dir = parse_args(argv)
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

def query_api(key, url):
    request = urllib2.Request(API_ROOT + url, headers={'Authorization' : 'ApiKey {key}'.format(key=key)})
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

def download_user(key):
    with open('users.yml', 'w') as yaml_file:
        result = {'objects': [query_api(key, '/v1/user')]}
        write_to_fixture(yaml_file, result)

def download_archives(key):
    with open('archives.yml', 'w') as yaml_file:
        # initial seed for the first iteration
        for result in query_paginated_api(key, '/v1/user/archives/?limit=3'):
            write_to_fixture(yaml_file, result)

            for i, archive in enumerate(result['objects']):
                download_assets(archive)
                per_comp = (result['meta']['offset'] + i + 1.0) / result['meta']['total_count']
                update_progress(round(per_comp, 3))

def download_assets(archive):
    asset = archive['assets'][0]
    path = asset['base_storage_path']

    for key, val in asset.iteritems():
        if key == 'base_storage_path' or not val or val == 'failed':
            continue

        # create the directory if needed
        if not os.path.exists(path):
            os.makedirs(path)

        # write the file
        with open('{0}/{1}'.format(path, val), 'wb') as cap_file:
            url = '{0}/{1}/{2}'.format(MEDIA_ROOT, path, val)
            remote = urllib2.urlopen(url)
            cap_file.write(remote.read())

def download_folders(key):
    with open('folders.yml', 'w') as yaml_file:
        # initial seed for the first iteration
        for result in query_paginated_api(key, '/v1/user/folders/?limit=3'):
            write_to_fixture(yaml_file, result)

def download_vesting_orgs(key):
    with open('vesting_orgs.yml', 'w') as yaml_file:
        # initial seed for the first iteration
        for result in query_paginated_api(key, '/v1/user/vesting_orgs/?limit=3'):
            write_to_fixture(yaml_file, result)

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