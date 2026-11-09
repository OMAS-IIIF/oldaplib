import json
from datetime import date
from enum import Enum
from typing import Dict, Self

from convertdate import gregorian, hebrew, islamic, julian, persian

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@serializer
class DatePrecision(Enum):
    DAY = 'oldap:DayPrecision'
    MONTH = 'oldap:MonthPrecision'
    YEAR = 'oldap:YearPrecision'
    DECADE = 'oldap:DecadePrecision'
    CENTURY = 'oldap:CenturyPrecision'

    def _as_dict(self) -> Dict[str, str]:
        return {__class__: self.__class__.__name__, 'value': self.value}


@serializer
class OldapCalendar(Enum):
    GREGORIAN = 'oldap:GregorianCalendar'
    JULIAN = 'oldap:JulianCalendar'
    HEBREW = 'oldap:HebrewCalendar'
    ISLAMIC = 'oldap:IslamicCalendar'
    PERSIAN = 'oldap:PersianCalendar'

    def _as_dict(self) -> dict[str, str]:
        return {__class__: self.__class__.__name__, 'value': self.value}

    @staticmethod
    def from_string(s: str) -> Self:
        match s:
            case 'GREGORIAN' | 'oldap:GregorianCalendar':
                return OldapCalendar.GREGORIAN
            case 'JULIAN' | 'oldap:JulianCalendar':
                return OldapCalendar.JULIAN
            case 'HEBREW' | 'oldap:HebrewCalendar':
                return OldapCalendar.HEBREW
            case 'ISLAMIC' | 'oldap:IslamicCalendar':
                return OldapCalendar.ISLAMIC
            case 'PERSIAN' | 'oldap:PersianCalendar':
                return OldapCalendar.PERSIAN
            case _:
                raise OldapErrorValue(f'Invalid calendar: {s}')


DatingTuple = tuple[int, ...] | list[int]


