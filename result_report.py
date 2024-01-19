from typing import List, Dict, Union
from datetime import datetime
from pathlib import Path
from lxml import etree
from enum import Enum
from abc import ABC

import logging
import json
import uuid


class IssueLevel(Enum):
    """Class to represent the level of an validation issue."""
    ERROR = 1
    WARNING = 2
    INFORMATION = 3

def get_IssueLevel_str(level: IssueLevel) -> str:
    if (level == IssueLevel.ERROR):
        return "Error"
    elif (level == IssueLevel.WARNING):
        return "Warning"
    return "Info"

def get_IssueLevel_from_str(level: str) -> IssueLevel:
    if (level.lower() == "error"):
        return IssueLevel.ERROR
    elif (level.lower() == "warning"):
        return IssueLevel.WARNING
    return IssueLevel.INFORMATION


class Location(ABC):
    """Empty abstract class for validation locations.
    Location of an validation issue can refer to an file, line, position, ...
    """
    class_type: int

    def __lt__(self, other):
        return self.class_type < other.class_type   

    #pass


class FileLocation(Location):
    """Validation issue for a file location.

    Args:
        Location (Location): Extends abstract location class.
    """

    file_type: str
    row: int
    column: int

    def __init__(self, 
                 row: int = 0, 
                 column: int = 0) -> None:
        """Constructs a FileLocation object.

        Args:
            row (int, optional): The row of the issue in the refered file. Defaults to 0.
            column (int, optional): The column of the issue in the refered file. Defaults to 0.
        """
        super().__init__()
        self.file_type = '1' # Todo ask Cariad
        self.row = row
        self.column = column
        self.class_type = 0


class XmlLocation(Location):
    """Validation issue for a xml location.

    Args:
        Location (Location): Extends abstract location class.
    """

    xpath: str

    def __init__(self,
                 xpath: Union[str, etree._Element] = None) -> None:
        """Constructs a XmlLocation object.

        Args:
            file (Path, optional): Path of the file the issue refers to. Defaults to None.
            xpath (str, optional): XPath location in the refered file. Defaults to None.
        """
        super().__init__()
        if xpath is not None:
            if isinstance(xpath, str):
                self.xpath = xpath
            elif isinstance(xpath, etree._Element):
                # ToDo check if this produces a valid xpath beginning from root node
                el: etree._Element = xpath
                tree = etree.ElementTree(el)
                self.xpath = tree.getpath(el)
            else:
                logging.error(f'Unknown type of provided XPath: {type(xpath)}')
        self.class_type = 1


class RoadLocation(Location):
    """Validation issue for a road location.

    Args:
        Location (Location): Extends abstract location class.
    """

    road_id: str
    s: str
    t: str

    def __init__(self,
                 road_id: str = None,
                 s: str = None, 
                 t: str = None) -> None:
        """Constructs a RoadLocation object.

        Args:
            road_id (str, optional): Road id in the refered file. Defaults to None.
            s (str, optional): s postion along road in the refered file. Defaults to None.
            t (str, optional): s postion along road in the refered file. Defaults to None.
        """
        super().__init__()
        self.road_id = road_id
        self.s = s
        self.t = t
        self.class_type = 2


def create_location_for_road(el: etree._Element, roadID: int, s: float, t: float) -> List[Location]:
    locations = [
        XmlLocation(el),
        RoadLocation(roadID, str(s), str(t)),
        FileLocation(el.sourceline, 0)
    ]
    return locations


def create_location_from_error(error) -> List[Location]:
    locations = [
        FileLocation(error.line, error.column)
    ]
    if error.path is not None:
        locations.append(XmlLocation(error.path))
    return locations


def create_location_from_element(el: etree._Element) -> List[Location]:
    locations = [ 
        XmlLocation(el),
        FileLocation(el.sourceline, 0)
    ]
    return locations


class Issue:
    """Class representing a validation issue."""

    identifier: uuid.UUID
    level: IssueLevel
    description: str
    locations: List[Location]
    external: object

    def __init__(self, 
                 identifier: uuid.UUID = None,
                 level: IssueLevel = None,
                 description: str = None,
                 locations: List[Location] = None,
                 external: object = None) -> None:
        """Constructs a RoadLocation object.

        Args:
            identifier (uuid.UUID, optional): Identifier of the issue. Defaults to None.
            level (IssueLevel, optional): Severity level of the issue. Defaults to None.
            description (str, optional): Description of the issue. Defaults to None.
            locations (List[Location], optional): Locations the issue refers to. Defaults to None.
            external (object, optional): External links the issue refers to. Defaults to None.
        """
        self.identifier = identifier
        self.level = level
        self.description = description
        self.locations = locations
        self.external = external

    def __lt__(self, other):
        return self.identifier < other.identifier           


