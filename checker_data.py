from dataclasses import dataclass
from result_report import Checker, ResultReport
from pathlib import Path
from lxml import etree
from typing import Tuple

@dataclass
class CheckerData:
    checker: Checker
    reporter: ResultReport
    data: any
    file: Path
    config: dict
    format_settings: dict
    version: Tuple[int, int]

    def __init__(self, 
                file : Path,
                reporter: ResultReport, 
                config : dict, 
                format_settings : dict,
                checker: Checker = None, 
                data : any = None, 
                version: Tuple[int, int] = None) -> None:

        super().__init__()
        self.file = file
        self.reporter = reporter        
        self.config = config
        self.format_settings = format_settings
        self.checker = checker
        self.data = data
        self.version = version
