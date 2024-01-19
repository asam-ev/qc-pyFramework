#!/bin/python3

if __name__ == '__main__':
    from validator import validate, get_files
else:
    from .validator import validate, get_files
from pathlib import Path

import argparse
import logging
import json
import os

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s.%(msecs)03d [%(levelname)5s-%(name)s] {%(module)s -> %(funcName)s} %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')
logging.getLogger(__name__).setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(prog='main.py',
                                     description='Validates a given XML based OpenX file.')

    parser.add_argument('-o', '--output-directory', type=str, default='reports/', help='Path to validation report folder.')
    parser.add_argument('-t', '--output-type', choices=['xqar', 'json', 'txt'], default='xqar', help='Output format of result report (available: xqar, json, txt).')
    parser.add_argument('-e', '--exit-type', choices=['no-exit', 'exit-if-error'], default='no-exit', help='Should the script be terminated after an error or not.')
    parser.add_argument('-a', '--addition-check-dirs', action='append', help='Additional directories for validation checks.')
    parser.add_argument('-c', '--config', type=str, help='Path to config file. Otherwise the config is taken from the format folder')
    parser.add_argument('-f', '--format', type=str, default='xodr', help='Specification of the formats to be checked (file extension or check folder), e.g. xodr for OpenDrive.') # TODO format dependent
    parser.add_argument('INPUT_FILES', nargs='+', help='file(s) or folder to validate')

    args = parser.parse_args()

    # get output dir
    output_directory = Path(args.output_directory)
    if not output_directory.exists():
        logging.info(f'Provided output foler ({output_directory.absolute()}) does not exist. Creating it...')
        output_directory.mkdir(exist_ok=True, parents=True)
    elif output_directory.exists() and not output_directory.is_dir():
        logging.error(f'Provided output folder exists and is not an directory: {output_directory.absolute()}')
        exit(1)

    # get config path
    config_path = None
    if args.config:
        config_path = Path(args.config)

    issue_counter = []
    # validate input files
    for file in get_files(args.INPUT_FILES):
        output_file = output_directory / (file.name + '.' + args.output_type)        
        
        # validate        
        result, valid = validate(file, args.addition_check_dirs, config_path, args.format)
        
        # write result
        if valid:
            logging.info(f'write to {output_file}')
            if args.output_type == 'json':
                result.write_as_json(output_file)
            elif args.output_type == 'xqar':
                result.write_as_xqar(output_file)
            elif args.output_type == 'txt':
                result.write_as_txt(output_file)

            issue_counter.append(f'{result.get_issues_count()} issues in {os.path.basename(file)}')
        elif args.exit_type == 'exit-if-error':
            exit(1)

    for file_isses in issue_counter:
        print(file_isses)


if __name__ == '__main__':
    main()