class Checker:
    """Class representing a checker."""

    _issues: List[Issue]
    checker_id: str
    description: str

    def __init__(self, checker_id: str = None, description: str = None):
        """Constructs a Checker object.

        Args:
            checker_id (str, optional): ID of the checker. Defaults to None.
            description (str, optional): Description of the checker. Defaults to None.
        """
        self._issues = []
        self.checker_id = checker_id
        self.description = description

    def __lt__(self, other):
        return self.checker_id < other.checker_id

    def add_issue(self, issue: Issue):
        """Adds an issue to the list of issues for this checker.

        Args:
            issue (Issue): The issue to be attached.
        """
        logging.info(f"  {self.checker_id}: {issue.description}")
        self._issues.append(issue)

    def gen_issue(self, level: IssueLevel = None,
                 description: str = None,
                 locations: List[Location] = None,
                 external: object = None) -> Issue:
        """Generates an Issue with the specified parameters, appends it to the list of issues and returns it.

        Args:
            level (IssueLevel, optional): Level of the issue. Defaults to None.
            description (str, optional): Description of the issue. Defaults to None.
            locations (List[Location], optional): Locations of the issue. Defaults to None.
            external (object, optional): External link of the issue. Defaults to None.

        Returns:
            Issue: the generated issue.
        """
        logging.info(f"  {self.checker_id}: {description}")
        issue = Issue(uuid.uuid4(), level, description, locations, external)
        self._issues.append(issue)
        return issue

    def get_summary(self):
        """Generates a string summary of the checker.

        Returns:
            str: String summary of the checker.
        """
        return f'Found {len(self._issues)} issue' if len(self._issues) == 1 else f'Found {len(self._issues)} issues'


class CheckerBundle:
    """Class representing a checker bundle."""

    _checkers: List[Checker]
    params: Dict[str, str]
    name: str
    description: str
    version: str

    def __init__(self, name: str = None, description: str = None, version: str = None):
        """Constructs a CheckerBundle object.

        Args:
            name (str, optional): Name of the checker bundle. Defaults to None.
            description (str, optional): Description of the checker bundle. Defaults to None.
            version (str, optional): Version of the checker bundle. Defaults to None.
        """
        self.version = version
        self.name = name
        self.description = description
        self._checkers = []
        self.params = {}

    def __lt__(self, other):
        return self.name < other.name          

    def add_checker(self, checker: Checker):
        """Appends a checker to the list in this bundle.

        Args:
            checker (Checker): The checker to be attached.
        """
        self._checkers.append(checker)

    def gen_checker(self, checker_id: str = None, description: str = None) -> Checker:
        """Generates a Checker with the specified parameters, appends it to the list of checkers and returns it.

        Args:
            checker_id (str, optional): ID of the checker. Defaults to None.
            description (str, optional): Description of the checker. Defaults to None.

        Returns:
            Checker: The new created checker.
        """
        checker = Checker(checker_id, description)
        self._checkers.append(checker)
        return checker

    def get_summary(self):
        """Generates a string summary of the checker.

        Returns:
            str: String summary of the checker bundle.
        """
        incidents = sum([len(checker._issues) for checker in self._checkers])
        return f'Found {incidents} incident' if incidents == 1 else f'Found {incidents} incidents'
    
    def get_build_date(self):
        """Returns the build date of the checker bundle.

        Returns:
            datetime.date: date object of build.
        """
        return datetime.now().strftime('%Y-%m-%d')


def dumper(obj):
    """Dumping method for json serialization.

    Args:
        obj (any): Any object that should be serialized

    Returns:
        str: Serialized object as JSON str.
    """
    try:
        return obj.toJSON()
    except:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, Enum):
            return str(obj)
        return obj.__dict__


