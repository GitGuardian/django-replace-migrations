import re

from django import get_version
from django.db.migrations.operations.special import (
    RunPython,
    RunSQL,
    SeparateDatabaseAndState,
)
from django.db.migrations.writer import MigrationWriter, OperationWriter
from django.utils.timezone import now


class ReplaceMigrationWriter(MigrationWriter):
    def as_string(self):
        """Return a string of the file contents."""
        items = {
            "replaces_str": "",
            "initial_str": "",
        }

        imports = set()

        # Deconstruct operations
        operations = []
        for operation in self.migration.operations:
            if isinstance(operation, (RunPython, RunSQL, SeparateDatabaseAndState)):
                continue
            operation_string, operation_imports = OperationWriter(operation).serialize()
            imports.update(operation_imports)
            operations.append(operation_string)
        items["operations"] = "\n".join(operations) + "\n" if operations else ""

        # Deconstruct special_operations
        special_operations = []
        for special_op in self.migration.operations:
            if (
                isinstance(special_op, (RunPython, RunSQL, SeparateDatabaseAndState))
                and not special_op.elidable
            ):
                operation_string, operation_imports = OperationWriter(
                    special_op
                ).serialize()
                imports.update(operation_imports)
                special_operations.append(operation_string)
        special_ops = (
            "\n".join(special_operations) + "\n" if special_operations else None
        )
        items["special_operations"] = (
            "\n    # /!\\ PRINT ALL THE SPECIAL OPERATIONS\n"
            + "    # /!\\ MUST BE MANUALLY REVIEWED\n\n"
            + "   special_operations = [\n"
            + special_ops
            + "   ]\n"
            if special_ops
            else ""
        )

        # Format dependencies and write out swappable dependencies right
        dependencies = []
        for dependency in self.migration.dependencies:
            if dependency[0] == "__setting__":
                dependencies.append(
                    f"        migrations.swappable_dependency(settings.{dependency[1]}),"
                )
                imports.add("from django.conf import settings")
            else:
                dependencies.append(f"        {self.serialize(dependency)[0]},")
        items["dependencies"] = (
            "\n".join(sorted(dependencies)) + "\n" if dependencies else ""
        )

        # Format imports nicely, swapping imports of functions from migration files
        # for comments
        migration_imports = set()
        for line in list(imports):
            if re.match(r"^import (.*)\.\d+[^\s]*$", line):
                migration_imports.add(line.split("import")[1].strip())
                imports.remove(line)
                self.needs_manual_porting = True

        # django.db.migrations is always used, but models import may not be.
        # If models import exists, merge it with migrations import.
        if "from django.db import models" in imports:
            imports.discard("from django.db import models")
            imports.add("from django.db import migrations, models")
        else:
            imports.add("from django.db import migrations")

        # Sort imports by the package / module to be imported (the part after
        # "from" in "from ... import ..." or after "import" in "import ...").
        sorted_imports = sorted(imports, key=lambda i: i.split()[1])
        items["imports"] = "\n".join(sorted_imports) + "\n" if imports else ""
        if migration_imports:
            items["imports"] += (
                "\n\n# Functions from the following migrations need manual "
                "copying.\n# Move them and any dependencies into this file, "
                "then update the\n# RunPython operations to refer to the local "
                "versions:\n# %s"
            ) % "\n# ".join(sorted(migration_imports))
        # If there's a replaces, make a string for it
        if self.migration.replaces:
            items[
                "replaces_str"
            ] = f"\n    replaces = {self.serialize(sorted(self.migration.replaces))[0]}\n"
        # Hinting that goes into comment
        if self.include_header:
            items["migration_header"] = MIGRATION_HEADER_TEMPLATE % {
                "version": get_version(),
                "timestamp": now().strftime("%Y-%m-%d %H:%M"),
            }
        else:
            items["migration_header"] = ""

        if self.migration.initial:
            items["initial_str"] = "\n    initial = True\n"

        return MIGRATION_TEMPLATE % items


MIGRATION_HEADER_TEMPLATE = """\
# Generated by Django %(version)s on %(timestamp)s

"""


MIGRATION_TEMPLATE = """\
%(migration_header)s%(imports)s

from phased_migrations.constants import DeployPhase


class Migration(migrations.Migration):
    # Note: deploy_phase was added to ensure consistency with no down time
    # it is possible that this migration in not really compatible with pre-deploy
    deploy_phase = DeployPhase.pre_deploy

    squashed_with_gg_script = True

%(replaces_str)s%(initial_str)s
    dependencies = [
%(dependencies)s\
    ]

    operations = [
%(operations)s\
    ]

%(special_operations)s
"""
