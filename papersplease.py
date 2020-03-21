from collections import defaultdict
from datetime import datetime
from typing import Iterable, List, Tuple, Dict


FIELDS_TO_STR = {
    'NAME': 'name',
    'DOB': 'date of birth',
    'SEX': 'sex',
    'ID#': 'ID number',
    'NATION': 'nationality',
}
MISMATCH_FIELDS = tuple(FIELDS_TO_STR.keys())
TODAY = datetime(1982, 11, 22)
COUNTRIES = {'arstotzka', 'antegria', 'impor', 'kolechia', 'obristan', 'republia', 'united federation'}


Documents = Dict[str, Dict[str, str]]


def parse_document(document: str) -> Dict[str, str]:
    entries = document.split('\n')
    parsed = {}
    for entry in entries:
        title, data = entry.strip().split(': ')
        parsed[title] = data
    return parsed


def check_mismatches(documents: Documents, fields: Iterable[str] = MISMATCH_FIELDS) -> List[Tuple[str, set]]:
    mismatches = []
    for field in fields:
        values = set(
            document[field]
            for document in documents.values()
            if field in document
        )
        if len(values) > 1:
            mismatches.append((field, values))
    return mismatches


def check_expirations(documents: Documents, check_date=TODAY) -> List[str]:
    expired = []
    for document_title, document in documents.items():
        date = document.get('EXP')
        if date:
            if datetime.strptime(date, '%Y.%m.%d') < check_date:
                expired.append(document_title)
    return expired


def get_name(documents: Documents) -> str:
    name = None
    for document in documents.values():
        name = document.get('NAME')
        if name:
            break
    return name


def get_nationality(documents: Documents) -> str:
    nationality = None
    for document in documents.values():
        nationality = document.get('NATION')
        if nationality:
            break
    return nationality