class ResultReport:
    """Class representing a result report."""

    _checker_bundles: List[CheckerBundle]
    report_meta: Dict[str, str]
    checked_file: Path

    def __init__(self, checked_file: Path = None):
        """Constructs a ResultReport object.

        Args:
            checked_file (Path, optional): The path to the referenced checked file. Defaults to None.
        """
        self._checker_bundles = []
        self.report_meta = {}
        self.checked_file = checked_file

    def add_checker_bundle(self, checker_bundle: CheckerBundle):
        """Appends a checker bundle to this result report.

        Args:
            checker_bundle (CheckerBundle): CheckerBundle to be attached.
        """
        self._checker_bundles.append(checker_bundle)
    
    def gen_checker_bundle(self, name: str, description: str, version: str) -> CheckerBundle:
        """Generates a CheckerBundle with the specified parameters, appends it to the list of checkers and returns it.

        Args:
            name (str): Name of the CheckerBundle.
            description (str): Description of the CheckerBundle.
            version (str): Version of the CheckerBundle.

        Returns:
            CheckerBundle: The generated CheckerBundle.
        """
        checker_bundle = CheckerBundle(name=name, description=description, version=version)
        self._checker_bundles.append(checker_bundle)
        return checker_bundle
    
    def get_issues_count(self):
        count = 0
        for bundle in self._checker_bundles:
            count = count + sum([len(checker._issues) for checker in bundle._checkers])
        return count

    def write_as_json(self, file: Path):
        """Serializes this result report as an JSON string into the specified file.

        Args:
            file (Path): The path the JSON string will be written to.
        """
        with open(file, 'w') as f:
            json.dump(self, f,  default=dumper, sort_keys=True, indent=4)

    def get_as_xqar_xml_tree(self) -> etree._Element:
        """Returns this ResultReport as an XQAR, XML conform representation.

        Returns:
            etree._Element: The XML element representing this result report in XQAR.
        """
        xml_tree = etree.Element('CheckerResults')
        xml_tree.set('version', '1.0.0')

        self._checker_bundles.sort()
        for bundle in self._checker_bundles:
            bundle_element = etree.SubElement(xml_tree, 'CheckerBundle')
            for k, v in bundle.params.items():
                param_element = etree.SubElement(bundle_element, 'Param')
                param_element.set('name', k)
                param_element.set('value', v)

            bundle_element.set('build_date', bundle.get_build_date())
            bundle_element.set('description', bundle.description)
            bundle_element.set('name', bundle.name)
            bundle_element.set('summary', bundle.get_summary())
            bundle_element.set('version', str(bundle.version))

            bundle._checkers.sort()
            for check in bundle._checkers:
                check_element = etree.SubElement(bundle_element, 'Checker')
                check_element.set('checkerId', check.checker_id)
                check_element.set('description', check.description)
                check_element.set('summary', check.get_summary())

                check._issues.sort()
                for issue in check._issues:                
                    issue_element = etree.SubElement(check_element, 'Issue')
                    issue_element.set('description', issue.description)
                    issue_element.set('issueId', str(issue.identifier))                    
                    issue_element.set('level', str(issue.level.value))

                    location_element = etree.SubElement(issue_element, 'Locations')
                    location_element.set('description', issue.description)
                    if issue.locations is not None:
                        issue.locations.sort()
                        for location in issue.locations:
                            if isinstance(location, XmlLocation) and location.xpath is not None:
                                x_path_location_element = etree.SubElement(location_element, 'XMLLocation')
                                x_path_location_element.set('xpath', str(location.xpath))
                            if isinstance(location, FileLocation):
                                file_location_element = etree.SubElement(location_element, 'FileLocation')
                                file_location_element.set('column', str(location.column))
                                file_location_element.set('fileType', str(location.file_type))
                                file_location_element.set('row', str(location.row))
                            if isinstance(location, RoadLocation):
                                road_location_element = etree.SubElement(location_element, 'RoadLocation')
                                road_location_element.set('roadId', str(location.road_id))
                                if location.s is not None:
                                    road_location_element.set('s', str(location.s))
                                if location.t is not None:
                                    road_location_element.set('t', str(location.t)) 
        return xml_tree
    

    def write_as_xqar(self, file: Path):
        """Serializes this result report as an XQAR conform string into the specified file.

        Args:
            file (Path): The path the XQAR conform string will be written to.
        """
        et = etree.ElementTree(self.get_as_xqar_xml_tree())
        et.write(file, pretty_print=True, xml_declaration=True, encoding='utf-8')
    

    def get_as_text_list(self) -> list:
        """Returns this ResultReport as a simple text representation.

        Returns:
            list: The text list representing this result report in simple text.
        """
        text = list()
        text.append('CheckerResults:')
        for bundle in self._checker_bundles:
            text.append(f'bundle {bundle.name}')

            for check in bundle._checkers:
                text.append(f'  check = {check.checker_id} - {check.description}')

                if len(check._issues) > 0:
                    for issue in check._issues:                
                        text.append(f'    {get_IssueLevel_str(issue.level)}: {issue.description}')
                    else:
                        text.append('    ok') 
        return text    

    
    def write_as_txt(self, file: Path):
        """Serializes this result report as an simple text string into the specified file.

        Args:
            file (Path): The path the text string will be written to.
        """
        text = self.get_as_text_list()
        with open(file, 'w') as f:
            for line in text:
                f.write("%s\n" % line)