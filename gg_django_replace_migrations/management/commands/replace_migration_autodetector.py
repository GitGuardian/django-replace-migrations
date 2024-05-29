import re

from django.db.migrations.autodetector import MigrationAutodetector


class ReplaceMigrationAutodetector(MigrationAutodetector):
    @classmethod
    def parse_number(cls, name):
        """
        Given a migration name, try to extract a number from the beginning of
        it. For a squashed migration such as '0001_squashed_0004…', return the
        second number. If no number is found, return None.
        """
        if squashed_match := re.search(r"(\d+)_squashed_.*", name):
            return int(squashed_match[1])
        return None