class Inspector:
    def __init__(self):
        self.allowed_countries = {'arstotzka'}
        self.required_documents = defaultdict(set)
        self.required_vaccinations = defaultdict(set)
        self.wanted_criminals = set()
        self.work_pass_required = False

    def receive_bulletin(self, bulletin: str):
        entries = bulletin.split('\n')
        for entry in entries:
            entry = entry.strip()

            if 'Foreigners' in entry:
                rep = f'Citizens of {", ".join(COUNTRIES.difference({"arstotzka"}))}'
                entry = entry.replace('Foreigners', rep)

            if 'Entrants' in entry:
                rep = f'Citizens of {", ".join(COUNTRIES)}'
                entry = entry.replace('Entrants', rep)

            print(entry)

            if entry.startswith('Allow citizens of '):
                countries = entry[len('Allow citizens of '):].split(', ')
                countries = set(map(str.lower, countries))
                self.allowed_countries = self.allowed_countries.union(countries)

            elif entry.startswith('Deny citizens of '):
                countries = entry[len('Deny citizens of '):].split(', ')
                countries = set(map(str.lower, countries))
                self.allowed_countries = self.allowed_countries.difference(countries)

            elif entry.startswith('Wanted by the State: '):
                name = entry[len('Wanted by the State: '):]
                first, last = name.split(' ')
                self.wanted_criminals.add(f"{last}, {first}")

            elif 'no longer require' in entry:
                end = entry.find(' no longer require')
                if 'Citizens of ' in entry:
                    beg = entry.find('of ') + 3
                    categories = set(entry[beg:end].split(', '))
                elif 'Workers' in entry:
                    self.work_pass_required = False
                    continue
                else:
                    raise ValueError(f"Cannot parse entry {entry}.")

                requirement = entry[entry.find(' require') + len(' require '):]
                if 'vaccination' in requirement:
                    disease = " ".join(requirement.split(' ')[:-1])
                    for category in categories:
                        self.required_vaccinations[category.lower()].remove(disease)
                else:
                    for category in categories:
                        self.required_documents[category.lower()].remove(requirement)

            elif 'require' in entry:
                end = entry.find(' require')
                if 'Citizens of ' in entry:
                    beg = entry.find('of ') + 3
                    categories = set(entry[beg:end].split(', '))
                elif 'Workers' in entry:
                    self.work_pass_required = True
                    continue
                else:
                    raise ValueError(f"Cannot parse entry {entry}.")

                requirement = entry[entry.find(' require') + len(' require '):]
                if 'vaccination' in requirement:
                    disease = " ".join(requirement.split(' ')[:-1])
                    for category in categories:
                        self.required_vaccinations[category.lower()].add(disease)
                else:
                    for category in categories:
                        self.required_documents[category.lower()].add(requirement)

            else:
                raise ValueError(f"Could not parse entry : {entry}")

        print("\n"*3, self)

    def __str__(self):
        lines = ["Rules :"]
        if self.allowed_countries:
            lines.append(f"Allowed countries : {self.allowed_countries}")
        if self.required_documents:
            lines.append(f"Required documents : ")
            for country, items in self.required_documents.items():
                if items:
                    lines.append(f" {country:10s} : {items}")
        if self.required_vaccinations:
            lines.append(f"Required vaccinations : ")
            for country, items in self.required_vaccinations.items():
                if items:
                    lines.append(f" {country:10s} : {items}")
        if self.wanted_criminals:
            lines.append(f"Wanted criminals : {self.wanted_criminals}")

        return "\n".join(lines)

    def inspect(self, entrant: dict) -> str:
        documents = {
            document_title.replace('_', ' ').lower(): parse_document(document)
            for document_title, document in entrant.items()
        }

        mismatches = check_mismatches(documents)
        if mismatches:
            return f'Detainment: {FIELDS_TO_STR[mismatches[0][0]]} mismatch.'

        name = get_name(documents)

        # Check if wanted
        if name in self.wanted_criminals:
            return 'Detainment: Entrant is a wanted criminal.'

        nationality = get_nationality(documents)
        if nationality:
            nationality = nationality.lower()

        # Check required documents except access permits
        if nationality is None:
            required_documents = set().union(*self.required_documents.values())
        else:
            required_documents = self.required_documents[nationality]
        for required_document in required_documents:
            if required_document == 'access permit':
                continue
            if required_document.lower() not in documents:
                return f'Entry denied: missing required {required_document}.'

        # Check expiration dates
        expirations = check_expirations(documents)
        if expirations:
            document_title = expirations[0].replace("_", " ")
            return f'Entry denied: {document_title} expired.'

        # Check access permits
        if nationality != 'arstotzka':
            if 'access permit' in self.required_documents[nationality]:
                if 'access permit' not in documents:
                    valid_access = False
                    if 'grant of asylum' in documents:
                        valid_access = True
                    elif 'diplomatic authorization' in documents:
                        document = documents['diplomatic authorization']
                        authorized_countries = set(document['ACCESS'].split(', '))
                        if 'Arstotzka' not in authorized_countries:
                            return f'Entry denied: invalid diplomatic authorization.'
                        valid_access = True

                    if not valid_access:
                        return f'Entry denied: missing required access permit.'
                else:
                    if self.work_pass_required:
                        visit_purpose = documents['access permit']['PURPOSE']
                        if visit_purpose == "WORK":
                            if "work pass" not in documents:
                                print("DOCUMENTS : ", documents)
                                return 'Entry denied: missing required work pass.'

        # Check for allowed nationality
        if nationality not in self.allowed_countries:
            return 'Entry denied: citizen of banned nation.'

        # Check vaccinations
        required_vaccinations = self.required_vaccinations[nationality]
        if required_vaccinations:
            if 'certificate of vaccination' not in documents:
                return 'Entry denied: missing required certificate of vaccination.'
            vaccinations = set(documents['certificate of vaccination']['VACCINES'].split(', '))
            if not required_vaccinations.issubset(vaccinations):
                return 'Entry denied: missing required vaccination.'

        # Farewell
        if nationality == 'arstotzka':
            return 'Glory to Arstotzka.'
        else:
            return 'Cause no trouble.'
