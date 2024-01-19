from result_report import ResultReport, IssueLevel, FileLocation
from checker_data import CheckerData 
from pathlib import Path
from typing import List
from lxml import etree

import logging
import os
import json

def get_bundle(sorted_bundles: List, path: Path):
    name = os.path.relpath(str(path), Path(__file__).parent).replace('/', '.').replace('.py', '').replace('\\', '.')
    module = __import__(name, fromlist=['ORDER'])
    order = []
    if hasattr(module, 'ORDER'):
        for bundle in module.ORDER:
            order.append(bundle)

    bundles = []
    bundles.extend([mod for mod in path.iterdir() if mod.is_dir() and mod.name != '__pycache__'])

    # sort
    bundle_names = {bundle.name: bundle for bundle in bundles}
    assigned = set()
    for bundle_order in order:
        if bundle_order in bundle_names:
            sorted_bundles.append(bundle_names[bundle_order])
            assigned.add(bundle_order)
        else:
            logging.error(f'Provided bundle {bundle_order} is defined in order but cannot be found.')
    for name in set(bundle_names.keys()) - assigned:
        sorted_bundles.append(bundle_names[name])

    return sorted_bundles

def get_sorted_checker_bundles(additional_check_dirs: List[str], format_setting: dict) -> List:
    # first get bundles from default format folder
    format_path = Path(__file__).parent / format_setting['extension'] / 'checks'
    bundle_order = []
    bundle_order = get_bundle(bundle_order, format_path)

    # then get bundles from additional folder
    if additional_check_dirs is not None:
        for additional_dir in additional_check_dirs:
            additional_path = Path(additional_dir)
            bundle_order = get_bundle(bundle_order, additional_path)
    
    return bundle_order


def run_checks(file: Path, result_report: ResultReport, additional_check_dirs: List[str], config: dict, format_setting: dict) -> bool:

    checker_data = CheckerData(file=file, reporter=result_report, config=config, format_settings=format_setting)

    check_bundles = get_sorted_checker_bundles(additional_check_dirs, format_setting)
    logging.debug(f'Found {len(check_bundles)} checker modules')

    for check_bundle in check_bundles:
        try:
            # load checker bundle
            parent_module = __name__
            if '.' in parent_module:
                parent_module = parent_module[:parent_module.rfind('.') + 1]
            else:
                parent_module = ''
            bundle_name = parent_module + os.path.relpath(str(check_bundle), Path(__file__).parent).replace('/', '.').replace('.py', '').replace('\\', '.')
            logging.debug(f'Loading checker bundle {{{bundle_name}}}')
            bundle_module = __import__(bundle_name, fromlist=['CHECKER_BUNDLE_NAME', 'CHECKER_BUNDLE_DESCRIPTION', 'CHECKER_BUNDLE_VERSION', 'ORDER'])
            
            checker_bundle = result_report.gen_checker_bundle(bundle_module.CHECKER_BUNDLE_NAME, bundle_module.CHECKER_BUNDLE_DESCRIPTION, bundle_module.CHECKER_BUNDLE_VERSION)
            param_name = format_setting['extension'].capitalize() + 'File'
            checker_bundle.params[param_name] = str(file)

            # get all checker python files
            checkers = [checker for checker in check_bundle.iterdir() if checker.name.endswith('.py') and checker.name != '__init__.py' and checker.name.startswith('check_')]
            checker_names = {checker.name: checker for checker in checkers}

            # sort checks according to bundle order
            if hasattr(bundle_module, 'ORDER'):
                order = bundle_module.ORDER
                sorted_checkers = []
                assigned = set()
                for checker_order in order:
                    py_name = f'{checker_order}.py'
                    if checker_order in checker_names:
                        sorted_checkers.append(checker_names[checker_order])
                        assigned.add(checker_order)
                    elif py_name in checker_names:
                        sorted_checkers.append(checker_names[py_name])
                        assigned.add(py_name)
                    else:
                        logging.error(f'Provided checker {checker_order} is defined in order but cannot be found.')
                for name in set(checker_names.keys()) - assigned:
                    sorted_checkers.append(checker_names[name])
                checkers = sorted_checkers

            # load and execute checks
            for checker in checkers:
                module_name = parent_module + os.path.relpath(str(checker), Path(__file__).parent).replace('/', '.').replace('.py', '').replace('\\', '.')
                logging.debug(f'Loading checker {{{module_name}}}')
                try:
                    check_module = __import__(module_name, fromlist=['check', 'get_checker_id', 'get_description'])
                except:
                    logging.exception(f'Could not load checker bundle {module_name}')
                    continue
                
                # check required functions
                required_functions = ['check', 'get_checker_id', 'get_description']
                missing_function = False
                for function in required_functions:
                    if not hasattr(check_module, function):    
                        logging.error(f'{module_name} has no requried function {function}')
                        missing_function = True
                        break
                if missing_function: 
                    continue                                        

                # create checker
                checker_data.checker  = checker_bundle.gen_checker(check_module.get_checker_id(), check_module.get_description())
                # get config for check
                if bundle_module.CHECKER_BUNDLE_NAME in config and check_module.get_checker_id() in config[bundle_module.CHECKER_BUNDLE_NAME]:
                    checker_data.config = config[bundle_module.CHECKER_BUNDLE_NAME][check_module.get_checker_id()]
                
                # execute check
                try:
                    success = check_module.check(checker_data)
                    if success is False: # not exist or readable or critcal check issue
                        logging.exception(f'Cancel checks for the file {check_module.get_checker_id()}')
                        return False
                except:
                    logging.exception(f'Could not {check_module.get_checker_id()}')
                    checker_data.checker.gen_issue(IssueLevel.ERROR, f'Could not {check_module.get_description()}')                
                
        except:
            logging.exception(f'Could not load checker bundle {check_bundle}')
    return True


def validate(file: Path, additional_check_dirs: List[str], config_path: Path, format_extension: str) -> (ResultReport, bool):
    
    # init result_report and checker
    result_report = ResultReport()
    result_report.checked_file = file
    file = file.expanduser()
    file = file.resolve()
    
    # find format settings
    if format_extension == None:
        format_extension = file.suffix.lstrip('.')
    format_path = Path(__file__).parent / f'{format_extension}/format.json'
    if not format_path.exists() or not format_path.is_file():
        logging.error(f'Provided format description path does not exist or is not a file: {format_path.absolute()}')
        return result_report, False    
    # load format settings
    with open(format_path, 'r') as f:
        format_settings = json.load(f)

    # get config file
    if config_path == None:
        config_path = Path(__file__).parent / f'{format_extension}/config.json'
    if not config_path.exists() or not config_path.is_file():
        logging.error(f'Provided config path does not exist or is not a file: {config_path.absolute()}')
        return result_report, False
    with open(config_path, 'r') as f:
        config = json.load(f)        

    # run checks
    sucess = run_checks(file, result_report, additional_check_dirs, config, format_settings)
    
    return result_report, sucess

def get_files(input_files: any):
    for data in input_files:
        if os.path.isdir(data):
            for root, dirs, files in os.walk(data):
                for file in files:
                    yield Path(os.path.join(root, file))
        else:
            yield Path(data)