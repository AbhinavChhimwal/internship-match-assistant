import argparse
from db import init_db, create_user

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Assign private demo access codes. Codes are printed once; SQLite stores only hashes.')
    parser.add_argument('command',choices=['create-users'])
    parser.add_argument('--names',nargs='+',required=True)
    args=parser.parse_args()
    if not 1<=len(args.names)<=10:
        parser.error('Create between one and ten invited accounts at a time.')
    init_db()
    for name in args.names:
        print(f'{name}: {create_user(name)}')
