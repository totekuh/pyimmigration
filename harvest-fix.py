#!/usr/bin/env python3

import sys

used_emails_file = 'used_emails.txt'

new_file = sys.argv[1]

with open(used_emails_file, 'r') as f:
    used_emails_content = [line.strip().lstrip(',./\'"') for line in f.readlines() if line.strip() and '@' in line]

with open(new_file, 'r') as f:
    new_emails_content = [line.strip().lstrip(',./\'"') for line in f.readlines() if line.strip() and '@' in line]

for line in new_emails_content:
    if line not in used_emails_content and len(line) < 150:
        print(line)