@serializer
class Dating(Xsd):
    __iri: Iri | Xsd_QName | None
    _dateStartTuple: tuple[int, ...]
    _dateEndTuple: tuple[int, ...]
    _normalizedStart: date
    _normalizedEnd: date
    _verbatimDate: str | None
    _datePrecision: DatePrecision
    _inCalendar: OldapCalendar
    _beforeDating: set[Self]

    @staticmethod
    def __parse(s: str) -> tuple[tuple[int, ...], OldapCalendar]:
        try:
            datestr, cal = s.split(':', 1)
        except ValueError:
            datestr = s
            cal = 'GREGORIAN'
        newcal = OldapCalendar.from_string(cal)
        parts = datestr.split('-')
        if len(parts) not in {1, 2, 3}:
            raise OldapErrorValue(f'Invalid date format: {datestr}')
        try:
            return tuple(map(int, parts)), newcal
        except ValueError as err:
            raise OldapErrorValue(f'Invalid date format: {datestr}') from err

    @staticmethod
    def __normalize_date_tuple(value: DatingTuple | str,
                               *,
                               default_calendar: OldapCalendar | None = None) -> tuple[tuple[int, ...], OldapCalendar | None]:
        if isinstance(value, str):
            return Dating.__parse(value)
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise OldapErrorValue(f'Invalid date format: {value}')
        if not value:
            raise OldapErrorValue('Date tuple must not be empty.')
        if isinstance(value[-1], OldapCalendar):
            if default_calendar is not None and default_calendar != value[-1]:
                raise OldapErrorValue(f'Inconsistent calendar info: {value[-1]} != {default_calendar}')
            return tuple(value[:-1]), value[-1]
        return tuple(value), default_calendar

    @staticmethod
    def __infer_precision(date_start: tuple[int, ...], date_end: tuple[int, ...]) -> DatePrecision:
        if len(date_start) == 3:
            return DatePrecision.DAY
        if len(date_start) == 2:
            return DatePrecision.MONTH
        if date_start[0] % 100 == 0 and date_end[0] == date_start[0] + 99:
            return DatePrecision.CENTURY
        if date_start[0] % 10 == 0 and date_end[0] == date_start[0] + 9:
            return DatePrecision.DECADE
        return DatePrecision.YEAR

    @staticmethod
    def __validate_precision(date_start: tuple[int, ...], date_end: tuple[int, ...], precision: DatePrecision) -> None:
        match precision:
            case DatePrecision.DAY:
                if len(date_start) != 3:
                    raise OldapErrorValue('Invalid date format: Date precision does not correspond to DAY.')
                if date_end < date_start:
                    raise OldapErrorValue('Invalid date format: End date precedes start date.')
            case DatePrecision.MONTH:
                if len(date_start) != 2:
                    raise OldapErrorValue('Invalid date format: Date precision does not correspond to MONTH.')
                if date_end < date_start:
                    raise OldapErrorValue('Invalid date format: End date precedes start date.')
            case DatePrecision.YEAR:
                if len(date_start) != 1:
                    raise OldapErrorValue('Invalid date format: Date precision does not correspond to YEAR.')
                if date_end[0] < date_start[0]:
                    raise OldapErrorValue('Invalid date format: End date precedes start date.')
            case DatePrecision.DECADE:
                if len(date_start) != 1 or date_start[0] % 10 != 0 or date_end[0] < date_start[0]:
                    raise OldapErrorValue('Invalid date format: Date precision does not correspond to DECADE.')
            case DatePrecision.CENTURY:
                if len(date_start) != 1 or date_start[0] % 100 != 0 or date_end[0] < date_start[0]:
                    raise OldapErrorValue('Invalid date format: Date precision does not correspond to CENTURY.')

    @staticmethod
    def __normalize_precision_range(date_start: tuple[int, ...],
                                    date_end: tuple[int, ...],
                                    precision: DatePrecision) -> tuple[tuple[int, ...], tuple[int, ...]]:
        if len(date_start) != 1 or len(date_end) != 1:
            return date_start, date_end
        start_y = date_start[0]
        end_y = date_end[0]
        match precision:
            case DatePrecision.DECADE:
                start_bucket = (start_y // 10) * 10
                end_bucket = (end_y // 10) * 10
                if end_bucket < start_bucket:
                    return (start_bucket,), (end_bucket,)
                if end_y % 10 == 9:
                    return (start_bucket,), (end_y,)
                if end_bucket == start_bucket:
                    return (start_bucket,), (start_bucket + 9,)
                return (start_bucket,), (end_bucket - 1,)
            case DatePrecision.CENTURY:
                start_bucket = (start_y // 100) * 100
                end_bucket = (end_y // 100) * 100
                if end_bucket < start_bucket:
                    return (start_bucket,), (end_bucket,)
                if end_y % 100 == 99:
                    return (start_bucket,), (end_y,)
                if end_bucket == start_bucket:
                    return (start_bucket,), (start_bucket + 99,)
                return (start_bucket,), (end_bucket - 1,)
            case _:
                return date_start, date_end

    @staticmethod
    def __collapse_normalized_input(date_start: tuple[int, ...],
                                    date_end: tuple[int, ...],
                                    precision: DatePrecision) -> tuple[tuple[int, ...], tuple[int, ...]]:
        if len(date_start) != 3 or len(date_end) != 3:
            return date_start, date_end
        match precision:
            case DatePrecision.DAY:
                return date_start, date_end
            case DatePrecision.MONTH:
                if date_start[0:2] == date_end[0:2] and date_start[2] == 1 and date_end[2] == gregorian.month_length(date_end[0], date_end[1]):
                    return date_start[:2], date_end[:2]
            case DatePrecision.YEAR:
                if date_start[1:] == (1, 1) and date_end[1:] == (12, gregorian.month_length(date_end[0], 12)):
                    return (date_start[0],), (date_end[0],)
            case DatePrecision.DECADE:
                if (date_start[1:] == (1, 1)
                        and date_end[1:] == (12, gregorian.month_length(date_end[0], 12))
                        and date_start[0] % 10 == 0
                        and date_end[0] % 10 == 9):
                    return (date_start[0],), (date_end[0],)
            case DatePrecision.CENTURY:
                if (date_start[1:] == (1, 1)
                        and date_end[1:] == (12, gregorian.month_length(date_end[0], 12))
                        and date_start[0] % 100 == 0
                        and date_end[0] % 100 == 99):
                    return (date_start[0],), (date_end[0],)
        return date_start, date_end

    @staticmethod
    def __normalized_range(date_tuple: tuple[int, ...], precision: DatePrecision) -> tuple[int, int, int, int, int, int]:
        if len(date_tuple) == 3:
            y, m, d = date_tuple
            return y, m, d, y, m, d
        if len(date_tuple) == 2:
            y, m = date_tuple
            ml = gregorian.month_length(y, m)
            return y, m, 1, y, m, ml
        y = date_tuple[0]
        match precision:
            case DatePrecision.YEAR:
                return y, 1, 1, y, 12, gregorian.month_length(y, 12)
            case DatePrecision.DECADE:
                end_y = y + 9
                return y, 1, 1, end_y, 12, gregorian.month_length(end_y, 12)
            case DatePrecision.CENTURY:
                end_y = y + 99
                return y, 1, 1, end_y, 12, gregorian.month_length(end_y, 12)
            case _:
                raise OldapErrorValue(f'Unsupported precision {precision} for year-only date.')

    def __init__(self,
                 dateStart: DatingTuple | str,
                 dateEnd: DatingTuple | str | None = None,
                 verbatimDate: str | None = None,
                 *,
                 datePrecision: DatePrecision | None = None,
                 inCalendar: OldapCalendar | str = OldapCalendar.GREGORIAN,
                 before: set[Self | None] | None = None,
                 iri: Iri | Xsd_QName | None = None) -> None:
        self.__iri = iri
        self._verbatimDate = verbatimDate
        self._beforeDating = {x for x in (before or set()) if x is not None}
        self._inCalendar = inCalendar if isinstance(inCalendar, OldapCalendar) else OldapCalendar.from_string(inCalendar)

        date_start_tuple, inferred_calendar = self.__normalize_date_tuple(dateStart, default_calendar=self._inCalendar)
        if inferred_calendar is not None:
            self._inCalendar = inferred_calendar

        if dateEnd is None:
            date_end_tuple = date_start_tuple
        else:
            date_end_tuple, end_calendar = self.__normalize_date_tuple(dateEnd, default_calendar=self._inCalendar)
            if end_calendar is not None and end_calendar != self._inCalendar:
                raise OldapErrorValue(f'Inconsistent calendar info: {end_calendar} != {self._inCalendar}')

        if datePrecision is not None:
            date_start_tuple, date_end_tuple = self.__collapse_normalized_input(date_start_tuple, date_end_tuple, datePrecision)
            date_start_tuple, date_end_tuple = self.__normalize_precision_range(date_start_tuple, date_end_tuple, datePrecision)

        if len(date_start_tuple) != len(date_end_tuple):
            raise OldapErrorValue(f'Invalid date format: {date_start_tuple} / {date_end_tuple}: inconsistent precision!')

        self._datePrecision = datePrecision or self.__infer_precision(date_start_tuple, date_end_tuple)
        self.__validate_precision(date_start_tuple, date_end_tuple, self._datePrecision)
        self._dateStartTuple = date_start_tuple
        self._dateEndTuple = date_end_tuple

        start_y, start_m, start_d, end_y, end_m, end_d = self.__normalized_range(date_start_tuple, self._datePrecision)
        if len(date_end_tuple) == 1:
            end_y = date_end_tuple[0]
            end_m = 12
            end_d = gregorian.month_length(end_y, end_m)
        elif len(date_end_tuple) > 1:
            if len(date_end_tuple) == 2:
                end_y, end_m = date_end_tuple
                end_d = gregorian.month_length(end_y, end_m)
            else:
                end_y, end_m, end_d = date_end_tuple

        match self._inCalendar:
            case OldapCalendar.GREGORIAN:
                self._normalizedStart = date(start_y, start_m, start_d)
                self._normalizedEnd = date(end_y, end_m, end_d)
            case OldapCalendar.JULIAN:
                self._normalizedStart = date(*julian.to_gregorian(start_y, start_m, start_d))
                self._normalizedEnd = date(*julian.to_gregorian(end_y, end_m, end_d))
            case OldapCalendar.HEBREW:
                self._normalizedStart = date(*hebrew.to_gregorian(start_y, start_m, start_d))
                self._normalizedEnd = date(*hebrew.to_gregorian(end_y, end_m, end_d))
            case OldapCalendar.ISLAMIC:
                self._normalizedStart = date(*islamic.to_gregorian(start_y, start_m, start_d))
                self._normalizedEnd = date(*islamic.to_gregorian(end_y, end_m, end_d))
            case OldapCalendar.PERSIAN:
                self._normalizedStart = date(*persian.to_gregorian(start_y, start_m, start_d))
                self._normalizedEnd = date(*persian.to_gregorian(end_y, end_m, end_d))
            case _:
                raise OldapErrorValue(f'Invalid calendar: {self._inCalendar}')

    def __str__(self) -> str:
        return f'{self._normalizedStart.isoformat()} - {self._normalizedEnd.isoformat()} ({self._inCalendar.name}, {self._datePrecision.name})'

    def __repr__(self) -> str:
        return f'Dating({self._dateStartTuple!r}, {self._dateEndTuple!r}, {self._verbatimDate!r}, inCalendar={self._inCalendar.name!r})'

    def __hash__(self) -> int:
        return hash((self._dateStartTuple, self._dateEndTuple, self._inCalendar, self._datePrecision))

    def __eq__(self, other: Self) -> bool:
        return (
            self._normalizedStart == other._normalizedStart and
            self._normalizedEnd == other._normalizedEnd and
            self._inCalendar == other._inCalendar and
            self._datePrecision == other._datePrecision
        )

    def __lt__(self, other: Self) -> bool:
        return (self._normalizedStart, self._normalizedEnd) < (other._normalizedStart, other._normalizedEnd)

    def __le__(self, other: Self) -> bool:
        return (self._normalizedStart, self._normalizedEnd) <= (other._normalizedStart, other._normalizedEnd)

    def __gt__(self, other: Self) -> bool:
        return (self._normalizedStart, self._normalizedEnd) > (other._normalizedStart, other._normalizedEnd)

    def __ge__(self, other: Self) -> bool:
        return (self._normalizedStart, self._normalizedEnd) >= (other._normalizedStart, other._normalizedEnd)

    def overlaps(self, other: Self) -> bool:
        return self._normalizedEnd >= other._normalizedStart and self._normalizedStart <= other._normalizedEnd

    def before(self, other: Self) -> bool:
        return self._normalizedEnd < other._normalizedStart

    def after(self, other: Self) -> bool:
        return self._normalizedStart > other._normalizedEnd

    @property
    def iri(self) -> Iri | Xsd_QName | None:
        return self.__iri

    def create(self, con: IConnection, project: Project | Iri | str, indent: int = 0, indent_inc: int = 4) -> None:
        if not isinstance(project, Project):
            project_obj = Project.read(con, project)
        else:
            project_obj = project
        if not self.__iri:
            self.__iri = Iri()
        graph = f'{project_obj.projectShortName}:data'
        blank = ''
        sparql = f'{blank:{indent * indent_inc}}INSERT DATA {{'
        sparql += f'\n{blank:{(indent + 1) * indent_inc}}GRAPH {graph} {{'
        sparql += f'\n{blank:{(indent + 2) * indent_inc}}{self.__iri.toRdf} a oldap:Dating'
        if self._verbatimDate:
            sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:verbatimDate """{self._verbatimDate}"""'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:normalizedStart "{self._normalizedStart.isoformat()}"^^xsd:date'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:normalizedEnd "{self._normalizedEnd.isoformat()}"^^xsd:date'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:datePrecision {self._datePrecision.value}'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:inCalendar {self._inCalendar.value}'
        if self._beforeDating:
            for x in self._beforeDating:
                sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}oldap:before {x.toRdf}'
        sparql += f' .\n{blank:{(indent + 1) * indent_inc}}}}'
        sparql += f'\n{blank:{indent * indent_inc}}}}'
        con.update_query(sparql)

    @property
    def toRdf(self) -> str:
        parts = []
        if self._verbatimDate:
            parts.append(f'oldap:verbatimDate """{self._verbatimDate}"""')
        parts.append(f'oldap:normalizedStart "{self._normalizedStart.isoformat()}"^^xsd:date')
        parts.append(f'oldap:normalizedEnd "{self._normalizedEnd.isoformat()}"^^xsd:date')
        parts.append(f'oldap:datePrecision {self._datePrecision.value}')
        parts.append(f'oldap:inCalendar {self._inCalendar.value}')
        for x in self._beforeDating:
            parts.append(f'oldap:before {x.toRdf}')
        return ' ;\n'.join(parts)

    def _as_dict(self) -> dict[str, object]:
        res: dict[str, object] = {
            'dateStart': list(self._dateStartTuple),
            'dateEnd': list(self._dateEndTuple),
            'inCalendar': self._inCalendar,
        }
        if self.__iri:
            res['iri'] = self.__iri
        if self._verbatimDate:
            res['verbatimDate'] = self._verbatimDate
        if self._datePrecision:
            res['datePrecision'] = self._datePrecision
        if self._beforeDating:
            res['before'] = list(self._beforeDating)
        return res


if __name__ == '__main__':
    d = Dating((1530,), (1560,), inCalendar=OldapCalendar.JULIAN)
    print(str(d))

    d = Dating('1666-10-11:JULIAN')
    print(str(d))

    jsonstr = json.dumps(d, default=serializer.encoder_default)
    d2 = json.loads(jsonstr, object_hook=serializer.decoder_hook)
    assert d == d2

    d = Dating((1880, 2), (1880, 5), 'Zwischen Feb. und Mai desselbigen Jahres')
    print(d.toRdf)

    d = Dating((1580, 2), (1580, 5),
               'Zwischen Feb. und Mai desselbigen Jahres',
               inCalendar='JULIAN')
    print(d.toRdf)
